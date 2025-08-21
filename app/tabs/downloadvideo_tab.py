from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QLabel, QTextEdit, QComboBox, QSpinBox,
    QMessageBox, QFileDialog, QCheckBox, QGroupBox, QLineEdit
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtCore import QThreadPool

from app.uiToolbarTab import UIToolbarTab

from app.core.config import AppConfig

from pathlib import Path

from app.workers.download_Worker import DownloadRunnable
import os
from datetime import datetime

import subprocess

class DownloadVideoTab(UIToolbarTab):
    """
    Tab Convert đơn giản để minh họa việc áp dụng HistoryPanel cho mỗi tab
    """

    def __init__(self, parent_main: QWidget) -> None:
        super().__init__(parent_main)
        self._initialize_state_variables()
       # self._setup_history()
        self._setup_ui()

    def _initialize_state_variables(self) -> None:

        # Concurrency state
        self.index = 1
        self.active_threads = []
        self.max_workers = 4
        self.running = 0
        self.stopped = False

        # Thread pool for QRunnable-based downloads
        self.thread_pool = QThreadPool.globalInstance()
        # Upper bound; actual concurrency is controlled by self.max_workers and self.running
        try:
            self.thread_pool.setMaxThreadCount(8)
        except Exception:
            pass






    def _force_stop_all_threads(self):
        """Force stop all tasks (QRunnable) by killing their subprocess if any"""
        for task in self.active_threads[:]:
            try:
                if hasattr(task, 'stop_flag'):
                    task.stop_flag = True
                if hasattr(task, 'process') and task.process:
                    try:
                        task.process.kill()
                        task.process.terminate()
                    except Exception:
                        pass
            except Exception:
                pass
        self.active_threads.clear()
        self.running = 0

    def _reset_download_state(self):
        """Reset download state to initial values"""
        self.stopped = False
        self.index = 1
        self.running = 0
        self.active_threads.clear()
        self.download_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self._reset_progress()

    def _safe_start_download(self):
        """Safe wrapper for start_download with error handling"""
        try:
            self.start_download()
        except Exception as e:
            print(f"Error starting download: {e}")
            self._add_log_item(f"❌ Lỗi khi bắt đầu tải: {e}", "error")
            self._reset_download_state()

    def _setup_history(self) -> None:
        """Enable per-tab history with its own panel and button"""
        # self.enable_history(
        #     hist_title="Lịch sử Download Video",
        #     item_factory=lambda text, ts, meta: TTSHistoryItem(text, ts, meta),
        # )

        # Đưa nút lịch sử vào thanh toolbar của tab
        if self.history:
            self.add_toolbar_widget(self.history.btn)

        # Không thêm demo; sẽ load khi mở panel

    def _setup_ui(self) -> None:
        """Create simple content for the Convert tab"""
        root_layout = self.layout()

        self._setup_header_section(root_layout)
        self._setup_content_section(root_layout)
        self._setup_bottom_section(root_layout)

    def _setup_header_section(self, root_layout: QVBoxLayout) -> None:

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(2, 2, 2, 2)

        row_layout = QVBoxLayout()

        # Job parameters row
        self._create_job_parameters_row(row_layout)
        self._create_control_buttons_row(row_layout)
        header_layout.addLayout(row_layout)
        root_layout.addLayout(header_layout)

    def _setup_content_section(self, root_layout: QVBoxLayout) -> None:

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        # Text input area
        self._group_box_downloadvideo(content_layout)
        self._create_text_input_area(content_layout)

        root_layout.addLayout(content_layout)

    def _setup_bottom_section(self, root_layout: QVBoxLayout) -> None:
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(2, 2, 2, 2)
        self._create_btn_downloadvideo(bottom_layout)
        root_layout.addLayout(bottom_layout)

    def _create_job_parameters_row(self, parent_layout: QVBoxLayout) -> None:
        """Create job parameters row"""
        row1_layout = QHBoxLayout()

        self.type_video = QComboBox()
        self.type_video.addItems(["Video", "Playlist"])
        self.type_video.setCurrentText("Video")

        self.sub_mode = QComboBox()
        self.sub_mode_list = [
            ("❌ Không tải xuống", ""),
            ("📄 Phụ đề có sẵn", "1"),
            ("🤖 Phụ đề tự động", "2"),
        ]
        for name, code in self.sub_mode_list:
            self.sub_mode.addItem(name, userData=code)

        for i in range(self.sub_mode.count()):
            if self.sub_mode.itemData(i) == "2":
                self.sub_mode.setCurrentIndex(i)
                break
        self.language_box = QComboBox()
        self.languages = [
            ("Tiếng Việt", "vi"),
            ("Tiếng Anh", "en"),
            ("Tiếng Nhật", "ja"),
            ("Tiếng Trung", "zh")
        ]
        for name, code in self.languages:
            self.language_box.addItem(name, userData=code)

        # Chọn ngôn ngữ theo mã code (VD: "ja")
        for i in range(self.language_box.count()):
            if self.language_box.itemData(i) == "vi":
                self.language_box.setCurrentIndex(i)
                break
        # Threads spinbox
        self.theard_video = QSpinBox()
        self.theard_video.setRange(1, 16)
        self.theard_video.setValue(AppConfig.DEFAULT_WORKERS_PLAYER)
        self.theard_video.setSuffix(" Thread")

        row1_layout.addWidget(self.type_video)
        row1_layout.addWidget(self.sub_mode)
        row1_layout.addWidget(self.language_box)
        row1_layout.addStretch()
        row1_layout.addWidget(self.theard_video)
        parent_layout.addLayout(row1_layout)

    def _create_control_buttons_row(self, parent_layout: QVBoxLayout) -> None:

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self.audio_only = QCheckBox("🎵 Tải âm thanh MP3")
        self.include_thumb = QCheckBox("🖼️ Tải ảnh thumbnail")
        self.subtitle_only = QCheckBox("📜 Chỉ tải phụ đề")

        row.addWidget(self.audio_only)
        row.addWidget(self.include_thumb)
        row.addWidget(self.subtitle_only)
        row.addStretch()
        parent_layout.addLayout(row)

    def _group_box_downloadvideo(self, content_layout: QVBoxLayout) -> None:
        """Create group box download video"""
        self.group_box = QGroupBox("📁 Tên thư mục tải (tuỳ chọn)")
        group_layout = QVBoxLayout()  # ✅ cần thêm dòng này

        # Tạo layout ngang cho input + button
        input_layout = QHBoxLayout()
        self.folder_name_input = QLineEdit()
        self.folder_name_input.setPlaceholderText(
            "Nhập tên thư mục hoặc chọn thư mục...")
        self.folder_name_input.setReadOnly(True)
        self.folder_name_input.setObjectName("folderNameInput")
        # ✅ Đường dẫn mặc định: thư mục hiện tại + "/Video"
        default_dir = Path.cwd() / "Video"
        self.folder_name_input.setText(str(default_dir))
        folder_button = QPushButton("Open",
                                    clicked=self.open_folder_dialog
                                    )
        folder_button.setObjectName("btn_style_1")
        # folder_button.clicked.connect(self.open_folder_dialog)

        # Thêm vào layout ngang
        input_layout.addWidget(self.folder_name_input)
        input_layout.addWidget(folder_button)

        # Thêm layout ngang vào layout chính của group box
        group_layout.addLayout(input_layout)

        # Set layout cho group box
        self.group_box.setLayout(group_layout)

        # Cuối cùng, thêm group box vào content layout
        content_layout.addWidget(self.group_box)

    def _create_text_input_area(self, content_layout: QVBoxLayout) -> None:
        """Create text input area"""
        self.url_inputdownloadvideo = QTextEdit(
            placeholderText="Nhập URL video hoặc văn bản tại đây..."
        )
        self.url_inputdownloadvideo.setPlainText(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.url_inputdownloadvideo.setMinimumHeight(
            200)  # Chiều cao tối thiểu 100px
        content_layout.addWidget(self.url_inputdownloadvideo, 2)

    def _create_btn_downloadvideo(self, content_layout: QVBoxLayout) -> None:
        """Create button download video"""

        self.download_button = QPushButton(
            "🚀 Bắt đầu tải",
            clicked=self._safe_start_download
        )
        self.download_button.setObjectName("btn_style_1")
        self.stop_button = QPushButton(
            "⏹️ Dừng Tải")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_download)
        self.stop_button.setObjectName("btn_style_1")
        content_layout.addWidget(self.download_button)
        content_layout.addWidget(self.stop_button)

    def open_folder_dialog(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Chọn thư mục")
        if folder_path:
            self.folder_name_input.setText(folder_path)

    def start_download(self):
        """Start download with proper error handling"""
        try:
            # Stop any existing downloads first
            if self.active_threads or self.running > 0:
                self.stop_download()
                # Use non-blocking approach to wait for threads to stop
                QTimer.singleShot(100, self._start_download_after_stop)
                return
            
            # If no threads running, start immediately
            self._start_download_immediate()
            
        except Exception as e:
            print(f"Error in start_download: {e}")
            self._add_log_item(f"❌ Lỗi khi bắt đầu tải: {e}", "error")
            self._force_reset_state()

    def _start_download_after_stop(self):
        """Start download after stopping existing threads"""
        try:
            # Check if threads are really stopped
            if self.active_threads or self.running > 0:
                # Schedule another check
                QTimer.singleShot(100, self._start_download_after_stop)
                return
            
            # All threads stopped, start download
            self._start_download_immediate()
            
        except Exception as e:
            print(f"Error in _start_download_after_stop: {e}")
            self._force_reset_state()

    def _start_download_immediate(self):
        """Start download immediately"""
        try:
            # Reset state
            self.stopped = False
            self.index = 1
            self.running = 0
            self.active_threads.clear()

            # Validate input
            urls = [u.strip() for u in self.url_inputdownloadvideo.toPlainText().splitlines() if u.strip()]
            if not urls:
                QMessageBox.warning(self, "Cảnh báo", "Bạn chưa nhập URL nào.")
                return

            self.urls = urls
            selected_code = self.language_box.currentData()

            # Hiển thị các tùy chọn khác
            options = []
            if self.audio_only.isChecked():
                options.append("🎵 Audio MP3")
            if self.include_thumb.isChecked():
                options.append("🖼️ Thumbnail")
            if self.subtitle_only.isChecked():
                options.append("📝 Chỉ phụ đề")

            if options:
                self._add_log_item(f"⚙️ Tùy chọn: {', '.join(options)}")

            # Folder name
            custom_folder = self.folder_name_input.text()
            if custom_folder:
                self._add_log_item(f"📁 Thư mục: {custom_folder}")

            selected_sub_mode = self.sub_mode.currentData()
            sub_mode_name = next(
                (name for name, code in self.sub_mode_list if code == selected_sub_mode), None)
            if selected_sub_mode:
                self._add_log_item(f"📜 Chế độ {sub_mode_name}")

            # Cap workers to number of URLs to avoid spawning unnecessary threads
            self.max_workers = min(int(self.theard_video.value()), len(self.urls))
            self._add_log_item(f"Đang chạy với {self.max_workers} thread")

            # Update UI
            self.download_button.setEnabled(False)
            self.stop_button.setEnabled(True)

            # Set flags
            self.custom_folder_name = custom_folder
            self.video_mode = self.type_video.currentText()
            self.audio_only_flag = self.audio_only.isChecked()
            self.sub_mode_flag = selected_sub_mode
            self.sub_lang_code_flag = selected_code
            self.sub_lang_name_flag = self.language_box.currentText()
            self.include_thumb_flag = self.include_thumb.isChecked()
            self.subtitle_only_flag = self.subtitle_only.isChecked()
            self.download_folder = self._create_download_folder()
            
            # Reset progress and start
            self._reset_progress()
            self._update_progress_title("Tiến trình xử lý")
            self._update_progress(15)
            self._add_log_item("🚀 Bắt đầu tải video...")
            self.download_next_batch()
            
        except Exception as e:
            print(f"Error in _start_download_immediate: {e}")
            self._add_log_item(f"❌ Lỗi khi bắt đầu tải: {e}", "error")
            self._force_reset_state()

    def stop_download(self):
        """Stop all downloads safely without blocking UI"""
        try:
            self.stopped = True
            
            # Update UI immediately
            self._add_log_item("⏹ Đang dừng các tiến trình tải...")
            # Tắt cả hai nút để tránh nhấp liên tục; sẽ bật lại khi dừng xong
            self.stop_button.setEnabled(False)
            self.download_button.setEnabled(False)
            
            # Use non-blocking approach to stop threads
            self._stop_threads_async()
            
        except Exception as e:
            print(f"Error in stop_download: {e}")
            # Force reset state if something goes wrong
            self._force_reset_state()

    def _stop_threads_async(self):
        """Stop threads asynchronously to prevent UI freezing"""
        try:
            # Set stop flags for all threads
            for thread in self.active_threads[:]:
                if hasattr(thread, 'stop_flag'):
                    thread.stop_flag = True
                if hasattr(thread, 'process') and thread.process:
                    try:
                        thread.process.kill()
                        thread.process.terminate()
                    except Exception as e:
                        print(f"Error killing process: {e}")
            
            # Schedule thread cleanup after a short delay
            QTimer.singleShot(500, self._cleanup_stopped_threads)
            self.kill_with_taskkill()
        except Exception as e:
            print(f"Error in _stop_threads_async: {e}")

    def _cleanup_stopped_threads(self):
        """With QRunnable, simply mark complete after clearing state."""
        self._complete_stop_process()

    def _complete_stop_process(self):
        """Complete the stop process after all threads are stopped"""
        try:
            # Clear any remaining threads
            self.active_threads.clear()
            self.running = 0
            
            # Update UI
            self._add_log_item("⏹ Đã dừng toàn bộ tiến trình.")
            self._reset_progress()
            # Chỉ khi dừng xong mới bật lại Start
            self.download_button.setEnabled(True)
                
        except Exception as e:
            print(f"Error in _complete_stop_process: {e}")

    def _force_reset_state(self):
        """Force reset state when normal reset fails"""
        try:
            self.stopped = True
            self.running = 0
            self.active_threads.clear()
            self.download_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self._reset_progress()
            
        except Exception as e:
            print(f"Error in force reset: {e}")

    def download_next_batch(self):
        while self.running < self.max_workers and self.index <= len(self.urls) and not self.stopped:
            url = self.urls[self.index - 1]
            worker_id = self.running + 1

            task = DownloadRunnable(
                url=url,
                video_index=self.index,
                total_urls=len(self.urls),
                worker_id=worker_id,
                video_mode=self.video_mode,
                audio_only=self.audio_only_flag,
                sub_mode=self.sub_mode_flag,
                sub_lang=self.sub_lang_code_flag,
                sub_lang_name=self.sub_lang_name_flag,
                include_thumb=self.include_thumb_flag,
                subtitle_only=self.subtitle_only_flag,
                custom_folder_name=self.download_folder
            )

            # Connect signals
            task.signals.message_signal.connect(self._add_log_item)
            task.signals.finished_signal.connect(self.handle_thread_done)
            task.signals.progress_signal.connect(self.update_progress)
            task.signals.error_signal.connect(self.error_thread)
            self.active_threads.append(task)
            self.thread_pool.start(task)
            self.running += 1
            self.index += 1

    def handle_thread_done(self, message: str = ""):
        """Handle when a thread finishes - no parameters needed"""
        self.running -= 1
           

        # Clean up active tasks list
        if self.active_threads:
            # Remove one finished task marker if present
            try:
                self.active_threads.pop(0)
            except Exception:
                pass
        
        # Schedule next downloads immediately if capacity available
        if not self.stopped and self.index <= len(self.urls):
            self.download_next_batch()
        elif self.running == 0:
            if self.stopped:
                self._add_log_item("⏹ Đã dừng toàn bộ tiến trình.")
            else:

                if message == "success":
                    self._add_log_item("✅ Tải xong tất cả video.")
                    self._add_log_item(
                        f"📂 Video được lưu tại: {self.download_folder}")
                elif message == "error":
                    self._add_log_item("❌ Không tải được video. Bỏ qua và tiếp tục.")
                elif message == "error_no_file":
                    self._add_log_item("❌ Không tìm thấy file đã download!")
                elif message == "error_copy_file":
                    self._add_log_item("❌ Lỗi khi copy file!")
                else:
                    self._add_log_item("❌ Lỗi khi tải video!")
                
                bCheckFolder = self._check_and_cleanup_empty_folders(self.download_folder)
                if bCheckFolder:
                    self._add_log_item("✅ Đã dọn dẹp thư mục rỗng.")

            self.download_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self._reset_progress()

    def error_thread(self, value):
        # Only log error; do not reset UI here because other threads may be running
        self._add_log_item(value, "error")
        

    def update_progress(self, value):
        self._update_progress(value)
        # self._reset_ui_after_download()

    def _create_download_folder(self):
        """Tạo thư mục download với cấu trúc đơn giản"""
        base_folder = "Video"
        os.makedirs(base_folder, exist_ok=True)

        if self.custom_folder_name:
            # Nếu có tên thư mục tùy chọn
            if os.path.isabs(self.custom_folder_name):
                # Đường dẫn đầy đủ
                date_folder = self.custom_folder_name
            else:
                # Tên thư mục - tạo trong thư mục Video
                date_folder = os.path.join(
                    base_folder, self.custom_folder_name)
        else:
            # Không có tên tùy chọn - tạo theo ngày
            date_str = datetime.now().strftime("%Y-%m-%d")
            date_folder = os.path.join(base_folder, date_str)

        # Tạo thư mục con với số thứ tự (01, 02, 03...)
        download_folder = self._create_numbered_subfolder(date_folder)

        os.makedirs(download_folder, exist_ok=True)
        return download_folder

    def _create_numbered_subfolder(self, date_folder):
        """Tạo thư mục con với số thứ tự (01, 02, 03...)"""
        if not os.path.exists(date_folder):
            os.makedirs(date_folder, exist_ok=True)

        # Tìm số thứ tự cao nhất trong thư mục ngày
        max_number = 0
        for item in os.listdir(date_folder):
            item_path = os.path.join(date_folder, item)
            if os.path.isdir(item_path) and item.isdigit():
                max_number = max(max_number, int(item))

        # Tạo thư mục con mới với số tiếp theo (format 2 chữ số)
        next_number = max_number + 1
        subfolder_name = f"{next_number:02d}"
        download_folder = os.path.join(date_folder, subfolder_name)

        return download_folder

    def _reset_progress(self) -> None:
        """Reset progress bar from main window"""
        try:
            if hasattr(self.parent_main, 'progress_bar'):
                # Ẩn progress bar khi reset về 0
                self.parent_main.progress_bar.setVisible(False)
                # Reset về 0
                self.parent_main.progress_bar.setValue(0)
        except Exception as e:
            print(f"[TTS PROGRESS ERROR] {e}")

    def _update_progress_title(self, title: str) -> None:
        """Update progress title from main window"""
        try:
            if hasattr(self.parent_main, '_progress_title'):
                # Chỉ hiện progress title khi có tiêu đề
                if title and title.strip():
                    self.parent_main._progress_title.setVisible(True)
                    self.parent_main._progress_title.setText(title)
                else:
                    self.parent_main._progress_title.setVisible(False)
        except Exception as e:
            print(f"[TTS PROGRESS TITLE ERROR] {e}")

    def _update_progress(self, value: int) -> None:
        """Update progress bar from main window"""
        try:
            if hasattr(self.parent_main, 'progress_bar'):
                # Chỉ hiện progress bar khi có giá trị
                if value > 0:
                    self.parent_main.progress_bar.setVisible(True)
                # Cập nhật giá trị
                self.parent_main.progress_bar.setValue(value)
        except Exception as e:
            print(f"[TTS PROGRESS ERROR] {e}")

    def _add_log_item(self, message: str, level: str = "") -> None:
        """Add log item to main window's output_list if available"""
        try:
            # Try to access main window's output_list
            if hasattr(self.parent_main, '_add_log_item'):
                self.parent_main._add_log_item(message, level)
        except Exception as e:
            # Fallback to print if logging fails
            print(f"[DOWNLOAD LOG ERROR] {e}")

    def cleanup_threads(self):
        """Clean up all threads when tab is closed"""
        try:
            self.stopped = True
            
            # Stop cleanup timer
            if hasattr(self, 'cleanup_timer'):
                self.cleanup_timer.stop()

            # Stop log timer
            if hasattr(self, '_log_timer'):
                self._log_timer.stop()
            
            # Stop all active threads safely
            threads_to_cleanup = self.active_threads[:]
            for thread in threads_to_cleanup:
                try:
                    # Set stop flag
                    if hasattr(thread, 'stop_flag'):
                        thread.stop_flag = True
                    
                    # Kill subprocess if exists
                    if hasattr(thread, 'process') and thread.process:
                        try:
                            thread.process.kill()
                            thread.process.terminate()
                        except Exception as e:
                            print(f"Error killing process during cleanup: {e}")
                    
                    # Stop thread
                    if thread.isRunning():
                        thread.quit()
                        if not thread.wait(3000):  # Wait up to 3 seconds
                            thread.terminate()
                            thread.wait(1000)
                    
                    # Delete thread object
                    thread.deleteLater()
                    
                except Exception as e:
                    print(f"Error cleaning up thread during tab close: {e}")
                    try:
                        thread.deleteLater()
                    except:
                        pass
            
            # Clear state
            self.active_threads.clear()
            self.running = 0
            
        except Exception as e:
            print(f"Error in cleanup_threads: {e}")
            # Force clear everything
            try:
                self.active_threads.clear()
                self.running = 0

            except:
                pass
    
    def _check_and_cleanup_empty_folders(self, folder_path: str) -> bool:
        """
        Kiểm tra thư mục có file nào không, nếu không có thì xóa thư mục
        Returns: True nếu thư mục được xóa, False nếu thư mục còn file
        """
        try:
            if not os.path.exists(folder_path):
                return False
            
            # Kiểm tra xem thư mục có file nào không
            items = os.listdir(folder_path)
            
            # Lọc ra các file (không phải thư mục con)
            files = [item for item in items if os.path.isfile(os.path.join(folder_path, item))]
            
            if not files:
                # Không có file nào, xóa thư mục
                try:
                    os.rmdir(folder_path)  # Xóa thư mục rỗng
                    print(f"Đã xóa thư mục rỗng: {folder_path}")
                    return True
                except OSError as e:
                    # Nếu không thể xóa bằng rmdir (có thể có thư mục con rỗng)
                    try:
                        import shutil
                        shutil.rmtree(folder_path)  # Xóa đệ quy
                        print(f"Đã xóa thư mục và thư mục con: {folder_path}")
                        return True
                    except Exception as e2:
                        print(f"Không thể xóa thư mục {folder_path}: {e2}")
                        return False
            else:
                print(f"Thư mục {folder_path} còn {len(files)} file, không xóa")
                return False
                
        except Exception as e:
            print(f"Lỗi khi kiểm tra thư mục {folder_path}: {e}")
            return False

    def _cleanup_empty_download_folders(self, base_folder):
        """
        Dọn dẹp các thư mục download rỗng
        """
        try:
            if not os.path.exists(base_folder):
                return
            
            # Duyệt qua các thư mục ngày
            for date_item in os.listdir(base_folder):
                date_path = os.path.join(base_folder, date_item)
                if os.path.isdir(date_path):
                    # Duyệt qua các thư mục con số
                    for sub_item in os.listdir(date_path):
                        sub_path = os.path.join(date_path, sub_item)
                        if os.path.isdir(sub_path) and sub_item.isdigit():
                            # Kiểm tra và xóa thư mục rỗng
                            self._check_and_cleanup_empty_folders(sub_path)
                    
                    # Kiểm tra thư mục ngày có còn thư mục con nào không
                    remaining_subdirs = [item for item in os.listdir(date_path) 
                                       if os.path.isdir(os.path.join(date_path, item))]
                    if not remaining_subdirs:
                        # Không còn thư mục con nào, xóa thư mục ngày
                        try:
                            os.rmdir(date_path)
                            print(f"Đã xóa thư mục ngày rỗng: {date_path}")
                        except Exception as e:
                            print(f"Không thể xóa thư mục ngày {date_path}: {e}")
                            
        except Exception as e:
            print(f"Lỗi khi dọn dẹp thư mục download: {e}")

    def closeEvent(self, event):
        """Handle tab close event"""
        self.cleanup_threads()
        super().closeEvent(event)
    
    def kill_with_taskkill():
        for name in ("yt-dlp.exe", "ffmpeg.exe"):
            try:
                subprocess.run(
                    ["taskkill", "/IM", name, "/T", "/F"],
                    capture_output=True, text=True, check=False
                )
            except Exception:
                pass