# -*- coding: utf-8 -*-
"""
Core module for TTS application
"""

from .audio_player import AudioPlayer, ClickSlider
from .language_manager import LanguageManager, language_manager

__all__ = [
    'AudioPlayer',
    'ClickSlider',
    'LanguageManager',
    'language_manager'
]
