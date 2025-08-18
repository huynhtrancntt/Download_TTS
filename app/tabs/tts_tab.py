# -*- coding: utf-8 -*-
"""
Tab Text-to-Speech - Sử dụng hoàn toàn AudioPlayer
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QLabel, QTextEdit, QComboBox, QSlider, QSpinBox,
    QListWidget, QProgressBar, QMessageBox,
    QFileDialog, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal
from typing import Optional, List

# Import AudioPlayer
from app.core.audio_player import AudioPlayer
# Import SegmentManager
from app.core.segment_manager import SegmentManager

import os
from datetime import datetime
from pathlib import Path
import tempfile
# Import modules
from app.uiToolbarTab import UIToolbarTab
from app.appConfig import AppConfig
from app.history.historyItem_TTS import TTSHistoryItem
from app.workers import MTProducerWorker


from app.utils.helps import (
    clean_all_temp_parts
)
from app.utils.audio_helpers import ms_to_mmss, prepare_pydub_ffmpeg, get_mp3_duration_ms
from app.utils.helps import hide_directory_on_windows

# Import audio library
from pydub import AudioSegment


class TTSTab(UIToolbarTab):
    """
    Tab Text-to-Speech sử dụng hoàn toàn AudioPlayer
    """

    def __init__(self, parent_main: QWidget) -> None:
        super().__init__(parent_main)

        # Initialize state variables
        self._initialize_state_variables()

        # Setup UI
        self._setup_ui()

        # Setup audio system
        self._setup_audio_system()

        # Connect signals
        self._connect_signals()

    def _initialize_state_variables(self) -> None:
        """Initialize state variables"""
        self.current_index: int = -1
        self.worker: Optional[MTProducerWorker] = None
        self.file_output: str = ""
        self.audio_player: Optional[AudioPlayer] = None

        # Initialize SegmentManager
        self.segment_manager = SegmentManager()

    def _setup_ui(self) -> None:
        """Setup UI"""
        root_layout = self.layout()

        # Setup history system
        self._setup_history_system()

        # Setup header section
        self._setup_header_section(root_layout)

        # Setup content section
        self._setup_content_section(root_layout)

        # Setup player section
        self._setup_player_section(root_layout)

        # Update status bar
        if getattr(self.parent_main, "status", None):
            self.parent_main.status.showMessage(
                "TTS Tab sẵn sàng - Chức năng ngắt đoạn đã kích hoạt")

    def _setup_history_system(self) -> None:
        """Setup history system"""
        hist = self.enable_history(
            hist_title="Lịch sử TTS",
            item_factory=lambda text, ts, lang, meta: TTSHistoryItem(
                text, ts, lang, meta),
            on_item_selected=self._on_history_selected
        )

        # Add demo history
        self.append_history(
            "Xin chào, tôi là trợ lý AI ...",
            meta={"demo": True, "priority": "high"}
        )
        self.append_history(
            "Hôm nay thời tiết thế nào?",
            meta={"demo": True, "priority": "normal"}
        )

    def _setup_header_section(self, root_layout: QVBoxLayout) -> None:
        """Setup header section"""
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(2, 2, 2, 2)

        row_layout = QVBoxLayout()

        # Job parameters row
        self._create_job_parameters_row(row_layout)

        # Control buttons row
        self._create_control_buttons_row(row_layout)

        header_layout.addLayout(row_layout)
        root_layout.addLayout(header_layout)

    def _create_job_parameters_row(self, parent_layout: QVBoxLayout) -> None:
        """Create job parameters row"""
        row1_layout = QHBoxLayout()

        # Threads spinbox
        self.theard_edge_tts = QSpinBox()
        self.theard_edge_tts.setRange(1, 16)
        self.theard_edge_tts.setValue(AppConfig.DEFAULT_WORKERS_PLAYER)
        self.theard_edge_tts.setSuffix(" Thread")

        # Max length spinbox
        self.maxlen_spin_edge_tts = QSpinBox()
        self.maxlen_spin_edge_tts.setRange(80, 2000)
        self.maxlen_spin_edge_tts.setValue(AppConfig.DEFAULT_MAXLEN)
        self.maxlen_spin_edge_tts.setSuffix(" ký tự/đoạn")

        # Gap spinbox
        self.gap_spin_edge_tts = QSpinBox()
        self.gap_spin_edge_tts.setRange(0, 2000)
        self.gap_spin_edge_tts.setValue(AppConfig.DEFAULT_GAP_MS)
        self.gap_spin_edge_tts.setSuffix(" ms nghỉ ghép")

        # Add to layout
        row1_layout.addWidget(QLabel("Thread"))
        row1_layout.addWidget(self.theard_edge_tts)
        row1_layout.addWidget(self.maxlen_spin_edge_tts)
        row1_layout.addWidget(self.gap_spin_edge_tts)
        row1_layout.addStretch()

        # Add history button
        if hasattr(self, 'history') and self.history:
            row1_layout.addWidget(self.history.btn)

        parent_layout.addLayout(row1_layout)

    def _create_control_buttons_row(self, parent_layout: QVBoxLayout) -> None:
        """Create control buttons row"""
        row2_layout = QHBoxLayout()
        row2_layout.setContentsMargins(0, 0, 0, 0)

        # Open file button
        self.btn_open_edge_tts = QPushButton("📂 Mở file")
        self.btn_open_edge_tts.clicked.connect(self.on_open_file)
        row2_layout.addWidget(self.btn_open_edge_tts)

        row2_layout.addStretch()

        # Start/Stop buttons
        self.btn_start_edge_tts = QPushButton("▶️ Bắt đầu")
        self.btn_start_edge_tts.clicked.connect(self.on_start)

        self.btn_end_edge_tts = QPushButton("⏹ Kết thúc")
        self.btn_end_edge_tts.clicked.connect(self.on_end_all)
        self.btn_end_edge_tts.setEnabled(False)

        row2_layout.addWidget(self.btn_start_edge_tts)
        row2_layout.addWidget(self.btn_end_edge_tts)

        parent_layout.addLayout(row2_layout)

    def _setup_content_section(self, root_layout: QVBoxLayout) -> None:
        """Setup content section"""
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Text input area
        self._create_text_input_area(content_layout)

        # Configuration controls
        self._create_configuration_controls(content_layout)

        # Segments list
        self._create_segments_list(content_layout)

        # Status label
        self._create_status_label(content_layout)

        root_layout.addLayout(content_layout)

    def _create_text_input_area(self, content_layout: QVBoxLayout) -> None:
        """Create text input area"""
        self.text_input_edge_tts = QTextEdit(
            placeholderText="Dán văn bản hoặc bấm Mở .txt"
        )
        content_layout.addWidget(self.text_input_edge_tts, 2)

    def _create_configuration_controls(self, content_layout: QVBoxLayout) -> None:
        """Create configuration controls"""
        # Language and gender controls
        self._create_language_gender_controls(content_layout)

        # Speed and pitch controls
        self._create_speed_pitch_controls(content_layout)

        # TTS control buttons
        self._create_tts_control_buttons(content_layout)

    def _create_language_gender_controls(self, content_layout: QVBoxLayout) -> None:
        """Create language and gender controls"""
        row_layout = QHBoxLayout()

        # Language combo box
        self.cmb_lang = QComboBox()
        self.cmb_lang.setMinimumWidth(120)
        for label, code in [
            ("Vietnamese (vi)", "vi"), ("English US (en-US)", "en-US"),
            ("English UK (en-GB)", "en-GB"), ("Japanese (ja)", "ja"),
            ("Korean (ko)", "ko"), ("Chinese (zh-CN)", "zh-CN"),
            ("French (fr-FR)", "fr-FR"), ("German (de-DE)", "de-DE"),
            ("Spanish (es-ES)", "es-ES"),
        ]:
            self.cmb_lang.addItem(label, code)
        self.cmb_lang.setCurrentIndex(0)

        # Gender combo box
        self.cmb_gender = QComboBox()
        self.cmb_gender.setMinimumWidth(80)
        self.cmb_gender.addItems(["Female", "Male", "Any"])
        self.cmb_gender.setCurrentText("Female")

        row_layout.addWidget(QLabel("Ngôn ngữ"))
        row_layout.addWidget(self.cmb_lang)
        row_layout.addWidget(QLabel("Giới tính"))
        row_layout.addWidget(self.cmb_gender)
        row_layout.addStretch()

        content_layout.addLayout(row_layout)

    def _create_speed_pitch_controls(self, content_layout: QVBoxLayout) -> None:
        """Create speed and pitch controls"""
        row_layout = QHBoxLayout()

        # Speed slider
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(100)
        self.speed_slider.setTickInterval(10)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)

        self.lbl_speed_val = QLabel("1.0")
        self.speed_slider.valueChanged.connect(
            lambda v: self.lbl_speed_val.setText(f"{v/100:.1f}")
        )

        # Pitch slider
        self.pitch_slider = QSlider(Qt.Horizontal)
        self.pitch_slider.setRange(-50, 50)
        self.pitch_slider.setValue(0)
        self.pitch_slider.setTickInterval(10)
        self.pitch_slider.setTickPosition(QSlider.TicksBelow)

        self.lbl_pitch_val = QLabel("1.0")
        self.pitch_slider.valueChanged.connect(
            lambda v: self.lbl_pitch_val.setText(f"{1 + v/100:.1f}")
        )

        row_layout.addWidget(QLabel("Tốc độ"))
        row_layout.addWidget(self.speed_slider, 1)
        row_layout.addWidget(self.lbl_speed_val)
        row_layout.addSpacing(12)
        row_layout.addWidget(QLabel("Cao độ"))
        row_layout.addWidget(self.pitch_slider, 1)
        row_layout.addWidget(self.lbl_pitch_val)

        content_layout.addLayout(row_layout)

    def _create_tts_control_buttons(self, content_layout: QVBoxLayout) -> None:
        """Create TTS control buttons"""
        # Row 1: Main TTS controls
        row1_layout = QHBoxLayout()

        # Create buttons for row 1
        self.btn_say = QPushButton("🔊 Chuyển đổi")
        self.btn_save = QPushButton("💾 Lưu")
        self.btn_info = QPushButton("ℹ️ Info")

        # Connect buttons for row 1
        self.btn_info.clicked.connect(self._print_segments_info)
        self.btn_save.clicked.connect(self.on_export_mp3)

        # Apply style to buttons in row 1
        for btn in (self.btn_say, self.btn_save, self.btn_info):
            btn.setStyleSheet(AppConfig.BUTTON_STYLE)
            btn.setMinimumWidth(80)
            btn.setMaximumWidth(120)
            row1_layout.addWidget(btn)

        row1_layout.addStretch()
        content_layout.addLayout(row1_layout)

        # Row 2: Media and segment controls
        row2_layout = QHBoxLayout()

        # Create buttons for row 2
        self.btn_add_audio = QPushButton("🎵 Thêm Audio")
        self.btn_add_video = QPushButton("🎬 Thêm Video")
        self.btn_remove_segment = QPushButton("❌ Xóa Segment")
        self.btn_reorder = QPushButton("🔄 Sắp xếp")
        self.btn_test_loop = QPushButton("🔄 Test Loop")

        # Add segment break controls
        self.btn_break_segment = QPushButton("✂️ Ngắt đoạn")
        self.cmb_break_duration = QComboBox()
        self.cmb_break_duration.addItems(["3s", "4s", "5s", "10s"])
        self.cmb_break_duration.setCurrentText("3s")
        self.cmb_break_duration.setMinimumWidth(60)

        # Connect buttons for row 2
        self.btn_add_audio.clicked.connect(self.on_add_audio_file)
        self.btn_add_video.clicked.connect(self.on_add_video_file)
        self.btn_remove_segment.clicked.connect(
            self.on_remove_selected_segment)
        self.btn_reorder.clicked.connect(self.on_reorder_segments)
        self.btn_test_loop.clicked.connect(self.on_test_loop)
        self.btn_break_segment.clicked.connect(self.on_break_segment)

        # Apply style to buttons in row 2
        for btn in (self.btn_add_audio, self.btn_add_video, self.btn_remove_segment,
                    self.btn_reorder, self.btn_test_loop):
            btn.setStyleSheet(AppConfig.BUTTON_STYLE)
            btn.setMinimumWidth(80)
            btn.setMaximumWidth(120)
            row2_layout.addWidget(btn)

        # Add break duration combo box

        row2_layout.addWidget(self.cmb_break_duration)
        row2_layout.addWidget(self.btn_break_segment)
        #   row2_layout.addWidget(QLabel("Khoảng:"))
        row2_layout.addStretch()
        content_layout.addLayout(row2_layout)

    def _create_segments_list(self, content_layout: QVBoxLayout) -> None:
        """Create segments list"""
        # Create container widget for segments list
        self.segments_container = QWidget()
        self.segments_container.setVisible(False)  # Ẩn ban đầu

        segments_layout = QVBoxLayout(self.segments_container)
        segments_layout.setContentsMargins(0, 0, 0, 0)

        # Add label for segments
        # segments_label = QLabel("📋 Danh sách Audio Segments:")
        # segments_label.setStyleSheet(
        #     "font-weight: bold; color: #333; margin: 5px 0;")
        # segments_layout.addWidget(segments_label)

        # Create segments list widget với custom row widget
        self.list_segments = QListWidget()
        segments_layout.addWidget(self.list_segments, 1)

        # Add empty state message
        self.empty_segments_label = QLabel(
            "Chưa có audio segments. Hãy bắt đầu TTS hoặc thêm audio file.")
        self.empty_segments_label.setStyleSheet(
            "color: #888; font-style: italic; text-align: center; padding: 20px;")
        self.empty_segments_label.setAlignment(Qt.AlignCenter)
        segments_layout.addWidget(self.empty_segments_label)

        # Add container to content layout
        content_layout.addWidget(self.segments_container, 2)

    # Các method này đã được chuyển sang SegmentManager

    def _create_status_label(self, content_layout: QVBoxLayout) -> None:
        """Create status label"""
        self.lbl_status = QLabel("Sẵn sàng")
        self.lbl_status.setStyleSheet(
            "color: #888; font-size: 12px; padding: 5px;"
        )
        content_layout.addWidget(self.lbl_status)

    def _setup_player_section(self, root_layout: QVBoxLayout) -> None:
        """Setup player section using AudioPlayer"""
        # Create AudioPlayer
        self.audio_player = AudioPlayer()

        # Create container widget for AudioPlayer section
        self.player_container = QWidget()
        self.player_container.setVisible(False)  # Ẩn ban đầu

        player_layout = QVBoxLayout(self.player_container)
        player_layout.setContentsMargins(0, 0, 0, 0)

        # Add AudioPlayer to container
        player_layout.addWidget(self.audio_player)

        # Progress bar sẽ sử dụng từ main window
        # Không cần tạo progress bar riêng nữa

        # Add container to root layout
        root_layout.addWidget(self.player_container)

    def _setup_audio_system(self) -> None:
        """Setup audio system"""
        # Connect signals from AudioPlayer
        self.audio_player.position_changed.connect(
            self.on_audio_position_changed)
        self.audio_player.segment_changed.connect(
            self.on_audio_segment_changed)
        self.audio_player.playback_state_changed.connect(
            self.on_audio_playback_state_changed)
        self.audio_player.audio_split_requested.connect(
            self.on_audio_split_requested)

        # Update break segment button state based on audio position
        self.audio_player.position_changed.connect(
            self._update_break_button_state)

        # Setup SegmentManager with UI components
        self.segment_manager.set_ui_components(
            self.list_segments, self.audio_player)
        


    def _show_player_section(self, show: bool = True) -> None:
        """Show or hide player section and segments list"""
        if hasattr(self, 'player_container'):
            self.player_container.setVisible(show)

        # Ẩn/hiện segments list cùng với player
        if hasattr(self, 'segments_container'):
            self.segments_container.setVisible(show)

            # Ẩn/hiện empty state message
            if hasattr(self, 'empty_segments_label'):
                # Hiện khi ẩn segments, ẩn khi hiện segments
                self.empty_segments_label.setVisible(not show)

    def _show_empty_state_message(self, show: bool = True) -> None:
        """Show or hide empty state message"""
        if hasattr(self, 'empty_segments_label'):
            self.empty_segments_label.setVisible(show)

    def _connect_signals(self) -> None:
        """Connect signals"""
        # Connect double click on list segments
        if hasattr(self, 'list_segments'):
            self.list_segments.itemDoubleClicked.connect(
                self.on_list_item_double_clicked)

        # Connect break duration combo box change
        if hasattr(self, 'cmb_break_duration'):
            self.cmb_break_duration.currentTextChanged.connect(
                self._on_break_duration_changed)

        # Connect audio player signals
        if self.audio_player:
            self.audio_player.position_changed.connect(
                self._update_break_button_state)

        # Đảm bảo progress bar hiển thị sau khi kết nối signals
        self._ensure_progress_visible()

    def append_history(self, text: str, meta: Optional[dict] = None) -> None:
        """Add item to TTS history"""
        if self.history:
            self.history.panel.add_history(text, meta=meta or {})

    def _on_history_selected(self, text: str) -> None:
        """Callback when history item is selected"""
        self.text_input_edge_tts.setPlainText(text)
        self.text_input_edge_tts.setFocus()

    def _on_break_duration_changed(self, duration_text: str) -> None:
        """Callback when break duration combo box changes"""
        if hasattr(self, 'btn_break_segment') and hasattr(self, '_update_break_button_state'):
            # Update button tooltip with new duration
            if self.audio_player:
                current_pos = self.audio_player.get_current_position()
                if current_pos > 0:
                    self.btn_break_segment.setToolTip(
                        f"Ngắt đoạn tại vị trí hiện tại: {ms_to_mmss(current_pos)}\n"
                        f"Khoảng nghỉ: {duration_text}"
                    )

    # ==================== AudioPlayer Callbacks ====================

    def on_audio_position_changed(self, position_ms: int) -> None:
        """Callback when audio position changes from AudioPlayer"""
        # Update TTS progress bar từ main window
        total_ms = self.audio_player.get_total_duration()
        if total_ms > 0:
            progress = int((position_ms / total_ms) * 100)
            # self._update_progress(progress)

    def on_audio_segment_changed(self, segment_index: int) -> None:
        """Callback when audio segment changes from AudioPlayer"""
        self.current_index = segment_index
        # Update UI
        if hasattr(self, 'list_segments') and segment_index >= 0:
            self.list_segments.setCurrentRow(segment_index)

    def on_audio_playback_state_changed(self, is_playing: bool) -> None:
        """Callback when playback state changes from AudioPlayer"""
        pass

    def on_audio_split_requested(self, segment_index: int, split_position_ms: int) -> None:
        """Callback when audio player requests a segment segment split"""
        try:
            self._add_log_item(
                f"✂️ Yêu cầu cắt audio tại segment {segment_index + 1}, vị trí {ms_to_mmss(split_position_ms)}", "info")

            # Cắt audio file
            part1_path, part2_path = self.audio_player.split_audio_file(
                segment_index, split_position_ms)

            if part1_path and part2_path:
                # Sử dụng SegmentManager để cắt segment
                if self.segment_manager.split_segment(segment_index, split_position_ms):
                    # Cập nhật AudioPlayer để đồng bộ hóa dữ liệu
                    self.audio_player.update_segments_after_split(
                        segment_index, part1_path, part2_path, split_position_ms)

                    # Cập nhật AudioPlayer với segments mới
                    valid_paths, valid_durations = self.segment_manager.get_valid_segments()
                    self.audio_player.add_segments(
                        valid_paths, valid_durations)

                    self._add_log_item(
                        f"✅ Đã cắt audio thành công: {os.path.basename(part1_path)} và {os.path.basename(part2_path)}", "info")

                    # Hiện thông báo thành công
                    part1_duration = split_position_ms
                    part2_duration = (
                        self.segment_manager.segment_durations[segment_index] or 0) - split_position_ms
                    QMessageBox.information(self, "Thành công",
                                            f"Đã cắt audio thành công!\n"
                                            f"Phần 1: {os.path.basename(part1_path)} ({ms_to_mmss(part1_duration)})\n"
                                            f"Phần 2: {os.path.basename(part2_path)} ({ms_to_mmss(part2_duration)})")

                    # Cập nhật trạng thái break button
                    if hasattr(self, '_update_break_button_state'):
                        current_pos = self.audio_player.get_current_position()
                        self._update_break_button_state(current_pos)
                else:
                    self._add_log_item("❌ Lỗi khi cắt segment", "error")
                    QMessageBox.warning(self, "Lỗi", "Không thể cắt segment")

            else:
                self._add_log_item("❌ Lỗi khi cắt audio file", "error")
                QMessageBox.warning(self, "Lỗi", "Không thể cắt audio file")

        except Exception as e:
            self._add_log_item(f"❌ Lỗi khi cắt audio: {e}", "error")
            QMessageBox.critical(self, "Lỗi", f"Lỗi khi cắt audio: {e}")

    def _update_break_button_state(self, position_ms: int) -> None:
        """Update break segment button state based on current audio position"""
        if not hasattr(self, 'btn_break_segment'):
            return

        # Enable break button when we have valid position and segments
        can_break = (position_ms > 0 and
                     self.segment_manager.segment_paths and
                     any(self.segment_manager.segment_paths) and
                     self.audio_player and
                     self.audio_player.get_total_duration() > 0)

        self.btn_break_segment.setEnabled(can_break)

        # Update button tooltip with current position
        if can_break:
            self.btn_break_segment.setToolTip(
                f"Ngắt đoạn tại vị trí hiện tại: {ms_to_mmss(position_ms)}\n"
                f"Khoảng nghỉ: {self.cmb_break_duration.currentText()}"
            )
        else:
            self.btn_break_segment.setToolTip(
                "Không thể ngắt đoạn - vui lòng phát audio")

    # ==================== Event Handlers ====================

    def on_open_file(self) -> None:
        """Open text file and read content"""
        # Tạo filter string rõ ràng
        file_filter = (
            "Text Files (*.txt);;"
            "Markdown Files (*.md);;"
            "All Files (*.*)"
        )

        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file văn bản", "", file_filter)
        if not path:
            return

        try:
            # Đọc nội dung file
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            # Hiển thị nội dung trong text input
            self.text_input_edge_tts.setPlainText(content)

            # Hiển thị thông báo phù hợp với loại file
            file_ext = os.path.splitext(path)[1].lower()
            if file_ext == '.md':
                status_msg = f"📝 Đã mở Markdown: {os.path.basename(path)} - {len(content)} ký tự"
                self.lbl_status.setText(status_msg)
                self._add_log_item(
                    f"📝 Đã mở file Markdown: {os.path.basename(path)} ({len(content)} ký tự)", "info")
            else:
                status_msg = f"📄 Đã mở: {os.path.basename(path)} - {len(content)} ký tự"
                self.lbl_status.setText(status_msg)
                self._add_log_item(
                    f"📄 Đã mở file văn bản: {os.path.basename(path)} ({len(content)} ký tự)", "info")

            # Tự động focus vào text input để người dùng có thể chỉnh sửa
            self.text_input_edge_tts.setFocus()

        except Exception as e:
            error_msg = f"Không đọc được file: {e}"
            QMessageBox.critical(self, "Lỗi", error_msg)
            self._add_log_item(f"❌ Lỗi mở file: {e}", "error")

    def on_add_audio_file(self) -> None:
        """Add audio file to segments list"""
        # Choose audio file
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file audio để thêm", "",
            "Audio Files (*.mp3 *.wav *.m4a *.ogg *.flac);;MP3 Files (*.mp3);;WAV Files (*.wav);;All Files (*)")

        if not path:
            return

        try:
            # Use SegmentManager to add audio file
            if self.segment_manager.add_audio_file(path):
                # Update AudioPlayer
                if self.audio_player:
                    valid_paths, valid_durations = self.segment_manager.get_valid_segments()
                    self.audio_player.add_segments(
                        valid_paths, valid_durations)

                    # Hiện player section khi thêm audio file
                    self._show_player_section(True)

                    # Update break button state
                    if hasattr(self, '_update_break_button_state'):
                        current_pos = self.audio_player.get_current_position()
                        self._update_break_button_state(current_pos)

                # Success message
                duration_ms = self.segment_manager.segment_durations[-1]
                success_msg = f"✅ Đã thêm audio: {os.path.basename(path)} ({ms_to_mmss(duration_ms)})"
                self.lbl_status.setText(success_msg)
                self._add_log_item(
                    f"🎵 Đã thêm file audio: {os.path.basename(path)} ({ms_to_mmss(duration_ms)})", "info")
            else:
                QMessageBox.warning(
                    self, "Lỗi", "Không thể đọc được thời lượng của file audio")

        except Exception as e:
            error_msg = f"Không thể thêm file audio: {e}"
            QMessageBox.critical(self, "Lỗi", error_msg)
            self._add_log_item(f"❌ Lỗi thêm audio: {e}", "error")

    def on_add_video_file(self) -> None:
        """Add video file to segments list"""
        # Choose video file
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file video để thêm", "",
            "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv);;MP4 Files (*.mp4);;AVI Files (*.avi);;All Files (*)")

        if not path:
            return

        try:
            # Use SegmentManager to add video file
            if self.segment_manager.add_video_file(path):
                # Update AudioPlayer
                if self.audio_player:
                    valid_paths, valid_durations = self.segment_manager.get_valid_segments()
                    self.audio_player.add_segments(
                        valid_paths, valid_durations)

                    # Hiện player section khi thêm video file
                    self._show_player_section(True)

                    # Update break button state
                    if hasattr(self, '_update_break_button_state'):
                        current_pos = self.audio_player.get_current_position()
                        self._update_break_button_state(current_pos)

                # Success message
                success_msg = f"✅ Đã thêm video: {os.path.basename(path)} (Tạo 3s audio)"
                self.lbl_status.setText(success_msg)
                self._add_log_item(
                    f"🎬 Đã thêm file video: {os.path.basename(path)} (Tạo 3s audio)", "info")
            else:
                QMessageBox.warning(
                    self, "Lỗi", "Không thể tạo audio từ file video")

        except Exception as e:
            error_msg = f"Không thể thêm file video: {e}"
            QMessageBox.critical(self, "Lỗi", error_msg)
            self._add_log_item(f"❌ Lỗi thêm video: {e}", "error")

    def on_remove_selected_segment(self) -> None:
        """Remove selected segment from list"""
        current_row = self.list_segments.currentRow()
        if current_row < 0:
            QMessageBox.information(
                self, "Thông báo", "Vui lòng chọn segment cần xóa")
            return

        if current_row >= len(self.segment_manager.segment_paths):
            QMessageBox.warning(self, "Lỗi", "Segment không hợp lệ")
            return

        # Confirm deletion
        segment_name = os.path.basename(
            self.segment_manager.segment_paths[current_row]) if self.segment_manager.segment_paths[current_row] else f"Segment {current_row + 1}"
        reply = QMessageBox.question(
            self, "Xác nhận xóa",
            f"Bạn có chắc muốn xóa segment:\n{segment_name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # Use SegmentManager to remove segment
                removed_path, removed_duration = self.segment_manager.remove_segment(
                    current_row)

                if removed_path and removed_duration:
                    # Update AudioPlayer
                    if self.audio_player:
                        valid_paths, valid_durations = self.segment_manager.get_valid_segments()
                        self.audio_player.add_segments(
                            valid_paths, valid_durations)

                    # If playing deleted segment, stop playback
                    if self.current_index == current_row:
                        if self.audio_player:
                            self.audio_player.stop()
                        self.current_index = -1
                    elif self.current_index > current_row:
                        # Adjust current_index if needed
                        self.current_index -= 1

                    # Update break button state
                    if hasattr(self, '_update_break_button_state'):
                        current_pos = self.audio_player.get_current_position()
                        self._update_break_button_state(current_pos)

                    # Success message
                    success_msg = f"🗑️ Đã xóa segment: {os.path.basename(removed_path)}"
                    self.lbl_status.setText(success_msg)
                    self._add_log_item(
                        f"🗑️ Đã xóa segment: {os.path.basename(removed_path)}", "info")

            except Exception as e:
                error_msg = f"Không thể xóa segment: {e}"
                QMessageBox.critical(self, "Lỗi", error_msg)
                self._add_log_item(f"❌ Lỗi xóa segment: {e}", "error")

    def on_reorder_segments(self) -> None:
        """Reorder segments"""
        if len(self.segment_manager.segment_paths) < 2:
            QMessageBox.information(
                self, "Thông báo", "Cần ít nhất 2 segments để sắp xếp")
            return

        try:
            # Create reorder dialog
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QLabel

            dialog = QDialog(self)
            dialog.setWindowTitle("Sắp xếp Segments")
            dialog.setModal(True)
            dialog.resize(500, 400)

            layout = QVBoxLayout(dialog)

            # Instruction label
            layout.addWidget(QLabel("Kéo thả để sắp xếp lại thứ tự segments:"))

            # Reorder list widget
            reorder_list = QListWidget()
            reorder_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)

            # Add all segments to list
            for i, (path, duration) in enumerate(zip(self.segment_manager.segment_paths, self.segment_manager.segment_durations)):
                if path and duration:
                    item_text = f"{i+1:02d}. {os.path.basename(path)} — {ms_to_mmss(duration)}"
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.UserRole, i)  # Save original index
                    reorder_list.addItem(item)

            layout.addWidget(reorder_list)

            # Buttons
            btn_layout = QHBoxLayout()
            btn_ok = QPushButton("✅ Áp dụng")
            btn_cancel = QPushButton("❌ Hủy")

            btn_ok.clicked.connect(dialog.accept)
            btn_cancel.clicked.connect(dialog.reject)

            btn_layout.addWidget(btn_ok)
            btn_layout.addWidget(btn_cancel)
            layout.addLayout(btn_layout)

            # Show dialog
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get new order
                new_order = []
                for i in range(reorder_list.count()):
                    item = reorder_list.item(i)
                    original_index = item.data(Qt.UserRole)
                    new_order.append(original_index)

                # Use SegmentManager to reorder segments
                if self.segment_manager.reorder_segments(new_order):
                    # Update AudioPlayer
                    if self.audio_player:
                        valid_paths, valid_durations = self.segment_manager.get_valid_segments()
                        self.audio_player.add_segments(
                            valid_paths, valid_durations)

                    # Update break button state
                    if hasattr(self, '_update_break_button_state'):
                        current_pos = self.audio_player.get_current_position()
                        self._update_break_button_state(current_pos)

                    # Success message
                    self.lbl_status.setText("🔄 Đã sắp xếp lại segments")
                    self._add_log_item(
                        "🔄 Đã sắp xếp lại thứ tự segments", "info")

        except Exception as e:
            error_msg = f"Không thể sắp xếp segments: {e}"
            QMessageBox.critical(self, "Lỗi", error_msg)
            self._add_log_item(f"❌ Lỗi sắp xếp segments: {e}", "error")

    def on_break_segment(self) -> None:
        """Handle segment break button click"""
        try:
            # Check if we have segments
            if not self.segment_manager.segment_paths or not any(self.segment_manager.segment_paths):
                QMessageBox.warning(
                    self, "Lỗi", "Không có segments để ngắt đoạn")
                return

            # Get current position from audio player (current playback position)
            if not self.audio_player:
                QMessageBox.warning(self, "Lỗi", "Audio player chưa sẵn sàng")
                return

            current_pos = self.audio_player.get_current_position()
            if current_pos < 0:
                QMessageBox.warning(
                    self, "Lỗi", "Không thể xác định vị trí hiện tại")
                return

            # Get break duration from combo box
            break_text = self.cmb_break_duration.currentText()
            break_seconds = int(break_text.replace('s', ''))
            break_ms = break_seconds * 1000

            # Find current segment
            segment_index = -1
            segment_start = 0
            segment_duration = 0
            segment_path = ""

            for i, duration in enumerate(self.segment_manager.segment_durations):
                if duration:
                    if segment_start <= current_pos < segment_start + duration:
                        segment_index = i
                        segment_duration = duration
                        segment_path = self.segment_manager.segment_paths[i]
                        break
                    segment_start += duration

            if segment_index == -1:
                QMessageBox.warning(
                    self, "Lỗi", "Không tìm thấy segment chứa vị trí hiện tại")
                return

            # Check if position is at beginning or end of segment
            segment_end = segment_start + segment_duration
            is_at_beginning = abs(
                current_pos - segment_start) <= 1000  # Within 1 second
            # Within 1 second
            is_at_end = abs(current_pos - segment_end) <= 1000

            # Allow breaking at end of segment (after segment)
            if is_at_end:
                # Break after current segment
                break_position = "sau"
                insert_index = segment_index + 1
            elif is_at_beginning:
                # Break before current segment
                break_position = "trước"
                insert_index = segment_index
            else:
                # Break after current segment (at current position)
                break_position = "sau"
                insert_index = segment_index + 1

            # Log break attempt
            self._add_log_item(
                f"✂️ Thử ngắt đoạn tại {ms_to_mmss(current_pos)} - Segment: {os.path.basename(segment_path)}", "blue")

            # Confirm break operation
            reply = QMessageBox.question(
                self, "Xác nhận ngắt đoạn",
                f"Tạo khoảng nghỉ {break_seconds}s khoảng nghỉ {break_position} segment?\n"
                f"Segment: {os.path.basename(segment_path)}\n"
                f"Vị trí: {ms_to_mmss(current_pos)} ({break_position} segment)",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self._add_log_item(
                    f"✅ Xác nhận ngắt đoạn - Tạo {break_seconds}s khoảng nghỉ {break_position} segment", "info")
                self._perform_segment_break(
                    segment_index, segment_path, segment_duration, break_ms, insert_index, break_position)
            else:
                self._add_log_item("❌ Hủy ngắt đoạn", "warning")

        except Exception as e:
            error_msg = f"Không thể ngắt đoạn: {e}"
            QMessageBox.critical(self, "Lỗi", error_msg)
            self._add_log_item(f"❌ Lỗi ngắt đoạn: {e}", "error")

    def _perform_segment_break(self, segment_index: int, segment_path: str,
                               segment_duration: int, break_ms: int, insert_index: int, break_position: str) -> None:
        """Perform the actual segment break operation"""
        try:
            # Use SegmentManager to add gap segment
            if self.segment_manager.add_gap_segment(break_ms, insert_index, break_position):
                # Update AudioPlayer
                if self.audio_player:
                    valid_paths, valid_durations = self.segment_manager.get_valid_segments()
                    self.audio_player.add_segments(
                        valid_paths, valid_durations)

                # Update break button state
                if hasattr(self, '_update_break_button_state'):
                    current_pos = self.audio_player.get_current_position()
                    self._update_break_button_state(current_pos)

                # Success message
                break_seconds = break_ms / 1000
                success_msg = f"Đã ngắt đoạn thành công!\nTạo {break_seconds}s khoảng nghỉ {break_position} segment.\nAudio gốc được giữ nguyên."
                QMessageBox.information(self, "Thành công", success_msg)

                # Update status
                status_msg = f"✂️ Đã ngắt đoạn tại {ms_to_mmss(self.audio_player.get_current_position())} - Tạo {break_seconds}s khoảng nghỉ"
                self.lbl_status.setText(status_msg)

                # Log success
                self._add_log_item(
                    f"✂️ Đã ngắt đoạn thành công! Tạo {break_seconds}s khoảng nghỉ {break_position} segment", "info")
            else:
                raise Exception("Không thể tạo gap segment")

        except Exception as e:
            error_msg = f"Không thể thực hiện ngắt đoạn: {e}"
            QMessageBox.critical(self, "Lỗi", error_msg)
            self._add_log_item(f"❌ Lỗi thực hiện ngắt đoạn: {e}", "error")

    # Các method này đã được chuyển sang SegmentManager

    def on_test_loop(self) -> None:
        """Test loop condition manually"""
        if not self.segment_manager.segment_paths or not any(self.segment_manager.segment_paths):
            QMessageBox.information(
                self, "Thông báo", "Chưa có segments để test loop")
            return

        # Check loop condition
        should_loop = self._should_start_loop()

        # Show detailed information
        if self.audio_player:
            current_pos = self.audio_player.get_current_position()
            total_dur = self.audio_player.get_total_duration()
        else:
            current_pos = 0
            total_dur = self.segment_manager.total_known_ms

        info_text = f"🔍 Loop Test Results:\n\n"
        info_text += f"Current Position: {current_pos}ms ({ms_to_mmss(current_pos)})\n"
        info_text += f"Total Duration: {total_dur}ms ({ms_to_mmss(total_dur)})\n"
        info_text += f"Loop Enabled: {self.audio_player.chk_loop.isChecked()}\n"
        info_text += f"Should Loop: {should_loop}\n\n"

        if should_loop:
            info_text += "✅ Điều kiện loop đã thỏa mãn!\n"
            info_text += "Có thể bắt đầu loop từ segment đầu tiên."
        else:
            info_text += "⏸️ Chưa đủ điều kiện để loop.\n"
            info_text += f"Cần phát thêm {total_dur - current_pos}ms nữa."

        QMessageBox.information(self, "Loop Test", info_text)

    def _should_start_loop(self) -> bool:
        """Check if should start loop"""
        if not self.audio_player.chk_loop.isChecked():
            return False

        current_global_pos = self.audio_player.get_current_position()
        total_duration = self.audio_player.get_total_duration()

        # Only loop when completely finished
        should_loop = current_global_pos >= total_duration

        return should_loop

    def on_start(self) -> None:
        """Start TTS processing"""
        # Stop old worker if running
        if self.worker and self.worker.isRunning():
            self.worker.stop()

        # Reset AudioPlayer
        if self.audio_player:
            self.audio_player.clear_segments()

        clean_all_temp_parts()
        # Reset segments list using SegmentManager
        self.segment_manager.clear_segments()
        self.current_index = -1
        # Reset progress bar từ main window và hiện lên
        self._reset_progress()
        self._update_progress_title("Tiến trình xử lý")
        # Hiện progress bar khi bắt đầu TTS
        try:
            if hasattr(self.parent_main, 'progress_bar'):
                self.parent_main.progress_bar.setVisible(True)
        except Exception as e:
            print(f"[TTS PROGRESS ERROR] {e}")
        self.lbl_status.setText("Sẵn sàng")

        # Reset break segment controls
        if hasattr(self, 'cmb_break_duration'):
            self.cmb_break_duration.setCurrentText("3s")

        # Ẩn player section khi bắt đầu
        self._show_player_section(False)

        # Check input text
        text = self.text_input_edge_tts.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Thiếu nội dung",
                                "Dán hoặc mở file .txt trước khi bắt đầu.")
            return

        # Create new worker
        self.worker = MTProducerWorker(
            text, "vi-VN-HoaiMyNeural", 0, 0, 500, 4)

        # Connect signals
        self.worker.segment_ready.connect(self.on_segment_ready)
        self.worker.progress.connect(self.on_produce_progress)
        self.worker.status.connect(self.on_status)
        self.worker.all_done.connect(self.on_all_done)
        self.worker.error.connect(self.on_error)

        # Update UI
        self.btn_start_edge_tts.setEnabled(False)
        self.btn_end_edge_tts.setEnabled(True)
        status_msg = f"🔄 Đang sinh audio ({self.theard_edge_tts.value()} luồng)…"
        self.lbl_status.setText(status_msg)

        # Update progress title
        self._update_progress_title(
            f"TTS - Đang sinh audio ({self.theard_edge_tts.value()} luồng)")

        # Log start
        self._add_log_item(
            f"🚀 Bắt đầu TTS với {self.theard_edge_tts.value()} luồng", "info")

        # Start worker
        self.worker.start()

    def on_end_all(self) -> None:
        """Stop all processes"""
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

        # Stop AudioPlayer
        if self.audio_player:
            try:
                self.audio_player.stop()
            except Exception as e:
                print(
                    f"Warning: Error stopping audio player in on_end_all: {e}")

        # Clear segments list using SegmentManager
        self.segment_manager.clear_segments()
        self.current_index = -1

        # Reset break segment controls
        if hasattr(self, 'cmb_break_duration'):
            self.cmb_break_duration.setCurrentText("3s")

        # Ẩn player section khi kết thúc
        self._show_player_section(False)

        self.btn_end_edge_tts.setEnabled(False)
        self.btn_start_edge_tts.setEnabled(True)
        self.lbl_status.setText("⏹ Đã kết thúc.")

        # Update progress title and hide progress bar
        self._update_progress_title("")
        self._reset_progress()

        # Log end
        self._add_log_item("⏹ Đã kết thúc TTS", "info")

    # ==================== Worker callbacks ====================

    def on_segment_ready(self, path: str, duration_ms: int, index1: int) -> None:
        """Callback when audio segment is ready"""
        self._ensure_capacity(index1)
        self.segment_manager.segment_paths[index1 - 1] = path
        self.segment_manager.segment_durations[index1 - 1] = duration_ms

        # Update total duration
        self.segment_manager._update_total_duration()

        # Update segments display with detailed time information
        self.segment_manager._update_display()

        # Update AudioPlayer
        if self.audio_player:
            valid_paths, valid_durations = self.segment_manager.get_valid_segments()
            self.audio_player.add_segments(valid_paths, valid_durations)

            # Hiện player section khi có segment đầu tiên
            if index1 == 1:
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

    def _ensure_capacity(self, n: int) -> None:
        """Ensure segments list has enough capacity"""
        while len(self.segment_manager.segment_paths) < n:
            self.segment_manager.segment_paths.append(None)
            self.segment_manager.segment_durations.append(None)

    def on_produce_progress(self, emitted: int, total: int) -> None:
        """Callback for processing progress"""
        # Update progress bar từ main window
        self._update_progress(int(emitted / total * 100))

    def on_status(self, msg: str) -> None:
        """Callback for status messages"""
        self.lbl_status.setText(msg)

    def on_all_done(self) -> None:
        """Callback when all processing is done"""
        self.lbl_status.setText(self.lbl_status.text())
        self.btn_start_edge_tts.setEnabled(True)
        self.btn_end_edge_tts.setEnabled(False)
        self._update_progress_title("")
        self._reset_progress()

        # Log completion
        self._add_log_item("✅ TTS hoàn thành tất cả segments", "info")

    def on_error(self, msg: str) -> None:
        """Callback for errors"""
        QMessageBox.critical(self, "Lỗi", msg)
        self.btn_end_edge_tts.setEnabled(False)
        self.btn_start_edge_tts.setEnabled(True)

        # Log error
        self._add_log_item(f"❌ Lỗi TTS: {msg}", "error")

    def _add_log_item(self, message: str, level: str = "info") -> None:
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

    def _ensure_progress_visible(self) -> None:
        """Ensure progress bar and title are properly configured from main window"""
        try:
            # Không force hiển thị, để progress bar tự quyết định visibility
            pass
        except Exception as e:
            print(f"[TTS PROGRESS VISIBILITY ERROR] {e}")

    def _print_segments_info(self) -> None:
        """Print detailed information about all segments"""
        if not self.segment_manager.segment_durations or not any(self.segment_manager.segment_durations):
            self._add_log_item("📋 Không có segments để hiển thị", "warning")
            return

        # Log segments information
        self._add_log_item("📋 Thông tin chi tiết Segments:", "info")

        # Use SegmentManager to get statistics
        stats = self.segment_manager.get_segments_statistics()

        # Log summary
        self._add_log_item(
            f"📊 Tổng thời lượng: {ms_to_mmss(stats['total_duration'])}", "info")
        self._add_log_item(
            f"📊 Tổng segments: {stats['total_segments']}", "info")

        # Additional statistics
        self._add_log_item(f"📊 TTS segments: {stats['tts_count']}", "blue")
        self._add_log_item(f"📊 Gap segments: {stats['gap_count']}", "blue")
        self._add_log_item(
            f"📊 Broken segments: {stats['broken_count']}", "blue")

    def on_list_item_double_clicked(self, item) -> None:
        """Callback when double-clicking list item"""
        row = self.list_segments.row(item)
        if 0 <= row < len(self.segment_manager.segment_paths) and self.segment_manager.segment_paths[row]:
            if self.audio_player:
                # Calculate global position for this segment
                global_offset = sum((d or 0)
                                    for d in self.segment_manager.segment_durations[:row])
                self.audio_player.seek_to(global_offset)

    # ==================== Export MP3 ====================

    def on_export_mp3(self) -> None:
        """Export MP3 from segments with proper gap handling"""
        parts = [p for p in self.segment_manager.segment_paths if p]
        if not parts:
            QMessageBox.information(
                self, "Chưa có dữ liệu", "Chưa có đoạn nào để xuất.")
            return

        # Choose save location
        default_name = f"Player_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Chọn nơi lưu MP3", str(
                AppConfig.OUTPUT_DIR / default_name), "MP3 Files (*.mp3)"
        )
        if not out_path:
            return

        try:
            prepare_pydub_ffmpeg()
            gap_ms = self.gap_spin_edge_tts.value()
            final = AudioSegment.silent(duration=0)

            total_ms = 0
            valid_count = 0

            # Concatenate segments with smart gap handling
            for i, p in enumerate(parts):
                try:
                    seg = AudioSegment.from_file(p)
                    final += seg

                    # Add gap between segments (but not after the last one)
                    if i < len(parts) - 1:
                        # Check if next segment is a gap segment
                        next_path = parts[i + 1] if i + \
                            1 < len(parts) else None
                        if next_path and "gap_" in next_path:
                            # Skip adding extra gap since gap segment already exists
                            pass
                        else:
                            # Add normal gap
                            gap = AudioSegment.silent(duration=gap_ms)
                            final += gap

                    d = get_mp3_duration_ms(p)
                    total_ms += d
                    valid_count += 1
                except Exception as e:
                    print(f"Warning: Could not process segment {p}: {e}")
                    continue

            if valid_count == 0:
                QMessageBox.warning(self, "Xuất thất bại",
                                    "Không ghép được dữ liệu hợp lệ.")
                return

            # Export MP3 file
            final.export(out_path, format="mp3")

            # Show success message with details
            gap_count = sum(1 for p in parts if "gap_" in p)
            if gap_count > 0:
                success_msg = f"Đã xuất MP3 với {gap_count} khoảng nghỉ:\n{out_path}\nTổng thời lượng: {ms_to_mmss(total_ms)}"
                QMessageBox.information(self, "Thành công", success_msg)
                self._add_log_item(
                    f"💾 Đã xuất MP3 với {gap_count} khoảng nghỉ - {ms_to_mmss(total_ms)}", "info")
            else:
                success_msg = f"Đã xuất MP3:\n{out_path}"
                QMessageBox.information(self, "Thành công", success_msg)
                self._add_log_item(
                    f"💾 Đã xuất MP3 thành công - {ms_to_mmss(total_ms)}", "info")

        except Exception as e:
            error_msg = f"Không thể xuất MP3:\n{e}"
            QMessageBox.critical(self, "Lỗi xuất", error_msg)
            self._add_log_item(f"❌ Lỗi xuất MP3: {e}", "error")

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
                print(f"Warning: Error stopping worker: {e}")
                # Force cleanup
                try:
                    if hasattr(self, 'worker') and self.worker:
                        self.worker.terminate()
                        self.worker.wait(1000)
                        self.worker = None
                except:
                    pass

        # Stop AudioPlayer
        if self.audio_player:
            try:
                self.audio_player.stop()
            except Exception as e:
                print(f"Warning: Error stopping audio player: {e}")

        # Clean temp files
        try:
            clean_all_temp_parts()
            # Also clean break segment temp files
            temp_dir = AppConfig.TEMP_DIR
            if temp_dir.exists():
                for temp_file in temp_dir.glob("part*_*.mp3"):
                    try:
                        temp_file.unlink()
                    except Exception as e:
                        print(
                            f"Warning: Could not delete temp file {temp_file}: {e}")
                for temp_file in temp_dir.glob("gap_*.mp3"):
                    try:
                        temp_file.unlink()
                    except Exception as e:
                        print(
                            f"Warning: Could not delete temp file {temp_file}: {e}")
        except Exception as e:
            print(f"Warning: Error cleaning temp files: {e}")

        # Ẩn player section
        self._show_player_section(False)

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
