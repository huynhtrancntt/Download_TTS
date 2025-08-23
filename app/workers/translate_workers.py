# -*- coding: utf-8 -*-
"""
Workers cho xử lý dịch thuật đa luồng
Chứa các worker class để xử lý dịch thuật song song và batch processing
"""

import os
import tempfile
from datetime import datetime
import time
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Tuple
import json

from PySide6.QtCore import QThread, Signal

from app.utils.helps import split_text, group_by_char_limit_with_len
from deep_translator import GoogleTranslator
import google.generativeai as genai
import openai

# Thêm import cần thiết ở đầu file
from app.utils.audio_helpers import get_mp3_duration_ms

# ==================== MultiThreadTranslateWorker - Worker đa luồng cho Tab Translate ====================

class MultiThreadTranslateWorker(QThread):
    """
    Worker đa luồng cho việc dịch thuật
    Xử lý văn bản song song và trả về kết quả theo đúng thứ tự

    Signals:
        segment_translated: Phát khi một đoạn được dịch xong (original, translated, index)
        progress: Tiến trình xử lý (completed, total)
        status: Thông báo trạng thái
        all_done: Hoàn thành tất cả
        error: Có lỗi xảy ra
    """

    # Định nghĩa các signals
    segment_translated = Signal(str, str, int)  # original, translated, index
    progress = Signal(int, int)                 # completed, total
    status = Signal(str)                        # status message
    all_done = Signal()                         # all processing done
    error = Signal(str)                         # error message

    def __init__(self, text: str, source_lang: str, target_lang: str, 
                 service: str, api_key: str, max_len: int, workers: int, 
                 custom_prompt: str = "") -> None:
        """
        Khởi tạo worker dịch thuật đa luồng

        Args:
            text: Văn bản cần dịch
            source_lang: Ngôn ngữ nguồn (code)
            target_lang: Ngôn ngữ đích (code)
            service: Dịch vụ dịch thuật ("Google Translate", "Google Gemini", "OpenAI")
            api_key: API key cho dịch vụ (nếu cần)
            max_len: Độ dài tối đa mỗi đoạn (ký tự)
            workers: Số luồng xử lý song song
            custom_prompt: Prompt tùy chỉnh cho AI models
        """
        super().__init__()

        # Tham số dịch thuật
        self.text: str = text
        self.source_lang: str = source_lang
        self.target_lang: str = target_lang
        self.service: str = service
        self.api_key: str = api_key
        self.max_len: int = max_len
        self.workers: int = max(1, workers)  # Tối thiểu 1 worker
        self.custom_prompt: str = custom_prompt
        
        # Trạng thái worker
        self.stop_flag: bool = False
        self.tmpdir: Optional[str] = None

    def stop(self) -> None:
        """
        Dừng worker (set flag để các thread con dừng)
        """
        self.stop_flag = True

    def _translate_segment_google(self, text: str) -> str:
        """Dịch bằng Google Translate"""
        try:
            translator = GoogleTranslator(source=self.source_lang, target=self.target_lang)
            return translator.translate(text)
        except Exception as e:
            raise Exception(f"Lỗi Google Translate: {str(e)}")

    def _translate_segment_gemini(self, text: str) -> str:
        """Dịch bằng Google Gemini"""
        try:
            if not self.api_key:
                raise Exception("Thiếu Gemini API Key")
            
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel('gemini-pro')
            
            prompt = f"""
            Bạn là một dịch giả chuyên nghiệp. Hãy dịch văn bản sau từ {self.source_lang} sang {self.target_lang}.
            
            {self.custom_prompt if self.custom_prompt else "Hãy dịch chính xác và tự nhiên, giữ nguyên ý nghĩa và ngữ cảnh."}
            
            Văn bản cần dịch:
            {text}
            
            Chỉ trả về bản dịch, không có giải thích thêm.
            """
            
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            raise Exception(f"Lỗi Google Gemini: {str(e)}")

    def _translate_segment_openai(self, text: str) -> str:
        """Dịch bằng OpenAI ChatGPT"""
        try:
            if not self.api_key:
                raise Exception("Thiếu OpenAI API Key")
            
            openai.api_key = self.api_key
            
            prompt = f"""
            Bạn là một dịch giả chuyên nghiệp. Hãy dịch văn bản sau từ {self.source_lang} sang {self.target_lang}.
            
            {self.custom_prompt if self.custom_prompt else "Hãy dịch chính xác và tự nhiên, giữ nguyên ý nghĩa và ngữ cảnh."}
            
            Văn bản cần dịch:
            {text}
            
            Chỉ trả về bản dịch, không có giải thích thêm.
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Bạn là một dịch giả chuyên nghiệp."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"Lỗi OpenAI: {str(e)}")

    def _translate_segment(self, text: str) -> str:
        """Dịch một đoạn văn bản theo service được chọn"""
        if self.service == "Google Translate":
            return self._translate_segment_google(text)
        elif self.service == "Google Gemini":
            return self._translate_segment_gemini(text)
        elif self.service == "OpenAI (ChatGPT)":
            return self._translate_segment_openai(text)
        else:
            raise Exception(f"Không hỗ trợ service: {self.service}")

    def run(self) -> None:
        """
        Phương thức chính chạy worker dịch thuật
        Chia văn bản thành chunks và xử lý song song
        """
        try:
            # Kiểm tra văn bản đầu vào
            if not self.text.strip():
                self.error.emit("❌ Chưa có nội dung văn bản để dịch.")
                return

            # 1) Tách ý (ý đơn) — dùng ngưỡng nhỏ hơn để ý không quá dài
            ideas = split_text(self.text, self.max_len)
            
            # 2) Gộp ý thành cụm lớn hơn — giữ đúng thứ tự
            # grouped = group_by_char_limit_with_len(
            #     ideas,
            #     max_group=5,  # Tối đa 5 ý/nhóm để dịch hiệu quả
            #     max_chars=self.max_len,
            #     sep=" | "
            # )
            chunks = ideas
            # chunks = [item[0] for item in grouped]
            # print(chunks)
            total = len(chunks)
            
            if total == 0:
                self.error.emit("❌ Không thể tách văn bản thành các đoạn.")
                return

            self.status.emit(f"🔧 Tạo {total} đoạn để dịch bằng {self.workers} luồng...")

            # Dictionary để lưu kết quả theo thứ tự
            completed: Dict[int, Tuple[str, str]] = {}  # index -> (original, translated)
            next_index = 1
            emitted = 0

            def job(index1: int, content: str) -> Tuple[int, str, str]:
                """Job xử lý một đoạn văn bản"""
                try:
                    # Lấy thông tin thread hiện tại
                    import threading
                    current_thread = threading.current_thread()
                    thread_name = current_thread.name
                    thread_id = current_thread.ident
                    
                    self.status.emit(f"🧵 Thread {thread_name} (ID: {thread_id}) bắt đầu dịch đoạn {index1}")
                    
                    # Dịch đoạn văn bản
                    translated = self._translate_segment(content)
                    
                    # Nghỉ ngẫu nhiên để tránh rate limit
                    time.sleep(random.uniform(0.5, 1.5))
                    
                    return (index1, content, translated)
                    
                except Exception as e:
                    raise Exception(f"Lỗi xử lý đoạn {index1}: {str(e)}")

            # Xử lý đa luồng theo batch để tránh treo và rate-limit
            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                batch_size = 50  # Batch size nhỏ hơn cho dịch thuật
                
                for batch_start in range(0, total, batch_size):
                    if self.stop_flag:
                        self.status.emit("⏹ Đã dừng theo yêu cầu người dùng.")
                        break

                    batch_end = min(total, batch_start + batch_size)
                    
                    # Submit batch hiện tại
                    futures = [executor.submit(job, i + 1, chunks[i])
                               for i in range(batch_start, batch_end)]

                    # Xử lý kết quả của batch
                    for future in as_completed(futures):
                        if self.stop_flag:
                            self.status.emit("⏹ Đã dừng theo yêu cầu người dùng.")
                            break

                        try:
                            idx1, original, translated = future.result()
                            completed[idx1] = (original, translated)
                        except Exception as e:
                            self.status.emit(f"⚠️ {str(e)}")
                            continue

                        # Emit các đoạn theo đúng thứ tự
                        while next_index in completed:
                            orig, trans = completed.pop(next_index)
                            self.segment_translated.emit(orig, trans, next_index)
                            emitted += 1
                            self.progress.emit(emitted, total)
                            next_index += 1

                    if self.stop_flag:
                        break

                    # Nếu còn batch kế tiếp, nghỉ ngẫu nhiên 1-3s
                    if batch_end < total:
                        delay = random.uniform(1, 3)
                        self.status.emit(f"⏳ Nghỉ {delay:.1f}s trước batch tiếp theo...")
                        time.sleep(delay)

            if self.stop_flag:
                self.status.emit("⏹ Đã dừng theo yêu cầu người dùng.")
                return

            # Kiểm tra xem tất cả đã hoàn thành chưa
            if emitted == total:
                self.status.emit("✅ Hoàn thành dịch tất cả đoạn!")
                self.all_done.emit()
            else:
                self.error.emit(f"⚠️ Chỉ hoàn thành {emitted}/{total} đoạn.")

        except Exception as e:
            self.error.emit(f"❌ Lỗi: {str(e)}")
        finally:
            # Cleanup
            if self.tmpdir and os.path.exists(self.tmpdir):
                try:
                    import shutil
                    shutil.rmtree(self.tmpdir)
                except Exception:
                    pass

# ==================== BatchTranslateWorker - Worker xử lý nhiều file ====================

class BatchTranslateWorker(QThread):
    """
    Worker xử lý dịch thuật hàng loạt cho nhiều file
    """
    
    fileProgress = Signal(int, int)      # completed, total files
    fileStatus = Signal(str)             # status message
    attachWorker = Signal(object, str)   # worker, filename
    
    def __init__(self, files: list[str], source_lang: str, target_lang: str,
                 service: str, api_key: str, max_len: int, workers_chunk: int, 
                 workers_file: int, custom_prompt: str = ""):
        super().__init__()
        self.files = files
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.service = service
        self.api_key = api_key
        self.max_len = max_len
        self.workers_chunk = workers_chunk
        self.workers_file = max(1, workers_file)
        self.custom_prompt = custom_prompt
        self.stop_flag = False
        self.children: list[MultiThreadTranslateWorker] = []

    def stop(self):
        self.stop_flag = True
        for w in self.children:
            try:
                w.stop()
            except Exception:
                pass

    def run(self):
        total = len(self.files)
        done = 0
        self.fileStatus.emit(f"�� Xử lý {total} file với {self.workers_file} file song song...")
        
        idx = 0
        active: list[MultiThreadTranslateWorker] = []
        
        try:
            while idx < total or active:
                while idx < total and len(active) < self.workers_file and not self.stop_flag:
                    f = self.files[idx]
                    
                    # Đọc nội dung file
                    try:
                        with open(f, "r", encoding="utf-8") as file:
                            text = file.read()
                    except Exception as e:
                        self.fileStatus.emit(f"⚠️ Không thể đọc file {Path(f).name}: {e}")
                        idx += 1
                        continue
                    
                    w = MultiThreadTranslateWorker(
                        text, self.source_lang, self.target_lang, self.service,
                        self.api_key, self.max_len, self.workers_chunk, self.custom_prompt
                    )
                    self.children.append(w)
                    self.attachWorker.emit(w, Path(f).name)
                    w.start()
                    active.append(w)
                    idx += 1
                
                for w in list(active):
                    if not w.isRunning():
                        active.remove(w)
                        done += 1
                        self.fileProgress.emit(done, total)
                
                self.msleep(100)
                
        finally:
            self.fileStatus.emit("�� Hoàn tất batch.")

class TranslateTTSWorker(QThread):
    """
    Worker để tạo audio TTS cho các đoạn đã dịch
    Tự động phát audio khi hoàn thành mỗi đoạn
    """
    
    # Signals
    audio_ready = Signal(str, int, int)  # path, duration_ms, index
    tts_progress = Signal(int, int)      # completed, total
    tts_status = Signal(str)             # status message
    tts_error = Signal(str)              # error message
    
    def __init__(self, translated_segments: List[Tuple[str, str, int]], 
                 target_lang: str, voice: str = "", rate: int = 0, pitch: int = 0) -> None:
        """
        Khởi tạo worker TTS cho dịch thuật
        
        Args:
            translated_segments: List các tuple (original, translated, index)
            target_lang: Ngôn ngữ đích để chọn voice phù hợp
            voice: Voice cụ thể (nếu để trống sẽ tự động chọn)
            rate: Tốc độ (-50 đến 50)
            pitch: Cao độ (-12 đến 12)
        """
        super().__init__()
        
        self.translated_segments = translated_segments
        self.target_lang = target_lang
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.stop_flag = False
        self.tmpdir = None
        
    def stop(self) -> None:
        """Dừng worker"""
        self.stop_flag = True
        
    def run(self) -> None:
        """Chạy worker TTS"""
        try:
            if not self.translated_segments:
                self.tts_error.emit("Không có đoạn văn bản nào để tạo audio")
                return
                
            # Tạo thư mục tạm
            self.tmpdir = tempfile.mkdtemp(prefix="translate_tts_")
            
            total_segments = len(self.translated_segments)
            completed = 0
            
            self.tts_status.emit(f"Bắt đầu tạo audio cho {total_segments} đoạn văn bản...")
            
            for index, (original, translated, segment_index) in enumerate(self.translated_segments):
                if self.stop_flag:
                    break
                    
                try:
                    # Tạo audio cho đoạn đã dịch
                    audio_path = self._create_audio_for_segment(translated, segment_index)
                    
                    if audio_path and os.path.exists(audio_path):
                        # Sử dụng duration cố định dựa trên độ dài text
                        # Ước tính: 1 ký tự = 100ms, tối thiểu 1000ms
                        estimated_duration = max(1000, len(translated) * 100)
                        
                        # Emit signal audio ready
                        self.audio_ready.emit(audio_path, estimated_duration, segment_index)
                        
                        completed += 1
                        self.tts_progress.emit(completed, total_segments)
                        
                        # Tự động phát audio ngay khi hoàn thành
                        self.tts_status.emit(f"✅ Đã tạo audio cho đoạn {segment_index + 1}")
                        
                except Exception as e:
                    self.tts_error.emit(f"Lỗi tạo audio cho đoạn {segment_index + 1}: {str(e)}")
                    continue
                    
            if not self.stop_flag:
                self.tts_status.emit("🎵 Hoàn thành tạo audio cho tất cả đoạn văn bản!")
                
        except Exception as e:
            self.tts_error.emit(f"Lỗi trong quá trình tạo audio: {str(e)}")
        finally:
            # Cleanup
            # self._cleanup_temp_files()
            pass
                    
    def _cleanup_temp_files(self):
        """Cleanup temporary files"""
        if self.tmpdir and os.path.exists(self.tmpdir):
            try:
                import shutil
                shutil.rmtree(self.tmpdir)
                self.tmpdir = None
            except Exception as e:
                print(f"Warning: Error cleaning up temp files: {e}")
                
    def _create_audio_for_segment(self, text: str, segment_index: int) -> Optional[str]:
        """Tạo audio cho một đoạn văn bản"""
        try:
            # Tự động chọn voice nếu không có
            if not self.voice:
                self.voice = self._get_auto_voice(self.target_lang)
                
            # Tạo tên file
            filename = f"translate_segment_{segment_index:03d}_{int(time.time())}.mp3"
            output_path = os.path.join(self.tmpdir, filename)
            
            # Sử dụng TTS function từ helps.py với đúng signature
            from app.utils.helps import tts_sync_save
            
            # Signature: tts_sync_save(text, out_path, voice, rate_percent, pitch_hz)
            tts_sync_save(
                text=text,
                out_path=output_path,  # Sửa từ output_path thành out_path
                voice=self.voice,
                rate_percent=self.rate,  # Sửa từ rate thành rate_percent
                pitch_hz=self.pitch      # Sửa từ pitch thành pitch_hz
            )
            
            if os.path.exists(output_path):
                return output_path
            else:
                return None
                
        except Exception as e:
            print(f"Lỗi tạo audio: {e}")
            return None
            
    def _get_auto_voice(self, lang_code: str) -> str:
        """Tự động chọn voice phù hợp với ngôn ngữ"""
        voice_mapping = {
            "vi": "vi-VN-HoaiMyNeural",
            "en": "en-US-JennyNeural", 
            "ja": "ja-JP-NanamiNeural",
            "zh-CN": "zh-CN-XiaoxiaoNeural",
            "ko": "ko-KR-SunHiNeural",
            "fr": "fr-FR-DeniseNeural",
            "de": "de-DE-KatjaNeural",
            "es": "es-ES-ElviraNeural",
            "pt": "pt-BR-FranciscaNeural",
            "th": "th-TH-AcharaNeural",
            "ru": "ru-RU-SvetlanaNeural",
            "it": "it-IT-ElsaNeural"
        }
        
        return voice_mapping.get(lang_code, "en-US-JennyNeural")
        
    def __del__(self):
        """Destructor để đảm bảo cleanup"""
        try:
            if hasattr(self, 'tmpdir') and self.tmpdir:
                self._cleanup_temp_files()
        except:
            pass
