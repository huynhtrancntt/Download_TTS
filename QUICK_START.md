# 🚀 Hướng dẫn nhanh - Download TTS

## ⚡ Cài đặt và chạy trong 5 phút

### 1. Tải dự án
```bash
git clone <repository-url>
cd Download_TTS
```

### 2. Chạy cài đặt tự động (Windows)
```bash
install.bat
```

### 3. Hoặc cài đặt thủ công
```bash
# Tạo môi trường ảo
python -m venv venv

# Kích hoạt (Windows)
venv\Scripts\activate

# Kích hoạt (Linux/Mac)
source venv/bin/activate

# Cài đặt dependencies
pip install -r requirements.txt
```

### 4. Chạy ứng dụng
```bash
python main.py
```

## 🎯 Sử dụng cơ bản

### Chuyển đổi văn bản thành giọng nói
1. **Nhập văn bản**: Dán văn bản vào ô nhập liệu
2. **Chọn ngôn ngữ**: Vietnamese, English, Japanese, etc.
3. **Điều chỉnh tham số**: Tốc độ, cao độ, giới tính
4. **Bấm "Chuyển đổi"**: Bắt đầu xử lý TTS

### Phát audio
- **▶️ Play/Pause**: Bắt đầu/dừng phát
- **⏮/⏭**: Chuyển đoạn trước/sau
- **Timeline**: Click vào slider để seek nhanh
- **🔁 Lặp lại**: Bật/tắt chế độ lặp

### Xuất file MP3
1. **Chờ xử lý xong**: Tất cả segments hoàn thành
2. **Bấm "Lưu"**: Chọn nơi lưu file MP3
3. **Chờ ghép file**: Tự động ghép các đoạn

## ⚙️ Cài đặt quan trọng

### FFmpeg (bắt buộc)
- **Windows**: Tải từ https://ffmpeg.org
- **Linux**: `sudo apt install ffmpeg`
- **macOS**: `brew install ffmpeg`

### Python 3.8+
- Tải từ https://python.org
- Đảm bảo đã chọn "Add to PATH"

## 🔧 Xử lý sự cố nhanh

### Lỗi "FFmpeg not found"
```bash
# Đặt ffmpeg.exe trong thư mục dự án
# Hoặc thêm vào PATH
```

### Lỗi PySide6
```bash
pip install --force-reinstall PySide6
```

### Lỗi audio
- Kiểm tra driver âm thanh
- Thử chuyển đổi sang định dạng khác

## 📱 Giao diện chính

```
┌─────────────────────────────────────────┐
│ [TTS Tab] [Convert Tab] [Simple Tab]   │
├─────────────────────────────────────────┤
│ Threads: [4] MaxLen: [500] Gap: [100]  │
│ [📂 Mở file] [▶️ Bắt đầu] [⏹ Kết thúc] │
├─────────────────────────────────────────┤
│ [Văn bản đầu vào...]                   │
│                                         │
├─────────────────────────────────────────┤
│ Ngôn ngữ: [Vietnamese] Giới tính: [F]  │
│ Tốc độ: [██████████] 1.0x              │
│ Cao độ: [██████████] 1.0x              │
├─────────────────────────────────────────┤
│ [🔊 Chuyển đổi] [💾 Lưu] [⏹️ Dừng]     │
├─────────────────────────────────────────┤
│ [Danh sách segments...]                │
├─────────────────────────────────────────┤
│ ⏮ [▶️] ⏭ [██████████████████] 00:00/00:00 │
└─────────────────────────────────────────┘
```

## 🎵 Tính năng nâng cao

### Đa luồng xử lý
- **Threads**: 1-16 (tùy CPU)
- **MaxLen**: 80-2000 ký tự/đoạn
- **Gap**: 0-2000ms giữa các đoạn

### Hỗ trợ ngôn ngữ
- **Vietnamese**: vi-VN-HoaiMyNeural
- **English US**: en-US-AriaNeural
- **Japanese**: ja-JP-NanamiNeural
- **Korean**: ko-KR-SunHiNeural
- **Chinese**: zh-CN-XiaoxiaoNeural
- **French**: fr-FR-DeniseNeural
- **German**: de-DE-KatjaNeural
- **Spanish**: es-ES-ElviraNeural

### Điều chỉnh audio
- **Tốc độ**: 0.5x - 2.0x
- **Cao độ**: -50% đến +50%
- **Giới tính**: Female, Male, Any

## 📁 Cấu trúc file

```
Download_TTS/
├── 📄 main.py              # Chạy ứng dụng
├── 📄 run.bat              # Chạy nhanh (Windows)
├── 📄 install.bat          # Cài đặt tự động
├── 📄 build.bat            # Build executable
├── 📁 app/                 # Code chính
├── 📁 images/              # Icons và hình ảnh
├── 📁 output/              # File xuất MP3
└── 📄 README.md            # Tài liệu chi tiết
```

## 🚀 Lệnh nhanh

### Chạy ứng dụng
```bash
# Windows
run.bat

# Linux/Mac
python main.py
```

### Build executable
```bash
# Windows
build.bat

# Linux/Mac
pyinstaller --noconsole --onefile main.py
```

### Cài đặt dependencies
```bash
# Windows
install.bat

# Linux/Mac
pip install -r requirements.txt
```

## 📞 Hỗ trợ

- **Documentation**: Xem README.md
- **Issues**: Tạo issue trên GitHub
- **Features**: Đề xuất tính năng mới
- **Contributions**: Fork và tạo PR

---

**⏱️ Thời gian cài đặt**: ~5 phút  
**🎯 Độ khó**: Dễ dàng  
**📱 Hỗ trợ**: Windows, Linux, macOS
