from PySide6.QtWidgets import (
    QVBoxLayout, QPushButton, QHBoxLayout,
    QLabel, QFrame,
)

from PySide6.QtCore import Signal

from typing import Optional

from app.ui_setting import COLORS


class BaseHistoryItem(QFrame):
    """Base class for history items with common functionality"""
    selected = Signal(str)

    def __init__(self, text: str, timestamp: str, meta: Optional[dict] = None):
        super().__init__()
        self._text = text
        self._timestamp = timestamp
        self._meta = meta or {}
        self._setup_ui()

    def _setup_ui(self):
        """Override in subclasses"""
        raise NotImplementedError

    def mousePressEvent(self, event):
        """Handle mouse click to select item"""
        self.selected.emit(self._text)
        super().mousePressEvent(event)


class TTSHistoryItem(BaseHistoryItem):
    """History item for Convert tab"""

    def _setup_ui(self):

        status = self._meta.get("status", "Draft")
        value = self._meta.get("value", self._text)

        # Thiết kế với viền ngoài, không viền bên trong
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['primary_bg']};
                border: 1px solid  {COLORS['border']};
                border-radius: 6px; 
                margin: 0px 0px;
                margin-bottom: 2px;
                margin-left: 4px;
                margin-right: 4px;
                padding: 0px 0px;
            }}
            QFrame:hover {{
                background-color: {COLORS['secondary_bg']};
            }}
            QFrame[selected="true"] {{
                background-color: {COLORS['secondary_bg']};
                border: 1px solid  {COLORS['border']};
            }}
            QLabel#value_label {{
                background: transparent;
                color: {COLORS['text_white']};
                font-size: 12px;
                border: none;
                margin: 0px 0px;
                margin-top: 4px;
                margin-left: 4px;
                margin-right: 4px;
                margin-bottom: 1px;
            }}
            QLabel#history_label {{
                color: {COLORS['text_history_label']}; 
                font-size: 10px;
                border: none;
                background: transparent;
                margin: 0px 0px;
                margin-top: 0px;
                margin-left: 4px;
                margin-right: 4px;
                 margin-bottom: 1px;
            }}
             QLabel#history_label_2 {{
                color: {COLORS['text_history_label_2']}; 
                font-size: 10px;
                border: none;
                background: transparent;
                padding: 0px 0px;
                margin: 0px 0px;
            }}
        """)

        layout = QVBoxLayout(self)

        # Layout compact với spacing 3px
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        if len(value) > 100:
            value = value[:100] + "..."
        # Text content - compact
        value_label = QLabel(value)
        value_label.setObjectName("value_label")
        value_label.setWordWrap(True)
        layout.addWidget(value_label)

        # Bottom row - timestamp (+ optional language from meta)
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        # Timestamp
        timestamp_label = QLabel(self._timestamp)
        timestamp_label.setObjectName("history_label")
        timestamp_label.setContentsMargins(0, 0, 0, 0)
        bottom_layout.addWidget(timestamp_label)

        # Optional language badge from meta
        lang_value = None
        try:
            lang_value = self._meta.get("lang")
        except Exception:
            lang_value = None
        if lang_value:
            lang_label = QLabel(f"{lang_value}")
            lang_label.setObjectName("history_label_2")
            bottom_layout.addWidget(lang_label)
        bottom_layout.addStretch()

        layout.addLayout(bottom_layout)

        # Kích thước compact
        self.setMinimumHeight(55)
        # self.setMaximumHeight(75)

    def set_selected(self, is_selected: bool) -> None:
        """Toggle selected visual state"""
        try:
            self.setProperty("selected", True if is_selected else False)
            # Re-apply style to reflect property change
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()
        except Exception:
            pass
