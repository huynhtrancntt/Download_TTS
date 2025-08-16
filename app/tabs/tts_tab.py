from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QLabel, QFrame, QTextEdit, QComboBox,
    QSlider, QSpinBox
)
from PySide6.QtCore import Qt
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, List, Tuple, Any

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


class TTSTab(UIToolbarTab):
    """Text-to-Speech tab with improved UI and functionality"""

    def __init__(self, parent_main: QWidget):
        super().__init__(parent_main)
        self._setup_ui()

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
        header_layout.setContentsMargins(0, 0, 0, 0)
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
        row2_layout.addWidget(self.btn_open_edge_tts)
        row2_layout.addStretch()
        self.btn_start_edge_tts = QPushButton("▶️ Bắt đầu")
        self.btn_end_edge_tts = QPushButton("⏹ Kết thúc")
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

        row_b1_layout.addWidget(QLabel("Tốc độ:"))
        row_b1_layout.addWidget(self.speed_slider, 1)
        row_b1_layout.addWidget(self.lbl_speed_val)

        row_b1_layout.addSpacing(12)
        row_b1_layout.addWidget(QLabel("Cao độ:"))
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
        self.lbl_status = QLabel("Sẵn sàng.")
        self.lbl_status.setStyleSheet(
            "color: #888; font-size: 12px; padding: 5px;")

        # Ghép các phần vào content
        row_box.addLayout(row_b1_layout)
        row_box.addLayout(row_b2_layout)
        content_layout.addLayout(row_box)
        content_layout.addStretch()
        content_layout.addWidget(self.lbl_status)
        self.text_input_edge_tts1 = QTextEdit(
            placeholderText="Dán văn bản hoặc bấm Mở .txt")
        self.text_input_edge_tts1.setMinimumHeight(200)
        # content_layout.addWidget(self.text_input_edge_tts1, 2)
        # Thêm vào root THEO THỨ TỰ (tránh insertLayout với index cứng 0/1)
        root_layout.addLayout(header_layout)
        root_layout.addLayout(content_layout)
        # root_layout.insertLayout(0, header_layout)
        # root_layout.insertLayout(1, content_layout)

        # layout = QVBoxLayout(self)
        # layout.setContentsMargins(0, 0, 0, 0)
        # layout.addLayout(root_layout)
        # root_layout.addLayout(self.history_layout)

        # Kết nối sự kiện (đặt sau khi UI sẵn sàng)
        # self.btn_say.clicked.connect(self._on_say_clicked)
        # self.btn_save.clicked.connect(self._on_save_clicked)
        # self.btn_stop.clicked.connect(self._on_stop_clicked)
        # self.btn_clear_chunks.clicked.connect(self._on_clear_chunks_clicked)

        # Cập nhật status bar của cửa sổ cha (nếu có)
        if getattr(self.parent_main, "status", None):
            self.parent_main.status.showMessage("TTS Tab sẵn sàng")

    # ==== Callback khi chọn item lịch sử ====
    def _on_history_selected(self, text: str):
        """Khi click chọn 1 item lịch sử: đổ text về ô nhập hiện tại"""
        # Sửa lỗi: đúng tên widget là text_input_edge_tts (trước đây code dùng self.text_input là sai)
        self.text_input_edge_tts.setPlainText(text)
        self.text_input_edge_tts.setFocus()
