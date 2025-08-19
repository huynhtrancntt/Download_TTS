from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
)
from typing import Optional, Callable, Type
from PySide6.QtCore import Signal

from app.uiToolbarTab import UIToolbarTab
from app.history.historyItem_TTS import TTSHistoryItem
from app.historyFeature import HistoryFeature


class ConvertTab(UIToolbarTab):
    """
    Tab Convert đơn giản để minh họa việc áp dụng HistoryPanel cho mỗi tab
    """

    def __init__(self, parent_main: QWidget) -> None:
        super().__init__(parent_main)

        self._setup_history()
        self._setup_ui()

    def _setup_history(self) -> None:
        """Enable per-tab history with its own panel and button"""
        self.enable_history(
            hist_title="Lịch sử Convert",
            item_factory=lambda text, ts, meta: TTSHistoryItem(text, ts, meta),
        )

        # Đưa nút lịch sử vào thanh toolbar của tab
        if self.history:
            self.add_toolbar_widget(self.history.btn)

        # Không thêm demo; sẽ load khi mở panel

    def _setup_ui(self) -> None:
        """Create simple content for the Convert tab"""
        root_layout: QVBoxLayout = self.layout()  # Đã có từ UIToolbarTab
        content = QLabel("Nội dung Convert (demo). Bấm '🕘 Lịch sử' để mở panel bên phải.")
        content.setWordWrap(True)
        root_layout.addWidget(content)

        # Không cần nút refresh riêng nữa vì sẽ tự động refresh khi mở history panel
        """Load latest history data from source"""
        


