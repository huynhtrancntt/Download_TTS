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

            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW | getattr(
                    subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

            self.signals.message_signal.emit(
                f"{message_thread} 🔽 Bắt đầu tải: {self.url}", ""
            )
            delay = random.uniform(2, 15)  # số thực, ví dụ 7.38 giây
            print(f"delay {delay}s")
            time.sleep(delay)
            print(f"xong delay {delay}s")
            ytdlp_path = "yt-dlp"
            if os.path.exists(self.ytdlp_path):
                ytdlp_path = self.ytdlp_path
            get_title_cmd = [ytdlp_path, "--encoding",
                             "utf-8", "--get-title", self.url , "--no-warnings","--no-check-certificate"]
           
            result = subprocess.run(
                    get_title_cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    creationflags=creation_flags,
                )
            # print(result)

            title = result.stdout.strip().replace("/", "-").replace("\\", "-")
            if title == "":
                self.signals.message_signal.emit(
                    f"{message_thread} ❌ Không tải được video. Bỏ qua và tiếp tục.", "")
                self.signals.finished_signal.emit("error")
                return
            # if not title:
            #     self.signals.error_signal.emit(
            #         f"{message_thread} Internet của bạn có vấn đề. vui lòng check lại!",)
            #     self._cleanup_temp()
            #     self.signals.finished_signal.emit("error")
            #     return
            self.signals.message_signal.emit(
                        f"{message_thread} Đang tải video {title}", "")
                        
            output_filename = f"{self.video_index:02d}.{title}.%(ext)s"
            if self.video_mode != "Video":
                output_filename = f"playlist.{self.video_index:02d}.{title}.%(ext)s"

            self.temp_dir = tempfile.mkdtemp(prefix="yt_download_")
            temp_output = os.path.join(self.temp_dir, output_filename)
            # final_output = os.path.join(self.final_dir, output_filename)

            download_cmd = self._build_command(ytdlp_path, temp_output)
            delay = random.uniform(4, 10)  # số thực, ví dụ 7.38 giây
            print(f"delay {delay}s")
            time.sleep(delay)
            print(f"xong delay {delay}s")

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
                success = self._copy_files_to_final(downloaded_files, title)
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


    def _copy_files_to_final(self, temp_files, title):
        try:
            os.makedirs(self.final_dir, exist_ok=True)
            for temp_file in temp_files:
                filename = os.path.basename(temp_file)
                final_file = os.path.join(self.final_dir, filename)
                if self._is_video_file(filename):
                    if not self._copy_video_file(temp_file, final_file):
                        return False
                elif self._is_audio_file(filename):
                    if not self._copy_audio_file(temp_file, final_file):
                        return False
                elif self._is_subtitle_file(filename):
                    if not self._copy_subtitle_file(temp_file, final_file):
                        return False
                elif self._is_thumbnail_file(filename):
                    if not self._copy_thumbnail_file(temp_file, final_file):
                        return False
                else:
                    if not self._copy_other_file(temp_file, final_file):
                        return False
            return True
        except Exception as e:
            print(f"Error copying files (runnable): {e}")
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