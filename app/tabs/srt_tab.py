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

from PySide6.QtCore import Qt

from app.core.segment_audio import SegmentAudio

from typing import Optional
from app.core.segment_manager import SegmentManager
from app.core.srt_playback_controller import SRTPlaybackController
from app.core.language_manager import language_manager

# Import history system
from app.uiToolbarTab import UIToolbarTab
from app.core.config import AppConfig
from app.history.historyItem_TTS import TTSHistoryItem
import json
from datetime import datetime


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
        self._initialize_state_variables()

        layout = QVBoxLayout(self)

        # Ô nhập nội dung
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Dán nội dung SRT vào đây...")
        self.text_edit.setContextMenuPolicy(Qt.NoContextMenu)
        # layout.addWidget(self.text_edit)

        # Nút kiểm tra
        self.btn_check = QPushButton("Kiểm tra & Hiển thị")
        self.btn_check.clicked.connect(self.check_and_show)
        # layout.addWidget(self.btn_check)

        # Bảng hiển thị (thêm cột Dịch)
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Thời gian", "Nội dung", "Dịch"])
        self.table.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.table.setWordWrap(True)
        self.table.setContextMenuPolicy(Qt.NoContextMenu)
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
        self.current_index: int = -1
        self.is_reading_audio: bool = False
        # Throttle logging time (per second)
        self._last_logged_second: int = -1

    def _setup_audio_system(self) -> None:
        """Setup audio system for text reading"""
        # Create controller which manages AudioPlayer + SegmentManager + TTS worker
        self.controller = SRTPlaybackController(
            list_widget=getattr(self, 'segment_list', None),
            total_duration_label=getattr(self, 'total_duration_label', None),
            segment_count_label=getattr(self, 'segment_count_label', None),
        )

        # Expose to keep compatibility with existing code paths
        self.audio_player = self.controller.audio_player
        self.segment_manager = self.controller.segment_manager

        # Connect controller signals to existing handlers
        self.controller.position_changed.connect(self._on_audio_position_changed)
        # self.controller.segment_changed.connect(self._on_audio_segment_changed)
            # self.controller.playback_state_changed.connect(self._on_audio_playback_state_changed)
        # self.controller.status_signal.connect(self._on_audio_status_changed)
        # self.controller.playback_finished.connect(self._on_audio_finished)

        # Setup segment manager after controller created
        self._setup_segment_manager()

    def _on_audio_position_changed(self, position_ms: int) -> None:
        """Callback khi vị trí audio thay đổi"""
        try:
            # Log mỗi khi đổi giây để tránh spam
            current_second = int(max(0, position_ms) // 1000)
            if current_second != self._last_logged_second:
                self._last_logged_second = current_second
                minutes = current_second // 60
                seconds = current_second % 60
                self._add_log_item(f"⏱️ Thời gian phát: {minutes:02d}:{seconds:02d}", "info")
        except Exception:
            pass

    def _on_audio_segment_changed(self, segment_index: int) -> None:
        """Callback khi segment audio thay đổi"""
        try:
            # Highlight current segment in the list
            if hasattr(self, 'segment_list') and self.segment_list and 0 <= segment_index < self.segment_list.count():
                self.segment_list.setCurrentRow(segment_index)

            # Log khi chuyển segment
            if hasattr(self, 'segment_manager') and self.segment_manager:
                total_segments = len(
                    [p for p in self.segment_manager.segment_paths if p])
                if segment_index < total_segments:
                    segment_name = os.path.basename(
                        self.segment_manager.segment_paths[segment_index]) if self.segment_manager.segment_paths[segment_index] else f"Segment {segment_index + 1}"
                    self._add_log_item(
                        f"▶️ Đang phát: {segment_name} ({segment_index + 1}/{total_segments})", "info")

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
            self._add_log_item(
                "⏹️ Audio đã phát xong tất cả segments - Dừng hoàn toàn", "info")
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
        """Handle segment list item click"""
        pass

    def _on_segment_list_item_double_clicked(self, item) -> None:
        """Handle segment list item double click"""
        try:
            if not hasattr(self, 'segment_list') or not self.segment_list:
                return
            row = self.segment_list.currentRow()
            if row is None or row < 0:
                return
            if not hasattr(self, 'controller') or not self.controller:
                return
            player = getattr(self.controller, 'audio_player', None)
            manager = getattr(self.controller, 'segment_manager', None)
            if not player or not manager:
                return
            # Validate index within available paths
            if row >= len(manager.segment_paths):
                return
            path = manager.segment_paths[row]
            if not path:
                return
            # Play selected segment from beginning
            player.play_segment(row, 0)
            self._is_playing_segments = True
            self._add_log_item(f"🎬 Phát segment {row + 1}", "info")
        except Exception as e:
            print(f"Error on double click play: {e}")

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
        self.total_duration_label.setStyleSheet(
            "font-weight: bold; font-size: 12px;")
        header_layout.addWidget(self.total_duration_label)

        header_layout.addStretch()

        # Segment count label
        self.segment_count_label = QLabel("Số segments: 0")
        self.segment_count_label.setStyleSheet("font-size: 11px; color: #666;")
        header_layout.addWidget(self.segment_count_label)

        self.segment_manager_layout.addLayout(header_layout)

        # Segment list widget
        self.segment_list = QListWidget()
        self.segment_list.setSelectionMode(
            QListWidget.SelectionMode.MultiSelection)
        self.segment_list.setContextMenuPolicy(Qt.NoContextMenu)
        self.segment_list.itemClicked.connect(
            self._on_segment_list_item_clicked)
        self.segment_list.itemDoubleClicked.connect(
            self._on_segment_list_item_double_clicked)
        self.segment_manager_layout.addWidget(self.segment_list)

        # Control buttons for segments
        segment_controls = QHBoxLayout()

        self.play_segments_btn = QPushButton("▶️ Phát tất cả")
        self.play_segments_btn.clicked.connect(self._play_all_segments)
        self.play_segments_btn.setObjectName("btn_style_2")

        self.stop_segments_btn = QPushButton("⏹️ Dừng")
        self.stop_segments_btn.clicked.connect(self._stop_segments_playback)
        self.stop_segments_btn.setObjectName("btn_style_2")

        # New review button to restart from beginning
        self.review_segments_btn = QPushButton("🔁 Xem lại từ đầu")
        self.review_segments_btn.clicked.connect(self._review_from_start)
        self.review_segments_btn.setObjectName("btn_style_2")

        # Export audio button
        self.export_segments_btn = QPushButton("📤 Export audio")
        self.export_segments_btn.clicked.connect(self._export_segments_audio)
        self.export_segments_btn.setObjectName("btn_style_2")

        # Merge all button
        self.merge_segments_btn = QPushButton("🔗 Gộp tất cả")
        self.merge_segments_btn.clicked.connect(self._merge_all_segments)
        self.merge_segments_btn.setObjectName("btn_style_2")

        # Add buttons to controls layout
        segment_controls.addWidget(self.play_segments_btn)
        segment_controls.addWidget(self.stop_segments_btn)
        segment_controls.addWidget(self.review_segments_btn)
        segment_controls.addWidget(self.export_segments_btn)
        segment_controls.addWidget(self.merge_segments_btn)
        segment_controls.addStretch()

        # Attach controls layout to the segment manager layout
        self.segment_manager_layout.addLayout(segment_controls)

        self.segment_manager_group.setLayout(self.segment_manager_layout)
        # Ẩn section mặc định khi khởi tạo
        self.segment_manager_group.setVisible(False)
        content_layout.addWidget(self.segment_manager_group)


    def _stop_segments_playback(self) -> None:
        """Stop segments playback"""
        if hasattr(self, 'controller') and self.controller:
            self.controller.stop_all()
            # Reset playing state
            if hasattr(self, '_is_playing_segments'):
                self._is_playing_segments = False
            self._add_log_item("⏹️ Đã dừng phát segments", "info")

    def _review_from_start(self) -> None:
        """Restart playback from the first segment"""
        try:
            if hasattr(self, 'controller') and self.controller:
                # Stop current playback and seek to start
                self.controller.stop_all()
                # Reset internal playing state so play can start again
                if hasattr(self, '_is_playing_segments'):
                    self._is_playing_segments = False
                # Seek to 0 and play
                if hasattr(self.controller, 'seek_to'):
                    self.controller.seek_to(0)
                self.controller.play()
                self._is_playing_segments = True
                self._add_log_item("🔁 Xem lại từ đầu", "info")
        except Exception as e:
            print(f"Error restarting from start: {e}")

    def _play_all_segments(self) -> None:
        """Play all segments from the beginning."""
        if hasattr(self, 'controller') and self.controller:
            self.controller.play_all()
            self._add_log_item("▶️ Đã phát tất cả segments", "info")

    def stop_all_audio(self) -> None:
        """Dừng toàn bộ phát audio và TTS, reset nút trạng thái"""
        try:
            if hasattr(self, 'controller') and self.controller:
                self.controller.stop_all()
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
                # Dừng audio/TTS đang chạy nếu có
                if hasattr(self, 'controller') and self.controller:
                    self.controller.stop_all()

                # Hiện section Quản lý Audio Segments
                if hasattr(self, 'segment_manager_group'):
                    self.segment_manager_group.setVisible(True)

                text_type = "source"
                text = f"Chức năng đã được sửa để:\n1. Sử dụng vị trí hiện tại của audio player để ngắt đoạn\n2. Bấm nút “✂️ Ngắt đoạn” để thực hiện\n3. Ngắt theo tùy chọn từ dropdown (3s, 4s, 5s, 10s)\n4. Giữ lại tên file cũ và thêm đoạn mới vào\n5. Vị trí ngắt đoạn được phép ở ĐẦU, CUỐI hoặc SAU segment"

                # Bắt đầu đọc
                self.is_reading_audio = True
                self.btn_play_audio.setText("🔇 Tắt đọc văn bản")
                self.btn_play_audio.setStyleSheet(
                    "background-color: #ff6b6b; color: white;")
                # Reset current_index để có thể auto-play segment đầu tiên
                self.current_index = -1

                selected_voice = "Tự phát hiện"

                # Xử lý voice được chọn
                if selected_voice == "Tự phát hiện":
                    # Sử dụng langdetect để tự động phát hiện
                    detected_lang = language_manager.detect_language_from_text(
                        text)
                    voice_name = language_manager.get_female_voice(
                        detected_lang) or language_manager.get_default_voice_for_language(detected_lang)
                    lang_display_name = language_manager.get_language_display_name(
                        detected_lang)
                    self._add_log_item(
                        f"🔍 Phát hiện ngôn ngữ: {lang_display_name} ({detected_lang})", "info")
                    print(
                        f"🔍 Detected language: {detected_lang}, Voice: {voice_name}")

                voice_name = "vi-VN-HoaiMyNeural"  # Default Vietnamese
                self._add_log_item("🎯 Fallback voice: Tiếng Việt (vi)", "info")

                # Bắt đầu TTS qua controller
                if hasattr(self, 'controller') and self.controller:
                    print(f"🔊 Bắt đầu đọc văn bản {text_type}: {len(text)} ký tự")
                    self._add_log_item("🔊 Bắt đầu đọc văn bản {text_type}: {len(text)} ký tự", "info")
                    self.controller.start_tts(
                        text=text,
                        voice_name=voice_name,
                        speed=0,
                        pitch=0,
                        max_length=200,
                        workers=4,
                    )
                    # self.controller.segment_ready.connect(self._on_tts_segment_ready)
                    self.controller.status_signal.connect(lambda msg: self._add_log_item(msg, "info"))

                # Log
                self._add_log_item(
                    f"🔊 Bắt đầu đọc văn bản {text_type}: {len(text)} ký tự", "info")

            # Lần thứ hai bấm: Dừng và clear data
            else:
                # Dừng đọc
                self.is_reading_audio = False
                self.btn_play_audio.setText("🗑️ Clear & Đọc lại")
                self.btn_play_audio.setStyleSheet(
                    "background-color: #ffa500; color: white;")

                # Dừng audio và TTS
                if hasattr(self, 'controller') and self.controller:
                    self.controller.stop_all()

                # Clear segments
                if hasattr(self, 'controller') and self.controller:
                    self.controller.clear_segments()

                # Ẩn section Quản lý Audio Segments
                if hasattr(self, 'segment_manager_group'):
                    self.segment_manager_group.setVisible(False)

                self._add_log_item("⏹️ Đã dừng và clear data", "info")

                # Reset về trạng thái ban đầu để lần sau bấm sẽ đọc lại
                self.is_reading_audio = False
                self.current_index = -1

        except Exception as e:
            print(f"Error playing audio from segments: {e}")


    def _setup_segment_manager(self) -> None:
        """Setup segment manager with UI components"""
        try:
            if hasattr(self, 'segment_manager') and self.segment_manager:
                self.segment_manager.set_ui_components(
                    self.segment_list, self.audio_player, enable_context_menu=False)

                # Connect segment manager signals
                self.segment_manager.segments_changed.connect(
                    self._update_segment_display)
                self.segment_manager.segment_added.connect(
                    self._on_segment_added)
                self.segment_manager.segment_removed.connect(
                    self._on_segment_removed)

                # Initial display update
                self._update_segment_display()

        except Exception as e:
            print(f"Error setting up segment manager: {e}")
            self._add_log_item(
                f"❌ Lỗi khi thiết lập segment manager: {e}", "error")

    def _update_segment_display(self) -> None:
        """Update segment display information via helper"""
        try:
            manager = getattr(self, 'segment_manager', None)
            SegmentAudio.update_segment_display(
                manager,
                getattr(self, 'total_duration_label', None),
                getattr(self, 'segment_count_label', None),
            )
        except Exception as e:
            print(f"Error updating segment display: {e}")

    def _on_segment_added(self, path: str, duration: int) -> None:
        """Handle when a new segment is added"""
        self._update_segment_display()
        self._add_log_item(
            f"✅ Đã thêm segment: {os.path.basename(path)} ({duration}ms)", "info")

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

        # Save check action to history
        self._save_check_to_history(text, len(result))

    def _save_check_to_history(self, text: str, row_count: int) -> None:
        """Save SRT check action to history"""
        try:
            if hasattr(self, 'parent_main') and hasattr(self.parent_main, '_add_log_item'):
                # Create history entry for checked SRT
                history_entry = {
                    'input_file': text,
                    'output_file': '',
                    'status': 'checked',
                    'created_chunks': row_count,
                    'started_at': datetime.now().isoformat(),
                    'type': 'srt_checked',
                    'translation_count': 0,
                    'total_rows': row_count
                }

                # Save to history file
                history_file = AppConfig.HISTORY_FILE
                if history_file.exists():
                    with open(history_file, 'r', encoding='utf-8') as f:
                        try:
                            entries = json.load(f)
                        except Exception:
                            entries = []
                else:
                    entries = []

                if not isinstance(entries, list):
                    entries = []

                entries.append(history_entry)

                # Keep only last 100 entries
                if len(entries) > 100:
                    entries = entries[-100:]

                with open(history_file, 'w', encoding='utf-8') as f:
                    json.dump(entries, f, ensure_ascii=False, indent=4)

                self.parent_main._add_log_item(
                    f"✅ Đã kiểm tra SRT và lưu vào lịch sử: {row_count} dòng", "info")

        except Exception as e:
            print(f"Error saving check to history: {e}")

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

            # Save to history
            self._save_to_history(srt_text, filename)

    def _save_to_history(self, srt_text: str, filename: str = "") -> None:
        """Save SRT content to history"""
        try:
            if hasattr(self, 'parent_main') and hasattr(self.parent_main, '_add_log_item'):
                # Get original text and translation data
                original_text = self.text_edit.toPlainText()
                table_data = self.get_table_data()

                # Create history entry
                history_entry = {
                    'input_file': original_text,
                    'output_file': filename,
                    'status': 'completed',
                    'created_chunks': len(table_data),
                    'started_at': datetime.now().isoformat(),
                    'type': 'srt_processing',
                    # Count translated rows
                    'translation_count': sum(1 for row in table_data if row[2].strip()),
                    'total_rows': len(table_data)
                }

                # Save to history file
                history_file = AppConfig.HISTORY_FILE
                if history_file.exists():
                    with open(history_file, 'r', encoding='utf-8') as f:
                        try:
                            entries = json.load(f)
                        except Exception:
                            entries = []
                else:
                    entries = []

                if not isinstance(entries, list):
                    entries = []

                entries.append(history_entry)

                # Keep only last 100 entries
                if len(entries) > 100:
                    entries = entries[-100:]

                with open(history_file, 'w', encoding='utf-8') as f:
                    json.dump(entries, f, ensure_ascii=False, indent=4)

                self.parent_main._add_log_item(
                    f"💾 Đã lưu vào lịch sử: {len(original_text)} ký tự, {len(table_data)} dòng", "info")

        except Exception as e:
            print(f"Error saving to history: {e}")

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

        # Save to history
        self._save_open_to_history(content, filename)

    def _save_open_to_history(self, content: str, filename: str) -> None:
        """Save opened SRT file to history"""
        try:
            if hasattr(self, 'parent_main') and hasattr(self.parent_main, '_add_log_item'):
                # Create history entry for opened file
                history_entry = {
                    'input_file': content,
                    'output_file': filename,
                    'status': 'opened',
                    'created_chunks': 0,
                    'started_at': datetime.now().isoformat(),
                    'type': 'srt_opened',
                    'translation_count': 0,
                    'total_rows': 0
                }

                # Save to history file
                history_file = AppConfig.HISTORY_FILE
                if history_file.exists():
                    with open(history_file, 'r', encoding='utf-8') as f:
                        try:
                            entries = json.load(f)
                        except Exception:
                            entries = []
                else:
                    entries = []

                if not isinstance(entries, list):
                    entries = []

                entries.append(history_entry)

                # Keep only last 100 entries
                if len(entries) > 100:
                    entries = entries[-100:]

                with open(history_file, 'w', encoding='utf-8') as f:
                    json.dump(entries, f, ensure_ascii=False, indent=4)

                self.parent_main._add_log_item(
                    f"📂 Đã mở và lưu vào lịch sử: {os.path.basename(filename)} ({len(content)} ký tự)", "info")

        except Exception as e:
            print(f"Error saving open to history: {e}")

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
                self, "Thành công", "✅ Đã dịch xong tất cả dòng")

            # Save translation to history
            self._save_translation_to_history()

        def on_error(msg: str):
            self.btn_translate_all.setEnabled(True)
            QMessageBox.warning(self, "Lỗi", msg)

        self.translate_worker.segment_translated.connect(on_segment_translated)
        self.translate_worker.progress.connect(on_progress)
        self.translate_worker.all_done.connect(on_done)
        self.translate_worker.error.connect(on_error)
        self.translate_worker.start()

    def _save_translation_to_history(self) -> None:
        """Save translation completion to history"""
        try:
            if hasattr(self, 'parent_main') and hasattr(self.parent_main, '_add_log_item'):
                # Get current data
                original_text = self.text_edit.toPlainText()
                table_data = self.get_table_data()

                # Count translated rows
                translated_count = sum(
                    1 for row in table_data if row[2].strip())

                # Create history entry
                history_entry = {
                    'input_file': original_text,
                    'output_file': '',
                    'status': 'translated',
                    'created_chunks': len(table_data),
                    'started_at': datetime.now().isoformat(),
                    'type': 'srt_translation',
                    'translation_count': translated_count,
                    'total_rows': len(table_data)
                }

                # Save to history file
                history_file = AppConfig.HISTORY_FILE
                if history_file.exists():
                    with open(history_file, 'r', encoding='utf-8') as f:
                        try:
                            entries = json.load(f)
                        except Exception:
                            entries = []
                else:
                    entries = []

                if not isinstance(entries, list):
                    entries = []

                entries.append(history_entry)

                # Keep only last 100 entries
                if len(entries) > 100:
                    entries = entries[-100:]

                with open(history_file, 'w', encoding='utf-8') as f:
                    json.dump(entries, f, ensure_ascii=False, indent=4)

                self.parent_main._add_log_item(
                    f"🌐 Đã lưu bản dịch vào lịch sử: {translated_count}/{len(table_data)} dòng", "info")

        except Exception as e:
            print(f"Error saving translation to history: {e}")

    def _ensure_capacity(self, n: int) -> None:
        """Đảm bảo segment_paths và segment_durations có đủ capacity cho n segments"""
        # Handled by controller now
        pass

    def _add_log_item(self, message: str, level: str = "") -> None:
        """Add log item to console"""
        try:
            print(f"[{level.upper() if level else 'INFO'}] {message}")
            
            parent_main = getattr(self, 'parent_main', None)
            if parent_main and hasattr(parent_main, '_add_log_item'):
                parent_main._add_log_item(message, level)
        except Exception as e:
            print(f"[LOG ERROR] {e}")

    def _update_progress(self, value: int) -> None:
        """Update progress bar (placeholder)"""
        pass

    def _show_player_section(self, show: bool = True) -> None:
        """Show/hide player section"""
        if hasattr(self, 'segment_manager_group'):
            self.segment_manager_group.setVisible(show)

    def _export_segments_audio(self) -> None:
        """Export all available segment audio files to a chosen folder in order."""
        try:
            if not hasattr(self, 'controller') or not self.controller:
                QMessageBox.warning(self, "Export audio", "Chưa có controller để lấy danh sách segments.")
                return
            manager = getattr(self.controller, 'segment_manager', None)
            if not manager or not getattr(manager, 'segment_paths', None):
                QMessageBox.information(self, "Export audio", "Không có segment nào để xuất.")
                return

            # Chọn thư mục đích
            folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục để lưu audio")
            if not folder:
                return

            exported, total = SegmentAudio.export_all_to_folder(manager, folder)
            QMessageBox.information(self, "Export audio", f"✅ Đã xuất {exported}/{total} file vào:\n{folder}")
            self._add_log_item(f"📤 Exported {exported}/{total} segments to {folder}", "info")
        except Exception as e:
            QMessageBox.warning(self, "Export audio", f"Lỗi: {e}")
            print(f"Export segments error: {e}")

    def _merge_all_segments(self) -> None:
        """Merge all valid segments into a single MP3 and replace the list with the merged file."""
        try:
            if not hasattr(self, 'controller') or not self.controller:
                QMessageBox.warning(self, "Gộp audio", "Chưa có controller để lấy danh sách segments.")
                return
            manager = getattr(self.controller, 'segment_manager', None)
            player = getattr(self.controller, 'audio_player', None)
            if not manager or not getattr(manager, 'segment_paths', None):
                QMessageBox.information(self, "Gộp audio", "Không có segment nào để gộp.")
                return

            parts = [p for p in manager.segment_paths if p]
            if not parts:
                QMessageBox.information(self, "Gộp audio", "Không có file audio hợp lệ để gộp.")
                return

            # Chọn nơi lưu file gộp
            default_name = f"SRT_Merged_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
            out_path, _ = QFileDialog.getSaveFileName(
                self, "Chọn nơi lưu file gộp", str(AppConfig.OUTPUT_DIR / default_name), "MP3 Files (*.mp3)"
            )
            if not out_path:
                return

            # Ghép các đoạn qua exporter
            out_path, total_ms, merged = SegmentAudio.merge_all_to_file(manager, out_path, gap_ms=0)
            if not out_path or total_ms is None:
                QMessageBox.warning(self, "Gộp thất bại", "Không có dữ liệu hợp lệ để gộp.")
                return

            # Thay danh sách segments bằng file gộp
            manager.clear_segments()
            manager.add_segment(out_path, total_ms)

            # Đồng bộ player
            if player:
                valid_paths, valid_durations = manager.get_valid_segments()
                player.add_segments(valid_paths, valid_durations)
                # Hiện section nếu đang ẩn
                if hasattr(self, 'segment_manager_group'):
                    self.segment_manager_group.setVisible(True)

            # Refresh stats display
            try:
                SegmentAudio.update_segment_display(
                    manager,
                    getattr(self, 'segment_manager_group', None),
                    getattr(self, 'total_duration_label', None),
                    getattr(self, 'segment_count_label', None),
                )
            except Exception:
                pass

            QMessageBox.information(self, "Thành công", f"Đã gộp {merged} đoạn vào 1 file:\n{out_path}")
            self._add_log_item(f"🔗 Đã gộp {merged} segments thành 1 file", "info")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi gộp", f"Không thể gộp segments:\n{e}")
            print(f"Merge segments error: {e}")


class SRTTab(UIToolbarTab):
    def __init__(self, parent_main: QWidget) -> None:
        super().__init__(parent_main)
        # Initialize state variables
        self._initialize_state_variables()

        # Setup history system
        # self._setup_history_system()

        # Setup UI (after history so the button is available)
        self._setup_ui()

    def _initialize_state_variables(self) -> None:
        """Initialize state variables"""
        self.current_index: int = -1
        self.worker: Optional[MultiThreadTranslateWorker] = None
        self.file_output: str = ""

    def _setup_ui(self) -> None:
        """Setup UI"""
        root_layout = self.layout()

        # Setup header section
        self._setup_header_section(root_layout)

        # Setup content section
        self._setup_content_section(root_layout)

        # Update status b
        # ar

    def _setup_header_section(self, parent_main: QVBoxLayout) -> None:
        """Setup header section"""
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(2, 2, 2, 2)

        row_layout = QVBoxLayout()

        # Control buttons row
        self._create_control_buttons_row(row_layout)

        header_layout.addLayout(row_layout)
        parent_main.addLayout(header_layout)

    def _create_control_buttons_row(self, parent_layout: QVBoxLayout) -> None:
        """Create control buttons row"""
        row2_layout = QHBoxLayout()
        row2_layout.setContentsMargins(0, 0, 0, 0)

        row2_layout.addStretch()

        # Add history button
        if hasattr(self, 'history') and self.history:
            row2_layout.addWidget(self.history.btn)
            print("[SRTTab] History button added to toolbar")

        parent_layout.addLayout(row2_layout)

    def _setup_content_section(self, parent_main: QVBoxLayout) -> None:
        """Setup content section"""
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Create SRTChecker widget
        self.viewer = SRTChecker()
        try:
            self.viewer.parent_main = self.parent_main
        except Exception:
            pass
        content_layout.addWidget(self.viewer)

        parent_main.addLayout(content_layout)

    def _setup_history_system(self) -> None:
        """Setup history system with auto-refresh"""
        hist = self.enable_history(
            hist_title="Lịch sử SRT",
            item_factory=lambda text, ts, meta: TTSHistoryItem(
                text, ts, meta),
            on_item_selected=self._on_history_selected,
            refresh_callback=self._refresh_history_list,
            on_delete=self._on_delete,
        )

        # Không load demo data ngay, sẽ load khi mở panel
        print(
            "[SRTTab] History system setup complete - will auto-refresh when panel opens")

    def _on_history_selected(self, payload: Optional[dict] = None) -> None:
        """Handle click from a history item"""
        try:
            if payload is not None:
                if isinstance(payload, str):
                    # Nếu payload là text, load vào text editor
                    if hasattr(self.viewer, 'text_edit'):
                        self.viewer.text_edit.setPlainText(payload)
                        # Focus vào text editor
                        self.viewer.text_edit.setFocus()
                elif isinstance(payload, dict) and 'full_text' in payload:
                    # Nếu payload là dict có full_text, load vào text editor
                    if hasattr(self.viewer, 'text_edit'):
                        self.viewer.text_edit.setPlainText(
                            payload['full_text'])
                        # Focus vào text editor
                        self.viewer.text_edit.setFocus()
        except Exception as e:
            print(f"[SRTTab] Error handling history selection: {e}")

    def _on_delete(self, index: int):
        """Handle delete button click from history panel"""
        try:
            print(f"[SRTTab] Delete index requested: {index}")
            # Lấy widget và meta của item để xác định entry tương ứng
            panel = getattr(self, 'history', None).panel if getattr(
                self, 'history', None) else None
            if not panel:
                return
            list_widget = panel.history_list
            if index < 0 or index >= list_widget.count():
                return
            list_item = list_widget.item(index)
            item_widget = list_widget.itemWidget(list_item)
            meta = getattr(item_widget, "_meta", {}) if item_widget else {}

            entries_path = AppConfig.HISTORY_FILE
            if not entries_path.exists():
                QMessageBox.warning(self, "Xóa lịch sử",
                                    "Không tìm thấy tệp lịch sử để cập nhật.")
                return
            import json as _json
            with open(entries_path, 'r', encoding='utf-8') as f:
                try:
                    entries = _json.load(f)
                except Exception:
                    entries = []

            if not isinstance(entries, list):
                entries = []

            # Tìm entry phù hợp theo started_at hoặc full_text/input_file
            started_at = meta.get('started_at') if isinstance(
                meta, dict) else None
            full_text = meta.get('full_text') if isinstance(
                meta, dict) else None
            voice_meta = meta.get('voice') if isinstance(meta, dict) else None

            match_idx = -1
            for i in range(len(entries) - 1, -1, -1):  # duyệt ngược để ưu tiên item mới
                e = entries[i]
                if started_at and e.get('started_at') == started_at:
                    match_idx = i
                    break
                if full_text and e.get('input_file') == full_text:
                    if not voice_meta or e.get('voice') == voice_meta:
                        match_idx = i
                        break

            if match_idx == -1:
                # Không tìm thấy entry phù hợp
                QMessageBox.information(
                    self, "Xóa lịch sử", "Không tìm thấy mục tương ứng trong file lịch sử. Chỉ xóa khỏi danh sách hiển thị.")
                return

            # Xóa entry khỏi JSON và ghi lại
            try:
                entries.pop(match_idx)
                with open(entries_path, 'w', encoding='utf-8') as f:
                    _json = __import__('json')
                    _json.dump(entries, f, ensure_ascii=False, indent=4)
            except Exception as write_err:
                pass

        except Exception as e:
            pass

    def _refresh_history_list(self):
        """Refresh history list with latest items from entries.json"""
        try:
            print("[SRTTab] Refreshing history list...")

            # Clear current history
            if self.history and hasattr(self.history.panel, 'clear_history'):
                self.history.panel.clear_history()

            # Load lại history mới nhất từ entries.json
            latest_history = self._load_latest_history()

            # Thêm lại các item mới
            if self.history and hasattr(self.history.panel, 'add_history'):
                for item in latest_history:
                    self.history.panel.add_history(
                        text=item.get('text', ''),
                        meta=item.get('meta', {})
                    )

        except Exception as e:
            print(f"[SRTTab] Error refreshing history list: {e}")

    def _load_latest_history(self):
        """Load latest history data"""
        try:
            # Load từ file entries.json
            history_file = AppConfig.HISTORY_FILE
            if history_file.exists():
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Chuyển đổi cấu trúc data thành format phù hợp
                    history_items = []
                    for item in data[-20:]:  # Lấy 20 item gần nhất
                        # Xử lý text để hiển thị đẹp hơn
                        input_text = item.get('input_file', '')
                        display_text = input_text[:100] + \
                            '...' if len(input_text) > 100 else input_text

                        # Xử lý timestamp
                        started_at = item.get('started_at', '')
                        if started_at:
                            try:
                                from datetime import datetime
                                dt = datetime.fromisoformat(
                                    started_at.replace('Z', '+00:00'))
                                timestamp = dt.strftime("%H:%M %d/%m/%Y")
                            except:
                                # Lấy phần đầu nếu parse lỗi
                                timestamp = started_at[:19]
                        else:
                            timestamp = "Unknown"

                        history_items.append({
                            'text': display_text,
                            'meta': {
                                'voice': item.get('voice', ''),
                                'status': item.get('status', ''),
                                'created_chunks': item.get('created_chunks', 0),
                                'started_at': started_at,
                                'timestamp': timestamp,
                                'full_text': input_text,
                                'lang': 'vi-VN'  # Thêm language info
                            }
                        })

                    return history_items
            else:
                print("[SRTTab] file not found")
            return []
        except Exception as e:
            print(f"[SRTTab] Error loading history: {e}")
            return []

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
            if hasattr(self, 'viewer', 'stop_all_audio'):
                self.viewer.stop_all_audio()
        except Exception:
            pass
        super().closeEvent(event)

    
