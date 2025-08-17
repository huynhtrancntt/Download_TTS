# -*- coding: utf-8 -*-
"""
Tab Text-to-Speech - Chức năng chuyển văn bản thành giọng nói
Cung cấp giao diện để nhập văn bản, cấu hình giọng nói và phát audio
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QLabel, QTextEdit, QComboBox, QSlider, QSpinBox, 
    QListWidget, QProgressBar, QCheckBox, QMessageBox, 
    QFileDialog, QListWidgetItem
)
from PySide6.QtCore import Qt, QTimer, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

import sys
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List

# Import các module của ứng dụng
from app.uiToolbarTab import UIToolbarTab
from app.appConfig import AppConfig
from app.history.historyItem_TTS import TTSHistoryItem
from app.workers import MTProducerWorker

# Import constants và utilities
from ..constants import (
    VOICE_CHOICES, RATE_CHOICES, PITCH_CHOICES,
    DEFAULT_VOICE, DEFAULT_RATE, DEFAULT_PITCH, DEFAULT_MAXLEN, 
    DEFAULT_WORKERS_PLAYER, DEFAULT_GAP_MS, OUTPUT_DIR
)
from app.utils.helps import (
    ms_to_mmss, clean_all_temp_parts, get_mp3_duration_ms, 
    save_log_entry, prepare_pydub_ffmpeg
)

# Import thư viện xử lý audio
from pydub import AudioSegment


class ClickSlider(QSlider):
    """
    Slider cải tiến cho phép click vào bất kỳ vị trí nào để seek ngay lập tức
    
    Tính năng:
    - Click vào bất kỳ vị trí nào trên slider để seek
    - Hỗ trợ cả click chuột trái và phải
    - Tự động tính toán vị trí chính xác dựa trên tọa độ click
    """
    
    # Signal phát ra khi click vào slider
    clickedValue = Signal(int)

    def mousePressEvent(self, event) -> None:
        """
        Xử lý sự kiện click chuột
        Cho phép click vào bất kỳ vị trí nào để seek
        """
        if event.button() in (Qt.LeftButton, Qt.RightButton):
            # Tính tỷ lệ vị trí click so với chiều rộng slider
            ratio = event.position().x() / max(1, self.width())
            
            # Giới hạn ratio trong khoảng [0, 1]
            ratio = max(0.0, min(1.0, ratio))
            
            # Tính giá trị tương ứng
            vmin, vmax = self.minimum(), self.maximum()
            value = int(vmin + ratio * (vmax - vmin))
            
            # Cập nhật giá trị slider
            self.setValue(value)
            
            # Phát signal với giá trị mới
            self.clickedValue.emit(value)
        
        # Gọi phương thức gốc để xử lý các sự kiện khác
        super().mousePressEvent(event)


class TTSTab(UIToolbarTab):
    """
    Tab Text-to-Speech với giao diện và chức năng cải tiến
    
    Chức năng chính:
    - Nhập văn bản từ file hoặc typing trực tiếp
    - Cấu hình giọng nói, tốc độ, cao độ
    - Chuyển đổi văn bản thành audio với đa luồng
    - Phát audio với điều khiển timeline
    - Lưu lịch sử và xuất file MP3
    """

    def __init__(self, parent_main: QWidget) -> None:
        """
        Khởi tạo tab TTS
        Args:
            parent_main: Widget cha (MainWindow)
        """
        super().__init__(parent_main)
        
        # Khởi tạo biến trạng thái
        self._initialize_state_variables()
        
        # Thiết lập giao diện
        self._setup_ui()
        
        # Thiết lập hệ thống audio
        self._setup_audio_system()
        
        # Thiết lập timer và kết nối tín hiệu
        self._setup_timers_and_connections()

    def _initialize_state_variables(self) -> None:
        """
        Khởi tạo các biến trạng thái của tab
        """
        # Danh sách các đoạn audio và thời lượng
        self.segment_paths: List[Optional[str]] = []
        self.segment_durations: List[Optional[int]] = []
        
        # Trạng thái phát nhạc
        self.total_known_ms: int = 0
        self.current_index: int = -1
        self.seeking: bool = False
        self.is_playing: bool = False
        
        # Worker xử lý TTS
        self.worker: Optional[MTProducerWorker] = None
        
        # File output
        self.file_output: str = ""
        
        # Giá trị seek pending
        self._pending_seek_value: Optional[int] = None
        
        # Thời gian seek cuối cùng để bảo vệ timeline
        self._last_seek_time: float = 0.0

    def _setup_audio_system(self) -> None:
        """
        Thiết lập hệ thống audio (player và output)
        """
        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)

    def _setup_timers_and_connections(self) -> None:
        """
        Thiết lập timer và kết nối các tín hiệu
        """
        # Timer cập nhật timeline
        self.timer = QTimer(self)
        self.timer.setInterval(100)  # Cập nhật mỗi 100ms
        self.timer.timeout.connect(self.update_timeline)

        # Kết nối tín hiệu player
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.player.errorOccurred.connect(self.on_media_error)
        self.player.positionChanged.connect(self.on_player_position_changed)
        self.player.playbackStateChanged.connect(self.on_playback_state_changed)

        # Timer debounce cho seek
        self.seek_debounce = QTimer(self)
        self.seek_debounce.setInterval(150)  # Debounce 150ms
        self.seek_debounce.setSingleShot(True)
        self.seek_debounce.timeout.connect(self.apply_seek_target)

    def append_history(self, text: str, meta: Optional[dict] = None) -> None:
        """
        Thêm item vào lịch sử TTS
        Args:
            text: Văn bản cần lưu vào lịch sử
            meta: Metadata bổ sung (tùy chọn)
        """
        if self.history:
            self.history.panel.add_history(text, meta=meta or {})

    def _setup_ui(self) -> None:
        """
        Khởi tạo toàn bộ giao diện cho tab TTS
        Chia thành các phần: header, content, player controls
        """
        root_layout = self.layout()
        self.file_output = ""

        # Thiết lập hệ thống lịch sử
        self._setup_history_system()
        
        # Thiết lập phần header (tham số và nút điều khiển)
        self._setup_header_section(root_layout)
        
        # Thiết lập phần content chính
        self._setup_content_section(root_layout)
        
        # Thiết lập phần player controls
        self._setup_player_section(root_layout)
        
        # Kết nối các tín hiệu còn lại
        self._connect_remaining_signals()
        
        # Cập nhật status bar của cửa sổ cha
        if getattr(self.parent_main, "status", None):
            self.parent_main.status.showMessage("TTS Tab sẵn sàng")

    def _setup_history_system(self) -> None:
        """
        Thiết lập hệ thống lịch sử TTS
        """
        # Bật khu vực lịch sử với factory method
        hist = self.enable_history(
            hist_title="Lịch sử TTS",
            item_factory=lambda text, ts, lang, meta: TTSHistoryItem(text, ts, lang, meta),
            on_item_selected=self._on_history_selected
        )

        # Thêm một số demo history (có thể xóa sau)
        self.append_history(
            "Xin chào, tôi là trợ lý AI ...", 
            meta={"demo": True, "priority": "high"}
        )
        self.append_history(
            "Hôm nay thời tiết thế nào?", 
            meta={"demo": True, "priority": "normal"}
        )

    def _setup_header_section(self, root_layout: QVBoxLayout) -> None:
        """
        Thiết lập phần header với tham số job và nút điều khiển
        """
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(2, 2, 2, 2)
        
        # Tạo layout 2 hàng trong header
        row_layout = QVBoxLayout()
        
        # Hàng 1: tham số job + nút mở lịch sử
        self._create_job_parameters_row(row_layout)
        
        # Hàng 2: nút mở file + start/stop
        self._create_control_buttons_row(row_layout)
        
        # Ghép vào header
        header_layout.addLayout(row_layout)
        root_layout.addLayout(header_layout)

    def _create_job_parameters_row(self, parent_layout: QVBoxLayout) -> None:
        """
        Tạo hàng tham số job (threads, maxlen, gap)
        """
        row1_layout = QHBoxLayout()
        
        # Spin box số threads
        self.theard_edge_tts = QSpinBox()
        self.theard_edge_tts.setRange(1, 16)
        self.theard_edge_tts.setValue(DEFAULT_WORKERS_PLAYER)
        self.theard_edge_tts.setSuffix(" Theard")

        # Spin box độ dài tối đa mỗi đoạn
        self.maxlen_spin_edge_tts = QSpinBox()
        self.maxlen_spin_edge_tts.setRange(80, 2000)
        self.maxlen_spin_edge_tts.setValue(DEFAULT_MAXLEN)
        self.maxlen_spin_edge_tts.setSuffix(" ký tự/đoạn")

        # Spin box khoảng cách giữa các đoạn
        self.gap_spin_edge_tts = QSpinBox()
        self.gap_spin_edge_tts.setRange(0, 2000)
        self.gap_spin_edge_tts.setValue(DEFAULT_GAP_MS)
        self.gap_spin_edge_tts.setSuffix(" ms nghỉ ghép")

        # Thêm vào layout
        row1_layout.addWidget(QLabel("Theard"))
        row1_layout.addWidget(self.theard_edge_tts)
        row1_layout.addWidget(self.maxlen_spin_edge_tts)
        row1_layout.addWidget(self.gap_spin_edge_tts)
        row1_layout.addStretch()
        
        # Thêm nút lịch sử (sẽ được lấy từ history system)
        if hasattr(self, 'history') and self.history:
            row1_layout.addWidget(self.history.btn)
        
        parent_layout.addLayout(row1_layout)

    def _create_control_buttons_row(self, parent_layout: QVBoxLayout) -> None:
        """
        Tạo hàng nút điều khiển (mở file, start, stop)
        """
        row2_layout = QHBoxLayout()
        row2_layout.setContentsMargins(0, 0, 0, 0)
        
        # Nút mở file
        self.btn_open_edge_tts = QPushButton("📂 Mở file")
        self.btn_open_edge_tts.clicked.connect(self.on_open_file)
        row2_layout.addWidget(self.btn_open_edge_tts)
        
        row2_layout.addStretch()
        
        # Nút bắt đầu và kết thúc
        self.btn_start_edge_tts = QPushButton("▶️ Bắt đầu")
        self.btn_start_edge_tts.clicked.connect(self.on_start)
        
        self.btn_end_edge_tts = QPushButton("⏹ Kết thúc")
        self.btn_end_edge_tts.clicked.connect(self.on_end_all)
        self.btn_end_edge_tts.setEnabled(False)  # Mặc định disabled
        
        row2_layout.addWidget(self.btn_start_edge_tts)
        row2_layout.addWidget(self.btn_end_edge_tts)
        
        parent_layout.addLayout(row2_layout)

    def _setup_content_section(self, root_layout: QVBoxLayout) -> None:
        """
        Thiết lập phần content chính (text input, cấu hình, controls)
        """
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Text input area
        self._create_text_input_area(content_layout)
        
        # Configuration controls
        self._create_configuration_controls(content_layout)
        
        # Segments list
        self._create_segments_list(content_layout)
        
        # Status label
        self._create_status_label(content_layout)
        
        root_layout.addLayout(content_layout)

    def _create_text_input_area(self, content_layout: QVBoxLayout) -> None:
        """
        Tạo khu vực nhập văn bản
        """
        self.text_input_edge_tts = QTextEdit(
            placeholderText="Dán văn bản hoặc bấm Mở .txt"
        )
        self.text_input_edge_tts.setMinimumHeight(200)
        content_layout.addWidget(self.text_input_edge_tts, 2)

    def _create_configuration_controls(self, content_layout: QVBoxLayout) -> None:
        """
        Tạo các control cấu hình (ngôn ngữ, giới tính, tốc độ, cao độ, nút điều khiển)
        """
        # Tạo combo boxes cho ngôn ngữ và giới tính
        self._create_language_gender_controls(content_layout)
        
        # Tạo sliders cho tốc độ và cao độ
        self._create_speed_pitch_controls(content_layout)
        
        # Tạo nút điều khiển TTS
        self._create_tts_control_buttons(content_layout)

    def _create_language_gender_controls(self, content_layout: QVBoxLayout) -> None:
        """
        Tạo combo box ngôn ngữ và giới tính
        """
        row_layout = QHBoxLayout()
        
        # Combo box ngôn ngữ
        self.cmb_lang = QComboBox()
        self.cmb_lang.setMinimumWidth(120)
        for label, code in [
            ("Vietnamese (vi)", "vi"), ("English US (en-US)", "en-US"),
            ("English UK (en-GB)", "en-GB"), ("Japanese (ja)", "ja"),
            ("Korean (ko)", "ko"), ("Chinese (zh-CN)", "zh-CN"),
            ("French (fr-FR)", "fr-FR"), ("German (de-DE)", "de-DE"),
            ("Spanish (es-ES)", "es-ES"),
        ]:
            self.cmb_lang.addItem(label, code)
        self.cmb_lang.setCurrentIndex(0)

        # Combo box giới tính
        self.cmb_gender = QComboBox()
        self.cmb_gender.setMinimumWidth(80)
        self.cmb_gender.addItems(["Female", "Male", "Any"])
        self.cmb_gender.setCurrentText("Female")

        row_layout.addWidget(QLabel("Ngôn ngữ"))
        row_layout.addWidget(self.cmb_lang)
        row_layout.addWidget(QLabel("Giới tính"))
        row_layout.addWidget(self.cmb_gender)
        row_layout.addStretch()
        
        content_layout.addLayout(row_layout)

    def _create_speed_pitch_controls(self, content_layout: QVBoxLayout) -> None:
        """
        Tạo slider tốc độ và cao độ
        """
        row_layout = QHBoxLayout()
        
        # Slider tốc độ (0.5x → 2.0x)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(50, 200)
        self.speed_slider.setValue(100)  # 1.0x mặc định
        self.speed_slider.setTickInterval(10)
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        
        self.lbl_speed_val = QLabel("1.0")
        self.speed_slider.valueChanged.connect(
            lambda v: self.lbl_speed_val.setText(f"{v/100:.1f}")
        )

        # Slider cao độ (-50% → +50%)
        self.pitch_slider = QSlider(Qt.Horizontal)
        self.pitch_slider.setRange(-50, 50)
        self.pitch_slider.setValue(0)  # 0% mặc định
        self.pitch_slider.setTickInterval(10)
        self.pitch_slider.setTickPosition(QSlider.TicksBelow)
        
        self.lbl_pitch_val = QLabel("1.0")
        self.pitch_slider.valueChanged.connect(
            lambda v: self.lbl_pitch_val.setText(f"{1 + v/100:.1f}")
        )

        row_layout.addWidget(QLabel("Tốc độ"))
        row_layout.addWidget(self.speed_slider, 1)
        row_layout.addWidget(self.lbl_speed_val)
        row_layout.addSpacing(12)
        row_layout.addWidget(QLabel("Cao độ"))
        row_layout.addWidget(self.pitch_slider, 1)
        row_layout.addWidget(self.lbl_pitch_val)
        
        content_layout.addLayout(row_layout)

    def _create_tts_control_buttons(self, content_layout: QVBoxLayout) -> None:
        """
        Tạo các nút điều khiển TTS (Chuyển đổi, Lưu, Dừng, Xóa chunks)
        """
        row_layout = QHBoxLayout()
        
        # Tạo các nút
        self.btn_say = QPushButton("🔊 Chuyển đổi")
        self.btn_save = QPushButton("💾 Lưu")
        self.btn_stop = QPushButton("⏹️ Dừng")
        self.btn_clear_chunks = QPushButton("🗑️ Xóa Chunks")
        self.btn_info = QPushButton("ℹ️ Info")
        self.btn_add_audio = QPushButton("🎵 Thêm Audio")
        self.btn_remove_segment = QPushButton("❌ Xóa Segment")
        self.btn_reorder = QPushButton("🔄 Sắp xếp")
        self.btn_test_loop = QPushButton("🔄 Test Loop")
        
        # Kết nối các nút
        self.btn_info.clicked.connect(self._print_segments_info)
        self.btn_add_audio.clicked.connect(self.on_add_audio_file)
        self.btn_remove_segment.clicked.connect(self.on_remove_selected_segment)
        self.btn_reorder.clicked.connect(self.on_reorder_segments)
        self.btn_test_loop.clicked.connect(self.on_test_loop)
        
        # Áp dụng style cho các nút
        for btn in (self.btn_say, self.btn_save, self.btn_stop, self.btn_clear_chunks, self.btn_info, self.btn_add_audio, self.btn_remove_segment, self.btn_reorder, self.btn_test_loop):
            btn.setStyleSheet(AppConfig.BUTTON_STYLE)
            btn.setMinimumWidth(80)
            btn.setMaximumWidth(120)
            row_layout.addWidget(btn)
        
        row_layout.addStretch()
        content_layout.addLayout(row_layout)

    def _create_segments_list(self, content_layout: QVBoxLayout) -> None:
        """
        Tạo list widget hiển thị các segments
        """
        self.list_segments = QListWidget()
        content_layout.addWidget(self.list_segments, 2)

    def _create_status_label(self, content_layout: QVBoxLayout) -> None:
        """
        Tạo label hiển thị trạng thái
        """
        self.lbl_status = QLabel("Sẵn sàng")
        self.lbl_status.setStyleSheet(
            "color: #888; font-size: 12px; padding: 5px;"
        )
        content_layout.addWidget(self.lbl_status)

    def _setup_player_section(self, root_layout: QVBoxLayout) -> None:
        """
        Thiết lập phần player controls
        """
        # Tạo các nút điều khiển player
        self.btn_prev = QPushButton("⏮")
        self.btn_prev.clicked.connect(self.play_prev)
        
        self.btn_playpause = QPushButton("▶️")
        self.btn_playpause.clicked.connect(self.toggle_playpause)

        self.btn_next = QPushButton("⏭")
        self.btn_next.clicked.connect(self.play_next)

        # Slider timeline với click-to-seek cải tiến
        self.slider = ClickSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)

        # Label thời gian và progress bar
        self.lbl_time = QLabel("00:00 / 00:00")
        self.progress_gen = QProgressBar()
        self.progress_gen.setRange(0, 100)
        self.progress_gen.setValue(0)

        # Checkbox lặp lại
        self.chk_loop = QCheckBox("🔁 Lặp lại")
        self.chk_loop.setChecked(True)

        # Tạo widget player và layout
        self.player_widget = QWidget()
        player_row = QHBoxLayout(self.player_widget)
        
        # Thêm controls vào layout
        player_row.addWidget(self.btn_prev)
        player_row.addWidget(self.btn_playpause)
        player_row.addWidget(self.btn_next)
        player_row.addWidget(self.slider, 1)
        player_row.addWidget(self.lbl_time)
        player_row.addWidget(self.chk_loop)
        
        root_layout.addWidget(self.player_widget)

    def _connect_remaining_signals(self) -> None:
        """
        Kết nối các tín hiệu còn lại
        """
        # Kết nối slider signals
        if hasattr(self, 'slider'):
            self.slider.sliderPressed.connect(self.on_slider_pressed)
            self.slider.sliderMoved.connect(self.on_slider_moved)
            self.slider.sliderReleased.connect(self.on_slider_released)
            self.slider.clickedValue.connect(self.on_slider_clicked)
        
        # Kết nối double click trên list segments
        if hasattr(self, 'list_segments'):
            self.list_segments.itemDoubleClicked.connect(self.on_list_item_double_clicked)

    def _ensure_capacity(self, n: int) -> None:
        """
        Đảm bảo danh sách segments có đủ capacity
        """
        while len(self.segment_paths) < n:
            self.segment_paths.append(None)
            self.segment_durations.append(None)
    
    def _print_segments_info(self) -> None:
        """
        In ra thông tin chi tiết về tất cả segments
        """
        if not self.segment_durations or not any(self.segment_durations):
            print("📋 No segments available")
            return
        
        print("📋 Segments Information:")
        total_duration = 0
        cumulative_time = 0
        
        for i, (path, duration) in enumerate(zip(self.segment_paths, self.segment_durations)):
            if duration:
                segment_start = cumulative_time
                segment_end = cumulative_time + duration
                filename = os.path.basename(path) if path else "No path"
                
                # Kiểm tra xem có phải segment được thêm thủ công không
                is_manual = " (Thêm thủ công)" if "Thêm thủ công" in self.list_segments.item(i).text() else ""
                
                print(f"  [{i:02d}] {filename}{is_manual}")
                print(f"       Duration: {duration}ms ({ms_to_mmss(duration)})")
                print(f"       Range: {ms_to_mmss(segment_start)} to {ms_to_mmss(segment_end)}")
                print(f"       Global offset: {cumulative_time}ms ({ms_to_mmss(cumulative_time)})")
                
                total_duration += duration
                cumulative_time += duration
        
        print(f"📊 Total duration: {total_duration}ms ({ms_to_mmss(total_duration)})")
        print(f"📊 Total segments: {len([d for d in self.segment_durations if d])}")
        
        # Thống kê thêm
        manual_count = sum(1 for i in range(self.list_segments.count()) 
                          if "Thêm thủ công" in self.list_segments.item(i).text())
        tts_count = len([d for d in self.segment_durations if d]) - manual_count
        
        print(f"📊 TTS segments: {tts_count}")
        print(f"📊 Manual audio: {manual_count}")

    def _on_history_selected(self, text: str) -> None:
        """
        Callback khi chọn item lịch sử
        Đổ text về ô nhập hiện tại
        """
        self.text_input_edge_tts.setPlainText(text)
        self.text_input_edge_tts.setFocus()

    def _reset_seeking_flag(self) -> None:
        """
        Reset flag seeking sau khi seek hoàn thành
        """
        self.seeking = False
    
    def _should_start_loop(self) -> bool:
        """
        Kiểm tra xem có nên bắt đầu loop hay không
        Returns:
            bool: True nếu nên loop, False nếu chưa
        """
        if not self.chk_loop.isChecked():
            return False
        
        # Tính toán vị trí global hiện tại
        current_global_pos = self.get_global_position_ms()
        total_duration = self.total_known_ms
        
        # Chỉ loop khi đã phát hết hoàn toàn (vị trí >= tổng thời lượng)
        should_loop = current_global_pos >= total_duration
        
        return should_loop

    # ==================== Các phương thức xử lý sự kiện ====================

    def on_open_file(self) -> None:
        """
        Mở file văn bản và đọc nội dung
        """
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file văn bản", "", "Text Files (*.txt);;All Files (*)")
        if not path:
            return
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.text_input_edge_tts.setPlainText(f.read())
            self.lbl_status.setText(f"📄 Đã mở: {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không đọc được file: {e}")

    def on_add_audio_file(self) -> None:
        """
        Thêm file audio vào cuối danh sách segments
        """
        # Chọn file audio
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file audio để thêm", "", 
            "Audio Files (*.mp3 *.wav *.m4a *.ogg *.flac);;MP3 Files (*.mp3);;WAV Files (*.wav);;All Files (*)")
        
        if not path:
            return
        
        try:
            # Lấy duration của file audio
            duration_ms = get_mp3_duration_ms(path)
            if duration_ms <= 0:
                QMessageBox.warning(self, "Lỗi", "Không thể đọc được thời lượng của file audio")
                return
            
            # Thêm vào cuối danh sách
            self.segment_paths.append(path)
            self.segment_durations.append(duration_ms)
            
            # Cập nhật tổng thời lượng
            self.total_known_ms = sum(d or 0 for d in self.segment_durations)
            
            # Cập nhật slider range
            self.slider.setRange(0, max(0, self.total_known_ms))
            
            # Tạo text hiển thị cho segment mới
            segment_index = len(self.segment_paths)
            line = f"{segment_index:03d}. {os.path.basename(path)}  —  {ms_to_mmss(duration_ms)} (Thêm thủ công)"
            
            # Thêm vào list segments
            self.list_segments.addItem(QListWidgetItem(line))
            
            # Cập nhật label thời gian
            self.update_time_label(
                self.get_global_position_ms(), self.total_known_ms)
            
            # Thông báo thành công
            self.lbl_status.setText(f"✅ Đã thêm audio: {os.path.basename(path)} ({ms_to_mmss(duration_ms)})")
            

            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể thêm file audio: {e}")
            print(f"❌ Error adding audio file: {e}")

    def on_remove_selected_segment(self) -> None:
        """
        Xóa segment được chọn trong list
        """
        current_row = self.list_segments.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Thông báo", "Vui lòng chọn segment cần xóa")
            return
        
        if current_row >= len(self.segment_paths):
            QMessageBox.warning(self, "Lỗi", "Segment không hợp lệ")
            return
        
        # Xác nhận xóa
        segment_name = os.path.basename(self.segment_paths[current_row]) if self.segment_paths[current_row] else f"Segment {current_row + 1}"
        reply = QMessageBox.question(
            self, "Xác nhận xóa", 
            f"Bạn có chắc muốn xóa segment:\n{segment_name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Xóa segment
                removed_path = self.segment_paths.pop(current_row)
                removed_duration = self.segment_durations.pop(current_row)
                
                # Xóa item khỏi list widget
                self.list_segments.takeItem(current_row)
                
                # Cập nhật tổng thời lượng
                self.total_known_ms = sum(d or 0 for d in self.segment_durations)
                
                # Cập nhật slider range
                self.slider.setRange(0, max(0, self.total_known_ms))
                
                # Cập nhật label thời gian
                self.update_time_label(
                    self.get_global_position_ms(), self.total_known_ms)
                
                # Nếu đang phát segment bị xóa, dừng phát
                if self.current_index == current_row:
                    self.player.stop()
                    self.timer.stop()
                    self.is_playing = False
                    self.btn_playpause.setText("▶️")
                    self.current_index = -1
                elif self.current_index > current_row:
                    # Điều chỉnh current_index nếu cần
                    self.current_index -= 1
                
                # Thông báo thành công
                self.lbl_status.setText(f"🗑️ Đã xóa segment: {os.path.basename(removed_path)}")
                
                
                
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể xóa segment: {e}")
                print(f"❌ Error removing segment: {e}")

    def on_reorder_segments(self) -> None:
        """
        Sắp xếp lại thứ tự segments
        """
        if len(self.segment_paths) < 2:
            QMessageBox.information(self, "Thông báo", "Cần ít nhất 2 segments để sắp xếp")
            return
        
        try:
            # Tạo dialog để sắp xếp
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QLabel
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Sắp xếp Segments")
            dialog.setModal(True)
            dialog.resize(500, 400)
            
            layout = QVBoxLayout(dialog)
            
            # Label hướng dẫn
            layout.addWidget(QLabel("Kéo thả để sắp xếp lại thứ tự segments:"))
            
            # List widget để sắp xếp
            reorder_list = QListWidget()
            reorder_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
            
            # Thêm tất cả segments vào list
            for i, (path, duration) in enumerate(zip(self.segment_paths, self.segment_durations)):
                if path and duration:
                    item_text = f"{i+1:02d}. {os.path.basename(path)} — {ms_to_mmss(duration)}"
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.UserRole, i)  # Lưu index gốc
                    reorder_list.addItem(item)
            
            layout.addWidget(reorder_list)
            
            # Buttons
            btn_layout = QHBoxLayout()
            btn_ok = QPushButton("✅ Áp dụng")
            btn_cancel = QPushButton("❌ Hủy")
            
            btn_ok.clicked.connect(dialog.accept)
            btn_cancel.clicked.connect(dialog.reject)
            
            btn_layout.addWidget(btn_ok)
            btn_layout.addWidget(btn_cancel)
            layout.addLayout(btn_layout)
            
            # Hiển thị dialog
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Lấy thứ tự mới
                new_order = []
                for i in range(reorder_list.count()):
                    item = reorder_list.item(i)
                    original_index = item.data(Qt.UserRole)
                    new_order.append(original_index)
                
                # Sắp xếp lại segments theo thứ tự mới
                new_paths = [self.segment_paths[i] for i in new_order]
                new_durations = [self.segment_durations[i] for i in new_order]
                
                # Cập nhật danh sách
                self.segment_paths = new_paths
                self.segment_durations = new_durations
                
                # Cập nhật tổng thời lượng
                self.total_known_ms = sum(d or 0 for d in self.segment_durations)
                
                # Cập nhật slider range
                self.slider.setRange(0, max(0, self.total_known_ms))
                
                # Cập nhật list widget
                self.list_segments.clear()
                for i, (path, duration) in enumerate(zip(self.segment_paths, self.segment_durations)):
                    if path and duration:
                        line = f"{i+1:03d}. {os.path.basename(path)}  —  {ms_to_mmss(duration)}"
                        self.list_segments.addItem(QListWidgetItem(line))
                
                # Cập nhật label thời gian
                self.update_time_label(
                    self.get_global_position_ms(), self.total_known_ms)
                
                # Thông báo thành công
                self.lbl_status.setText("🔄 Đã sắp xếp lại segments")
                

                
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể sắp xếp segments: {e}")
            print(f"❌ Error reordering segments: {e}")

    def on_test_loop(self) -> None:
        """
        Test loop condition một cách thủ công
        """
        if not self.segment_paths or not any(self.segment_paths):
            QMessageBox.information(self, "Thông báo", "Chưa có segments để test loop")
            return
        
        # Kiểm tra điều kiện loop
        should_loop = self._should_start_loop()
        
        # Hiển thị thông tin chi tiết
        current_pos = self.get_global_position_ms()
        total_dur = self.total_known_ms
        
        info_text = f"🔍 Loop Test Results:\n\n"
        info_text += f"Current Position: {current_pos}ms ({ms_to_mmss(current_pos)})\n"
        info_text += f"Total Duration: {total_dur}ms ({ms_to_mmss(total_dur)})\n"
        info_text += f"Loop Enabled: {self.chk_loop.isChecked()}\n"
        info_text += f"Should Loop: {should_loop}\n\n"
        
        if should_loop:
            info_text += "✅ Điều kiện loop đã thỏa mãn!\n"
            info_text += "Có thể bắt đầu loop từ segment đầu tiên."
        else:
            info_text += "⏸️ Chưa đủ điều kiện để loop.\n"
            info_text += f"Cần phát thêm {total_dur - current_pos}ms nữa."
        
        QMessageBox.information(self, "Loop Test", info_text)
        


    def on_start(self) -> None:
        """
        Bắt đầu xử lý TTS
        """
        # Dừng worker cũ nếu đang chạy
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        
        # Reset player và timer
        self.player.stop()
        self.timer.stop()
        self.is_playing = False
        self.btn_playpause.setText("▶")
        
        # Reset danh sách segments
        self.segment_paths.clear()
        self.segment_durations.clear()
        self.total_known_ms = 0
        self.current_index = -1
        self.seeking = False
        self.list_segments.clear()
        self.slider.setRange(0, 0)
        self.update_time_label(0, 0)
        self.progress_gen.setValue(0)
        self.lbl_status.setText("Sẵn sàng")

        # Kiểm tra văn bản đầu vào
        text = self.text_input_edge_tts.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Thiếu nội dung",
                                "Dán hoặc mở file .txt trước khi bắt đầu.")
            return

        # Tạo worker mới
        self.worker = MTProducerWorker(
            text, "vi-VN-HoaiMyNeural", 0, 0, 500, 4)
        
        # Kết nối signals
        self.worker.segment_ready.connect(self.on_segment_ready)
        self.worker.progress.connect(self.on_produce_progress)
        self.worker.status.connect(self.on_status)
        self.worker.all_done.connect(self.on_all_done)
        self.worker.error.connect(self.on_error)

        # Cập nhật UI
        self.btn_start_edge_tts.setEnabled(False)
        self.btn_end_edge_tts.setEnabled(True)
        self.lbl_status.setText(
            f"🔄 Đang sinh audio ({self.theard_edge_tts.value()} luồng)…")
        
        # Bắt đầu worker
        self.worker.start()

    def on_end_all(self) -> None:
        """
        Dừng tất cả quá trình xử lý
        """
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        
        self.player.stop()
        self.timer.stop()
        self.is_playing = False
        self.btn_playpause.setText("▶️")
        self.btn_end_edge_tts.setEnabled(False)
        self.btn_start_edge_tts.setEnabled(True)
        self.lbl_status.setText("⏹ Đã kết thúc.")

    # ==================== Worker callbacks ====================

    def on_segment_ready(self, path: str, duration_ms: int, index1: int) -> None:
        """
        Callback khi một segment audio được tạo xong
        """
        self._ensure_capacity(index1)
        self.segment_paths[index1 - 1] = path
        self.segment_durations[index1 - 1] = duration_ms

        # Cập nhật tổng thời lượng
        self.total_known_ms = sum(d or 0 for d in self.segment_durations)
        

        
        # Tạo text hiển thị cho segment
        line = f"{index1:03d}. {os.path.basename(path)}  —  {ms_to_mmss(duration_ms)}"
        
        # Cập nhật list segments
        if index1 - 1 < self.list_segments.count():
            self.list_segments.item(index1 - 1).setText(line)
        else:
            # Thêm placeholder cho các segment chưa hoàn thành
            while self.list_segments.count() < index1 - 1:
                self.list_segments.addItem(QListWidgetItem("(đang tạo...)"))
            self.list_segments.addItem(QListWidgetItem(line))

        # Cập nhật slider range
        self.slider.setRange(0, max(0, self.total_known_ms))
        
        self.update_time_label(
            self.get_global_position_ms(), self.total_known_ms)

        # Tự động phát segment đầu tiên nếu chưa có gì đang phát
        if self.current_index < 0 and self.segment_paths and self.segment_paths[0]:
            self.play_segment(0)

    def on_produce_progress(self, emitted: int, total: int) -> None:
        """
        Callback tiến trình xử lý
        """
        self.progress_gen.setValue(int(emitted / total * 100))

    def on_status(self, msg: str) -> None:
        """
        Callback thông báo trạng thái
        """
        self.lbl_status.setText(msg)

    def on_all_done(self) -> None:
        """
        Callback khi hoàn thành tất cả
        """
        self.lbl_status.setText(self.lbl_status.text() + "  ✅ Xong.")
        self.btn_start_edge_tts.setEnabled(True)
        self.btn_end_edge_tts.setEnabled(False)
        
        if self.player.playbackState() != QMediaPlayer.PlayingState:
            self.is_playing = False
            self.btn_playpause.setText("▶")

    def on_error(self, msg: str) -> None:
        """
        Callback khi có lỗi
        """
        QMessageBox.critical(self, "Lỗi", msg)
        self.btn_end_edge_tts.setEnabled(False)
        self.btn_start_edge_tts.setEnabled(True)

    # ==================== Player controls ====================

    def play_segment(self, idx: int, pos_in_segment_ms: int = 0) -> None:
        """
        Phát một segment cụ thể
        Args:
            idx: Index của segment
            pos_in_segment_ms: Vị trí trong segment (ms)
        """
        if idx < 0 or idx >= len(self.segment_paths):
            print(f"❌ Invalid segment index: {idx}")
            return
        
        path = self.segment_paths[idx]
        if not path:
            print(f"❌ No path for segment[{idx}]")
            return
        
        # Lấy thông tin segment
        segment_duration = self.segment_durations[idx] or 0
        
        # Kiểm tra vị trí seek có hợp lệ không
        if pos_in_segment_ms >= segment_duration:
            pos_in_segment_ms = max(0, segment_duration - 1)
        
        # Cập nhật trạng thái
        self.current_index = idx
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.setPosition(max(0, pos_in_segment_ms))
        self.player.play()
        self.timer.start()
        self.is_playing = True
        self.btn_playpause.setText("⏹")
        
        # Highlight segment trong list
        self.list_segments.setCurrentRow(idx)
        


    def play_next(self) -> None:
        """
        Phát segment tiếp theo
        """
        i = self.current_index + 1
        while i < len(self.segment_paths) and not self.segment_paths[i]:
            i += 1
        
        if i < len(self.segment_paths):
            self.play_segment(i, 0)
        else:
            # Kiểm tra loop - chỉ loop khi đã phát hết tất cả segments
            if self._should_start_loop():
                idx0 = next((k for k, p in enumerate(self.segment_paths) if p), None)
                if idx0 is not None:
                    self.play_segment(idx0, 0)
                    return
            
            # Không còn gì để phát hoặc không loop
            self.is_playing = False
            self.btn_playpause.setText("▶️")

    def play_prev(self) -> None:
        """
        Phát segment trước đó
        """
        i = self.current_index - 1
        while i >= 0 and not self.segment_paths[i]:
            i -= 1
        
        if i >= 0:
            self.play_segment(i, 0)
        else:
            self.player.setPosition(0)

    def toggle_playpause(self) -> None:
        """
        Toggle play/pause
        """
        if not self.is_playing:
            if self.current_index < 0 and any(self.segment_paths):
                # Bắt đầu phát từ segment đầu tiên
                idx0 = next((i for i, p in enumerate(self.segment_paths) if p), None)
                if idx0 is not None:
                    self.play_segment(idx0, 0)
            else:
                # Tiếp tục phát
                self.player.play()
                self.is_playing = True
                self.btn_playpause.setText("⏹")
        else:
            # Dừng phát
            self.player.stop()
            self.timer.stop()
            self.is_playing = False
            self.btn_playpause.setText("▶️")

    # ==================== Media player callbacks ====================

    def on_media_status_changed(self, status) -> None:
        """
        Callback khi trạng thái media thay đổi
        """
        if status == QMediaPlayer.EndOfMedia:
            self.play_next()

    def on_media_error(self, err) -> None:
        """
        Callback khi có lỗi media
        """
        self.lbl_status.setText(
            f"⚠️ Lỗi phát: {self.player.errorString() or str(err)}")
        self.play_next()

    def on_player_position_changed(self, pos_ms: int) -> None:
        """
        Callback khi vị trí player thay đổi
        """
        if not self.seeking:
            self.update_timeline()

    def on_playback_state_changed(self, state) -> None:
        """
        Callback khi trạng thái playback thay đổi
        """
        if state == QMediaPlayer.StoppedState:
            # Kiểm tra xem có phải segment cuối cùng không
            if self.current_index + 1 >= len(self.segment_paths):
                if self._should_start_loop():
                    self.play_next()
                    return
                
                # Không loop hoặc chưa đủ điều kiện loop
                self.is_playing = False
                self.btn_playpause.setText("▶")

    # ==================== Timeline controls ====================

    def update_timeline(self) -> None:
        """
        Cập nhật timeline dựa trên vị trí hiện tại
        """
        if self.current_index < 0:
            return
        
        # Nếu đang seeking, không cập nhật timeline
        if self.seeking:
            # print(f"⏰ Timeline update SKIPPED - seeking in progress")
            return
        
        # Kiểm tra thời gian seek cuối cùng để bảo vệ timeline
        import time
        current_time = time.time()
        if current_time - self._last_seek_time < 2.0:  # Tăng bảo vệ lên 2 giây sau khi seek
            # print(f"⏰ Timeline update SKIPPED - seek protection active ({(current_time - self._last_seek_time):.2f}s ago)")
            return
        
        # Tính vị trí global
        offset = sum((d or 0) for d in self.segment_durations[:self.current_index])
        player_pos = self.player.position()
        current_pos = offset + player_pos
        

        
        # Cập nhật slider (block signals để tránh loop)
        self.slider.blockSignals(True)
        self.slider.setValue(current_pos)
        self.slider.blockSignals(False)
        
        # Cập nhật label thời gian
        self.update_time_label(current_pos, self.total_known_ms)

    def on_slider_pressed(self) -> None:
        """Slider được nhấn"""
        # Bật flag seeking để tránh update timeline
        self.seeking = True
        
        # Cập nhật thời gian seek để bảo vệ timeline
        import time
        self._last_seek_time = time.time()

    def on_slider_moved(self, value: int) -> None:
        """Slider được kéo"""
        # Cập nhật giá trị seek pending
        self._pending_seek_value = value
        
        # Khởi động debounce timer
        self.seek_debounce.start()
        
        # Đảm bảo seeking flag được bật
        if not self.seeking:
            self.seeking = True
            
            # Cập nhật thời gian seek để bảo vệ timeline
            import time
            self._last_seek_time = time.time()

    def on_slider_released(self) -> None:
        """Slider được thả"""
        # Nếu có debounce timer đang chạy, dừng nó và áp dụng seek
        if self.seek_debounce.isActive():
            self.seek_debounce.stop()
            self.apply_seek_target()
        
        # Giữ flag seeking lâu hơn để tránh timeline update ghi đè
        QTimer.singleShot(800, self._reset_seeking_flag)

    def on_slider_clicked(self, value: int) -> None:
        """Slider được click (từ ClickSlider)"""
        # Bật flag seeking để tránh timeline update ghi đè
        self.seeking = True
        
        # Cập nhật thời gian seek để bảo vệ timeline
        import time
        self._last_seek_time = time.time()
        
        # Kiểm tra xem có segments để seek không
        if not self.segment_durations or not any(self.segment_durations):
            self.seeking = False
            return
        
        self._pending_seek_value = value
        
        # Áp dụng seek ngay lập tức
        self.apply_seek_target()
        
        # Giữ flag seeking lâu hơn để tránh timeline update ghi đè
        # Sẽ reset sau khi player đã seek xong và ổn định
        QTimer.singleShot(800, self._reset_seeking_flag)

    def apply_seek_target(self) -> None:
        """
        Áp dụng seek đến vị trí mục tiêu
        """
        if self._pending_seek_value is None:
            return
        
        target = self._pending_seek_value
        self._pending_seek_value = None
        
        # Map vị trí global về segment và vị trí local
        idx, local = self.map_global_to_local(target)
        if idx is not None:
            # Cập nhật slider position để tránh nhảy về đầu
            self.slider.blockSignals(True)
            self.slider.setValue(target)
            self.slider.blockSignals(False)
            
            # Phát segment tại vị trí local
            self.play_segment(idx, local)
            
            # Cập nhật label thời gian
            self.update_time_label(target, self.total_known_ms)
            
            # Giữ seeking flag lâu hơn để tránh timeline update ghi đè
            # Sẽ reset sau khi player đã seek xong và ổn định
            QTimer.singleShot(1000, self._reset_seeking_flag)
        else:
            # Reset seeking flag ngay nếu seek thất bại
            self.seeking = False

    def map_global_to_local(self, global_ms: int) -> tuple:
        """
        Map vị trí global (từ slider) về segment index và vị trí local
        Returns:
            tuple: (segment_index, local_position_ms) hoặc (None, None) nếu không tìm thấy
        """
        # Nếu không có segments, trả về None
        if not self.segment_durations or not any(self.segment_durations):
            return None, None
        
        # Tính tổng thời lượng
        total_duration = sum(d or 0 for d in self.segment_durations)
        
        # Nếu vị trí vượt quá tổng thời lượng, giới hạn lại
        if global_ms >= total_duration:
            global_ms = total_duration - 1
        
        # Nếu vị trí nhỏ hơn 0, giới hạn lại
        if global_ms < 0:
            global_ms = 0
        
        # Tìm segment chứa vị trí global
        acc = 0
        for i, d in enumerate(self.segment_durations):
            d = d or 0
            segment_start = acc
            segment_end = acc + d
            
            # Kiểm tra xem global_ms có nằm trong segment này không
            if segment_start <= global_ms < segment_end:
                local_pos = global_ms - segment_start
                return i, local_pos
            
            acc += d
        
        # Nếu không tìm thấy (hiếm khi xảy ra), trả về segment cuối cùng
        last_idx = len(self.segment_durations) - 1
        last_dur = self.segment_durations[last_idx] or 0
        return last_idx, max(0, last_dur - 1)

    def get_global_position_ms(self) -> int:
        """
        Lấy vị trí global hiện tại (ms)
        """
        if self.current_index < 0:
            return 0
        
        offset = sum((d or 0) for d in self.segment_durations[:self.current_index])
        current_pos = offset + self.player.position()
        
        return current_pos

    def update_time_label(self, cur_ms: int, total_ms: int) -> None:
        """
        Cập nhật label hiển thị thời gian
        """
        self.lbl_time.setText(f"{ms_to_mmss(cur_ms)} / {ms_to_mmss(total_ms)}")

    def on_list_item_double_clicked(self, item) -> None:
        """
        Callback khi double click vào item trong list segments
        Phát audio file tương ứng
        """
        row = self.list_segments.row(item)
        if 0 <= row < len(self.segment_paths) and self.segment_paths[row]:
            self.play_segment(row, 0)

    # ==================== Export MP3 ====================

    def on_export_mp3(self) -> None:
        """
        Xuất file MP3 từ các segments
        """
        parts = [p for p in self.segment_paths if p]
        if not parts:
            QMessageBox.information(
                self, "Chưa có dữ liệu", "Chưa có đoạn nào để xuất.")
            return

        # Chọn nơi lưu file
        default_name = f"Player_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Chọn nơi lưu MP3", str(OUTPUT_DIR / default_name), "MP3 Files (*.mp3)"
        )
        if not out_path:
            return

        try:
            prepare_pydub_ffmpeg()
            gap_ms = self.gap_spin_edge_tts.value()
            gap = AudioSegment.silent(duration=gap_ms)
            final = AudioSegment.silent(duration=0)

            total_ms = 0
            valid_count = 0
            
            # Ghép các segments
            for p in parts:
                try:
                    seg = AudioSegment.from_file(p)
                    final += seg + gap
                    d = get_mp3_duration_ms(p)
                    total_ms += d
                    valid_count += 1
                except Exception:
                    pass

            if valid_count == 0:
                QMessageBox.warning(self, "Xuất thất bại",
                                    "Không ghép được dữ liệu hợp lệ.")
                return

            # Xuất file MP3
            final.export(out_path, format="mp3")
            QMessageBox.information(
                self, "Thành công", f"Đã xuất MP3:\n{out_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Lỗi xuất", f"Không thể xuất MP3:\n{e}")

    def stop_all(self) -> None:
        """
        Dừng tất cả quá trình
        """
        # Ngừng worker TTS
        if getattr(self, "worker", None) and self.worker.isRunning():
            try:
                self.worker.stop()
                # Đợi worker dừng hoàn toàn
                if self.worker.wait(3000):  # Đợi tối đa 3 giây
                    pass
                else:
                    self.worker.terminate()
                    self.worker.wait(1000)
            except Exception:
                pass
        
        # Ngừng player/timer
        try:
            self.player.stop()
        except Exception:
            pass
        
        if getattr(self, "timer", None) and self.timer.isActive():
            self.timer.stop()
        
        # Xóa file tạm
        try:
            clean_all_temp_parts()
        except Exception:
            pass
        
        # Cập nhật UI
        self.is_playing = False
        if hasattr(self, "btn_playpause"):
            self.btn_playpause.setText("▶️")

    def closeEvent(self, event) -> None:
        """
        Xử lý sự kiện đóng tab
        """
        self.stop_all()
        super().closeEvent(event)
