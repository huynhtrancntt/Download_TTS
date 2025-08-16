
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QLabel, QFrame, QTextEdit, QComboBox,
    QSlider
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


class TTSTab(UIToolbarTab):
    """Text-to-Speech tab with improved UI and functionality"""

    def __init__(self, parent_main: QWidget):
        super().__init__(parent_main)
        self._setup_ui()

    def append_history(self, text: str, meta: Optional[dict] = None):
        """Add TTS item to history - only text and meta parameters"""
        if self.history:
            # TTS specific: only text and meta
            self.history.panel.add_history(text, meta=meta or {})

    def _setup_ui(self):
        """Setup the TTS tab UI"""
        root_layout = self.layout()
        self.file_output = ""
        # Enable history first to get the button
        hist = self.enable_history(
            hist_title="Lịch sử TTS",
            item_factory=lambda text, ts, lang, meta: TTSHistoryItem(
                text, ts, lang, meta),
            on_item_selected=self._on_history_selected
        )

        # Add demo items using TTSTab's append_history method
        self.append_history("Xin chào, tôi là trợ lý AI Xin chào, tôi là trợ lý AIXin chào, tôi là trợ lý AIXin chào, tôi là trợ lý AIXin chào, tôi là trợ lý AIXin chào, tôi là trợ lý AIXin chào", meta={
                            "demo": True, "priority": "high"})
        self.append_history("Hôm nay thời tiết thế nào?", meta={
                            "demo": True, "priority": "normal"})
        self.append_history("Hôm nay thời tiết thế nào?", meta={
                            "demo": True, "priority": "normal"})
        self.append_history("Hôm nay thời tiết thế nào?", meta={
                            "demo": True, "priority": "normal"}) 
        self.append_history("Hôm nay thời tiết thế nào?", meta={
                            "demo": True, "priority": "normal"})
        # Header with title and history button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        title = QLabel("Nội dung cần nói")
        title.setStyleSheet("font-weight:600; font-size:16px;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(hist.btn)

        root_layout.insertLayout(0, header_layout)

        # Main content layout
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Text input area
        # content_layout.addWidget(QLabel("Nội dung cần nói:"))
        self.text_input = QTextEdit(placeholderText="Nhập văn bản tại đây…")
        self.text_input.setPlainText("Xin chào! Đây là giọng nói tiếng Việt.")
        # Make text input responsive
        # self.text_input.setMaximumHeight(120)
        # self.text_input.setMinimumHeight(60)
        content_layout.addWidget(self.text_input)
        content_layout.addStretch()
        # Settings section - split into two rows for better responsiveness
        settings_group = QWidget()
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setContentsMargins(0, 5, 0, 5)

        # First row - Language and Gender
        settings_row1 = QHBoxLayout()
        settings_row1.addWidget(QLabel("Ngôn ngữ:"))
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
        settings_row1.addWidget(self.cmb_lang)

        settings_row1.addWidget(QLabel("Giới tính:"))
        self.cmb_gender = QComboBox()
        self.cmb_gender.setMinimumWidth(80)
        self.cmb_gender.addItems(["Female", "Male", "Any"])
        self.cmb_gender.setCurrentText("Female")
        settings_row1.addWidget(self.cmb_gender)
        settings_row1.addStretch()

        # Second row - Speed control
        settings_row1.addWidget(QLabel("Tốc độ:"))
        self.sld_rate = QSlider(Qt.Horizontal)
        self.sld_rate.setRange(50, 200)
        self.sld_rate.setValue(100)
        self.sld_rate.setTickInterval(10)
        self.sld_rate.setTickPosition(QSlider.TicksBelow)
        self.sld_rate.setSingleStep(1)
        self.sld_rate.setPageStep(10)
        # Responsive: min width instead of fixed
        self.sld_rate.setMinimumWidth(50)
        self.sld_rate.setMaximumWidth(200)  # Max width for better layout
        # settings_row2.addWidget(self.sld_rate)
        settings_row1.addWidget(self.sld_rate)
        self.lbl_rate_val = QLabel("1.0")
        self.lbl_rate_val.setMinimumWidth(30)
        self.sld_rate.valueChanged.connect(
            lambda v: self.lbl_rate_val.setText(f"{v/100:.1f}"))
        settings_row1.addWidget(self.lbl_rate_val)

        settings_layout.addLayout(settings_row1)

        content_layout.addWidget(settings_group)

        # Control buttons - responsive layout
        buttons_layout = QHBoxLayout()
        self.btn_say = QPushButton(" 🔊 Chuyển đổi")
        self.btn_save = QPushButton("💾 Lưu")
        self.btn_stop = QPushButton("⏹️ Dừng")
        self.btn_clear_chunks = QPushButton("🗑️ Xóa Chunks")

        for btn in (self.btn_say, self.btn_save, self.btn_stop, self.btn_clear_chunks):
            btn.setStyleSheet(AppConfig.BUTTON_STYLE)
            btn.setMinimumWidth(80)  # Ensure minimum width for buttons
            btn.setMaximumWidth(120)  # Prevent buttons from being too wide
            buttons_layout.addWidget(btn)

        buttons_layout.addStretch()
        content_layout.addLayout(buttons_layout)

        # Status label
        self.lbl_status = QLabel("Sẵn sàng.")
        self.lbl_status.setStyleSheet(
            "color: #888; font-size: 12px; padding: 5px;")
        content_layout.addWidget(self.lbl_status)

        root_layout.insertLayout(1, content_layout)

        # Connect events
        # self.btn_say.clicked.connect(self._on_say_clicked)
        # self.btn_save.clicked.connect(self._on_save_clicked)
        # self.btn_stop.clicked.connect(self._on_stop_clicked)
        # self.btn_clear_chunks.clicked.connect(self._on_clear_chunks_clicked)

        # self._seeking = False

        # Update status bar - now it's guaranteed to existf
        self.parent_main.status.showMessage("TTS Tab sẵn sàng")

    def _on_history_selected(self, text: str):
        """Handle history item selection"""
        self.text_input.setPlainText(text)
        self.text_input.setFocus()
