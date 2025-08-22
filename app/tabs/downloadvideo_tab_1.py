from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QLabel, QTextEdit, QComboBox, QSpinBox,
    QMessageBox, QFileDialog, QCheckBox, QGroupBox, QLineEdit
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtCore import QThreadPool

from app.uiToolbarTab import UIToolbarTab

from app.core.config import AppConfig

from pathlib import Path

from app.workers.DL_workers import NTDownloadWorker

import os
from datetime import datetime

import subprocess
from typing import Optional


class DownloadVideoTab1(UIToolbarTab):
    """
    Tab Convert đơn giản để minh họa việc áp dụng HistoryPanel cho mỗi tab
    """

    def __init__(self, parent_main: QWidget) -> None:
        super().__init__(parent_main)
        self._initialize_state_variables()
       # self._setup_history()
        self._setup_ui()

    def _initialize_state_variables(self) -> None:

        self.worker: Optional[NTDownloadWorker] = None

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
        self.theard = QSpinBox()
        self.theard.setRange(1, 16)
        self.theard.setValue(AppConfig.DEFAULT_WORKERS_PLAYER)
        self.theard.setSuffix(" Thread")

        row1_layout.addWidget(self.type_video)
        row1_layout.addWidget(self.sub_mode)
        row1_layout.addWidget(self.language_box)
        row1_layout.addStretch()
        row1_layout.addWidget(self.theard)
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
            f"https://www.youtube.com/watch?v=BtxAPNXGgd8")
        self.url_inputdownloadvideo.setMinimumHeight(
            200)  # Chiều cao tối thiểu 100px
        content_layout.addWidget(self.url_inputdownloadvideo, 2)

    def _create_btn_downloadvideo(self, content_layout: QVBoxLayout) -> None:
        """Create button download video"""

        self.download_button = QPushButton(
            "🚀 Bắt đầu tải",
            clicked=self.on_start
        )
        self.download_button.setObjectName("btn_style_1")
        self.stop_button = QPushButton(
            "⏹️ Dừng Tải")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.on_end_all)
        self.stop_button.setObjectName("btn_style_1")
        content_layout.addWidget(self.download_button)
        content_layout.addWidget(self.stop_button)

    def open_folder_dialog(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Chọn thư mục")
        if folder_path:
            self.folder_name_input.setText(folder_path)

    def on_start(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        self._reset_progress()

        # Create new worker
        self.worker = NTDownloadWorker(
            self.url_inputdownloadvideo.toPlainText(), "vi-VN-HoaiMyNeural", 0, 0, 500, self.theard.value())

        # Connect signals
        self.worker.segment_ready.connect(self.on_segment_ready)
        self.worker.progress.connect(self.on_produce_progress)
        self.worker.progress_single.connect(self.on_update_progress)
        self.worker.status.connect(self.on_status)
        self.worker.all_done.connect(self.on_all_done)
        self.worker.error.connect(self.on_error)

        self.download_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        # Start worker
        self.worker.start()

    def on_end_all(self) -> None:

        # Stop TTS worker
        if self.worker and self.worker.isRunning():
            try:
                self.worker.stop()
                # Wait for worker to stop completely
                if self.worker.wait(3000):  # Wait max 3 seconds
                    pass
                else:
                    self.worker.terminate()
                    self.worker.wait(1000)

                # Reset worker reference
                self.worker = None
            except Exception as e:
                print(f"Warning: Error stopping worker in on_end_all: {e}")
                # Force cleanup
                try:
                    if self.worker:
                        self.worker.terminate()
                        self.worker.wait(1000)
                        self.worker = None
                except:
                    pass

        self.stop_button.setEnabled(False)
        self.download_button.setEnabled(True)
        # Update progress title and hide progress bar
        self._update_progress_title("")
        self._reset_progress()

        # Log end
        self._add_log_item("⏹ Đã kết thúc.", "info")

    def on_segment_ready(self, url: str, title: str) -> None:

        print(f"Segment {url} {title}")

    def on_produce_progress(self, emitted: int, total: int) -> None:

        self._update_progress(int(emitted / total * 100))

    def on_update_progress(self,  total: int) -> None:
        self._update_progress(total)

    def on_status(self, status: str) -> None:

        self._add_log_item(status)

    def on_all_done(self) -> None:

        # elf.lbl_status.setText(self.lbl_status.text())
        self.download_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self._update_progress_title("")
        self._reset_progress()

        # Log completion
        self._add_log_item("✅ Đã hoàn thành tất cả segments", "info")

    def on_error(self, error: str) -> None:

        self.stop_button.setEnabled(False)
        self.download_button.setEnabled(True)
        print(f"Error: {error}")

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

    def _add_log_item(self, message: str, level: str = "") -> None:
        """Add log item to main window's output_list if available"""
        try:
            # Try to access main window's output_list
            if hasattr(self.parent_main, '_add_log_item'):
                self.parent_main._add_log_item(message, level)
        except Exception as e:
            # Fallback to print if logging fails
            print(f"[TTS LOG ERROR] {e}")

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

    def stop_all(self) -> None:
        """Stop all processes"""
        # Stop TTS worker
        if getattr(self, "worker", None) and self.worker.isRunning():
            try:
                self.worker.stop()
                # Wait for worker to stop completely
                if self.worker.wait(3000):  # Wait max 3 seconds
                    pass
                else:
                    self.worker.terminate()
                    self.worker.wait(1000)

                # Reset worker reference
                self.worker = None
            except Exception as e:
                print(f"Warning: Error stopping worker in stop_all: {e}")
                # Force cleanup
                try:
                    if self.worker:
                        self.worker.terminate()
                        self.worker.wait(1000)
                        self.worker = None
                except:
                    pass

    def closeEvent(self, event) -> None:
        """Handle tab close event"""
        try:
            self.stop_all()
        except Exception as e:
            print(f"Warning: Error in closeEvent: {e}")
            # Force cleanup
            try:
                if hasattr(self, 'worker') and self.worker:
                    self.worker.terminate()
                    self.worker.wait(1000)
                    self.worker = None
            except:
                pass

        super().closeEvent(event)