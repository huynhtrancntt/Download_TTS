from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint

from typing import Optional, Callable, Tuple
from datetime import datetime

from app.appConfig import AppConfig


class HistoryPanelTab(QWidget):
    """
    Phiên bản HistoryPanel dành cho từng tab, có thêm các nút thao tác ở footer
    và callback tùy chỉnh.
    """

    def __init__(
        self,
        title_text: str = "Lịch sử",
        item_factory: Optional[Callable] = None,
        on_item_selected: Optional[Callable] = None,
        close_callback: Optional[Callable] = None,
        on_play: Optional[Callable] = None,
        on_delete: Optional[Callable] = None,
        on_open_root: Optional[Callable] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self.setFixedWidth(AppConfig.HISTORY_PANEL_WIDTH)
        self.item_factory = item_factory
        self.on_item_selected = on_item_selected
        self.close_callback = close_callback
        self._on_play_cb = on_play
        self._on_delete_cb = on_delete
        self._on_open_root_cb = on_open_root

        self._setup_ui(title_text)
        self.hide()

    def _setup_ui(self, title_text: str):
        self.setObjectName("HistoryPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        from app.ui.styles import AppStyles
        self.setStyleSheet(f"""
            QWidget#HistoryPanel {{
                background-color: {AppStyles.COLORS['background']};
                border-radius: 8px;
                border: 1px solid {AppStyles.COLORS['border']};
            }}
        """)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(12, 8, 12, 6)

        self.title = QLabel(title_text)
        self.title.setStyleSheet(f"""
            color: {AppStyles.COLORS['text_primary']};
            font-weight: 600;
            font-size: 14px;
        """)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                color: {AppStyles.COLORS['text_secondary']};
                background: transparent;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: {AppStyles.COLORS['text_primary']};
                background: {AppStyles.COLORS['border']};
                border-radius: 12px;
            }}
        """)
        close_btn.clicked.connect(self.close_panel)

        header_layout.addWidget(self.title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        layout.addLayout(header_layout)

        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet(
            f"background-color: {AppStyles.COLORS['border']};")
        layout.addWidget(separator)

        self.history_list = QListWidget()
        self.history_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.history_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self.history_list)

        footer = QHBoxLayout()
        self.btn_play = QPushButton("Phát")
        self.btn_play.clicked.connect(self._on_play_selected)
        self.btn_del = QPushButton("Xóa")
        self.btn_del.clicked.connect(self._delete_selected)
        self.btn_open = QPushButton("Thư mục")
        self.btn_open.clicked.connect(self._open_root)
        for b in (self.btn_play, self.btn_del, self.btn_open):
            footer.addWidget(b)
        layout.addLayout(footer)

    def _get_selected_item_widget(self) -> Optional[QWidget]:
        idx = self.history_list.currentRow()
        if idx < 0:
            return None
        item: QListWidgetItem = self.history_list.item(idx)
        return self.history_list.itemWidget(item)

    def _on_play_selected(self):
        widget = self._get_selected_item_widget()
        if self._on_play_cb and widget is not None:
            try:
                # Truyền text hoặc meta nếu có
                payload = getattr(widget, "_meta", None) or getattr(widget, "_text", None)
                self._on_play_cb(payload)
            except Exception:
                pass

    def _delete_selected(self):
        idx = self.history_list.currentRow()
        if idx < 0:
            return
        try:
            item = self.history_list.takeItem(idx)
            del item
            if self._on_delete_cb:
                self._on_delete_cb(idx)
        except Exception:
            pass

    def _open_root(self):
        if self._on_open_root_cb:
            try:
                self._on_open_root_cb()
            except Exception:
                pass

    def add_history(self, text: str, meta: Optional[dict] = None):
        timestamp = datetime.now().strftime("%H:%M %d/%m/%Y")
        if self.item_factory:
            item_widget = self.item_factory(text, timestamp, meta or {})
            self._connect_item_signals(item_widget)

            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())
            self.history_list.insertItem(0, list_item)
            self.history_list.setItemWidget(list_item, item_widget)

    def _connect_item_signals(self, item):
        if self.on_item_selected and hasattr(item, "selected"):
            try:
                item.selected.connect(self.on_item_selected)
            except Exception:
                pass

    def clear_history(self):
        self.history_list.clear()

    def show_with_animation(self, parent_width: int):
        self.show()
        top, height = self._calculate_geometry()
        end_x = parent_width - self.width()
        start_x = parent_width
        self.setGeometry(end_x, top, self.width(), height)
        self.move(QPoint(start_x, top))
        anim = QPropertyAnimation(self, b"pos", self)
        anim.setDuration(220)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.setStartValue(QPoint(start_x, top))
        anim.setEndValue(QPoint(end_x, top))
        anim.start()
        self._anim_show = anim

    def close_panel(self):
        self.hide_with_animation()

    def dock_right(self):
        if not self.parent():
            return
        parent = self.parent()
        top, height = self._calculate_geometry()
        x = parent.width() - self.width()
        self.setGeometry(x, top, self.width(), height)

    def _calculate_geometry(self) -> Tuple[int, int]:
        top = 0
        parent = self.parent()
        if hasattr(parent, "menuBar") and parent.menuBar():
            top = parent.menuBar().height()
        height = parent.height() - top
        return top, height

    def hide_with_animation(self):
        parent = self.parent()
        if not parent:
            self.hide()
            if self.close_callback:
                self.close_callback()
            return
        top, _ = self._calculate_geometry()
        start_pos = self.pos()
        end_pos = QPoint(parent.width(), top)
        anim = QPropertyAnimation(self, b"pos", self)
        anim.setDuration(200)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.setStartValue(start_pos)
        anim.setEndValue(end_pos)

        def _after():
            try:
                self.hide()
            finally:
                if self.close_callback:
                    self.close_callback()

        anim.finished.connect(_after)
        anim.start()
        self._anim_hide = anim


