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
    refresh_history = Signal()  # Thêm signal mới

    def __init__(self, parent_main: QWidget, hist_title: str,
                 item_factory: Callable,
                 on_item_selected: Optional[Callable] = None,
                 refresh_callback: Optional[Callable] = None,  # Thêm callback refresh
                 panel_cls: Optional[Type[QWidget]] = None,
                 **panel_kwargs):
        super().__init__(parent_main)

        # History button
        self.btn = QPushButton("🕘 Lịch sử")
        self.btn.setStyleSheet(
            "background-color:#2b2d3a; border:1px solid #444; border-radius:6px; padding:8px; font-size:12px;")
        self.btn.clicked.connect(self._on_history_button_clicked)

        # History panel (allow custom panel class)
        PanelClass = panel_cls or HistoryPanel
        self.panel = PanelClass(
            title_text=hist_title,
            item_factory=item_factory,
            on_item_selected=on_item_selected,
            refresh_callback=refresh_callback,  # Truyền callback refresh
            close_callback=self._on_panel_closed,
            parent=parent_main,
            **panel_kwargs
        )
        
        # Kết nối signal refresh
        self.refresh_history.connect(self._on_refresh_requested)

    def _on_panel_closed(self):
        """Handle panel close event"""
        self.request_hide_history.emit()

    def _on_refresh_requested(self):
        """Handle refresh request"""
        if hasattr(self.panel, 'refresh_callback') and self.panel.refresh_callback:
            self.panel.refresh_callback()

    def _on_history_button_clicked(self):
        """Handle history button click - show panel and auto-refresh"""
        # Emit signal để hiển thị panel
        self.request_show_history.emit()
        
        # Tự động refresh data khi mở panel
        if hasattr(self.panel, 'refresh_callback') and self.panel.refresh_callback:
            # Delay một chút để panel hiển thị trước
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self.panel.refresh_callback)
