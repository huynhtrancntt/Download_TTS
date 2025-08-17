# -*- coding: utf-8 -*-
"""
Workers cho xử lý TTS đa luồng
Chứa các worker class để xử lý text-to-speech song song và batch processing
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List

from PySide6.QtCore import QThread, Signal
from pydub import AudioSegment

from app.appConfig import AppConfig
from app.utils.helps import split_text, tts_sync_save, save_log_entry
from app.utils.audio_helpers import get_mp3_duration_ms, hide_directory_on_windows

# ==================== MTProducerWorker - Worker đa luồng cho Tab TTS ====================


class MTProducerWorker(QThread):
    """
    Worker đa luồng cho việc tạo audio TTS
    Xử lý văn bản song song và phát theo đúng thứ tự

    Signals:
        segment_ready: Phát khi một đoạn audio được tạo xong (path, duration_ms, index)
        progress: Tiến trình xử lý (completed, total)
        status: Thông báo trạng thái
        all_done: Hoàn thành tất cả
        error: Có lỗi xảy ra
    """

    # Định nghĩa các signals
    segment_ready = Signal(str, int, int)  # path, duration_ms, index1
    progress = Signal(int, int)            # completed, total
    status = Signal(str)                   # status message
    all_done = Signal()                    # all processing done
    error = Signal(str)                    # error message

    def __init__(self, text: str, voice: str, rate: int, pitch: int, max_len: int, workers: int) -> None:
        """
        Khởi tạo worker TTS đa luồng

        Args:
            text: Văn bản cần chuyển đổi
            voice: Giọng nói (ví dụ: "vi-VN-HoaiMyNeural")
            rate: Tốc độ (-50 đến 50)
            pitch: Cao độ (-12 đến 12)
            max_len: Độ dài tối đa mỗi đoạn (ký tự)
            workers: Số luồng xử lý song song
        """
        super().__init__()

        # Tham số TTS
        self.text: str = text
        self.voice: str = voice
        self.rate: int = rate
        self.pitch: int = pitch
        self.max_len: int = max_len
        self.workers: int = max(1, workers)  # Tối thiểu 1 worker

        # Trạng thái worker
        self.stop_flag: bool = False
        self.tmpdir: Optional[str] = None

    def stop(self) -> None:
        """
        Dừng worker (set flag để các thread con dừng)
        """
        self.stop_flag = True

    def run(self) -> None:
        """
        Phương thức chính chạy worker TTS
        Chia văn bản thành chunks và xử lý song song
        """
        try:
            # Kiểm tra văn bản đầu vào
            if not self.text.strip():
                self.error.emit("❌ Chưa có nội dung văn bản để xử lý.")
                return

            # Chia văn bản thành các đoạn nhỏ
            chunks = split_text(self.text, self.max_len)
            total = len(chunks)

            if total == 0:
                self.error.emit("❌ Không thể tách văn bản thành các đoạn.")
                return

            # Tạo thư mục tạm để lưu các file audio
            self.tmpdir = tempfile.mkdtemp(prefix=AppConfig.TEMP_PREFIX)

            hide_directory_on_windows(self.tmpdir)

            self.status.emit(
                f"🚀 Bắt đầu sinh {total} đoạn audio bằng {self.workers} luồng...")

            # Khởi tạo biến theo dõi tiến trình
            # Dict lưu kết quả đã hoàn thành {index: (path, duration)}
            completed = {}
            next_index = 1  # Index tiếp theo cần emit
            emitted = 0     # Số đoạn đã emit

            def job(index1: int, content: str) -> tuple:
                """
                Job function cho mỗi worker thread
                Args:
                    index1: Index của đoạn (1-based)
                    content: Nội dung văn bản đoạn
                Returns:
                    tuple: (index, path, duration_ms)
                """
                try:
                    path = os.path.join(self.tmpdir, f"part_{index1:04d}.mp3")
                    tts_sync_save(content, path, self.voice,
                                  self.rate, self.pitch)
                    dur = get_mp3_duration_ms(path)
                    return (index1, path, dur)
                except Exception as e:
                    raise Exception(f"Lỗi xử lý đoạn {index1}: {str(e)}")

            # Xử lý đa luồng với ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                # Submit tất cả jobs
                futures = [executor.submit(job, i+1, chunk)
                           for i, chunk in enumerate(chunks)]

                # Xử lý kết quả khi hoàn thành
                for future in as_completed(futures):
                    if self.stop_flag:
                        self.status.emit("⏹ Đã dừng theo yêu cầu người dùng.")
                        break

                    try:
                        idx1, path, dur = future.result()
                        completed[idx1] = (path, dur)
                    except Exception as e:
                        self.status.emit(f"⚠️ {str(e)}")
                        continue

                    # Emit các đoạn theo đúng thứ tự
                    while next_index in completed:
                        p, d = completed.pop(next_index)
                        self.segment_ready.emit(p, d, next_index)
                        emitted += 1
                        self.progress.emit(emitted, total)
                        next_index += 1

            # Emit các đoạn còn lại (nếu có)
            while not self.stop_flag and next_index in completed:
                p, d = completed.pop(next_index)
                self.segment_ready.emit(p, d, next_index)
                emitted += 1
                self.progress.emit(emitted, total)
                next_index += 1

            if not self.stop_flag:
                self.status.emit(
                    f"✅ Hoàn thành tạo {emitted}/{total} đoạn audio.")
                self.all_done.emit()

        except Exception as e:
            self.error.emit(f"❌ Lỗi nghiêm trọng: {str(e)}")


# ==================== OneFileWorker & BatchWorker - Workers cho xử lý batch files ====================


class OneFileWorker(QThread):
    """
    Worker xử lý một file văn bản thành audio
    Sử dụng cho chức năng batch convert nhiều file

    Signals:
        progress: Tiến trình xử lý chunks (created, total, filename)
        status: Trạng thái xử lý (message, filename)
        done: Hoàn thành (output_path, filename)
        failed: Thất bại (error_msg, filename)
    """

    # Định nghĩa signals
    progress = Signal(int, int, str)   # created_chunks, total_chunks, filename
    status = Signal(str, str)          # status_msg, filename
    done = Signal(str, str)            # output_path, filename
    failed = Signal(str, str)          # error_msg, filename

    def __init__(self, txt_path: str, voice: str, rate: int, pitch: int,
                 maxlen: int, gap_ms: int, workers_chunk: int) -> None:
        """
        Khởi tạo worker xử lý một file

        Args:
            txt_path: Đường dẫn file văn bản
            voice: Giọng nói
            rate: Tốc độ
            pitch: Cao độ
            maxlen: Độ dài tối đa mỗi chunk
            gap_ms: Khoảng cách giữa các chunk (ms)
            workers_chunk: Số luồng xử lý chunk
        """
        super().__init__()

        # Tham số xử lý
        self.txt_path: str = txt_path
        self.voice: str = voice
        self.rate: int = rate
        self.pitch: int = pitch
        self.maxlen: int = maxlen
        self.gap_ms: int = gap_ms
        self.workers_chunk: int = max(1, workers_chunk)

        # Trạng thái worker
        self.tempdir: Optional[Path] = None
        self.stop_flag: bool = False

    def stop(self) -> None:
        """Dừng worker"""
        self.stop_flag = True

    def run(self):
        start_time = datetime.now().isoformat()
        base_name = Path(self.txt_path).stem
        self.tempdir = Path(tempfile.mkdtemp(prefix=AppConfig.TEMP_PREFIX))

        hide_directory_on_windows(self.tmpdir)

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
            out_path = AppConfig.OUTPUT_DIR / out_name
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
