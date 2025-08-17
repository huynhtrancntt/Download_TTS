@echo off
@chcp 65001 >nul
setlocal

echo 🚀 Bắt đầu build ứng dụng Download TTS...

REM Kiểm tra môi trường ảo
if not exist venv (
    echo ❗ Chưa có môi trường ảo. Đang tạo venv...
    python -m venv venv
)

REM Kích hoạt môi trường ảo
echo ✅ Kích hoạt môi trường ảo...
call venv\Scripts\activate.bat

REM Cài đặt dependencies
echo 📦 Cài đặt dependencies...
pip install -r requirements.txt
pip install pyinstaller

REM Tạo thư mục build nếu chưa có
if not exist build (
    mkdir build
)

REM Xóa các file build cũ
echo 🧹 Dọn dẹp build cũ...
if exist dist (
    rmdir /s /q dist
)
if exist build (
    rmdir /s /q build
)
if exist *.spec (
    del *.spec
)

REM Build ứng dụng
echo 🔨 Đang build ứng dụng...
pyinstaller --noconsole --onefile --name "Download_TTS" ^
    --add-data "app;app" ^
    --add-data "images;images" ^
    --add-data "demo.txt;." ^
    --add-data "run.bat;." ^
    --icon "images/icon.ico" ^
    main.py

REM Kiểm tra kết quả
if exist "dist\Download_TTS.exe" (
    echo ✅ Build thành công!
    echo 📁 File executable: dist\Download_TTS.exe
    
    REM Tạo thư mục output nếu chưa có
    if not exist "dist\output" (
        mkdir "dist\output"
    )
    
    REM Copy các file cần thiết
    echo 📋 Copy các file cần thiết...
    copy "run.bat" "dist\"
    copy "demo.txt" "dist\"
    copy "README.md" "dist\"
    
    echo 🎉 Hoàn tất! Ứng dụng đã sẵn sàng trong thư mục dist\
) else (
    echo ❌ Build thất bại!
    echo 🔍 Kiểm tra lỗi trong quá trình build...
)

REM Giữ cửa sổ mở để xem kết quả
pause
