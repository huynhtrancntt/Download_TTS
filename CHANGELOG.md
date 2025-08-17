# Changelog

Tất cả các thay đổi quan trọng trong dự án này sẽ được ghi lại trong file này.

Định dạng dựa trên [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
và dự án này tuân thủ [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Thêm mới
- File README.md tổng hợp toàn bộ dự án
- File setup.py để cài đặt dễ dàng
- File build.bat để build executable
- File install.bat để thiết lập môi trường
- File .gitignore để quản lý source code
- File CHANGELOG.md để theo dõi thay đổi

### Cải tiến
- Cập nhật cấu trúc dự án
- Tối ưu hóa quy trình build và cài đặt

## [1.0.0] - 2024-12-19

### Thêm mới
- Giao diện TTS hoàn chỉnh với PySide6
- Hỗ trợ đa ngôn ngữ (Vietnamese, English, Japanese, Korean, Chinese, French, German, Spanish)
- Hệ thống đa luồng xử lý TTS với worker threads
- Player tích hợp với điều khiển timeline và seek
- Hệ thống lịch sử để lưu trữ và quản lý các lần chuyển đổi
- Xuất file MP3 từ các đoạn audio
- Giao diện thân thiện với người dùng

### Tính năng chính
- **Text-to-Speech**: Chuyển đổi văn bản thành giọng nói chất lượng cao
- **Đa luồng**: Xử lý song song với nhiều worker threads (1-16)
- **Timeline control**: Điều khiển phát audio với seek và timeline
- **Lịch sử**: Lưu trữ và tái sử dụng các lần chuyển đổi
- **Xuất MP3**: Ghép các đoạn audio thành file hoàn chỉnh
- **Cấu hình linh hoạt**: Điều chỉnh tốc độ, cao độ, ngôn ngữ, giới tính

### Cấu trúc dự án
- `app/`: Module chính của ứng dụng
  - `core/`: Cấu hình cốt lõi
  - `history/`: Hệ thống lịch sử
  - `tabs/`: Các tab chức năng
  - `ui/`: Giao diện và styles
  - `utils/`: Tiện ích hỗ trợ
  - `workers.py`: Worker threads xử lý TTS
- `images/`: Tài nguyên hình ảnh
- `output/`: Thư mục xuất file
- `main.py`: Entry point chính

### Kỹ thuật
- **Framework**: PySide6 (Qt6)
- **TTS Engine**: Microsoft Edge TTS
- **Audio Processing**: pydub + FFmpeg
- **Architecture**: Multi-threaded với worker pattern
- **UI Pattern**: Tab-based interface với toolbar

### Hỗ trợ hệ điều hành
- Windows 10/11 (khuyến nghị)
- Linux (Ubuntu, CentOS)
- macOS (10.14+)

### Dependencies
- PySide6 >= 6.0.0
- pydub >= 0.25.0
- edge-tts >= 6.0.0
- FFmpeg (để xử lý audio)

## [0.9.0] - 2024-12-18

### Thêm mới
- Phiên bản beta đầu tiên
- Giao diện cơ bản với PySide6
- Chức năng TTS đơn giản
- Hỗ trợ tiếng Việt

### Tính năng
- Chuyển đổi văn bản thành giọng nói
- Giao diện đơn giản
- Xuất file audio cơ bản

## [0.8.0] - 2024-12-17

### Thêm mới
- Khởi tạo dự án
- Cấu trúc cơ bản
- Tích hợp Microsoft Edge TTS

---

## Ghi chú về phiên bản

- **Major**: Thay đổi lớn, có thể không tương thích ngược
- **Minor**: Thêm tính năng mới, tương thích ngược
- **Patch**: Sửa lỗi, tương thích ngược hoàn toàn

## Quy trình phát hành

1. **Development**: Phát triển tính năng mới
2. **Testing**: Kiểm thử và sửa lỗi
3. **Release**: Đánh dấu phiên bản mới
4. **Documentation**: Cập nhật tài liệu
5. **Distribution**: Phân phối cho người dùng

## Liên hệ

- **Báo cáo lỗi**: Tạo issue trên GitHub
- **Đề xuất tính năng**: Tạo feature request
- **Đóng góp**: Fork và tạo pull request

---

*Changelog này được tạo tự động và cập nhật theo quá trình phát triển dự án.*
