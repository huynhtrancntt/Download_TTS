
# Legacy compatibility - import from new location
from app.core.config import AppConfig as CoreAppConfig, TTSConfig
from app.ui.styles import AppStyles

class AppConfig(CoreAppConfig):
    """Legacy AppConfig for backward compatibility"""
    
    # Keep legacy button style for compatibility
    BUTTON_STYLE = AppStyles.BUTTON_STYLE
    
    # Legacy colors mapping
    COLORS = {
        'success': AppStyles.COLORS['success'],
        'warning': AppStyles.COLORS['warning'], 
        'error': AppStyles.COLORS['error'],
        'info': AppStyles.COLORS['info'],
        'primary': AppStyles.COLORS['primary'],
    }
    
    # Re-export TTSConfig constants for backward compatibility
    DEFAULT_WORKERS_PLAYER = TTSConfig.DEFAULT_WORKERS_PLAYER
    DEFAULT_MAXLEN = TTSConfig.DEFAULT_MAXLEN
    DEFAULT_GAP_MS = TTSConfig.DEFAULT_GAP_MS
    TEMP_PREFIX = TTSConfig.TEMP_PREFIX
    TEMP_DIR = TTSConfig.TEMP_DIR
