from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QLabel, QProgressBar,
    QMainWindow, QTabWidget, QStatusBar, QLineEdit, QGroupBox,
    QListWidget, QListWidgetItem, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, QTime, QEvent, Signal
from PySide6.QtGui import QAction, QColor, QIcon
import sys
from datetime import datetime
from typing import Optional
from app.historyPanel import HistoryPanel
from app.core.config import AppConfig
from app.tabs.tts_tab import TTSTab
from app.uiToolbarTab import UIToolbarTab
from app.ui_setting import _init_addStyle, resource_path

import os


class ClickToCloseOverlay(QWidget):
    """Overlay to detect clicks outside of panels"""
    clicked_outside = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Widget)
        self.setStyleSheet("background: rgba(0,0,0,0.25);")
        self.hide()

    def mousePressEvent(self, event):
        """Handle mouse press to emit clicked_outside signal"""
        self.clicked_outside.emit()
        event.accept()


class MainWindow(QMainWindow):
    """Main application window with improved architecture"""

    def __init__(self):
        super().__init__()
        _init_addStyle(self)
        self._closing_history = False  # Prevent recursion in history close
        self._setup_complete = False  # Track setup completion
        self._setup_window()
        self._setup_ui()
        self._setup_progress_system()
        self._setup_connections()

        # Mark setup as complete
        self._setup_complete = True

        # Trigger initial tab state setup
        current_tab = self.tabs.currentIndex()
        self._on_tab_changed(current_tab)

    def _setup_window(self):
        """Setup main window properties"""
        self.setWindowTitle(AppConfig.WINDOW_TITLE)

        icon_path = resource_path(AppConfig.ICON_PATH)
        print(icon_path)
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # self.setMinimumSize(*AppConfig.MIN_WINDOW_SIZE)
        # self.resize(*AppConfig.DEFAULT_WINDOW_SIZE)  # Set default size
        # self.setStyleSheet(AppConfig.MAIN_STYLE)
        # _init_addStyle(self)
        # Center window on screen
        self._center_on_screen()

    def _setup_ui(self):
        """Setup the main UI components"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)  # Giảm khoảng cách giữa các widget
        main_layout.setContentsMargins(0, 0, 0, 0)  # Bỏ margin

        # Menu and status bar FIRST - so tabs can access status bar
        self._setup_menu_and_status()

        # Tab widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Create tabs - now status bar is available
        self.tab_tts = TTSTab(self)
        # self.tab_convert = ConvertTab(self)
        # self.tab_simple = SimpleTab(self)

        self._all_tabs = [self.tab_tts]

        # Add tabs to widget
        self.tabs.addTab(self.tab_tts, "Text to Speech")
        # self.tabs.addTab(self.tab_convert, "Convert")
        # self.tabs.addTab(self.tab_simple, "Simple")

        # main_layout.addStretch()
        # Progress and log section
        self._setup_progress_ui(main_layout)

        # Overlay and controls
        self._setup_overlay_controls()

        # Initialize button visibility based on lock state
        self._update_tab_buttons_visibility()

        # Ensure progress_widget is visible by default (app starts on Tab 0 - TTS)
        if hasattr(self, 'progress_widget') and self.progress_widget:
            self.progress_widget.setVisible(True)

        # Set initial state for Tab 1: hide progress bar only if locked, show log
        if not self._is_unlocked:
            self._hide_progress_bar()
        else:
            # Add log message for default unlocked state
            self._add_log_item(
                "🎉 Ứng dụng đã sẵn sàng - Tất cả chức năng đã được kích hoạt", level="info")

        if hasattr(self, 'output_list') and self.output_list:
            self.output_list.setVisible(True)

    def _setup_progress_ui(self, parent_layout: QVBoxLayout):
        """Setup progress UI section"""
        self.progress_widget = QWidget()  # Store reference for hide/show
        progress_layout = QVBoxLayout(self.progress_widget)
        progress_layout.addStretch()
        # Key Authentication Group Box
        self._setup_key_auth_group(progress_layout)

        # Title - store reference for toggle
        self._progress_title = QLabel("Tiến trình xử lý")
        self._progress_title.setStyleSheet(
            "font-size: 16px; font-weight: 600; margin-bottom: 10px;")
        progress_layout.addWidget(self._progress_title)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_bar)

        # Control buttons - responsive layout
        button_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶ Bắt đầu")
        self.btn_pause = QPushButton("⏸ Tạm dừng")
        self.btn_resume = QPushButton("⏯ Tiếp tục")
        self.btn_stop = QPushButton("⏹ Dừng")

        for btn in (self.btn_start, self.btn_pause, self.btn_resume, self.btn_stop):
            btn.setStyleSheet(AppConfig.BUTTON_STYLE)
            btn.setMinimumWidth(70)  # Minimum width for progress buttons
            btn.setMaximumWidth(100)  # Prevent buttons from being too wide
            button_layout.addWidget(btn)

        button_layout.addStretch()
        progress_layout.addStretch()
        progress_layout.addLayout(button_layout)

        # Log area
        self.output_list = QListWidget()
        # Make log area responsive - smaller for small screens
        # self.output_list.setMinimumHeight(60)
        # self.output_list.setMaximumHeight(80)
        self.output_list.setAlternatingRowColors(True)
        self.output_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        progress_layout.addWidget(self.output_list)

        parent_layout.addWidget(self.progress_widget)

        # Set size policy to prevent pushing down when hidden
        self.progress_widget.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.progress_bar.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.output_list.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Remove unnecessary addStretch() calls
        # progress_layout.addStretch()  # Removed to prevent pushing
        # button_layout.addStretch()  # Removed to prevent pushing

        # Add stretch only at the end if needed
        progress_layout.addStretch()

    def _setup_key_auth_group(self, parent_layout: QVBoxLayout):
        """Setup key authentication group box"""
        # Group box
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

        key_layout = QHBoxLayout(key_group)
        # Reduce margins for smaller screens
        key_layout.setContentsMargins(10, 5, 10, 5)

        # Key input - make more compact
        key_label = QLabel("Key:")  # Shortened label
        key_label.setStyleSheet("font-weight: normal; margin-right: 3px;")

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText(
            "Nhập key...")  # Shortened placeholder
        self.key_input.setMinimumWidth(80)   # Smaller minimum width
        # Smaller max width for better layout
        self.key_input.setMaximumWidth(150)
        self.key_input.setStyleSheet("""
            QLineEdit:focus {
                border: 2px solid #FFD700;
            }
        """)
        self.key_input.textChanged.connect(self._on_key_changed)

        # Unlock button
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

        # Status label - will be set to unlocked state later
        self.key_status = QLabel("🔒 Đã khóa")
        self.key_status.setStyleSheet("color: #FF6B35; font-weight: bold;")

        key_layout.addWidget(key_label)
        key_layout.addWidget(self.key_input)
        key_layout.addWidget(self.unlock_btn)
        key_layout.addWidget(self.key_status)
        key_layout.addStretch()

        parent_layout.addWidget(key_group)

        # Initialize unlocked state - default unlocked
        self._is_unlocked = True

        # Set UI to unlocked state
        self.key_input.setText("HT")
        self.key_input.setEnabled(False)
        self.key_status.setText("✅ Đã mở khóa")
        self.key_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
        self.unlock_btn.setText("✅ Đã mở")
        self.unlock_btn.setEnabled(False)

        # Note: _update_tab_buttons_visibility() will be called after UI setup is complete

        # Store reference to key_auth_group for toggling
        self.key_auth_group = key_group
        parent_layout.addWidget(self.key_auth_group)

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
        self.unlock_btn.setEnabled(len(key) > 0 and not self._is_unlocked)

        # Auto unlock if correct key is entered and not already unlocked
        if key == "HT" and not self._is_unlocked:
            self._on_unlock_clicked()

    def _on_unlock_clicked(self):
        """Handle unlock button click"""
        # Skip if already unlocked
        if self._is_unlocked:
            return

        key = self.key_input.text().strip().upper()

        if key == "HT":
            self._is_unlocked = True
            self.key_status.setText("✅ Đã mở khóa")
            self.key_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
            self.unlock_btn.setText("✅ Đã mở")
            self.unlock_btn.setEnabled(False)
            self.key_input.setEnabled(False)
            self._update_tab_buttons_visibility()

            # Show progress bar if currently in Tab 1 (TTS)
            current_tab_index = self.tabs.currentIndex()
            if current_tab_index == 0:  # Tab 1 (TTS)
                self._show_progress_bar()
                self.status.showMessage(
                    "Tab TTS - Đã unlock, progress bar hiển thị")

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

    def _update_tab_buttons_visibility(self):
        """Update visibility of buttons in all tabs based on unlock status"""
        # Update tab buttons if they exist
        if hasattr(self, '_all_tabs'):
            for tab in self._all_tabs:
                if hasattr(tab, 'btn_convert'):
                    tab.btn_convert.setEnabled(self._is_unlocked)
                if hasattr(tab, 'btn_start'):
                    tab.btn_start.setEnabled(self._is_unlocked)
                if hasattr(tab, 'btn_pause'):
                    tab.btn_pause.setEnabled(self._is_unlocked)
                if hasattr(tab, 'btn_resume'):
                    tab.btn_resume.setEnabled(self._is_unlocked)
                if hasattr(tab, 'btn_stop'):
                    tab.btn_stop.setEnabled(self._is_unlocked)
                if hasattr(tab, 'btn_set_progress'):
                    tab.btn_set_progress.setEnabled(self._is_unlocked)

        # Also hide main progress buttons if they exist
        if hasattr(self, 'btn_start'):
            self.btn_start.setEnabled(self._is_unlocked)
        if hasattr(self, 'btn_pause'):
            self.btn_pause.setEnabled(self._is_unlocked)
        if hasattr(self, 'btn_resume'):
            self.btn_resume.setEnabled(self._is_unlocked)
        if hasattr(self, 'btn_stop'):
            self.btn_stop.setEnabled(self._is_unlocked)

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
                # Tab 1 (TTS) - Hide progress bar only if locked, keep log visible
                elif tab_index == 0:
                    self._hide_progress_bar()
                    # if not self._is_unlocked:
                    #     self._hide_progress_bar()
                    #     self.status.showMessage("Tab TTS - Progress bar ẩn (chưa unlock), log hiển thị")
                    # else:
                    #     self.status.showMessage("Tab TTS - Progress bar hiện (đã unlock), log hiển thị")
                    # Keep log visible
                    if hasattr(self, 'output_list') and self.output_list:
                        self.output_list.setVisible(True)

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


def main():
    """Main application entry point"""
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
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
