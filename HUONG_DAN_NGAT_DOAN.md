# 🎵 Hướng dẫn sử dụng chức năng Ngắt đoạn Audio (Phiên bản mới)

## ✂️ Tổng quan

Chức năng **Ngắt đoạn** đã được cải tiến để đơn giản hóa và hiệu quả hơn. Thay vì chia nhỏ audio gốc, chức năng này giờ đây:

- **Giữ nguyên audio gốc**: Không chia nhỏ hoặc thay đổi audio ban đầu
- **Tạo khoảng nghỉ 3 giây**: Luôn tạo khoảng nghỉ cố định 3 giây
- **Hỗ trợ thêm video**: Có thể thêm video mới tạo audio 3 giây
- **Bảo toàn nội dung**: Tất cả audio cũ được giữ nguyên

## 🚀 Cách sử dụng

### 1. Chuẩn bị
- **Có audio segments**: Bạn cần có ít nhất một đoạn audio (từ TTS hoặc thêm thủ công)
- **Audio player sẵn sàng**: Audio player phải được khởi tạo và có thể phát

### 2. Ngắt đoạn để tạo khoảng nghỉ
1. **Phát audio**: Sử dụng nút play/pause để di chuyển đến vị trí cần ngắt đoạn
   - **Ở ĐẦU segment**: Di chuyển đến trong vòng 1 giây đầu tiên của segment → Khoảng nghỉ TRƯỚC segment
   - **Ở CUỐI segment**: Di chuyển đến trong vòng 1 giây cuối cùng của segment → Khoảng nghỉ SAU segment
   - **Ở GIỮA segment**: Di chuyển đến vị trí bất kỳ trong segment → Khoảng nghỉ SAU segment hiện tại
2. **Chọn khoảng nghỉ**: Sử dụng dropdown "Khoảng:" để chọn thời gian nghỉ (3s, 4s, 5s, 10s)
3. **Ngắt đoạn**: Bấm nút **"✂️ Ngắt đoạn"** để thực hiện
4. **Xác nhận**: Hệ thống sẽ hiển thị dialog xác nhận với thông tin:
   - Vị trí ngắt (thời gian hiện tại)
   - Tên segment
   - Khoảng nghỉ đã chọn
   - Vị trí ngắt (trước hoặc sau segment)

### 3. Thêm video mới
1. **Bấm nút "🎬 Thêm Video"**: Chọn file video từ máy tính
2. **Hỗ trợ định dạng**: MP4, AVI, MKV, MOV, WMV
3. **Tự động tạo audio**: Video sẽ tạo ra file âm thanh 3 giây
4. **Giữ nguyên audio cũ**: Audio gốc và khoảng nghỉ không bị mất

### 4. Kết quả
Sau khi hoàn thành:
- **Audio gốc**: Được giữ nguyên hoàn toàn
- **Khoảng nghỉ**: Được tạo theo vị trí đã chọn:
  - **Nếu ngắt ở ĐẦU segment**: Khoảng nghỉ + Audio gốc
  - **Nếu ngắt ở CUỐI hoặc GIỮA segment**: Audio gốc + Khoảng nghỉ
- **Video audio**: 3 giây được tạo từ video mới
- **UI tự động cập nhật**: Danh sách segments hiển thị cấu trúc mới
- **Audio player**: Được cập nhật với cấu trúc mới

## 📊 Hiển thị kết quả

### Trong danh sách segments:
- **Audio gốc**: `[tên gốc]  —  [thời lượng]`
- **Khoảng nghỉ**: `[KHOẢNG NGHỈ 3s]  —  00:03`
- **Video audio**: `[tên video]  —  00:03 (Video - 3s audio)`

### Thống kê chi tiết:
Sử dụng nút **"ℹ️ Info"** để xem:
- Tổng số segments
- Số lượng khoảng nghỉ
- Số đoạn video
- Thời lượng tổng cộng

## 🎯 Xuất file MP3

### Xử lý thông minh:
- **Khoảng nghỉ tự động**: Hệ thống nhận diện và xử lý các khoảng nghỉ đã tạo
- **Không trùng lặp**: Không thêm gap thừa giữa các khoảng nghỉ
- **Thông báo chi tiết**: Hiển thị số lượng khoảng nghỉ trong file xuất

### Quy trình xuất:
1. Bấm nút **"💾 Lưu"**
2. Chọn vị trí lưu file MP3
3. Hệ thống tự động ghép các segments với khoảng nghỉ
4. File MP3 hoàn chỉnh được tạo

## ⚠️ Lưu ý quan trọng

### Điều kiện ngắt đoạn:
- ✅ Có segments trong danh sách
- ✅ Vị trí ngắt hợp lệ (đầu, cuối hoặc giữa segment)
- ✅ Audio player sẵn sàng
- ❌ Không thể ngắt khi chưa có segments
- ✅ Có thể ngắt ở bất kỳ vị trí nào trong segment

### Giới hạn kỹ thuật:
- **Định dạng hỗ trợ**: MP3, WAV, M4A, OGG, FLAC (audio), MP4, AVI, MKV, MOV, WMV (video)
- **Kích thước file**: Phụ thuộc vào RAM và dung lượng ổ cứng
- **Thời gian xử lý**: Phụ thuộc vào độ dài audio và hiệu suất máy

### Quản lý file tạm:
- Các file tạm được tạo trong `TEMP_DIR` từ config (mặc định: `output/temp/`)
- Tự động cleanup khi kết thúc hoặc đóng ứng dụng
- Có thể xóa thủ công nếu cần
- Có thể cấu hình đường dẫn trong `app/core/config.py`

## 🔧 Xử lý sự cố

### Lỗi thường gặp:

1. **"Không tìm thấy segment chứa vị trí hiện tại"**
   - **Nguyên nhân**: Vị trí đã chọn không nằm trong segment nào
   - **Giải pháp**: Di chuyển đến vị trí khác trong segment

2. **"Không thể thêm file video"**
   - **Nguyên nhân**: File video không hỗ trợ hoặc bị hỏng
   - **Giải pháp**: Kiểm tra định dạng file và thử file khác

### Khắc phục nhanh:
- **Restart player**: Dừng và phát lại audio
- **Reload segments**: Bấm "Kết thúc" rồi "Bắt đầu" lại
- **Kiểm tra file**: Đảm bảo các file audio/video không bị hỏng

## 💡 Mẹo sử dụng

### Tối ưu hóa:
- **Phát audio chính xác**: Sử dụng nút play/pause để di chuyển đến vị trí cần ngắt đoạn
- **Đầu segment**: Di chuyển đến 1 giây đầu tiên để tạo khoảng nghỉ TRƯỚC audio
- **Cuối segment**: Di chuyển đến 1 giây cuối cùng để tạo khoảng nghỉ SAU audio
- **Giữa segment**: Di chuyển đến vị trí bất kỳ để tạo khoảng nghỉ SAU audio
- **Chọn khoảng nghỉ phù hợp**: 3s cho nội dung ngắn, 5-10s cho nội dung quan trọng
- **Thêm video hợp lý**: Chọn video phù hợp với nội dung audio

### Workflow hiệu quả:
1. **Tạo TTS** với văn bản hoàn chỉnh
2. **Phát audio** để di chuyển đến vị trí cần ngắt đoạn
3. **Chọn khoảng nghỉ** từ dropdown (3s, 4s, 5s, 10s)
4. **Bấm ngắt đoạn** để tạo khoảng nghỉ
5. **Thêm video** tại các vị trí phù hợp
6. **Kiểm tra** kết quả bằng cách phát lại
7. **Xuất file** MP3 hoàn chỉnh

### Kết hợp với các tính năng khác:
- **Thêm audio thủ công**: Kết hợp với audio có sẵn
- **Sắp xếp segments**: Thay đổi thứ tự sau khi ngắt
- **Lặp lại**: Sử dụng với chế độ loop để kiểm tra

## 🎬 Tính năng thêm Video

### Hỗ trợ định dạng:
- **MP4**: Định dạng phổ biến nhất
- **AVI**: Định dạng cũ nhưng ổn định
- **MKV**: Định dạng container mở
- **MOV**: Định dạng của Apple
- **WMV**: Định dạng của Microsoft

### Xử lý tự động:
- **Tạo audio 3 giây**: Mỗi video tạo ra audio 3 giây cố định
- **Giữ nguyên audio cũ**: Không ảnh hưởng đến segments hiện có
- **Tích hợp hoàn hảo**: Video được xử lý như segment audio bình thường

### Cách sử dụng:
1. Bấm nút **"🎬 Thêm Video"**
2. Chọn file video từ máy tính
3. Hệ thống tự động tạo audio 3 giây
4. Video xuất hiện trong danh sách segments
5. Có thể phát và xuất như audio bình thường

## 🎉 Kết luận

Chức năng **Ngắt đoạn Audio** đã được cải tiến đáng kể với:

- **Phát audio chính xác**: Sử dụng nút play/pause để di chuyển đến vị trí cần ngắt đoạn
- **Khoảng nghỉ tùy chỉnh**: Chọn từ dropdown (3s, 4s, 5s, 10s) theo nhu cầu
- **Giữ nguyên audio**: Audio gốc không bị mất khi ngắt đoạn
- **Hỗ trợ video**: Thêm video mới tạo audio 3 giây
- **Tích hợp hoàn hảo**: Hoạt động mượt mà với các tính năng hiện có

Chức năng này mở ra nhiều khả năng mới cho việc tạo và chỉnh sửa audio, đặc biệt hữu ích cho:
- Tạo bài thuyết trình với khoảng nghỉ
- Thêm video vào audio content
- Tạo cấu trúc rõ ràng cho audio
- Kết hợp nhiều loại media khác nhau

Hãy thử nghiệm và khám phá các cách sử dụng sáng tạo cho chức năng này!

---

**Lưu ý**: Chức năng này yêu cầu FFmpeg để xử lý audio. Đảm bảo FFmpeg đã được cài đặt và cấu hình đúng.
