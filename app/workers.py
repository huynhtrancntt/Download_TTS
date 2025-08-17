import os
import tempfile
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from PySide6.QtCore import QThread, Signal
from pydub import AudioSegment

from app.constants import TEMP_PREFIX, OUTPUT_DIR
from app.utils.helps import split_text, tts_sync_save, get_mp3_duration_ms, save_log_entry

# ---------- Tab 1: MTProducerWorker (đa luồng, phát đúng thứ tự) ----------


class MTProducerWorker(QThread):
    segment_ready = Signal(str, int, int)  # path, duration_ms, index1
    progress = Signal(int, int)
    status = Signal(str)
    all_done = Signal()
    error = Signal(str)

    def __init__(self, text: str, voice: str, rate: int, pitch: int, max_len: int, workers: int):
        super().__init__()
        self.text = text
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.max_len = max_len
        self.workers = max(1, workers)
        self.stop_flag = False
        self.tmpdir = None

    def stop(self):
        self.stop_flag = True

    def run(self):
        try:
            if not self.text.strip():
                self.error.emit("Chưa có nội dung văn bản.")
                return

            chunks = split_text(self.text, self.max_len)
            total = len(chunks)
            if total == 0:
                self.error.emit("Không tách được đoạn nào từ văn bản.")
                return

            self.tmpdir = tempfile.mkdtemp(prefix=TEMP_PREFIX)
            self.status.emit(
                f"🚀 Bắt đầu sinh {total} đoạn bằng {self.workers} luồng…")

            completed = {}
            next_index = 1
            emitted = 0

            def job(index1: int, content: str):
                path = os.path.join(self.tmpdir, f"part_{index1:04d}.mp3")
                tts_sync_save(content, path, self.voice, self.rate, self.pitch)
                dur = get_mp3_duration_ms(path)
                return (index1, path, dur)

            with ThreadPoolExecutor(max_workers=self.workers) as ex:
                futs = [ex.submit(job, i+1, c) for i, c in enumerate(chunks)]
                for fut in as_completed(futs):
                    if self.stop_flag:
                        break
                    try:
                        idx1, path, dur = fut.result()
                    except Exception as e:
                        self.status.emit(f"⚠️ Lỗi tạo 1 đoạn: {e}")
                        continue
                    completed[idx1] = (path, dur)

                    while next_index in completed:
                        p, d = completed.pop(next_index)
                        self.segment_ready.emit(p, d, next_index)
                        emitted += 1
                        self.progress.emit(emitted, total)
                        next_index += 1

            while not self.stop_flag and next_index in completed:
                p, d = completed.pop(next_index)
                self.segment_ready.emit(p, d, next_index)
                emitted += 1
                self.progress.emit(emitted, total)
                next_index += 1

            self.all_done.emit()

        except Exception as e:
            self.error.emit(str(e))


# ---------- Tab 2: OneFileWorker & BatchWorker ----------


class OneFileWorker(QThread):
    progress = Signal(int, int, str)   # created_chunks, total_chunks, filename
    status = Signal(str, str)          # status_msg, filename
    done = Signal(str, str)            # output_path, filename
    failed = Signal(str, str)          # error_msg, filename

    def __init__(self, txt_path: str, voice: str, rate: int, pitch: int,
                 maxlen: int, gap_ms: int, workers_chunk: int):
        super().__init__()
        self.txt_path = txt_path
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.maxlen = maxlen
        self.gap_ms = gap_ms
        self.workers_chunk = max(1, workers_chunk)
        self.tempdir = None
        self.stop_flag = False

    def stop(self): self.stop_flag = True

    def run(self):
        start_time = datetime.now().isoformat()
        base_name = Path(self.txt_path).stem
        self.tempdir = Path(tempfile.mkdtemp(prefix=TEMP_PREFIX))

        try:
            with open(self.txt_path, "r", encoding="utf-8") as f:
                text = f.read()
            chunks = split_text(text, self.maxlen)

            total = len(chunks)
            if total == 0:
                raise RuntimeError("File rỗng hoặc không thể tách đoạn.")

            self.status.emit(
                f"🔧 {base_name}: Tạo {total} đoạn bằng {self.workers_chunk} luồng…", base_name)

            results, emitted = {}, 0

            def job(idx1: int, content: str):
                part_path = str(self.tempdir / f"part_{idx1:04d}.mp3")
                tts_sync_save(content, part_path, self.voice,
                              self.rate, self.pitch)
                d = get_mp3_duration_ms(part_path)
                return (idx1, part_path, d)

            with ThreadPoolExecutor(max_workers=self.workers_chunk) as ex:
                futs = [ex.submit(job, i+1, c) for i, c in enumerate(chunks)]
                for fut in as_completed(futs):
                    if self.stop_flag:
                        break
                    try:
                        idx1, p, d = fut.result()
                        results[idx1] = (p, d)
                    except Exception as e:
                        self.status.emit(
                            f"⚠️ {base_name}: lỗi đoạn - {e}", base_name)
                    emitted += 1
                    self.progress.emit(min(emitted, total), total, base_name)

            if self.stop_flag:
                raise RuntimeError("Bị dừng bởi người dùng.")

            gap = AudioSegment.silent(duration=self.gap_ms)
            final = AudioSegment.silent(duration=0)
            total_ms = 0
            for idx in range(1, total + 1):
                if idx not in results:
                    self.status.emit(
                        f"⚠️ {base_name}: thiếu đoạn {idx}, bỏ qua.", base_name)
                    continue
                seg = AudioSegment.from_file(results[idx][0])
                total_ms += results[idx][1]
                final += seg + gap

            out_name = f"{base_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
            out_path = OUTPUT_DIR / out_name
            final.export(str(out_path), format="mp3")

            self.status.emit(
                f"✅ {base_name}: xong -> {out_path.name}", base_name)
            self.done.emit(str(out_path), base_name)

            entry = {
                "input_file": str(self.txt_path),
                "output_file": str(out_path),
                "media_type": "audio/mp3",
                "voice": self.voice,
                "rate_percent": self.rate,
                "pitch_hz": self.pitch,
                "max_chunk_chars": self.maxlen,
                "gap_ms": self.gap_ms,
                "created_chunks": emitted,
                "total_duration_ms_est": total_ms,
                "started_at": start_time,
                "finished_at": datetime.now().isoformat(),
                "status": "success",
            }
            save_log_entry(entry)

        except Exception as e:
            msg = f"❌ {base_name}: {e}"
            self.failed.emit(msg, base_name)
            entry = {
                "input_file": str(self.txt_path),
                "output_file": None,
                "media_type": "audio/mp3",
                "voice": self.voice,
                "rate_percent": self.rate,
                "pitch_hz": self.pitch,
                "max_chunk_chars": self.maxlen,
                "gap_ms": self.gap_ms,
                "started_at": start_time,
                "finished_at": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e),
            }
            save_log_entry(entry)
        finally:
            try:
                if self.tempdir and self.tempdir.exists():
                    import shutil
                    shutil.rmtree(self.tempdir, ignore_errors=True)
            except Exception:
                pass


class BatchWorker(QThread):
    fileProgress = Signal(int, int)
    fileStatus = Signal(str)
    attachWorker = Signal(object, str)

    def __init__(self, files: list[str], voice: str, rate: int, pitch: int,
                 maxlen: int, gap_ms: int, workers_chunk: int, workers_file: int):
        super().__init__()
        self.files = files
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.maxlen = maxlen
        self.gap_ms = gap_ms
        self.workers_chunk = workers_chunk
        self.workers_file = max(1, workers_file)
        self.stop_flag = False
        self.children: list[OneFileWorker] = []

    def stop(self):
        self.stop_flag = True
        for w in self.children:
            try:
                w.stop()
            except Exception:
                pass

    def run(self):
        total = len(self.files)
        done = 0
        self.fileStatus.emit(
            f"🚀 Xử lý {total} file với {self.workers_file} file song song…")
        idx = 0
        active: list[OneFileWorker] = []
        try:
            while idx < total or active:
                while idx < total and len(active) < self.workers_file and not self.stop_flag:
                    f = self.files[idx]
                    w = OneFileWorker(f, self.voice, self.rate, self.pitch,
                                      self.maxlen, self.gap_ms, self.workers_chunk)
                    self.children.append(w)
                    self.attachWorker.emit(w, Path(f).name)
                    w.start()
                    active.append(w)
                    idx += 1
                for w in list(active):
                    if not w.isRunning():
                        active.remove(w)
                        done += 1
                        self.fileProgress.emit(done, total)
                self.msleep(100)
        finally:
            self.fileStatus.emit("🏁 Hoàn tất batch.")
