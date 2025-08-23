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
        self._setup_ui()
        # "Google Translate" #Google Gemini, OpenAI (ChatGPT)
        default_service = "Google Translate"
        self.service_combo.setCurrentText(default_service)
        self._on_service_changed(default_service)

    def _initialize_state_variables(self) -> None:
        # Thêm worker và các biến trạng thái
        self.worker: Optional[MultiThreadTranslateWorker] = None
        self.batch_worker: Optional[BatchTranslateWorker] = None
        self.translated_segments: List[Tuple[str, str, int]] = []  # (original, translated, index)
        self.is_batch_mode = False
        
        # Thread management
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(10)  # Tối đa 10 thread
        

        
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
        
        # Thêm nút đọc văn bản nguồn
        input_button_layout = QHBoxLayout()
        self.read_source_btn = QPushButton("🔊 Đọc văn bản nguồn")
        # self.read_source_btn.clicked.connect(self._read_source_text)
        self.read_source_btn.setObjectName("btn_style_1")
        input_button_layout.addWidget(self.read_source_btn)

        input_button_layout.addStretch()
        
        input_layout.addWidget(self.input_text)
        input_layout.addLayout(input_button_layout)
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
        input_button_layout_target = QHBoxLayout()
        self.read_target_btn = QPushButton("🔊 Đọc văn bản đích")
        self.read_target_btn.setObjectName("btn_style_1")
        input_button_layout_target.addWidget(self.read_target_btn)
        input_button_layout_target.addStretch()
        output_layout.addWidget(self.output_text)
        output_layout.addLayout(input_button_layout_target)
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
        
        # Dừng phát audio nếu đang phát
        if hasattr(self, 'audio_player') and self.audio_player:
            try:
                self.audio_player.stop()
            except:
                pass
        
        # Dừng phát tuần tự
        if hasattr(self, 'is_playing_sequence'):
            self.is_playing_sequence = False
        
        # Dừng TTS worker nếu đang chạy
        if hasattr(self, 'tts_worker') and self.tts_worker and self.tts_worker.isRunning():
            try:
                self.tts_worker.stop()
                self.tts_worker.wait(3000)
            except:
                pass
        
        # Reset trạng thái các nút đọc
        self._reset_read_buttons()
        
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


    def closeEvent(self, event):
        """Handle tab close event - cleanup threads properly"""
        try:
            # Dừng phát audio nếu đang phát
            if hasattr(self, 'is_playing_sequence') and self.is_playing_sequence:
                self.is_playing_sequence = False
            
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
                try:
                    self.audio_player.stop()
                except:
                    pass
                
            # Xóa file audio tạm trước khi đóng
            self._cleanup_temp_audio_files()
                
        except Exception as e:
            print(f"Warning: Error in closeEvent: {e}")
        
        super().closeEvent(event)

    
 

    def _write_log_to_file(self, message: str) -> None:
        """Ghi log vào file testtr.txt"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] {message}\n"
            
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(log_entry)
                
        except Exception as e:
            print(f"❌ Lỗi khi ghi log vào file: {str(e)}")
