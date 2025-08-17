# -*- coding: utf-8 -*-
"""
Audio helper functions
Chứa các hàm hỗ trợ xử lý audio, tránh circular import
"""

from pydub import AudioSegment
from pydub.utils import which


def get_mp3_duration_ms(path: str) -> int:
    """Lấy thời lượng file MP3 theo milliseconds"""
    try:
        seg = AudioSegment.from_file(path)
        return int(seg.duration_seconds * 1000)
    except Exception:
        return 0


def ms_to_mmss(ms: int) -> str:
    """Chuyển đổi milliseconds thành định dạng MM:SS"""
    if ms < 0:
        ms = 0
    s = ms // 1000
    m = s // 60
    s = s % 60
    return f"{m:02d}:{s:02d}"


def prepare_pydub_ffmpeg():
    """Chuẩn bị FFmpeg cho pydub"""
    ffmpeg = which("ffmpeg") or r"C:\ffmpeg\bin\ffmpeg.exe"
    ffprobe = which("ffprobe") or r"C:\ffmpeg\bin\ffprobe.exe"
    AudioSegment.converter = ffmpeg
    AudioSegment.ffprobe = ffprobe
