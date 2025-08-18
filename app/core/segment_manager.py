# -*- coding: utf-8 -*-
"""
Segment Manager - Quản lý audio segments cho TTS Tab
"""

from PySide6.QtWidgets import QListWidget, QListWidgetItem, QMessageBox, QWidget, QHBoxLayout, QLabel, QGridLayout, QSizePolicy
from PySide6.QtCore import QObject, Signal, Qt
from typing import List, Optional, Tuple
import os
from pathlib import Path
import tempfile
from datetime import datetime

from app.appConfig import AppConfig
from app.utils.audio_helpers import ms_to_mmss, get_mp3_duration_ms
from app.utils.helps import hide_directory_on_windows
from pydub import AudioSegment


class ListRow(QWidget):
    """Custom row widget với 3 cột sử dụng QGridLayout"""
    
    def __init__(self, left_text: str, center_text: str, right_text: str):
        super().__init__()
        
        # Set background và border để dễ nhìn - theme terminal
        self.setStyleSheet("""
            QWidget {
                min-height: 20px;
            }
        """)
        
        grid = QGridLayout(self)
        grid.setContentsMargins(8, 6, 8, 6)
        grid.setHorizontalSpacing(12)

        # Tạo labels với styling rõ ràng
        self.lbl_left = QLabel(left_text)
        self.lbl_center = QLabel(center_text)
        self.lbl_right = QLabel(right_text)

        # Styling cho labels - giống terminal với font monospaced
        label_style = """
            QLabel {
                font-size: 14px;
                padding-top: 0px;
                padding-bottom: 8px;
        
            } """ 
        self.lbl_left.setStyleSheet(label_style)
        self.lbl_center.setStyleSheet(label_style)
        self.lbl_right.setStyleSheet(label_style)

        # Căn trái - giữa - phải
        self.lbl_left.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_center.setAlignment(Qt.AlignCenter)
        self.lbl_right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Trung tâm giãn nở, hai bên co
        self.lbl_center.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.lbl_left.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.lbl_right.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)

        # Set minimum width cho các cột
        self.lbl_left.setMinimumWidth(200)
        self.lbl_center.setMinimumWidth(120)
        self.lbl_right.setMinimumWidth(80)

        grid.addWidget(self.lbl_left,   0, 0)
        grid.addWidget(self.lbl_center, 0, 1)
        grid.addWidget(self.lbl_right,  0, 2)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)  # cột giữa ăn hết không gian
        grid.setColumnStretch(2, 0)

    def get_data(self):
        return (self.lbl_left.text(), self.lbl_center.text(), self.lbl_right.text())


class SegmentManager(QObject):
    """
    Quản lý audio segments cho TTS Tab
    """
    
    # Signals
    segments_changed = Signal()  # Khi segments thay đổi
    segment_added = Signal(str, int)  # path, duration
    segment_removed = Signal(int)  # index
    segment_reordered = Signal()
    
    def __init__(self):
        super().__init__()
        
        # Segment data
        self.segment_paths: List[Optional[str]] = []
        self.segment_durations: List[Optional[int]] = []
        self.total_known_ms: int = 0
        
        # UI components (sẽ được set từ TTS Tab)
        self.list_widget: Optional[QListWidget] = None
        self.audio_player = None
        
    def set_ui_components(self, list_widget: QListWidget, audio_player) -> None:
        """Set UI components từ TTS Tab"""
        self.list_widget = list_widget
        self.audio_player = audio_player
        self._setup_list_widget()
        
    def _setup_list_widget(self) -> None:
        """Setup list widget cho hiển thị 3 cột"""
        if not self.list_widget:
            return
            
        # Set list widget properties
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)
        
    def add_custom_row(self, left_text: str, center_text: str, right_text: str) -> None:
        """Thêm custom row với 3 cột vào list widget"""
        if not self.list_widget:
            return
            
        # Tạo custom row widget
        row_widget = ListRow(left_text, center_text, right_text)
        
        # Tạo QListWidgetItem và set widget
        item = QListWidgetItem()
        item.setSizeHint(row_widget.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, row_widget)
        
    def add_segment(self, path: str, duration_ms: int) -> None:
        """Thêm segment mới"""
        self.segment_paths.append(path)
        self.segment_durations.append(duration_ms)
        self._update_total_duration()
        self._update_display()
        self.segment_added.emit(path, duration_ms)
        self.segments_changed.emit()
        
    def remove_segment(self, index: int) -> Tuple[Optional[str], Optional[int]]:
        """Xóa segment tại index"""
        if 0 <= index < len(self.segment_paths):
            removed_path = self.segment_paths.pop(index)
            removed_duration = self.segment_durations.pop(index)
            self._update_total_duration()
            self._update_display()
            self.segment_removed.emit(index)
            self.segments_changed.emit()
            return removed_path, removed_duration
        return None, None
        
    def clear_segments(self) -> None:
        """Xóa tất cả segments"""
        self.segment_paths.clear()
        self.segment_durations.clear()
        self.total_known_ms = 0
        self._update_display()
        self.segments_changed.emit()
        
    def get_valid_segments(self) -> Tuple[List[str], List[int]]:
        """Lấy danh sách segments hợp lệ"""
        valid_paths = [p for p in self.segment_paths if p]
        valid_durations = [d for d in self.segment_durations if d]
        return valid_paths, valid_durations
        
    def add_audio_file(self, path: str) -> bool:
        """Thêm audio file vào segments"""
        try:
            duration_ms = get_mp3_duration_ms(path)
            if duration_ms <= 0:
                return False
                
            self.add_segment(path, duration_ms)
            return True
            
        except Exception as e:
            print(f"Error adding audio file: {e}")
            return False
            
    def add_video_file(self, video_path: str) -> bool:
        """Thêm video file (tạo 3s audio placeholder)"""
        try:
            duration_ms = 3000  # Fixed 3 seconds
            
            # Create silent audio segment for video
            temp_dir = Path(tempfile.mkdtemp(prefix=AppConfig.TEMP_PREFIX))
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Ẩn thư mục tạm sau khi tạo (chỉ trên Windows)
            hide_directory_on_windows(temp_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_audio_path = str(temp_dir / f"video_audio_{timestamp}.mp3")
            
            # Create silent audio for video (3 seconds)
            video_audio = AudioSegment.silent(duration=duration_ms)
            video_audio.export(video_audio_path, format="mp3")
            
            self.add_segment(video_audio_path, duration_ms)
            return True
            
        except Exception as e:
            print(f"Error adding video file: {e}")
            return False
            
    def add_gap_segment(self, duration_ms: int, insert_index: int, break_position: str) -> bool:
        """Thêm khoảng nghỉ (gap) vào segments"""
        try:
            # Create silent gap with specified duration
            gap = AudioSegment.silent(duration=duration_ms)
            
            # Create temporary file for gap
            temp_dir = Path(tempfile.mkdtemp(prefix=AppConfig.TEMP_PREFIX))
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Ẩn thư mục tạm sau khi tạo (chỉ trên Windows)
            hide_directory_on_windows(temp_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            gap_path = str(temp_dir / f"gap_{timestamp}.mp3")
            
            # Export gap
            gap.export(gap_path, format="mp3")
            
            # Insert gap at specified position
            if break_position == "trước":
                self.segment_paths.insert(insert_index, gap_path)
                self.segment_durations.insert(insert_index, duration_ms)
            else:  # break_position == "sau"
                self.segment_paths.insert(insert_index, gap_path)
                self.segment_durations.insert(insert_index, duration_ms)
                
            self._update_total_duration()
            self._update_display()
            self.segments_changed.emit()
            return True
            
        except Exception as e:
            print(f"Error adding gap segment: {e}")
            return False
            
    def split_segment(self, segment_index: int, split_position_ms: int) -> bool:
        """Cắt segment tại vị trí cụ thể"""
        try:
            if not (0 <= segment_index < len(self.segment_paths)):
                return False
                
            original_path = self.segment_paths[segment_index]
            original_duration = self.segment_durations[segment_index]
            
            if not original_path or not original_duration:
                return False
                
            # Cắt audio file
            part1_path, part2_path = self._split_audio_file(original_path, split_position_ms)
            
            if part1_path and part2_path:
                part1_duration = split_position_ms
                part2_duration = original_duration - split_position_ms
                
                # Thay thế segment cũ bằng phần 1
                self.segment_paths[segment_index] = part1_path
                self.segment_durations[segment_index] = part1_duration
                
                # Thêm phần 2 vào cuối
                self.segment_paths.append(part2_path)
                self.segment_durations.append(part2_duration)
                
                self._update_total_duration()
                self._update_display()
                self.segments_changed.emit()
                return True
                
            return False
            
        except Exception as e:
            print(f"Error splitting segment: {e}")
            return False
            
    def reorder_segments(self, new_order: List[int]) -> bool:
        """Sắp xếp lại thứ tự segments"""
        try:
            if len(new_order) != len(self.segment_paths):
                return False
                
            # Reorder segments
            new_paths = [self.segment_paths[i] for i in new_order]
            new_durations = [self.segment_durations[i] for i in new_order]
            
            # Update lists
            self.segment_paths = new_paths
            self.segment_durations = new_durations
            
            self._update_total_duration()
            self._update_display()
            self.segment_reordered.emit()
            self.segments_changed.emit()
            return True
            
        except Exception as e:
            print(f"Error reordering segments: {e}")
            return False
            
    def get_segment_info(self, index: int) -> Optional[dict]:
        """Lấy thông tin chi tiết của segment"""
        if 0 <= index < len(self.segment_paths):
            path = self.segment_paths[index]
            duration = self.segment_durations[index]
            
            if path and duration:
                return {
                    'path': path,
                    'duration': duration,
                    'filename': os.path.basename(path),
                    'file_size': self._get_file_size(path),
                    'is_gap': 'gap_' in path,
                    'is_part': 'part1_' in path or 'part2_' in path
                }
        return None
        
    def get_segments_statistics(self) -> dict:
        """Lấy thống kê về segments"""
        total_segments = len([d for d in self.segment_durations if d])
        gap_count = sum(1 for p in self.segment_paths if p and "gap_" in p)
        broken_count = sum(1 for p in self.segment_paths if p and ("part1_" in p or "part2_" in p))
        tts_count = total_segments - gap_count - broken_count
        
        return {
            'total_segments': total_segments,
            'total_duration': self.total_known_ms,
            'gap_count': gap_count,
            'broken_count': broken_count,
            'tts_count': tts_count
        }
        
    def _update_total_duration(self) -> None:
        """Cập nhật tổng thời lượng"""
        self.total_known_ms = sum(d or 0 for d in self.segment_durations)
        
    def _update_display(self) -> None:
        """Cập nhật hiển thị segments với custom row widget"""
        if not self.list_widget:
            return
            
        self.list_widget.clear()
        
        if not self.segment_paths or not any(self.segment_paths):
            return
            
        cumulative_ms = 0
        total_ms = self.total_known_ms
        
        for i, (path, duration) in enumerate(zip(self.segment_paths, self.segment_durations)):
            if path and duration:
                filename = os.path.basename(path)
                cumulative_ms += duration
                
                # Tạo custom row widget
                row_widget = self._create_segment_row_widget(
                    i + 1, filename, duration, cumulative_ms, total_ms, path
                )
                
                # Tạo QListWidgetItem và set widget
                item = QListWidgetItem()
                item.setSizeHint(row_widget.sizeHint())
                self.list_widget.addItem(item)
                self.list_widget.setItemWidget(item, row_widget)
                
            elif path is None and duration is None:
                # Phần đang tạo
                row_widget = self._create_loading_row_widget(i + 1)
                item = QListWidgetItem()
                item.setSizeHint(row_widget.sizeHint())
                self.list_widget.addItem(item)
                self.list_widget.setItemWidget(item, row_widget)
                
    def _create_segment_row_widget(self, index: int, filename: str, duration_ms: int, 
                                  cumulative_ms: int, total_ms: int, file_path: str) -> QWidget:
        """Tạo custom row widget cho segment với 3 cột"""
        # Format text cho 3 cột
        left_text = self._format_segment_name(index, filename, duration_ms)
        center_text = f"{ms_to_mmss(cumulative_ms)}-{ms_to_mmss(total_ms)}"
        right_text = self._get_file_size(file_path)
        
        # Tạo ListRow widget
        return ListRow(left_text, center_text, right_text)
        
    def _create_loading_row_widget(self, index: int) -> QWidget:
        """Tạo custom row widget cho phần đang tạo"""
        # Format text cho 3 cột
        left_text = f"{index:03d}. (đang tạo...)"
        center_text = "--"
        right_text = "--"
        
        # Tạo ListRow widget
        return ListRow(left_text, center_text, right_text)
        
    def _format_segment_name(self, index: int, filename: str, duration_ms: int) -> str:
        """Format tên segment cho cột đầu tiên"""
        # Xử lý các trường hợp đặc biệt
        if filename.startswith("gap_"):
            # Khoảng nghỉ
            segment_time = ms_to_mmss(duration_ms)
            return f"{index:03d}. [KHOẢNG NGHỈ] — {segment_time}"
        elif "part1_" in filename or "part2_" in filename:
            # Phần được chia
            original_name = filename.replace("part1_", "").replace("part2_", "")
            part_num = "1" if "part1_" in filename else "2"
            segment_time = ms_to_mmss(duration_ms)
            return f"{index:03d}. {original_name} (Phần {part_num}) — {segment_time}"
        else:
            # Segment thông thường
            segment_time = ms_to_mmss(duration_ms)
            return f"{index:03d}. {filename} — {segment_time}"
                
    def _format_segment_display_text(self, index: int, filename: str, duration_ms: int, cumulative_ms: int, total_ms: int) -> str:
        """Format text hiển thị cho segment với thông tin thời gian và kích thước file chi tiết"""
        # Xử lý các trường hợp đặc biệt
        if filename.startswith("gap_"):
            # Khoảng nghỉ
            segment_time = ms_to_mmss(duration_ms)
            cumulative_time = ms_to_mmss(cumulative_ms)
            total_time = ms_to_mmss(total_ms)
            return f"{index:03d}. [KHOẢNG NGHỈ] - {segment_time} - {cumulative_time}/{total_time}"
        elif "part1_" in filename or "part2_" in filename:
            # Phần được chia
            original_name = filename.replace("part1_", "").replace("part2_", "")
            part_num = "1" if "part1_" in filename else "2"
            segment_time = ms_to_mmss(duration_ms)
            cumulative_time = ms_to_mmss(cumulative_ms)
            total_time = ms_to_mmss(total_ms)
            return f"{index:03d}. {original_name} (Phần {part_num}) - {segment_time} - {cumulative_time}/{total_time}"
        else:
            # Segment thông thường
            segment_time = ms_to_mmss(duration_ms)
            cumulative_time = ms_to_mmss(cumulative_ms)
            total_time = ms_to_mmss(total_ms)
            return f"{index:03d}. {filename} - {segment_time} - {cumulative_time}/{total_time}"
            
    def _get_file_size(self, file_path: str) -> str:
        """Lấy kích thước file và format thành KB/MB"""
        try:
            if file_path and os.path.exists(file_path):
                size_bytes = os.path.getsize(file_path)
                
                # Format kích thước
                if size_bytes < 1024:
                    return f"{size_bytes}B"
                elif size_bytes < 1024 * 1024:
                    size_kb = size_bytes / 1024
                    return f"{size_kb:.1f}KB"
                else:
                    size_mb = size_bytes / (1024 * 1024)
                    return f"{size_mb:.1f}MB"
            else:
                return "N/A"
        except Exception:
            return "N/A"
            
    def _split_audio_file(self, audio_path: str, split_position_ms: int) -> Tuple[Optional[str], Optional[str]]:
        """Cắt audio file thành 2 phần"""
        try:
            # Load audio
            audio = AudioSegment.from_file(audio_path)
            
            # Split audio
            part1 = audio[:split_position_ms]
            part2 = audio[split_position_ms:]
            
            # Create temporary files
            temp_dir = Path(tempfile.mkdtemp(prefix=AppConfig.TEMP_PREFIX))
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Ẩn thư mục tạm sau khi tạo (chỉ trên Windows)
            hide_directory_on_windows(temp_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = os.path.splitext(os.path.basename(audio_path))[0]
            
            part1_path = str(temp_dir / f"part1_{base_name}_{timestamp}.mp3")
            part2_path = str(temp_dir / f"part2_{base_name}_{timestamp}.mp3")
            
            # Export parts
            part1.export(part1_path, format="mp3")
            part2.export(part2_path, format="mp3")
            
            return part1_path, part2_path
            
        except Exception as e:
            print(f"Error splitting audio file: {e}")
            return None, None
