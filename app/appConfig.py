
# Legacy compatibility - import from new location
from app.core.config import AppConfig as CoreAppConfig
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
