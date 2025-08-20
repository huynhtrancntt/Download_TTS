# -*- coding: utf-8 -*-
"""
Ứng dụng Text-to-Speech với giao diện PySide6
Phiên bản tối ưu với comment tiếng Việt và cấu trúc code rõ ràng
"""

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QLabel, QProgressBar, QMainWindow, QTabWidget, QStatusBar, 
    QLineEdit, QGroupBox, QListWidget, QListWidgetItem, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, QTime, QEvent, Signal
from PySide6.QtGui import QAction, QColor, QIcon
import sys
import signal
import os
from datetime import datetime
from typing import Optional, List

# Import các module của ứng dụng
from app.historyPanel import HistoryPanel
from app.core.config import AppConfig
from app.tabs.tts_tab import TTSTab
from app.tabs.convert_tab import ConvertTab
from app.uiToolbarTab import UIToolbarTab
from app.ui_setting import _init_addStyle, resource_path
from app.utils.helps import clean_all_temp_parts


class ClickToCloseOverlay(QWidget):
    """
    Lớp overlay để phát hiện click bên ngoài panel
    Sử dụng để đóng các panel lịch sử khi click ra ngoài
    """
    clicked_outside = Signal()  # Signal phát ra khi click bên ngoài

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Khởi tạo overlay
        Args:
            parent: Widget cha (thường là MainWindow)
        """
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Widget)
        self.setStyleSheet("background: rgba(0,0,0,0.25);")  # Nền trong suốt với opacity 25%
        self.hide()  # Ẩn mặc định

    def mousePressEvent(self, event) -> None:
        """
        Xử lý sự kiện click chuột để phát tín hiệu clicked_outside
        Args:
            event: Sự kiện click chuột
        """
        self.clicked_outside.emit()
        event.accept()


class MainWindow(QMainWindow):
    """
    Cửa sổ chính của ứng dụng Text-to-Speech
    
    Chức năng chính:
    - Quản lý các tab chức năng (TTS, Convert, Simple)
    - Xử lý tiến trình và trạng thái ứng dụng
    - Quản lý hệ thống xác thực và lịch sử
    - Điều khiển giao diện người dùng
    """

    def __init__(self) -> None:
        """
        Khởi tạo cửa sổ chính
        Thiết lập giao diện, kết nối tín hiệu và khởi tạo trạng thái ban đầu
        """
        super().__init__()
        
        # Áp dụng style cho ứng dụng
        _init_addStyle(self)
        
        # Biến trạng thái nội bộ
        self._closing_history: bool = False  # Ngăn đệ quy khi đóng lịch sử
        self._setup_complete: bool = False   # Theo dõi quá trình khởi tạo
        self._show_key_auth: bool = True     # Điều khiển hiển thị group xác thực key
        
        # Thiết lập các thành phần chính
        self._setup_window()
        self._setup_ui()
        self._setup_progress_system()
        self._setup_connections()

        # Đánh dấu hoàn tất khởi tạo
        self._setup_complete = True

        # Kích hoạt trạng thái tab ban đầu
        current_tab = self.tabs.currentIndex()
        self._on_tab_changed(current_tab)

    def _setup_window(self) -> None:
        """
        Thiết lập thuộc tính cơ bản của cửa sổ chính
        Bao gồm: tiêu đề, icon, kích thước và vị trí
        """
        # Thiết lập tiêu đề cửa sổ
        self.setWindowTitle(AppConfig.WINDOW_TITLE)

        # Thiết lập icon ứng dụng
        icon_path = resource_path(AppConfig.ICON_PATH)
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            print(f"Cảnh báo: Không tìm thấy icon tại {icon_path}")

        # Thiết lập kích thước cửa sổ 400x600
        self.setMinimumSize(800, 700)  # Kích thước tối thiểu 400x600
        self.resize(800, 700)  # Kích thước mặc định khi khởi động 400x600

        # Có thể bật lại nếu cần thiết lập kích thước cố định
        # self.setMinimumSize(*AppConfig.MIN_WINDOW_SIZE)
        # self.resize(*AppConfig.DEFAULT_WINDOW_SIZE)
        
        # Căn giữa cửa sổ trên màn hình
        self._center_on_screen()

    def _setup_ui(self) -> None:
        """
        Thiết lập các thành phần giao diện chính
        Bao gồm: menu, tabs, progress bar, overlay
        """
        # Tạo scroll area thay vì widget thông thường
        from PySide6.QtWidgets import QScrollArea
        
        # Tạo scroll area làm central widget
        self.scroll_area = QScrollArea()
        self.setCentralWidget(self.scroll_area)
        
        # Tạo widget chứa nội dung
        self.content_widget = QWidget()
        self.scroll_area.setWidget(self.content_widget)
        
        # Thiết lập scroll area
        self.scroll_area.setWidgetResizable(True)  # Widget tự động resize
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # Hiện thanh trượt dọc khi cần
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # Hiện thanh trượt ngang khi cần
        
        # Tạo layout chính cho content widget
        main_layout = QVBoxLayout(self.content_widget)
        main_layout.setSpacing(2)  # Giảm khoảng cách giữa các widget
        main_layout.setContentsMargins(5, 5, 5, 5)  # Giảm margin

        # Thiết lập menu và status bar TRƯỚC - để các tab có thể truy cập
        self._setup_menu_and_status()

        # Tạo widget tab chính
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tạo các tab - bây giờ status bar đã sẵn sàng
        self._setup_tabs()

        # Thiết lập khu vực progress và log
        self._setup_progress_ui(main_layout)

        # Thiết lập overlay và controls
        self._setup_overlay_controls()

        # Thiết lập trạng thái ban đầu của UI
        self._initialize_ui_state()

    def _setup_tabs(self) -> None:
        """
        Thiết lập và tạo các tab chức năng
        Hiện tại chỉ có tab TTS, có thể mở rộng thêm Convert, Simple
        """
        # Tạo tab TTS
        self.tab_tts = TTSTab(self)
        # Tạo tab Convert (mới)
        self.tab_convert = ConvertTab(self)

        # Lưu danh sách tất cả tabs để quản lý
        self._all_tabs: List[UIToolbarTab] = [self.tab_tts, self.tab_convert]

        # Thêm tabs vào widget
        self.tabs.addTab(self.tab_tts, "Text to Speech")
        self.tabs.addTab(self.tab_convert, "Convert")

    def _initialize_ui_state(self) -> None:
        """
        Khởi tạo trạng thái ban đầu của giao diện
        Thiết lập visibility và trạng thái của các thành phần
        """
        # Đảm bảo progress widget hiển thị mặc định (ứng dụng bắt đầu ở Tab TTS)
        if hasattr(self, 'progress_widget') and self.progress_widget:
            self.progress_widget.setVisible(True)

        # Thêm thông báo log cho trạng thái đã sẵn sàng
        self._add_log_item(
            "🎉 Ứng dụng đã sẵn sàng - Tất cả chức năng đã được kích hoạt", 
            level="info"
        )
        # Progress bar sẽ ẩn mặc định, chỉ hiện khi có giá trị

        # Đảm bảo output list hiển thị
        if hasattr(self, 'output_list') and self.output_list:
            self.output_list.setVisible(True)

    def _setup_progress_ui(self, parent_layout: QVBoxLayout) -> None:
        """
        Thiết lập khu vực giao diện tiến trình và log
        Bao gồm: xác thực key, thanh tiến trình, nút điều khiển, khu vực log
        """
        # Tạo widget chứa toàn bộ khu vực progress
        self.progress_widget = QWidget()
        progress_layout = QVBoxLayout(self.progress_widget)
        progress_layout.addStretch()
        
        # Thiết lập nhóm xác thực key
        self._setup_key_auth_group(progress_layout)

        # Tiêu đề tiến trình - lưu reference để có thể ẩn/hiện
        self._progress_title = QLabel("Tiến trình xử lý")
        self._progress_title.setStyleSheet(
            "font-size: 16px; font-weight: 600; margin-bottom: 10px;"
        )
        progress_layout.addWidget(self._progress_title)

        # Thanh tiến trình chính
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_bar)

        # Tạo các nút điều khiển tiến trình
        self._create_progress_control_buttons(progress_layout)

        # Khu vực hiển thị log
        self._setup_log_area(progress_layout)

        # Thêm progress widget vào layout chính
        parent_layout.addWidget(self.progress_widget)

        # Thiết lập size policy để tối ưu hiển thị
        self._configure_progress_size_policies()

        # Thêm stretch cuối để căn chỉnh
        progress_layout.addStretch()

    def _create_progress_control_buttons(self, progress_layout: QVBoxLayout) -> None:
        """
        Tạo các nút điều khiển tiến trình (Bắt đầu, Tạm dừng, Tiếp tục, Dừng)
        """
        button_layout = QHBoxLayout()
        
        # Tạo các nút điều khiển
        self.btn_start = QPushButton("▶ Bắt đầu")
        self.btn_pause = QPushButton("⏸ Tạm dừng")
        self.btn_resume = QPushButton("⏯ Tiếp tục")
        self.btn_stop = QPushButton("⏹ Dừng")

        # Áp dụng style và kích thước cho các nút
        for btn in (self.btn_start, self.btn_pause, self.btn_resume, self.btn_stop):
            btn.setStyleSheet(AppConfig.BUTTON_STYLE)
            btn.setMinimumWidth(70)   # Chiều rộng tối thiểu
            btn.setMaximumWidth(100)  # Chiều rộng tối đa để tránh quá lớn
            button_layout.addWidget(btn)

        button_layout.addStretch()
        progress_layout.addLayout(button_layout)

    def _setup_log_area(self, progress_layout: QVBoxLayout) -> None:
        """
        Thiết lập khu vực hiển thị log
        """
        self.output_list = QListWidget()
        
        # Cấu hình hiển thị log
        self.output_list.setAlternatingRowColors(True)  # Màu xen kẽ các dòng
        self.output_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)  # Cuộn mượt
        
        # Giới hạn chiều cao của log frame để không quá dài
        self.output_list.setMaximumHeight(150)  # Giới hạn chiều cao tối đa 150px
        self.output_list.setMinimumHeight(100)  # Chiều cao tối thiểu 100px
        
        progress_layout.addWidget(self.output_list)

    def _configure_progress_size_policies(self) -> None:
        """
        Cấu hình size policy cho các thành phần progress để tối ưu hiển thị
        """
        self.progress_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Thay đổi size policy của output_list để không mở rộng quá mức
        self.output_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def _setup_key_auth_group(self, parent_layout: QVBoxLayout) -> None:
        """
        Thiết lập nhóm xác thực key
        Bao gồm: ô nhập key, nút mở khóa, trạng thái khóa
        """
        # Tạo group box cho xác thực
        key_group = QGroupBox("🔐 Xác thực truy cập")
        key_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #334155;
                border-radius: 8px;
                margin: 5px 0px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #FFD700;
            }
        """)

        # Layout ngang cho các thành phần trong group
        key_layout = QHBoxLayout(key_group)
        key_layout.setContentsMargins(10, 5, 10, 5)  # Giảm margin cho màn hình nhỏ

        # Tạo các thành phần xác thực
        self._create_key_input_components(key_layout)

        # Thêm group vào layout chính
        parent_layout.addWidget(key_group)

        # Lưu reference để có thể toggle sau này
        self.key_auth_group = key_group
        
        self._show_key_auth = False
        # Sử dụng biến điều khiển để ẩn/hiện group
        key_group.setVisible(self._show_key_auth)

    def _create_key_input_components(self, key_layout: QHBoxLayout) -> None:
        """
        Tạo các thành phần nhập key (label, input, button, status)
        """
        # Label cho key
        key_label = QLabel("Key:")
        key_label.setStyleSheet("font-weight: normal; margin-right: 3px;")

        # Ô nhập key
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Nhập key...")
        self.key_input.setMinimumWidth(80)
        self.key_input.setMaximumWidth(150)
        self.key_input.setStyleSheet("""
            QLineEdit:focus {
                border: 2px solid #FFD700;
            }
        """)
        self.key_input.textChanged.connect(self._on_key_changed)

        # Nút mở khóa
        self.unlock_btn = QPushButton("🔓 Mở khóa")
        self.unlock_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF6B35;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #E55A2B;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        self.unlock_btn.clicked.connect(self._on_unlock_clicked)

        # Label trạng thái khóa
        self.key_status = QLabel("🔒 Đã khóa")
        self.key_status.setStyleSheet("color: #FF6B35; font-weight: bold;")

        # Thêm các thành phần vào layout
        key_layout.addWidget(key_label)
        key_layout.addWidget(self.key_input)
        key_layout.addWidget(self.unlock_btn)
        key_layout.addWidget(self.key_status)
        key_layout.addStretch()

    def _setup_overlay_controls(self):
        """Setup overlay and close button"""
        # Overlay for clicking outside panels
        self.overlay = ClickToCloseOverlay(self)
        self.overlay.clicked_outside.connect(self._close_current_tab_history)

        # Floating close button
        self.close_history_btn = QPushButton("✕", self)
        self.close_history_btn.setFixedSize(28, 28)
        self.close_history_btn.setStyleSheet("""
            QPushButton { 
                background-color: #2b2d3a; 
                color: white; 
                border: 1px solid #444; 
                border-radius: 14px; 
                font-weight: bold; 
            }
            QPushButton:hover { 
                background-color: #3a3d4f; 
            }
        """)
        self.close_history_btn.clicked.connect(self._close_current_tab_history)
        self.close_history_btn.hide()

    def _setup_menu_and_status(self):
        """Setup menu bar and status bar"""
        # Menu bar
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")
        exit_action = QAction("Thoát", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("&View")
        toggle_history_action = QAction("Hiện/Ẩn lịch sử", self)
        toggle_history_action.triggered.connect(
            self._toggle_current_tab_history)
        view_menu.addAction(toggle_history_action)

        close_history_action = QAction("Đóng lịch sử (Esc)", self)
        close_history_action.setShortcut("Esc")
        close_history_action.triggered.connect(self._close_current_tab_history)
        view_menu.addAction(close_history_action)

        # Thêm action để điều khiển hiển thị group xác thực key
        toggle_key_auth_action = QAction("Hiện/Ẩn xác thực key", self)
        toggle_key_auth_action.triggered.connect(self.toggle_key_auth_visibility)
        view_menu.addAction(toggle_key_auth_action)

        # Thêm action để ẩn group xác thực key
        hide_key_auth_action = QAction("Ẩn xác thực key", self)
        hide_key_auth_action.triggered.connect(lambda: self.set_key_auth_visibility(False))
        view_menu.addAction(hide_key_auth_action)

        # Thêm action để hiện group xác thực key
        show_key_auth_action = QAction("Hiện xác thực key", self)
        show_key_auth_action.triggered.connect(lambda: self.set_key_auth_visibility(True))
        view_menu.addAction(show_key_auth_action)


        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Sẵn sàng")

    def _add_log_item(self, message: str, level=""):
        """Add item to output list with timestamp and color coding"""
        if hasattr(self, 'output_list') and self.output_list:
            current_time = QTime.currentTime().toString("HH:mm:ss")
            message = f"[{current_time}] {message}"
            item = QListWidgetItem(message)
            if level == "info":
                item.setForeground(QColor("#05df60"))
            elif level == "warning":
                item.setForeground(QColor("orange"))
            elif level == "error":
                item.setForeground(QColor("red"))
            elif level == "blue":
                item.setForeground(QColor("#4a5568"))
            self.output_list.addItem(item)
            self.output_list.scrollToBottom()

    def _setup_progress_system(self):
        """Setup progress tracking system"""
        self._progress_timer = QTimer(self)
        self._progress_timer.timeout.connect(self._update_progress)
        self._progress_value = 0
        self._paused = False

        # Initial button states
        self._update_progress_buttons(False)

    def _on_key_changed(self):
        """Handle key input change"""
        key = self.key_input.text().strip().upper()
        self.unlock_btn.setEnabled(len(key) > 0)

        # Auto unlock if correct key is entered
        if key == "HT":
            self._on_unlock_clicked()

    def _on_unlock_clicked(self):
        """Handle unlock button click"""
        key = self.key_input.text().strip().upper()

        if key == "HT":
            # Ẩn group xác thực key khi unlock thành công
            self._show_key_auth = False
            if hasattr(self, 'key_auth_group') and self.key_auth_group:
                self.key_auth_group.setVisible(self._show_key_auth)
            
            self._update_tab_buttons_visibility()

            # Show success message in log
            self._add_log_item(
                "✅ Xác thực thành công! Các chức năng đã được mở khóa.", level="info")
        else:
            # Wrong key
            self.key_status.setText("❌ Key không đúng")
            self.key_status.setStyleSheet("color: #F44336; font-weight: bold;")
            self.key_input.selectAll()
            self.key_input.setFocus()

            # Show error in log
            self._add_log_item(f"❌ Key không đúng: '{key}'", level="error")

    def toggle_key_auth_visibility(self):
        """Toggle hiển thị/ẩn group xác thực key"""
        self._show_key_auth = not self._show_key_auth
        if hasattr(self, 'key_auth_group') and self.key_auth_group:
            self.key_auth_group.setVisible(self._show_key_auth)
        
        # Log trạng thái
        status = "hiển thị" if self._show_key_auth else "ẩn"
        self._add_log_item(f"🔐 Group xác thực key: {status}", level="info")

    def set_key_auth_visibility(self, visible: bool):
        """Set hiển thị/ẩn group xác thực key"""
        self._show_key_auth = visible
        if hasattr(self, 'key_auth_group') and self.key_auth_group:
            self.key_auth_group.setVisible(self._show_key_auth)
        
        # Log trạng thái
        status = "hiển thị" if self._show_key_auth else "ẩn"
        self._add_log_item(f"🔐 Group xác thực key: {status}", level="info")



    def _update_tab_buttons_visibility(self):
        """Update visibility of buttons in all tabs"""
        # Update tab buttons if they exist
        if hasattr(self, '_all_tabs'):
            for tab in self._all_tabs:
                if hasattr(tab, 'btn_convert'):
                    tab.btn_convert.setEnabled(True)
                if hasattr(tab, 'btn_start'):
                    tab.btn_start.setEnabled(True)
                if hasattr(tab, 'btn_pause'):
                    tab.btn_pause.setEnabled(True)
                if hasattr(tab, 'btn_resume'):
                    tab.btn_resume.setEnabled(True)
                if hasattr(tab, 'btn_stop'):
                    tab.btn_stop.setEnabled(True)
                if hasattr(tab, 'btn_set_progress'):
                    tab.btn_set_progress.setEnabled(True)

        # Also enable main progress buttons if they exist
        if hasattr(self, 'btn_start'):
            self.btn_start.setEnabled(True)
        if hasattr(self, 'btn_pause'):
            self.btn_pause.setEnabled(True)
        if hasattr(self, 'btn_resume'):
            self.btn_resume.setEnabled(True)
        if hasattr(self, 'btn_stop'):
            self.btn_stop.setEnabled(True)

    def _setup_connections(self):
        """Setup signal connections"""
        # Progress button connections
        self.btn_start.clicked.connect(self.on_start)
        self.btn_pause.clicked.connect(self.on_pause)
        self.btn_resume.clicked.connect(self.on_resume)
        self.btn_stop.clicked.connect(self.on_stop)

        # Tab change connection - with progress visibility logic
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # History connections
        self._connect_history_signals()

    def _safe_layout_update(self, widget=None):
        """Safely update layouts to prevent UI breaking and QPainter errors"""
        try:
            # Defer the update to avoid paint conflicts
            QTimer.singleShot(10, lambda: self._do_layout_update(widget))
        except Exception as e:
            self._add_log_item(
                f"Layout update error: {str(e)}", level="warning")

    def _do_layout_update(self, widget=None):
        """Perform the actual layout update"""
        try:
            # Update specific widget or progress widget
            target_widget = widget or getattr(self, 'progress_widget', None)

            if target_widget and hasattr(target_widget, 'updateGeometry'):
                target_widget.updateGeometry()
                if hasattr(target_widget, 'layout') and target_widget.layout():
                    target_widget.layout().update()

            # Update main window - less aggressive approach
            if self.centralWidget() and hasattr(self.centralWidget(), 'updateGeometry'):
                self.centralWidget().updateGeometry()
                if hasattr(self.centralWidget(), 'layout') and self.centralWidget().layout():
                    self.centralWidget().layout().update()

        except Exception as e:
            self._add_log_item(
                f"Layout update execution error: {str(e)}", level="warning")

    def _hide_progress_bar(self):
        """Hide progress bar and related elements"""
        if hasattr(self, 'progress_bar') and self.progress_bar:
            self.progress_bar.setVisible(False)
        if hasattr(self, '_progress_title') and self._progress_title:
            self._progress_title.setVisible(False)

        # Hide progress control buttons
        buttons = [self.btn_start, self.btn_pause,
                   self.btn_resume, self.btn_stop]
        for btn in buttons:
            if btn:
                btn.setVisible(False)

        # Safe layout update
        self._safe_layout_update()

    def _show_progress_bar(self):
        """Show progress bar and related elements"""
        if hasattr(self, 'progress_bar') and self.progress_bar:
            self.progress_bar.setVisible(True)
        if hasattr(self, '_progress_title') and self._progress_title:
            self._progress_title.setVisible(True)

        # Show progress control buttons
        buttons = [self.btn_start, self.btn_pause,
                   self.btn_resume, self.btn_stop]
        for btn in buttons:
            if btn:
                btn.setVisible(True)

        # Safe layout update
        self._safe_layout_update()

    def _on_tab_changed(self, tab_index):
        """Handle tab change - manage progress visibility"""
        # Skip if setup not complete (prevents interference with initial state)
        if not getattr(self, '_setup_complete', False):
            return

        # Close history panels
        self._close_current_tab_history()

        # Handle progress section visibility based on tab
        if hasattr(self, 'progress_widget'):
            if tab_index == 2:  # Tab 3 (Simple) - Hide progress section completely
                self.progress_widget.setVisible(False)
                self.status.showMessage("Tab Simple - Đã ẩn progress section")
            else:  # Tab 1 (TTS) or Tab 2 (Convert) - Show progress section
                self.progress_widget.setVisible(True)

                # Reset toggle button states when switching to tab 2
                if tab_index == 1:  # Convert tab
                    # Ensure all elements are visible and buttons show correct text
                    if hasattr(self, 'progress_bar') and self.progress_bar:
                        self.progress_bar.setVisible(True)
                    if hasattr(self, '_progress_title') and self._progress_title:
                        self._progress_title.setVisible(True)
                    if hasattr(self, 'output_list') and self.output_list:
                        self.output_list.setVisible(True)

                    # Show progress control buttons
                    buttons = [self.btn_start, self.btn_pause,
                               self.btn_resume, self.btn_stop]
                    for btn in buttons:
                        if btn:
                            btn.setVisible(True)

                    # Reset Convert tab toggle buttons to default state
                    convert_tab = self._all_tabs[1]
                    if hasattr(convert_tab, 'btn_toggle_progress'):
                        convert_tab.btn_toggle_progress.setText(
                            "🔽 Ẩn Progress Bar")
                    if hasattr(convert_tab, 'btn_toggle_log'):
                        convert_tab.btn_toggle_log.setText("🔽 Ẩn Log")

                    self.status.showMessage(
                        "Tab Convert - Đã hiện progress section")
                # Tab 1 (TTS) - Hide progress bar initially, keep log visible
                elif tab_index == 0:
                    self._hide_progress_bar()
                    # Keep log visible
                    if hasattr(self, 'output_list') and self.output_list:
                        self.output_list.setVisible(True)
                    self.status.showMessage("Tab TTS - Progress bar ẩn, log hiển thị")

            # Safe layout update after tab change
            self._safe_layout_update()

    def _connect_history_signals(self):
        """Connect history show/hide signals from tabs"""
        for i, tab in enumerate(self._all_tabs):
            if hasattr(tab, 'history') and tab.history:
                tab.history.request_show_history.connect(
                    lambda checked=False, tab_index=i: self._open_tab_history(tab_index))
                tab.history.request_hide_history.connect(
                    lambda checked=False, tab_index=i: self._close_tab_history(tab_index))

    # Progress Control Methods
    def on_start(self):
        """Start progress"""
        self._reset_progress()
        self._progress_timer.start(30)  # Update every 30ms
        self.status.showMessage("Đang xử lý...")
        self._add_log_item("Bắt đầu xử lý", level="blue")
        self._update_progress_buttons(True)

    def on_pause(self):
        """Pause progress"""
        self._paused = True
        self.status.showMessage("Đã tạm dừng")
        self._add_log_item("Tạm dừng", level="warning")
        self._update_progress_buttons(True, paused=True)

    def on_resume(self):
        """Resume progress"""
        self._paused = False
        self.status.showMessage("Tiếp tục xử lý...")
        self._add_log_item("Tiếp tục", level="blue")
        self._update_progress_buttons(True, paused=False)

    def on_stop(self):
        """Stop progress"""
        self._progress_timer.stop()
        self.status.showMessage("Đã dừng")
        self._add_log_item("Dừng xử lý", level="warning")
        self._update_progress_buttons(False)

    def _update_progress(self):
        """Update progress value"""
        if self._paused:
            return

        self._progress_value += 1
        self.progress_bar.setValue(self._progress_value)

        # Log progress periodically
        if self._progress_value % 20 == 0:
            self._add_log_item(
                f"Tiến trình: {self._progress_value}%", level="blue")

        # Complete when reaching 100%
        if self._progress_value >= 100:
            self._progress_timer.stop()
            self.status.showMessage("Hoàn thành!")
            self._add_log_item("Hoàn thành xử lý", level="info")
            self._update_progress_buttons(False)

            # Processing completed
            pass

    def _update_progress_buttons(self, running: bool, paused: bool = False):
        """Update progress button states"""
        self.btn_start.setEnabled(not running)
        self.btn_pause.setEnabled(running and not paused)
        self.btn_resume.setEnabled(running and paused)
        self.btn_stop.setEnabled(running)

    def _reset_progress(self):
        """Reset progress to initial state"""
        self._progress_value = 0
        self.progress_bar.setValue(0)
        self._paused = False

    # History Management Methods

    def _get_current_tab(self) -> Optional[UIToolbarTab]:
        """Get current active tab"""
        try:
            return self.tabs.currentWidget()
        except Exception:
            return None

    def _get_current_panel(self) -> Optional[HistoryPanel]:
        """Get current tab's history panel"""
        tab = self._get_current_tab()
        if not tab or not hasattr(tab, 'history') or not tab.history:
            return None
        return tab.history.panel

    def _get_tab_index(self, target_tab) -> int:
        """Get index of a specific tab"""
        try:
            return self._all_tabs.index(target_tab)
        except (ValueError, AttributeError):
            return -1

    def _toggle_current_tab_history(self):
        """Toggle current tab's history panel"""
        panel = self._get_current_panel()
        if not panel:
            return

        if panel.isHidden():
            self._open_current_tab_history()
        else:
            self._close_current_tab_history()

    def _open_tab_history(self, tab_index: int):
        """Open specific tab's history panel"""
        if tab_index < 0 or tab_index >= len(self._all_tabs):
            return

        tab = self._all_tabs[tab_index]
        if not hasattr(tab, 'history') or not tab.history:
            return

        panel = tab.history.panel
        if not panel:
            return

        # Tab-specific logic
        tab_name = self.tabs.tabText(tab_index)
        print(f"Opening history for {tab_name} (tab {tab_index})")

        if tab_index == 0:  # TTS Tab
            self._add_log_item(
                f"[{datetime.now().strftime('%H:%M:%S')}] 🎤 Mở lịch sử TTS")
        elif tab_index == 1:  # Convert Tab
            self._add_log_item(
                f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Mở lịch sử Convert")
        elif tab_index == 2:  # Simple Tab
            self._add_log_item(
                f"[{datetime.now().strftime('%H:%M:%S')}] 📝 Mở lịch sử Simple")

        # Close other panels first
        for i, other_tab in enumerate(self._all_tabs):
            if (i != tab_index and hasattr(other_tab, 'history') and other_tab.history and
                    other_tab.history.panel != panel and not other_tab.history.panel.isHidden()):
                other_tab.history.panel.hide()

        # Show current panel
        panel.dock_right()
        panel.show_with_animation(self.width())

        # Update UI state
        self._set_tabs_enabled(False)
        self._show_overlay()

    def _close_tab_history(self, tab_index: int):
        """Close specific tab's history panel"""
        if tab_index < 0 or tab_index >= len(self._all_tabs):
            return

        tab = self._all_tabs[tab_index]
        if not hasattr(tab, 'history') or not tab.history:
            return

        panel = tab.history.panel
        if not panel or panel.isHidden():
            return

        # Tab-specific logic
        tab_name = self.tabs.tabText(tab_index)
        print(f"Closing history for {tab_name} (tab {tab_index})")

        if tab_index == 0:  # TTS Tab
            self._add_log_item(
                f"[{datetime.now().strftime('%H:%M:%S')}] 🎤 Đóng lịch sử TTS")
            # TTS specific cleanup
        elif tab_index == 1:  # Convert Tab
            self._add_log_item(
                f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Đóng lịch sử Convert")
            # Convert specific cleanup
        elif tab_index == 2:  # Simple Tab
            self._add_log_item(
                f"[{datetime.now().strftime('%H:%M:%S')}] 📝 Đóng lịch sử Simple")
            # Simple specific cleanup

        # Prevent recursion
        if hasattr(self, '_closing_history') and self._closing_history:
            return

        self._closing_history = True
        try:
            panel.hide()
            self._set_tabs_enabled(True)
            self._hide_overlay()
        finally:
            self._closing_history = False

    def _open_current_tab_history(self):
        """Open current tab's history panel"""
        panel = self._get_current_panel()
        if not panel:
            return

        # Close other panels first
        for tab in self._all_tabs:
            if (hasattr(tab, 'history') and tab.history and
                    tab.history.panel != panel and not tab.history.panel.isHidden()):
                tab.history.panel.hide()  # Direct hide to avoid recursion

        # Show current panel
        panel.dock_right()
        panel.show_with_animation(self.width())

        # Update UI state
        self._set_tabs_enabled(False)
        self._show_overlay()
        # Hide the floating close button, use only panel's X button
        # self.close_history_btn.show()
        # self._position_close_history_btn(panel)

    def _close_current_tab_history(self):
        """Close current tab's history panel"""
        # Prevent recursion
        if hasattr(self, '_closing_history') and self._closing_history:
            return

        self._closing_history = True
        try:
            panel = self._get_current_panel()

            # Close panel if open
            if panel and not panel.isHidden():
                # Close without triggering callback to prevent recursion
                panel.hide()  # Direct hide instead of close_panel()

            # Restore UI state
            self._set_tabs_enabled(True)
            # self.close_history_btn.hide()  # Already hidden
            self._hide_overlay()
        finally:
            self._closing_history = False

    def _set_tabs_enabled(self, enabled: bool):
        """Enable/disable tab switching but keep content interactive"""
        # Only disable tab bar, not the tab content
        self.tabs.tabBar().setEnabled(enabled)

        # Update progress buttons based on current state
        running = self._progress_timer.isActive()
        paused = self._paused
        self._update_progress_buttons(running, paused)

    def _show_overlay(self):
        """Show click-to-close overlay that doesn't block main content"""
        menubar_height = self.menuBar().height()
        panel = self._get_current_panel()

        if panel:
            # Overlay only covers the area not occupied by the panel
            overlay_width = self.width() - panel.width()
            self.overlay.setGeometry(
                0, menubar_height, overlay_width, self.height() - menubar_height)
        else:
            # Fallback: cover entire area
            self.overlay.setGeometry(
                0, menubar_height, self.width(), self.height() - menubar_height)

        self.overlay.show()
        self.overlay.raise_()

        # Ensure panel is on top
        if panel:
            panel.raise_()

    def _hide_overlay(self):
        """Hide overlay"""
        self.overlay.hide()

    def _position_close_history_btn(self, panel: HistoryPanel):
        """Position the floating close button"""
        if self.close_history_btn.isHidden():
            return

        menubar_height = self.menuBar().height()
        x = panel.x() - self.close_history_btn.width() - 8
        y = menubar_height + 8
        self.close_history_btn.move(x, y)

    # Toast Management

    def _center_on_screen(self):
        """Center the window on screen"""
        try:
            screen = QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
                x = (screen_geometry.width() - self.width()) // 2
                y = (screen_geometry.height() - self.height()) // 2
                self.move(x, y)
        except Exception:
            # Fallback: just use default position
            pass

    # Event Handlers
    def resizeEvent(self, event):
        """Handle window resize with safe UI updates"""
        try:
            super().resizeEvent(event)

            # Only reposition if not minimized and panel is visible
            if not self.isMinimized():
                panel = self._get_current_panel()
                if panel and not panel.isHidden():
                    # Use timer to defer repositioning and avoid paint conflicts
                    QTimer.singleShot(
                        50, lambda: self._safe_resize_panel(panel))
        except Exception as e:
            self._add_log_item(
                f"Resize event error: {str(e)}", level="warning")

    def _safe_resize_panel(self, panel):
        """Safely reposition panel after resize"""
        try:
            if panel and not panel.isHidden() and not self.isMinimized():
                panel.dock_right()
                self._show_overlay()
        except Exception as e:
            self._add_log_item(
                f"Panel resize error: {str(e)}", level="warning")

    def changeEvent(self, event):
        """Handle window state changes (minimize/restore)"""
        try:
            super().changeEvent(event)

            # Handle window state changes
            if event.type() == QEvent.Type.WindowStateChange:
                if self.isMinimized():
                    # Hide history panels when minimized to prevent paint issues
                    self._close_current_tab_history()
                elif self.windowState() == Qt.WindowState.WindowNoState:
                    # Window restored - defer UI updates to avoid paint conflicts
                    QTimer.singleShot(100, self._on_window_restored)

        except Exception as e:
            self._add_log_item(
                f"Window state change error: {str(e)}", level="warning")

    def _on_window_restored(self):
        """Handle window restore with safe UI updates"""
        try:
            # Force a safe layout update after restoration
            self._safe_layout_update()
        except Exception as e:
            self._add_log_item(
                f"Window restore error: {str(e)}", level="warning")

    def closeEvent(self, event):
        """Cleanup temporary parts when the application is closing."""
        try:
            cleaned = clean_all_temp_parts()
            # Log to output list if available
            self._add_log_item(f"🧹 Đã dọn {cleaned} thư mục tạm.", level="info")
        except Exception as e:
            try:
                self._add_log_item(f"⚠️ Lỗi khi dọn thư mục tạm: {str(e)}", level="warning")
            except Exception:
                pass
        finally:
            event.accept()


def main():
    """Main application entry point"""
    # Dọn dẹp tàn dư từ phiên trước (trong trường hợp app bị treo/crash)
    try:
        cleaned_on_start = clean_all_temp_parts()
        # Không log được ở đây vì chưa có window; chỉ đảm bảo sạch tàn dư
    except Exception:
        pass

    app = QApplication(sys.argv)
    window = MainWindow()
    screen = app.primaryScreen().geometry()
    screen_width = screen.width()

    # Lấy kích thước cửa sổ
    win_width = window.frameGeometry().width()
   # Đặt vị trí: giữa theo chiều ngang, y = 0
    x = (screen_width - win_width) // 2
    y = 0

    window.move(x, y)
    
    # Thiết lập cleanup khi app thoát (backup ngoài closeEvent)
    try:
        def _qt_about_to_quit():
            try:
                clean_all_temp_parts()
            except Exception:
                pass
        app.aboutToQuit.connect(_qt_about_to_quit)
    except Exception:
        pass

    # Cài đặt bắt exception toàn cục để dọn dẹp trước khi thoát bất thường
    try:
        def _global_excepthook(exctype, exc, tb):
            try:
                clean_all_temp_parts()
            except Exception:
                pass
            # Gọi excepthook mặc định
            sys.__excepthook__(exctype, exc, tb)
        sys.excepthook = _global_excepthook
    except Exception:
        pass

    # Bắt tín hiệu hệ thống (Ctrl+C, đóng tiến trình) để dọn dẹp
    try:
        def _signal_handler(signum, frame):
            try:
                clean_all_temp_parts()
            except Exception:
                pass
            # Kết thúc tiến trình ngay
            sys.exit(0)
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)
        if hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, _signal_handler)
    except Exception:
        pass

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
