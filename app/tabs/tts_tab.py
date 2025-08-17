from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QLabel, QTextEdit, QComboBox,
    QSlider, QSpinBox, QListWidget, QProgressBar, QCheckBox, QMessageBox, QFileDialog, QListWidgetItem
)
from PySide6.QtCore import Qt, QTimer, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import os
import tempfile
from app.uiToolbarTab import UIToolbarTab
from app.appConfig import AppConfig

from app.history.historyItem_TTS import TTSHistoryItem

from ..constants import (
    VOICE_CHOICES, RATE_CHOICES, PITCH_CHOICES,
    DEFAULT_VOICE, DEFAULT_RATE, DEFAULT_PITCH, DEFAULT_MAXLEN, DEFAULT_WORKERS_PLAYER,
    DEFAULT_GAP_MS, OUTPUT_DIR
)
from app.utils.helps import ms_to_mmss, clean_all_temp_parts, get_mp3_duration_ms, save_log_entry, prepare_pydub_ffmpeg
from app.workers import MTProducerWorker

from pydub import AudioSegment


class TTSTab(UIToolbarTab):
    """Text-to-Speech tab with improved UI and functionality"""

    def __init__(self, parent_main: QWidget):
        super().__init__(parent_main)
        self._setup_ui()

        self.segment_paths: list[str | None] = []
        self.segment_durations: list[int | None] = []
        self.total_known_ms = 0
        self.current_index = -1
        self.seeking = False
        self.is_playing = False
        self.worker: MTProducerWorker | None = None

        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)

        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_timeline)

        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.player.errorOccurred.connect(self.on_media_error)
        self.player.positionChanged.connect(self.on_player_position_changed)
        self.player.playbackStateChanged.connect(
            self.on_playback_state_changed)

        self.seek_debounce = QTimer(self)
        self.seek_debounce.setInterval(150)
        self.seek_debounce.setSingleShot(True)
        self.seek_debounce.timeout.connect(self.apply_seek_target)
        self._pending_seek_value = None

        self.list_segments.itemDoubleClicked.connect(
            self.on_list_item_double_clicked)

    def append_history(self, text: str, meta: Optional[dict] = None):
        """Thêm item vào lịch sử (TTS): chỉ lưu text + meta"""
        if self.history:
            self.history.panel.add_history(text, meta=meta or {})

    def _setup_ui(self):
        """Khởi tạo toàn bộ UI cho tab TTS"""
        root_layout = self.layout()
        self.file_output = ""

        # Bật khu vực Lịch sử để có nút mở panel lịch sử
        hist = self.enable_history(
            hist_title="Lịch sử TTS",
            item_factory=lambda text, ts, lang, meta: TTSHistoryItem(
                text, ts, lang, meta),
            on_item_selected=self._on_history_selected
        )

        # Demo history (có thể xoá sau)
        self.append_history("Xin chào, tôi là trợ lý AI ...", meta={
                            "demo": True, "priority": "high"})
        self.append_history("Hôm nay thời tiết thế nào?", meta={
                            "demo": True, "priority": "normal"})

        # ===== Header chứa 2 hàng: tham số job + nút mở file/bắt đầu/kết thúc
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(2, 2, 2, 2)
        # Các tham số job
        self.theard_edge_tts = QSpinBox()
        self.theard_edge_tts.setRange(1, 16)
        self.theard_edge_tts.setValue(DEFAULT_WORKERS_PLAYER)
        self.theard_edge_tts.setSuffix(" Theard")

        self.maxlen_spin_edge_tts = QSpinBox()
        self.maxlen_spin_edge_tts.setRange(80, 2000)
        self.maxlen_spin_edge_tts.setValue(DEFAULT_MAXLEN)
        self.maxlen_spin_edge_tts.setSuffix(" ký tự/đoạn")

        self.gap_spin_edge_tts = QSpinBox()
        self.gap_spin_edge_tts.setRange(0, 2000)
        self.gap_spin_edge_tts.setValue(DEFAULT_GAP_MS)
        self.gap_spin_edge_tts.setSuffix(" ms nghỉ ghép")

        # Dàn 2 hàng trong header
        row_layout = QVBoxLayout()

        # Hàng 1: tham số job + nút mở lịch sử
        row1_layout = QHBoxLayout()
        row1_layout.addWidget(QLabel("Theard"))
        row1_layout.addWidget(self.theard_edge_tts)
        row1_layout.addWidget(self.maxlen_spin_edge_tts)
        row1_layout.addWidget(self.gap_spin_edge_tts)
        row1_layout.addStretch()
        row1_layout.addWidget(hist.btn)

        # Hàng 2: mở file + start/stop
        row2_layout = QHBoxLayout()
        row2_layout.setContentsMargins(0, 0, 0, 0)
        self.btn_open_edge_tts = QPushButton("📂 Mở file")
        self.btn_open_edge_tts.clicked.connect(self.on_open_file)
        row2_layout.addWidget(self.btn_open_edge_tts)
        row2_layout.addStretch()
        self.btn_start_edge_tts = QPushButton("▶️ Bắt đầu")
        self.btn_start_edge_tts.clicked.connect(self.on_start)
        self.btn_end_edge_tts = QPushButton("⏹ Kết thúc")
        self.btn_end_edge_tts.clicked.connect(self.on_end_all)
        self.btn_end_edge_tts.setEnabled(False)

        row2_layout.addWidget(self.btn_start_edge_tts)
        row2_layout.addWidget(self.btn_end_edge_tts)

        # Ghép 2 hàng vào header
        row_layout.addLayout(row1_layout)    # đúng: addLayout cho layout con
        row_layout.addLayout(row2_layout)
        header_layout.addLayout(row_layout)  # đúng: addLayout, không addWidget

        # ===== Content chính (textbox + cấu hình voice/rate + nút điều khiển + status)
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Text input
        self.text_input_edge_tts = QTextEdit(
            placeholderText="Dán văn bản hoặc bấm Mở .txt")
        self.text_input_edge_tts.setMinimumHeight(200)
        content_layout.addWidget(self.text_input_edge_tts, 2)

        # Ngôn ngữ & Giới tính
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

        self.cmb_gender = QComboBox()
        self.cmb_gender.setMinimumWidth(80)
        self.cmb_gender.addItems(["Female", "Male", "Any"])
        self.cmb_gender.setCurrentText("Female")

        # ===== Sliders CHUẨN HÓA TÊN/Ý NGHĨA =====
        # Tốc độ (speed multiplier): 0.5x → 2.0x (range 50..200), hiển thị 0.5..2.0
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(100)             # 1.0x mặc định
        self.speed_slider.setTickInterval(10)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setSingleStep(1)
        self.speed_slider.setPageStep(10)
        # Tạo label TRƯỚC khi connect
        self.lbl_speed_val = QLabel("1.0")
        self.speed_slider.valueChanged.connect(
            lambda v: self.lbl_speed_val.setText(f"{v/100:.1f}")
        )

        # Cao độ (pitch multiplier quanh 1.0): -50..+50% → hiển thị 0.5..1.5
        self.pitch_slider = QSlider(Qt.Horizontal)
        self.pitch_slider.setRange(-50, 50)
        self.pitch_slider.setValue(0)               # +0% = 1.0
        self.pitch_slider.setTickInterval(10)
        self.pitch_slider.setTickPosition(QSlider.TicksBelow)
        self.lbl_pitch_val = QLabel("1.0")
        self.pitch_slider.valueChanged.connect(
            lambda v: self.lbl_pitch_val.setText(f"{1 + v/100:.1f}")
        )

        # Nhóm cấu hình (ngôn ngữ/giới tính/tốc độ/cao độ)
        row_box = QVBoxLayout()

        row_b1_layout = QHBoxLayout()
        row_b1_layout.setContentsMargins(0, 5, 0, 5)
        row_b1_layout.addWidget(QLabel("Ngôn ngữ"))
        row_b1_layout.addWidget(self.cmb_lang)
        row_b1_layout.addWidget(QLabel("Giới tính"))
        row_b1_layout.addWidget(self.cmb_gender)
        row_b1_layout.addStretch()

        row_b1_layout.addWidget(QLabel("Tốc độ"))
        row_b1_layout.addWidget(self.speed_slider, 1)
        row_b1_layout.addWidget(self.lbl_speed_val)

        row_b1_layout.addSpacing(12)
        row_b1_layout.addWidget(QLabel("Cao độ"))
        row_b1_layout.addWidget(self.pitch_slider, 1)
        row_b1_layout.addWidget(self.lbl_pitch_val)

        # Hàng nút điều khiển
        row_b2_layout = QHBoxLayout()
        row_b2_layout.setContentsMargins(0, 5, 0, 5)
        buttons_layout = QHBoxLayout()
        self.btn_say = QPushButton(" 🔊 Chuyển đổi")
        self.btn_save = QPushButton("💾 Lưu")
        self.btn_stop = QPushButton("⏹️ Dừng")
        self.btn_clear_chunks = QPushButton("🗑️ Xóa Chunks")
        for btn in (self.btn_say, self.btn_save, self.btn_stop, self.btn_clear_chunks):
            btn.setStyleSheet(AppConfig.BUTTON_STYLE)
            btn.setMinimumWidth(80)
            btn.setMaximumWidth(120)
            buttons_layout.addWidget(btn)
        buttons_layout.addStretch()
        # ✅ addLayout (đúng), KHÔNG dùng addWidget
        row_b2_layout.addLayout(buttons_layout)

        # Label trạng thái
        self.lbl_status = QLabel("Sẵn sàng")
        self.lbl_status.setStyleSheet(
            "color: #888; font-size: 12px; padding: 5px;")

        # Ghép các phần vào content
        row_box.addLayout(row_b1_layout)
        row_box.addLayout(row_b2_layout)
        content_layout.addLayout(row_box)
        content_layout.addStretch()
        self.list_segments = QListWidget()
        content_layout.addWidget(self.list_segments, 2)
        content_layout.addWidget(self.lbl_status)
        self.text_input_edge_tts1 = QTextEdit(
            placeholderText="Dán văn bản hoặc bấm Mở .txt")
        # self.text_input_edge_tts1.setMinimumHeight(200)
        root_layout.addLayout(header_layout)
        root_layout.addLayout(content_layout)

        self.btn_prev = QPushButton("⏮")
        self.btn_prev.clicked.connect(self.play_prev)
        self.btn_playpause = QPushButton("▶️")
        self.btn_playpause.clicked.connect(self.toggle_playpause)

        self.btn_next = QPushButton("⏭")
        self.btn_next.clicked.connect(self.play_next)

        # Slider có click-to-seek
        self.slider = ClickSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)

        self.slider.sliderPressed.connect(self.on_slider_pressed)
        self.slider.sliderMoved.connect(self.on_slider_moved)
        self.slider.sliderReleased.connect(self.on_slider_released)
        self.slider.clickedValue.connect(self.on_slider_clicked)

        self.lbl_time = QLabel("00:00 / 00:00")
        # self.lbl_status = QLabel("Sẵn sàng.")
        # self.lbl_status.setWordWrap(True)
        self.progress_gen = QProgressBar()
        self.progress_gen.setRange(0, 100)
        self.progress_gen.setValue(0)

        # Lặp lại
        self.chk_loop = QCheckBox("🔁 Lặp lại")

        self.chk_loop.setChecked(True)

        self.player_widget = QWidget()
        player_row = QHBoxLayout(self.player_widget)

        # Thêm các control vào player_row
        player_row.addWidget(self.btn_prev)
        player_row.addWidget(self.btn_playpause)
        player_row.addWidget(self.btn_next)
        player_row.addWidget(self.slider, 1)
        player_row.addWidget(self.lbl_time)
        player_row.addWidget(self.chk_loop)
        content_layout.addWidget(self.player_widget)

        # Cập nhật status bar của cửa sổ cha (nếu có)
        if getattr(self.parent_main, "status", None):
            self.parent_main.status.showMessage("TTS Tab sẵn sàng")

    def _ensure_capacity(self, n: int):
        while len(self.segment_paths) < n:
            self.segment_paths.append(None)
            self.segment_durations.append(None)

    # ==== Callback khi chọn item lịch sử ====

    def _on_history_selected(self, text: str):
        """Khi click chọn 1 item lịch sử: đổ text về ô nhập hiện tại"""
        # Sửa lỗi: đúng tên widget là text_input_edge_tts (trước đây code dùng self.text_input là sai)
        self.text_input_edge_tts.setPlainText(text)
        self.text_input_edge_tts.setFocus()

    ##

        # ---------- actions ----------
    def on_open_file(self):
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

    def on_start(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        self.player.stop()
        self.timer.stop()
        self.is_playing = False
        self.btn_playpause.setText("▶")
        self.segment_paths.clear()
        self.segment_durations.clear()
        self.total_known_ms = 0
        self.current_index = -1
        self.seeking = False
        self.list_segments.clear()
        self.slider.setRange(0, 0)
        self.update_time_label(0, 0)
        self.progress_gen.setValue(0)
        self.lbl_status.setText("Sẵn sàng. 2222")
        # self.btn_export.setEnabled(False)
        # clean_all_temp_parts()

        text = self.text_input_edge_tts.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Thiếu nội dung",
                                "Dán hoặc mở file .txt trước khi bắt đầu.")
            return


#         vi-VN-HoaiMyNeural
# 0
# 0
# 220
# 4
        self.lbl_status.setText("Sẵn sàng.3 ")
        self.worker = MTProducerWorker(
            text, "vi-VN-HoaiMyNeural", 0,
            0, 500, 4)
        # self.worker = MTProducerWorker(
        #     text, self.voice_cb.currentText(), self.rate_cb.currentData(),
        #     self.pitch_cb.currentData(), self.maxlen_spin.value(), self.theard_edge_tts.value()
        # )
        self.worker.segment_ready.connect(self.on_segment_ready)
        self.worker.progress.connect(self.on_produce_progress)
        self.worker.status.connect(self.on_status)
        self.worker.all_done.connect(self.on_all_done)
        self.worker.error.connect(self.on_error)

        self.btn_start_edge_tts.setEnabled(False)
        self.btn_end_edge_tts.setEnabled(True)
        self.lbl_status.setText(
            f"🔄 Đang sinh audio ({self.theard_edge_tts.value()} luồng)…")
        self.worker.start()

    def on_end_all(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        self.player.stop()
        self.timer.stop()
        self.is_playing = False
        self.btn_playpause.setText("▶️")
        self.btn_end_edge_tts.setEnabled(False)
        self.btn_start_edge_tts.setEnabled(True)
        self.lbl_status.setText("⏹ Đã kết thúc.")
        # clean_all_temp_parts()

    # ---------- worker callbacks ----------
    def on_segment_ready(self, path: str, duration_ms: int, index1: int):
        self._ensure_capacity(index1)
        self.segment_paths[index1 - 1] = path
        self.segment_durations[index1 - 1] = duration_ms

        self.total_known_ms = sum(d or 0 for d in self.segment_durations)
        line = f"{index1:03d}. {os.path.basename(path)}  —  {ms_to_mmss(duration_ms)}"
        if index1 - 1 < self.list_segments.count():
            self.list_segments.item(index1 - 1).setText(line)
        else:
            while self.list_segments.count() < index1 - 1:
                self.list_segments.addItem(QListWidgetItem("(đang tạo...)"))
            self.list_segments.addItem(QListWidgetItem(line))

        self.slider.setRange(0, max(0, self.total_known_ms))
        self.update_time_label(
            self.get_global_position_ms(), self.total_known_ms)

        if self.current_index < 0 and self.segment_paths and self.segment_paths[0]:
            self.play_segment(0)

        if any(self.segment_paths):
            # self.btn_export.setEnabled(True)
            pass

    def on_produce_progress(self, emitted: int, total: int):
        self.progress_gen.setValue(int(emitted / total * 100))

    def on_status(self, msg: str): self.lbl_status.setText(msg)

    def on_all_done(self):
        self.lbl_status.setText(self.lbl_status.text() + "  ✅ Xong.")
        self.btn_start_edge_tts.setEnabled(True)
        self.btn_end_edge_tts.setEnabled(False)
        if self.player.playbackState() != QMediaPlayer.PlayingState:
            self.is_playing = False
            self.btn_playpause.setText("▶")

    def on_error(self, msg: str):
        QMessageBox.critical(self, "Lỗi", msg)
        self.btn_end_edge_tts.setEnabled(False)
        self.btn_start_edge_tts.setEnabled(True)

    # ---------- player ----------
    def play_segment(self, idx: int, pos_in_segment_ms: int = 0):
        if idx < 0 or idx >= len(self.segment_paths):
            return
        p = self.segment_paths[idx]
        if not p:
            return
        self.current_index = idx
        self.player.setSource(QUrl.fromLocalFile(p))
        self.player.setPosition(max(0, pos_in_segment_ms))
        self.player.play()
        self.timer.start()
        self.is_playing = True
        self.btn_playpause.setText("⏹")
        self.list_segments.setCurrentRow(idx)

    def play_next(self):
        i = self.current_index + 1
        while i < len(self.segment_paths) and not self.segment_paths[i]:
            i += 1
        if i < len(self.segment_paths):
            self.play_segment(i, 0)
        else:
            if self.chk_loop.isChecked():
                idx0 = next((k for k, p in enumerate(
                    self.segment_paths) if p), None)
                if idx0 is not None:
                    self.play_segment(idx0, 0)
                    return
            self.is_playing = False
            self.btn_playpause.setText("▶️")

    def play_prev(self):
        i = self.current_index - 1
        while i >= 0 and not self.segment_paths[i]:
            i -= 1
        if i >= 0:
            self.play_segment(i, 0)
        else:
            self.player.setPosition(0)

    def toggle_playpause(self):
        if not self.is_playing:
            if self.current_index < 0 and any(self.segment_paths):
                idx0 = next((i for i, p in enumerate(
                    self.segment_paths) if p), None)
                if idx0 is not None:
                    self.play_segment(idx0, 0)
            else:
                self.player.play()
                self.is_playing = True
                self.btn_playpause.setText("⏹")
        else:
            self.player.stop()
            self.timer.stop()
            self.is_playing = False
            self.btn_playpause.setText("▶️")

    def on_media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.play_next()

    def on_media_error(self, err):
        self.lbl_status.setText(
            f"⚠️ Lỗi phát: {self.player.errorString() or str(err)}")
        self.play_next()

    def on_player_position_changed(self, pos_ms: int):
        if not self.seeking:
            self.update_timeline()

    def on_playback_state_changed(self, state):

        if state == QMediaPlayer.StoppedState:
            if self.current_index + 1 >= len(self.segment_paths):
                if self.chk_loop.isChecked():
                    self.play_next()
                    return
                self.is_playing = False
                self.btn_playpause.setText("▶")

    # ---------- timeline ----------
    def update_timeline(self):
        if self.current_index < 0:
            return
        offset = sum((d or 0)
                     for d in self.segment_durations[:self.current_index])
        current_pos = offset + self.player.position()
        self.slider.blockSignals(True)
        self.slider.setValue(current_pos)
        self.slider.blockSignals(False)
        self.update_time_label(current_pos, self.total_known_ms)

    def on_slider_pressed(self): self.seeking = True

    def on_slider_moved(self, value: int):
        self._pending_seek_value = value
        self.seek_debounce.start()

    def on_slider_released(self):
        if self.seek_debounce.isActive():
            self.seek_debounce.stop()
            self.apply_seek_target()
        self.seeking = False

    def on_slider_clicked(self, value: int):
        self.seeking = True
        self._pending_seek_value = value
        self.apply_seek_target()
        self.seeking = False

    def apply_seek_target(self):
        if self._pending_seek_value is None:
            return
        target = self._pending_seek_value
        self._pending_seek_value = None
        idx, local = self.map_global_to_local(target)
        if idx is not None:
            self.play_segment(idx, local)

    def map_global_to_local(self, global_ms: int):
        acc = 0
        for i, d in enumerate(self.segment_durations):
            d = d or 0
            if global_ms < acc + d:
                return i, global_ms - acc
            acc += d
        if any(self.segment_durations):
            last_idx = len(self.segment_durations) - 1
            last_dur = (self.segment_durations[last_idx] or 10)
            return last_idx, max(0, last_dur - 10)
        return None, None

    def get_global_position_ms(self) -> int:
        if self.current_index < 0:
            return 0
        acc = sum((d or 0)
                  for d in self.segment_durations[:self.current_index])
        return acc + self.player.position()

    def update_time_label(self, cur_ms: int, total_ms: int):
        self.lbl_time.setText(f"{ms_to_mmss(cur_ms)} / {ms_to_mmss(total_ms)}")

    def on_list_item_double_clicked(self, item):
        row = self.list_segments.row(item)
        if 0 <= row < len(self.segment_paths) and self.segment_paths[row]:
            self.play_segment(row, 0)

    # ---------- Export MP3 ----------
    def on_export_mp3(self):
        parts = [p for p in self.segment_paths if p]
        if not parts:
            QMessageBox.information(
                self, "Chưa có dữ liệu", "Chưa có đoạn nào để xuất.")
            return

        default_name = f"Player_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Chọn nơi lưu MP3", str(
                OUTPUT_DIR / default_name), "MP3 Files (*.mp3)"
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

            final.export(out_path, format="mp3")

            # entry = {
            #     "input_file": None,
            #     "output_file": out_path,
            #     "media_type": "audio/mp3",
            #     "voice": self.voice_cb.currentText(),
            #     "rate_percent": self.rate_cb.currentData(),
            #     "pitch_hz": self.pitch_cb.currentData(),
            #     "max_chunk_chars": self.maxlen_spin.value(),
            #     "gap_ms": gap_ms,
            #     "created_chunks": valid_count,
            #     "total_duration_ms_est": total_ms,
            #     "started_at": None,
            #     "finished_at": datetime.now().isoformat(),
            #     "status": "success_export_player",
            # }
            # save_log_entry(entry)

            QMessageBox.information(
                self, "Thành công", f"Đã xuất MP3:\n{out_path}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi xuất", f"Không thể xuất MP3:\n{e}")

    def stop_all(self):
        # Ngừng worker TTS
        if getattr(self, "worker", None) and self.worker.isRunning():
            self.worker.stop()
        # Ngừng player/timer
        try:
            self.player.stop()
        except Exception:
            pass
        if getattr(self, "timer", None) and self.timer.isActive():
            self.timer.stop()
        # Xoá file tạm
        try:
            clean_all_temp_parts()
        except Exception:
            pass
        # Cờ UI
        self.is_playing = False
        if hasattr(self, "btn_playpause"):
            self.btn_playpause.setText("▶️")

    def closeEvent(self, event):
        self.stop_all()
        super().closeEvent(event)


class ClickSlider(QSlider):
    """Slider cho phép click để seek ngay vị trí click"""
    clickedValue = Signal(int)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            ratio = event.position().x() / max(1, self.width())
            vmin, vmax = self.minimum(), self.maximum()
            value = int(vmin + ratio * (vmax - vmin))
            self.setValue(value)
            self.clickedValue.emit(value)
        super().mousePressEvent(event)
