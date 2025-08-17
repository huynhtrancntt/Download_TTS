@echo off
@chcp 65001 >nul
setlocal

echo 🚀 Thiết lập môi trường cho Download TTS...

REM Kiểm tra Python
echo 🔍 Kiểm tra Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python không được tìm thấy!
    echo 📥 Vui lòng cài đặt Python 3.8+ từ https://python.org
    pause
    exit /b 1
)

REM Hiển thị phiên bản Python
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% đã được tìm thấy

REM Kiểm tra pip
echo 🔍 Kiểm tra pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip không được tìm thấy!
    echo 🔧 Đang cài đặt pip...
    python -m ensurepip --upgrade
)

REM Tạo môi trường ảo
echo 🌍 Tạo môi trường ảo...
if exist venv (
    echo ℹ️ Môi trường ảo đã tồn tại
) else (
    echo 📦 Đang tạo môi trường ảo...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Không thể tạo môi trường ảo!
        pause
        exit /b 1
    )
)

REM Kích hoạt môi trường ảo
echo ✅ Kích hoạt môi trường ảo...
call venv\Scripts\activate.bat

REM Cập nhật pip
echo 🔄 Cập nhật pip...
python -m pip install --upgrade pip

REM Cài đặt dependencies
echo 📦 Cài đặt dependencies...
pip install -r requirements.txt

REM Kiểm tra cài đặt
echo 🔍 Kiểm tra cài đặt...
python -c "import PySide6; print('✅ PySide6:', PySide6.__version__)" 2>nul
if errorlevel 1 (
    echo ❌ PySide6 cài đặt thất bại!
    pause
    exit /b 1
)

python -c "import pydub; print('✅ pydub:', pydub.__version__)" 2>nul
if errorlevel 1 (
    echo ❌ pydub cài đặt thất bại!
    pause
    exit /b 1
)

python -c "import edge_tts; print('✅ edge-tts:', edge_tts.__version__)" 2>nul
if errorlevel 1 (
    echo ❌ edge-tts cài đặt thất bại!
    pause
    exit /b 1
)

REM Tạo thư mục output nếu chưa có
if not exist output (
    echo 📁 Tạo thư mục output...
    mkdir output
)

REM Kiểm tra FFmpeg
echo 🔍 Kiểm tra FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ⚠️ FFmpeg không được tìm thấy trong PATH
    echo 📥 Vui lòng cài đặt FFmpeg từ https://ffmpeg.org
    echo 💡 Hoặc đặt ffmpeg.exe trong thư mục dự án
) else (
    echo ✅ FFmpeg đã được tìm thấy
)

REM Thông báo hoàn tất
echo.
echo 🎉 Thiết lập hoàn tất!
echo.
echo 📋 Để chạy ứng dụng:
echo   1. Kích hoạt môi trường ảo: venv\Scripts\activate
echo   2. Chạy ứng dụng: python main.py
echo   3. Hoặc sử dụng: run.bat
echo.
echo 🔨 Để build executable: build.bat
echo.

REM Hỏi người dùng có muốn chạy ngay không
set /p RUN_NOW="Bạn có muốn chạy ứng dụng ngay bây giờ? (y/n): "
if /i "%RUN_NOW%"=="y" (
    echo 🚀 Khởi động ứng dụng...
    python main.py
) else (
    echo ℹ️ Bạn có thể chạy ứng dụng sau bằng cách sử dụng run.bat
)

pause
