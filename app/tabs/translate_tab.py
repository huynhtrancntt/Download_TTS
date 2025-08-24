from PySide6.QtWidgets import (QApplication,
                               QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
                               QLabel, QTextEdit, QComboBox, QSpinBox,
                               QMessageBox, QFileDialog, QCheckBox, QGroupBox, QLineEdit,
                               QTableWidget, QTableWidgetItem, QHeaderView, QListWidget
                               )
from PySide6.QtCore import Qt, QTimer, QThreadPool

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
from app.workers.TTS_workers import MTProducerWorker
from app.core.segment_manager import SegmentManager
from app.core.voices_data import voices_data
from app.core.language_manager import language_manager

from app.utils.helps import clean_all_temp_parts

# Các hàm helper đã được di chuyển sang language_manager
# Sử dụng language_manager.code_by_name() và language_manager.name_by_code()


class TranslateTab(UIToolbarTab):
    """
    Tab Convert đơn giản để minh họa việc áp dụng HistoryPanel cho mỗi tab
    """

    def __init__(self, parent_main: QWidget) -> None:
        super().__init__(parent_main)
        self._initialize_state_variables()
        self._setup_ui()
        self._setup_history()
        # "Google Translate" #Google Gemini, OpenAI (ChatGPT)
        default_service = "Google Translate"
        self.service_combo.setCurrentText(default_service)
        self._on_service_changed(default_service)
        
        # Đồng bộ TTS combobox với ngôn ngữ dịch ban đầu
        # Delay một chút để đảm bảo UI đã được thiết lập hoàn toàn
        QTimer.singleShot(100, self._sync_tts_with_translation_languages)

    def _initialize_state_variables(self) -> None:
        # Thêm worker và các biến trạng thái
        self.worker: Optional[MultiThreadTranslateWorker] = None
        self.batch_worker: Optional[BatchTranslateWorker] = None
        self.translated_segments: List[Tuple[str, str, int]] = []  # (original, translated, index)
        self.is_batch_mode = False
        
        # Language management
        self.languages = language_manager.get_available_languages()
        
        # Thread management
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(10)  # Tối đa 10 thread
        
        # Audio system
        self.audio_player: Optional[AudioPlayer] = None
        self.tts_worker: Optional[MTProducerWorker] = None
        self.is_playing_sequence = False
        self.current_index: int = -1  # Thêm current_index
        
        # TTS reading states
        self.is_reading_source: bool = False
        self.is_reading_target: bool = False
        
        # Log file
        self.log_file_path = "testtr.txt"

        # Segment management
        self.segment_manager = SegmentManager()

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
        
        # Setup audio system
        self._setup_audio_system()

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
        
        # Add segment manager UI
        self._create_segment_manager_section(content_layout)
        
        root_layout.addLayout(content_layout)

    def _setup_bottom_section(self, root_layout: QVBoxLayout) -> None:
        """Thiết lập phần bottom của tab"""
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(2, 2, 2, 2)
        self._create_btn_downloadvideo(bottom_layout)
        root_layout.addLayout(bottom_layout)

    def _setup_audio_system(self) -> None:
        """Setup audio system for text reading"""
        # Create AudioPlayer
        self.audio_player = AudioPlayer()
        
        # Connect audio player signals
        if self.audio_player:
            self.audio_player.position_changed.connect(self._on_audio_position_changed)
            self.audio_player.segment_changed.connect(self._on_audio_segment_changed)
            self.audio_player.playback_state_changed.connect(self._on_audio_playback_state_changed)
            self.audio_player.status_signal.connect(self._on_audio_status_changed)
        # Setup segment manager after audio player is created
        self._setup_segment_manager()

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
        self.input_text.setPlaceholderText("Nhập văn bản cần dịch vào đây... (Bấm Enter để dịch, Shift+Enter để xuống dòng)")
        # Kết nối signal textChanged để clear dữ liệu đích khi văn bản nguồn thay đổi
        self.input_text.textChanged.connect(self._on_source_text_changed)
        # Kết nối signal returnPressed để dịch khi bấm Enter
        self.input_text.installEventFilter(self)
        
        # Thêm nút đọc văn bản nguồn và combobox ngôn ngữ
        input_button_layout = QHBoxLayout()
        self.read_source_btn = QPushButton("🔊 Đọc văn bản nguồn")
        self.read_source_btn.clicked.connect(self._read_source_text)
        self.read_source_btn.setObjectName("btn_style_1")
        input_button_layout.addWidget(self.read_source_btn)
        
        # Combobox chọn voice cho văn bản nguồn
        self.source_tts_lang_combo = QComboBox()
        self.source_tts_lang_combo.setFixedWidth(150)
        self.source_tts_lang_combo.setFixedHeight(30)
        self.source_tts_lang_combo.setCurrentText("Tự phát hiện")
        # Populate voices khi khởi tạo
        # Delay để đảm bảo combobox đã được thiết lập
        QTimer.singleShot(50, self._populate_source_voices)
        input_button_layout.addWidget(self.source_tts_lang_combo)

        input_button_layout.addStretch()
        
        # Thêm text hiển thị số từ và ký tự cho input
        self.input_word_count_label = QLabel("")
        self.input_word_count_label.setStyleSheet("color: #64748b; font-size: 12px; margin-top: 5px; text-align: right;")
        self.input_word_count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.input_word_count_label.setTextFormat(Qt.TextFormat.RichText)
        input_layout.addWidget(self.input_text)
        input_layout.addWidget(self.input_word_count_label)
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
        
        # Thêm text hiển thị số từ và ký tự cho output
        self.output_word_count_label = QLabel("")
        self.output_word_count_label.setStyleSheet("color: #64748b; font-size: 12px; margin-top: 5px; text-align: right;")
        self.output_word_count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.output_word_count_label.setTextFormat(Qt.TextFormat.RichText)
        input_button_layout_target = QHBoxLayout()
        self.read_target_btn = QPushButton("🔊 Đọc văn bản đích")
        self.read_target_btn.clicked.connect(self._read_target_text)
        self.read_target_btn.setObjectName("btn_style_1")
        input_button_layout_target.addWidget(self.read_target_btn)
        
        # Combobox chọn voice cho văn bản đích
        self.target_tts_lang_combo = QComboBox()

        self.target_tts_lang_combo.setFixedHeight(30)
        self.target_tts_lang_combo.setCurrentText("Tự phát hiện")
        # Populate voices khi khởi tạo
        # Delay để đảm bảo combobox đã được thiết lập
        QTimer.singleShot(50, self._populate_target_voices)
        input_button_layout_target.addWidget(self.target_tts_lang_combo)
        
        input_button_layout_target.addStretch()
        output_layout.addWidget(self.output_text)
        output_layout.addWidget(self.output_word_count_label)
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
        service_label.setFixedWidth(120)  # Đặt độ rộng cố định cho label
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
        source_label.setFixedWidth(120)
        second_row.addWidget(source_label)

        # Cột 2: Combobox Ngôn ngữ nguồn
        self.source_lang_combo = QComboBox()
        # Sử dụng self.languages đã được khởi tạo
        self.source_lang_combo.addItems([n for n, _ in self.languages])
        self.source_lang_combo.setFixedHeight(30)
        # Đặt độ rộng cố định giống service_combo
        self.source_lang_combo.setFixedWidth(150)
        # Đặt ngôn ngữ nguồn mặc định là Tự phát hiện
        self.source_lang_combo.setCurrentText("Tự phát hiện")
        # Kết nối signal để tự động cập nhật TTS combobox
        self.source_lang_combo.currentTextChanged.connect(self._on_source_lang_changed)
        second_row.addWidget(self.source_lang_combo)

        # Cột 3: Label Ngôn ngữ đích
        target_label = QLabel("Ngôn ngữ đích:")
        target_label.setFixedWidth(120)  # Đặt độ rộng cố định giống api_label
        second_row.addWidget(target_label)

        # Cột 4: Combobox Ngôn ngữ đích
        self.target_lang_combo = QComboBox()
        # Sử dụng self.languages đã được khởi tạo
        self.target_lang_combo.addItems([n for n, _ in self.languages])
        self.target_lang_combo.setCurrentText("Tiếng Anh")
        self.target_lang_combo.setFixedWidth(150)
        # Kết nối signal để tự động cập nhật TTS combobox
        self.target_lang_combo.currentTextChanged.connect(self._on_target_lang_changed)
        second_row.addWidget(self.target_lang_combo)

        second_row.addStretch()  # Đẩy sang trái
        parent_layout.addLayout(second_row)

        # Hàng 3: Batch mode và các tham số
        third_row = QHBoxLayout()
        
        # Cột 2: Label Max Length
        max_len_label = QLabel("Độ dài tối đa:")
        max_len_label.setFixedWidth(120)
        third_row.addWidget(max_len_label)
        
        # Cột 3: Spinbox Max Length
        self.max_len_spinbox = QSpinBox()
        self.max_len_spinbox.setRange(100, 4000)
        self.max_len_spinbox.setValue(AppConfig.DEFAULT_MAXLEN)
        self.max_len_spinbox.setFixedHeight(30)
        self.max_len_spinbox.setFixedWidth(150)
        self.max_len_spinbox.setSuffix(" ký tự")
        third_row.addWidget(self.max_len_spinbox)
        third_row.addStretch()
        
        # Cột 5: Spinbox Workers
        self.workers_spinbox = QSpinBox()
        self.workers_spinbox.setRange(1, 16)
        self.workers_spinbox.setValue(AppConfig.DEFAULT_WORKERS_PLAYER)
        self.workers_spinbox.setSuffix(" Thread")
        self.workers_spinbox.setFixedHeight(30)
        self.workers_spinbox.setFixedWidth(200)
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

    def _create_segment_manager_section(self, content_layout: QVBoxLayout) -> None:
        """Create segment manager UI section with timing display"""
        # Create group box for segment manager
        self.segment_manager_group = QGroupBox("🎵 Quản lý Audio Segments")
        self.segment_manager_group.setFixedHeight(200)
        self.segment_manager_layout = QVBoxLayout()
        
        # Header with timing information
        header_layout = QHBoxLayout()
        
        # Total duration label
        self.total_duration_label = QLabel("Tổng thời lượng: 00:00")
        self.total_duration_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        header_layout.addWidget(self.total_duration_label)
        
        header_layout.addStretch()
        
        # Segment count label
        self.segment_count_label = QLabel("Số segments: 0")
        self.segment_count_label.setStyleSheet("font-size: 11px; color: #666;")
        header_layout.addWidget(self.segment_count_label)
        
        self.segment_manager_layout.addLayout(header_layout)
        
        # Segment list widget
        self.segment_list = QListWidget()
        self.segment_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.segment_list.itemClicked.connect(self._on_segment_list_item_clicked)
        self.segment_list.itemDoubleClicked.connect(self._on_segment_list_item_double_clicked)
        self.segment_manager_layout.addWidget(self.segment_list)
        
        # Control buttons for segments
        segment_controls = QHBoxLayout()
        
        self.play_segments_btn = QPushButton("▶️ Phát tất cả")
        self.play_segments_btn.clicked.connect(self._play_all_segments)
        self.play_segments_btn.setObjectName("btn_style_1")
        # segment_controls.addWidget(self.play_segments_btn)
        
        self.stop_segments_btn = QPushButton("⏹️ Dừng")
        self.stop_segments_btn.clicked.connect(self._stop_segments_playback)
        self.stop_segments_btn.setObjectName("btn_style_2")
        # segment_controls.addWidget(self.stop_segments_btn)
        
        self.clear_segments_btn = QPushButton("🗑️ Xóa tất cả")
        self.clear_segments_btn.clicked.connect(self._clear_all_segments)
        self.clear_segments_btn.setObjectName("btn_style_2")
        # segment_controls.addWidget(self.clear_segments_btn)
        
        segment_controls.addStretch()
        # self.segment_manager_layout.addLayout(segment_controls)
        
        self.segment_manager_group.setLayout(self.segment_manager_layout)
        # Ẩn section mặc định khi khởi tạo
        self.segment_manager_group.setVisible(False)
        content_layout.addWidget(self.segment_manager_group)

    def _setup_segment_manager(self) -> None:
        """Setup segment manager with UI components"""
        try:
            if hasattr(self, 'segment_manager') and self.segment_manager:
                self.segment_manager.set_ui_components(self.segment_list, self.audio_player)
                
                # Connect segment manager signals
                self.segment_manager.segments_changed.connect(self._update_segment_display)
                self.segment_manager.segment_added.connect(self._on_segment_added)
                self.segment_manager.segment_removed.connect(self._on_segment_removed)
                
                # Initial display update
                self._update_segment_display()
                
        except Exception as e:
            print(f"Error setting up segment manager: {e}")
            self._add_log_item(f"❌ Lỗi khi thiết lập segment manager: {e}", "error")

    def _on_segment_list_item_clicked(self, item) -> None:
        """Handle single click on segment list item - play the selected segment"""
        try:
            # Get the row index
            row = self.segment_list.row(item)
            if row >= 0:
                # Highlight the selected segment
                self.segment_list.setCurrentRow(row)
                
                # Play the selected segment
                if self.audio_player and hasattr(self, 'segment_manager') and self.segment_manager:
                    valid_paths, valid_durations = self.segment_manager.get_valid_segments()
                    if row < len(valid_paths) and valid_paths[row]:
                        # Stop current playback
                        self.audio_player.stop()
                        
                        # Add all segments to audio player (để có thể chuyển segment)
                        self.audio_player.add_segments(valid_paths, valid_durations)
                        
                        # Play from the selected segment
                        self.audio_player.play_segment(row, 0)
                        
                        segment_name = os.path.basename(valid_paths[row])
                        self._add_log_item(f"▶️ Phát segment {row + 1}: {segment_name}", "info")
                        
                print(f"Playing segment row: {row}")
        except Exception as e:
            print(f"Error handling segment click: {e}")
            self._add_log_item(f"❌ Lỗi khi phát segment: {e}", "error")

    def _on_segment_list_item_double_clicked(self, item) -> None:
        """Handle double click on segment list item"""
        try:
            # Get the row index
            row = self.segment_list.row(item)
            if row >= 0:
                # Could add functionality like playing specific segment
                print(f"Double clicked segment row: {row}")
                # Example: play specific segment
                # if self.audio_player and hasattr(self, 'segment_manager'):
                #     valid_paths, valid_durations = self.segment_manager.get_valid_segments()
                #     if row < len(valid_paths):
                #         self.audio_player.add_segments([valid_paths[row]], [valid_durations[row]])
                #         self.audio_player.play()
        except Exception as e:
            print(f"Error handling segment double click: {e}")

    def _on_segment_added(self, path: str, duration: int) -> None:
        """Handle when a new segment is added"""
        self._update_segment_display()
        self._add_log_item(f"✅ Đã thêm segment: {os.path.basename(path)} ({duration}ms)", "info")

    def _on_segment_removed(self, index: int) -> None:
        """Handle when a segment is removed"""
        self._update_segment_display()
        self._add_log_item(f"🗑️ Đã xóa segment {index + 1}", "info")

    def _update_segment_display(self) -> None:
        """Update segment display information"""
        try:
            if hasattr(self, 'segment_manager') and self.segment_manager:
                stats = self.segment_manager.get_segments_statistics()
                
                # Update segment count in the group box title
                if hasattr(self, 'segment_manager_group'):
                    self.segment_manager_group.setTitle(f"🎵 Quản lý Audio Segments ({stats['total_segments']} segments)")
                
                # Update timing labels
                if stats['total_duration'] > 0:
                    total_seconds = stats['total_duration'] / 1000
                    
                    # Tính giờ, phút, giây
                    hours = int(total_seconds // 3600)
                    minutes = int((total_seconds % 3600) // 60)
                    seconds = int(total_seconds % 60)
                    
                    # Format thời gian
                    if hours > 0:
                        total_duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    else:
                        total_duration_str = f"{minutes:02d}:{seconds:02d}"
                    
                    self.total_duration_label.setText(f"Tổng thời lượng: {total_duration_str}")
                else:
                    self.total_duration_label.setText("Tổng thời lượng: 00:00")
                
                self.segment_count_label.setText(f"Số segments: {stats['total_segments']}")
                
        except Exception as e:
            print(f"Error updating segment display: {e}")
            # Fallback display
            try:
                if hasattr(self, 'total_duration_label'):
                    self.total_duration_label.setText("Tổng thời lượng: 00:00")
                if hasattr(self, 'segment_count_label'):
                    self.segment_count_label.setText("Số segments: 0")
                if hasattr(self, 'segment_manager_group'):
                    self.segment_manager_group.setTitle("🎵 Quản lý Audio Segments (0 segments)")
            except Exception as fallback_error:
                print(f"Fallback display error: {fallback_error}")

    def _add_segment_to_manager(self, text: str, segment_type: str = "text") -> None:
        """Add a text segment to the segment manager"""
        try:
            if hasattr(self, 'segment_manager') and self.segment_manager:
                # For text segments, we'll create a placeholder
                # In a real implementation, you might want to create audio files
                self.segment_manager.add_custom_row(
                    f"Segment {len(self.segment_manager.segment_paths) + 1}",
                    segment_type,
                    f"{len(text)} chars"
                )
                self._update_segment_display()
        except Exception as e:
            print(f"Error adding segment to manager: {e}")

    def _play_all_segments(self) -> None:
        """Play all segments in sequence from the beginning"""
        try:
            if hasattr(self, 'segment_manager') and self.segment_manager:
                valid_paths, valid_durations = self.segment_manager.get_valid_segments()
                
                if not valid_paths:
                    QMessageBox.information(self, "Thông báo", "Không có segments nào để phát.")
                    return
                
                # Stop current playback
                if self.audio_player:
                    self.audio_player.stop()
                
                # Add all segments to audio player
                self.audio_player.add_segments(valid_paths, valid_durations)
                
                # Start playback from the beginning (0:00)
                self.audio_player.play()
                
                self._add_log_item(f"▶️ Bắt đầu phát {len(valid_paths)} segments từ đầu", "info")
                
        except Exception as e:
            self._add_log_item(f"❌ Lỗi khi phát segments: {e}", "error")
            print(f"Error in _play_all_segments: {e}")
            # Fallback: try to play at least the first segment
            try:
                if self.audio_player and hasattr(self, 'segment_manager') and self.segment_manager:
                    valid_paths, valid_durations = self.segment_manager.get_valid_segments()
                    if valid_paths:
                        self.audio_player.add_segments([valid_paths[0]], [valid_durations[0]])
                        self.audio_player.play()
                        self._add_log_item("▶️ Đã phát segment đầu tiên từ đầu (fallback)", "info")
            except Exception as fallback_error:
                print(f"Fallback error: {fallback_error}")

    def _stop_segments_playback(self) -> None:
        """Stop segments playback"""
        try:
            if self.audio_player:
                self.audio_player.stop()
            self._add_log_item("⏹️ Đã dừng phát segments", "info")
        except Exception as e:
            self._add_log_item(f"❌ Lỗi khi dừng segments: {e}", "error")

    def _clear_all_segments(self) -> None:
        """Clear all segments and stop audio playback"""
        try:
            reply = QMessageBox.question(
                self, "Xác nhận xóa", 
                "Bạn có chắc muốn xóa tất cả segments?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Dừng audio đang phát trước khi xóa
                if self.audio_player:
                    self.audio_player.stop()
                    self._add_log_item("⏹️ Đã dừng phát audio", "info")
                
                # Xóa tất cả segments
                if hasattr(self, 'segment_manager') and self.segment_manager:
                    self.segment_manager.clear_segments()
                
                self._add_log_item("🗑️ Đã xóa tất cả segments", "info")
                
        except Exception as e:
            self._add_log_item(f"❌ Lỗi khi xóa segments: {e}", "error")

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
        # Clear audio và reset nút đọc trước khi bắt đầu dịch
        self._clear_audio_and_reset_buttons()
        
        self._start_single_translation()
          

    def _start_single_translation(self) -> None:
        """Bắt đầu dịch một văn bản"""
        text = self.input_text.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Thông báo", "Vui lòng nhập văn bản cần dịch.")
            return

        src = language_manager.code_by_name(self.source_lang_combo.currentText())
        tgt = language_manager.code_by_name(self.target_lang_combo.currentText())
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
            
        src = language_manager.code_by_name(self.source_lang_combo.currentText())
        tgt = language_manager.code_by_name(self.target_lang_combo.currentText())
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
        
        output_text = "\n".join(output_lines)
        self.output_text.setPlainText(output_text)
        
        # Cập nhật số từ và ký tự cho output
        self._update_word_count(output_text, self.output_word_count_label)

    def _attach_batch_worker(self, worker: MultiThreadTranslateWorker, filename: str) -> None:
        """Kết nối worker con của batch worker"""
        worker.segment_translated.connect(self._on_segment_translated)
        worker.progress.connect(self._update_progress)
        worker.status.connect(self._add_log_item)
        worker.all_done.connect(lambda: self._add_log_item(f"✅ Hoàn thành file: {filename}"))
        worker.error.connect(lambda e: self._add_log_item(f"❌ Lỗi file {filename}: {e}"))

    def _read_source_text(self) -> None:
        """Đọc văn bản nguồn bằng TTS - toggle play/stop"""
        # Kiểm tra xem có đang đọc không
        if hasattr(self, 'is_reading_source') and self.is_reading_source:
            # Đang đọc -> dừng đọc
            self._stop_tts_reading("source")
        else:
            # Chưa đọc -> bắt đầu đọc
            text = self.input_text.toPlainText().strip()
            if not text:
                QMessageBox.information(self, "Thông báo", "Vui lòng nhập văn bản cần đọc.")
                return
            
            self._start_tts_reading(text, "source")

    def _read_target_text(self) -> None:
        """Đọc văn bản đích bằng TTS - toggle play/stop"""
        # Kiểm tra xem có đang đọc không
        if hasattr(self, 'is_reading_target') and self.is_reading_target:
            # Đang đọc -> dừng đọc
            self._stop_tts_reading("target")
        else:
            # Chưa đọc -> bắt đầu đọc
            text = self.output_text.toPlainText().strip()
            if not text:
                QMessageBox.information(self, "Thông báo", "Vui lòng dịch văn bản trước khi đọc.")
                return
            
            self._start_tts_reading(text, "target")

    def _start_tts_reading(self, text: str, text_type: str) -> None:
        """Bắt đầu đọc văn bản bằng TTS"""
        try:
            # Dừng audio đang phát nếu có
            if self.audio_player:
                self.audio_player.stop()
            
            # Dừng TTS worker cũ nếu đang chạy
            if self.tts_worker and self.tts_worker.isRunning():
                self.tts_worker.stop()
                self.tts_worker.wait(3000)
            
            # Hiện section Quản lý Audio Segments
            if hasattr(self, 'segment_manager_group'):
                self.segment_manager_group.setVisible(True)
            
            # Dừng đọc văn bản cũ trước khi bắt đầu đọc văn bản mới
            if text_type == "source":
                # Nếu đang đọc văn bản đích, dừng nó trước
                if self.is_reading_target:
                    self.is_reading_target = False
                    self.read_target_btn.setText("🔊 Đọc văn bản đích")
                    self.read_target_btn.setStyleSheet("")
                    # Dừng audio và xóa segments cũ
                    if self.audio_player:
                        self.audio_player.stop()
                    if hasattr(self, 'segment_manager') and self.segment_manager:
                        self.segment_manager.clear_segments()
                    # Ẩn section Quản lý Audio Segments khi chuyển đổi
                    if hasattr(self, 'segment_manager_group'):
                        self.segment_manager_group.setVisible(False)
                    # Enable combobox TTS đích
                    self.target_tts_lang_combo.setEnabled(True)
                    # Xóa dữ liệu tạm khi chuyển đổi
                    clean_all_temp_parts()
                
                # Bắt đầu đọc văn bản nguồn
                self.is_reading_source = True
                self.read_source_btn.setText("🔇 Tắt đọc văn bản nguồn")
                self.read_source_btn.setStyleSheet("background-color: #ff6b6b; color: white;")
                # Disable combobox TTS nguồn khi đang đọc
                self.source_tts_lang_combo.setEnabled(False)
            else:  # target
                # Nếu đang đọc văn bản nguồn, dừng nó trước
                if self.is_reading_source:
                    self.is_reading_source = False
                    self.read_source_btn.setText("🔊 Đọc văn bản nguồn")
                    self.read_source_btn.setStyleSheet("")
                    # Dừng audio và xóa segments cũ
                    if self.audio_player:
                        self.audio_player.stop()
                    if hasattr(self, 'segment_manager') and self.segment_manager:
                        self.segment_manager.clear_segments()
                    # Ẩn section Quản lý Audio Segments khi chuyển đổi
                    if hasattr(self, 'segment_manager_group'):
                        self.segment_manager_group.setVisible(False)
                    # Enable combobox TTS nguồn
                    self.source_tts_lang_combo.setEnabled(True)
                    # Xóa dữ liệu tạm khi chuyển đổi
                    clean_all_temp_parts()
                
                # Bắt đầu đọc văn bản đích
                self.is_reading_target = True
                self.read_target_btn.setText("🔇 Tắt đọc văn bản đích")
                self.read_target_btn.setStyleSheet("background-color: #ff6b6b; color: white;")
                # Disable combobox TTS đích khi đang đọc
                self.target_tts_lang_combo.setEnabled(False)
            
            # Lấy voice từ combobox TTS
            if text_type == "source":
                selected_voice = self.source_tts_lang_combo.currentText()
            else:  # target
                selected_voice = self.target_tts_lang_combo.currentText()
            
            # Xử lý voice được chọn
            if selected_voice == "Tự phát hiện":
                # Sử dụng langdetect để tự động phát hiện
                detected_lang = language_manager.detect_language_from_text(text)
                voice_name = language_manager.get_female_voice(detected_lang) or language_manager.get_default_voice_for_language(detected_lang)
                lang_display_name = language_manager.get_language_display_name(detected_lang)
                self._add_log_item(f"🔍 Phát hiện ngôn ngữ: {lang_display_name} ({detected_lang})", "info")
                print(f"🔍 Detected language: {detected_lang}, Voice: {voice_name}")
            else:
                # Lấy voice name từ label (ví dụ: "Nữ - HoaiMy (vi-VN-HoaiMyNeural)")
                voice_name = language_manager.extract_voice_name_from_label(selected_voice)
                if voice_name:
                    self._add_log_item(f"🎯 Sử dụng voice: {selected_voice}", "info")
                    print(f"🎯 Selected voice: {voice_name}")
                else:
                    # Fallback: sử dụng ngôn ngữ từ combobox dịch
                    if text_type == "source":
                        lang_code = language_manager.code_by_name(self.source_lang_combo.currentText())
                    else:
                        lang_code = language_manager.code_by_name(self.target_lang_combo.currentText())
                    
                    if lang_code != "auto":
                        voice_name = language_manager.get_female_voice(lang_code) or language_manager.get_default_voice_for_language(lang_code)
                        lang_display_name = language_manager.get_language_display_name(lang_code)
                        self._add_log_item(f"🎯 Fallback voice: {lang_display_name} ({lang_code})", "info")
                    else:
                        voice_name = "vi-VN-HoaiMyNeural"  # Default Vietnamese
                        self._add_log_item("🎯 Fallback voice: Tiếng Việt (vi)", "info")
            # Tạo TTS worker
            self.tts_worker = MTProducerWorker(
                text, voice_name, 0, 0, 500, 4
            )
            
            # Kết nối signals
            self.tts_worker.segment_ready.connect(self._on_tts_segment_ready)
            self.tts_worker.progress.connect(self._on_tts_progress)
            self.tts_worker.status.connect(self._on_tts_status)
            self.tts_worker.all_done.connect(self._on_tts_complete)
            self.tts_worker.error.connect(self._on_tts_error)
            
            # Bắt đầu TTS
            self.tts_worker.start()
            
            # Log
            self._add_log_item(f"🔊 Bắt đầu đọc văn bản {text_type}: {len(text)} ký tự", "info")
            
        except Exception as e:
            self._add_log_item(f"❌ Lỗi khi bắt đầu TTS: {e}", "error")
            # Chỉ reset nút tương ứng khi có lỗi
            if text_type == "source":
                self.is_reading_source = False
                self.read_source_btn.setText("🔊 Đọc văn bản nguồn")
                self.read_source_btn.setStyleSheet("")
            else:  # target
                self.is_reading_target = False
                self.read_target_btn.setText("🔊 Đọc văn bản đích")
                self.read_target_btn.setStyleSheet("")

    def _stop_tts_reading(self, text_type: str) -> None:
        """Dừng đọc văn bản bằng TTS và xóa segments"""
        try:
            # Dừng audio đang phát
            if self.audio_player:
                self.audio_player.stop()
            
            # Dừng TTS worker nếu đang chạy
            if self.tts_worker and self.tts_worker.isRunning():
                self.tts_worker.stop()
                self.tts_worker.wait(3000)
            
            # Xóa tất cả segments
            if hasattr(self, 'segment_manager') and self.segment_manager:
                self.segment_manager.clear_segments()
                self._add_log_item("🗑️ Đã xóa tất cả segments", "info")
            
            # Ẩn section Quản lý Audio Segments
            if hasattr(self, 'segment_manager_group'):
                self.segment_manager_group.setVisible(False)
            
            # Cập nhật trạng thái nút đọc
            if text_type == "source":
                self.is_reading_source = False
                self.read_source_btn.setText("🔊 Đọc văn bản nguồn")
                self.read_source_btn.setStyleSheet("")
                # Enable combobox TTS nguồn khi dừng đọc
                self.source_tts_lang_combo.setEnabled(True)
            else:
                self.is_reading_target = False
                self.read_target_btn.setText("🔊 Đọc văn bản đích")
                self.read_target_btn.setStyleSheet("")
                # Enable combobox TTS đích khi dừng đọc
                self.target_tts_lang_combo.setEnabled(True)
            
            # Xóa dữ liệu tạm khi dừng đọc
            clean_all_temp_parts()
            
            # Log
            self._add_log_item(f"⏹️ Đã dừng đọc văn bản {text_type}", "info")
            
        except Exception as e:
            self._add_log_item(f"❌ Lỗi khi dừng TTS: {e}", "error")
    def _ensure_capacity(self, n: int) -> None:
        """Ensure segments list has enough capacity"""
        while len(self.segment_manager.segment_paths) < n:
            self.segment_manager.segment_paths.append(None)
            self.segment_manager.segment_durations.append(None)
            
    def _show_player_section(self, show: bool = True) -> None:
        """Show or hide player section and segments list"""
        # This method is a placeholder for translate_tab.py
        # In translate_tab.py, we don't have a separate player section
        # but we can use it to show/hide the segment manager section
        if hasattr(self, 'segment_manager_group'):
            self.segment_manager_group.setVisible(show)
            
    def _update_break_button_state(self, position_ms: int) -> None:
        """Update break segment button state based on current audio position"""
        # This method is a placeholder for translate_tab.py
        # In translate_tab.py, we don't have break segment functionality
        # but we can use it for future features
        pass

    def _on_tts_segment_ready(self, path: str, duration_ms: int, index: int) -> None:
        """Callback khi TTS segment sẵn sàng"""
        self._ensure_capacity(index)
        self.segment_manager.segment_paths[index - 1] = path
        self.segment_manager.segment_durations[index - 1] = duration_ms

        # Update total duration
        self.segment_manager._update_total_duration()

        # Update segments display with detailed time information
        # Use debounced update to reduce UI churn for large numbers of segments
        if hasattr(self.segment_manager, 'schedule_display_update'):
            self.segment_manager.schedule_display_update(200)
        else:
            self.segment_manager._update_display()
        
        # Cập nhật UI của translate_tab.py
        self._update_segment_display()

        # Update AudioPlayer
        if self.audio_player:
            valid_paths, valid_durations = self.segment_manager.get_valid_segments()
            self.audio_player.add_segments(valid_paths, valid_durations)

            # Hiện player section khi có segment đầu tiên
            if index == 1:
                self._show_player_section(True)

            # Update break button state
            if hasattr(self, '_update_break_button_state'):
                current_pos = self.audio_player.get_current_position()
                self._update_break_button_state(current_pos)

        # Auto-play first segment if nothing is playing
        if self.current_index < 0 and self.segment_manager.segment_paths and self.segment_manager.segment_paths[0]:
            if self.audio_player:
                self.audio_player.play()
                self._add_log_item(
                    f"▶️ Tự động phát segment đầu tiên: {os.path.basename(self.segment_manager.segment_paths[0])}", "blue")

    def _on_tts_progress(self, emitted: int, total: int) -> None:
        """Callback cho tiến trình TTS"""
        progress = int((emitted / total) * 100) if total > 0 else 0
        self._add_log_item(f"🔄 TTS: {progress}% ({emitted}/{total})", "info")

    def _on_tts_status(self, msg: str) -> None:
        """Callback cho status TTS"""
        self._add_log_item(f"ℹ️ TTS: {msg}", "info")

    def _on_tts_complete(self) -> None:
        """Callback khi TTS hoàn thành"""
        self._add_log_item("✅ TTS hoàn thành", "info")
        # Không reset nút ở đây, để người dùng có thể dừng khi muốn

    def _on_tts_error(self, msg: str) -> None:
        """Callback khi TTS có lỗi"""
        self._add_log_item(f"❌ Lỗi TTS: {msg}", "error")
        # Không reset buttons ở đây để tránh ảnh hưởng đến nút đang đọc
        # Chỉ log lỗi, giữ nguyên trạng thái buttons

    def _reset_read_buttons(self) -> None:
        """Reset trạng thái các nút đọc - chỉ reset nút không đang đọc"""
        # Chỉ reset nút source nếu không đang đọc
        if not self.is_reading_source:
            self.read_source_btn.setEnabled(True)
            self.read_source_btn.setText("🔊 Đọc văn bản nguồn")
            self.read_source_btn.setStyleSheet("")
            # Enable combobox TTS nguồn
            if hasattr(self, 'source_tts_lang_combo'):
                self.source_tts_lang_combo.setEnabled(True)
        
        # Chỉ reset nút target nếu không đang đọc
        if not self.is_reading_target:
            self.read_target_btn.setEnabled(True)
            self.read_target_btn.setText("🔊 Đọc văn bản đích")
            self.read_target_btn.setStyleSheet("")
            # Enable combobox TTS đích
            if hasattr(self, 'target_tts_lang_combo'):
                self.target_tts_lang_combo.setEnabled(True)

    def _reset_all_read_buttons(self) -> None:
        """Reset tất cả nút đọc về trạng thái ban đầu (dùng khi đóng tab hoặc cần thiết)"""
        self.is_reading_source = False
        self.is_reading_target = False
        
        self.read_source_btn.setEnabled(True)
        self.read_source_btn.setText("🔊 Đọc văn bản nguồn")
        self.read_source_btn.setStyleSheet("")
        
        self.read_target_btn.setEnabled(True)
        self.read_target_btn.setText("🔊 Đọc văn bản đích")
        self.read_target_btn.setStyleSheet("")
        
        # Enable tất cả combobox TTS
        if hasattr(self, 'source_tts_lang_combo'):
            self.source_tts_lang_combo.setEnabled(True)
        if hasattr(self, 'target_tts_lang_combo'):
            self.target_tts_lang_combo.setEnabled(True)

    def _on_audio_position_changed(self, position_ms: int) -> None:
        """Callback khi vị trí audio thay đổi"""
        try:
            # Có thể thêm logic để cập nhật UI theo vị trí audio
            # Ví dụ: cập nhật progress bar, timeline, etc.
            pass
        except Exception as e:
            print(f"Error handling audio position change: {e}")

    def _on_audio_segment_changed(self, segment_index: int) -> None:
        """Callback khi segment audio thay đổi"""
        try:
            # Highlight current segment in the list
            if hasattr(self, 'segment_list') and self.segment_list and 0 <= segment_index < self.segment_list.count():
                self.segment_list.setCurrentRow(segment_index)
        except Exception as e:
            print(f"Error highlighting segment: {e}")

    def _on_audio_playback_state_changed(self, is_playing: bool) -> None:
        """Callback khi trạng thái phát audio thay đổi"""
        try:
            # Update button states
            # if hasattr(self, 'play_segments_btn'):
            #     self.play_segments_btn.setEnabled(not is_playing)  # Enable khi KHÔNG phát
            if hasattr(self, 'stop_segments_btn'):
                self.stop_segments_btn.setEnabled(is_playing)      # Enable khi ĐANG phát
        except Exception as e:
            print(f"Error updating button states: {e}")

    def _on_audio_status_changed(self, status: str) -> None:
        """Callback khi status audio thay đổi"""
        self._add_log_item(f"🎵 Audio: {status}", "info")

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
        
        # Reset trạng thái các nút đọc khi dừng dịch thuật
        # Chỉ reset nút không đang đọc để tránh ảnh hưởng đến nút đang đọc
        if not self.is_reading_source:
            self.read_source_btn.setEnabled(True)
            self.read_source_btn.setText("🔊 Đọc văn bản nguồn")
            self.read_source_btn.setStyleSheet("")
            # Enable combobox TTS nguồn
            if hasattr(self, 'source_tts_lang_combo'):
                self.source_tts_lang_combo.setEnabled(True)
        
        if not self.is_reading_target:
            self.read_target_btn.setEnabled(True)
            self.read_target_btn.setText("🔊 Đọc văn bản đích")
            self.read_target_btn.setStyleSheet("")
            # Enable combobox TTS đích
            if hasattr(self, 'target_tts_lang_combo'):
                self.target_tts_lang_combo.setEnabled(True)
        
        # Xóa dữ liệu tạm khi dừng dịch thuật
        clean_all_temp_parts()
        
        self.stop_button.setEnabled(False)
        self._add_log_item("⏹ Đã dừng dịch thuật")

    def clear_results(self) -> None:
        """Xóa kết quả dịch"""
        # Clear audio và reset nút đọc khi xóa kết quả
        self._clear_audio_and_reset_buttons()
        
        # Clear kết quả dịch
        self.output_text.clear()
        self.translated_segments.clear()
        
        # Xóa số từ và ký tự cho output
        self._update_word_count("", self.output_word_count_label)
        
        # Log thông báo
        self._add_log_item("🗑️ Đã xóa kết quả và clear audio")

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
                
            # Clear segment manager
            if hasattr(self, 'segment_manager'):
                self.segment_manager.clear_segments()
            
            # Reset tất cả nút đọc về trạng thái ban đầu
            self._reset_all_read_buttons()
            
            # Xóa dữ liệu tạm khi đóng tab
            clean_all_temp_parts()
                
        except Exception as e:
            print(f"Warning: Error in closeEvent: {e}")
        
        super().closeEvent(event)

    def _cleanup_temp_audio_files(self) -> None:
        """Xóa các file audio tạm thời"""
        try:
            # Xóa file audio tạm từ TTS
          
            clean_all_temp_parts()
            
            # Xóa file gap nếu có
            from app.core.config import AppConfig
            temp_dir = AppConfig.TEMP_DIR
            if temp_dir.exists():
                for temp_file in temp_dir.glob("gap_*.mp3"):
                    try:
                        temp_file.unlink()
                    except Exception as e:
                        print(f"Warning: Could not delete temp file {temp_file}: {e}")
        except Exception as e:
            print(f"Warning: Error cleaning temp files: {e}")

    
 

    def _write_log_to_file(self, message: str) -> None:
        """Ghi log vào file testtr.txt"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] {message}\n"
            
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(log_entry)
                
        except Exception as e:
            print(f"❌ Lỗi khi ghi log vào file: {str(e)}")
    
    def _update_word_count(self, text: str, label: QLabel) -> None:
        """Cập nhật số từ và ký tự cho label"""
        try:
            if not text or not text.strip():
                label.setText("")
                return
            
            # Đếm từ (tách theo khoảng trắng)
            words = len([word for word in text.split() if word.strip()])
            
            # Đếm ký tự (bao gồm cả khoảng trắng)
            characters = len(text)
            
            # Cập nhật label với HTML formatting: số màu đỏ, text màu xám
            label.setText(f'<span style="color: #10b981;">{words:,}</span> từ (<span style="color: #ff6b6b;">{characters:,}</span> ký tự)')
            
        except Exception as e:
            print(f"Warning: Error updating word count: {e}")
            label.setText("")

    def eventFilter(self, obj, event) -> bool:
        """Event filter để xử lý sự kiện Enter trong input_text"""
        if obj == self.input_text and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                # Kiểm tra nếu đang giữ Shift thì cho phép xuống dòng
                if event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                    return False  # Cho phép xuống dòng bình thường
                else:
                    # Bấm Enter đơn thuần - kích hoạt dịch
                    self.translate_now()
                    return True  # Đã xử lý sự kiện
        return False  # Không xử lý, để Qt xử lý bình thường

    def _clear_audio_and_reset_buttons(self) -> None:
        """Clear audio và reset nút đọc khi bắt đầu dịch"""
        try:
            # Dừng audio player nếu đang phát
            if hasattr(self, 'audio_player') and self.audio_player:
                self.audio_player.stop()
            
            # Dừng TTS worker nếu đang chạy
            if hasattr(self, 'tts_worker') and self.tts_worker and self.tts_worker.isRunning():
                self.tts_worker.stop()
                self.tts_worker.wait(3000)
            
            # Clear segment manager
            if hasattr(self, 'segment_manager') and self.segment_manager:
                self.segment_manager.clear_segments()
            
            # Ẩn section Quản lý Audio Segments
            if hasattr(self, 'segment_manager_group'):
                self.segment_manager_group.setVisible(False)
            
            # Reset tất cả nút đọc về trạng thái ban đầu
            self._reset_all_read_buttons()
            
            # Xóa dữ liệu tạm
            clean_all_temp_parts()
            
            # Log thông báo
            self._add_log_item("🧹 Đã clear audio và reset nút đọc để bắt đầu dịch mới", "info")
            
        except Exception as e:
            print(f"Warning: Error in _clear_audio_and_reset_buttons: {e}")

    def _on_source_text_changed(self):
        """Callback khi văn bản nguồn thay đổi - clear dữ liệu đích và reset nút đọc"""
        try:
            # Cập nhật số từ và ký tự cho input
            current_text = self.input_text.toPlainText()
            self._update_word_count(current_text, self.input_word_count_label)
            
            # Clear output text
            self.output_text.clear()
            
            # Clear translated segments
            if hasattr(self, 'translated_segments'):
                self.translated_segments.clear()
            
            # Xóa số từ và ký tự cho output
            self._update_word_count("", self.output_word_count_label)
            
            # Clear segment manager nếu có
            if hasattr(self, 'segment_manager') and self.segment_manager:
                self.segment_manager.clear_segments()
            
            # Ẩn section Quản lý Audio Segments
            if hasattr(self, 'segment_manager_group'):
                self.segment_manager_group.setVisible(False)
            
            # Dừng audio player nếu đang phát
            if hasattr(self, 'audio_player') and self.audio_player:
                self.audio_player.stop()
            
            # Reset progress nếu có
            if hasattr(self, '_reset_progress'):
                self._reset_progress()
            
            # Reset tất cả nút đọc về trạng thái ban đầu
            self._reset_all_read_buttons()
            
            # Log thông báo
            self._add_log_item("🔄 Văn bản nguồn đã thay đổi - đã xóa dữ liệu đích và reset nút đọc", "info")
            
        except Exception as e:
            print(f"Warning: Error in _on_source_text_changed: {e}")

    def _on_playback_started(self):
        """Callback khi bắt đầu phát từ 0:00"""
        print("Playback started from 0:00")
        # Thêm logic xử lý khi bắt đầu phát

    def _on_playback_stopped(self):
        """Callback khi dừng phát"""
        print("Playback stopped")
        # Thêm logic xử lý khi dừng phát

    # Các hàm liên quan đến ngôn ngữ và voices đã được di chuyển sang language_manager
    # Sử dụng language_manager.get_*() thay vì các hàm local

    def _on_source_lang_changed(self, lang_name: str) -> None:
        """Callback khi thay đổi ngôn ngữ nguồn"""
        try:
            # Populate voices mới cho TTS combobox
            self._populate_source_voices()
        except Exception as e:
            print(f"Error updating source TTS language: {e}")

    def _on_target_lang_changed(self, lang_name: str) -> None:
        """Callback khi thay đổi ngôn ngữ đích"""
        try:
            # Populate voices mới cho TTS combobox
            self._populate_target_voices()
        except Exception as e:
            print(f"Error updating target TTS language: {e}")

    def _sync_tts_with_translation_languages(self) -> None:
        """Đồng bộ TTS combobox với ngôn ngữ dịch ban đầu"""
        try:
            # Populate voices cho cả source và target
            if hasattr(self, 'source_tts_lang_combo'):
                self._populate_source_voices()
            
            if hasattr(self, 'target_tts_lang_combo'):
                self._populate_target_voices()
                
        except Exception as e:
            print(f"Error syncing TTS languages: {e}")

    # Hàm _extract_voice_name_from_label đã được di chuyển sang language_manager
    # Sử dụng language_manager.extract_voice_name_from_label() thay thế

    def _populate_source_voices(self) -> None:
        """Populate source TTS combobox với voices của ngôn ngữ nguồn"""
        try:
            self.source_tts_lang_combo.clear()
            
            # Lấy ngôn ngữ nguồn hiện tại
            source_lang = self.source_lang_combo.currentText()
            if source_lang != "Tự phát hiện":
                lang_code = language_manager.code_by_name(source_lang)
                # Sử dụng language_manager để populate voices
                voices = language_manager.populate_voices_for_language(lang_code)
                for voice in voices:
                    self.source_tts_lang_combo.addItem(voice)
            else:
                # Nếu là "Tự phát hiện", chỉ thêm option đó
                self.source_tts_lang_combo.addItem("Tự phát hiện")
            
            # Đặt lại selection
            self.source_tts_lang_combo.setCurrentText("Tự phát hiện")
            
        except Exception as e:
            print(f"Error populating source voices: {e}")

    def _populate_target_voices(self) -> None:
        """Populate target TTS combobox với voices của ngôn ngữ đích"""
        try:
            self.target_tts_lang_combo.clear()
            
            # Lấy ngôn ngữ đích hiện tại
            target_lang = self.target_lang_combo.currentText()
            if target_lang != "Tự phát hiện":
                lang_code = language_manager.code_by_name(target_lang)
                # Sử dụng language_manager để populate voices
                voices = language_manager.populate_voices_for_language(lang_code)
                for voice in voices:
                    self.target_tts_lang_combo.addItem(voice)
            else:
                # Nếu là "Tự phát hiện", chỉ thêm option đó
                self.target_tts_lang_combo.addItem("Tự phát hiện")
            
            # Đặt lại selection
            self.target_tts_lang_combo.setCurrentText("Tự phát hiện")
            
        except Exception as e:
            print(f"Error populating target voices: {e}")