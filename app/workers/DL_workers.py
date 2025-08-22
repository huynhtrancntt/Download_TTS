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

import shutil   
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
    progress = Signal(int, int)
    progress_single = Signal(int)       # completed, total
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
        self.group_max_items: int = 10      # NEW: tối đa bao nhiêu ý/nhóm
        self.group_sep: str = " | "
        # Trạng thái worker
        self.stop_flag: bool = False
        self.tmpdir: Optional[str] = None
        self.video_mode: str = "Video"
        self.ffmpeg_path: str = resource_path(
            os.path.join("data", "ffmpeg.exe"))
        self.ytdlp_path: str = resource_path(
            os.path.join("data", "yt-dlp.exe"))
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
                self.error.emit("❌ Chưa có url để tải.")
                return
            chunks = [u.strip() for u in self.text.splitlines() if u.strip()]
            print(chunks)
            # chunks = [chunk for (chunk, _len_) in grouped]
            total = len(chunks)
            if total == 0:
                self.error.emit("❌ Không thể tải video vì không có url.")
                return

            # self.tmpdir = Path(tempfile.mkdtemp(prefix=AppConfig.TEMP_PREFIX))

            self.status.emit(
                f"🚀 Bắt đầu tải {total} url bằng {self.workers} luồng...")

            # Khởi tạo biến theo dõi tiến trình
            # Dict lưu kết quả đã hoàn thành {index: (path, duration)}
            completed = {}
            next_index = 1  # Index tiếp theo cần emit
            emitted = 0     # Số đoạn đã emit

            def job(index1: int, content: str) -> tuple:
                self.temp_dir = ""
                title = ""
                
                # Lấy thông tin thread hiện tại
                import threading
                current_thread = threading.current_thread()
                thread_name = current_thread.name
                thread_id = current_thread.ident
                
                self.status.emit(f"🧵 Thread {thread_name} (ID: {thread_id}) bắt đầu xử lý URL {index1}")
                print(f"🧵 Thread {thread_name} (ID: {thread_id}) bắt đầu xử lý URL {index1}")
                
                try:
                    if not os.path.exists(self.ytdlp_path):
                        self.ytdlp_path = "yt-dlp"

                    # output_template = f"video_{index1:02d}_%(title)s.%(ext)s" if self.video_mode else f"playlist_{i}_%(autonumber)03d_%(title)s.%(ext)s"
                    output_template = f"video_{index1:02d}_%(title)s.%(ext)s"
                    if self.video_mode != "Video":
                        output_template = f"playlist_{index1:02d}_%(title)s.%(ext)s"
                    
                    self.temp_dir = tempfile.mkdtemp(prefix="yt_download_")
                    self.temp_dir = os.path.join(self.temp_dir, str(uuid.uuid4()))
                    os.makedirs(self.temp_dir, exist_ok=True)
                    temp_output = os.path.join(self.temp_dir, output_template)
                    
                    download_cmd = self._build_command(
                        self.ytdlp_path, temp_output, content)

                    # Thời gian chờ cơ bản: 5-20s
                    base_delay = random.randint(5, 20)
                    
                    # Nếu chạy thêm thread thì + thêm 2s cho mỗi thread
                    # Thread 1: +2s, Thread 2: +4s, Thread 3: +6s, v.v.
                    thread_delay = (self.workers - 1) * 2
                    total_delay = base_delay + thread_delay
                    self.status.emit(f"⏳ Chờ {total_delay}s trước khi tải video {index1}...")
                    time.sleep(total_delay)

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
                    
                    # Kiểm tra process có khởi động thành công không
                    if self.process.poll() is not None:
                        raise Exception("Process yt-dlp không thể khởi động")
                    
                    self.status.emit(f"Đã bắt đầu tải video: {title}") 
                    
                    # Đọc output và theo dõi progress với timeout
                    stdout_lines = []
                    start_time = time.time()
                    timeout_seconds = 300  # 5 phút timeout
                    
                    try:
                        for line in self.process.stdout:
                            if self.stop_flag:
                                self.process.kill()
                                self.process.terminate()
                                self.status.emit(
                                    "⏹ Đã dừng theo yêu cầu người dùng.")
                                return

                            # Kiểm tra process còn sống không
                            if self.process.poll() is not None:
                                # Process đã kết thúc
                                break

                            # Kiểm tra timeout
                            if time.time() - start_time > timeout_seconds:
                                self.process.kill()
                                self.process.terminate()
                                raise Exception(f"Timeout sau {timeout_seconds}s - URL có thể bị treo")

                            if line.strip():
                                stdout_lines.append(line.strip())
                                self.status.emit(line.strip()) 
                                match = PROGRESS_RE.search(line)
                                if match:
                                    percent = int(float(match.group(1)))
                                    if percent < 90:
                                        self.progress_single.emit(int(percent))
                    
                        # Chờ process hoàn thành với timeout
                        return_code = self.process.wait(timeout=timeout_seconds)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        self.process.terminate()
                        raise Exception(f"Process timeout sau {timeout_seconds}s - URL có thể bị treo")
                    
                    if return_code != 0:
                        # Tìm thông tin lỗi trong output
                        error_lines = [line for line in stdout_lines if 'ERROR:' in line or 'error:' in line]
                        error_info = ""
                        if error_lines:
                            error_info = f" - Errors: {'; '.join(error_lines[-3:])}"  # Lấy 3 dòng lỗi cuối cùng
                        
                        raise Exception(f"yt-dlp download failed with return code: {return_code}{error_info}")
                    
                    self.status.emit(f"✅ Xong tải video: {title}") 
                    
                    # Copy file vào thư mục Videos
                    dst = "Videos"
                    os.makedirs(dst, exist_ok=True)
                    
                    # Tìm file đã tải trong temp_dir
                    downloaded_files = [f for f in os.listdir(self.temp_dir) if os.path.isfile(os.path.join(self.temp_dir, f))]
                    if downloaded_files:
                        # Copy từng file vào thư mục Videos
                        for file_name in downloaded_files:
                            src_file = os.path.join(self.temp_dir, file_name)
                            dst_file = os.path.join(dst, file_name)
                            shutil.copy2(src_file, dst_file)
                    
                    # Dọn dẹp temp_dir
                    # if os.path.exists(self.temp_dir):
                    #     shutil.rmtree(self.temp_dir)
                    
                    print(f"Đã copy file vào {dst}")
                    
                    # Log hoàn thành
                    self.status.emit(f"🧵 Thread {thread_name} (ID: {thread_id}) hoàn thành URL {index1}")
                    print(f"🧵 Thread {thread_name} (ID: {thread_id}) hoàn thành URL {index1}")
                    
                    return (index1, content, title, dst)
                    
                except Exception as e:
                    # Log lỗi với thông tin thread
                    error_msg = f"Lỗi xử lý url {index1}: {str(e)}"
                    self.status.emit(f"❌ Thread {thread_name} (ID: {thread_id}) - {error_msg}")
                    print(f"❌ Thread {thread_name} (ID: {thread_id}) - {error_msg}")
                    raise Exception(error_msg)

            # Xử lý đa luồng theo batch để tránh treo và rate-limit
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                # Giảm batch size để tránh treo
                batch_size = min(50, total)  # Tối đa 50 URLs mỗi batch
                for batch_start in range(0, total, batch_size):
                    if self.stop_flag:
                        self.status.emit("⏹ Đã dừng theo yêu cầu người dùng.")
                        break

                    batch_end = min(total, batch_start + batch_size)
                    batch_num = (batch_start // batch_size) + 1
                    
                    self.status.emit(f"📦 Bắt đầu batch {batch_num}: URLs {batch_start + 1}-{batch_end} (sử dụng {self.workers} threads)")
                    print(f"📦 Bắt đầu batch {batch_num}: URLs {batch_start + 1}-{batch_end} (sử dụng {self.workers} threads)")
                    
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

                    # Log hoàn thành batch
                    self.status.emit(f"✅ Hoàn thành batch {batch_num}: URLs {batch_start + 1}-{batch_end}")
                    print(f"✅ Hoàn thành batch {batch_num}: URLs {batch_start + 1}-{batch_end}")

                    # Nếu còn batch kế tiếp, nghỉ ngẫu nhiên 500-700s như yêu cầu
                    if batch_end < total:
                        delay_sec = random.randint(10, 20)
                        self.status.emit(f"⏳ Tạm dừng {delay_sec}s trước khi chuyển sang batch tiếp theo...")
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
            # Log lỗi chi tiết
            import traceback
            error_trace = traceback.format_exc()
            print(f"❌ Lỗi nghiêm trọng trong worker: {str(e)}")
            print(f"Traceback: {error_trace}")
            
            # Dọn dẹp process nếu còn tồn tại
            if hasattr(self, 'process') and self.process:
                try:
                    self.process.kill()
                    self.process.terminate()
                except:
                    pass
            
            self.error.emit(f"❌ Lỗi nghiêm trọng: {str(e)}")

    # Remove duplicate legacy helpers below (kept single implementations above)

    def _build_command(self, ytdlp_path, output, url):
        """Xây dựng lệnh yt-dlp với retry và fallback options"""
        cmd = [ytdlp_path]
        cmd += ["--encoding", "utf-8"]
        cmd += [url, "--progress", "--newline"]
        
        # Thêm đường dẫn ffmpeg nếu tồn tại
        if os.path.exists(self.ffmpeg_path):
            cmd += ["--ffmpeg-location", self.ffmpeg_path]

        # Thêm các tùy chọn để xử lý lỗi HTTP 403 và format issues
        # cmd += [
        #     "--ignore-errors",              # Bỏ qua lỗi nhỏ
        #     "--no-warnings",    
        #     "--no-check-certificate",       # Bỏ qua kiểm tra SSL certificate
        #     "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",  # User agent giả
        # ]

        if self.subtitle_only:
            # Chỉ tải phụ đề
            cmd.append("--skip-download")
            self.message_signal.emit("📝 Chế độ: Chỉ tải phụ đề", "")
        else:
            # Tải cả video MP4 và audio MP3
            cmd += ["-f", "bv*+ba/b", "--merge-output-format", "mp4"]

        if self.audio_only:
            cmd += ["--extract-audio", "--audio-format", "mp3", "--keep-video"]
        cmd += ["-o", output]

        # Xử lý phụ đề (chỉ khi check "Tải MP3" hoặc có yêu cầu cụ thể)
        if self.sub_mode != "":
            if self.sub_mode == "1":
                cmd += ["--write-subs", "--sub-langs", self.sub_lang]
            elif self.sub_mode == "2":
                cmd += ["--write-auto-subs", "--sub-langs", self.sub_lang]

            # Thêm các tùy chọn để đảm bảo tải được phụ đề
            cmd += [
                "--sub-format", "srt/best",  # Ưu tiên định dạng SRT
            ]

        cmd += ["--convert-subs", "srt"]

        # Tải thumbnail nếu được yêu cầu
        if self.include_thumb:
            cmd.append("--write-thumbnail")

        return cmd
