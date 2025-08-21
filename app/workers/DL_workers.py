# -*- coding: utf-8 -*-
"""
Workers cho xử lý TTS đa luồng
Chứa các worker class để xử lý text-to-speech song song và batch processing
"""

import os
import tempfile
from datetime import datetime
import time
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List

from PySide6.QtCore import QThread, Signal

from app.core.config import AppConfig
from app.utils.helps import split_text, tts_sync_save, save_log_entry, group_by_char_limit_with_len
from app.utils.audio_helpers import get_mp3_duration_ms
from app.utils.helps import hide_directory_on_windows
from app.utils.historyLog import save_history_log
import json
import uuid
from app.ui_setting import resource_path
import subprocess
import re
PROGRESS_RE = re.compile(r"\[download\]\s+(\d{1,3}(?:\.\d{1,2})?)%")
class NTDownloadWorker(QThread):
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
    segment_ready = Signal(str, str)  # path, duration_ms, index1
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
        self.text: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        # self.text: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.voice: str = voice
        self.rate: int = rate
        self.pitch: int = pitch
        self.max_len: int = max_len
        self.workers: int = max(1, workers)  # Tối thiểu 1 worker
        self.group_max_items: int = 10      # NEW: tối đa bao nhiêu ý/nhóm
        self.group_sep: str = " | "
        # Trạng thái worker
        self.stop_flag: bool = False
        self.tmpdir: Optional[str] = None
        self.video_mode: str = "Video"
        self.ffmpeg_path: str = resource_path(os.path.join("data", "ffmpeg.exe"))
        self.ytdlp_path: str = resource_path(os.path.join("data", "yt-dlp.exe"))
        self.subtitle_only: bool = False
        self.audio_only: bool = False
        self.sub_mode: str = "1"
        self.sub_lang: str = "vi"
        self.include_thumb: bool = False

    def stop(self) -> None:
        """
        Dừng worker (set flag để các thread con dừng)
        """
        self.stop_flag = True

    def run(self) -> None:

        try:
            # Kiểm tra văn bản đầu vào
            if not self.text.strip():
                self.error.emit("❌ Chưa có nội dung văn bản để xử lý.")
                return
            chunks = [u.strip() for u in self.text.splitlines() if u.strip()]
            print(chunks)
            # chunks = [chunk for (chunk, _len_) in grouped]
            total = len(chunks)
            if total == 0:
                self.error.emit("❌ Không thể tách văn bản thành các đoạn.")
                return

            # self.tmpdir = Path(tempfile.mkdtemp(prefix=AppConfig.TEMP_PREFIX))

            self.status.emit(
                f"🚀 Bắt đầu sinh {total} đoạn audio bằng {self.workers} luồng...")

            # Khởi tạo biến theo dõi tiến trình
            # Dict lưu kết quả đã hoàn thành {index: (path, duration)}
            completed = {}
            next_index = 1  # Index tiếp theo cần emit
            emitted = 0     # Số đoạn đã emit

            def job(index1: int, content: str) -> tuple:

                try:
                    
                    if not os.path.exists(self.ytdlp_path):
                        self.ytdlp_path = "yt-dlp"

                    get_title_cmd = [
                        self.ytdlp_path,
                        "--encoding", "utf-8",
                        "--get-title", content,
                        "--no-warnings",
                        "--no-check-certificate",
                    ]
                    result = subprocess.run(
                        get_title_cmd,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                    )

                    if result.returncode != 0:
                        raise Exception(result.stderr.strip() or "yt-dlp failed to get title")

                    title = result.stdout.strip().splitlines()[0] if result.stdout else ""

                    output_filename = f"{index1:02d}.{title}.%(ext)s"
                    if self.video_mode != "Video":
                        output_filename = f"playlist.{index1:02d}.{title}.%(ext)s"
                    # print(f"output_filename {output_filename}")
                    self.tmpdir = Path(tempfile.mkdtemp(prefix="yt_download_"))
                    self.tmpdir = self.tmpdir / str(uuid.uuid4())
                    temp_output = self.tmpdir / output_filename  # Path object
                    print(f"temp_output {temp_output}")
                    download_cmd = self._build_command(self.ytdlp_path, temp_output, content)
                    # print(f"download_cmd {download_cmd}")
                    self.process = subprocess.Popen(
                        download_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL,
                        text=True,
                        bufsize=1,
                        encoding="utf-8",
                        creationflags=0
                    )


                    for line in self.process.stdout:
                        if self.stop_flag:
                            self.process.kill()
                            self.process.terminate()
                            self.status.emit("⏹ Đã dừng theo yêu cầu người dùng.")
                            return

                        if line.strip():
                        
                        
                            match = PROGRESS_RE.search(line)
                            if match:
                                percent = int(float(match.group(1)))
                                # self.status.emit(f"{percent}%")
                    # temp_output = os.path.join(self.temp_dir, output_filename)

                    return (index1,content, title,temp_output)
                except Exception as e:
                    raise Exception(f"Lỗi xử lý đoạn {index1}: {str(e)}")

            # Xử lý đa luồng theo batch để tránh treo và rate-limit
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                batch_size = 150
                for batch_start in range(0, total, batch_size):
                    if self.stop_flag:
                        self.status.emit("⏹ Đã dừng theo yêu cầu người dùng.")
                        break

                    batch_end = min(total, batch_start + batch_size)
                    # Submit batch hiện tại
                    futures = [executor.submit(job, i + 1, chunks[i])
                               for i in range(batch_start, batch_end)]

                    # Xử lý kết quả của batch
                    for future in as_completed(futures):
                        if self.stop_flag:
                            self.status.emit(
                                "⏹ Đã dừng theo yêu cầu người dùng.")
                            break

                        try:
                            idx1, url, title, temp_output = future.result()
                            completed[idx1] = (url, title)
                        except Exception as e:
                            self.status.emit(f"⚠️ {str(e)}")
                            continue

                        # Emit các đoạn theo đúng thứ tự (status + progress)
                        while next_index in completed:
                            url, title = completed.pop(next_index)
                            self.segment_ready.emit(url, title)
                            emitted += 1
                            self.progress.emit(emitted, total)
                            next_index += 1

                    if self.stop_flag:
                        break

                    # Nếu còn batch kế tiếp, nghỉ ngẫu nhiên 500-700s như yêu cầu
                    if batch_end < total:
                        delay_sec = random.randint(10, 20)
                        # self.status.emit(
                        #     f"⏳ Tạm dừng {delay_sec}s để tránh giới hạn hệ thống, sẽ tiếp tục sau…"
                        # )
                        remaining_ms = delay_sec * 1000
                        # Ngủ theo bước nhỏ để có thể dừng sớm nếu người dùng bấm dừng
                        while remaining_ms > 0 and not self.stop_flag:
                            step = min(200, remaining_ms)
                            self.msleep(step)
                            remaining_ms -= step

            # Emit các đoạn còn lại (nếu có)
            while not self.stop_flag and next_index in completed:
                url, title = completed.pop(next_index)
                self.segment_ready.emit(url, title)
                emitted += 1
                self.progress.emit(emitted, total)
                next_index += 1

            if not self.stop_flag:

                self.all_done.emit()

        except Exception as e:
            self.error.emit(f"❌ Lỗi nghiêm trọng: {str(e)}")




    # Remove duplicate legacy helpers below (kept single implementations above)
    def _build_command(self, ytdlp_path, output, url):
        """Xây dựng lệnh yt-dlp"""
        cmd = [ytdlp_path]
        cmd += ["--encoding", "utf-8"]
        cmd += [url, "--progress", "--newline"]
        # Thêm đường dẫn ffmpeg nếu tồn tại
        if os.path.exists(self.ffmpeg_path):
            cmd += ["--ffmpeg-location", self.ffmpeg_path]

        # Xử lý từng chế độ download cụ thể
        if self.subtitle_only:
            # Chỉ tải phụ đề
            cmd.append("--skip-download")
            self.message_signal.emit("📝 Chế độ: Chỉ tải phụ đề", "")
        else:
            # Tải cả video MP4 và audio MP3
            cmd += ["-f", "bv*+ba/b", "--merge-output-format", "mp4"]

        if self.audio_only:
            cmd += ["--extract-audio", "--audio-format", "mp3", "--keep-video"]
            self.message_signal.emit("🎬 Chế độ: Tải MP3", "")

        cmd += ["-o", output]

        # Đặt timeout/kịch bản retry để tránh treo khi mạng chập chờn
        # cmd += [
        #     "--socket-timeout", "15",
        #     "--retries", "3",
        #     "--fragment-retries", "3",
        #     "--retry-sleep", "3",
        #     "--no-warnings",
        #     "--no-continue",
        #     "--sleep-requests", "3",
        #     "--max-sleep-interval", "6",
        # ]

        # Xử lý phụ đề (chỉ khi check "Tải MP3" hoặc có yêu cầu cụ thể)
        if self.sub_mode != "":
            if self.sub_mode == "1":
                cmd += ["--write-subs", "--sub-langs", self.sub_lang]
                # self.message.emit(
                #     f"🔤 Tải phụ đề chính thức cho ngôn ngữ: {lang_display}")
            elif self.sub_mode == "2":
                cmd += ["--write-auto-subs", "--sub-langs", self.sub_lang]
                # self.message.emit(
                #     f"🤖 Tải phụ đề tự động cho ngôn ngữ: {lang_display}")

            # Thêm các tùy chọn để đảm bảo tải được phụ đề
            cmd += [
                "--ignore-errors",           # Bỏ qua lỗi nếu một ngôn ngữ không có
                "--no-warnings",            # Không hiển thị cảnh báo
                "--sub-format", "srt/best",  # Ưu tiên định dạng SRT
            ]

        cmd += ["--convert-subs", "srt"]

        # Tải thumbnail nếu được yêu cầu
        if self.include_thumb:
            cmd.append("--write-thumbnail")

        # print(cmd)
        return cmd