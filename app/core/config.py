"""
Application configuration and constants
"""
from pathlib import Path

class AppConfig:
    """Application configuration constants"""
    
    # Application info
    APP_NAME = "HT - Downloader"
    APP_VERSION = "1.0.0"
    WINDOW_TITLE = f"{APP_NAME} (v{APP_VERSION})"
    
    # Window settings
    MIN_WINDOW_SIZE = (700, 500)
    DEFAULT_WINDOW_SIZE = (1000, 700)
    
    # Layout settings
    HISTORY_PANEL_WIDTH = 300
    
    # Paths
    APP_DIR = Path(__file__).resolve().parent.parent.parent  # Project root
    OUTPUT_DIR = APP_DIR / "output"
    
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True)
    LOG_PATH = OUTPUT_DIR / "log.json"

class TTSConfig:
    """TTS-specific configuration"""
    
    # Default values
    DEFAULT_VOICE = "vi-VN-HoaiMyNeural"
    DEFAULT_RATE = 0
    DEFAULT_PITCH = 0
    DEFAULT_MAXLEN = 220
    DEFAULT_GAP_MS = 150
    DEFAULT_WORKERS_CHUNK = 4
    DEFAULT_WORKERS_FILE = 2
    DEFAULT_WORKERS_PLAYER = 4
    
    # Voice options
    VOICE_CHOICES = [
        "vi-VN-HoaiMyNeural",
        "vi-VN-NamMinhNeural", 
        "en-US-JennyNeural",
        "en-US-GuyNeural",
        "ja-JP-NanamiNeural",
        "ko-KR-SunHiNeural",
    ]
    
    # Rate and pitch ranges
    RATE_CHOICES = [-50, -40, -30, -20, -10, 0, 10, 20, 30, 40, 50]
    PITCH_CHOICES = [-12, -8, -6, -4, -2, 0, 2, 4, 6, 8, 12]
    
    # Language options
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
    
    # Gender options
    GENDER_OPTIONS = ["Female", "Male", "Any"]
    
    # File settings
    TEMP_PREFIX = "edge_tts_parts_"
