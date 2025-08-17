# -*- coding: utf-8 -*-
"""
Audio Player Class - Class tái sử dụng để phát âm thanh
Cung cấp các chức năng cơ bản để phát, dừng, seek audio
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider, QCheckBox
from PySide6.QtCore import Qt, QTimer, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from typing import Optional, List, Tuple
import os
import time

from app.utils.helps import ms_to_mmss


class ClickSlider(QSlider):
    """
    Slider cải tiến cho phép click vào bất kỳ vị trí nào để seek ngay lập tức
    """
    clickedValue = Signal(int)

    def mousePressEvent(self, event) -> None:
        if event.button() in (Qt.LeftButton, Qt.RightButton):
            ratio = event.position().x() / max(1, self.width())
            ratio = max(0.0, min(1.0, ratio))
            vmin, vmax = self.minimum(), self.maximum()
            value = int(vmin + ratio * (vmax - vmin))
            self.setValue(value)
            self.clickedValue.emit(value)
        super().mousePressEvent(event)


class AudioPlayer(QWidget):
    """
    Class Audio Player có thể tái sử dụng
    Cung cấp giao diện và chức năng phát âm thanh cơ bản
    """
    
    # Signals
    position_changed = Signal(int)  # Vị trí hiện tại (ms)
    duration_changed = Signal(int)  # Tổng thời lượng (ms)
    playback_state_changed = Signal(bool)  # Trạng thái phát (True = đang phát)
    segment_changed = Signal(int)  # Segment hiện tại
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Khởi tạo biến trạng thái
        self.segment_paths: List[Optional[str]] = []
        self.segment_durations: List[Optional[int]] = []
        self.total_known_ms: int = 0
        self.current_index: int = -1
        self.seeking: bool = False
        self.is_playing: bool = False
        
        # Giá trị seek pending
        self._pending_seek_value: Optional[int] = None
        self._last_seek_time: float = 0.0
        
        # Thiết lập giao diện
        self._setup_ui()
        
        # Thiết lập hệ thống audio
        self._setup_audio_system()
        
        # Thiết lập timer và kết nối tín hiệu
        self._setup_timers_and_connections()

    def _setup_ui(self):
        """Thiết lập giao diện cơ bản"""
        layout = QVBoxLayout(self)
        
        # Player controls
        controls_layout = QHBoxLayout()
        
        self.btn_prev = QPushButton("⏮")
        self.btn_prev.clicked.connect(self.play_prev)
        
        self.btn_playpause = QPushButton("▶️")
        self.btn_playpause.clicked.connect(self.toggle_playpause)
        
        self.btn_next = QPushButton("⏭")
        self.btn_next.clicked.connect(self.play_next)
        
        # Slider timeline
        self.slider = ClickSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        
        # Label thời gian
        self.lbl_time = QLabel("00:00 / 00:00")
        
        # Checkbox lặp lại
        self.chk_loop = QCheckBox("🔁 Lặp lại")
        self.chk_loop.setChecked(True)
        
        # Thêm controls vào layout
        controls_layout.addWidget(self.btn_prev)
        controls_layout.addWidget(self.btn_playpause)
        controls_layout.addWidget(self.btn_next)
        controls_layout.addWidget(self.slider, 1)
        controls_layout.addWidget(self.lbl_time)
        controls_layout.addWidget(self.chk_loop)
        
        layout.addLayout(controls_layout)
        
        # Status label
        self.lbl_status = QLabel("Sẵn sàng")
        self.lbl_status.setStyleSheet("color: #888; font-size: 12px; padding: 5px;")
        layout.addWidget(self.lbl_status)

    def _setup_audio_system(self):
        """Thiết lập hệ thống audio"""
        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)

    def _setup_timers_and_connections(self):
        """Thiết lập timer và kết nối các tín hiệu"""
        # Timer cập nhật timeline
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_timeline)
        
        # Kết nối tín hiệu player
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.player.errorOccurred.connect(self.on_media_error)
        self.player.positionChanged.connect(self.on_player_position_changed)
        self.player.playbackStateChanged.connect(self.on_playback_state_changed)
        
        # Timer debounce cho seek
        self.seek_debounce = QTimer(self)
        self.seek_debounce.setInterval(150)
        self.seek_debounce.setSingleShot(True)
        self.seek_debounce.timeout.connect(self.apply_seek_target)
        
        # Kết nối slider signals
        self.slider.sliderPressed.connect(self.on_slider_pressed)
        self.slider.sliderMoved.connect(self.on_slider_moved)
        self.slider.sliderReleased.connect(self.on_slider_released)
        self.slider.clickedValue.connect(self.on_slider_clicked)

    # ==================== Public Methods ====================
    
    def add_segments(self, paths: List[str], durations: List[int]):
        """Thêm danh sách segments"""
        self.segment_paths = paths.copy()
        self.segment_durations = durations.copy()
        self.total_known_ms = sum(d or 0 for d in self.segment_durations)
        self.slider.setRange(0, max(0, self.total_known_ms))
        self.update_time_label(0, self.total_known_ms)
        self.lbl_status.setText(f"Đã tải {len(paths)} segments")

    def clear_segments(self):
        """Xóa tất cả segments"""
        self.stop()
        self.segment_paths.clear()
        self.segment_durations.clear()
        self.total_known_ms = 0
        self.current_index = -1
        self.slider.setRange(0, 0)
        self.update_time_label(0, 0)
        self.lbl_status.setText("Sẵn sàng")

    def play(self):
        """Bắt đầu phát"""
        if not self.segment_paths:
            return
        
        if self.current_index < 0:
            # Bắt đầu từ segment đầu tiên
            self.play_segment(0, 0)
        else:
            # Tiếp tục phát
            self.player.play()
            self.is_playing = True
            self.btn_playpause.setText("⏹")
            self.timer.start()

    def stop(self):
        """Dừng phát"""
        self.player.stop()
        self.timer.stop()
        self.is_playing = False
        self.btn_playpause.setText("▶️")

    def pause(self):
        """Tạm dừng"""
        if self.is_playing:
            self.player.pause()
            self.timer.stop()
            self.is_playing = False
            self.btn_playpause.setText("▶️")

    def seek_to(self, global_ms: int):
        """Seek đến vị trí cụ thể"""
        if not self.segment_paths:
            return
        
        self._pending_seek_value = global_ms
        self.apply_seek_target()

    def get_current_position(self) -> int:
        """Lấy vị trí hiện tại (ms)"""
        return self.get_global_position_ms()

    def get_total_duration(self) -> int:
        """Lấy tổng thời lượng (ms)"""
        return self.total_known_ms

    def is_audio_playing(self) -> bool:
        """Kiểm tra xem có đang phát audio không"""
        return self.is_playing

    # ==================== Private Methods ====================
    
    def _should_start_loop(self) -> bool:
        """Kiểm tra xem có nên bắt đầu loop hay không"""
        if not self.chk_loop.isChecked():
            return False
        
        current_global_pos = self.get_global_position_ms()
        return current_global_pos >= self.total_known_ms

    def _reset_seeking_flag(self):
        """Reset flag seeking sau khi seek hoàn thành"""
        self.seeking = False

    def get_global_position_ms(self) -> int:
        """Lấy vị trí global hiện tại (ms)"""
        if self.current_index < 0:
            return 0
        
        offset = sum((d or 0) for d in self.segment_durations[:self.current_index])
        current_pos = offset + self.player.position()
        return current_pos

    def update_time_label(self, cur_ms: int, total_ms: int):
        """Cập nhật label hiển thị thời gian"""
        self.lbl_time.setText(f"{ms_to_mmss(cur_ms)} / {ms_to_mmss(total_ms)}")

    def play_segment(self, idx: int, pos_in_segment_ms: int = 0):
        """Phát một segment cụ thể"""
        if idx < 0 or idx >= len(self.segment_paths):
            return
        
        path = self.segment_paths[idx]
        if not path:
            return
        
        # Kiểm tra vị trí seek có hợp lệ không
        segment_duration = self.segment_durations[idx] or 0
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
        
        # Phát signal
        self.segment_changed.emit(idx)

    def play_next(self):
        """Phát segment tiếp theo"""
        i = self.current_index + 1
        while i < len(self.segment_paths) and not self.segment_paths[i]:
            i += 1
        
        if i < len(self.segment_paths):
            self.play_segment(i, 0)
        else:
            # Kiểm tra loop
            if self._should_start_loop():
                idx0 = next((k for k, p in enumerate(self.segment_paths) if p), None)
                if idx0 is not None:
                    self.play_segment(idx0, 0)
                    return
            
            # Không còn gì để phát
            self.is_playing = False
            self.btn_playpause.setText("▶️")

    def play_prev(self):
        """Phát segment trước đó"""
        i = self.current_index - 1
        while i >= 0 and not self.segment_paths[i]:
            i -= 1
        
        if i >= 0:
            self.play_segment(i, 0)
        else:
            self.player.setPosition(0)

    def toggle_playpause(self):
        """Toggle play/pause"""
        if not self.is_playing:
            if self.current_index < 0 and any(self.segment_paths):
                # Bắt đầu phát từ segment đầu tiên
                idx0 = next((i for i, p in enumerate(self.segment_paths) if p), None)
                if idx0 is not None:
                    self.play_segment(idx0, 0)
            else:
                # Tiếp tục phát
                self.play()
        else:
            # Tạm dừng
            self.pause()

    def map_global_to_local(self, global_ms: int) -> Tuple[Optional[int], Optional[int]]:
        """Map vị trí global về segment index và vị trí local"""
        if not self.segment_durations or not any(self.segment_durations):
            return None, None
        
        # Giới hạn vị trí
        total_duration = sum(d or 0 for d in self.segment_durations)
        if global_ms >= total_duration:
            global_ms = total_duration - 1
        if global_ms < 0:
            global_ms = 0
        
        # Tìm segment chứa vị trí global
        acc = 0
        for i, d in enumerate(self.segment_durations):
            d = d or 0
            segment_start = acc
            segment_end = acc + d
            
            if segment_start <= global_ms < segment_end:
                local_pos = global_ms - segment_start
                return i, local_pos
            
            acc += d
        
        # Fallback: segment cuối cùng
        last_idx = len(self.segment_durations) - 1
        last_dur = self.segment_durations[last_idx] or 0
        return last_idx, max(0, last_dur - 1)

    def apply_seek_target(self):
        """Áp dụng seek đến vị trí mục tiêu"""
        if self._pending_seek_value is None:
            return
        
        target = self._pending_seek_value
        self._pending_seek_value = None
        
        # Map vị trí global về segment và vị trí local
        idx, local = self.map_global_to_local(target)
        if idx is not None:
            # Cập nhật slider position
            self.slider.blockSignals(True)
            self.slider.setValue(target)
            self.slider.blockSignals(False)
            
            # Phát segment tại vị trí local
            self.play_segment(idx, local)
            
            # Cập nhật label thời gian
            self.update_time_label(target, self.total_known_ms)
            
            # Giữ seeking flag lâu hơn
            QTimer.singleShot(1000, self._reset_seeking_flag)
        else:
            self.seeking = False

    def update_timeline(self):
        """Cập nhật timeline dựa trên vị trí hiện tại"""
        if self.current_index < 0 or self.seeking:
            return
        
        # Kiểm tra thời gian seek cuối cùng
        current_time = time.time()
        if current_time - self._last_seek_time < 2.0:
            return
        
        # Tính vị trí global
        offset = sum((d or 0) for d in self.segment_durations[:self.current_index])
        player_pos = self.player.position()
        current_pos = offset + player_pos
        
        # Cập nhật slider
        self.slider.blockSignals(True)
        self.slider.setValue(current_pos)
        self.slider.blockSignals(False)
        
        # Cập nhật label thời gian
        self.update_time_label(current_pos, self.total_known_ms)
        
        # Phát signal
        self.position_changed.emit(current_pos)

    # ==================== Slider Event Handlers ====================
    
    def on_slider_pressed(self):
        """Slider được nhấn"""
        self.seeking = True
        self._last_seek_time = time.time()

    def on_slider_moved(self, value: int):
        """Slider được kéo"""
        self._pending_seek_value = value
        self.seek_debounce.start()
        
        if not self.seeking:
            self.seeking = True
            self._last_seek_time = time.time()

    def on_slider_released(self):
        """Slider được thả"""
        if self.seek_debounce.isActive():
            self.seek_debounce.stop()
            self.apply_seek_target()
        
        QTimer.singleShot(800, self._reset_seeking_flag)

    def on_slider_clicked(self, value: int):
        """Slider được click"""
        self.seeking = True
        self._last_seek_time = time.time()
        
        if not self.segment_durations or not any(self.segment_durations):
            self.seeking = False
            return
        
        self._pending_seek_value = value
        self.apply_seek_target()
        QTimer.singleShot(800, self._reset_seeking_flag)

    # ==================== Media Player Callbacks ====================
    
    def on_media_status_changed(self, status):
        """Callback khi trạng thái media thay đổi"""
        if status == QMediaPlayer.EndOfMedia:
            self.play_next()

    def on_media_error(self, err):
        """Callback khi có lỗi media"""
        self.lbl_status.setText(f"⚠️ Lỗi phát: {self.player.errorString() or str(err)}")
        self.play_next()

    def on_player_position_changed(self, pos_ms: int):
        """Callback khi vị trí player thay đổi"""
        if not self.seeking:
            self.update_timeline()

    def on_playback_state_changed(self, state):
        """Callback khi trạng thái playback thay đổi"""
        if state == QMediaPlayer.StoppedState:
            # Kiểm tra xem có phải segment cuối cùng không
            if self.current_index + 1 >= len(self.segment_paths):
                if self._should_start_loop():
                    self.play_next()
                    return
                
                # Không loop hoặc chưa đủ điều kiện loop
                self.is_playing = False
                self.btn_playpause.setText("▶️")
        
        # Phát signal
        self.playback_state_changed.emit(self.is_playing)
