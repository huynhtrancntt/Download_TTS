# 🎵 Download TTS - Ứng dụng Text-to-Speech

Ứng dụng Text-to-Speech với giao diện PySide6, hỗ trợ chuyển đổi văn bản thành giọng nói chất lượng cao sử dụng Microsoft Edge TTS.

## ✨ Tính năng chính

- **Text-to-Speech**: Chuyển đổi văn bản thành giọng nói với nhiều ngôn ngữ
- **Đa luồng xử lý**: Hỗ trợ xử lý song song với nhiều worker threads
- **Player tích hợp**: Phát audio với điều khiển timeline và seek
- **Ngắt đoạn thông minh**: ✂️ Ngắt đoạn audio tại vị trí bất kỳ với khoảng nghỉ 3 giây cố định
- **Thêm video**: 🎬 Thêm file video tạo audio 3 giây tự động
- **Giữ nguyên audio**: Audio gốc không bị mất khi ngắt đoạn hoặc thêm video
- **Lịch sử**: Lưu trữ và quản lý các lần chuyển đổi
- **Xuất MP3**: Ghép các đoạn audio thành file MP3 hoàn chỉnh với khoảng nghỉ tự động
- **Giao diện thân thiện**: UI hiện đại với PySide6

## 🚀 Cài đặt và chạy

### Yêu cầu hệ thống
- Python 3.8+
- Windows 10/11 (khuyến nghị)
- FFmpeg (để xử lý audio)

### Cài đặt nhanh

1. **Clone hoặc tải dự án**
```bash
git clone <repository-url>
cd Download_TTS
```

2. **Tạo môi trường ảo**
```bash
python -m venv venv
```

3. **Kích hoạt môi trường ảo**
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

4. **Cài đặt dependencies**
```bash
pip install -r requirements.txt
```

5. **Chạy ứng dụng**
```bash
python main.py
```

### Chạy bằng file batch (Windows)
```bash
run.bat
```

## 📁 Cấu trúc dự án

```
Download_TTS/
├── app/                    # Thư mục chính của ứng dụng
│   ├── core/              # Cấu hình cốt lõi
│   ├── history/           # Hệ thống lịch sử
│   ├── tabs/              # Các tab chức năng
│   ├── ui/                # Giao diện và styles
│   ├── utils/             # Tiện ích hỗ trợ
│   ├── workers.py         # Worker threads xử lý TTS
│   ├── historyPanel.py    # Panel hiển thị lịch sử
│   ├── uiToolbarTab.py    # Base class cho các tab
│   ├── ui_setting.py      # Cài đặt giao diện
│   ├── appConfig.py       # Cấu hình ứng dụng
│   └── constants.py       # Hằng số và cấu hình
├── images/                 # Tài nguyên hình ảnh
├── output/                 # Thư mục xuất file
├── main.py                 # Entry point chính
├── requirements.txt        # Dependencies
├── run.bat                 # Script chạy Windows
└── README.md               # Tài liệu này
```

## 🎯 Hướng dẫn sử dụng

### 1. Khởi động ứng dụng
- Chạy `python main.py` hoặc `run.bat`
- Giao diện chính sẽ hiển thị với tab TTS

### 2. Sử dụng TTS
- **Nhập văn bản**: Dán văn bản trực tiếp hoặc mở file .txt
- **Cấu hình**: Chọn ngôn ngữ, giới tính, tốc độ, cao độ
- **Tham số**: Điều chỉnh số threads, độ dài đoạn, khoảng cách
- **Chuyển đổi**: Bấm "Chuyển đổi" để bắt đầu xử lý

### 3. Phát audio
- **Điều khiển**: Play/Pause, Next/Previous, Seek
- **Timeline**: Click vào slider để seek nhanh
- **Lặp lại**: Bật/tắt chế độ lặp

### 4. Ngắt đoạn audio
- **Ngắt đoạn**: Bấm nút "✂️ Ngắt đoạn" khi đang phát audio
- **Khoảng nghỉ cố định**: Tự động tạo khoảng nghỉ 3 giây
- **Giữ nguyên audio**: Audio gốc không bị mất khi ngắt đoạn
- **Vị trí ngắt**: Ngắt tại vị trí hiện tại đang phát
- **Tự động cập nhật**: UI và player tự động cập nhật sau khi ngắt

### 5. Thêm video
- **Thêm video**: Bấm nút "🎬 Thêm Video" để chọn file video
- **Hỗ trợ định dạng**: MP4, AVI, MKV, MOV, WMV
- **Tạo audio tự động**: Video sẽ tạo ra file âm thanh 3 giây
- **Giữ nguyên audio cũ**: Audio gốc và khoảng nghỉ không bị mất

### 6. Xuất file
- **Lưu MP3**: Ghép các đoạn thành file hoàn chỉnh với khoảng nghỉ
- **Xử lý thông minh**: Tự động nhận diện và xử lý các khoảng nghỉ đã tạo
- **Lịch sử**: Xem và tái sử dụng các lần chuyển đổi

## ⚙️ Cấu hình

### Tham số TTS
- **Threads**: Số luồng xử lý (1-16)
- **Max Length**: Độ dài tối đa mỗi đoạn (80-2000 ký tự)
- **Gap**: Khoảng cách giữa các đoạn (0-2000ms)

### Ngôn ngữ hỗ trợ
- Vietnamese (vi)
- English US (en-US)
- English UK (en-GB)
- Japanese (ja)
- Korean (ko)
- Chinese (zh-CN)
- French (fr-FR)
- German (de-DE)
- Spanish (es-ES)

### Cài đặt audio
- **Tốc độ**: 0.5x - 2.0x
- **Cao độ**: -50% đến +50%

## 🔧 Tùy chỉnh và phát triển

### Thêm ngôn ngữ mới
Chỉnh sửa `app/constants.py`:
```python
VOICE_CHOICES = [
    ("Vietnamese (vi)", "vi-VN-HoaiMyNeural"),
    ("New Language (code)", "language-code-voice"),
]
```

### Thay đổi giao diện
- Styles: `app/ui/styles.py`
- Layout: `app/tabs/tts_tab.py`
- Icons: `images/`

### Cấu hình đường dẫn
- **Temp directory**: `app/core/config.py` - `TTSConfig.TEMP_DIR`
- **Output directory**: `app/core/config.py` - `AppConfig.OUTPUT_DIR`
- **File prefixes**: `app/core/config.py` - `TTSConfig.TEMP_PREFIX`

### Thêm tính năng mới
- Tạo tab mới: Kế thừa từ `UIToolbarTab`
- Worker mới: Kế thừa từ `MTProducerWorker`

## 📦 Build và phân phối

### Tạo executable
```bash
pyinstaller --noconsole --onefile --name EdgeTTSSuite main.py
```

### Tạo installer
```bash
# Sử dụng Inno Setup hoặc NSIS
# Cấu hình trong setup.iss
```

## 🐛 Xử lý sự cố

### Lỗi thường gặp

1. **FFmpeg không tìm thấy**
   - Cài đặt FFmpeg và thêm vào PATH
   - Hoặc đặt ffmpeg.exe trong thư mục dự án

2. **Lỗi PySide6**
   - Cập nhật Python lên phiên bản mới nhất
   - Cài đặt lại: `pip install --force-reinstall PySide6`

3. **Lỗi audio**
   - Kiểm tra driver âm thanh
   - Thử chuyển đổi sang định dạng khác

### Debug mode
```python
# Thêm vào main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📝 Changelog

### Version 1.2.0 (2024-12-19)
- ✂️ **Ngắt đoạn audio cải tiến**: Giữ nguyên audio gốc, chỉ tạo khoảng nghỉ 3 giây
- 🎬 **Thêm video mới**: Hỗ trợ thêm file video tạo audio 3 giây tự động
- 🔄 **Đơn giản hóa logic**: Loại bỏ logic phức tạp chia nhỏ segment
- 🎵 **Bảo toàn nội dung**: Audio cũ không bị mất khi ngắt đoạn hoặc thêm video

### Version 1.1.0
- ✂️ **Ngắt đoạn audio thông minh**: Ngắt đoạn tại vị trí bất kỳ với khoảng nghỉ tùy chỉnh
- 🔄 **Tự động cập nhật**: UI và player tự động cập nhật sau khi ngắt đoạn
- 📊 **Thống kê nâng cao**: Hiển thị thông tin chi tiết về segments, khoảng nghỉ, và đoạn đã ngắt
- 🎯 **Xuất MP3 thông minh**: Tự động xử lý các khoảng nghỉ khi xuất file

### Version 1.0.0
- ✅ Giao diện TTS hoàn chỉnh
- ✅ Hỗ trợ đa ngôn ngữ
- ✅ Player tích hợp với timeline
- ✅ Hệ thống lịch sử
- ✅ Xuất MP3
- ✅ Đa luồng xử lý

## 🤝 Đóng góp

1. Fork dự án
2. Tạo feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit thay đổi (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Mở Pull Request

## 📄 Giấy phép

Dự án này được phân phối dưới giấy phép MIT. Xem `LICENSE` để biết thêm chi tiết.

## 👥 Tác giả

- **Tên tác giả** - *Công việc ban đầu* - [GitHub](https://github.com/username)

## 🙏 Lời cảm ơn

- Microsoft Edge TTS API
- PySide6 team
- FFmpeg project
- Cộng đồng Python

---

**Lưu ý**: Đây là phiên bản beta. Vui lòng báo cáo lỗi và đề xuất tính năng mới!
