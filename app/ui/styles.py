# -*- coding: utf-8 -*-
"""
Cấu hình style tập trung cho ứng dụng
Chứa tất cả các style và màu sắc được sử dụng trong giao diện
"""

class AppStyles:
    """
    Lớp chứa các hằng số và phương thức styling cho ứng dụng
    Quản lý màu sắc, style cho button, input, combo box, slider
    """
    
    # Bảng màu chính của ứng dụng
    COLORS = {
        'primary': '#2b2d3a',      # Màu chính - xanh đậm
        'secondary': '#3a3d4f',    # Màu phụ - xanh nhạt hơn
        'accent': '#FFD700',       # Màu nhấn - vàng
        'success': '#4CAF50',      # Màu thành công - xanh lá
        'warning': '#FF9800',      # Màu cảnh báo - cam
        'error': '#F44336',        # Màu lỗi - đỏ
        'info': '#2196F3',         # Màu thông tin - xanh dương
        'background': '#0f172b',   # Màu nền chính - xanh đen
        'surface': '#1e293b',      # Màu bề mặt - xanh xám
        'text_primary': '#f1f5f9', # Màu chữ chính - trắng nhạt
        'text_secondary': '#64748b', # Màu chữ phụ - xám
        'border': '#334155',       # Màu viền - xám đậm
        'border_hover': '#475569', # Màu viền khi hover - xám sáng
    }
    
    # Style chung cho các thành phần
    
    # Style cho nút bấm
    BUTTON_STYLE = f"""
        QPushButton {{
            background-color: {COLORS['primary']};    /* Màu nền chính */
            border: 1px solid {COLORS['border']};      /* Viền */
            border-radius: 6px;                        /* Bo tròn góc */
            padding: 8px 12px;                         /* Khoảng cách trong */
            font-size: 12px;                           /* Kích thước font */
            color: {COLORS['text_primary']};           /* Màu chữ */
            font-weight: 500;                          /* Độ đậm chữ */
        }}
        QPushButton:hover {{
            background-color: {COLORS['secondary']};   /* Màu khi hover */
            border-color: {COLORS['border_hover']};    /* Viền khi hover */
        }}
        QPushButton:pressed {{
            background-color: {COLORS['border']};      /* Màu khi nhấn */
        }}
        QPushButton:disabled {{
            background-color: #555;                    /* Màu khi vô hiệu */
            color: #888;                               /* Màu chữ khi vô hiệu */
            border-color: #444;                        /* Viền khi vô hiệu */
        }}
    """
    
    # Style cho ô nhập liệu
    INPUT_STYLE = f"""
        QLineEdit, QTextEdit {{
            background-color: {COLORS['background']};  /* Màu nền */
            border: 1px solid {COLORS['border']};       /* Viền */
            border-radius: 6px;                         /* Bo tròn góc */
            padding: 8px;                               /* Khoảng cách trong */
            font-size: 13px;                            /* Kích thước font */
            color: {COLORS['text_primary']};            /* Màu chữ */
        }}
        QLineEdit:focus, QTextEdit:focus {{
            border: 2px solid {COLORS['accent']};       /* Viền khi focus - màu vàng */
        }}
    """
    
    # Style cho combo box (dropdown)
    COMBO_STYLE = f"""
        QComboBox {{
            background-color: {COLORS['primary']};     /* Màu nền */
            border: 1px solid {COLORS['border']};       /* Viền */
            border-radius: 6px;                         /* Bo tròn góc */
            padding: 6px 12px;                          /* Khoảng cách trong */
            font-size: 12px;                            /* Kích thước font */
            color: {COLORS['text_primary']};            /* Màu chữ */
        }}
        QComboBox:hover {{
            border-color: {COLORS['border_hover']};     /* Viền khi hover */
        }}
        QComboBox::drop-down {{
            border: none;                               /* Không viền cho nút dropdown */
        }}
        QComboBox::down-arrow {{
            image: none;                                /* Không dùng ảnh mũi tên */
            border-left: 4px solid transparent;        /* Tạo mũi tên CSS */
            border-right: 4px solid transparent;
            border-top: 4px solid {COLORS['text_secondary']};
        }}
    """
    
    # Style cho slider (thanh trượt)
    SLIDER_STYLE = f"""
        QSlider::groove:horizontal {{
            border: 1px solid {COLORS['border']};       /* Viền rãnh slider */
            height: 6px;                                /* Chiều cao rãnh */
            background: {COLORS['background']};         /* Màu nền rãnh */
            border-radius: 3px;                         /* Bo tròn rãnh */
        }}
        QSlider::handle:horizontal {{
            background: {COLORS['accent']};             /* Màu nền nút kéo - vàng */
            border: 1px solid {COLORS['border']};       /* Viền nút kéo */
            width: 18px;                                /* Chiều rộng nút kéo */
            margin: -6px 0;                             /* Căn giữa nút kéo */
            border-radius: 9px;                         /* Bo tròn nút kéo */
        }}
        QSlider::handle:horizontal:hover {{
            background: {COLORS['accent']};             /* Màu khi hover */
            border: 2px solid {COLORS['text_primary']}; /* Viền đậm khi hover */
        }}
    """
    
    @classmethod
    def get_panel_style(cls) -> str:
        """
        Lấy style cho các panel/container
        Returns:
            str: CSS style cho panel
        """
        return f"""
            QWidget {{
                background-color: {cls.COLORS['background']};  /* Màu nền */
                border-radius: 8px;                            /* Bo tròn góc */
                border: 1px solid {cls.COLORS['border']};      /* Viền */
            }}
        """
    
    @classmethod 
    def get_group_box_style(cls, title_color: str = None) -> str:
        """
        Lấy style cho group box
        Args:
            title_color: Màu tiêu đề (mặc định là accent color)
        Returns:
            str: CSS style cho group box
        """
        title_color = title_color or cls.COLORS['accent']
        return f"""
            QGroupBox {{
                font-size: 14px;                              /* Kích thước font */
                font-weight: bold;                             /* Độ đậm chữ */
                border: 1px solid {cls.COLORS['border']};      /* Viền */
                border-radius: 8px;                            /* Bo tròn góc */
                margin: 5px 0px;                               /* Margin trên dưới */
                padding-top: 15px;                             /* Padding trên */
                background-color: {cls.COLORS['background']};  /* Màu nền */
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;                     /* Vị trí tiêu đề */
                left: 10px;                                    /* Căn trái */
                padding: 0 5px 0 5px;                          /* Padding tiêu đề */
                color: {title_color};                          /* Màu tiêu đề */
            }}
        """
