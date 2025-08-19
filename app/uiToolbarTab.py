from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,

)

from typing import Optional, Callable, Type
from app.historyPanel import HistoryPanel
from app.historyFeature import HistoryFeature


class UIToolbarTab(QWidget):
    """Base UI tab with toolbar functionality and tab logic"""

    def __init__(self, parent_main: QWidget):
        super().__init__()
        self.parent_main = parent_main
        self.history: Optional[HistoryFeature] = None

        root_layout = QVBoxLayout(self)
        self.toolbar = QHBoxLayout()
        root_layout.addLayout(self.toolbar)

    def enable_history(self, hist_title: str, item_factory: Callable,
                       on_item_selected: Optional[Callable] = None,
                       refresh_callback: Optional[Callable] = None,  # Thêm refresh_callback
                       panel_cls: Optional[Type[QWidget]] = None,
                       **panel_kwargs) -> HistoryFeature:
        """Enable history functionality for this tab"""
        self.history = HistoryFeature(
            parent_main=self.parent_main,
            hist_title=hist_title,
            item_factory=item_factory,
            on_item_selected=on_item_selected,
            refresh_callback=refresh_callback,  # Truyền refresh_callback
            panel_cls=panel_cls,
            **panel_kwargs
        )
        return self.history

    def append_history(self, text: str, meta: Optional[dict] = None):
        """Add item to history"""
        if self.history:
            self.history.panel.add_history(text, meta=meta or {})

    def has_history(self) -> bool:
        """Check if tab has history enabled"""
        return self.history is not None

    def get_current_panel(self) -> Optional[HistoryPanel]:
        """Get the current history panel"""
        return self.history.panel if self.history else None

    def add_toolbar_widget(self, widget: QWidget):
        """Add widget to toolbar"""
        self.toolbar.insertWidget(self.toolbar.count(), widget)