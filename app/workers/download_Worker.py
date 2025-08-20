from PySide6.QtCore import Qt, Signal, QThread
import sys
import os
from datetime import datetime
import subprocess
from app.ui_setting import resource_path


class DownloadVideo(QThread):
    """Worker thread để xử lý download video"""
    message = Signal(str)
    progress_signal = Signal(int)
    finished = Signal(str)

    def __init__(self, urls, video_mode, audio_only, sub_mode, sub_lang, sub_lang_name, include_thumb, subtitle_only, custom_folder_name=""):
        super().__init__()
        self.urls = urls
        self.video_mode = video_mode
        self.audio_only = audio_only
        self.sub_mode = sub_mode
        self.sub_lang = sub_lang

        self.include_thumb = include_thumb
        self.subtitle_only = subtitle_only
        self.custom_folder_name = custom_folder_name.strip()
        self.stop_flag = False
        self.process = None
        self.ffmpeg_path = resource_path(os.path.join("data", "ffmpeg.exe"))
        self.ytdlp_path = resource_path(os.path.join("data", "yt-dlp.exe"))
        languages = [
            ("Tiếng Việt", "vi"),
            ("Tiếng Anh", "en"),
            ("Tiếng Nhật", "ja"),
            ("Tiếng Trung", "zh")
        ]
        self.sub_lang_name = next(
            (name for name, lang_code in languages if lang_code == self.sub_lang), None)

    def stop(self):
        """Dừng quá trình download"""
        self.stop_flag = True
        if self.process:
            self.process.terminate()
            self.message.emit("⏹ Dừng tải...")

    def run(self):
        """Chạy quá trình download"""
        try:
            download_folder = self._create_download_folder()
            download_folder = download_folder.replace('\\', '/')
            for i, url in enumerate(self.urls, 1):
                if self.stop_flag:
                    self.message.emit("⏹ Đã dừng tải.")
                    break

                self.message.emit(f"🔗 [{i}] Đang tải: {url}")

                if self._download_single_url(url, download_folder, i):
                    self.message.emit(f"✅ Hoàn thành link URL: {url}")
                else:
                    self.message.emit(f"❌ Lỗi khi tải link: {url}")

                self.progress_signal.emit(int(i / len(self.urls) * 100))

            self.finished.emit(f"📂 Video được lưu tại: {download_folder}")

        except Exception as e:
            self.message.emit(f"❌ Lỗi: {e}")

    def _create_download_folder(self):
        """Tạo thư mục download với cấu trúc đơn giản"""
        base_folder = "Video"
        os.makedirs(base_folder, exist_ok=True)

        if self.custom_folder_name:
            # Nếu có tên thư mục tùy chọn
            if os.path.isabs(self.custom_folder_name):
                # Đường dẫn đầy đủ
                date_folder = self.custom_folder_name
            else:
                # Tên thư mục - tạo trong thư mục Video
                date_folder = os.path.join(
                    base_folder, self.custom_folder_name)
        else:
            # Không có tên tùy chọn - tạo theo ngày
            date_str = datetime.now().strftime("%Y-%m-%d")
            date_folder = os.path.join(base_folder, date_str)

        # Tạo thư mục con với số thứ tự (01, 02, 03...)
        download_folder = self._create_numbered_subfolder(date_folder)

        os.makedirs(download_folder, exist_ok=True)
        return download_folder

    def _create_numbered_subfolder(self, date_folder):
        """Tạo thư mục con với số thứ tự (01, 02, 03...)"""
        if not os.path.exists(date_folder):
            os.makedirs(date_folder, exist_ok=True)

        # Tìm số thứ tự cao nhất trong thư mục ngày
        max_number = 0
        for item in os.listdir(date_folder):
            item_path = os.path.join(date_folder, item)
            if os.path.isdir(item_path) and item.isdigit():
                max_number = max(max_number, int(item))

        # Tạo thư mục con mới với số tiếp theo (format 2 chữ số)
        next_number = max_number + 1
        subfolder_name = f"{next_number:02d}"
        download_folder = os.path.join(date_folder, subfolder_name)

        return download_folder

    def _download_single_url(self, url, download_folder, index):
        """Download một URL đơn"""
        cmd = self._build_command(url, download_folder, index)
        print(cmd)
        # Thiết lập creation flags để ẩn console window trên Windows
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NO_WINDOW

        self.process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, creationflags=creation_flags
        )
        for line in self.process.stdout:
            if self.stop_flag:
                self.process.terminate()
                self.message.emit("⏹ Đang dừng...")
                break

            line = line.strip()
            # print(line)
            if line:
                self.message.emit(line)
                self._update_progress_from_line(line)

        self.process.wait()

        if self.process.returncode == 0:
            return True
        return False

    def _build_command(self, url, download_folder, index):
        """Xây dựng lệnh yt-dlp"""

        ytdlp_path = "yt-dlp"
        cmd = [ytdlp_path]
        if os.path.exists(self.ytdlp_path):
            cmd = [self.ytdlp_path]
        cmd += ["--encoding", "utf-8"]
        cmd += [url, "--progress"]
        # Thêm đường dẫn ffmpeg nếu tồn tại
        if os.path.exists(self.ffmpeg_path):
            cmd += ["--ffmpeg-location", self.ffmpeg_path]

        if self.subtitle_only:
            cmd.append("--skip-download")
            self.message.emit("📝 Chế độ: Chỉ tải phụ đề")
        else:
            cmd += ["-f", "bv*+ba/b", "--merge-output-format", "mp4"]

        # Template output
        if self.video_mode:
            if index == 1:
                output_template = f"%(title)s.%(ext)s"
            else:
                output_template = f"video_{index}_%(title)s.%(ext)s"
        else:
            if index == 1:
                output_template = f"%(autonumber)03d_%(title)s.%(ext)s"
                cmd.append("--yes-playlist")
            else:
                output_template = f"playlist_{index}_%(autonumber)03d_%(title)s.%(ext)s"
                cmd.append("--yes-playlist")
        cmd += ["-o", os.path.join(download_folder, output_template)]

        if self.audio_only and not self.subtitle_only:
            cmd += ["--extract-audio", "--audio-format", "mp3"]

        # Xử lý phụ đề
        if self.sub_mode != "":
            self._add_subtitle_options(cmd)

        cmd += ["--convert-subs", "srt"]

        if self.include_thumb:
            cmd.append("--write-thumbnail")
            self.message.emit("🖼️ Thumbnail")

        # print(cmd)
        return cmd

    def _add_subtitle_options(self, cmd):
        """Thêm tùy chọn phụ đề vào lệnh"""
        # sub_lang bây giờ là string đơn thay vì list
        lang_string = self.sub_lang
        lang_display = self.sub_lang_name
        if self.sub_mode == "1":
            cmd += ["--write-subs", "--sub-langs", lang_string]
            self.message.emit(
                f"🔤 Tải phụ đề chính thức cho ngôn ngữ: {lang_display}")
        elif self.sub_mode == "2":
            cmd += ["--write-auto-subs", "--sub-langs", lang_string]
            self.message.emit(
                f"🤖 Tải phụ đề tự động cho ngôn ngữ: {lang_display}")

        # Thêm các tùy chọn để đảm bảo tải được phụ đề
        cmd += [
            "--ignore-errors",           # Bỏ qua lỗi nếu một ngôn ngữ không có
            "--no-warnings",            # Không hiển thị cảnh báo
            "--sub-format", "srt/best"  # Ưu tiên định dạng SRT
        ]

        # Debug: In ra lệnh phụ đề
        # self.message.emit(f"🔧 Debug: Lệnh phụ đề = --sub-langs {lang_string}")

    def _update_progress_from_line(self, line):
        """Cập nhật progress từ output line"""
        if "%" in line:
            try:
                percent_str = line.split(
                    "%", 1)[0].split()[-1].replace(".", "").strip()
                percent = int(percent_str)
                if 0 <= percent <= 100:
                    self.progress_signal.emit(percent)
            except:
                pass
