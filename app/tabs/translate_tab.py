from signal import default_int_handler
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QLabel, QTextEdit, QComboBox, QSpinBox,
    QMessageBox, QFileDialog, QCheckBox, QGroupBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtCore import QThreadPool

from app.uiToolbarTab import UIToolbarTab

from app.core.config import AppConfig

from pathlib import Path

import os
from datetime import datetime

import subprocess
from typing import Optional


class TranslateTab(UIToolbarTab):
    """
    Tab Convert đơn giản để minh họa việc áp dụng HistoryPanel cho mỗi tab
    """

    def __init__(self, parent_main: QWidget) -> None:
        super().__init__(parent_main)
        self._initialize_state_variables()
       # self._setup_history()
        self._setup_ui()
        default_service = "Google Gemini" #"Google Translate" #Google Gemini, OpenAI (ChatGPT)   
        self.service_combo.setCurrentText(default_service)
        self._on_service_changed(default_service)

    def _initialize_state_variables(self) -> None:
        pass
        # self.worker: Optional[NTDownloadWorker] = None

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
        # self._create_job_parameters_row(row_layout)
        self._create_control_buttons_row(row_layout)
        header_layout.addLayout(row_layout)
        root_layout.addLayout(header_layout)

    def _setup_content_section(self, root_layout: QVBoxLayout) -> None:

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        # Text input area
        self._create_box_translate(content_layout)
        self._create_text_input_area(content_layout)

        root_layout.addLayout(content_layout)

    def _setup_bottom_section(self, root_layout: QVBoxLayout) -> None:
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(2, 2, 2, 2)
        self._create_btn_downloadvideo(bottom_layout)
        root_layout.addLayout(bottom_layout)

  

    def _create_control_buttons_row(self, parent_layout: QVBoxLayout) -> None:
        """Create control buttons and settings row with 4 columns and 2 rows"""
        # Hàng 1: Dịch vụ và OpenAI API Key
        first_row = QHBoxLayout()
        
        # Cột 1: Label Dịch vụ
        service_label = QLabel("Dịch vụ:")
        service_label.setFixedWidth(100)  # Đặt độ rộng cố định cho label
        first_row.addWidget(service_label)
        
        # Cột 2: Combobox Dịch vụ
        self.service_combo = QComboBox()
        self.service_combo.addItems(["Google Translate", "Google Gemini", "OpenAI (ChatGPT)"])
        self.service_combo.setFixedHeight(30)
        self.service_combo.setFixedWidth(150)  # Đặt độ rộng cố định cho combobox
        self.service_combo.currentTextChanged.connect(self._on_service_changed)  # Kết nối signal
        first_row.addWidget(self.service_combo)
        # Cột 3: Label OpenAI API Key
        self.api_label = QLabel("API Key:")  # Đổi tên để linh hoạt hơn
        self.api_label.setFixedWidth(120)  # Đặt độ rộng cố định cho label
        first_row.addWidget(self.api_label)
        
        # Cột 4: Input OpenAI API Key
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Dán API Key của bạn vào đây")
        self.api_key_input.setFixedHeight(30)
        self.api_key_input.setFixedWidth(300)
        first_row.addWidget(self.api_key_input)
        # Bỏ addStretch() để input có thể kéo dãn tối đa
        first_row.addStretch()
        parent_layout.addLayout(first_row)
        
        # Hàng 2: Ngôn ngữ nguồn và đích
        second_row = QHBoxLayout()
        
        # Cột 1: Label Ngôn ngữ nguồn
        source_label = QLabel("Ngôn ngữ nguồn:")
        source_label.setFixedWidth(100)  # Đặt độ rộng cố định giống service_label
        second_row.addWidget(source_label)
        
        # Cột 2: Combobox Ngôn ngữ nguồn
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.addItems(["Auto Detect", "Vietnamese", "English", "Chinese", "Japanese", "Korean"])
        self.source_lang_combo.setFixedHeight(30)
        self.source_lang_combo.setFixedWidth(150)  # Đặt độ rộng cố định giống service_combo
        second_row.addWidget(self.source_lang_combo)
        
        # Cột 3: Label Ngôn ngữ đích
        target_label = QLabel("Ngôn ngữ đích:")
        target_label.setFixedWidth(120)  # Đặt độ rộng cố định giống api_label
        second_row.addWidget(target_label)
        
        # Cột 4: Combobox Ngôn ngữ đích
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItems(["English", "Vietnamese", "Chinese", "Japanese", "Korean"])
        self.target_lang_combo.setCurrentText("English")
        self.target_lang_combo.setFixedHeight(30)
        self.target_lang_combo.setFixedWidth(150)  # Đặt độ rộng cố định giống source_lang_combo
        second_row.addWidget(self.target_lang_combo)
        
        second_row.addStretch()  # Đẩy sang trái
        parent_layout.addLayout(second_row)
        
    
    def _on_service_changed(self, service_name: str) -> None:
        """Xử lý khi service thay đổi"""
        if service_name == "Google Translate":
            # Google Translate không cần API Key và prompt
            self.api_label.setVisible(False)
            self.api_key_input.setVisible(False)
            # Ẩn prompt_container
            if hasattr(self, 'prompt_container'):
                self.prompt_container.setVisible(False)
        elif service_name == "Google Gemini":
            # Google Gemini cần API Key và prompt
            self.api_label.setVisible(True)
            self.api_key_input.setVisible(True)
            self.api_label.setText("Gemini API Key:")
            self.api_key_input.setEnabled(True)
            self.api_key_input.setPlaceholderText("Dán Gemini API Key của bạn vào đây")
            # Hiện prompt_container
            if hasattr(self, 'prompt_container'):
                self.prompt_container.setVisible(True)
        elif service_name == "OpenAI (ChatGPT)":
            # OpenAI cần API Key và prompt
            self.api_label.setVisible(True)
            self.api_key_input.setVisible(True)
            self.api_label.setText("OpenAI API Key:")
            self.api_key_input.setEnabled(True)
            self.api_key_input.setPlaceholderText("Dán OpenAI API Key của bạn vào đây")
            # Hiện prompt_container
            if hasattr(self, 'prompt_container'):
                self.prompt_container.setVisible(True)

    def _create_box_translate(self, content_layout: QVBoxLayout) -> None:
        """Create group box download video"""
        self.input_output_layout = QHBoxLayout()  # Make it an instance variable
        self.input_text = QTextEdit()
        self.input_text.setMinimumHeight(200)
        self.input_text.setPlaceholderText("Nhập văn bản cần dịch vào đây...")
        self.output_text = QTextEdit()
        self.output_text.setMinimumHeight(200)
        self.output_text.setPlaceholderText(
            "Kết quả dịch sẽ hiển thị ở đây...")
        self.output_text.setReadOnly(True)
        self.input_output_layout.addWidget(self.input_text)
        self.input_output_layout.addWidget(self.output_text)
        # layout.addLayout(input_output_layout)

        # Cuối cùng, thêm group box vào content layout
        content_layout.addLayout(self.input_output_layout)  # Use addLayout instead of addWidget

    def _create_text_input_area(self, content_layout: QVBoxLayout) -> None:
        """Create text input area"""
        # Tạo container widget để chứa prompt_layout
        self.prompt_container = QWidget()
        self.prompt_layout = QVBoxLayout()
        self.prompt_layout.setContentsMargins(0, 0, 0, 0)
        
        self.prompt_text = QTextEdit()
        self.prompt_text.setPlaceholderText("Nhập prompt tại đây...")
        self.prompt_layout.addWidget(QLabel("Prompt Tùy chỉnh cho các mô hình AI"))
        self.prompt_layout.addWidget(self.prompt_text)
        
        # Đặt layout cho container
        self.prompt_container.setLayout(self.prompt_layout)
         
        content_layout.addWidget(self.prompt_container)

    def _create_btn_downloadvideo(self, content_layout: QVBoxLayout) -> None:
        """Create button download video"""

        self.btn_translate = QPushButton(
            "🚀 Bắt đầu dịch",
            # clicked=self.on_start
        )
        self.btn_translate.setObjectName("btn_style_1")
        # self.stop_button = QPushButton(
        #     "⏹️ Dừng Tải")
        # self.stop_button.setEnabled(False)
        # self.stop_button.clicked.connect(self.on_end_all)
        # self.stop_button.setObjectName("btn_style_1")
        content_layout.addWidget(self.btn_translate)
        # content_layout.addWidget(self.stop_button)

    def on_all_done(self) -> None:

        pass
        # self.download_button.setEnabled(True)
        # self.stop_button.setEnabled(False)
        # self._update_progress_title("")
        # self._reset_progress()

        # # Log completion
        # self._add_log_item("✅ Đã hoàn thành tất cả segments", "info")

    def on_error(self, error: str) -> None:

        # self.stop_button.setEnabled(False)
        # self.download_button.setEnabled(True)
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

    # def stop_all(self) -> None:
    #     """Stop all processes"""
    #     # Stop TTS worker
    #     if getattr(self, "worker", None) and self.worker.isRunning():
    #         try:
    #             self.worker.stop()
    #             # Wait for worker to stop completely
    #             if self.worker.wait(3000):  # Wait max 3 seconds
    #                 pass
    #             else:
    #                 self.worker.terminate()
    #                 self.worker.wait(1000)

    #             # Reset worker reference
    #             self.worker = None
    #         except Exception as e:
    #             print(f"Warning: Error stopping worker in stop_all: {e}")
    #             # Force cleanup
    #             try:
    #                 if self.worker:
    #                     self.worker.terminate()
    #                     self.worker.wait(1000)
    #                     self.worker = None
    #             except:
    #                 pass

    # def closeEvent(self, event) -> None:
    #     """Handle tab close event"""
    #     try:
    #         self.stop_all()
    #     except Exception as e:
    #         print(f"Warning: Error in closeEvent: {e}")
    #         # Force cleanup
    #         try:
    #             if hasattr(self, 'worker') and self.worker:
    #                 self.worker.terminate()
    #                 self.worker.wait(1000)
    #                 self.worker = None
    #         except:
    #             pass

        # super().closeEvent(event)