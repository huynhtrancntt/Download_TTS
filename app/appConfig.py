
class AppConfig:
    """Application configuration constants"""
    WINDOW_TITLE = "HT - Downloader (v1.0.0)"
    MIN_WINDOW_SIZE = (700, 500)  # Reduced for better responsiveness
    DEFAULT_WINDOW_SIZE = (1000, 700)

    HISTORY_PANEL_WIDTH = 300

    # Color scheme
    COLORS = {
        'success': '#4CAF50',    # Xanh lá - thành công
        'warning': '#FF9800',    # Vàng cam - cảnh báo
        'error': '#F44336',      # Đỏ - lỗi
        'info': '#2196F3',       # Xanh dương - thông tin
        'primary': '#9C27B0',    # Tím - chính
    }

    # Styles
    # MAIN_STYLE = "background-color: #1a1c24; color: white; font-size: 13px;"
    # TOAST_STYLE = """
    #     QWidget { background-color: #101828; border: 1px solid rgba(0,227,150,.6); border-radius: 8px; }
    #     QLabel { color: white; font-weight: bold; font-size: 12px; }
    #     QPushButton { background: transparent; color: #888; border: none; font-size: 14px; }
    #     QPushButton:hover { color: white; }
    #     QProgressBar { background-color: transparent; border: none; height: 3px; }
    #     QProgressBar::chunk { background-color: #00e396; border-radius: 1px; }
    # """
    BUTTON_STYLE = """
        QPushButton{background:#2b2d3a;border:1px solid #444;border-radius:6px;padding:6px;font-size:12px;} 
        QPushButton:hover{background:#3a3d4f;}
    """
