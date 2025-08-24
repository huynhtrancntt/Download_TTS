# Language Manager

## Tổng quan

`LanguageManager` là một class được thiết kế để quản lý tất cả logic liên quan đến ngôn ngữ và voices cho TTS (Text-to-Speech). Class này giúp tổ chức code tốt hơn và dễ bảo trì hơn.

## Cấu trúc

```
app/core/
├── language_manager.py      # File chính chứa LanguageManager
├── voices_data.py          # Dữ liệu voices (được import)
└── __init__.py             # Export LanguageManager
```

## Cách sử dụng

### 1. Import

```python
from app.core.language_manager import language_manager
# Hoặc
from app.core import language_manager
```

### 2. Các phương thức chính

#### Quản lý ngôn ngữ

```python
# Lấy danh sách tất cả ngôn ngữ có sẵn
languages = language_manager.get_available_languages()
# Kết quả: [("Tự phát hiện", "auto"), ("Tiếng Việt", "vi"), ("Tiếng Anh", "en"), ...]

# Lấy tên hiển thị của ngôn ngữ
display_name = language_manager.get_language_display_name("vi")
# Kết quả: "Tiếng Việt"

# Kiểm tra ngôn ngữ có được hỗ trợ không
is_supported = language_manager.is_language_supported("vi")
# Kết quả: True

# Lấy tổng số ngôn ngữ
count = language_manager.get_language_count()
# Kết quả: 50+
```

#### Quản lý voices

```python
# Lấy tất cả voices của một ngôn ngữ
voices = language_manager.get_voices_for_language("vi")
# Kết quả: [{"gender": "Nam", "shortname": "vi-VN-NamMinhNeural", "label": "Nam - NamMinh (vi-VN-NamMinhNeural)"}, ...]

# Lấy voice theo giới tính
male_voice = language_manager.get_male_voice("vi")
# Kết quả: "vi-VN-NamMinhNeural"

female_voice = language_manager.get_female_voice("vi")
# Kết quả: "vi-VN-HoaiMyNeural"

# Lấy voice mặc định
default_voice = language_manager.get_default_voice_for_language("vi")
# Kết quả: "vi-VN-NamMinhNeural"

# Lấy voices theo giới tính
male_voices = language_manager.get_voices_by_gender("vi", "Nam")
female_voices = language_manager.get_voices_by_gender("vi", "Nữ")
all_voices = language_manager.get_voices_by_gender("vi")
```

#### Phát hiện ngôn ngữ

```python
# Tự động phát hiện ngôn ngữ từ văn bản
detected_lang = language_manager.detect_language_from_text("Hello world")
# Kết quả: "en"

detected_lang = language_manager.detect_language_from_text("Xin chào")
# Kết quả: "vi"
```

#### Quản lý display names

```python
# Lấy tên hiển thị ngắn gọn của voice
display_name = language_manager.get_voice_display_name("Nam - NamMinh (vi-VN-NamMinhNeural)")
# Kết quả: "Nam - NamMinh"

# Trích xuất voice name từ display name
voice_name = language_manager.extract_voice_name_from_label("Nam - NamMinh")
# Kết quả: "vi-VN-NamMinhNeural"
```

#### Populate combobox

```python
# Lấy danh sách voices để populate combobox
voices = language_manager.populate_voices_for_language("vi")
# Kết quả: ["Tự phát hiện", "Nam - NamMinh", "Nữ - HoaiMy"]

voices = language_manager.populate_voices_for_language("vi", include_auto_detect=False)
# Kết quả: ["Nam - NamMinh", "Nữ - HoaiMy"]
```

#### Helper functions

```python
# Chuyển đổi giữa tên và mã ngôn ngữ
lang_code = language_manager.code_by_name("Tiếng Việt")
# Kết quả: "vi"

display_name = language_manager.name_by_code("en")
# Kết quả: "Tiếng Anh"
```

## Ví dụ sử dụng trong translate_tab.py

### Trước (sử dụng hàm local và biến global):

```python
# Biến global
LANGS = [("Tự phát hiện", "auto")] + [(voices_data[lang]["display_name"], lang) for lang in voices_data.keys()]

def _create_control_buttons_row(self, parent_layout):
    # Sử dụng biến global
    languages = self.get_available_languages()
    self.source_lang_combo.addItems([n for n, _ in languages])
    
def _populate_source_voices(self):
    self.source_tts_lang_combo.clear()
    self.source_tts_lang_combo.addItem("Tự phát hiện")
    
    source_lang = self.source_lang_combo.currentText()
    if source_lang != "Tự phát hiện":
        lang_code = code_by_name(source_lang)
        if lang_code in voices_data:
            voices = voices_data[lang_code]["voices"]
            for voice in voices:
                display_name = voice["label"].split(" (")[0]
                self.source_tts_lang_combo.addItem(display_name)
```

### Sau (sử dụng language_manager và self.languages):

```python
def _initialize_state_variables(self):
    # Khởi tạo languages trong __init__
    self.languages = language_manager.get_available_languages()

def _create_control_buttons_row(self, parent_layout):
    # Sử dụng self.languages đã được khởi tạo
    self.source_lang_combo.addItems([n for n, _ in self.languages])
    
def _populate_source_voices(self):
    self.source_tts_lang_combo.clear()
    
    source_lang = self.source_lang_combo.currentText()
    if source_lang != "Tự phát hiện":
        lang_code = language_manager.code_by_name(source_lang)
        voices = language_manager.populate_voices_for_language(lang_code)
        for voice in voices:
            self.source_tts_lang_combo.addItem(voice)
    else:
        self.source_tts_lang_combo.addItem("Tự phát hiện")
```

## Lợi ích

1. **Tổ chức code tốt hơn**: Tất cả logic liên quan đến ngôn ngữ được tập trung vào một nơi
2. **Dễ bảo trì**: Khi cần thay đổi logic, chỉ cần sửa một file
3. **Tái sử dụng**: Có thể sử dụng `LanguageManager` ở nhiều nơi khác trong ứng dụng
4. **Dễ test**: Có thể test riêng biệt logic ngôn ngữ
5. **Giảm code trùng lặp**: Không còn các hàm tương tự ở nhiều nơi

## Migration

Để chuyển từ code cũ sang sử dụng `LanguageManager`:

1. **Thay thế import**:
   ```python
   # Cũ
   from langdetect import detect
   
   # Mới
   from app.core.language_manager import language_manager
   ```

2. **Thay thế các hàm**:
   ```python
   # Cũ
   self.get_female_voice(lang_code)
   self.detect_language_from_text(text)
   code_by_name(lang_name)
   name_by_code(lang_code)
   
   # Mới
   language_manager.get_female_voice(lang_code)
   language_manager.detect_language_from_text(text)
   language_manager.code_by_name(lang_name)
   language_manager.name_by_code(lang_code)
   ```

3. **Xóa các hàm local** không còn cần thiết

4. **Cập nhật populate voices** để sử dụng `populate_voices_for_language()`

## Lưu ý

- `language_manager` là một instance global, không cần tạo mới
- Tất cả các phương thức đều có error handling
- Fallback về tiếng Việt khi có lỗi
- Hỗ trợ đầy đủ các ngôn ngữ từ `voices_data.py`
