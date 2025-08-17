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
    """
    Xóa tất cả các thư mục tạm thời của ứng dụng

    Returns:
        int: Số lượng thư mục đã xóa thành công
    """
    cleaned_count = 0
    tmpdir = tempfile.gettempdir()

    try:
        for name in os.listdir(tmpdir):
            p = os.path.join(tmpdir, name)
            if os.path.isdir(p) and name.startswith(TTSConfig.TEMP_PREFIX):
                try:
                    shutil.rmtree(p, ignore_errors=True)
                    cleaned_count += 1
                    print(f"Đã xóa thư mục tạm: {name}")
                except Exception as e:
                    print(f"Lỗi khi xóa thư mục {name}: {e}")
    except Exception as e:
        print(f"Lỗi khi quét thư mục tạm: {e}")

    print(f"Đã xóa {cleaned_count} thư mục tạm thời")
    return cleaned_count


def timestamp_str():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def save_log_entry(entry: dict):
    """
    Lưu một entry log vào file JSON

    Args:
        entry (dict): Dữ liệu log cần lưu

    Returns:
        bool: True nếu lưu thành công, False nếu thất bại
    """
    try:
        # Đảm bảo entry là dict
        if not isinstance(entry, dict):
            print("Lỗi: entry phải là dictionary")
            return False

        data = []

        # Đọc dữ liệu cũ nếu file tồn tại
        if TTSConfig.LOG_PATH.exists():
            try:
                with open(TTSConfig.LOG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, list):
                        data = []
            except json.JSONDecodeError:
                print("Lỗi: File log bị hỏng, tạo mới")
                data = []
            except Exception as e:
                print(f"Lỗi khi đọc file log: {e}")
                data = []

        # Thêm entry mới
        entry['timestamp'] = datetime.now().isoformat()
        data.append(entry)

        # Lưu vào file
        with open(TTSConfig.LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:
        print(f"Lỗi khi lưu log: {e}")
        return False


def hide_directory_on_windows(directory_path):
    """
    Ẩn thư mục trên Windows bằng lệnh attrib +h

    Args:
        directory_path (str): Đường dẫn đến thư mục cần ẩn

    Returns:
        bool: True nếu thành công, False nếu thất bại

    Raises:
        OSError: Nếu không phải hệ điều hành Windows
    """
    import platform
    import subprocess

    # Kiểm tra hệ điều hành
    if platform.system() != 'Windows':
        raise OSError("Hàm này chỉ hoạt động trên Windows")

    try:
        # Kiểm tra thư mục có tồn tại không
        if not os.path.exists(directory_path):
            print(f"Thư mục không tồn tại: {directory_path}")
            return False

        # Thực hiện lệnh ẩn thư mục
        result = subprocess.run(
            ['attrib', '+h', directory_path],
            shell=True,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"Đã ẩn thư mục thành công: {directory_path}")
            return True
        else:
            print(f"Lỗi khi ẩn thư mục: {result.stderr}")
            return False

    except Exception as e:
        print(f"Lỗi khi ẩn thư mục: {e}")
        return False


def show_directory_on_windows(directory_path):
    """
    Hiện thư mục đã ẩn trên Windows bằng lệnh attrib -h

    Args:
        directory_path (str): Đường dẫn đến thư mục cần hiện

    Returns:
        bool: True nếu thành công, False nếu thất bại

    Raises:
        OSError: Nếu không phải hệ điều hành Windows
    """
    import platform
    import subprocess

    # Kiểm tra hệ điều hành
    if platform.system() != 'Windows':
        raise OSError("Hàm này chỉ hoạt động trên Windows")

    try:
        # Kiểm tra thư mục có tồn tại không
        if not os.path.exists(directory_path):
            print(f"Thư mục không tồn tại: {directory_path}")
            return False

        # Thực hiện lệnh hiện thư mục
        result = subprocess.run(
            ['attrib', '-h', directory_path],
            shell=True,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"Đã hiện thư mục thành công: {directory_path}")
            return True
        else:
            print(f"Lỗi khi hiện thư mục: {result.stderr}")
            return False

    except Exception as e:
        print(f"Lỗi khi hiện thư mục: {e}")
        return False


def is_directory_hidden(directory_path):
    """
    Kiểm tra trạng thái ẩn của thư mục trên Windows

    Args:
        directory_path (str): Đường dẫn đến thư mục cần kiểm tra

    Returns:
        bool: True nếu thư mục bị ẩn, False nếu không

    Raises:
        OSError: Nếu không phải hệ điều hành Windows
    """
    import platform
    import subprocess

    # Kiểm tra hệ điều hành
    if platform.system() != 'Windows':
        raise OSError("Hàm này chỉ hoạt động trên Windows")

    try:
        # Kiểm tra thư mục có tồn tại không
        if not os.path.exists(directory_path):
            print(f"Thư mục không tồn tại: {directory_path}")
            return False

        # Kiểm tra thuộc tính ẩn
        result = subprocess.run(
            ['attrib', directory_path],
            shell=True,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            # Kiểm tra xem có chứa 'H' (hidden) không
            return 'H' in result.stdout
        else:
            # print(f"Lỗi khi kiểm tra thuộc tính: {result.stderr}")
            rzeturn False

    except Exception as e:
        print(f"Lỗi khi kiểm tra thuộc tính: {e}")
        return False
