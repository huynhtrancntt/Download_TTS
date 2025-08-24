# File: Ui_setting.py
from PySide6.QtWidgets import QMessageBox
import sys
import os
from pathlib import Path

# Version of the application
UPDATE_CHECK_URL = "https://raw.githubusercontent.com/huynhtrancntt/auto_update/main/update.json"
APP_VERSION = "1.6.0"  # Placeholder for actual version, replace with your app's version

# ===== STYLE VARIABLES =====
# Color palette
COLORS = {
    'primary_bg': '#0f172b',
    'secondary_bg': '#1e293b',
    'surface': '#1e293b',  # Màu bề mặt cho scrollbar
    'menu_bg': '#0d2538',
    'border': '#334155',
    'text_primary': '#e2e8f0',
    'text_white': '#ffffff',
    'text_disabled': '#a0aec0',
    'text_history_label': '#94a3b8',
    'text_history_label_2': '#4a5568',  # 64748b
    'accent_green': '#05ff8f',
    'accent_green_dark': '#05df60',
    'accent_green_hover': '#16a34a',
    'accent_blue': '#4299e1',
    'accent_gray': '#4a5568',
    'button_bg': '#2b2d3a',
    'button_hover': '#3a3d4f',
    'button_disabled': '#6c757d',
    'button_skip_hover': '#545b62',
    'button_manual': '#007bff',
    'button_manual_hover': '#0056b3',
    'success_green': '#28a745',
    'version_box_bg': '#0d2b32',
    'player_green_light': 'rgba(40, 167, 69, 0.1)',
    'player_green_medium': 'rgba(40, 167, 69, 0.2)',
    'player_green_border': '#34ce57',
    'player_green_pressed': '#1e7e34'
}

# Font settings
FONTS = {
    'family': 'Arial',
    'size_normal': '14px',
    'size_small': '12px',
    'monospace': '"Consolas", "Monaco", monospace'
}

# Common dimensions
DIMENSIONS = {
    'border_radius': '6px',
    'border_radius_large': '8px',
    'border_radius_xlarge': '12px',
    'padding_small': '6px',
    'padding_medium': '8px',
    'padding_large': '10px',
    'padding_xlarge': '12px',
    'slider_height': '8px',
    'slider_handle': '16px',
    'player_button_size': '32px'
}
ABOUT_TEMPLATE = """
<h3>🎬 HT DownloadVID v{version}</h3>
<p><b>Ứng dụng download video và phụ đề</b></p>
<p>📅 Phiên bản: {version}</p>
<p>👨‍💻 Phát triển bởi: HT Software</p>
<p>🔧 Sử dụng: yt-dlp + ffmpeg</p>
<br>

<p><b>Tính năng:</b></p>
<ul>
  <li>✅ Download video từ nhiều nền tảng</li>
  <li>✅ Hỗ trợ playlist</li>
  <li>✅ Download phụ đề đa ngôn ngữ</li>
  <li>✅ Chuyển đổi audio sang MP3</li>
  <li>✅ Lưu settings tự động</li>
  <li>✅ Kiểm tra cập nhật tự động</li>
</ul>
"""


def resource_path(rel: str) -> str:
    if hasattr(sys, "_MEIPASS"):         # PyInstaller
        base = Path(sys._MEIPASS)
    elif "__compiled__" in globals():     # Nuitka onefile
        base = Path(os.path.dirname(sys.argv[0]))
    else:
        base = Path(os.path.abspath("."))
    return str(base / rel)


# ===== STYLE COMPONENTS =====
def get_menu_styles():
    """Get menu and menubar styles"""
    return f"""
        QMenuBar {{
            background-color: {COLORS['menu_bg']};
            color: {COLORS['text_white']};
            font-family: {FONTS['family']};
            font-size: {FONTS['size_normal']};
        }}
        QMenu {{
            background-color: {COLORS['menu_bg']};
            color: {COLORS['text_white']};
            font-family: {FONTS['family']};
            font-size: {FONTS['size_normal']};
        }}
        QMenu::item {{
            padding: {DIMENSIONS['padding_medium']} 16px;
        }}   
        QMenu::item:selected {{
            background-color: {COLORS['secondary_bg']};
            color: {COLORS['text_white']};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {COLORS['border']};
        }}
        QMenu::icon {{
            margin-right: {DIMENSIONS['padding_medium']};
        }}
        QMenu::item:disabled {{
            color: {COLORS['text_disabled']};
        }}
    """


def get_widget_base_styles():
    """Get base widget styles"""
    return f"""
        QWidget {{
            background-color: {COLORS['primary_bg']};
            color: {COLORS['text_primary']};
            font-family: {FONTS['family']};
            font-size: {FONTS['size_normal']};
        }}
        QLabel {{
            color: {COLORS['text_white']};
            background-color: transparent;
            font-weight: normal;
        }}
    """


def get_button_styles():
    """Get button styles"""
    return f"""
        QPushButton {{
            background: {COLORS['button_bg']};
            border: 1px solid #444;
            border-radius: {DIMENSIONS['border_radius']};
            padding: {DIMENSIONS['padding_small']};
            font-size: {FONTS['size_small']};
        }}
        QPushButton:hover {{
            background: {COLORS['button_hover']};
        }}
        QPushButton:disabled {{
            background-color: {COLORS['button_disabled']};
        }}
        QPushButton#skipBtn {{
            background-color: {COLORS['button_disabled']};
            color: white;
            font-weight: bold;
            padding: {DIMENSIONS['padding_large']} 20px;
            border-radius: 5px;
        }}
        QPushButton#skipBtn:hover {{
            background-color: {COLORS['button_skip_hover']};
        }}
        QPushButton#manualDownloadBtn {{
            background-color: {COLORS['button_manual']};
            color: white;
            font-weight: bold;
            padding: {DIMENSIONS['padding_large']} 20px;
            border-radius: 5px;
        }}
        QPushButton#manualDownloadBtn:hover {{
            background-color: {COLORS['button_manual_hover']};
        }}
    """


def get_input_styles():
    """Get input field styles"""
    return f"""
        QTextEdit, QLineEdit, QComboBox {{
            background-color: {COLORS['secondary_bg']};
            color: {COLORS['text_primary']};
            border: 1px solid {COLORS['border']};
            border-radius: {DIMENSIONS['border_radius']};
            padding: {DIMENSIONS['padding_small']};
        }}
        QTextEdit:hover {{
            border: 1px solid {COLORS['success_green']};
        }}
        QLineEdit:hover {{
            border: 1px solid {COLORS['success_green']};
        }}
        
        /* Tắt màu tô đen khi chọn text */
        QTextEdit::selection, QLineEdit::selection {{
            background-color: transparent;
            color: {COLORS['text_primary']};
        }}
    """


def get_combobox_styles(arrow_icon_path):
    """Get combobox specific styles"""
    return f"""
        QComboBox {{
            background-color: {COLORS['secondary_bg']};
            color: {COLORS['text_primary']};
            border: 1px solid {COLORS['border']};
            border-radius: {DIMENSIONS['border_radius']};
            padding: {DIMENSIONS['padding_small']};   
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left-width: 1px;
            border-left-color: {COLORS['border']};
            border-left-style: solid;
        }}
        QComboBox::down-arrow {{
            image: url("{arrow_icon_path}");
            width: 16px;
            height: 16px;
        }}
    """


def get_spinbox_styles(down_arrow, up_arrow):
    """Get spinbox styles similar to combobox"""
    return f"""
        QSpinBox, QDoubleSpinBox {{
            background-color: {COLORS['secondary_bg']};
            color: {COLORS['text_primary']};
            border: 1px solid {COLORS['border']};
            border-radius: {DIMENSIONS['border_radius']};
            padding: {DIMENSIONS['padding_small']};
            min-height: 20px;
        }}
        /*
        QSpinBox:hover, QDoubleSpinBox:hover {{
            border: 1px solid {COLORS['success_green']};
        }}*/

        QSpinBox::up-button , QDoubleSpinBox::up-button {{
            subcontrol-origin: border;
            subcontrol-position: top right;
            width: 20px;
            border-left-width: 1px;
            border-left-color: {COLORS['border']};
            border-left-style: solid;
            border-top-right-radius: {DIMENSIONS['border_radius']};
            background-color: {COLORS['secondary_bg']};
            border-top: 1px solid {COLORS['border']};
            border-right: 1px solid {COLORS['border']};
        }}

         
        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
            background-color: {COLORS['accent_gray']};
        }}
        QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed {{
            background-color: {COLORS['accent_gray']};
        }}
        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
            image: url("{up_arrow}");
            width: 12px;
            height: 12px;
            transform: rotate(180deg);
            
        }}
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            subcontrol-origin: border;
            subcontrol-position: bottom right;
            width: 20px;
            border-left-width: 1px;
            border-left-color: {COLORS['border']};
            border-left-style: solid;
            border-bottom-right-radius: {DIMENSIONS['border_radius']};
            background-color: {COLORS['secondary_bg']};
            border-top: 1px solid {COLORS['border']};
            border-right: 1px solid {COLORS['border']};
            border-bottom: 1px solid {COLORS['border']};
        }}
        
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
            background-color: {COLORS['accent_gray']};
        }}
        QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {{
            background-color: {COLORS['accent_gray']};
        }}
        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
            image: url("{down_arrow}");
            width: 12px;
            height: 12px;
        }}
    """


def get_checkbox_radio_styles(down_arrow):
    """Get checkbox and radio button styles"""
    return f"""
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {COLORS['accent_gray']};
            border-radius: 4px;
            background-color: {COLORS['secondary_bg']};
            margin: 2px;
        }}
        QCheckBox::indicator:hover {{
            border: 2px solid {COLORS['accent_green']};
        }}
        QCheckBox::indicator:checked {{
          
            border: 2px solid {COLORS['accent_green']};
            image: url("{down_arrow}");
        }}
        QCheckBox::indicator:checked:hover {{

            border: 2px solid {COLORS['accent_green_hover']};
        }}
        QCheckBox {{
            color: {COLORS['text_white']};
            font-size: {FONTS['size_normal']};
            spacing: 8px;
            padding: 2px;
        }}
        QCheckBox:hover {{
            color: {COLORS['accent_green']};
        }}
        QRadioButton {{
            color: {COLORS['text_white']};
            font-size: {FONTS['size_normal']};
            spacing: 8px;
            padding: 2px;
        }}
        QRadioButton:hover {{
            color: {COLORS['accent_green']};
        }}
        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {COLORS['accent_gray']};
            border-radius: 9px;
            background-color: {COLORS['secondary_bg']};
            margin: 2px;
        }}
        QRadioButton::indicator:hover {{
            border: 2px solid {COLORS['accent_green']};
        }}
        QRadioButton::indicator:checked {{
            background-color: {COLORS['accent_green']};
            border: 2px solid {COLORS['accent_green']};
        }}
        QRadioButton::indicator:checked:hover {{
            background-color: {COLORS['accent_green_hover']};
            border: 2px solid {COLORS['accent_green_hover']};
        }}
    """


def get_slider_styles():
    """Get slider styles"""
    return f"""
        QSlider::groove:horizontal {{
            background: {COLORS['border']};
            height: {DIMENSIONS['slider_height']};
            border-radius: 4px;
        }}
        QSlider::sub-page:horizontal {{
            background: {COLORS['accent_green']};
            height: {DIMENSIONS['slider_height']};
            border-radius: 4px;
        }}
        QSlider::handle:horizontal {{
            background: {COLORS['accent_green_dark']};
            height: {DIMENSIONS['slider_handle']};
            width: {DIMENSIONS['slider_handle']};
            margin: -4px 0;
            border-radius: 8px;
        }}
    """


def get_list_widget_styles():
    """Get list widget styles"""
    return f"""
        QListWidget {{
            background-color: {COLORS['secondary_bg']};
            color: {COLORS['text_primary']};
            border: 1px solid {COLORS['border']};
            border-radius: {DIMENSIONS['border_radius']};
            font-family: {FONTS['monospace']};
            font-size: {FONTS['size_small']};
            padding: {DIMENSIONS['padding_small']};
            selection-background-color: {COLORS['accent_blue']};
            outline: none;
        }}
        QListWidget::item {{
            padding: {DIMENSIONS['padding_small']} {DIMENSIONS['padding_medium']};
            border-bottom: 1px solid {COLORS['accent_gray']};
            min-height: 20px;
            word-wrap: break-word;
        }}
        QListWidget::item:hover {{
            background-color: {COLORS['accent_gray']};
        }}
        QListWidget::item:selected {{
            background-color: {COLORS['accent_gray']};
            color: {COLORS['text_white']};
        }}
    """


def get_progress_bar_styles():
    """Get progress bar styles"""
    return f"""
        QProgressBar {{
            border: 2px solid {COLORS['accent_blue']};
            border-radius: {DIMENSIONS['border_radius']};
            text-align: center;
            height: 20px;
            background-color: {COLORS['border']};
            color: #fff;
            font-weight: bold;
        }}
        QProgressBar::chunk {{
            background-color: {COLORS['accent_blue']};
            border-radius: 5px;
        }}
    """


def get_tab_styles():
    """Get tab widget styles"""
    return f"""
        QTabBar::tab {{
            font-weight: bold;
            color: white;
            margin-top: 0px;
            margin-left: {DIMENSIONS['padding_large']};
            margin-right: {DIMENSIONS['padding_large']};
            padding: {DIMENSIONS['padding_medium']};
            padding-top: 2px;
            border: none;
        }}
        QTabBar::tab:selected {{
           border-bottom: 1px solid {COLORS['success_green']};
        }}
        QTabWidget::pane {{
            border: none;
            outline: none;
        }}
    """


def get_group_box_styles():
    """Get group box styles"""
    return f"""
        QGroupBox {{
            border: 1px solid {COLORS['border']};
            border-radius: {DIMENSIONS['border_radius_large']};
            margin-top: {DIMENSIONS['padding_large']};
            padding: {DIMENSIONS['padding_large']};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px;
        }}
    """


def get_frame_styles():
    """Get frame styles"""
    return f"""
        QFrame#versionBox {{
            background-color: {COLORS['version_box_bg']};
            border-radius: {DIMENSIONS['padding_large']};
            padding: {DIMENSIONS['padding_xlarge']};
        }}
    """


def get_player_styles():
    """Get player component styles"""
    return f"""
        /* ----- Player container ----- */
        #PlayerPanel {{
            border: 1px solid {COLORS['border']};
            border-radius: {DIMENSIONS['border_radius_xlarge']};
            padding: {DIMENSIONS['padding_medium']};
        }}

        /* ----- Nút play/pause tròn, không nền xanh ----- */
        QPushButton#PlayerPlay {{
            background: transparent;
            color: {COLORS['text_white']};
            border: 1px solid {COLORS['border']};
            border-radius: 16px;
            width: {DIMENSIONS['player_button_size']};
            height: {DIMENSIONS['player_button_size']};
            font-size: {FONTS['size_normal']};
            font-weight: bold;
            text-align: center;
            margin: 0px;
            padding: 0px;
        }}
        QPushButton#PlayerPlay:hover {{
            background: {COLORS['player_green_light']};
            border: 1px solid {COLORS['player_green_border']};
        }}
        QPushButton#PlayerPlay:pressed {{
            background: {COLORS['player_green_medium']};
            border: 1px solid {COLORS['player_green_pressed']};
        }}

        /* ----- Thanh seek (tiến trình) ----- */
        QSlider#PlayerSeek {{
            height: {DIMENSIONS['player_button_size']};
        }}
        QSlider#PlayerSeek::groove:horizontal {{
            height: {DIMENSIONS['slider_height']};
            background: {COLORS['border']};
            border: none;
            border-radius: 4px;
        }}
        QSlider#PlayerSeek::sub-page:horizontal {{
            background: {COLORS['accent_green']};
            border: none;
            border-radius: 4px;
        }}
        QSlider#PlayerSeek::add-page:horizontal {{
            background: {COLORS['border']};
            border: none;
            border-radius: 4px;
        }}
        QSlider#PlayerSeek::handle:horizontal {{
            width: 14px;
            margin: -5px 0;
            border-radius: 7px;
            background: {COLORS['text_primary']};
            border: 2px solid {COLORS['accent_green_hover']};
        }}

        /* ----- Thanh volume (nhỏ, gọn) ----- */
        QSlider#PlayerVol {{
            max-width: 140px;
        }}
        QSlider#PlayerVol::groove:horizontal {{
            height: {DIMENSIONS['slider_height']};
            background: {COLORS['border']};
            border: none;
            border-radius: 4px;
        }}
        QSlider#PlayerVol::sub-page:horizontal {{
            background: {COLORS['accent_green']};
            border: none;
            border-radius: 4px;
        }}
        QSlider#PlayerVol::add-page:horizontal {{
            background: {COLORS['border']};
            border: none;
            border-radius: 4px;
        }}
        QSlider#PlayerVol::handle:horizontal {{
            width: 14px;
            margin: -5px 0;
            border-radius: 7px;
            background: {COLORS['text_primary']};
            border: 2px solid {COLORS['accent_green_hover']};
        }}
    """


def get_scrollbar_styles():
    """Get scrollbar styles for all scrollable widgets"""
    return f"""
        /* ----- Thanh trượt dọc (vertical scrollbar) ----- */
        QScrollBar:vertical {{
            background: {COLORS['surface']};
            width: 0px;
            border-radius: 4px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {COLORS['border']};
            border-radius: 4px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {COLORS['accent_gray']};
        }}
        QScrollBar::handle:vertical:pressed {{
            background: {COLORS['accent_blue']};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}

        /* ----- Thanh trượt ngang (horizontal scrollbar) ----- */
        QScrollBar:horizontal {{
            background: {COLORS['surface']};
            height: 8px;
            border-radius: 4px;
            margin: 0px;
        }}
        QScrollBar::handle:horizontal {{
            background: {COLORS['border']};
            border-radius: 4px;
            min-width: 20px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {COLORS['accent_gray']};
        }}
        QScrollBar::handle:horizontal:pressed {{
            background: {COLORS['accent_blue']};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}

        /* ----- Thanh trượt cho QListWidget và QTextEdit ----- */
        QListWidget QScrollBar:vertical, QTextEdit QScrollBar:vertical {{
            background: {COLORS['secondary_bg']};
            width: 6px;
            border-radius: 3px;
        }}
        QListWidget QScrollBar::handle:vertical, QTextEdit QScrollBar::handle:vertical {{
            background: {COLORS['accent_gray']};
            border-radius: 3px;
            min-height: 15px;
        }}
        QListWidget QScrollBar::handle:vertical:hover, QTextEdit QScrollBar::handle:vertical:hover {{
            background: {COLORS['accent_blue']};
        }}
        
        /* Tắt màu tô đen khi chọn text trong QTextEdit */
        QTextEdit::selection {{
            background-color: transparent;
            color: {COLORS['text_primary']};
        }}
    """


def get_button_style_1__styles():
    """Get button styles"""
    return f"""
        QPushButton#btn_style_1{{
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
            }}
        QPushButton#btn_style_1:hover {{
                background-color: #218838;
            }}
        QPushButton#btn_style_1:disabled {{
                background-color: #6c757d;
            }}
        QPushButton#btn_style_skip {{
            background-color: #6c757d;
            color: white;
            font-weight: bold;
            padding: 10px 20px;
            border-radius: 5px;
        }}
        QPushButton#btn_style_skip:hover {{
            background-color: #545b62;
        }}
    """


def show_about_ui(self):
    about_text = ABOUT_TEMPLATE.format(version=self.version)
    QMessageBox.about(self, "Về ứng dụng", about_text)


def _init_addStyle(self):
    """Initialize application styles using modular style functions"""
    arrow_icon_path = resource_path("images/down-arrow.png").replace("\\", "/")
    down_arrow = resource_path("images/down.png").replace("\\", "/")
    up_arrow = resource_path("images/up.png").replace("\\", "/")
    # Combine all style components
    combined_styles = (
        get_menu_styles() +
        get_widget_base_styles() +
        get_button_styles() +
        get_input_styles() +
        get_combobox_styles(arrow_icon_path) +
        get_spinbox_styles(down_arrow, up_arrow) +
        get_checkbox_radio_styles(down_arrow) +
        get_slider_styles() +
        get_list_widget_styles() +
        get_progress_bar_styles() +
        get_tab_styles() +
        get_group_box_styles() +
        get_frame_styles() +
        get_player_styles() +
        get_scrollbar_styles() +
        get_button_style_1__styles()
    )

    self.setStyleSheet(combined_styles)
