# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Tuple, List, Optional
import os
import shutil

from pydub import AudioSegment  # type: ignore

from app.utils.audio_helpers import prepare_pydub_ffmpeg, get_mp3_duration_ms


class SegmentAudio:
	"""
	Helper class to work with audio segments managed by SegmentManager:
	- Collect valid paths
	- Export all segments to a folder
	- Merge all segments to a single file
	- Update segment stats display in UI
	"""

	@staticmethod
	def collect_valid_paths(manager) -> List[str]:
		paths = []
		try:
			for p in getattr(manager, 'segment_paths', []) or []:
				if p:
					paths.append(p)
		except Exception:
			pass
		return paths

	@staticmethod
	def export_all_to_folder(manager, dest_folder: str) -> Tuple[int, int]:
		"""Copy all valid segment files to dest_folder with zero-padded order.
		Returns (exported_count, total_valid).
		"""
		paths = SegmentAudio.collect_valid_paths(manager)
		if not paths:
			return 0, 0
		os.makedirs(dest_folder, exist_ok=True)
		width = max(3, len(str(len(paths))))
		exported = 0
		for idx, src in enumerate(paths, start=1):
			try:
				if not os.path.exists(src):
					continue
				base = os.path.basename(src)
				name, ext = os.path.splitext(base)
				dst_name = f"{idx:0{width}d}_{name}{ext}"
				dst_path = os.path.join(dest_folder, dst_name)
				shutil.copy2(src, dst_path)
				exported += 1
			except Exception:
				continue
		return exported, len(paths)

	@staticmethod
	def merge_all_to_file(manager, out_path: str, gap_ms: int = 0) -> Tuple[Optional[str], Optional[int], int]:
		"""Merge all valid segments into a single MP3 at out_path.
		Optionally insert silent gap_ms between non-gap segments.
		Returns (out_path_or_none, total_duration_ms_or_none, merged_count).
		"""
		parts = SegmentAudio.collect_valid_paths(manager)
		if not parts:
			return None, None, 0
		prepare_pydub_ffmpeg()
		final = AudioSegment.silent(duration=0)
		merged = 0
		for i, p in enumerate(parts):
			try:
				seg = AudioSegment.from_file(p)
				final += seg
				# optional gap between segments (skip after last)
				if gap_ms and i < len(parts) - 1:
					next_path = parts[i + 1] if i + 1 < len(parts) else None
					if not (next_path and 'gap_' in next_path):
						final += AudioSegment.silent(duration=gap_ms)
				merged += 1
			except Exception:
				continue
		if merged == 0:
			return None, None, 0
		# export
		final.export(out_path, format='mp3')
		total_ms = get_mp3_duration_ms(out_path)
		return out_path, total_ms, merged

	@staticmethod
	def update_segment_display(manager, total_label, count_label) -> None:
		"""Update segment UI labels and group box title based on manager stats."""
		try:
			if not manager:
				return
			stats = manager.get_segments_statistics()
			# Recompute using valid segments to avoid None/0 durations affecting counts
			try:
				valid_paths, valid_durations = manager.get_valid_segments()
				total_segments = len(valid_paths)
				total_ms_override = sum(d or 0 for d in valid_durations)
			except Exception:
				total_segments = stats.get('total_segments', 0)
				total_ms_override = stats.get('total_duration', 0)
			# Update total duration label
			if total_label is not None:
				total_ms = total_ms_override if total_ms_override is not None else stats['total_duration']
				if total_ms <= 0:
					total_label.setText("Tổng thời lượng: 00:00")
				else:
					total_seconds = total_ms // 1000
					hours = total_seconds // 3600
					minutes = (total_seconds % 3600) // 60
					seconds = total_seconds % 60
					if hours > 0:
						text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
					else:
						text = f"{minutes:02d}:{seconds:02d}"
					total_label.setText(f"Tổng thời lượng: {text}")
			# Update count label
			if count_label is not None:
				count_label.setText(f"Số segments: {total_segments}")
		except Exception:
			pass
