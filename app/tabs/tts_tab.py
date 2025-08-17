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

import os
from datetime import datetime
from pathlib import Path

# Import modules
from app.uiToolbarTab import UIToolbarTab
from app.appConfig import AppConfig
from app.history.historyItem_TTS import TTSHistoryItem
from app.workers import MTProducerWorker

# Import constants
from ..constants import (
    DEFAULT_WORKERS_PLAYER, DEFAULT_MAXLEN, DEFAULT_GAP_MS, OUTPUT_DIR
)
from app.utils.helps import (
    ms_to_mmss, clean_all_temp_parts, get_mp3_duration_ms, 
    prepare_pydub_ffmpeg
)

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
        self.segment_paths: List[Optional[str]] = []
        self.segment_durations: List[Optional[int]] = []
        self.total_known_ms: int = 0
        self.current_index: int = -1
        self.worker: Optional[MTProducerWorker] = None
        self.file_output: str = ""
        self.audio_player: Optional[AudioPlayer] = None

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
            self.parent_main.status.showMessage("TTS Tab sẵn sàng")

    def _setup_history_system(self) -> None:
        """Setup history system"""
        hist = self.enable_history(
            hist_title="Lịch sử TTS",
            item_factory=lambda text, ts, lang, meta: TTSHistoryItem(text, ts, lang, meta),
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
        self.theard_edge_tts.setValue(DEFAULT_WORKERS_PLAYER)
        self.theard_edge_tts.setSuffix(" Thread")

        # Max length spinbox
        self.maxlen_spin_edge_tts = QSpinBox()
        self.maxlen_spin_edge_tts.setRange(80, 2000)
        self.maxlen_spin_edge_tts.setValue(DEFAULT_MAXLEN)
        self.maxlen_spin_edge_tts.setSuffix(" ký tự/đoạn")

        # Gap spinbox
        self.gap_spin_edge_tts = QSpinBox()
        self.gap_spin_edge_tts.setRange(0, 2000)
        self.gap_spin_edge_tts.setValue(DEFAULT_GAP_MS)
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
        self.text_input_edge_tts.setMinimumHeight(200)
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
        row_layout = QHBoxLayout()
        
        # Create buttons
        self.btn_say = QPushButton("🔊 Chuyển đổi")
        self.btn_save = QPushButton("💾 Lưu")
        self.btn_stop = QPushButton("⏹️ Dừng")
        self.btn_clear_chunks = QPushButton("🗑️ Xóa Chunks")
        self.btn_info = QPushButton("ℹ️ Info")
        self.btn_add_audio = QPushButton("🎵 Thêm Audio")
        self.btn_remove_segment = QPushButton("❌ Xóa Segment")
        self.btn_reorder = QPushButton("🔄 Sắp xếp")
        self.btn_test_loop = QPushButton("🔄 Test Loop")
        
        # Connect buttons
        self.btn_info.clicked.connect(self._print_segments_info)
        self.btn_add_audio.clicked.connect(self.on_add_audio_file)
        self.btn_remove_segment.clicked.connect(self.on_remove_selected_segment)
        self.btn_reorder.clicked.connect(self.on_reorder_segments)
        self.btn_test_loop.clicked.connect(self.on_test_loop)
        
        # Apply style to buttons
        for btn in (self.btn_say, self.btn_save, self.btn_stop, self.btn_clear_chunks, 
                   self.btn_info, self.btn_add_audio, self.btn_remove_segment, 
                   self.btn_reorder, self.btn_test_loop):
            btn.setStyleSheet(AppConfig.BUTTON_STYLE)
            btn.setMinimumWidth(80)
            btn.setMaximumWidth(120)
            row_layout.addWidget(btn)
        
        row_layout.addStretch()
        content_layout.addLayout(row_layout)

    def _create_segments_list(self, content_layout: QVBoxLayout) -> None:
        """Create segments list"""
        self.list_segments = QListWidget()
        content_layout.addWidget(self.list_segments, 2)

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
        
        # Keep progress bar for TTS generation
        self.progress_gen = QProgressBar()
        self.progress_gen.setRange(0, 100)
        self.progress_gen.setValue(0)
        
        # Add progress bar to container
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("Tiến độ TTS:"))
        progress_layout.addWidget(self.progress_gen, 1)
        player_layout.addLayout(progress_layout)
        
        # Add container to root layout
        root_layout.addWidget(self.player_container)

    def _setup_audio_system(self) -> None:
        """Setup audio system"""
        # Connect signals from AudioPlayer
        self.audio_player.position_changed.connect(self.on_audio_position_changed)
        self.audio_player.segment_changed.connect(self.on_audio_segment_changed)
        self.audio_player.playback_state_changed.connect(self.on_audio_playback_state_changed)

    def _show_player_section(self, show: bool = True) -> None:
        """Show or hide player section"""
        if hasattr(self, 'player_container'):
            self.player_container.setVisible(show)
            
            # Nếu ẩn player, cũng ẩn progress bar
            if hasattr(self, 'progress_gen'):
                self.progress_gen.setVisible(show)

    def _connect_signals(self) -> None:
        """Connect signals"""
        # Connect double click on list segments
        if hasattr(self, 'list_segments'):
            self.list_segments.itemDoubleClicked.connect(self.on_list_item_double_clicked)

    def append_history(self, text: str, meta: Optional[dict] = None) -> None:
        """Add item to TTS history"""
        if self.history:
            self.history.panel.add_history(text, meta=meta or {})

    def _on_history_selected(self, text: str) -> None:
        """Callback when history item is selected"""
        self.text_input_edge_tts.setPlainText(text)
        self.text_input_edge_tts.setFocus()

    # ==================== AudioPlayer Callbacks ====================
    
    def on_audio_position_changed(self, position_ms: int) -> None:
        """Callback when audio position changes from AudioPlayer"""
        # Update TTS progress bar
        if hasattr(self, 'progress_gen'):
            total_ms = self.audio_player.get_total_duration()
            if total_ms > 0:
                progress = int((position_ms / total_ms) * 100)
                self.progress_gen.setValue(progress)
    
    def on_audio_segment_changed(self, segment_index: int) -> None:
        """Callback when audio segment changes from AudioPlayer"""
        self.current_index = segment_index
        # Update UI
        if hasattr(self, 'list_segments') and segment_index >= 0:
            self.list_segments.setCurrentRow(segment_index)
    
    def on_audio_playback_state_changed(self, is_playing: bool) -> None:
        """Callback when playback state changes from AudioPlayer"""
        pass

    # ==================== Event Handlers ====================

    def on_open_file(self) -> None:
        """Open text file and read content"""
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file văn bản", "", "Text Files (*.txt);;All Files (*)")
        if not path:
            return
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.text_input_edge_tts.setPlainText(f.read())
            self.lbl_status.setText(f"📄 Đã mở: {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không đọc được file: {e}")

    def on_add_audio_file(self) -> None:
        """Add audio file to segments list"""
        # Choose audio file
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file audio để thêm", "", 
            "Audio Files (*.mp3 *.wav *.m4a *.ogg *.flac);;MP3 Files (*.mp3);;WAV Files (*.wav);;All Files (*)")
        
        if not path:
            return
        
        try:
            # Get audio duration
            duration_ms = get_mp3_duration_ms(path)
            if duration_ms <= 0:
                QMessageBox.warning(self, "Lỗi", "Không thể đọc được thời lượng của file audio")
                return
            
            # Add to list
            self.segment_paths.append(path)
            self.segment_durations.append(duration_ms)
            
            # Update total duration
            self.total_known_ms = sum(d or 0 for d in self.segment_durations)
            
            # Update AudioPlayer
            if self.audio_player:
                valid_paths = [p for p in self.segment_paths if p]
                valid_durations = [d for d in self.segment_durations if d]
                self.audio_player.add_segments(valid_paths, valid_durations)
                
                # Hiện player section khi thêm audio file
                self._show_player_section(True)
            
            # Create display text for new segment
            segment_index = len(self.segment_paths)
            line = f"{segment_index:03d}. {os.path.basename(path)}  —  {ms_to_mmss(duration_ms)} (Thêm thủ công)"
            
            # Add to list widget
            self.list_segments.addItem(QListWidgetItem(line))
            
            # Success message
            self.lbl_status.setText(f"✅ Đã thêm audio: {os.path.basename(path)} ({ms_to_mmss(duration_ms)})")
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể thêm file audio: {e}")

    def on_remove_selected_segment(self) -> None:
        """Remove selected segment from list"""
        current_row = self.list_segments.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Thông báo", "Vui lòng chọn segment cần xóa")
            return
        
        if current_row >= len(self.segment_paths):
            QMessageBox.warning(self, "Lỗi", "Segment không hợp lệ")
            return
        
        # Confirm deletion
        segment_name = os.path.basename(self.segment_paths[current_row]) if self.segment_paths[current_row] else f"Segment {current_row + 1}"
        reply = QMessageBox.question(
            self, "Xác nhận xóa", 
            f"Bạn có chắc muốn xóa segment:\n{segment_name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Remove segment
                removed_path = self.segment_paths.pop(current_row)
                removed_duration = self.segment_durations.pop(current_row)
                
                # Remove from list widget
                self.list_segments.takeItem(current_row)
                
                # Update total duration
                self.total_known_ms = sum(d or 0 for d in self.segment_durations)
                
                # Update AudioPlayer
                if self.audio_player:
                    valid_paths = [p for p in self.segment_paths if p]
                    valid_durations = [d for d in self.segment_durations if d]
                    self.audio_player.add_segments(valid_paths, valid_durations)
                
                # If playing deleted segment, stop playback
                if self.current_index == current_row:
                    if self.audio_player:
                        self.audio_player.stop()
                    self.current_index = -1
                elif self.current_index > current_row:
                    # Adjust current_index if needed
                    self.current_index -= 1
                
                # Success message
                self.lbl_status.setText(f"🗑️ Đã xóa segment: {os.path.basename(removed_path)}")
                
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể xóa segment: {e}")

    def on_reorder_segments(self) -> None:
        """Reorder segments"""
        if len(self.segment_paths) < 2:
            QMessageBox.information(self, "Thông báo", "Cần ít nhất 2 segments để sắp xếp")
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
            for i, (path, duration) in enumerate(zip(self.segment_paths, self.segment_durations)):
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
                
                # Reorder segments
                new_paths = [self.segment_paths[i] for i in new_order]
                new_durations = [self.segment_durations[i] for i in new_order]
                
                # Update lists
                self.segment_paths = new_paths
                self.segment_durations = new_durations
                
                # Update total duration
                self.total_known_ms = sum(d or 0 for d in self.segment_durations)
                
                # Update AudioPlayer
                if self.audio_player:
                    valid_paths = [p for p in self.segment_paths if p]
                    valid_durations = [d for d in self.segment_durations if d]
                    self.audio_player.add_segments(valid_paths, valid_durations)
                
                # Update list widget
                self.list_segments.clear()
                for i, (path, duration) in enumerate(zip(self.segment_paths, self.segment_durations)):
                    if path and duration:
                        line = f"{i+1:03d}. {os.path.basename(path)}  —  {ms_to_mmss(duration)}"
                        self.list_segments.addItem(QListWidgetItem(line))
                
                # Success message
                self.lbl_status.setText("🔄 Đã sắp xếp lại segments")
                
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể sắp xếp segments: {e}")

    def on_test_loop(self) -> None:
        """Test loop condition manually"""
        if not self.segment_paths or not any(self.segment_paths):
            QMessageBox.information(self, "Thông báo", "Chưa có segments để test loop")
            return
        
        # Check loop condition
        should_loop = self._should_start_loop()
        
        # Show detailed information
        if self.audio_player:
            current_pos = self.audio_player.get_current_position()
            total_dur = self.audio_player.get_total_duration()
        else:
            current_pos = 0
            total_dur = self.total_known_ms
        
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
        # Reset segments list
        self.segment_paths.clear()
        self.segment_durations.clear()
        self.total_known_ms = 0
        self.current_index = -1
        self.list_segments.clear()
        self.progress_gen.setValue(0)
        self.lbl_status.setText("Sẵn sàng")
        
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
        self.lbl_status.setText(
            f"🔄 Đang sinh audio ({self.theard_edge_tts.value()} luồng)…")
        
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
                print(f"Warning: Error stopping audio player in on_end_all: {e}")
        
        # Ẩn player section khi kết thúc
        # self._show_player_section(False)
        
        self.btn_end_edge_tts.setEnabled(False)
        self.btn_start_edge_tts.setEnabled(True)
        self.lbl_status.setText("⏹ Đã kết thúc.")

    # ==================== Worker callbacks ====================

    def on_segment_ready(self, path: str, duration_ms: int, index1: int) -> None:
        """Callback when audio segment is ready"""
        self._ensure_capacity(index1)
        self.segment_paths[index1 - 1] = path
        self.segment_durations[index1 - 1] = duration_ms

        # Update total duration
        self.total_known_ms = sum(d or 0 for d in self.segment_durations)
        
        # Create display text for segment
        line = f"{index1:03d}. {os.path.basename(path)}  —  {ms_to_mmss(duration_ms)}"
        
        # Update list segments
        if index1 - 1 < self.list_segments.count():
            self.list_segments.item(index1 - 1).setText(line)
        else:
            # Add placeholder for incomplete segments
            while self.list_segments.count() < index1 - 1:
                self.list_segments.addItem(QListWidgetItem("(đang tạo...)"))
            self.list_segments.addItem(QListWidgetItem(line))

        # Update AudioPlayer
        if self.audio_player:
            valid_paths = [p for p in self.segment_paths if p]
            valid_durations = [d for d in self.segment_durations if d]
            self.audio_player.add_segments(valid_paths, valid_durations)
            
            # Hiện player section khi có segment đầu tiên
            if index1 == 1:
                self._show_player_section(True)

        # Auto-play first segment if nothing is playing
        if self.current_index < 0 and self.segment_paths and self.segment_paths[0]:
            if self.audio_player:
                self.audio_player.play()

    def _ensure_capacity(self, n: int) -> None:
        """Ensure segments list has enough capacity"""
        while len(self.segment_paths) < n:
            self.segment_paths.append(None)
            self.segment_durations.append(None)

    def on_produce_progress(self, emitted: int, total: int) -> None:
        """Callback for processing progress"""
        self.progress_gen.setValue(int(emitted / total * 100))

    def on_status(self, msg: str) -> None:
        """Callback for status messages"""
        self.lbl_status.setText(msg)

    def on_all_done(self) -> None:
        """Callback when all processing is done"""
        self.lbl_status.setText(self.lbl_status.text() + "  ✅ Xong.")
        self.btn_start_edge_tts.setEnabled(True)
        self.btn_end_edge_tts.setEnabled(False)



    def on_error(self, msg: str) -> None:
        """Callback for errors"""
        QMessageBox.critical(self, "Lỗi", msg)
        self.btn_end_edge_tts.setEnabled(False)
        self.btn_start_edge_tts.setEnabled(True)

    def _print_segments_info(self) -> None:
        """Print detailed information about all segments"""
        if not self.segment_durations or not any(self.segment_durations):
            print("📋 No segments available")
            return
        
        print("📋 Segments Information:")
        total_duration = 0
        cumulative_time = 0
        
        for i, (path, duration) in enumerate(zip(self.segment_paths, self.segment_durations)):
            if duration:
                segment_start = cumulative_time
                segment_end = cumulative_time + duration
                filename = os.path.basename(path) if path else "No path"
                
                # Check if manually added segment
                is_manual = " (Thêm thủ công)" if "Thêm thủ công" in self.list_segments.item(i).text() else ""
                
                print(f"  [{i:02d}] {filename}{is_manual}")
                print(f"       Duration: {duration}ms ({ms_to_mmss(duration)})")
                print(f"       Range: {ms_to_mmss(segment_start)} to {ms_to_mmss(segment_end)}")
                print(f"       Global offset: {cumulative_time}ms ({ms_to_mmss(cumulative_time)})")
                
                total_duration += duration
                cumulative_time += duration
        
        print(f"📊 Total duration: {total_duration}ms ({ms_to_mmss(total_duration)})")
        print(f"📊 Total segments: {len([d for d in self.segment_durations if d])}")
        
        # Additional statistics
        manual_count = sum(1 for i in range(self.list_segments.count()) 
                          if "Thêm thủ công" in self.list_segments.item(i).text())
        tts_count = len([d for d in self.segment_durations if d]) - manual_count
        
        print(f"📊 TTS segments: {tts_count}")
        print(f"📊 Manual audio: {manual_count}")

    def on_list_item_double_clicked(self, item) -> None:
        """Callback when double-clicking list item"""
        row = self.list_segments.row(item)
        if 0 <= row < len(self.segment_paths) and self.segment_paths[row]:
            if self.audio_player:
                # Calculate global position for this segment
                global_offset = sum((d or 0) for d in self.segment_durations[:row])
                self.audio_player.seek_to(global_offset)

    # ==================== Export MP3 ====================

    def on_export_mp3(self) -> None:
        """Export MP3 from segments"""
        parts = [p for p in self.segment_paths if p]
        if not parts:
            QMessageBox.information(
                self, "Chưa có dữ liệu", "Chưa có đoạn nào để xuất.")
            return

        # Choose save location
        default_name = f"Player_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Chọn nơi lưu MP3", str(OUTPUT_DIR / default_name), "MP3 Files (*.mp3)"
        )
        if not out_path:
            return

        try:
            prepare_pydub_ffmpeg()
            gap_ms = self.gap_spin_edge_tts.value()
            gap = AudioSegment.silent(duration=gap_ms)
            final = AudioSegment.silent(duration=0)

            total_ms = 0
            valid_count = 0
            
            # Concatenate segments
            for p in parts:
                try:
                    seg = AudioSegment.from_file(p)
                    final += seg + gap
                    d = get_mp3_duration_ms(p)
                    total_ms += d
                    valid_count += 1
                except Exception:
                    pass

            if valid_count == 0:
                QMessageBox.warning(self, "Xuất thất bại",
                                    "Không ghép được dữ liệu hợp lệ.")
                return

            # Export MP3 file
            final.export(out_path, format="mp3")
            QMessageBox.information(
                self, "Thành công", f"Đã xuất MP3:\n{out_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Lỗi xuất", f"Không thể xuất MP3:\n{e}")

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
