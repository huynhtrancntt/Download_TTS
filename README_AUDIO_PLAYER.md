# 🎵 AudioPlayer Class - Hướng dẫn sử dụng

## 📋 Tổng quan

`AudioPlayer` là một class tái sử dụng được thiết kế để phát âm thanh trong các ứng dụng PySide6. Class này cung cấp giao diện hoàn chỉnh với các chức năng cơ bản như phát, dừng, seek, và loop audio.

## ✨ Tính năng chính

- **🎮 Điều khiển cơ bản**: Play, Pause, Stop, Next, Previous
- **🎯 Seek chính xác**: Click vào slider để seek đến vị trí bất kỳ
- **🔄 Loop tự động**: Tự động phát lại từ đầu khi kết thúc
- **📊 Timeline**: Hiển thị vị trí hiện tại và tổng thời lượng
- **🎵 Multi-segment**: Hỗ trợ phát nhiều file audio liên tiếp
- **📡 Signals**: Phát ra các tín hiệu để tích hợp với ứng dụng chính

## 🚀 Cách sử dụng cơ bản

### 1. Import và khởi tạo

```python
from app.core.audio_player import AudioPlayer

# Tạo instance
audio_player = AudioPlayer()

# Thêm vào layout
layout.addWidget(audio_player)
```

### 2. Thêm audio segments

```python
# Danh sách đường dẫn file
audio_files = ["file1.mp3", "file2.mp3", "file3.mp3"]

# Danh sách thời lượng tương ứng (ms)
durations = [30000, 45000, 60000]  # 30s, 45s, 60s

# Thêm vào player
audio_player.add_segments(audio_files, durations)
```

### 3. Điều khiển phát

```python
# Bắt đầu phát
audio_player.play()

# Tạm dừng
audio_player.pause()

# Dừng hoàn toàn
audio_player.stop()

# Seek đến vị trí cụ thể (ms)
audio_player.seek_to(30000)  # 30 giây
```

### 4. Lắng nghe sự kiện

```python
# Kết nối signals
audio_player.position_changed.connect(self.on_position_changed)
audio_player.segment_changed.connect(self.on_segment_changed)
audio_player.playback_state_changed.connect(self.on_playback_state_changed)

# Callback functions
def on_position_changed(self, position_ms):
    print(f"Vị trí hiện tại: {position_ms}ms")

def on_segment_changed(self, segment_index):
    print(f"Đang phát segment: {segment_index}")

def on_playback_state_changed(self, is_playing):
    print(f"Trạng thái: {'Đang phát' if is_playing else 'Đã dừng'}")
```

## 🔧 API Reference

### Public Methods

| Method | Mô tả | Parameters | Returns |
|--------|-------|------------|---------|
| `add_segments(paths, durations)` | Thêm danh sách segments | `paths: List[str]`, `durations: List[int]` | None |
| `clear_segments()` | Xóa tất cả segments | None | None |
| `play()` | Bắt đầu phát | None | None |
| `pause()` | Tạm dừng | None | None |
| `stop()` | Dừng hoàn toàn | None | None |
| `seek_to(global_ms)` | Seek đến vị trí | `global_ms: int` | None |
| `get_current_position()` | Lấy vị trí hiện tại | None | `int` (ms) |
| `get_total_duration()` | Lấy tổng thời lượng | None | `int` (ms) |
| `is_audio_playing()` | Kiểm tra trạng thái phát | None | `bool` |

### Signals

| Signal | Mô tả | Parameters |
|--------|-------|------------|
| `position_changed` | Vị trí thay đổi | `position_ms: int` |
| `duration_changed` | Thời lượng thay đổi | `duration_ms: int` |
| `playback_state_changed` | Trạng thái phát thay đổi | `is_playing: bool` |
| `segment_changed` | Segment thay đổi | `segment_index: int` |

## 📱 Tích hợp vào ứng dụng

### Ví dụ 1: Tích hợp vào TTS Tab

```python
from app.core.audio_player import AudioPlayer

class TTSTab(UIToolbarTab):
    def __init__(self, parent_main):
        super().__init__(parent_main)
        
        # Thay thế player cũ bằng AudioPlayer
        self.audio_player = AudioPlayer()
        
        # Thêm vào layout
        self.layout().addWidget(self.audio_player)
        
        # Kết nối với TTS system
        self.audio_player.segment_changed.connect(self.on_segment_changed)
    
    def on_segment_ready(self, path, duration_ms, index):
        # Cập nhật segments cho AudioPlayer
        self.audio_player.add_segments([path], [duration_ms])
```

### Ví dụ 2: Tạo ứng dụng đơn giản

```python
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from app.core.audio_player import AudioPlayer

class SimpleAudioApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Audio Player")
        
        # Tạo AudioPlayer
        self.audio_player = AudioPlayer()
        
        # Thêm vào giao diện
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self.audio_player)
        
        # Thêm demo audio
        self.audio_player.add_segments(
            ["demo1.mp3", "demo2.mp3"], 
            [30000, 45000]
        )

# Chạy ứng dụng
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimpleAudioApp()
    window.show()
    app.exec()
```

## 🎨 Tùy chỉnh giao diện

### Thay đổi style

```python
# Tùy chỉnh button style
audio_player.btn_playpause.setStyleSheet("""
    QPushButton {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 10px;
        border-radius: 5px;
    }
    QPushButton:hover {
        background-color: #45a049;
    }
""")

# Tùy chỉnh slider
audio_player.slider.setStyleSheet("""
    QSlider::groove:horizontal {
        border: 1px solid #bbb;
        background: white;
        height: 10px;
        border-radius: 5px;
    }
    QSlider::handle:horizontal {
        background: #4CAF50;
        border: 1px solid #5c6b7a;
        width: 18px;
        margin: -2px 0;
        border-radius: 9px;
    }
""")
```

### Ẩn/hiện các thành phần

```python
# Ẩn button next/prev
audio_player.btn_next.hide()
audio_player.btn_prev.hide()

# Ẩn checkbox loop
audio_player.chk_loop.hide()

# Ẩn status label
audio_player.lbl_status.hide()
```

## 🔍 Debug và Troubleshooting

### Kiểm tra trạng thái

```python
# In thông tin debug
print(f"Segments: {len(audio_player.segment_paths)}")
print(f"Current index: {audio_player.current_index}")
print(f"Total duration: {audio_player.total_known_ms}ms")
print(f"Is playing: {audio_player.is_playing}")
```

### Xử lý lỗi

```python
# Kết nối signal lỗi
audio_player.player.errorOccurred.connect(self.on_audio_error)

def on_audio_error(self, error):
    print(f"Audio error: {error}")
    print(f"Error string: {audio_player.player.errorString()}")
```

## 📁 Cấu trúc file

```
app/core/
├── audio_player.py          # Class AudioPlayer chính
├── audio_player_demo.py     # Demo ứng dụng
└── README_AUDIO_PLAYER.md  # Hướng dẫn này
```

## 🎯 Lợi ích của việc tái sử dụng

1. **🔄 Tái sử dụng**: Có thể dùng trong nhiều ứng dụng khác nhau
2. **🧹 Code sạch**: Tách biệt logic audio khỏi logic nghiệp vụ
3. **🔧 Dễ bảo trì**: Sửa lỗi và cải tiến ở một nơi duy nhất
4. **📱 Nhất quán**: Giao diện và hành vi giống nhau ở mọi nơi
5. **🧪 Dễ test**: Có thể test riêng biệt class AudioPlayer

## 🚀 Tương lai

Class `AudioPlayer` có thể được mở rộng thêm các tính năng:

- **🎛️ Equalizer**: Điều chỉnh âm thanh
- **📊 Visualization**: Hiển thị waveform
- **🎵 Playlist**: Quản lý danh sách phát
- **🌐 Streaming**: Hỗ trợ phát audio từ internet
- **💾 Cache**: Lưu cache audio để phát nhanh hơn

## 📞 Hỗ trợ

Nếu gặp vấn đề hoặc cần hỗ trợ, hãy:

1. Kiểm tra file demo `audio_player_demo.py`
2. Xem log lỗi trong console
3. Kiểm tra các signals và connections
4. Đảm bảo file audio có định dạng được hỗ trợ
