# Import dependencies
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
                               QLabel, QScrollArea, QListWidget, QListWidgetItem,
                               QMessageBox, QMenu
                               )
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint


from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Tuple
from app.core.config import AppConfig
import json


class HistoryPanel(QWidget):

    """Improved history panel with better performance and UX"""

    def __init__(self, title_text: str = "Lịch sử",
                 item_factory: Optional[Callable] = None,
                 on_item_selected: Optional[Callable] = None,
                 refresh_callback: Optional[Callable] = None,  # Thêm refresh_callback
                 close_callback: Optional[Callable] = None,
                 on_play: Optional[Callable] = None,  # Thêm callback cho nút Phát
                 on_delete: Optional[Callable] = None,  # Thêm callback cho nút Xóa
                 on_open_root: Optional[Callable] = None,  # Thêm callback cho nút Thư mục
                 parent: Optional[QWidget] = None):

        super().__init__(parent)

        self.setFixedWidth(AppConfig.HISTORY_PANEL_WIDTH)
        # self.setStyleSheet()
        self.item_factory = item_factory
        self.on_item_selected = on_item_selected
        self.refresh_callback = refresh_callback  # Lưu refresh_callback
        self.close_callback = close_callback
        self._on_play_cb = on_play  # Lưu callback cho nút Phát
        self._on_delete_cb = on_delete  # Lưu callback cho nút Xóa
        self._on_open_root_cb = on_open_root  # Lưu callback cho nút Thư mục

        self._setup_ui(title_text)
        self.hide()

    def _setup_ui(self, title_text: str):
        """Setup the history panel UI"""
        self.setObjectName("HistoryPanel")  # Đặt ID cho HistoryPanel
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # Bỏ margin để thiết kế lại
        layout.setSpacing(0)

        # Background và viền phân biệt - use new styling
        from app.ui.styles import AppStyles
        self.setStyleSheet(f"""
            QWidget#HistoryPanel {{
                background-color: {AppStyles.COLORS['background']};
                border-radius: 8px;
                border: 1px solid {AppStyles.COLORS['border']};
            }}

            /* Footer container background */
            QWidget#HistoryPanel QWidget#Footer {{
                background-color: {AppStyles.COLORS['background']};
            }}

        """)
        # Header nhỏ gọn
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

        # Thêm nút cập nhật
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(24, 24)
        refresh_btn.setToolTip("Cập nhật danh sách")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                color: {AppStyles.COLORS['text_secondary']};
                background: transparent;
                border: none;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: {AppStyles.COLORS['text_primary']};
                background: {AppStyles.COLORS['border']};
                border-radius: 12px;
            }}
        """)
        refresh_btn.clicked.connect(self.refresh_history)

        header_layout.addWidget(self.title)
        header_layout.addStretch()
        header_layout.addWidget(refresh_btn)  # Thêm nút cập nhật
        header_layout.addWidget(close_btn)
        layout.addLayout(header_layout)

        # Thêm đường viền phân biệt
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet(
            f"background-color: {AppStyles.COLORS['border']};")
        layout.addWidget(separator)

        # QListWidget nhỏ gọn (đặt TRƯỚC footer để footer nằm dưới cùng)
        self.history_list = QListWidget()
        self.history_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.history_list.setStyleSheet("""
             QListWidget {
                background: #0f172a;
                border: none;
                outline: none;
                spacing: 0px;
                border-radius: 0px;
            }
            QListWidget::item {
                background: transparent;
                border: none;
                padding: 3px;
                margin: 0px;

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
        self.history_list.setSpacing(6)
        self.history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Đồng bộ highlight khi đổi selection
        try:
            self.history_list.currentRowChanged.connect(self._update_selection_styles)
        except Exception:
            pass
        # Context menu for right-click actions
        try:
            self.history_list.setContextMenuPolicy(Qt.CustomContextMenu)
            self.history_list.customContextMenuRequested.connect(self._on_history_context_menu)
        except Exception:
            pass
        layout.addWidget(self.history_list)

        # Footer separator + 2 hàng nút (đặt SAU list để luôn ở cuối)
        footer_sep = QWidget()
        footer_sep.setFixedHeight(1)
        footer_sep.setStyleSheet(
            f"background-color: {AppStyles.COLORS['border']};")
        layout.addWidget(footer_sep)

        # Wrap footer in QWidget to style background via QSS
        footer_container = QWidget()
        footer_container.setObjectName("Footer")
        footer = QVBoxLayout(footer_container)
        footer.setContentsMargins(8, 6, 8, 8)
        footer.setSpacing(6)

        # Hàng 1: Phát + Xóa (căn giữa)
        row1_widget = QWidget()
        row1 = QHBoxLayout(row1_widget)
        self.btn_play = QPushButton("Phát")
        self.btn_del = QPushButton("Xóa")
        self.btn_del.setEnabled(False)  
        row1.addWidget(self.btn_play)
        row1.addWidget(self.btn_del)

        # Hàng 2: Thư mục (căn giữa)
        row2_widget = QWidget()
        row2 = QHBoxLayout(row2_widget)
        self.btn_open = QPushButton("Thư mục")
        # row2.addStretch()
        row2.addWidget(self.btn_open)
        row2.addStretch()

        footer.addWidget(row1_widget)
        # footer.addWidget(row2_widget)
        layout.addWidget(footer_container)
        
        # Kết nối các nút với callback
        self.btn_play.clicked.connect(self._on_play_selected)
        self.btn_del.clicked.connect(self._delete_selected)
        self.btn_open.clicked.connect(self._open_root)

    def add_history(self, text: str, meta: Optional[dict] = None):
        """Add a new history item using QListWidget"""
        timestamp = datetime.now().strftime("%H:%M %d/%m/%Y")

        if self.item_factory:
            item_widget = self.item_factory(text, timestamp, meta or {})
            self._connect_item_signals(item_widget)

            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())

            self.history_list.insertItem(0, list_item)
            self.history_list.setItemWidget(list_item, item_widget)

    def _connect_item_signals(self, item):
        """Connect item selection signal and wire selection highlighting"""
        if hasattr(item, "selected"):
            try:
                item.selected.connect(self._on_item_widget_selected)
            except Exception:
                pass  # Fail silently if connection fails

    def _on_item_widget_selected(self, _payload):
        """When an item widget is clicked, select it and forward a rich payload (text, timestamp, meta)"""
        try:
            widget = self.sender()
            if widget is not None:
                self._select_widget(widget)
            # Build rich payload from the widget instead of raw signal value
            payload_data = {}
            try:
                base_text = getattr(widget, '_text', None)
                base_ts = getattr(widget, '_timestamp', None)
                meta = getattr(widget, '_meta', {})
                meta_copy = dict(meta) if isinstance(meta, dict) else {}
                payload_data = {
                    'text': base_text,
                    'timestamp': base_ts,
                    'meta': meta_copy,
                }
                # Also merge meta fields at the top level for convenience
                if isinstance(meta_copy, dict):
                    payload_data.update(meta_copy)
            except Exception:
                pass
            # Forward to external callback after selection
            if self.on_item_selected:
                self.on_item_selected(payload_data)
        except Exception:
            pass

    def _on_history_context_menu(self, pos):
        """Show context menu on right-click for history list"""
        try:
            item = self.history_list.itemAt(pos)
            if not item:
                return
            index = self.history_list.row(item)
            if index < 0:
                return
            # Ensure the clicked item is selected
            self.history_list.setCurrentRow(index)
            # Build and show context menu
            menu = QMenu(self)
            menu.addAction("Xóa", lambda: self._delete_selected())
            global_pos = self.history_list.viewport().mapToGlobal(pos)
            menu.exec(global_pos)
        except Exception:
            pass

    def _select_widget(self, widget) -> None:
        """Set the given widget as the current selection in the list"""
        try:
            count = self.history_list.count()
            for i in range(count):
                it = self.history_list.item(i)
                w = self.history_list.itemWidget(it)
                if w is widget:
                    self.history_list.setCurrentRow(i)
                    break
            # Update styles
            self._update_selection_styles(self.history_list.currentRow())
        except Exception:
            pass

    def _update_selection_styles(self, current_index: int) -> None:
        """Toggle selected style on widgets to reflect current selection"""
        try:
            count = self.history_list.count()
            for i in range(count):
                it = self.history_list.item(i)
                w = self.history_list.itemWidget(it)
                if hasattr(w, 'set_selected'):
                    w.set_selected(i == current_index)
            # Toggle delete button based on selection
            if hasattr(self, 'btn_del'):
                self.btn_del.setEnabled(current_index >= 0)
        except Exception:
            pass

    def refresh_history(self):
        """Refresh history list with latest items"""
        # Clear current list
        self.history_list.clear()
        # Disable delete button when list is cleared
        if hasattr(self, 'btn_del'):
            self.btn_del.setEnabled(False)
        
        # Emit signal để yêu cầu cập nhật từ bên ngoài
        if hasattr(self, 'refresh_requested'):
            self.refresh_requested.emit()
        
        # Hoặc gọi callback nếu có
        if hasattr(self, 'refresh_callback') and self.refresh_callback:
            self.refresh_callback()
            
    def _on_history_selected(self, payload: Optional[dict] = None) -> None:
        """Handle history item selection"""
        if self._on_history_selected:
            self._on_history_selected(payload)

    def _get_selected_item_widget(self):
        """Get the currently selected item widget"""
        idx = self.history_list.currentRow()
        if idx < 0:
            return None


        item = self.history_list.item(idx)
        return self.history_list.itemWidget(item)

    def _on_play_selected(self):
        """Handle play button click"""
        widget = self._get_selected_item_widget()
        if self._on_play_cb and widget is not None:
            try:
                # Truyền text hoặc meta nếu có
                payload = getattr(widget, "_meta", None) or getattr(widget, "_text", None)
                self._on_play_cb(payload)
            except Exception:
                pass

    def _delete_selected(self):
        """Handle delete button click with confirmation"""
        idx = self.history_list.currentRow()
        if idx < 0:
            return
        try:
            # Lấy widget để hiển thị thông tin xác nhận
            item = self.history_list.item(idx)
            widget = self.history_list.itemWidget(item)
            display_text = getattr(widget, "_text", "mục đã chọn")

            # Hỏi xác nhận
            reply = QMessageBox.question(
                self,
                "Xác nhận xóa",
                f"Bạn có chắc muốn xóa mục lịch sử này và xóa file liên quan (nếu có)?\n\n{display_text}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

            # Gọi callback để xử lý logic xóa file/JSON trước khi xóa UI item
            if self._on_delete_cb:
                try:
                    self._on_delete_cb(idx)
                except Exception:
                    pass

            # Xóa khỏi UI
            taken_item = self.history_list.takeItem(idx)
            del taken_item
            # Auto-select the next item (or previous if last was removed) and update state
            try:
                remaining = self.history_list.count()
                if remaining > 0:
                    new_index = min(idx, remaining - 1)
                    self.history_list.setCurrentRow(new_index)
                    # Update styles for new selection
                    self._update_selection_styles(new_index)
                    # Fire external selection callback with rich payload
                    if self.on_item_selected:
                        try:
                            item2 = self.history_list.item(new_index)
                            widget2 = self.history_list.itemWidget(item2)
                            base_text = getattr(widget2, '_text', None)
                            base_ts = getattr(widget2, '_timestamp', None)
                            meta2 = getattr(widget2, '_meta', {})
                            meta_copy2 = dict(meta2) if isinstance(meta2, dict) else {}
                            payload2 = {
                                'text': base_text,
                                'timestamp': base_ts,
                                'meta': meta_copy2,
                            }
                            if isinstance(meta_copy2, dict):
                                payload2.update(meta_copy2)
                            self.on_item_selected(payload2)
                        except Exception:
                            pass
                # Update delete button based on current selection
                if hasattr(self, 'btn_del'):
                    self.btn_del.setEnabled(self.history_list.currentRow() >= 0)
            except Exception:
                if hasattr(self, 'btn_del'):
                    self.btn_del.setEnabled(False)
        except Exception:
            pass

    def _open_root(self):
        """Handle open root button click"""
        if self._on_open_root_cb:
            try:
                self._on_open_root_cb()
            except Exception:
                pass

    def clear_history(self):
        """Clear all history items"""
        self._clear_history_silent()

    def _clear_history_silent(self):
        """Clear all history items from QListWidget"""
        self.history_list.clear()
        # Ensure delete button is disabled when no items
        if hasattr(self, 'btn_del'):
            self.btn_del.setEnabled(False)

    def show_with_animation(self, parent_width: int):
        """Slide in the panel from the right with animation"""
        self.show()
        top, height = self._calculate_geometry()
        end_x = parent_width - self.width()
        start_x = parent_width
        # Start off-screen at the right edge
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
        """Close panel with slide-out animation"""
        self.hide_with_animation()

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

    def hide_with_animation(self):
        """Slide out the panel to the right and hide when finished"""
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
