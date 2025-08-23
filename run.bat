@echo off
@chcp 65001 >nul
setlocal

echo 🔍 Đang kiểm tra môi trường ảo...

if not exist venv (
    echo ❗ Chưa có môi trường ảo. Đang tạo venv...
    python -m venv venv
    python.exe -m pip install --upgrade pip
)

if exist venv\Scripts\activate.bat (
    echo ✅ Kích hoạt môi trường ảo...
    call venv\Scripts\activate.bat
) else (
    echo ❌ Không tìm thấy file kích hoạt môi trường.
    exit /b 1
)

cmd

@REM $PROFILE
@REM if (!(Test-Path -Path $PROFILE)) {
@REM     New-Item -Type File -Path $PROFILE -Force
@REM }
@REM notepad $PROFILE
@REM Set-Alias run "D:\DuAn\MyProject\run.bat"