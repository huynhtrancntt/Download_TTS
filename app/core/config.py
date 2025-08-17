# -*- coding: utf-8 -*-
"""
Cấu hình ứng dụng và các hằng số
Chứa tất cả các thiết lập cơ bản của ứng dụng Text-to-Speech
"""
from pathlib import Path
from app.ui.styles import AppStyles


class AppConfig:
    """
    Lớp cấu hình chính của ứng dụng
    Chứa các thiết lập về cửa sổ, đường dẫn, và giao diện
    """
    
    # Đường dẫn gốc của dự án
    APP_DIR = Path(__file__).resolve().parent.parent.parent
    
    # Thông tin ứng dụng
    APP_NAME = "HT - Downloader"
    APP_VERSION = "1.0.0"
    WINDOW_TITLE = f"{APP_NAME} (v{APP_VERSION})"

    # Thiết lập cửa sổ
    MIN_WINDOW_SIZE = (500, 400)      # Kích thước tối thiểu (width, height)
    DEFAULT_WINDOW_SIZE = (1000, 700) # Kích thước mặc định
    ICON_PATH = APP_DIR / "images" / "icon.ico"  # Đường dẫn icon ứng dụng
    
    # Thiết lập layout
    HISTORY_PANEL_WIDTH = 300  # Chiều rộng panel lịch sử

    # Đường dẫn các thư mục
    OUTPUT_DIR = APP_DIR / "output"  # Thư mục lưu file đầu ra

    # Tạo thư mục output nếu chưa tồn tại
    OUTPUT_DIR.mkdir(exist_ok=True)
    LOG_PATH = OUTPUT_DIR / "log.json"  # File log JSON

    # Style từ AppStyles
    BUTTON_STYLE = AppStyles.BUTTON_STYLE


class TTSConfig:
    """
    Cấu hình đặc biệt cho chức năng Text-to-Speech
    Chứa các thiết lập về giọng nói, tốc độ, cao độ và xử lý
    """

    # Giá trị mặc định
    DEFAULT_VOICE = "vi-VN-HoaiMyNeural"  # Giọng tiếng Việt nữ mặc định
    DEFAULT_RATE = 0                      # Tốc độ bình thường (0%)
    DEFAULT_PITCH = 0                     # Cao độ bình thường (0%)
    DEFAULT_MAXLEN = 500                  # Độ dài tối đa mỗi đoạn (ký tự)
    DEFAULT_GAP_MS = 150                  # Khoảng cách giữa các đoạn (ms)
    DEFAULT_WORKERS_CHUNK = 4             # Số luồng xử lý chunk
    DEFAULT_WORKERS_FILE = 2              # Số luồng xử lý file
    DEFAULT_WORKERS_PLAYER = 4            # Số luồng cho player

    # Danh sách giọng nói có sẵn
    VOICE_CHOICES = [
        "vi-VN-HoaiMyNeural",    # Tiếng Việt - Nữ
        "vi-VN-NamMinhNeural",   # Tiếng Việt - Nam
        "en-US-JennyNeural",     # Tiếng Anh Mỹ - Nữ
        "en-US-GuyNeural",       # Tiếng Anh Mỹ - Nam
        "ja-JP-NanamiNeural",    # Tiếng Nhật - Nữ
        "ko-KR-SunHiNeural",     # Tiếng Hàn - Nữ
    ]

    # Lựa chọn tốc độ (phần trăm thay đổi)
    RATE_CHOICES = [-50, -40, -30, -20, -10, 0, 10, 20, 30, 40, 50]
    
    # Lựa chọn cao độ (Hz thay đổi)
    PITCH_CHOICES = [-12, -8, -6, -4, -2, 0, 2, 4, 6, 8, 12]

    # Tùy chọn ngôn ngữ (tên hiển thị, mã ngôn ngữ)
    LANGUAGE_OPTIONS = [
        ("Vietnamese (vi)", "vi"),
        ("English US (en-US)", "en-US"),
        ("English UK (en-GB)", "en-GB"),
        ("Japanese (ja)", "ja"),
        ("Korean (ko)", "ko"),
        ("Chinese (zh-CN)", "zh-CN"),
        ("French (fr-FR)", "fr-FR"),
        ("German (de-DE)", "de-DE"),
        ("Spanish (es-ES)", "es-ES"),
    ]

    # Tùy chọn giới tính
    GENDER_OPTIONS = ["Female", "Male", "Any"]

    # Thiết lập file
    TEMP_PREFIX = "edge_tts_parts_"  # Tiền tố file tạm
    TEMP_DIR = Path(__file__).resolve().parent.parent.parent / "output" / "temp"   # Thư mục lưu file tạm
