from decimal import setcontext
from turtle import onclick
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QLabel, QTextEdit, QComboBox, QSlider, QSpinBox,
    QListWidget, QMessageBox,
    QFileDialog, QListWidgetItem, QCheckBox, QGroupBox, QLineEdit
)
from PySide6.QtCore import Qt, QTimer
from typing import Optional, Callable, Type
from PySide6.QtCore import Signal

from app.uiToolbarTab import UIToolbarTab

from app.core.config import AppConfig

from pathlib import Path

from app.workers.download_Worker import DownloadVideo
import os
from datetime import datetime


class DownloadVideoTab(UIToolbarTab):
    """
    Tab Convert đơn giản để minh họa việc áp dụng HistoryPanel cho mỗi tab
    """

    def __init__(self, parent_main: QWidget) -> None:
        super().__init__(parent_main)
        self._initialize_state_variables()
       # self._setup_history()
        self._setup_ui()

    def _initialize_state_variables(self) -> None:

        self.worker = None
        # Thread
        self.index = 1
        self.active_threads = []
        self.max_workers = 4
        self.running = 0
        self.stopped = False

    def _setup_history(self) -> None:
        """Enable per-tab history with its own panel and button"""
        # self.enable_history(
        #     hist_title="Lịch sử Download Video",
        #     item_factory=lambda text, ts, meta: TTSHistoryItem(text, ts, meta),
        # )

        # Đưa nút lịch sử vào thanh toolbar của tab
        if self.history:
            self.add_toolbar_widget(self.history.btn)

        # Không thêm demo; sẽ load khi mở panel

    def _setup_ui(self) -> None:
        """Create simple content for the Convert tab"""
        root_layout = self.layout()

        self._setup_header_section(root_layout)
        self._setup_content_section(root_layout)
        self._setup_bottom_section(root_layout)

    def _setup_header_section(self, root_layout: QVBoxLayout) -> None:

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(2, 2, 2, 2)

        row_layout = QVBoxLayout()

        # Job parameters row
        self._create_job_parameters_row(row_layout)
        self._create_control_buttons_row(row_layout)
        header_layout.addLayout(row_layout)
        root_layout.addLayout(header_layout)

    def _setup_content_section(self, root_layout: QVBoxLayout) -> None:

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        # Text input area
        self._group_box_downloadvideo(content_layout)
        self._create_text_input_area(content_layout)

        root_layout.addLayout(content_layout)

    def _setup_bottom_section(self, root_layout: QVBoxLayout) -> None:
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(2, 2, 2, 2)
        self._create_btn_downloadvideo(bottom_layout)
        root_layout.addLayout(bottom_layout)

    def _create_job_parameters_row(self, parent_layout: QVBoxLayout) -> None:
        """Create job parameters row"""
        row1_layout = QHBoxLayout()

        self.type_video = QComboBox()
        self.type_video.addItems(["Video", "Playlist"])
        self.type_video.setCurrentText("Video")

        self.sub_mode = QComboBox()
        self.sub_mode_list = [
            ("❌ Không tải xuống", ""),
            ("📄 Phụ đề có sẵn", "1"),
            ("🤖 Phụ đề tự động", "2"),
        ]
        for name, code in self.sub_mode_list:
            self.sub_mode.addItem(name, userData=code)

        for i in range(self.sub_mode.count()):
            if self.sub_mode.itemData(i) == "2":
                self.sub_mode.setCurrentIndex(i)
                break
        self.language_box = QComboBox()
        self.languages = [
            ("Tiếng Việt", "vi"),
            ("Tiếng Anh", "en"),
            ("Tiếng Nhật", "ja"),
            ("Tiếng Trung", "zh")
        ]
        for name, code in self.languages:
            self.language_box.addItem(name, userData=code)

        # Chọn ngôn ngữ theo mã code (VD: "ja")
        for i in range(self.language_box.count()):
            if self.language_box.itemData(i) == "vi":
                self.language_box.setCurrentIndex(i)
                break
        # Threads spinbox
        self.theard_video = QSpinBox()
        self.theard_video.setRange(1, 16)
        self.theard_video.setValue(AppConfig.DEFAULT_WORKERS_PLAYER)
        self.theard_video.setSuffix(" Thread")

        row1_layout.addWidget(self.type_video)
        row1_layout.addWidget(self.sub_mode)
        row1_layout.addWidget(self.language_box)
        row1_layout.addStretch()
        row1_layout.addWidget(self.theard_video)
        parent_layout.addLayout(row1_layout)

    def _create_control_buttons_row(self, parent_layout: QVBoxLayout) -> None:

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self.audio_only = QCheckBox("🎵 Tải âm thanh MP3")
        self.include_thumb = QCheckBox("🖼️ Tải ảnh thumbnail")
        self.subtitle_only = QCheckBox("📜 Chỉ tải phụ đề")

        row.addWidget(self.audio_only)
        row.addWidget(self.include_thumb)
        row.addWidget(self.subtitle_only)
        row.addStretch()
        parent_layout.addLayout(row)

    def _group_box_downloadvideo(self, content_layout: QVBoxLayout) -> None:
        """Create group box download video"""
        self.group_box = QGroupBox("📁 Tên thư mục tải (tuỳ chọn)")
        group_layout = QVBoxLayout()  # ✅ cần thêm dòng này

        # Tạo layout ngang cho input + button
        input_layout = QHBoxLayout()
        self.folder_name_input = QLineEdit()
        self.folder_name_input.setPlaceholderText(
            "Nhập tên thư mục hoặc chọn thư mục...")
        self.folder_name_input.setReadOnly(True)
        self.folder_name_input.setObjectName("folderNameInput")
        # ✅ Đường dẫn mặc định: thư mục hiện tại + "/Video"
        default_dir = Path.cwd() / "Video"
        self.folder_name_input.setText(str(default_dir))
        folder_button = QPushButton("Open",
                                    clicked=self.open_folder_dialog
                                    )
        folder_button.setObjectName("btn_style_1")
        # folder_button.clicked.connect(self.open_folder_dialog)

        # Thêm vào layout ngang
        input_layout.addWidget(self.folder_name_input)
        input_layout.addWidget(folder_button)

        # Thêm layout ngang vào layout chính của group box
        group_layout.addLayout(input_layout)

        # Set layout cho group box
        self.group_box.setLayout(group_layout)

        # Cuối cùng, thêm group box vào content layout
        content_layout.addWidget(self.group_box)

    def _create_text_input_area(self, content_layout: QVBoxLayout) -> None:
        """Create text input area"""
        self.url_inputdownloadvideo = QTextEdit(
            placeholderText="Nhập URL video hoặc văn bản tại đây..."
        )
        self.url_inputdownloadvideo.setPlainText(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.url_inputdownloadvideo.setMinimumHeight(
            200)  # Chiều cao tối thiểu 100px
        content_layout.addWidget(self.url_inputdownloadvideo, 2)

    def _create_btn_downloadvideo(self, content_layout: QVBoxLayout) -> None:
        """Create button download video"""

        self.download_button = QPushButton(
            "🚀 Bắt đầu tải",
            clicked=self.start_download
        )
        self.download_button.setObjectName("btn_style_1")
        self.stop_button = QPushButton(
            "⏹️ Dừng Tải")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_download)
        self.stop_button.setObjectName("btn_style_1")
        content_layout.addWidget(self.download_button)
        content_layout.addWidget(self.stop_button)

    def open_folder_dialog(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Chọn thư mục")
        if folder_path:
            self.folder_name_input.setText(folder_path)

    def start_download(self):

        # if self.worker and self.worker.isRunning():
        #     self.worker.stop()
        self.stopped = False

        urls = [u.strip()
                for u in self.url_inputdownloadvideo.toPlainText().splitlines() if u.strip()]
        if not urls:
            QMessageBox.warning(self, "Cảnh báo", "Bạn chưa nhập URL nào.")
            return

        urls = self.url_inputdownloadvideo.toPlainText().splitlines()
        urls = [u.strip() for u in urls if u.strip()]

        self.urls = urls

        selected_code = self.language_box.currentData()

        # Hiển thị các tùy chọn khác
        options = []
        if self.audio_only.isChecked():
            options.append("🎵 Audio MP3")
        if self.include_thumb.isChecked():
            options.append("🖼️ Thumbnail")
        if self.subtitle_only.isChecked():
            options.append("📝 Chỉ phụ đề")

        if options:
            self._add_log_item(f"⚙️ Tùy chọn: {', '.join(options)}")

        # Folder name
        custom_folder = self.folder_name_input.text()
        if custom_folder:
            self._add_log_item(f"📁 Thư mục: {custom_folder}")

        selected_sub_mode = self.sub_mode.currentData()
        sub_mode_name = next(
            (name for name, code in self.sub_mode_list if code == selected_sub_mode), None)
        if selected_sub_mode:
            self._add_log_item(f"📜 Chế độ {sub_mode_name}")

        self.max_workers = int(self.theard_video.value())
        self._add_log_item(f"Đang chạy với {self.max_workers} thread")

        self.download_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        self.custom_folder_name = custom_folder
        self.video_mode = self.type_video.currentText()
        self._add_log_item("🚀 Bắt đầu tải video...")
        self.index = 1
        self.active_threads.clear()
        self.running = 0
        self.audio_only_flag = self.audio_only.isChecked()
        self.sub_mode_flag = selected_sub_mode
        self.sub_lang_code_flag = selected_code
        self.sub_lang_name_flag = self.language_box.currentText()
        self.include_thumb_flag = self.include_thumb.isChecked()
        self.subtitle_only_flag = self.subtitle_only.isChecked()
        self.download_folder = self._create_download_folder()
        self._reset_progress()
        self._update_progress_title("Tiến trình xử lý")
        self.download_next_batch()

    def stop_download(self):
        self.stopped = True

        for thread in self.active_threads:
            thread.stop_flag = True

        self._add_log_item("⏹ Đang dừng các tiến trình tải...")
        self.stop_button.setEnabled(False)
        self.download_button.setEnabled(True)
        self._reset_progress()

    def download_next_batch(self):
        while self.running < self.max_workers and self.index <= len(self.urls) and not self.stopped:
            url = self.urls[self.index - 1]
            worker_id = self.running + 1
            thread = DownloadVideo(
                url=url,
                video_index=self.index,
                total_urls=len(self.urls),
                worker_id=worker_id,
                video_mode=self.video_mode,
                audio_only=self.audio_only_flag,
                sub_mode=self.sub_mode_flag,
                sub_lang=self.sub_lang_code_flag,
                sub_lang_name=self.sub_lang_name_flag,
                include_thumb=self.include_thumb_flag,
                subtitle_only=self.subtitle_only_flag,
                custom_folder_name=self.download_folder
            )
            thread.message_signal.connect(self._add_log_item)
            thread.finished_signal.connect(self.handle_thread_done)
            thread.progress_signal.connect(self.update_progress)
            thread.error_signal.connect(self.error_thread)
            self.active_threads.append(thread)
            thread.start()
            self.running += 1
            self.index += 1

    def handle_thread_done(self):
        self.running -= 1
        if not self.stopped and self.index <= len(self.urls):
            self.download_next_batch()
        elif self.running == 0:
            if self.stopped:
                self._add_log_item("⏹ Đã dừng toàn bộ tiến trình.")
            else:
                # self.progress.setValue(100)
                self._add_log_item("✅ Tải xong tất cả video.")
                self._add_log_item(
                    f"📂 Video được lưu tại: {self.download_folder}")
            self.download_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self._reset_progress()

    def error_thread(self, value):
        self._add_log_item(value, "error")

    def update_progress(self, value):
        self._update_progress(value)
        # self._reset_ui_after_download()

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

    def _reset_progress(self) -> None:
        """Reset progress bar from main window"""
        try:
            if hasattr(self.parent_main, 'progress_bar'):
                # Ẩn progress bar khi reset về 0
                self.parent_main.progress_bar.setVisible(False)
                # Reset về 0
                self.parent_main.progress_bar.setValue(0)
        except Exception as e:
            print(f"[TTS PROGRESS ERROR] {e}")

    def _update_progress_title(self, title: str) -> None:
        """Update progress title from main window"""
        try:
            if hasattr(self.parent_main, '_progress_title'):
                # Chỉ hiện progress title khi có tiêu đề
                if title and title.strip():
                    self.parent_main._progress_title.setVisible(True)
                    self.parent_main._progress_title.setText(title)
                else:
                    self.parent_main._progress_title.setVisible(False)
        except Exception as e:
            print(f"[TTS PROGRESS TITLE ERROR] {e}")

    def _update_progress(self, value: int) -> None:
        """Update progress bar from main window"""
        try:
            if hasattr(self.parent_main, 'progress_bar'):
                # Chỉ hiện progress bar khi có giá trị
                if value > 0:
                    self.parent_main.progress_bar.setVisible(True)
                # Cập nhật giá trị
                self.parent_main.progress_bar.setValue(value)
        except Exception as e:
            print(f"[TTS PROGRESS ERROR] {e}")

    def _add_log_item(self, message: str, level: str = "") -> None:
        """Add log item to main window's output_list if available"""
        try:
            # Try to access main window's output_list
            if hasattr(self.parent_main, '_add_log_item'):
                self.parent_main._add_log_item(message, level)
        except Exception as e:
            # Fallback to print if logging fails
            print(f"[DOWNLOAD LOG ERROR] {e}")
