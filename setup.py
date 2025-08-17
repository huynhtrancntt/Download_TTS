#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup script cho ứng dụng Download TTS
Hỗ trợ cài đặt và phân phối dễ dàng
"""

from setuptools import setup, find_packages
import os
import sys

# Đọc README để làm description
def read_readme():
    try:
        with open("README.md", "r", encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return "Ứng dụng Text-to-Speech với giao diện PySide6"

# Đọc requirements
def read_requirements():
    try:
        with open("requirements.txt", "r", encoding="utf-8") as fh:
            return [line.strip() for line in fh if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        return [
            "PySide6>=6.0.0",
            "pydub>=0.25.0",
            "edge-tts>=6.0.0",
        ]

# Kiểm tra Python version
if sys.version_info < (3, 8):
    sys.exit("Python 3.8+ is required!")

# Cấu hình setup
setup(
    name="download-tts",
    version="1.0.0",
    author="Tác giả",
    author_email="author@example.com",
    description="Ứng dụng Text-to-Speech với giao diện PySide6",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/username/download-tts",
    project_urls={
        "Bug Reports": "https://github.com/username/download-tts/issues",
        "Source": "https://github.com/username/download-tts",
        "Documentation": "https://github.com/username/download-tts#readme",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Software Development :: User Interfaces",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-qt>=4.0",
            "black>=22.0",
            "flake8>=4.0",
            "mypy>=0.950",
        ],
        "build": [
            "pyinstaller>=5.0",
            "setuptools>=60.0",
            "wheel>=0.37",
        ],
    },
    entry_points={
        "console_scripts": [
            "download-tts=main:main",
        ],
        "gui_scripts": [
            "download-tts-gui=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "app": [
            "*.py",
            "ui/*.py",
            "tabs/*.py",
            "core/*.py",
            "history/*.py",
            "utils/*.py",
        ],
    },
    data_files=[
        ("images", [
            "images/icon.ico",
            "images/down-arrow.png",
            "images/down.png",
            "images/up.png",
            "images/update.ico",
        ]),
        ("", [
            "run.bat",
            "demo.txt",
        ]),
    ],
    keywords=[
        "text-to-speech",
        "tts",
        "audio",
        "speech-synthesis",
        "pyside6",
        "gui",
        "desktop-app",
        "edge-tts",
        "microsoft",
        "vietnamese",
        "multilingual",
    ],
    platforms=["Windows", "Linux", "macOS"],
    license="MIT",
    zip_safe=False,
)
