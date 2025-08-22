from PySide6.QtCore import Signal, QRunnable, QObject
import sys
import os
import re
import subprocess
import shutil
import tempfile
import stat
import time
import random
from app.ui_setting import resource_path

# Compile once for efficiency
PROGRESS_RE = re.compile(r"\[download\]\s+(\d{1,3}(?:\.\d{1,2})?)%")

class DownloadSignals(QObject):
    message_signal = Signal(str, str)
    progress_signal = Signal(int)
    finished_signal = Signal(str)
    error_signal = Signal(str)


class DownloadRunnable(QRunnable):
    """QRunnable-based worker for QThreadPool."""

    def __init__(self, url, video_index,
                 total_urls, worker_id,
                 video_mode, audio_only,
                 sub_mode, sub_lang, sub_lang_name, include_thumb,
                 subtitle_only, custom_folder_name=""):
        super().__init__()
        self.signals = DownloadSignals()
        self.url = url
        self.video_index = video_index
        self.total_urls = total_urls
        self.worker_id = worker_id
        self.video_mode = video_mode
        self.audio_only = audio_only
        self.sub_mode = sub_mode
        self.sub_lang = sub_lang
        self.sub_lang_name = sub_lang_name
        self.include_thumb = include_thumb
        self.subtitle_only = subtitle_only
        self.custom_folder_name = custom_folder_name
        self.ffmpeg_path = resource_path(os.path.join("data", "ffmpeg.exe"))
        self.ytdlp_path = resource_path(os.path.join("data", "yt-dlp.exe"))
        self.stop_flag = False
        self.temp_dir = ""
        self.final_dir = custom_folder_name
        self.process = None

    def run(self):
        message_thread = f"[Thread {self.worker_id}] ({self.video_index}/{self.total_urls}) "
        try:
            if self.stop_flag:
                self.signals.message_signal.emit(
                    f"{message_thread} ⏹ Đã dừng trước khi bắt đầu.", "")
                self._cleanup_temp()
                self.signals.finished_signal.emit("stop")
                return

            # Kiểm tra đường dẫn yt-dlp
            if not os.path.exists(self.ytdlp_path):
                self.signals.error_signal.emit(
                    f"{message_thread} ❌ Không tìm thấy yt-dlp tại: {self.ytdlp_path}")
                self.signals.finished_signal.emit("error_no_ytdlp")
                return

            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW | getattr(
                    subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

            self.signals.message_signal.emit(
                f"{message_thread} 🔽 Bắt đầu tải: {self.url}", ""
            )

            output_template = f"video_{self.video_index:02d}_%(title)s.%(ext)s"
            if self.video_mode != "Video":
                output_template = f"playlist_{self.video_index:02d}_%(title)s.%(ext)s"

            self.temp_dir = tempfile.mkdtemp(prefix="yt_download_")
            temp_output = os.path.join(self.temp_dir, output_template)
            # Sử dụng đường dẫn đầy đủ đến yt-dlp.exe
            ytdlp_path = self.ytdlp_path if os.path.exists(self.ytdlp_path) else "yt-dlp"
            download_cmd = self._build_command(ytdlp_path, temp_output)
            
            # Kiểm tra lệnh download
            if not download_cmd:
                self.signals.error_signal.emit(
                    f"{message_thread} ❌ Lỗi khi tạo lệnh download")
                self._cleanup_temp()
                self.signals.finished_signal.emit("error_cmd")
                return
                
            base_delay = random.randint(10, 20)
            thread_delay = (self.worker_id - 1) * 2
            total_delay = base_delay + thread_delay
            self.signals.message_signal.emit(f"{message_thread} ⏳ Chờ {total_delay}s trước khi tải video","")
            time.sleep(total_delay)

            self.process = subprocess.Popen(
                download_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                encoding="utf-8",
                creationflags=creation_flags
            )


            for line in self.process.stdout:
                if self.stop_flag:
                    self.process.kill()
                    self.process.terminate()
                    self.signals.message_signal.emit(
                        f"{message_thread} ⏹ Đã dừng tải video.", "")
                    self._cleanup_temp()
                    self.signals.finished_signal.emit("stop")
                    return

                if line.strip():
                
                    self.signals.message_signal.emit(
                            f"{message_thread} {line.strip()}", "")
                
                    match = PROGRESS_RE.search(line)
                    if match:
                        percent = int(float(match.group(1)))
                        self.signals.progress_signal.emit(percent)


            self.process.wait()
            try:
                if self.process.stdout:
                    self.process.stdout.close()
            except Exception:
                pass

            if self.process.returncode != 0:
                self.signals.error_signal.emit(
                    f"{message_thread} ❌ Lỗi khi tải video! (mã {self.process.returncode}). Bỏ qua và tiếp tục.")
                self._cleanup_temp()
                self.signals.finished_signal.emit("error")
                return

            self.signals.progress_signal.emit(85)

            downloaded_files = self._find_downloaded_files()
            if not downloaded_files:
                self.signals.error_signal.emit(
                    f"{message_thread} ❌ Không có file nào được download. Bỏ qua và tiếp tục.")
                self.signals.finished_signal.emit("error_no_file")
            else:
                self.signals.message_signal.emit(
                    f"{message_thread} 📁 Đang copy file ra thư mục cuối cùng...", "")
                # Copy từng file từ thư mục tạm vào final_dir
                success = self._copy_files_to_final(downloaded_files)
                if success:
                    main_file = self._find_main_file(downloaded_files)
                    if main_file:
                        self.signals.message_signal.emit(
                            f"{message_thread} ✅ Hoàn thành download và copy!", "")
                    else:
                        self.signals.message_signal.emit(
                            f"{message_thread} ✅ Hoàn thành download!", "")
                    self.signals.finished_signal.emit("success")
                else:
                    self.signals.error_signal.emit(
                        f"{message_thread} ❌ Lỗi khi copy file! Bỏ qua và tiếp tục.")
                    self.signals.finished_signal.emit("error_copy_file")
            self._cleanup_temp()
        finally:
            self._cleanup_temp()

    # Reuse helper methods from DownloadVideo for runnable
    def _find_downloaded_files(self):
        try:
            return [
                os.path.join(self.temp_dir, item)
                for item in os.listdir(self.temp_dir)
                if os.path.isfile(os.path.join(self.temp_dir, item))
            ]
        except Exception as e:
            print(f"Error finding downloaded files: {e}")
            return []


    def _copy_files_to_final(self, temp_files):
        try:
            # Tạo thư mục đích nếu chưa tồn tại
            if not self.final_dir:
                self.final_dir = "output"  # Thư mục mặc định
            
            os.makedirs(self.final_dir, exist_ok=True)
            
            copied_count = 0
            total_files = len(temp_files)
            
            print(f"Bắt đầu copy {total_files} file từ thư mục tạm: {self.temp_dir}")
            print(f"Thư mục đích: {self.final_dir}")
            
            for i, temp_file in enumerate(temp_files, 1):
                try:
                    filename = os.path.basename(temp_file)
                    final_file = os.path.join(self.final_dir, filename)
                    
                    print(f"[{i}/{total_files}] Đang copy: {filename}")
                    
                    # Kiểm tra file nguồn có tồn tại không
                    if not os.path.exists(temp_file):
                        print(f"  ❌ Source file not found: {temp_file}")
                        continue
                    
                    # Kiểm tra file đích đã tồn tại chưa
                    if os.path.exists(final_file):
                        print(f"  ⚠️  File đích đã tồn tại, sẽ ghi đè: {filename}")
                    
                    if self._is_video_file(filename):
                        if self._copy_video_file(temp_file, final_file):
                            copied_count += 1
                            print(f"  ✅ Đã copy video file: {filename}")
                        else:
                            print(f"  ❌ Failed to copy video file: {filename}")
                    elif self._is_audio_file(filename):
                        if self._copy_audio_file(temp_file, final_file):
                            copied_count += 1
                            print(f"  ✅ Đã copy audio file: {filename}")
                        else:
                            print(f"  ❌ Failed to copy audio file: {filename}")
                    elif self._is_subtitle_file(filename):
                        if self._copy_subtitle_file(temp_file, final_file):
                            copied_count += 1
                            print(f"  ✅ Đã copy subtitle file: {filename}")
                        else:
                            print(f"  ❌ Failed to copy subtitle file: {filename}")
                    elif self._is_thumbnail_file(filename):
                        if self._copy_thumbnail_file(temp_file, final_file):
                            copied_count += 1
                            print(f"  ✅ Đã copy thumbnail file: {filename}")
                        else:
                            print(f"  ❌ Failed to copy thumbnail file: {filename}")
                    else:
                        if self._copy_other_file(temp_file, final_file):
                            copied_count += 1
                            print(f"  ✅ Đã copy other file: {filename}")
                        else:
                            print(f"  ❌ Failed to copy other file: {filename}")
                            
                except Exception as e:
                    print(f"  ❌ Error copying file {temp_file}: {e}")
                    continue
            
            print(f"Hoàn thành copy: {copied_count}/{total_files} file thành công")
            
            # Trả về True nếu có ít nhất 1 file được copy thành công
            return copied_count > 0
            
        except Exception as e:
            print(f"Error in _copy_files_to_final: {e}")
            return False

    def _find_main_file(self, temp_files):
        for temp_file in temp_files:
            filename = os.path.basename(temp_file)
            if self._is_video_file(filename) or self._is_audio_file(filename):
                return filename
        return None

    def _is_video_file(self, filename):
        video_extensions = ['.mp4', '.mkv', '.avi',
                            '.mov', '.wmv', '.flv', '.webm', '.m4v']
        return any(filename.lower().endswith(ext) for ext in video_extensions)

    def _is_audio_file(self, filename):
        audio_extensions = ['.mp3', '.wav', '.aac',
                            '.ogg', '.m4a', '.flac', '.wma']
        return any(filename.lower().endswith(ext) for ext in audio_extensions)

    def _is_subtitle_file(self, filename):
        subtitle_extensions = ['.srt', '.vtt', '.ass', '.ssa', '.sub', '.idx']
        return any(filename.lower().endswith(ext) for ext in subtitle_extensions)

    def _is_thumbnail_file(self, filename):
        image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif']
        return any(filename.lower().endswith(ext) for ext in image_extensions)

    def _copy_video_file(self, temp_file, final_file):
        try:
            if os.path.exists(self.ffmpeg_path):
                creation_flags = 0
                if sys.platform == "win32":
                    creation_flags = subprocess.CREATE_NO_WINDOW
                result = subprocess.run([self.ffmpeg_path, "-i", temp_file, "-c", "copy",
                                        "-y", final_file], capture_output=True, creationflags=creation_flags)
                if result.returncode == 0:
                    return True
            shutil.copy2(temp_file, final_file)
            return True
        except Exception as e:
            print(f"Error copying video file (runnable): {e}")
            return False

    def _copy_audio_file(self, temp_file, final_file):
        try:
            if os.path.exists(self.ffmpeg_path):
                creation_flags = 0
                if sys.platform == "win32":
                    creation_flags = subprocess.CREATE_NO_WINDOW
                result = subprocess.run([self.ffmpeg_path, "-i", temp_file, "-c", "copy",
                                        "-y", final_file], capture_output=True, creationflags=creation_flags)
                if result.returncode == 0:
                    return True
            shutil.copy2(temp_file, final_file)
            return True
        except Exception as e:
            print(f"Error copying audio file (runnable): {e}")
            return False

    def _copy_subtitle_file(self, temp_file, final_file):
        try:
            shutil.copy2(temp_file, final_file)
            return True
        except Exception as e:
            print(f"Error copying subtitle file (runnable): {e}")
            return False

    def _copy_thumbnail_file(self, temp_file, final_file):
        try:
            shutil.copy2(temp_file, final_file)
            return True
        except Exception as e:
            print(f"Error copying thumbnail file (runnable): {e}")
            return False

    def _copy_other_file(self, temp_file, final_file):
        try:
            shutil.copy2(temp_file, final_file)
            return True
        except Exception as e:
            print(f"Error copying other file (runnable): {e}")
            return False

    def _cleanup_temp(self):
        try:
            if hasattr(self, 'temp_dir') and self.temp_dir and os.path.exists(self.temp_dir):
                def _on_rm_error(func, path, exc_info):
                    try:
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                    except Exception:
                        pass
                shutil.rmtree(self.temp_dir, onerror=_on_rm_error)
        except Exception as e:
            print(f"Error cleaning up temp directory (runnable): {e}")



    
 

    # Remove duplicate legacy helpers below (kept single implementations above)
    def _build_command(self, ytdlp_path, output):
        """Xây dựng lệnh yt-dlp"""
        cmd = [ytdlp_path]
        cmd += ["--encoding", "utf-8"]
        cmd += [self.url, "--progress", "--newline"]
        # Thêm đường dẫn ffmpeg nếu tồn tại
        if os.path.exists(self.ffmpeg_path):
            cmd += ["--ffmpeg-location", self.ffmpeg_path]

        # Xử lý từng chế độ download cụ thể
        if self.subtitle_only:
            # Chỉ tải phụ đề
            cmd.append("--skip-download")
            # Không emit signal ở đây vì method này không có access đến signals
        else:
            # Tải cả video MP4 và audio MP3
            cmd += ["-f", "bv*+ba/b", "--merge-output-format", "mp4"]

        if self.audio_only:
            cmd += ["--extract-audio", "--audio-format", "mp3", "--keep-video"]
            # Không emit signal ở đây vì method này không có access đến signals

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