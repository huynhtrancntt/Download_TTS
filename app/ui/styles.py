"""
Centralized styling configuration for the application
"""

class AppStyles:
    """Application styling constants and methods"""
    
    # Color palette
    COLORS = {
        'primary': '#2b2d3a',
        'secondary': '#3a3d4f',
        'accent': '#FFD700',
        'success': '#4CAF50',
        'warning': '#FF9800', 
        'error': '#F44336',
        'info': '#2196F3',
        'background': '#0f172b',
        'surface': '#1e293b',
        'text_primary': '#f1f5f9',
        'text_secondary': '#64748b',
        'border': '#334155',
        'border_hover': '#475569',
    }
    
    # Common styles
    BUTTON_STYLE = f"""
        QPushButton {{
            background-color: {COLORS['primary']};
            border: 1px solid {COLORS['border']};
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 12px;
            color: {COLORS['text_primary']};
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {COLORS['secondary']};
            border-color: {COLORS['border_hover']};
        }}
        QPushButton:pressed {{
            background-color: {COLORS['border']};
        }}
        QPushButton:disabled {{
            background-color: #555;
            color: #888;
            border-color: #444;
        }}
    """
    
    INPUT_STYLE = f"""
        QLineEdit, QTextEdit {{
            background-color: {COLORS['background']};
            border: 1px solid {COLORS['border']};
            border-radius: 6px;
            padding: 8px;
            font-size: 13px;
            color: {COLORS['text_primary']};
        }}
        QLineEdit:focus, QTextEdit:focus {{
            border: 2px solid {COLORS['accent']};
        }}
    """
    
    COMBO_STYLE = f"""
        QComboBox {{
            background-color: {COLORS['primary']};
            border: 1px solid {COLORS['border']};
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 12px;
            color: {COLORS['text_primary']};
        }}
        QComboBox:hover {{
            border-color: {COLORS['border_hover']};
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 4px solid {COLORS['text_secondary']};
        }}
    """
    
    SLIDER_STYLE = f"""
        QSlider::groove:horizontal {{
            border: 1px solid {COLORS['border']};
            height: 6px;
            background: {COLORS['background']};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {COLORS['accent']};
            border: 1px solid {COLORS['border']};
            width: 18px;
            margin: -6px 0;
            border-radius: 9px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {COLORS['accent']};
            border: 2px solid {COLORS['text_primary']};
        }}
    """
    
    @classmethod
    def get_panel_style(cls) -> str:
        """Get style for panels/containers"""
        return f"""
            QWidget {{
                background-color: {cls.COLORS['background']};
                border-radius: 8px;
                border: 1px solid {cls.COLORS['border']};
            }}
        """
    
    @classmethod 
    def get_group_box_style(cls, title_color: str = None) -> str:
        """Get style for group boxes"""
        title_color = title_color or cls.COLORS['accent']
        return f"""
            QGroupBox {{
                font-size: 14px;
                font-weight: bold;
                border: 1px solid {cls.COLORS['border']};
                border-radius: 8px;
                margin: 5px 0px;
                padding-top: 15px;
                background-color: {cls.COLORS['background']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {title_color};
            }}
        """
