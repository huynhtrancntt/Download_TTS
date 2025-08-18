# SegmentManager - Quản lý Audio Segments

## Tổng quan

`SegmentManager` là một class được tách ra từ `TTSTab` để quản lý tất cả logic liên quan đến audio segments. Việc tách này giúp code dễ maintain và test hơn.

## Chức năng chính

### 1. Quản lý Segments
- Thêm/xóa segments
- Cập nhật thời lượng
- Lấy thông tin segments
- Thống kê segments

### 2. Xử lý Audio Files
- Thêm audio files (MP3, WAV, etc.)
- Thêm video files (tạo 3s audio placeholder)
- Tạo khoảng nghỉ (gap segments)
- Cắt segments thành nhiều phần

### 3. Hiển thị UI
- Format text hiển thị segments
- Cập nhật list widget
- Hiển thị thông tin thời gian và kích thước file

## Cách sử dụng

### Khởi tạo
```python
from app.core.segment_manager import SegmentManager

# Tạo instance
segment_manager = SegmentManager()

# Set UI components (sử dụng QListWidget với custom row widget)
segment_manager.set_ui_components(list_widget, audio_player)
```

### Hiển thị 3 cột
SegmentManager sử dụng `QListWidget` với custom `ListRow` widget để hiển thị segments theo 3 cột:

- **Cột 1 (Bên trái)**: Tên segment và thời lượng - Ví dụ: `004. part_0004.mp3 — 00:15`
- **Cột 2 (Giữa)**: Thời gian tích lũy - Ví dụ: `00:48/03:14`  
- **Cột 3 (Bên phải)**: Kích thước file - Ví dụ: `93.1KB`

Mỗi row sử dụng `ListRow` class với `QGridLayout` và `QSizePolicy` để tạo giao diện responsive:
- Cột giữa tự động giãn nở để chiếm hết không gian còn lại
- Hai cột bên cạnh có kích thước tối thiểu
- Căn chỉnh text: trái - giữa - phải
- **Styling Terminal Theme**: 
  - Background đen sâu (#0a0a0a) với border xanh lá (#00ff00)
  - Font monospaced (Consolas, Monaco, Courier New) giống terminal
  - Text màu xanh lá tươi (#00ff00) với text-shadow phát sáng
  - Background labels tối (#1a1a1a) để tạo contrast

### Sử dụng trực tiếp
```python
# Thêm custom row
segment_manager.add_custom_row("03", "nam 3", "96 kb")

# Lấy dữ liệu từ row
row_widget = segment_manager.list_widget.itemWidget(item)
left, center, right = row_widget.get_data()
```

### Thêm segments
```python
# Thêm audio file
success = segment_manager.add_audio_file("path/to/audio.mp3")

# Thêm video file
success = segment_manager.add_video_file("path/to/video.mp4")

# Thêm khoảng nghỉ
success = segment_manager.add_gap_segment(3000, 0, "sau")  # 3s gap
```

### Quản lý segments
```python
# Lấy segments hợp lệ
valid_paths, valid_durations = segment_manager.get_valid_segments()

# Xóa segment
removed_path, removed_duration = segment_manager.remove_segment(0)

# Xóa tất cả
segment_manager.clear_segments()

# Sắp xếp lại
new_order = [2, 0, 1]  # Thay đổi thứ tự
success = segment_manager.reorder_segments(new_order)
```

### Thông tin và thống kê
```python
# Lấy thông tin segment cụ thể
segment_info = segment_manager.get_segment_info(0)

# Lấy thống kê tổng quan
stats = segment_manager.get_segments_statistics()
print(f"Tổng segments: {stats['total_segments']}")
print(f"Tổng thời lượng: {stats['total_duration']}ms")
```

## Signals

SegmentManager phát ra các signals khi có thay đổi:

```python
# Kết nối signals
segment_manager.segments_changed.connect(self.on_segments_changed)
segment_manager.segment_added.connect(self.on_segment_added)
segment_manager.segment_removed.connect(self.on_segment_removed)
segment_manager.segment_reordered.connect(self.on_segment_reordered)
```

## Lợi ích của việc tách code

1. **Separation of Concerns**: Logic quản lý segments tách biệt khỏi UI
2. **Reusability**: Có thể sử dụng SegmentManager ở các tab khác
3. **Testability**: Dễ dàng viết unit tests cho SegmentManager
4. **Maintainability**: Code ngắn gọn, dễ đọc và sửa đổi
5. **Modularity**: Có thể thay thế hoặc cải tiến SegmentManager độc lập

## Migration từ TTSTab

Tất cả các method liên quan đến segments đã được chuyển sang SegmentManager:

- `_update_segments_display()` → `segment_manager._update_display()`
- `_format_segment_display_text()` → `segment_manager._format_segment_display_text()`
- `_get_file_size()` → `segment_manager._get_file_size()`
- Logic thêm/xóa/sắp xếp segments → Các method tương ứng trong SegmentManager

TTSTab giờ chỉ còn UI và điều phối, không còn chứa logic xử lý segments.
