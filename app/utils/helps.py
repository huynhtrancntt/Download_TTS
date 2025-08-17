import re
import os
import json
import shutil
import tempfile
from datetime import datetime
from typing import List
import asyncio
from pydub import AudioSegment
from pydub.utils import which
import edge_tts

from app.core.config import TTSConfig

# ---------- Text split ----------


# ===== Viết tắt để không cắt nhầm =====
ABBREVIATIONS = {
    "tp.hcm", "tp", "v.d.", "vd.", "ts.", "th.s.", "pgs.", "gs.",
    "mr.", "mrs.", "ms.", "dr.", "prof.", "sr.", "jr.", "st.",
    "no.", "etc.", "e.g.", "i.e.", "vs."
}

# ===== Regex =====
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…。！？])\s+")

# ===== Hàm xử lý =====


def _is_abbrev(token: str) -> bool:
    return token.lower().strip() in ABBREVIATIONS


def _split_sentences(paragraph: str) -> List[str]:
    """Tách paragraph thành câu, tránh cắt sai viết tắt."""
    rough = _SENTENCE_SPLIT.split(paragraph.strip())
    if len(rough) <= 1:
        return [paragraph.strip()]
    fixed, buf = [], ""
    for chunk in rough:
        chunk = chunk.strip()
        if not buf:
            buf = chunk
        else:
            last_token = buf.split()[-1] if buf.split() else ""
            if _is_abbrev(last_token):
                buf = f"{buf} {chunk}"
            else:
                fixed.append(buf)
                buf = chunk
    if buf:
        fixed.append(buf)
    return fixed


def split_text(text: str, max_len: int = None) -> List[str]:
    """
    Tách ý theo nguyên tắc:
    - Ưu tiên xuống dòng -> mỗi đoạn là 1 ý
    - Nếu đoạn dài -> tách theo câu, nhưng giữ câu liên quan
    - max_len: nếu đặt, giới hạn ký tự/ý
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    ideas: List[str] = []
    for para in paragraphs:
        if not max_len or len(para) <= max_len:
            ideas.append(para)
            continue

        sentences = _split_sentences(para)
        cur = ""
        for s in sentences:
            if not cur:
                cur = s
            elif not max_len or len(cur) + 1 + len(s) <= max_len:
                cur = f"{cur} {s}"
            else:
                ideas.append(cur.strip())
                cur = s
        if cur:
            ideas.append(cur.strip())

    return ideas


# def split_text(text: str, max_len: int = 220) -> List[str]:
#     sentences = re.split(r'(?<=[.!?…])\s+', text.strip())
#     chunks, cur = [], ""

#     def flush():
#         nonlocal cur
#         if cur.strip():
#             chunks.append(cur.strip())
#         cur = ""
#     for s in sentences:
#         s = s.strip()
#         if not s:
#             continue
#         if len(s) > max_len:
#             parts = re.split(r'([,;:])', s)
#             buff = ""
#             for p in parts:
#                 cand = (buff + p) if buff else p
#                 if len(cand) <= max_len:
#                     buff = cand
#                 else:
#                     if buff.strip():
#                         chunks.append(buff.strip())
#                     buff = p.strip()
#             if buff.strip():
#                 chunks.append(buff.strip())
#             continue
#         if len(cur) + len(s) + (1 if cur else 0) <= max_len:
#             cur = (cur + " " + s).strip() if cur else s
#         else:
#             flush()
#             cur = s
#     flush()
#     return chunks

# ---------- Edge TTS ----------


async def _edge_tts_save_async(text: str, out_path: str, voice: str, rate: str, pitch: str):
    communicate = edge_tts.Communicate(
        text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(out_path)


def tts_sync_save(text, out_path, voice, rate_percent, pitch_hz):
    asyncio.run(_edge_tts_save_async(
        text, out_path,
        voice=voice,
        rate=f"{rate_percent:+d}%",
        pitch=f"{pitch_hz:+d}Hz",
    ))

# ---------- Audio helpers ----------
# Moved to audio_helpers.py to avoid circular import

# ---------- Misc ----------


def clean_all_temp_parts():
    tmpdir = tempfile.gettempdir()
    for name in os.listdir(tmpdir):
        p = os.path.join(tmpdir, name)
        if os.path.isdir(p) and name.startswith(TTSConfig.TEMP_PREFIX):
            try:
                shutil.rmtree(p, ignore_errors=True)
            except Exception:
                pass


def timestamp_str():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def save_log_entry(entry: dict):
    try:
        data = []
        if TTSConfig.LOG_PATH.exists():
            with open(TTSConfig.LOG_PATH, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    if not isinstance(data, list):
                        data = []
                except Exception:
                    data = []
        data.append(entry)
        with open(TTSConfig.LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Log write error:", e)
