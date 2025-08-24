"""
Language Manager - Quản lý ngôn ngữ và voices cho TTS
"""

from typing import List, Dict, Optional, Tuple
from langdetect import detect
from .voices_data import voices_data


class LanguageManager:
    """Quản lý ngôn ngữ và voices cho TTS"""
    
    def __init__(self):
        """Khởi tạo Language Manager"""
        pass
    
    def get_voices_for_language(self, language_code: str) -> List[Dict]:
        """Lấy danh sách voices cho một ngôn ngữ cụ thể"""
        if language_code in voices_data:
            return voices_data[language_code]["voices"]
        return []
    
    def get_language_display_name(self, language_code: str) -> str:
        """Lấy tên hiển thị của ngôn ngữ từ mã ngôn ngữ"""
        if language_code in voices_data:
            return voices_data[language_code]["display_name"]
        return language_code
    
    def get_default_voice_for_language(self, language_code: str) -> str:
        """Lấy voice mặc định cho một ngôn ngữ cụ thể"""
        if language_code in voices_data and voices_data[language_code]["voices"]:
            # Trả về voice đầu tiên (thường là voice mặc định)
            return voices_data[language_code]["voices"][0]["shortname"]
        return "vi-VN-HoaiMyNeural"  # Fallback to Vietnamese
    
    def get_available_languages(self) -> List[Tuple[str, str]]:
        """Lấy danh sách tất cả ngôn ngữ có sẵn với mã và tên hiển thị"""
        return [("Tự phát hiện", "auto")] + [(voices_data[lang]["display_name"], lang) for lang in voices_data.keys()]
    
    def get_language_by_code(self, code: str) -> Optional[str]:
        """Lấy tên hiển thị của ngôn ngữ từ mã ngôn ngữ"""
        if code == "auto":
            return "Tự phát hiện"
        if code in voices_data:
            return voices_data[code]["display_name"]
        return None
    
    def get_voice_info(self, voice_name: str) -> Optional[Dict]:
        """Lấy thông tin chi tiết về một voice cụ thể"""
        for lang_code, lang_data in voices_data.items():
            for voice in lang_data["voices"]:
                if voice["shortname"] == voice_name:
                    return {
                        "language": lang_data["display_name"],
                        "language_code": lang_code,
                        "gender": voice["gender"],
                        "shortname": voice["shortname"],
                        "label": voice["label"]
                    }
        return None
    
    def get_voices_by_gender(self, language_code: str, gender: str = None) -> List[Dict]:
        """Lấy danh sách voices theo ngôn ngữ và giới tính (nếu có)"""
        if language_code not in voices_data:
            return []
        
        voices = voices_data[language_code]["voices"]
        if gender:
            return [v for v in voices if v["gender"] == gender]
        return voices
    
    def get_all_language_codes(self) -> List[str]:
        """Lấy danh sách tất cả mã ngôn ngữ có sẵn"""
        return list(voices_data.keys())
    
    def get_language_count(self) -> int:
        """Lấy tổng số ngôn ngữ có sẵn"""
        return len(voices_data)
    
    def get_voice_by_gender(self, language_code: str, gender: str) -> Optional[str]:
        """Lấy voice theo giới tính cho một ngôn ngữ cụ thể"""
        if language_code not in voices_data:
            return None
        
        for voice in voices_data[language_code]["voices"]:
            if voice["gender"] == gender:
                return voice["shortname"]
        return None
    
    def get_male_voice(self, language_code: str) -> Optional[str]:
        """Lấy voice nam cho một ngôn ngữ cụ thể"""
        return self.get_voice_by_gender(language_code, "Nam")
    
    def get_female_voice(self, language_code: str) -> Optional[str]:
        """Lấy voice nữ cho một ngôn ngữ cụ thể"""
        return self.get_voice_by_gender(language_code, "Nữ")
    
    def get_voice_display_name(self, voice_label: str) -> str:
        """Lấy tên hiển thị ngắn gọn của voice từ label đầy đủ"""
        try:
            # Tách phần "Gender - Name" từ "Gender - Name (shortname)"
            if " (" in voice_label:
                return voice_label.split(" (")[0]
            return voice_label
        except:
            return voice_label
    
    def detect_language_from_text(self, text: str) -> str:
        """Tự động phát hiện ngôn ngữ từ văn bản sử dụng langdetect"""
        try:
            if not text.strip():
                return "vi"  # Default to Vietnamese
            
            # Sử dụng langdetect để phát hiện ngôn ngữ
            detected_lang = detect(text)
            
            # Mapping một số mã ngôn ngữ phổ biến
            lang_mapping = {
                "zh-cn": "zh",  # Chinese simplified
                "zh-tw": "zh",  # Chinese traditional
            }
            
            detected_lang = lang_mapping.get(detected_lang, detected_lang)
            
            # Kiểm tra xem ngôn ngữ có được hỗ trợ không
            if self.is_language_supported(detected_lang):
                return detected_lang
            else:
                # Fallback to Vietnamese if not supported
                return "vi"
                
        except Exception as e:
            print(f"Error detecting language: {e}")
            return "vi"  # Fallback to Vietnamese
    
    def is_language_supported(self, language_code: str) -> bool:
        """Kiểm tra xem một ngôn ngữ có được hỗ trợ không"""
        return language_code in voices_data
    
    def get_voice_display_name(self, voice_label: str) -> str:
        """Lấy tên hiển thị ngắn gọn của voice (ví dụ: "Nam - NamMinh")"""
        if " (" in voice_label:
            return voice_label.split(" (")[0]
        return voice_label
    
    def extract_voice_name_from_label(self, voice_label: str) -> Optional[str]:
        """Trích xuất voice name từ label (ví dụ: "Nam - NamMinh" -> "vi-VN-NamMinhNeural")"""
        try:
            # Nếu là "Tự phát hiện", trả về None để xử lý tự động
            if voice_label == "Tự phát hiện":
                return None
            
            # Tìm trong voices_data bằng cách so sánh phần display name
            for lang_code, lang_data in voices_data.items():
                for voice in lang_data["voices"]:
                    # Lấy phần display name từ label gốc: "Nam - NamMinh (vi-VN-NamMinhNeural)" -> "Nam - NamMinh"
                    display_name = self.get_voice_display_name(voice["label"])
                    if display_name == voice_label:
                        return voice["shortname"]
            
            return None
            
        except Exception as e:
            print(f"Error extracting voice name: {e}")
            return None
    
    def populate_voices_for_language(self, language_code: str, include_auto_detect: bool = True) -> List[str]:
        """Lấy danh sách tên hiển thị voices cho một ngôn ngữ cụ thể"""
        voices = []
        
        if include_auto_detect:
            voices.append("Tự phát hiện")
        
        if language_code in voices_data:
            for voice in voices_data[language_code]["voices"]:
                display_name = self.get_voice_display_name(voice["label"])
                voices.append(display_name)
        
        return voices
    
    def code_by_name(self, name: str) -> str:
        """Lấy mã ngôn ngữ từ tên hiển thị"""
        if name == "Tự phát hiện":
            return "auto"
        
        for lang_code, lang_data in voices_data.items():
            if lang_data["display_name"] == name:
                return lang_code
        return "auto"
    
    def name_by_code(self, code: str) -> str:
        """Lấy tên hiển thị từ mã ngôn ngữ"""
        if code.lower() == "auto":
            return "Tự phát hiện"
        
        if code.lower() in voices_data:
            return voices_data[code.lower()]["display_name"]
        return code


# Tạo instance global để sử dụng
language_manager = LanguageManager()
