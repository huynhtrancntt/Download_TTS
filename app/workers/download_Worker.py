from PySide6.QtCore import QThread, Signal, QTime
import sys
import os
import re
import subprocess
import shutil
import tempfile
import stat
from app.ui_setting import resource_path


class DownloadVideo(QThread):
    message_signal = Signal(str, str)
    progress_signal = Signal(int)
    finished_signal = Signal(str)
    error_signal = Signal(str)
    stop_flag = False

    def __init__(self, url, video_index,
                 total_urls, worker_id,
                 video_mode, audio_only,
                 sub_mode, sub_lang, sub_lang_name, include_thumb,
                 subtitle_only, custom_folder_name=""):
        super().__init__()
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

        # Tạo thư mục tạm cho download
        self.temp_dir = tempfile.mkdtemp(prefix="yt_download_")
        self.final_dir = custom_folder_name

        # print(self.url)
        # print(f" video_mode {self.video_mode}")
        # print(f" audio_only {self.audio_only}")
        # print(f" sub_mode {self.sub_mode}")
        # print(f" sub_lang {self.sub_lang}")
        # print(f" sub_lang_name {self.sub_lang_name}")
        # print(f" subtitle_only {self.subtitle_only}")
        # print(f" custom_folder_name {self.custom_folder_name}")
        # print(f" temp_dir {self.temp_dir}")

    def run(self):
        try:
            message_thread = f"[Thread {self.worker_id}] ({self.video_index}/{self.total_urls}) "
            if self.stop_flag:
                self.message_signal.emit(
                    f"{message_thread} ⏹ Đã dừng trước khi bắt đầu.", "")
                self._cleanup_temp()
                self.finished_signal.emit(f"stop")
                return

            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW

            self.message_signal.emit(
                f"{message_thread} 🔽 Bắt đầu tải: {self.url}", ""
            )

            # Lấy tiêu đề video
            ytdlp_path = "yt-dlp"

            if os.path.exists(self.ytdlp_path):
                ytdlp_path = self.ytdlp_path

            get_title_cmd = [ytdlp_path, "--encoding",
                             "utf-8", "--get-title", self.url]
            result = subprocess.run(get_title_cmd, capture_output=True,
                                    text=True, encoding="utf-8", creationflags=creation_flags)

            title = result.stdout.strip().replace("/", "-").replace("\\", "-")
            if not title:
                self.error_signal.emit(
                    f"{message_thread} Internet của bạn có vấn đề. vui lòng check lại!",)
                self._cleanup_temp()
                return
            self.message_signal.emit(
                f"{message_thread} 🎯 Tiêu đề: {title}", "")

            # Download vào thư mục tạm
            output_filename = f"{self.video_index:02d}.{title}.%(ext)s"
            if self.video_mode == "Video":
                output_filename = f"{self.video_index:02d}.{title}.%(ext)s"
            else:
                output_filename = f"playlist.{self.video_index:02d}.{title}.%(ext)s"

            # Đường dẫn tạm
            temp_output = os.path.join(self.temp_dir, output_filename)

            # Đường dẫn cuối cùng
            final_output = os.path.join(self.final_dir, output_filename)

            download_cmd = self._build_command(ytdlp_path, temp_output)

            self.process = subprocess.Popen(
                download_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                creationflags=creation_flags
            )

            for line in self.process.stdout:
                if self.stop_flag:
                    self.process.kill()
                    self.process.terminate()
                    self.message_signal.emit(
                        f"{message_thread} ⏹ Đã dừng tải video.", "")
                    self._cleanup_temp()
                    self.finished_signal.emit(f"stop")
                    return

                if line.strip():
                    self.message_signal.emit(
                        f"{message_thread} {line.strip()}", "")
                    match = re.search(r"\[download\]\s+(\d{1,3}\.\d{1,2})%", line)
                    if match:
                        percent = float(match.group(1))
                        self.progress_signal.emit(int(percent))

            self.process.wait()

            # Kiểm tra xem download có thành công không
            if self.process.returncode != 0:
                self.error_signal.emit(
                    f"{message_thread} ❌ Lỗi khi tải video!")
                self._cleanup_temp()
                return

            self.progress_signal.emit(95)

            # Tìm file đã download trong thư mục tạm
            downloaded_files = self._find_downloaded_files()
            if not downloaded_files:
                self.error_signal.emit(
                    f"{message_thread} ❌ Hiện tại không có file nào được download!"),
                self._cleanup_temp()
                self.finished_signal.emit(f"error_no_file")
            else:
                # Copy file từ thư mục tạm ra thư mục cuối cùng
                self.message_signal.emit(
                    f"{message_thread} 📁 Đang copy file ra thư mục cuối cùng...", "")

                success = self._copy_files_to_final(downloaded_files, title)
                if success:
                    # Tìm tên file chính để hiển thị
                    main_file = self._find_main_file(downloaded_files)
                    if main_file:
                        self.message_signal.emit(
                            f"{message_thread} ✅ Hoàn thành download và copy!", "")
                    else:
                        self.message_signal.emit(
                            f"{message_thread} ✅ Hoàn thành download!", "")

                    # Dọn dẹp thư mục tạm
                    self._cleanup_temp()
                    self.finished_signal.emit(f"success")
                else:
                    self.error_signal.emit(
                        f"{message_thread} ❌ Lỗi khi copy file!")
                    self._cleanup_temp()
                    self.finished_signal.emit(f"error_copy_file")
        finally:
            # Always attempt to remove temp dir
            self._cleanup_temp()

    def _find_downloaded_files(self):
        """Tìm các file đã download trong thư mục tạm"""
        files = []
        try:
            for item in os.listdir(self.temp_dir):
                item_path = os.path.join(self.temp_dir, item)
                if os.path.isfile(item_path):
                    files.append(item_path)
        except Exception as e:
            print(f"Error finding downloaded files: {e}")
        return files

    def _copy_files_to_final(self, temp_files, title):
        """Copy file từ thư mục tạm ra thư mục cuối cùng"""
        try:
            # Đảm bảo thư mục đích tồn tại
            os.makedirs(self.final_dir, exist_ok=True)

            copied_files = []
            for temp_file in temp_files:
                filename = os.path.basename(temp_file)
                final_file = os.path.join(self.final_dir, filename)
                # print(f"filename: {filename}")
                # Kiểm tra xem có nên copy file này hay không dựa trên chế độ download
                # if not self._should_copy_file(filename):
                #     continue

                # Xử lý từng loại file cụ thể
                if self._is_video_file(filename):
                    # File video - dùng ffmpeg để copy với metadata
                    success = self._copy_video_file(temp_file, final_file)
                    if success:
                        copied_files.append(f"🎬 Video: {filename}")
                elif self._is_audio_file(filename):
                    # File audio (mp3, wav, etc.) - dùng ffmpeg để copy
                    success = self._copy_audio_file(temp_file, final_file)
                    if success:
                        copied_files.append(f"🎵 Audio: {filename}")
                elif self._is_subtitle_file(filename):
                    # File phụ đề - copy trực tiếp
                    success = self._copy_subtitle_file(temp_file, final_file)
                    if success:
                        copied_files.append(f"📝 Phụ đề: {filename}")
                elif self._is_thumbnail_file(filename):
                    # File thumbnail - copy trực tiếp
                    success = self._copy_thumbnail_file(temp_file, final_file)
                    if success:
                        copied_files.append(f"🖼️ Thumbnail: {filename}")
                else:
                    # File khác - copy trực tiếp
                    success = self._copy_other_file(temp_file, final_file)
                    if success:
                        copied_files.append(f"📄 File: {filename}")

            # Thông báo các file đã copy thành công
            if copied_files:
                self.message_signal.emit(
                    f"[Thread {self.worker_id}] ✅ Đã copy thành công:\n" + "\n".join(copied_files), "")

            return True

        except Exception as e:
            print(f"Error copying files: {e}")
            return False

    def _should_copy_file(self, filename):
        """Kiểm tra xem có nên copy file này hay không dựa trên chế độ download"""
        # Nếu chỉ tải phụ đề, chỉ copy file phụ đề
        if self.subtitle_only:
            return self._is_subtitle_file(filename)

        # Nếu check "Tải MP3": copy video + audio + thumbnail
        if self.audio_only:
            return (self._is_video_file(filename) or
                    self._is_audio_file(filename) or
                    self._is_thumbnail_file(filename))

        # Nếu chỉ check "Bao gồm ảnh": copy video + thumbnail
        if self.include_thumb and not self.audio_only:
            return self._is_video_file(filename) or self._is_thumbnail_file(filename)

        # Mặc định: chỉ copy video MP4
        return self._is_video_file(filename)

    def _copy_video_file(self, temp_file, final_file):
        """Copy file video với ffmpeg"""
        try:
            if os.path.exists(self.ffmpeg_path):
                # Dùng ffmpeg để copy với metadata
                ffmpeg_cmd = [
                    self.ffmpeg_path,
                    "-i", temp_file,
                    "-c", "copy",  # Copy không re-encode
                    "-y",  # Ghi đè file nếu có
                    final_file
                ]

                creation_flags = 0
                if sys.platform == "win32":
                    creation_flags = subprocess.CREATE_NO_WINDOW

                result = subprocess.run(
                    ffmpeg_cmd,
                    capture_output=True,
                    creationflags=creation_flags
                )

                if result.returncode == 0:
                    return True

            # Fallback: copy thường nếu ffmpeg thất bại hoặc không có
            shutil.copy2(temp_file, final_file)
            return True

        except Exception as e:
            print(f"Error copying video file: {e}")
            return False

    def _copy_audio_file(self, temp_file, final_file):
        """Copy file audio với ffmpeg"""
        try:
            if os.path.exists(self.ffmpeg_path):
                # Dùng ffmpeg để copy với metadata
                ffmpeg_cmd = [
                    self.ffmpeg_path,
                    "-i", temp_file,
                    "-c", "copy",  # Copy không re-encode
                    "-y",  # Ghi đè file nếu có
                    final_file
                ]

                creation_flags = 0
                if sys.platform == "win32":
                    creation_flags = subprocess.CREATE_NO_WINDOW

                result = subprocess.run(
                    ffmpeg_cmd,
                    capture_output=True,
                    creationflags=creation_flags
                )

                if result.returncode == 0:
                    return True

            # Fallback: copy thường nếu ffmpeg thất bại hoặc không có
            shutil.copy2(temp_file, final_file)
            return True

        except Exception as e:
            print(f"Error copying audio file: {e}")
            return False

    def _copy_subtitle_file(self, temp_file, final_file):
        """Copy file phụ đề"""
        try:
            shutil.copy2(temp_file, final_file)
            return True
        except Exception as e:
            print(f"Error copying subtitle file: {e}")
            return False

    def _copy_thumbnail_file(self, temp_file, final_file):
        """Copy file thumbnail"""
        try:
            shutil.copy2(temp_file, final_file)
            return True
        except Exception as e:
            print(f"Error copying thumbnail file: {e}")
            return False

    def _copy_other_file(self, temp_file, final_file):
        """Copy file khác"""
        try:
            shutil.copy2(temp_file, final_file)
            return True
        except Exception as e:
            print(f"Error copying other file: {e}")
            return False

    def _find_main_file(self, temp_files):
        """Tìm file chính (video hoặc audio) trong danh sách file tạm"""
        for temp_file in temp_files:
            filename = os.path.basename(temp_file)
            if self._is_video_file(filename) or self._is_audio_file(filename):
                return filename
        return None

    def _is_video_file(self, filename):
        """Kiểm tra xem file có phải là video file không"""
        video_extensions = ['.mp4', '.mkv', '.avi',
                            '.mov', '.wmv', '.flv', '.webm', '.m4v']
        return any(filename.lower().endswith(ext) for ext in video_extensions)

    def _is_audio_file(self, filename):
        """Kiểm tra xem file có phải là audio file không"""
        audio_extensions = ['.mp3', '.wav', '.aac',
                            '.ogg', '.m4a', '.flac', '.wma']
        return any(filename.lower().endswith(ext) for ext in audio_extensions)

    def _is_subtitle_file(self, filename):
        """Kiểm tra xem file có phải là subtitle file không"""
        subtitle_extensions = ['.srt', '.vtt', '.ass', '.ssa', '.sub', '.idx']
        return any(filename.lower().endswith(ext) for ext in subtitle_extensions)

    def _is_thumbnail_file(self, filename):
        """Kiểm tra xem file có phải là thumbnail file không"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif']
        return any(filename.lower().endswith(ext) for ext in image_extensions)

    def _cleanup_temp(self):
        """Dọn dẹp thư mục tạm"""
        try:
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                def _on_rm_error(func, path, exc_info):
                    try:
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                    except Exception:
                        pass
                shutil.rmtree(self.temp_dir, onerror=_on_rm_error)
        except Exception as e:
            print(f"Error cleaning up temp directory: {e}")

    def _build_command(self, ytdlp_path, output):
        """Xây dựng lệnh yt-dlp"""
        cmd = [ytdlp_path]
        cmd += ["--encoding", "utf-8"]
        cmd += [self.url, "--progress"]
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

    # def _update_progress_from_line(self, line):
    #     """Cập nhật progress từ output line"""
    #     if "%" in line:
    #         try:
    #             percent_str = line.split(
    #                 "%", 1)[0].split()[-1].replace(".", "").strip()
    #             percent = int(percent_str)
    #             if 0 <= percent <= 100:
    #                 self.progress_signal.emit(percent)
    #         except:
    #             pass
