from PySide6.QtWidgets import (
    QWidget, QPushButton
)
from PySide6.QtCore import Signal, QObject

from typing import Optional, Callable

from app.historyPanel import HistoryPanel
from typing import Type

class HistoryFeature(QObject):
    """Feature class to manage history functionality"""
    request_show_history = Signal()
    request_hide_history = Signal()

    def __init__(self, parent_main: QWidget, hist_title: str,
                 item_factory: Callable,
                 on_item_selected: Optional[Callable] = None,
                 panel_cls: Optional[Type[QWidget]] = None,
                 **panel_kwargs):
        super().__init__(parent_main)

        # History button
        self.btn = QPushButton("🕘 Lịch sử")
        self.btn.setStyleSheet(
            "background-color:#2b2d3a; border:1px solid #444; border-radius:6px; padding:8px; font-size:12px;")
        self.btn.clicked.connect(self.request_show_history.emit)

        # History panel (allow custom panel class)
        PanelClass = panel_cls or HistoryPanel
        self.panel = PanelClass(
            title_text=hist_title,
            item_factory=item_factory,
            on_item_selected=on_item_selected,
            close_callback=self._on_panel_closed,
            parent=parent_main,
            **panel_kwargs
        )

    def _on_panel_closed(self):
        """Handle panel close event"""
        self.request_hide_history.emit()
