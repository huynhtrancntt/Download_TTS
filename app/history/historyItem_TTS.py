from PySide6.QtWidgets import (
    QVBoxLayout, QPushButton, QHBoxLayout,
    QLabel, QFrame,
)
from PySide6.QtCore import Signal

from typing import Optional


class BaseHistoryItem(QFrame):
    """Base class for history items with common functionality"""
    selected = Signal(str)

    def __init__(self, text: str, timestamp: str, lang: str = "vi-VN", meta: Optional[dict] = None):
        super().__init__()
        self._text = text
        self._timestamp = timestamp
        self._lang = lang
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
        self.setStyleSheet("""
            QFrame { 
                background-color: #0f172b;
                border: 1px solid #475569;
                border-radius: 6px; 
                padding: 8px 12px;
            }
            QFrame:hover {
                background-color: #1e293b;
                border: 1px solid #475569;
            }
            QLabel { 
                color: #f1f5f9; 
                background: transparent;
                border: none;
            }
        """)

        layout = QVBoxLayout(self)

        # Layout compact với spacing 3px
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        if len(value) > 50:
          value = value[:50] + "..."
        # Text content - compact
        value_label = QLabel(value)
        value_label.setStyleSheet("""
            QLabel {
                background: transparent;
                color: #f1f5f9;
                font-size: 13px;
                font-weight: 400;
                border: none;
                line-height: 18px;  /* ← Thêm line-height */
                word-wrap: break-word;  /* ← Thêm word-wrap */
            }
        """)
        value_label.setWordWrap(True)
        layout.addWidget(value_label)

        # Bottom row - timestamp và language gần nhau
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(3)
        
        # Timestamp
        timestamp_label = QLabel(self._timestamp)
        timestamp_label.setStyleSheet("""
            color: #64748b; 
            font-size: 11px;
            border: none;
            background: transparent;
        """)
        
        # Language
        lang_label = QLabel(f"• {self._lang}")
        lang_label.setStyleSheet("""
            color: #64748b; 
            font-size: 11px;
            border: none;
            background: transparent;
        """)
        
        bottom_layout.addWidget(timestamp_label)
        bottom_layout.addWidget(lang_label)
        bottom_layout.addStretch()
        
        layout.addLayout(bottom_layout)
        
        # Kích thước compact
        self.setMinimumHeight(55)
        # self.setMaximumHeight(75)

    def _get_simple_status_chip_style(self, status: str) -> str:
        """Get simple style for status chip"""
        status_lower = status.lower()
        if status_lower == "applied":
            return """
                QLabel { 
                    padding: 4px 8px; 
                    border-radius: 4px; 
                    color: #ffffff; 
                    background-color: #48bb78;
                    font-weight: 500; 
                    font-size: 10px;
                }
            """
        elif status_lower == "auto":
            return """
                QLabel { 
                    padding: 4px 8px; 
                    border-radius: 4px; 
                    color: #ffffff; 
                    background-color: #ed8936;
                    font-weight: 500; 
                    font-size: 10px;
                }
            """
        else:  # Draft
            return """
                QLabel { 
                    padding: 4px 8px; 
                    border-radius: 4px; 
                    color: #ffffff; 
                    background-color: #667eea;
                    font-weight: 500; 
                    font-size: 10px;
                }
            """
            
    def _get_status_chip_style(self, status: str) -> str:
        """Legacy method - redirects to simple version"""
        return self._get_simple_status_chip_style(status)
