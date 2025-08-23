from signal import default_int_handler
from PySide6.QtWidgets import (QApplication,
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

from typing import Optional, List, Dict, Tuple

from langdetect import detect, DetectorFactory

from deep_translator import GoogleTranslator

from app.workers.translate_workers import MultiThreadTranslateWorker, BatchTranslateWorker

from app.core.audio_player import AudioPlayer
from app.workers.translate_workers import TranslateTTSWorker
from app.utils.helps import split_text, group_by_char_limit_with_len


LANGS = [
    ("Tự phát hiện", "auto"),
    ("Tiếng Việt", "vi"),
    ("Tiếng Anh", "en"),
    ("Tiếng Nhật", "ja"),
    ("Tiếng Trung", "zh-CN"),
    ("Tiếng Hàn", "ko"),
    ("Tiếng Pháp", "fr"),
    ("Tiếng Đức", "de"),
    ("Tiếng Tây Ban Nha", "es"),
    ("Tiếng Bồ Đào Nha", "pt"),
    ("Tiếng Thái", "th"),
    ("Tiếng Nga", "ru"),
    ("Tiếng Ý", "it"),
]


def code_by_name(name: str) -> str:
    for n, c in LANGS:
        if n == name:
            return c
    return "auto"


def name_by_code(code: str) -> str:
    for n, c in LANGS:
        if c.lower() == code.lower():
            return n
    return code

class TranslateTab(UIToolbarTab):
    """
    Tab Convert đơn giản để minh họa việc áp dụng HistoryPanel cho mỗi tab
    """

    def __init__(self, parent_main: QWidget) -> None:
        super().__init__(parent_main)
        self._initialize_state_variables()
       # self._setup_history()
        self._setup_ui()
        # "Google Translate" #Google Gemini, OpenAI (ChatGPT)
        default_service = "Google Translate"
        self.service_combo.setCurrentText(default_service)
        self._on_service_changed(default_service)
        
        # Xóa dòng này: QTimer.singleShot(100, self.load_voices_for_languages)

    def _initialize_state_variables(self) -> None:
        # Thêm worker và các biến trạng thái
        self.worker: Optional[MultiThreadTranslateWorker] = None
        self.batch_worker: Optional[BatchTranslateWorker] = None
        self.translated_segments: List[Tuple[str, str, int]] = []  # (original, translated, index)
        self.is_batch_mode = False
        
        # Thread management
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(10)  # Tối đa 10 thread
        
        # TTS worker cho audio
        self.tts_worker: Optional[TranslateTTSWorker] = None
        
        # Audio player
        self.audio_player: Optional[AudioPlayer] = None
        
        # Audio settings
        self.auto_play_audio = True  # Tự động phát audio khi hoàn thành
        self.audio_segments: List[str] = []  # Danh sách đường dẫn audio
        self.audio_durations: List[int] = []  # Danh sách thời lượng audio
        
        # Biến cho việc đọc tuần tự
        self.current_chunks: List[str] = []
        self.current_chunk_index: int = 0
        self.current_lang_code: str = ""
        self.current_text_type: str = ""
        
        # Log file
        self.log_file_path = "testtr.txt"

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
        self._create_control_buttons_row(row_layout)
        header_layout.addLayout(row_layout)
        root_layout.addLayout(header_layout)

    def _setup_content_section(self, root_layout: QVBoxLayout) -> None:

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        # Text input area
        self._create_box_translate(content_layout)
        self._create_text_input_area(content_layout)
        
        # Thêm danh sách file audio
        self._create_audio_list_section(content_layout)
        
        root_layout.addLayout(content_layout)

    def _setup_bottom_section(self, root_layout: QVBoxLayout) -> None:
        """Thiết lập phần bottom của tab"""
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(2, 2, 2, 2)
        self._create_btn_downloadvideo(bottom_layout)
        root_layout.addLayout(bottom_layout)

    def _create_box_translate(self, content_layout: QVBoxLayout) -> None:
        """Create group box download video"""
        self.input_output_layout = QHBoxLayout()  # Make it an instance variable
        
        # Input text area with auto read button
        input_container = QWidget()
        input_layout = QVBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        # Input text area
        self.input_text = QTextEdit()
        self.input_text.setMinimumHeight(200)
        self.input_text.setPlaceholderText("Nhập văn bản cần dịch vào đây...")
        
        # Auto read button for input text
        self.btn_read_source = QPushButton("🔊 Đọc văn bản nguồn")
        self.btn_read_source.clicked.connect(self._read_source_text)
        self.btn_read_source.setObjectName("btn_style_1")
        
        input_layout.addWidget(self.input_text)
        input_layout.addWidget(self.btn_read_source)
        input_container.setLayout(input_layout)
        
        # Output text area with auto read button
        output_container = QWidget()
        output_layout = QVBoxLayout()
        output_layout.setContentsMargins(0, 0, 0, 0)
        
        # Output text area
        self.output_text = QTextEdit()
        self.output_text.setMinimumHeight(200)
        self.output_text.setPlaceholderText("Kết quả dịch sẽ hiển thị ở đây...")
        self.output_text.setReadOnly(True)
        
        # Auto read button for output text
        self.btn_read_target = QPushButton("🔊 Đọc văn bản đích")
        self.btn_read_target.clicked.connect(self._read_target_text)
        self.btn_read_target.setObjectName("btn_style_1")
        
        output_layout.addWidget(self.output_text)
        output_layout.addWidget(self.btn_read_target)
        output_container.setLayout(output_layout)
        
        # Add to layout
        self.input_output_layout.addWidget(input_container)
        self.input_output_layout.addWidget(output_container)
        
        # Cuối cùng, thêm group box vào content layout
        content_layout.addLayout(self.input_output_layout)

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
        self.service_combo.addItems(
            ["Google Translate", "Google Gemini", "OpenAI (ChatGPT)"])
        self.service_combo.setFixedHeight(30)
        # Đặt độ rộng cố định cho combobox
        self.service_combo.setFixedWidth(150)
        self.service_combo.currentTextChanged.connect(
            self._on_service_changed)  # Kết nối signal
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
        # Đặt độ rộng cố định giống service_label
        source_label.setFixedWidth(100)
        second_row.addWidget(source_label)

        # Cột 2: Combobox Ngôn ngữ nguồn
        self.source_lang_combo = QComboBox()
        self.source_lang_combo.addItems([n for n, _ in LANGS])
        self.source_lang_combo.setFixedHeight(30)
        # Đặt độ rộng cố định giống service_combo
        self.source_lang_combo.setFixedWidth(150)
        second_row.addWidget(self.source_lang_combo)

        # Cột 3: Label Ngôn ngữ đích
        target_label = QLabel("Ngôn ngữ đích:")
        target_label.setFixedWidth(120)  # Đặt độ rộng cố định giống api_label
        second_row.addWidget(target_label)

        # Cột 4: Combobox Ngôn ngữ đích
        self.target_lang_combo = QComboBox()
        self.target_lang_combo.addItems([n for n, _ in LANGS])
        self.target_lang_combo.setCurrentText("Tiếng Anh")
        self.target_lang_combo.setFixedHeight(30)
        # Đặt độ rộng cố định giống source_lang_combo
        self.target_lang_combo.setFixedWidth(150)
        second_row.addWidget(self.target_lang_combo)

        second_row.addStretch()  # Đẩy sang trái
        parent_layout.addLayout(second_row)

        # Hàng 3: Batch mode và các tham số
        third_row = QHBoxLayout()
        
        # Cột 1: Checkbox Batch mode
        self.batch_mode_checkbox = QCheckBox("Chế độ hàng loạt")
        self.batch_mode_checkbox.setFixedWidth(120)
        self.batch_mode_checkbox.toggled.connect(self._on_batch_mode_toggled)
        third_row.addWidget(self.batch_mode_checkbox)
        
        # Cột 2: Label Max Length
        max_len_label = QLabel("Độ dài tối đa:")
        max_len_label.setFixedWidth(100)
        third_row.addWidget(max_len_label)
        
        # Cột 3: Spinbox Max Length
        self.max_len_spinbox = QSpinBox()
        self.max_len_spinbox.setRange(100, 1000)
        self.max_len_spinbox.setValue(500)
        self.max_len_spinbox.setFixedHeight(30)
        self.max_len_spinbox.setFixedWidth(100)
        self.max_len_spinbox.setSuffix(" ký tự")
        third_row.addWidget(self.max_len_spinbox)
        
        # Cột 4: Label Workers
        workers_label = QLabel("Số luồng:")
        workers_label.setFixedWidth(80)
        third_row.addWidget(workers_label)
        
        # Cột 5: Spinbox Workers
        self.workers_spinbox = QSpinBox()
        self.workers_spinbox.setRange(1, 3)
        self.workers_spinbox.setValue(3)
        self.workers_spinbox.setFixedHeight(30)
        self.workers_spinbox.setFixedWidth(80)
        third_row.addWidget(self.workers_spinbox)
        
        parent_layout.addLayout(third_row)

    def _on_service_changed(self, service_name: str) -> None:
        """Handle service selection change"""
        if service_name == "Google Translate":
            self.api_label.setText("API Key:")
            self.api_key_input.setPlaceholderText("Dán API Key của bạn vào đây")
            self.api_key_input.setReadOnly(False)
            self.api_key_input.clear()
        elif service_name == "Google Gemini":
            self.api_label.setText("API Key:")
            self.api_key_input.setPlaceholderText("Dán API Key của bạn vào đây")
            self.api_key_input.setReadOnly(False)
            self.api_key_input.clear()
        elif service_name == "OpenAI (ChatGPT)":
            self.api_label.setText("API Key:")
            self.api_key_input.setPlaceholderText("Dán API Key của bạn vào đây")
            self.api_key_input.setReadOnly(False)
            self.api_key_input.clear()

    def _on_batch_mode_toggled(self, checked: bool) -> None:
        """Handle batch mode checkbox change"""
        self.is_batch_mode = checked
        if checked:
            self.max_len_spinbox.setRange(100, 2000)
            self.max_len_spinbox.setValue(500)
            self.workers_spinbox.setRange(1, 10)
            self.workers_spinbox.setValue(3)
        else:
            self.max_len_spinbox.setRange(100, 1000)
            self.max_len_spinbox.setValue(500)
            self.workers_spinbox.setRange(1, 3)
            self.workers_spinbox.setValue(3)

    def _create_text_input_area(self, content_layout: QVBoxLayout) -> None:
        """Create text input area"""
        # Tạo container widget để chứa prompt_layout
        self.prompt_container = QWidget()
        self.prompt_layout = QVBoxLayout()
        self.prompt_layout.setContentsMargins(0, 0, 0, 0)

        self.prompt_text = QTextEdit()
        self.prompt_text.setPlaceholderText("Nhập prompt tại đây...")
        self.prompt_layout.addWidget(
            QLabel("Prompt Tùy chỉnh cho các mô hình AI"))
        self.prompt_layout.addWidget(self.prompt_text)

        # Đặt layout cho container
        self.prompt_container.setLayout(self.prompt_layout)

        content_layout.addWidget(self.prompt_container)

    def _create_btn_downloadvideo(self, content_layout: QVBoxLayout) -> None:
        """Create button download video"""
        button_layout = QHBoxLayout()
        
        self.btn_translate = QPushButton(
            "🚀 Bắt đầu dịch",
            clicked=self.translate_now
        )
        self.btn_translate.setObjectName("btn_style_1")
        button_layout.addWidget(self.btn_translate)
        
        # Thêm nút dừng
        self.stop_button = QPushButton("⏹️ Dừng")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_translation)
        self.stop_button.setObjectName("btn_style_1")
        button_layout.addWidget(self.stop_button)
        
        # Thêm nút xóa kết quả
        self.clear_button = QPushButton("🗑️ Xóa kết quả")
        self.clear_button.clicked.connect(self.clear_results)
        self.clear_button.setObjectName("btn_style_2")
        button_layout.addWidget(self.clear_button)
        
        button_layout.addStretch()
        content_layout.addLayout(button_layout)

    def translate_now(self) -> None:
        """Bắt đầu dịch thuật"""
        if self.is_batch_mode:
            self._start_batch_translation()
        else:
            self._start_single_translation()

    def _start_single_translation(self) -> None:
        """Bắt đầu dịch một văn bản"""
        text = self.input_text.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Thông báo", "Vui lòng nhập văn bản cần dịch.")
            return

        src = code_by_name(self.source_lang_combo.currentText())
        tgt = code_by_name(self.target_lang_combo.currentText())
        if tgt == "auto":
            QMessageBox.information(self, "Thông báo", "Ngôn ngữ đích không thể là 'Tự phát hiện'.")
            return

        service = self.service_combo.currentText()
        api_key = self.api_key_input.text().strip()
        
        # Kiểm tra API key nếu cần
        if service in ["Google Gemini", "OpenAI (ChatGPT)"] and not api_key:
            QMessageBox.warning(self, "Cảnh báo", f"Vui lòng nhập API Key cho {service}.")
            return

        # Lấy tham số
        max_len = self.max_len_spinbox.value()
        workers = self.workers_spinbox.value()
        custom_prompt = getattr(self, 'prompt_text', None)
        prompt = custom_prompt.toPlainText().strip() if custom_prompt else ""

        # Xóa kết quả cũ
        self.output_text.clear()
        self.translated_segments.clear()

        # Tạo và chạy worker
        self.worker = MultiThreadTranslateWorker(
            text, src, tgt, service, api_key, max_len, workers, prompt
        )
        
        # Kết nối signals
        self.worker.segment_translated.connect(self._on_segment_translated)
        self.worker.progress.connect(self._update_progress)
        self.worker.status.connect(self._add_log_item)
        self.worker.all_done.connect(self._on_translation_complete)
        self.worker.error.connect(self._on_translation_error)
        
        # Cập nhật UI
        self.reset_button_Translate(False)
        self.stop_button.setEnabled(True)
        self._update_progress_title("Đang dịch...")
        
        # Bắt đầu worker
        self.worker.start()

    def _start_batch_translation(self) -> None:
        """Bắt đầu dịch hàng loạt"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Chọn file để dịch hàng loạt", "", 
            "Text files (*.txt);;All files (*)"
        )
        
        if not files:
            return
            
        src = code_by_name(self.source_lang_combo.currentText())
        tgt = code_by_name(self.target_lang_combo.currentText())
        if tgt == "auto":
            QMessageBox.information(self, "Thông báo", "Ngôn ngữ đích không thể là 'Tự phát hiện'.")
            return

        service = self.service_combo.currentText()
        api_key = self.api_key_input.text().strip()
        
        if service in ["Google Gemini", "OpenAI (ChatGPT)"] and not api_key:
            QMessageBox.warning(self, "Cảnh báo", f"Vui lòng nhập API Key cho {service}.")
            return

        max_len = self.max_len_spinbox.value()
        workers_chunk = self.workers_spinbox.value()
        workers_file = min(3, len(files))  # Tối đa 3 file song song
        custom_prompt = getattr(self, 'prompt_text', None)
        prompt = custom_prompt.toPlainText().strip() if custom_prompt else ""

        # Xóa kết quả cũ
        self.output_text.clear()
        self.translated_segments.clear()

        # Tạo và chạy batch worker
        self.batch_worker = BatchTranslateWorker(
            files, src, tgt, service, api_key, max_len, workers_chunk, workers_file, prompt
        )
        
        # Kết nối signals
        self.batch_worker.fileProgress.connect(self._update_progress)
        self.batch_worker.fileStatus.connect(self._add_log_item)
        self.batch_worker.attachWorker.connect(self._attach_batch_worker)
        
        # Cập nhật UI
        self.reset_button_Translate(False)
        self.stop_button.setEnabled(True)
        self._update_progress_title("Đang dịch hàng loạt...")
        
        # Bắt đầu worker
        self.batch_worker.start()

    def _on_segment_translated(self, original: str, translated: str, index: int) -> None:
        """Xử lý khi một đoạn được dịch xong"""
        self.translated_segments.append((original, translated, index))
        
        # Sắp xếp theo index để hiển thị đúng thứ tự
        self.translated_segments.sort(key=lambda x: x[2])
        
        # Cập nhật output
        self._update_output_text()
        

    def _update_output_text(self) -> None:
        """Cập nhật text output với tất cả đoạn đã dịch"""
        if not self.translated_segments:
            return
            
        output_lines = []
        for original, translated, index in self.translated_segments:
            # output_lines.append(f"=== Đoạn {index} ===")
            # output_lines.append(f"Gốc: {original}")
            output_lines.append(f"{translated}")
            output_lines.append("")  # Dòng trống
        
        self.output_text.setPlainText("\n".join(output_lines))

    def _attach_batch_worker(self, worker: MultiThreadTranslateWorker, filename: str) -> None:
        """Kết nối worker con của batch worker"""
        worker.segment_translated.connect(self._on_segment_translated)
        worker.progress.connect(self._update_progress)
        worker.status.connect(self._add_log_item)
        worker.all_done.connect(lambda: self._add_log_item(f"✅ Hoàn thành file: {filename}"))
        worker.error.connect(lambda e: self._add_log_item(f"❌ Lỗi file {filename}: {e}"))

    def stop_translation(self) -> None:
        """Dừng dịch thuật"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        if self.batch_worker and self.batch_worker.isRunning():
            self.batch_worker.stop()
        
        self.stop_button.setEnabled(False)
        self._add_log_item("⏹ Đã dừng dịch thuật")

    def clear_results(self) -> None:
        """Xóa kết quả dịch"""
        self.output_text.clear()
        self.translated_segments.clear()
        self._add_log_item("🗑️ Đã xóa kết quả")

    def _on_translation_complete(self) -> None:
        """Xử lý khi hoàn thành dịch thuật"""
        self.reset_button_Translate(True)
        self.stop_button.setEnabled(False)
        self._update_progress_title("")
        self._reset_progress()
        self._add_log_item("✅ Hoàn thành dịch thuật!")

    def _on_translation_error(self, error: str) -> None:
        """Xử lý khi có lỗi dịch thuật"""
        self.reset_button_Translate(True)
        self.stop_button.setEnabled(False)
        self._update_progress_title("")
        self._reset_progress()
        self._add_log_item(f"❌ Lỗi: {error}")

    def reset_button_Translate(self, flag) -> None:

        if flag:
            self.btn_translate.setEnabled(True)
            self.btn_translate.setText("🚀 Bắt đầu dịch")
            QApplication.restoreOverrideCursor()
        else:
            self.btn_translate.setEnabled(False)
            self.btn_translate.setText("Đang dịch…")
            QApplication.setOverrideCursor(Qt.WaitCursor)

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

    def closeEvent(self, event):
        """Handle tab close event - cleanup threads properly"""
        try:
            # Stop all workers
            if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
                self.worker.stop()
                if not self.worker.wait(3000):  # Wait max 3 seconds
                    self.worker.terminate()
                    self.worker.wait(1000)
                self.worker = None
            
            if hasattr(self, 'batch_worker') and self.batch_worker and self.batch_worker.isRunning():
                self.batch_worker.stop()
                if not self.batch_worker.wait(3000):
                    self.batch_worker.terminate()
                    self.batch_worker.wait(1000)
                self.batch_worker = None
                
            # Stop TTS worker - cải thiện cleanup
            if hasattr(self, 'tts_worker') and self.tts_worker:
                if self.tts_worker.isRunning():
                    self.tts_worker.stop()
                    # Đợi thread dừng hoàn toàn
                    if not self.tts_worker.wait(5000):  # Tăng timeout lên 5 giây
                        self.tts_worker.terminate()
                        self.tts_worker.wait(2000)
                    # Đảm bảo thread đã dừng
                    if self.tts_worker.isRunning():
                        self.tts_worker.terminate()
                        self.tts_worker.wait(1000)
                # Reset reference
                self.tts_worker = None
                
            # Clear thread pool
            if hasattr(self, 'thread_pool'):
                self.thread_pool.clear()
                
            # Dừng audio player nếu đang phát
            if hasattr(self, 'audio_player') and self.audio_player:
                self.audio_player.stop()
                
            # Xóa file audio tạm trước khi đóng
            self._cleanup_temp_audio_files()
                
        except Exception as e:
            print(f"Warning: Error in closeEvent: {e}")
        
        super().closeEvent(event)

    def get_thread_status(self) -> Dict[str, bool]:
        """Get status of all running threads"""
        status = {
            'main_worker': False,
            'batch_worker': False,
            'voice_loader': False
        }
        
        if hasattr(self, 'worker') and self.worker:
            status['main_worker'] = self.worker.isRunning()
            
        if hasattr(self, 'batch_worker') and self.batch_worker:
            status['batch_worker'] = self.batch_worker.isRunning()
            
        if hasattr(self, 'voice_loader') and self.voice_loader:
            status['voice_loader'] = self.voice_loader.isRunning()
            
        return status
    
    def is_any_thread_running(self) -> bool:
        """Check if any thread is currently running"""
        status = self.get_thread_status()
        return any(status.values())

    def _update_tts_progress(self, completed: int, total: int) -> None:
        """Cập nhật tiến trình tạo audio"""
        if completed == total:
            self.create_audio_btn.setEnabled(True)
            self.create_audio_btn.setText("🎵 Tạo Audio cho tất cả")
            self._add_log_item(f"✅ Hoàn thành tạo audio cho {total} đoạn văn bản!")

    def _clear_audio(self) -> None:
        """Xóa tất cả audio"""
        if self.audio_player:
            self.audio_player.clear_segments()
        
        # Reset danh sách audio
        self.audio_segments.clear()
        self.audio_durations.clear()
        
        # Cập nhật danh sách
        self._update_audio_list()
        
        # Dừng TTS worker nếu đang chạy
        if self.tts_worker and self.tts_worker.isRunning():
            self.tts_worker.stop()
            self.tts_worker.wait(3000)
            self.tts_worker = None
            
        # Xóa các file audio tạm
        self._cleanup_temp_audio_files()
        
        self._add_log_item("🗑️ Đã xóa tất cả audio")

    def _cleanup_temp_audio_files(self) -> None:
        pass
        """Xóa các file audio tạm"""
        # try:
        #     for audio_path in self.audio_segments:
        #         if audio_path and os.path.exists(audio_path):
        #             try:
        #                 os.remove(audio_path)
        #                 self._write_log_to_file(f"️ Đã xóa file audio: {audio_path}")
        #             except Exception as e:
        #                 self._write_log_to_file(f"⚠️ Không thể xóa file: {audio_path}, lỗi: {str(e)}")
        # except Exception as e:
        #     self._write_log_to_file(f"⚠️ Lỗi khi xóa file audio: {str(e)}")

    def _on_auto_play_toggled(self, checked: bool) -> None:
        """Xử lý khi checkbox auto play thay đổi"""
        self.auto_play_audio = checked
        if checked:
            self._add_log_item("🎵 Đã bật tự động phát audio")
        else:
            self._add_log_item("🔇 Đã tắt tự động phát audio")
    def _reset_read_buttons(self) -> None:
        """Reset trạng thái các nút đọc"""
        self.btn_read_source.setEnabled(True)
        self.btn_read_source.setText("🔊 Đọc văn bản nguồn")
        self.btn_read_target.setEnabled(True)
        self.btn_read_target.setText("🔊 Đọc văn bản đích")
        
        # Đánh dấu không còn phát audio
        if hasattr(self, 'is_playing_audio'):
            self.is_playing_audio = False

    def _read_source_text(self) -> None:
        """Đọc văn bản nguồn bằng TTS"""
        text = self.input_text.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Thông báo", "Vui lòng nhập văn bản cần đọc.")
            return
        
        # Lấy ngôn ngữ nguồn
        source_lang = self.source_lang_combo.currentText()
        
        # Nếu là "Tự phát hiện", tự động phát hiện ngôn ngữ
        if source_lang == "Tự phát hiện":
            try:
                detected_lang = detect(text)
                self._add_log_item(f"🔍 Đã phát hiện ngôn ngữ: {detected_lang}")
                tts_lang_code = self._convert_lang_code_for_tts(detected_lang)
            except Exception as e:
                self._add_log_item(f"❌ Không thể phát hiện ngôn ngữ: {str(e)}")
                tts_lang_code = "vi"
        else:
            tts_lang_code = code_by_name(source_lang)
        
        # Chia nhỏ văn bản và đọc từng phần
        self._read_text_in_chunks(text, tts_lang_code, "source")

    def _read_target_text(self) -> None:
        """Đọc văn bản đích bằng TTS"""
        text = self.output_text.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Thông báo", "Vui lòng dịch văn bản trước khi đọc.")
            return
        
        # Lấy ngôn ngữ đích
        target_lang = self.target_lang_combo.currentText()
        
        # Nếu là "Tự phát hiện", tự động phát hiện ngôn ngữ
        if target_lang == "Tự phát hiện":
            try:
                detected_lang = detect(text)
                self._add_log_item(f"🔍 Đã phát hiện ngôn ngữ: {detected_lang}")
                tts_lang_code = self._convert_lang_code_for_tts(detected_lang)
            except Exception as e:
                self._add_log_item(f"❌ Không thể phát hiện ngôn ngữ: {str(e)}")
                tts_lang_code = "en"
        else:
            tts_lang_code = code_by_name(target_lang)
        
        # Chia nhỏ văn bản và đọc từng phần
        self._read_text_in_chunks(text, tts_lang_code, "target")

    def _read_text_in_chunks(self, text: str, lang_code: str, text_type: str) -> None:
        """Chia nhỏ văn bản và đọc từng phần"""
        try:
            # Sử dụng hàm split_text có sẵn để chia văn bản
            chunks = split_text(text, max_len=300)
            
            if len(chunks) == 1:
                # Nếu chỉ có 1 đoạn, đọc trực tiếp
                self._create_and_play_tts_chunk(chunks[0], lang_code, text_type, 0, 1)
            else:
                # Nếu có nhiều đoạn, đọc tuần tự
                self._read_chunks_sequentially(chunks, lang_code, text_type)
                
        except Exception as e:
            self._add_log_item(f"❌ Lỗi khi chia văn bản: {str(e)}")
    def _create_and_play_tts_chunk(self, text: str, lang_code: str, text_type: str, 
                                   chunk_index: int, total_chunks: int) -> None:
        """Tạo và phát TTS cho một đoạn văn bản"""
        try:
            # Dừng TTS worker cũ nếu đang chạy
            if self.tts_worker and self.tts_worker.isRunning():
                self.tts_worker.stop()
                self.tts_worker.wait(3000)
            
            # Tạo TTS worker mới với một đoạn văn bản
            segments = [(text, text, chunk_index)]  # (original, translated, index)
            self.tts_worker = TranslateTTSWorker(segments, lang_code)
            
            # Kết nối signals
            self.tts_worker.audio_ready.connect(self._on_chunk_audio_ready)
            self.tts_worker.tts_error.connect(self._on_tts_error)
            self.tts_worker.tts_status.connect(self._add_log_item)
            
            # Bắt đầu TTS
            self.tts_worker.start()
            
            # Cập nhật UI
            if text_type == "source":
                self.btn_read_source.setEnabled(False)
                self.btn_read_source.setText(f"🔄 Đang tạo đoạn {chunk_index + 1}/{total_chunks}...")
            else:
                self.btn_read_target.setEnabled(False)
                self.btn_read_target.setText(f"🔄 Đang tạo đoạn {chunk_index + 1}/{total_chunks}...")
                
            self._add_log_item(f" Đang tạo audio cho đoạn {chunk_index + 1}/{total_chunks}...")
            
        except Exception as e:
            self._add_log_item(f"❌ Lỗi khi tạo TTS: {str(e)}")
            self._reset_read_buttons()

    def _read_chunks_sequentially(self, chunks: List[str], lang_code: str, text_type: str) -> None:
        """Đọc các đoạn văn bản tuần tự"""
        self.current_chunks = chunks
        self.current_chunk_index = 0
        self.current_lang_code = lang_code
        self.current_text_type = text_type
        
        # Tạo tất cả audio trước, sau đó phát tuần tự
        self._create_all_audio_chunks()

    def _write_log_to_file(self, message: str) -> None:
        """Ghi log vào file testtr.txt"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] {message}\n"
            
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(log_entry)
                
        except Exception as e:
            print(f"❌ Lỗi khi ghi log vào file: {str(e)}")

    def _create_all_audio_chunks(self) -> None:
        """Tạo tất cả audio chunks song song"""
        try:
            # Reset danh sách audio trước khi tạo mới
            self.audio_segments.clear()
            self.audio_durations.clear()
            
            # Ghi log bắt đầu
            self._write_log_to_file(f"🎵 Bắt đầu tạo {len(self.current_chunks)} đoạn audio cho {self.current_text_type}")
            self._write_log_to_file(f"   Ngôn ngữ: {self.current_lang_code}")
            
            # Ghi log từng đoạn text
            for i, chunk in enumerate(self.current_chunks):
                self._write_log_to_file(f"   Đoạn {i+1}: {chunk}")
            
            # Cập nhật UI
            if self.current_text_type == "source":
                self.btn_read_source.setEnabled(False)
                self.btn_read_source.setText(f" Đang tạo {len(self.current_chunks)} đoạn audio...")
            else:
                self.btn_read_target.setEnabled(False)
                self.btn_read_target.setText(f" Đang tạo {len(self.current_chunks)} đoạn audio...")
            
            self._add_log_item(f"🎵 Bắt đầu tạo {len(self.current_chunks)} đoạn audio...")
            
            # Tạo TTS worker cho tất cả chunks
            segments = []
            for i, chunk in enumerate(self.current_chunks):
                segments.append((chunk, chunk, i))
            
            # Dừng TTS worker cũ nếu đang chạy
            if self.tts_worker and self.tts_worker.isRunning():
                self.tts_worker.stop()
                self.tts_worker.wait(3000)
            
            # Tạo TTS worker mới cho tất cả segments
            self.tts_worker = TranslateTTSWorker(segments, self.current_lang_code)
            
            # Kết nối signals
            self.tts_worker.audio_ready.connect(self._on_chunk_audio_ready)
            self.tts_worker.tts_error.connect(self._on_tts_error)
            self.tts_worker.tts_status.connect(self._add_log_item)
            
            # Bắt đầu TTS
            self.tts_worker.start()
            
        except Exception as e:
            error_msg = f"❌ Lỗi khi tạo audio: {str(e)}"
            self._add_log_item(error_msg)
            self._write_log_to_file(error_msg)
            self._reset_read_buttons()

    def _on_chunk_audio_ready(self, audio_path: str, duration_ms: int, index: int) -> None:
        """Xử lý khi audio TTS sẵn sàng cho một đoạn"""
        try:
            # Khởi tạo audio player nếu chưa có
            if not self.audio_player:
                self.audio_player = AudioPlayer()
            
            # Kiểm tra xem audio này đã tồn tại chưa
            if index < len(self.audio_segments) and self.audio_segments[index]:
                self._add_log_item(f"⚠️ Đoạn {index + 1} đã tồn tại, bỏ qua")
                self._write_log_to_file(f"⚠️ Đoạn {index + 1} đã tồn tại, bỏ qua")
                return
            
            # Kiểm tra file audio có tồn tại không và có kích thước > 0
            if not os.path.exists(audio_path):
                error_msg = f"❌ File audio không tồn tại: {audio_path}"
                self._add_log_item(error_msg)
                self._write_log_to_file(error_msg)
                return
            
            # Kiểm tra file size
            file_size = os.path.getsize(audio_path)
            if file_size == 0:
                error_msg = f"❌ File audio rỗng (0 bytes): {audio_path}"
                self._add_log_item(error_msg)
                self._write_log_to_file(error_msg)
                return
            
            # Thêm audio vào danh sách theo đúng thứ tự
            while len(self.audio_segments) <= index:
                self.audio_segments.append("")
                self.audio_durations.append(0)
            
            self.audio_segments[index] = audio_path
            self.audio_durations[index] = duration_ms
            
            # Lấy text của đoạn này
            current_text = self.current_chunks[index] if index < len(self.current_chunks) else "Unknown"
            
            # Ghi log vào file
            self._write_log_to_file(f"✅ Đã tạo xong đoạn {index + 1}/{len(self.current_chunks)}")
            self._write_log_to_file(f"   Text: {current_text}")
            self._write_log_to_file(f"   Audio path: {audio_path}")
            self._write_log_to_file(f"   Duration: {duration_ms}ms")
            self._write_log_to_file(f"   File size: {file_size} bytes")
            
            self._add_log_item(f"✅ Đã tạo xong đoạn {index + 1}/{len(self.current_chunks)}")
            
            # Cập nhật danh sách audio
            self._update_audio_list()
            
            # Kiểm tra xem đã tạo xong tất cả chưa
            completed_count = len([p for p in self.audio_segments if p])
            if completed_count == len(self.current_chunks):
                # Đã tạo xong tất cả, bắt đầu phát
                self._add_log_item(f" Đã tạo xong tất cả {completed_count} đoạn, bắt đầu phát!")
                self._write_log_to_file(f" Đã tạo xong tất cả {completed_count} đoạn, bắt đầu phát!")
                self._start_playing_all_chunks()
            
        except Exception as e:
            error_msg = f"❌ Lỗi khi xử lý audio: {str(e)}"
            self._add_log_item(error_msg)
            self._write_log_to_file(error_msg)

    def _start_playing_all_chunks(self) -> None:
        """Bắt đầu phát tất cả chunks tuần tự"""
        try:
            # Cập nhật audio player với tất cả segments
            self.audio_player.add_segments(self.audio_segments, self.audio_durations)
            
            # Đảm bảo volume đủ lớn
            if hasattr(self.audio_player, 'audio_output'):
                self.audio_player.audio_output.setVolume(0.8)  # Set volume 80%
                self.audio_player.audio_output.setMuted(False)  # Đảm bảo không bị mute
            
            # Kết nối signal để biết khi nào audio phát xong
            if hasattr(self.audio_player, 'playback_state_changed'):
                self.audio_player.playback_state_changed.connect(self._on_playback_state_changed)
            
            # Bắt đầu phát từ đoạn đầu tiên
            self.current_play_index = 0
            self._play_next_chunk()
            
            # Cập nhật UI
            if self.current_text_type == "source":
                self.btn_read_source.setText("🎵 Đang phát...")
            else:
                self.btn_read_target.setText("🎵 Đang phát...")
                
            self._add_log_item("🎵 Bắt đầu phát tất cả đoạn audio!")
            self._write_log_to_file("🎵 Bắt đầu phát tất cả đoạn audio!")
            
        except Exception as e:
            self._add_log_item(f"❌ Lỗi khi bắt đầu phát: {str(e)}")
            self._write_log_to_file(f"❌ Lỗi khi bắt đầu phát: {str(e)}")
            self._reset_read_buttons()

    def _play_next_chunk(self) -> None:
        """Phát đoạn audio tiếp theo"""
        if self.current_play_index >= len(self.audio_segments):
            # Đã phát xong tất cả
            self._add_log_item("🎵 Đã phát xong tất cả đoạn audio!")
            self._write_log_to_file("🎵 Đã phát xong tất cả đoạn audio!")
            self._reset_read_buttons()
            return
        
        try:
            # Hiển thị text đang được đọc
            current_text = self.current_chunks[self.current_play_index]
            print(f"current_text: {current_text}")
            
            # Ghi log vào file
            self._write_log_to_file(f"🔊 Đang đọc đoạn {self.current_play_index + 1}/{len(self.current_chunks)}: {current_text}")
            
            self._add_log_item(f"🔊 Đang đọc đoạn {self.current_play_index + 1}/{len(self.current_chunks)}: {current_text[:100]}{'...' if len(current_text) > 100 else ''}")
            
            # Kiểm tra file audio có tồn tại không
            audio_path = self.audio_segments[self.current_play_index]
            if not os.path.exists(audio_path):
                self._add_log_item(f"❌ File audio không tồn tại: {audio_path}")
                self._write_log_to_file(f"❌ File audio không tồn tại: {audio_path}")
                # Bỏ qua đoạn này và chuyển sang đoạn tiếp theo
                self.current_play_index += 1
                self._play_next_chunk()
                return
            
            # Kiểm tra file size
            file_size = os.path.getsize(audio_path)
            if file_size == 0:
                self._add_log_item(f"❌ File audio rỗng: {audio_path}")
                self._write_log_to_file(f"❌ File audio rỗng: {audio_path}")
                # Bỏ qua đoạn này và chuyển sang đoạn tiếp theo
                self.current_play_index += 1
                self._play_next_chunk()
                return
            
            # Dừng audio hiện tại nếu đang phát
            if self.audio_player and hasattr(self.audio_player, 'stop'):
                self.audio_player.stop()
            
            # Phát đoạn hiện tại
            self.audio_player.play_segment(self.current_play_index)
            
            # Lấy thời lượng của đoạn hiện tại
            duration = self.audio_durations[self.current_play_index]
            
            # Ghi log thông tin phát
            self._write_log_to_file(f"   Phát file: {audio_path}")
            self._write_log_to_file(f"   Thời lượng: {duration}ms")
            self._write_log_to_file(f"   File size: {file_size} bytes")
            
            # Lên lịch phát đoạn tiếp theo sau khi audio hiện tại phát xong
            # Thêm buffer 1 giây để đảm bảo audio phát xong hoàn toàn
            QTimer.singleShot(duration + 1000, self._play_next_chunk)
            
        except Exception as e:
            error_msg = f"❌ Lỗi khi phát đoạn {self.current_play_index + 1}: {str(e)}"
            self._add_log_item(error_msg)
            self._write_log_to_file(error_msg)
            # Bỏ qua đoạn này và chuyển sang đoạn tiếp theo
            self.current_play_index += 1
            self._play_next_chunk()

    def _on_playback_state_changed(self, is_playing: bool) -> None:
        """Xử lý khi trạng thái phát audio thay đổi"""
        try:
            if not is_playing:
                # Audio đã dừng (phát xong hoặc bị dừng)
                # Chuyển sang đoạn tiếp theo
                self.current_play_index += 1
                self._play_next_chunk()
                
        except Exception as e:
            error_msg = f"❌ Lỗi khi xử lý trạng thái phát: {str(e)}"
            self._add_log_item(error_msg)
            self._write_log_to_file(error_msg)

    def _convert_lang_code_for_tts(self, detected_lang: str) -> str:
        """Chuyển đổi mã ngôn ngữ phát hiện thành mã TTS phù hợp"""
        # Mapping từ mã ngôn ngữ phát hiện sang mã TTS
        lang_mapping = {
            'vi': 'vi',      # Tiếng Việt
            'en': 'en',      # Tiếng Anh
            'ja': 'ja',      # Tiếng Nhật
            'zh': 'zh-CN',   # Tiếng Trung
            'ko': 'ko',      # Tiếng Hàn
            'fr': 'fr',      # Tiếng Pháp
            'de': 'de',      # Tiếng Đức
            'es': 'es',      # Tiếng Tây Ban Nha
            'pt': 'pt',      # Tiếng Bồ Đào Nha
            'th': 'th',      # Tiếng Thái
            'ru': 'ru',      # Tiếng Nga
            'it': 'it',      # Tiếng Ý
        }
        
        # Lấy mã TTS tương ứng, nếu không có thì dùng mã gốc
        return lang_mapping.get(detected_lang, detected_lang)

    def _on_tts_error(self, error: str) -> None:
        """Xử lý khi có lỗi TTS"""
        error_msg = f"❌ Lỗi TTS: {error}"
        self._add_log_item(error_msg)
        self._write_log_to_file(error_msg)
        self._reset_read_buttons()

    def _create_audio_list_section(self, content_layout: QVBoxLayout) -> None:
        """Tạo phần hiển thị danh sách file audio"""
        # Container cho audio list
        audio_list_container = QWidget()
        audio_list_layout = QVBoxLayout()
        audio_list_layout.setContentsMargins(0, 0, 0, 0)
        
        # Label tiêu đề
        audio_list_label = QLabel("📁 Danh sách file audio đã tạo:")
        audio_list_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 14px;
                color: #333;
                padding: 5px;
            }
        """)
        audio_list_layout.addWidget(audio_list_label)
        
        # List widget để hiển thị file
        self.audio_list_widget = QTableWidget()
        self.audio_list_widget.setColumnCount(4)
        self.audio_list_widget.setHorizontalHeaderLabels(["STT", "File", "Thời lượng", "Trạng thái"])
        self.audio_list_widget.setMinimumHeight(150)
        self.audio_list_widget.setMaximumHeight(200)
        
        # Thiết lập cột
        header = self.audio_list_widget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # STT
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # File
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Thời lượng
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Trạng thái
        
        self.audio_list_widget.setColumnWidth(0, 50)   # STT
        self.audio_list_widget.setColumnWidth(2, 100)  # Thời lượng
        self.audio_list_widget.setColumnWidth(3, 100)  # Trạng thái
        
        audio_list_layout.addWidget(self.audio_list_widget)
        
        # Buttons cho audio list
        audio_buttons_layout = QHBoxLayout()
        
        # Nút thêm vào file
        self.btn_add_to_file = QPushButton("💾 Thêm vào file")
        self.btn_add_to_file.clicked.connect(self._add_audio_to_file)
        self.btn_add_to_file.setObjectName("btn_style_1")
        self.btn_add_to_file.setEnabled(False)  # Chỉ enable khi có audio
        
        # Nút xóa danh sách
        self.btn_clear_audio_list = QPushButton("🗑️ Xóa danh sách")
        self.btn_clear_audio_list.clicked.connect(self._clear_audio_list)
        self.btn_clear_audio_list.setObjectName("btn_style_2")
        
        # Nút mở thư mục chứa audio
        self.btn_open_audio_folder = QPushButton("📂 Mở thư mục")
        self.btn_open_audio_folder.clicked.connect(self._open_audio_folder)
        self.btn_open_audio_folder.setObjectName("btn_style_1")
        
        audio_buttons_layout.addWidget(self.btn_add_to_file)
        audio_buttons_layout.addWidget(self.btn_clear_audio_list)
        audio_buttons_layout.addWidget(self.btn_open_audio_folder)
        audio_buttons_layout.addStretch()
        
        audio_list_layout.addLayout(audio_buttons_layout)
        
        # Đặt layout cho container
        audio_list_container.setLayout(audio_list_layout)
        
        # Thêm vào content layout
        content_layout.addWidget(audio_list_container)

    def _update_audio_list(self) -> None:
        """Cập nhật danh sách file audio"""
        try:
            self.audio_list_widget.setRowCount(0)  # Xóa tất cả rows cũ
            
            if not self.audio_segments:
                self.btn_add_to_file.setEnabled(False)
                return
            
            # Thêm từng file audio vào list
            for i, (audio_path, duration) in enumerate(zip(self.audio_segments, self.audio_durations)):
                if not audio_path:
                    continue
                    
                # Tạo row mới
                row = self.audio_list_widget.rowCount()
                self.audio_list_widget.insertRow(row)
                
                # STT
                stt_item = QTableWidgetItem(str(i + 1))
                stt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.audio_list_widget.setItem(row, 0, stt_item)
                
                # Tên file
                filename = os.path.basename(audio_path)
                file_item = QTableWidgetItem(filename)
                file_item.setToolTip(audio_path)  # Hiển thị đường dẫn đầy đủ khi hover
                self.audio_list_widget.setItem(row, 1, file_item)
                
                # Thời lượng
                duration_text = f"{duration//1000}s" if duration > 0 else "N/A"
                duration_item = QTableWidgetItem(duration_text)
                duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.audio_list_widget.setItem(row, 2, duration_item)
                
                # Trạng thái
                status = "✅ Sẵn sàng" if os.path.exists(audio_path) else "❌ Lỗi"
                status_item = QTableWidgetItem(status)
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.audio_list_widget.setItem(row, 3, status_item)
            
            # Enable nút thêm vào file nếu có audio
            self.btn_add_to_file.setEnabled(len(self.audio_segments) > 0)
            
        except Exception as e:
            self._add_log_item(f"❌ Lỗi khi cập nhật danh sách audio: {str(e)}")

    def _add_audio_to_file(self) -> None:
        """Thêm danh sách audio vào file"""
        try:
            if not self.audio_segments:
                QMessageBox.information(self, "Thông báo", "Không có file audio nào để thêm vào file.")
                return
            
            # Chọn nơi lưu file
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Lưu danh sách audio", "audio_list.txt", 
                "Text files (*.txt);;All files (*)"
            )
            
            if not file_path:
                return
            
            # Ghi danh sách audio vào file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"Danh sách file audio - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")
                
                for i, (audio_path, duration) in enumerate(zip(self.audio_segments, self.audio_durations)):
                    if not audio_path:
                        continue
                        
                    filename = os.path.basename(audio_path)
                    duration_text = f"{duration//1000}s" if duration > 0 else "N/A"
                    status = "✅ Sẵn sàng" if os.path.exists(audio_path) else "❌ Lỗi"
                    
                    f.write(f"{i+1:2d}. {filename}\n")
                    f.write(f"    Đường dẫn: {audio_path}\n")
                    f.write(f"    Thời lượng: {duration_text}\n")
                    f.write(f"    Trạng thái: {status}\n")
                    f.write(f"    Kích thước: {os.path.getsize(audio_path) if os.path.exists(audio_path) else 'N/A'} bytes\n")
                    f.write("\n")
            
            self._add_log_item(f"✅ Đã lưu danh sách audio vào: {file_path}")
            QMessageBox.information(self, "Thành công", f"Đã lưu danh sách {len(self.audio_segments)} file audio vào:\n{file_path}")
            
        except Exception as e:
            error_msg = f"❌ Lỗi khi lưu danh sách audio: {str(e)}"
            self._add_log_item(error_msg)
            QMessageBox.critical(self, "Lỗi", error_msg)

    def _clear_audio_list(self) -> None:
        """Xóa danh sách audio"""
        try:
            self.audio_list_widget.setRowCount(0)
            self.audio_segments.clear()
            self.audio_durations.clear()
            
            if self.audio_player:
                self.audio_player.clear_segments()
            
            self.btn_add_to_file.setEnabled(False)
            self._add_log_item("🗑️ Đã xóa danh sách audio")
            
        except Exception as e:
            self._add_log_item(f"❌ Lỗi khi xóa danh sách audio: {str(e)}")

    def _open_audio_folder(self) -> None:
        """Mở thư mục chứa file audio"""
        try:
            if not self.audio_segments:
                QMessageBox.information(self, "Thông báo", "Không có file audio nào.")
                return
            
            # Lấy thư mục của file audio đầu tiên
            first_audio = self.audio_segments[0]
            if first_audio and os.path.exists(first_audio):
                folder_path = os.path.dirname(first_audio)
                
                # Mở thư mục trong file explorer
                if os.name == 'nt':  # Windows
                    os.startfile(folder_path)
                elif os.name == 'posix':  # macOS/Linux
                    import subprocess
                    subprocess.run(['open', folder_path] if os.name == 'darwin' else ['xdg-open', folder_path])
                
                self._add_log_item(f"📂 Đã mở thư mục: {folder_path}")
            else:
                QMessageBox.warning(self, "Cảnh báo", "Không thể xác định thư mục chứa file audio.")
                
        except Exception as e:
            self._add_log_item(f"❌ Lỗi khi mở thư mục: {str(e)}")