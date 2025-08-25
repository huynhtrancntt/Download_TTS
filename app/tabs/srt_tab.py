# -*- coding: utf-8 -*-
import re
import os
import shutil
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QFileDialog, QHBoxLayout,
    QAbstractItemView, QGroupBox, QLabel, QListWidget
)

from PySide6.QtWidgets import QHeaderView
from app.workers.translate_workers import MultiThreadTranslateWorker

from PySide6.QtWidgets import QProgressBar

from typing import Optional, List, Dict, Tuple
from app.core.audio_player import AudioPlayer
from app.workers.TTS_workers import MTProducerWorker
from app.core.segment_manager import SegmentManager
from app.core.language_manager import language_manager

def parse_srt(text: str):
    """Trả về danh sách [(index, timestamp, content), ...] nếu hợp lệ."""
    blocks = text.strip().split("\n\n")

    timestamp_pattern = re.compile(
        r"^\d{2}:\d{2}:\d{2},\d{3}\s-->\s\d{2}:\d{2}:\d{2},\d{3}$"
    )

    results = []

    for i, block in enumerate(blocks, start=1):
        lines = block.strip().splitlines()

        if len(lines) < 3:
            return None

        if not lines[0].isdigit() or int(lines[0]) != i:
            return None

        if not timestamp_pattern.match(lines[1]):
            return None

        content = " ".join(lines[2:])
        results.append((i, lines[1], content))

    return results


class SRTChecker(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kiểm tra, Chỉnh sửa & Dịch SRT")
        self.resize(800, 500)
        self._initialize_state_variables()

        layout = QVBoxLayout(self)

        # Ô nhập nội dung
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Dán nội dung SRT vào đây...")
        layout.addWidget(self.text_edit)

        # Nút kiểm tra
        self.btn_check = QPushButton("Kiểm tra & Hiển thị")
        self.btn_check.clicked.connect(self.check_and_show)
        layout.addWidget(self.btn_check)

        # Bảng hiển thị (thêm cột Dịch)
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Thời gian", "Nội dung", "Dịch"])
        self.table.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.table.setWordWrap(True)
        # Tự giãn cột nội dung và dịch theo chiều ngang, tự tính chiều cao dòng
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(
            0, QHeaderView.ResizeToContents)  # Thời gian
        header.setSectionResizeMode(
            1, QHeaderView.Stretch)           # Nội dung
        header.setSectionResizeMode(2, QHeaderView.Stretch)           # Dịch
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        layout.addWidget(self.table)

        # Nhóm nút dịch
        btn_layout = QHBoxLayout()
        self.btn_translate_all = QPushButton("Dịch tất cả")
        self.btn_translate_all.clicked.connect(self.translate_all)
        btn_layout.addWidget(self.btn_translate_all)

        layout.addLayout(btn_layout)

        # Nút mở và lưu
        btn_file_layout = QHBoxLayout()
        self.btn_open = QPushButton("Mở file SRT…")
        self.btn_open.clicked.connect(self.open_srt)
        btn_file_layout.addWidget(self.btn_open)

        self.btn_save = QPushButton("Lưu ra file SRT (có dịch)")
        self.btn_save.clicked.connect(self.save_srt)
        btn_file_layout.addWidget(self.btn_save)

        # Thêm nút đọc audio
        self.btn_play_audio = QPushButton("Đọc audio")
        self.btn_play_audio.clicked.connect(self.play_audio)
        btn_file_layout.addWidget(self.btn_play_audio)

        layout.addLayout(btn_file_layout)

        # Add segment manager UI
        self._create_segment_manager_section(layout)
        
        # Segment management
        self.segment_manager = SegmentManager()
        
        # Setup audio system
        self._setup_audio_system()

    def _initialize_state_variables(self) -> None:
        # Audio system
        self.audio_player: Optional[AudioPlayer] = None
        self.tts_worker: Optional[MTProducerWorker] = None
        self.is_playing_sequence = False
        self.current_index: int = -1
        self.is_reading_audio: bool = False

    def _setup_audio_system(self) -> None:
        """Setup audio system for text reading"""
        # Create AudioPlayer
        self.audio_player = AudioPlayer()
        
        # Connect audio player signals
        if self.audio_player:
            # Bật lặp lại mặc định cho AudioPlayer
            try:
                if hasattr(self.audio_player, 'chk_loop'):
                    self.audio_player.chk_loop.setChecked(True)
            except Exception:
                pass

            self.audio_player.position_changed.connect(self._on_audio_position_changed)
            self.audio_player.segment_changed.connect(self._on_audio_segment_changed)
            self.audio_player.playback_state_changed.connect(self._on_audio_playback_state_changed)
            self.audio_player.status_signal.connect(self._on_audio_status_changed)
            # Thêm callback khi audio phát xong để tự động dừng
            if hasattr(self.audio_player, 'playback_finished'):
                self.audio_player.playback_finished.connect(self._on_audio_finished)
        # Setup segment manager after audio player is created
        self._setup_segment_manager()

    def _on_audio_position_changed(self, position_ms: int) -> None:
        """Callback khi vị trí audio thay đổi"""
        try:
            pass
        except Exception as e:
            print(f"Error handling audio position change: {e}")

    def _on_audio_segment_changed(self, segment_index: int) -> None:
        """Callback khi segment audio thay đổi"""
        try:
            # Highlight current segment in the list
            if hasattr(self, 'segment_list') and self.segment_list and 0 <= segment_index < self.segment_list.count():
                self.segment_list.setCurrentRow(segment_index)
            
            # Log khi chuyển segment
            if hasattr(self, 'segment_manager') and self.segment_manager:
                total_segments = len([p for p in self.segment_manager.segment_paths if p])
                if segment_index < total_segments:
                    segment_name = os.path.basename(self.segment_manager.segment_paths[segment_index]) if self.segment_manager.segment_paths[segment_index] else f"Segment {segment_index + 1}"
                    self._add_log_item(f"▶️ Đang phát: {segment_name} ({segment_index + 1}/{total_segments})", "info")
                    
        except Exception as e:
            print(f"Error highlighting segment: {e}")

    def _on_audio_playback_state_changed(self, is_playing: bool) -> None:
        """Callback khi trạng thái phát audio thay đổi"""
        try:
            if hasattr(self, 'stop_segments_btn'):
                self.stop_segments_btn.setEnabled(is_playing)
        except Exception as e:
            print(f"Error updating button states: {e}")

    def _on_audio_status_changed(self, status: str) -> None:
        """Callback khi status audio thay đổi"""
        self._add_log_item(f"🎵 Audio: {status}", "info")

    def _on_audio_finished(self) -> None:
        """Callback khi audio phát xong hoàn toàn tất cả segments (không loop)"""
        try:
            self._add_log_item("⏹️ Audio đã phát xong tất cả segments - Dừng hoàn toàn", "info")
            # Reset current_index để có thể phát lại nếu cần
            self.current_index = -1
            # Tự động reset trạng thái nút về "Đọc audio" khi phát xong
            if self.is_reading_audio:
                self.is_reading_audio = False
                self.btn_play_audio.setText("Đọc audio")
                self.btn_play_audio.setStyleSheet("")
            
            # Đảm bảo audio player dừng hoàn toàn
            if self.audio_player:
                self.audio_player.stop()
                self._add_log_item("⏹️ Đã dừng audio player hoàn toàn", "info")
                
        except Exception as e:
            print(f"Error handling audio finished: {e}")

    def _on_segment_list_item_clicked(self, item) -> None:
        try:
            pass
        except Exception as e:
            print(f"Error on segment item click: {e}")

    def _on_segment_list_item_double_clicked(self, item) -> None:
        try:
            pass
        except Exception as e:
            print(f"Error on segment item double click: {e}")

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
        
        self.stop_segments_btn = QPushButton("⏹️ Dừng")
        self.stop_segments_btn.clicked.connect(self._stop_segments_playback)
        self.stop_segments_btn.setObjectName("btn_style_2")
        
        self.clear_segments_btn = QPushButton("🗑️ Xóa tất cả")
        self.clear_segments_btn.clicked.connect(self._clear_all_segments)
        self.clear_segments_btn.setObjectName("btn_style_2")
        
        segment_controls.addStretch()
        
        self.segment_manager_group.setLayout(self.segment_manager_layout)
        # Ẩn section mặc định khi khởi tạo
        self.segment_manager_group.setVisible(False)
        content_layout.addWidget(self.segment_manager_group)

    def _play_all_segments(self) -> None:
        try:
            if self.audio_player:
                self.audio_player.play()
                self._add_log_item("▶️ Phát tất cả segments", "info")
        except Exception as e:
            print(f"Error play all segments: {e}")

    def _stop_segments_playback(self) -> None:
        try:
            if hasattr(self, 'audio_player') and self.audio_player:
                self.audio_player.stop()
        except Exception as e:
            print(f"Error stopping segments playback: {e}")

    def _clear_all_segments(self) -> None:
        try:
            if hasattr(self, 'segment_manager') and self.segment_manager:
                self.segment_manager.clear_segments()
        except Exception as e:
            print(f"Error clearing segments: {e}")

    def stop_all_audio(self) -> None:
        """Dừng toàn bộ phát audio và TTS, reset nút trạng thái"""
        try:
            # Stop audio playback
            if hasattr(self, 'audio_player') and self.audio_player:
                self.audio_player.stop()
            # Stop TTS worker if running
            if hasattr(self, 'tts_worker') and self.tts_worker and self.tts_worker.isRunning():
                self.tts_worker.stop()
                self.tts_worker.wait(3000)
            # Reset UI state
            self.is_reading_audio = False
            if hasattr(self, 'btn_play_audio') and self.btn_play_audio:
                self.btn_play_audio.setText("Đọc audio")
                self.btn_play_audio.setStyleSheet("")
        except Exception as e:
            print(f"Error stopping all audio: {e}")

    def play_audio(self) -> None:
        """Toggle audio playback: Đọc -> Tắt -> Clear -> Đọc lại"""
        try:
            # Lần đầu bấm hoặc sau khi clear: Bắt đầu đọc
            if not self.is_reading_audio:
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
                
                text_type = "source"
                text = "Hello, how are you? This is a test text for TTS conversion."
                
                # Bắt đầu đọc
                self.is_reading_audio = True
                self.btn_play_audio.setText("🔇 Tắt đọc văn bản")
                self.btn_play_audio.setStyleSheet("background-color: #ff6b6b; color: white;")
                # Reset current_index để có thể auto-play segment đầu tiên
                self.current_index = -1
                
                selected_voice = "Tự phát hiện"
                
                # Xử lý voice được chọn
                if selected_voice == "Tự phát hiện":
                    # Sử dụng langdetect để tự động phát hiện
                    detected_lang = language_manager.detect_language_from_text(text)
                    voice_name = language_manager.get_female_voice(detected_lang) or language_manager.get_default_voice_for_language(detected_lang)
                    lang_display_name = language_manager.get_language_display_name(detected_lang)
                    self._add_log_item(f"🔍 Phát hiện ngôn ngữ: {lang_display_name} ({detected_lang})", "info")
                    print(f"🔍 Detected language: {detected_lang}, Voice: {voice_name}")
               
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
                
            # Lần thứ hai bấm: Dừng và clear data
            else:
                # Dừng đọc
                self.is_reading_audio = False
                self.btn_play_audio.setText("🗑️ Clear & Đọc lại")
                self.btn_play_audio.setStyleSheet("background-color: #ffa500; color: white;")
                
                # Dừng audio và TTS
                if self.audio_player:
                    self.audio_player.stop()
                if self.tts_worker and self.tts_worker.isRunning():
                    self.tts_worker.stop()
                    self.tts_worker.wait(3000)
                
                # Clear segments
                if hasattr(self, 'segment_manager') and self.segment_manager:
                    self.segment_manager.clear_segments()
                
                # Ẩn section Quản lý Audio Segments
                if hasattr(self, 'segment_manager_group'):
                    self.segment_manager_group.setVisible(False)
                
                self._add_log_item("⏹️ Đã dừng và clear data", "info")
                
                # Reset về trạng thái ban đầu để lần sau bấm sẽ đọc lại
                self.is_reading_audio = False
                self.current_index = -1
            
        except Exception as e:
            print(f"Error playing audio from segments: {e}")

    def _on_tts_segment_ready(self, path: str, duration_ms: int, index: int) -> None:
        """Callback khi TTS segment sẵn sàng"""
        self._ensure_capacity(index)
        self.segment_manager.segment_paths[index - 1] = path
        self.segment_manager.segment_durations[index - 1] = duration_ms

        # Update total duration
        self.segment_manager._update_total_duration()

        # Update segments display with detailed time information
        if hasattr(self.segment_manager, 'schedule_display_update'):
            self.segment_manager.schedule_display_update(200)
        else:
            self.segment_manager._update_display()
        
        # Cập nhật UI
        self._update_segment_display()

        # Update AudioPlayer
        if self.audio_player:
            valid_paths, valid_durations = self.segment_manager.get_valid_segments()
            self.audio_player.add_segments(valid_paths, valid_durations)

            # Hiện player section khi có segment đầu tiên
            if index == 1:
                self._show_player_section(True)

        # Auto-play tất cả segments tuần tự, phát xong thì dừng (không loop)
        if self.current_index < 0 and self.segment_manager.segment_paths and self.segment_manager.segment_paths[0]:
            if self.audio_player:
                # Không can thiệp loop tại đây; AudioPlayer tự quản lý chk_loop nội bộ
                
                self.audio_player.play()
                self._add_log_item(
                    f"▶️ Tự động phát tất cả segments: {len(self.segment_manager.segment_paths)} segments (không loop)", "blue")
                # Set current_index để tránh auto-play lại
                self.current_index = 0

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

    def _on_tts_error(self, msg: str) -> None:
        """Callback khi TTS có lỗi"""
        self._add_log_item(f"❌ Lỗi TTS: {msg}", "error")

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

    def _on_segment_added(self, path: str, duration: int) -> None:
        """Handle when a new segment is added"""
        self._update_segment_display()
        self._add_log_item(f"✅ Đã thêm segment: {os.path.basename(path)} ({duration}ms)", "info")

    def _on_segment_removed(self, index: int) -> None:
        """Handle when a segment is removed"""
        self._update_segment_display()
        self._add_log_item(f"🗑️ Đã xóa segment {index + 1}", "info")

    def check_and_show(self):
        text = self.text_edit.toPlainText()
        result = parse_srt(text)

        if result is None:
            QMessageBox.warning(
                self, "Kết quả", "❌ Không phải định dạng SRT hợp lệ")
            return

        self.table.setRowCount(len(result))
        for row, (_index, timestamp, content) in enumerate(result):
            self.table.setItem(row, 0, QTableWidgetItem(timestamp))
            self.table.setItem(row, 1, QTableWidgetItem(content))
            self.table.setItem(row, 2, QTableWidgetItem(""))
        self.table.resizeRowsToContents()

    def _on_row_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        timestamp_item = self.table.item(row, 0)
        content_item = self.table.item(row, 1)
        trans_item = self.table.item(row, 2)
        timestamp = timestamp_item.text() if timestamp_item else ""
        content = content_item.text() if content_item else ""
        trans = trans_item.text() if trans_item else ""

        # Bind về ô nhập: ưu tiên hiển thị nội dung gốc, kèm bản dịch nếu có
        display = content
        if trans.strip():
            display = f"{content}\n\n[Dịch]\n{trans}"

    def get_table_data(self):
        rows = self.table.rowCount()
        cols = self.table.columnCount()
        data = []
        for row in range(rows):
            row_data = []
            for col in range(cols):
                item = self.table.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)
        return data

    def export_to_srt(self):
        """Xuất ra SRT: dùng chỉ cột Dịch nếu có, bỏ STT (bảng đã có)."""
        data = self.get_table_data()  # Mỗi hàng: [timestamp, content, trans]
        srt_lines = []
        for idx, (timestamp, content, trans) in enumerate(data, start=1):
            srt_lines.append(str(idx))
            srt_lines.append(timestamp)
            text_line = (trans or "").strip() or (content or "")
            srt_lines.append(text_line)
            srt_lines.append("")
        return "\n".join(srt_lines)

    def save_srt(self):
        srt_text = self.export_to_srt()
        filename, _ = QFileDialog.getSaveFileName(
            self, "Lưu file SRT", "", "Subtitle Files (*.srt)")
        if filename:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(srt_text)
            QMessageBox.information(
                self, "Thành công", f"✅ Đã lưu file:\n{filename}")

    def open_srt(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Mở file SRT", "", "Subtitle Files (*.srt)")
        if not filename:
            return
        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # Fallback nếu không phải utf-8
            with open(filename, "r", encoding="cp1252", errors="replace") as f:
                content = f.read()
        self.text_edit.setPlainText(content)
        self.check_and_show()

    def translate_all(self):
        """Dùng TranslateWorker để dịch tất cả (EN→VI)"""
        rows = self.table.rowCount()
        if rows == 0:
            QMessageBox.information(
                self, "Thông báo", "Không có dữ liệu để dịch")
            return

        contents = []
        for row in range(rows):
            item = self.table.item(row, 1)  # cột Nội dung
            contents.append(item.text() if item else "")
        
        # Khởi tạo worker dịch: Google Translate, EN -> VI
        self.translate_worker = MultiThreadTranslateWorker(
            text="",
            source_lang="en",
            target_lang="vi",
            service="Google Translate",
            api_key="",
            max_len=500,
            workers=4,
            custom_prompt="",
            input_type="srt",
            chunks=contents
        )

        # Cập nhật UI theo tiến trình
        self.btn_translate_all.setEnabled(False)

        def on_segment_translated(original: str, translated: str, index: int):
            row_idx = index - 1
            if 0 <= row_idx < self.table.rowCount():
                self.table.setItem(row_idx, 2, QTableWidgetItem(translated))
                self.table.resizeRowToContents(row_idx)

        def on_progress(completed: int, total: int):
            pass

        def on_done():
            self.btn_translate_all.setEnabled(True)
            QMessageBox.information(
                self, "Hoàn tất", "✅ Đã dịch xong tất cả dòng")

        def on_error(msg: str):
            self.btn_translate_all.setEnabled(True)
            QMessageBox.warning(self, "Lỗi", msg)

        self.translate_worker.segment_translated.connect(on_segment_translated)
        self.translate_worker.progress.connect(on_progress)
        self.translate_worker.all_done.connect(on_done)
        self.translate_worker.error.connect(on_error)
        self.translate_worker.start()

    def _ensure_capacity(self, n: int) -> None:
        """Đảm bảo segment_paths và segment_durations có đủ capacity cho n segments"""
        try:
            if not hasattr(self, 'segment_manager') or not self.segment_manager:
                return
                
            while len(self.segment_manager.segment_paths) < n:
                self.segment_manager.segment_paths.append(None)
                self.segment_manager.segment_durations.append(None)
        except Exception as e:
            print(f"Error ensuring capacity: {e}")

    def _add_log_item(self, message: str, level: str = "") -> None:
        """Add log item to console"""
        try:
            print(f"[{level.upper() if level else 'INFO'}] {message}")
        except Exception as e:
            print(f"[LOG ERROR] {e}")

    def _update_progress(self, value: int) -> None:
        """Update progress bar (placeholder)"""
        try:
            print(f"[PROGRESS] {value}%")
        except Exception as e:
            print(f"[PROGRESS ERROR] {e}")

    def _show_player_section(self, show: bool = True) -> None:
        """Show/hide player section"""
        if hasattr(self, 'segment_manager_group'):
            self.segment_manager_group.setVisible(show)


class SRTTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.viewer = SRTChecker()
        layout.addWidget(self.viewer)
        self.setLayout(layout)

    def load_text(self, text: str):
        if hasattr(self.viewer, 'text_edit'):
            self.viewer.text_edit.setPlainText(text)

    def hideEvent(self, event):
        # Khi đổi tab (widget bị ẩn) thì dừng toàn bộ audio
        try:
            if hasattr(self, 'viewer') and self.viewer:
                self.viewer.stop_all_audio()
        except Exception:
            pass
        super().hideEvent(event)

    def closeEvent(self, event):
        # Khi tab bị đóng, dừng toàn bộ audio
        try:
            if hasattr(self, 'viewer') and self.viewer:
                self.viewer.stop_all_audio()
        except Exception:
            pass
        super().closeEvent(event)
