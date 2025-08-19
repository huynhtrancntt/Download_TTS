from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel
)
from typing import Optional

from app.uiToolbarTab import UIToolbarTab
from app.history.historyItem_TTS import TTSHistoryItem
from app.historyPanelConvertTab import HistoryPanelTab


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
            on_item_selected=self._on_history_selected,
            panel_cls=HistoryPanelTab,
            on_play=self._on_play,
            on_delete=self._on_delete,
            on_open_root=self._on_open_root
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

    def _on_history_selected(self, payload: Optional[dict] = None) -> None:
        """Handle click from a history item (if emitted by item widget)"""
        # TTSHistoryItem có signal selected(meta) – ở đây ta chỉ in ra hoặc có thể xử lý tùy ý
        try:
            if payload is not None:
                print("[ConvertTab] Selected history payload:", payload)
        except Exception:
            pass

    def _on_play(self, payload):
        try:
            print("[ConvertTab] Play requested:", payload)
        except Exception:
            pass

    def _on_delete(self, index: int):
        try:
            print(f"[ConvertTab] Delete index: {index}")
        except Exception:
            pass

    def _on_open_root(self):
        try:
            print("[ConvertTab] Open root requested")
        except Exception:
            pass


