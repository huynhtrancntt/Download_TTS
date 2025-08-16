from this import s
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
                               QLabel, QScrollArea, QListWidget, QListWidgetItem
                               )
from PySide6.QtCore import Qt


from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Tuple
from app.appConfig import AppConfig

class HistoryPanel(QWidget):
    
    """Improved history panel with better performance and UX"""

    def __init__(self, title_text: str = "Lịch sử",
                 item_factory: Optional[Callable] = None,
                 on_item_selected: Optional[Callable] = None,
                 close_callback: Optional[Callable] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
       
   
        self.setFixedWidth(AppConfig.HISTORY_PANEL_WIDTH)
        # self.setStyleSheet()
        self.item_factory = item_factory
        self.on_item_selected = on_item_selected
        self.close_callback = close_callback

        self._setup_ui(title_text)
        self.hide()

    def _setup_ui(self, title_text: str):
        """Setup the history panel UI"""
        self.setObjectName("HistoryPanel")  # Đặt ID cho HistoryPanel
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # Bỏ margin để thiết kế lại
        layout.setSpacing(0)
        
        # Background và viền phân biệt
        self.setStyleSheet("""
            QWidget#HistoryPanel {
                background-color: #0f172b;
                border-radius: 8px;
                border: 1px solid #334155;
            }
        """)
        # Header nhỏ gọn
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(12, 8, 12, 6)
        
        self.title = QLabel(title_text)
        self.title.setStyleSheet("""
            color: #f1f5f9; 
            font-weight: 600; 
            font-size: 14px;
        """)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                color: #94a3b8;
                background: transparent;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #f1f5f9;
                background: #334155;
                border-radius: 12px;
            }
        """)
        close_btn.clicked.connect(self.close_panel)

        header_layout.addWidget(self.title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        layout.addLayout(header_layout)
        
        # Thêm đường viền phân biệt
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #334155;")
        layout.addWidget(separator)

        # QListWidget nhỏ gọn
        self.history_list = QListWidget()
        self.history_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.history_list.setStyleSheet("""
            QListWidget {
                background: #0f172a;
                border: none;
                outline: none;
                spacing: 2px;
            }
            QListWidget::item {
                background: transparent;
                border: none;
                padding: 0px;
                margin: 2px 0px;
            }
            QListWidget::item:selected {
                background: transparent;
            }
            QScrollBar:vertical {
                background: #334155;
                width: 4px;
                border-radius: 2px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #475569;
                border-radius: 2px;
                min-height: 15px;
            }
            QScrollBar::handle:vertical:hover {
                background: #64748b;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        self.history_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # layout.addWidget(QLabel("TTTTe"))
        layout.addWidget(self.history_list)
        

    def add_history(self, text: str, lang: str = "vi-VN", meta: Optional[dict] = None):
        """Add a new history item using QListWidget"""
        timestamp = datetime.now().strftime("%H:%M %d/%m/%Y")

        if self.item_factory:
            # Tạo TTSHistoryItem widget
            item_widget = self.item_factory(text, timestamp, lang, meta or {})
            self._connect_item_signals(item_widget)

            # Tạo QListWidgetItem
            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())
            
            # Thêm vào đầu danh sách (vị trí 0)
            self.history_list.insertItem(0, list_item)
            self.history_list.setItemWidget(list_item, item_widget)

    def _connect_item_signals(self, item):
        """Connect item selection signal if available"""
        if self.on_item_selected and hasattr(item, "selected"):
            try:
                item.selected.connect(self.on_item_selected)
            except Exception:
                pass  # Fail silently if connection fails

    def clear_history(self):
        """Clear all history items"""
        self._clear_history_silent()

    def _clear_history_silent(self):
        """Clear all history items from QListWidget"""
        self.history_list.clear()

    def show_with_animation(self, parent_width: int):
        """Show panel without animation"""
        self.show()
        top, height = self._calculate_geometry()
        end_x = parent_width - self.width()
        self.setGeometry(end_x, top, self.width(), height)

    def close_panel(self):
        """Close panel without animation"""
        self.hide()

        if self.close_callback:
            self.close_callback()

    def dock_right(self):
        """Dock panel to the right side of parent"""
        if not self.parent():
            return

        parent = self.parent()
        top, height = self._calculate_geometry()
        x = parent.width() - self.width()
        self.setGeometry(x, top, self.width(), height)

    def _calculate_geometry(self) -> Tuple[int, int]:
        """Calculate top position and height for the panel"""
        top = 0
        parent = self.parent()

        if hasattr(parent, "menuBar") and parent.menuBar():
            top = parent.menuBar().height()

        height = parent.height() - top
        return top, height
