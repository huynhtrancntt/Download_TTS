# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional, Tuple, List

from PySide6.QtCore import QObject, Signal

from app.core.audio_player import AudioPlayer
from app.core.segment_manager import SegmentManager
from app.workers.TTS_workers import MTProducerWorker


class SRTPlaybackController(QObject):
    """
    Controller quản lý AudioPlayer, SegmentManager, MTProducerWorker cho SRT/TTS.

    UI chỉ cần truyền các widget cần thiết (list segments, labels, buttons) nếu muốn đồng bộ.
    """

    # Relay các tín hiệu hữu ích ra ngoài nếu cần
    position_changed = Signal(int)
    segment_changed = Signal(int)
    playback_state_changed = Signal(bool)
    status_signal = Signal(str)
    playback_finished = Signal()
    segments_changed = Signal()

    def __init__(
        self,
        parent: Optional[QObject] = None,
        list_widget=None,
        total_duration_label=None,
        segment_count_label=None,
    ) -> None:
        super().__init__(parent)

        self._list_widget = list_widget
        self._total_duration_label = total_duration_label
        self._segment_count_label = segment_count_label

        self.audio_player = AudioPlayer()
        self.segment_manager = SegmentManager()
        self.worker: Optional[MTProducerWorker] = None

        # Kết nối player → controller
        self.audio_player.position_changed.connect(self.position_changed.emit)
        self.audio_player.segment_changed.connect(self._on_segment_changed)
        self.audio_player.playback_state_changed.connect(self.playback_state_changed.emit)
        self.audio_player.status_signal.connect(self.status_signal.emit)
        if hasattr(self.audio_player, 'playback_finished'):
            self.audio_player.playback_finished.connect(self._on_playback_finished)

        # Đồng bộ SegmentManager với UI và Player
        self.segment_manager.set_ui_components(self._list_widget, self.audio_player)
        self.segment_manager.segments_changed.connect(self._on_segments_changed)

    # ===================== Public API =====================
    def add_audio_file(self, path: str) -> bool:
        if not path:
            return False
        added = self.segment_manager.add_audio_file(path)
        if added:
            self._sync_player_segments()
        return added

    def clear_segments(self) -> None:
        self.segment_manager.clear_segments()
        self._sync_player_segments()

    def play(self) -> None:
        self.audio_player.play()

    def play_all(self) -> None:
        """Seek to the beginning and play all segments from start."""
        try:
            self.seek_to(0)
        except Exception:
            pass
        self.play()

    def pause(self) -> None:
        self.audio_player.pause()

    def stop_all(self) -> None:
        try:
            if self.audio_player:
                self.audio_player.stop()
        except Exception:
            pass
        try:
            if self.worker and self.worker.isRunning():
                self.worker.stop()
                self.worker.wait(3000)
        except Exception:
            pass

    def set_loop(self, enabled: bool) -> None:
        try:
            if hasattr(self.audio_player, 'chk_loop'):
                self.audio_player.chk_loop.setChecked(bool(enabled))
        except Exception:
            pass

    def seek_to(self, position_ms: int) -> None:
        self.audio_player.seek_to(max(0, int(position_ms)))

    def start_tts(
        self,
        text: str,
        voice_name: str,
        speed: int,
        pitch: int,
        max_length: int,
        workers: int,
    ) -> None:
        # Dừng worker cũ nếu có
        if self.worker and self.worker.isRunning():
            try:
                self.worker.stop()
                self.worker.wait(2000)
            except Exception:
                pass

        # Xóa segments cũ
        self.clear_segments()

        # Tạo worker mới
        self.worker = MTProducerWorker(text, voice_name, speed, pitch, max_length, workers)
        self.worker.segment_ready.connect(self._on_tts_segment_ready)
        self.worker.progress.connect(lambda e, t: self.status_signal.emit(f"TTS {e}/{t}"))
        self.worker.status.connect(lambda s: self.status_signal.emit(s))
        self.worker.all_done.connect(lambda: self.status_signal.emit("TTS done"))
        self.worker.error.connect(lambda m: self.status_signal.emit(f"TTS error: {m}"))
        self.worker.start()

    # ===================== Internals =====================
    def _on_tts_segment_ready(self, path: str, duration_ms: int, index: int) -> None:
        # ensure capacity then set
        self._ensure_capacity_on_manager(index)
        self.segment_manager.segment_paths[index - 1] = path
        self.segment_manager.segment_durations[index - 1] = duration_ms
        self.segment_manager._update_total_duration()
        self.segment_manager._update_display()
        self._sync_player_segments()

        # Auto-play khi có segment đầu tiên
        if index == 1:
            self.audio_player.play()

    def _ensure_capacity_on_manager(self, n: int) -> None:
        try:
            while len(self.segment_manager.segment_paths) < n:
                self.segment_manager.segment_paths.append(None)
                self.segment_manager.segment_durations.append(None)
        except Exception:
            pass

    def _sync_player_segments(self) -> None:
        try:
            valid_paths, valid_durations = self.segment_manager.get_valid_segments()
            self.audio_player.add_segments(valid_paths, valid_durations)
            self._update_header_stats()
            self.segments_changed.emit()
        except Exception:
            pass

    def _update_header_stats(self) -> None:
        try:
            stats = self.segment_manager.get_segments_statistics()
            if self._segment_count_label:
                self._segment_count_label.setText(f"Số segments: {stats['total_segments']}")
            if self._total_duration_label:
                total_ms = stats['total_duration']
                if total_ms <= 0:
                    self._total_duration_label.setText("Tổng thời lượng: 00:00")
                else:
                    total_seconds = total_ms // 1000
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    if hours > 0:
                        s = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    else:
                        s = f"{minutes:02d}:{seconds:02d}"
                    self._total_duration_label.setText(f"Tổng thời lượng: {s}")
        except Exception:
            pass

    def _on_segments_changed(self) -> None:
        self._sync_player_segments()

    def _on_segment_changed(self, idx: int) -> None:
        # Relay và đồng bộ list selection nếu có
        self.segment_changed.emit(idx)
        try:
            if self._list_widget and 0 <= idx < self._list_widget.count():
                self._list_widget.setCurrentRow(idx)
        except Exception:
            pass

    def _on_playback_finished(self) -> None:
        self.playback_finished.emit()


