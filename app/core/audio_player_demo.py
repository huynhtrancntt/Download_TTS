# -*- coding: utf-8 -*-
"""
Demo sử dụng AudioPlayer Class
Minh họa cách tái sử dụng class AudioPlayer trong các ứng dụng khác nhau
"""

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QFileDialog, QMessageBox
from PySide6.QtCore import Qt
import sys
import os

from app.core.audio_player import AudioPlayer
from app.utils.helps import get_mp3_duration_ms


class AudioPlayerDemo(QMainWindow):
    """
    Demo ứng dụng sử dụng AudioPlayer
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Player Demo")
        self.setGeometry(100, 100, 800, 600)
        
        # Khởi tạo AudioPlayer
        self.audio_player = AudioPlayer()
        
        # Kết nối signals
        self.audio_player.position_changed.connect(self.on_position_changed)
        self.audio_player.segment_changed.connect(self.on_segment_changed)
        self.audio_player.playback_state_changed.connect(self.on_playback_state_changed)
        
        # Thiết lập giao diện
        self.setup_ui()
        
        # Danh sách segments demo
        self.demo_segments = []
        self.demo_durations = []

    def setup_ui(self):
        """Thiết lập giao diện demo"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("🎵 Audio Player Demo")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Class AudioPlayer có thể tái sử dụng cho nhiều ứng dụng khác nhau")
        desc.setStyleSheet("font-size: 14px; color: #666; margin: 5px;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        # Control buttons
        controls_layout = QVBoxLayout()
        
        # Load demo audio
        self.btn_load_demo = QPushButton("🎵 Tải Demo Audio")
        self.btn_load_demo.clicked.connect(self.load_demo_audio)
        controls_layout.addWidget(self.btn_load_demo)
        
        # Load custom audio
        self.btn_load_custom = QPushButton("📁 Tải Audio Tùy chọn")
        self.btn_load_custom.clicked.connect(self.load_custom_audio)
        controls_layout.addWidget(self.btn_load_custom)
        
        # Clear audio
        self.btn_clear = QPushButton("🗑️ Xóa Audio")
        self.btn_clear.clicked.connect(self.clear_audio)
        controls_layout.addWidget(self.btn_clear)
        
        layout.addLayout(controls_layout)
        
        # Thêm AudioPlayer vào giao diện
        layout.addWidget(self.audio_player)
        
        # Status info
        self.lbl_status = QLabel("Trạng thái: Sẵn sàng")
        self.lbl_status.setStyleSheet("font-size: 12px; color: #888; padding: 5px;")
        layout.addWidget(self.lbl_status)
        
        # Segment info
        self.lbl_segment = QLabel("Segment: Chưa có")
        self.lbl_segment.setStyleSheet("font-size: 12px; color: #888; padding: 5px;")
        layout.addWidget(self.lbl_segment)
        
        # Position info
        self.lbl_position = QLabel("Vị trí: 00:00 / 00:00")
        self.lbl_position.setStyleSheet("font-size: 12px; color: #888; padding: 5px;")
        layout.addWidget(self.lbl_position)

    def load_demo_audio(self):
        """Tải demo audio có sẵn"""
        # Tạo một số file demo (có thể thay thế bằng file thật)
        demo_files = [
            "demo_audio_1.mp3",
            "demo_audio_2.mp3", 
            "demo_audio_3.mp3"
        ]
        
        # Giả lập durations (trong thực tế sẽ đọc từ file)
        demo_durations = [30000, 45000, 60000]  # 30s, 45s, 60s
        
        # Kiểm tra xem có file thật không
        real_files = []
        real_durations = []
        
        for i, filename in enumerate(demo_files):
            # Tìm trong thư mục output hoặc images
            possible_paths = [
                f"output/{filename}",
                f"images/{filename}",
                filename
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    try:
                        duration = get_mp3_duration_ms(path)
                        if duration > 0:
                            real_files.append(path)
                            real_durations.append(duration)
                            break
                    except:
                        continue
        
        if real_files:
            # Sử dụng file thật
            self.audio_player.add_segments(real_files, real_durations)
            self.demo_segments = real_files.copy()
            self.demo_durations = real_durations.copy()
            self.lbl_status.setText(f"✅ Đã tải {len(real_files)} file audio thật")
        else:
            # Sử dụng demo giả
            self.audio_player.add_segments(demo_files, demo_durations)
            self.demo_segments = demo_files.copy()
            self.demo_durations = demo_durations.copy()
            self.lbl_status.setText("⚠️ Sử dụng demo giả (không có file thật)")

    def load_custom_audio(self):
        """Tải audio tùy chọn từ người dùng"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Chọn file audio", "", 
            "Audio Files (*.mp3 *.wav *.m4a *.ogg *.flac);;All Files (*)"
        )
        
        if not files:
            return
        
        # Đọc duration của từng file
        valid_files = []
        valid_durations = []
        
        for file_path in files:
            try:
                duration = get_mp3_duration_ms(file_path)
                if duration > 0:
                    valid_files.append(file_path)
                    valid_durations.append(duration)
                else:
                    QMessageBox.warning(self, "Lỗi", f"Không thể đọc được thời lượng của: {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.warning(self, "Lỗi", f"Không thể đọc file: {os.path.basename(file_path)}\nLỗi: {e}")
        
        if valid_files:
            self.audio_player.add_segments(valid_files, valid_durations)
            self.demo_segments = valid_files.copy()
            self.demo_durations = valid_durations.copy()
            self.lbl_status.setText(f"✅ Đã tải {len(valid_files)} file audio tùy chọn")
        else:
            QMessageBox.warning(self, "Lỗi", "Không có file audio hợp lệ nào được tải")

    def clear_audio(self):
        """Xóa tất cả audio"""
        self.audio_player.clear_segments()
        self.demo_segments.clear()
        self.demo_durations.clear()
        self.lbl_status.setText("Trạng thái: Đã xóa audio")

    def on_position_changed(self, position_ms):
        """Callback khi vị trí thay đổi"""
        from app.utils.helps import ms_to_mmss
        total_ms = self.audio_player.get_total_duration()
        self.lbl_position.setText(f"Vị trí: {ms_to_mmss(position_ms)} / {ms_to_mmss(total_ms)}")

    def on_segment_changed(self, segment_index):
        """Callback khi segment thay đổi"""
        if segment_index >= 0 and segment_index < len(self.demo_segments):
            filename = os.path.basename(self.demo_segments[segment_index])
            self.lbl_segment.setText(f"Segment: {segment_index + 1} - {filename}")
        else:
            self.lbl_segment.setText("Segment: Không xác định")

    def on_playback_state_changed(self, is_playing):
        """Callback khi trạng thái playback thay đổi"""
        if is_playing:
            self.lbl_status.setText("Trạng thái: Đang phát")
        else:
            self.lbl_status.setText("Trạng thái: Đã dừng")


def main():
    """Hàm main để chạy demo"""
    app = QApplication(sys.argv)
    
    # Tạo cửa sổ demo
    demo_window = AudioPlayerDemo()
    demo_window.show()
    
    # Chạy ứng dụng
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
