import sys
import os
import json
import asyncio
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (
    QThread, Signal, QObject, Qt, QUrl, QPoint, QTimer, QEasingCurve, QPropertyAnimation
)
from PySide6.QtGui import QDesktopServices, QAction, QMouseEvent
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QComboBox, QMessageBox, QFileDialog,
    QListWidget, QListWidgetItem, QMenu, QSlider, QFrame,
    QMainWindow, QTabWidget, QProgressBar, QGroupBox, QFormLayout,
    QLineEdit, QSplitter, QGraphicsOpacityEffect
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

import edge_tts
import pygame
try:
    from ui_setting import _init_addStyle  # có thì dùng, không có thì bỏ qua
except Exception:
    def _init_addStyle(*args, **kwargs): ...
os.environ.setdefault("SDL_AUDIODRIVER", "directsound")


# ========================= Helpers =========================
def human_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for u in units:
        if size < 1024.0 or u == units[-1]:
            return f"{size:.0f} {u}" if u == "B" else f"{size:.2f} {u}"
        size /= 1024.0


def human_duration(sec: float | None) -> str:
    if sec is None or sec <= 0:
        return "?"
    sec = int(round(sec))
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    if h > 0:
        return f"{h}h{m:02d}m{s:02d}s"
    if m > 0:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def mmss(ms: int) -> str:
    if ms <= 0:
        return "0:00"
    sec = ms // 1000
    m = sec // 60
    s = sec % 60
    return f"{m}:{s:02d}"


def audio_duration_seconds(path: Path) -> float | None:
    try:
        from mutagen import File as MutagenFile  # type: ignore
        mf = MutagenFile(str(path))
        if mf is not None and getattr(mf, "info", None):
            dur = getattr(mf.info, "length", None)
            if dur:
                return float(dur)
    except Exception:
        pass
    try:
        snd = pygame.mixer.Sound(str(path))
        return float(snd.get_length())
    except Exception:
        return None


# ========================= AppBus (kênh chia sẻ) =========================
class AppBus(QObject):
    append_output = Signal(str)     # log dùng chung
    set_progress = Signal(int)      # progress dùng chung
    add_history_path = Signal(str)  # thêm item lịch sử
    toggle_history = Signal(bool)   # bật/tắt drawer lịch sử


# ========================= Worker Edge TTS =========================
class EdgeTTSWorker(QObject):
    finished = Signal()
    error = Signal(str)
    status = Signal(str)
    progress = Signal(int)
    file_ready = Signal(str)

    def __init__(self, text: str, lang_code: str, gender: str, rate: int, save_path: Path | None = None):
        super().__init__()
        self.text = text
        self.lang_code = (lang_code or "vi").lower().strip()
        self.gender = (gender or "Female").capitalize()
        self.rate = rate
        self.save_path = Path(save_path) if save_path else None
        self.audio_root = Path.cwd() / "audio"
        self.audio_root.mkdir(parents=True, exist_ok=True)
        self.last_voice = None

    def run(self):
        try:
            asyncio.run(self._run_async())
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    async def _run_async(self):
        self.status.emit("Đang chọn voice phù hợp…")
        self.progress.emit(10)
        voice = await self._pick_voice(self.lang_code, self.gender)
        self.last_voice = voice
        if not voice:
            raise RuntimeError(
                f"Không tìm thấy voice cho ngôn ngữ '{self.lang_code}'.")

        pct = max(-50, min(50, (self.rate - 150)))
        ssml_text = (
            f"<speak version='1.0' xml:lang='{voice.split('-')[0]}'>"
            f"<prosody rate='{pct}%'>{self._escape_ssml(self.text)}</prosody></speak>"
        )

        self.status.emit("Đang tổng hợp giọng nói…")
        self.progress.emit(40)
        tts = edge_tts.Communicate(ssml_text, voice)

        # Lưu: audio/YYYY-MM-DD/tts_YYYYMMDD_HHMMSS.mp3
        if self.save_path is None:
            day_dir = self.audio_root / datetime.now().strftime("%Y-%m-%d")
            day_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = day_dir / f"tts_{timestamp}.mp3"
            idx = 1
            while out_path.exists():
                out_path = day_dir / f"tts_{timestamp}_{idx}.mp3"
                idx += 1
        else:
            out_path = self.save_path

        await tts.save(str(out_path))

        # metadata
        try:
            meta_txt = out_path.with_suffix(".txt")
            meta_txt.write_text(
                f"Created: {datetime.now():%Y-%m-%d %H:%M:%S}\n"
                f"Lang: {self.lang_code}\nGender: {self.gender}\n"
                f"Voice: {self.last_voice}\nRate(50-250): {self.rate}\n\n"
                f"----- TEXT -----\n{self.text}", encoding="utf-8"
            )
        except Exception as e:
            self.status.emit(f"Không thể lưu .txt: {e}")

        self.file_ready.emit(str(out_path))
        self.progress.emit(100)
        self.status.emit(f"Đã tạo: {out_path.name}")

    async def _pick_voice(self, lang_code: str, prefer_gender: str) -> str | None:
        voices = await edge_tts.list_voices()
        lang_code = lang_code.lower()
        def match_locale(v): return v.get(
            "Locale", "").lower().startswith(lang_code)
        candidates = [v for v in voices if match_locale(v)]
        if not candidates:
            return None
        for v in candidates:
            if v.get("Gender", "").lower() == prefer_gender.lower():
                return v.get("ShortName")
        return candidates[0].get("ShortName")

    @staticmethod
    def _escape_ssml(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ========================= Scrim (nền mờ) =========================
class Scrim(QWidget):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#0B122033;")  # đen 20%
        self._eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._eff)
        self._eff.setOpacity(0.0)
        self.hide()

    def mousePressEvent(self, e: QMouseEvent):
        self.clicked.emit()
        super().mousePressEvent(e)

    def fade_to(self, target: float, dur=180):
        anim = QPropertyAnimation(self._eff, b"opacity", self)
        anim.setDuration(dur)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.setStartValue(self._eff.opacity())
        anim.setEndValue(target)
        anim.start()
        self._anim = anim


# ========================= History Drawer (overlay) =========================
class HistoryDrawer(QFrame):
    playRequested = Signal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HistoryDrawer")
        self.setStyleSheet("""
        #HistoryDrawer { background-color:#0f172a; border-left:1px solid rgba(255,255,255,0.08); }
        QListWidget { background:#0f172a; border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:8px; }
        QListWidget::item { border-bottom:1px solid rgba(255,255,255,0.06); padding:10px 6px; }
        QListWidget::item:selected { background:rgba(255,255,255,0.06); }
        QPushButton { border-radius:8px; padding:6px 10px; }
        """)
        self.setFixedWidth(420)
        self.audio_root = Path.cwd() / "audio"

        lay = QVBoxLayout(self)
        hdr = QHBoxLayout()
        hdr.addWidget(QLabel("Lịch sử chuyển đổi"))
        hdr.addStretch(1)
        btn_clear = QPushButton("🗑️ Xóa tất cả")
        btn_clear.clicked.connect(self._clear_all)
        hdr.addWidget(btn_clear)
        lay.addLayout(hdr)

        self.lst = QListWidget()
        self.lst.setSelectionMode(QListWidget.SingleSelection)
        self.lst.itemDoubleClicked.connect(self._on_play_selected)
        self.lst.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lst.customContextMenuRequested.connect(self._on_context_menu)
        lay.addWidget(self.lst, 1)

        rowb = QHBoxLayout()
        self.btn_play = QPushButton("▶️ Phát")
        self.btn_play.clicked.connect(self._on_play_selected)
        self.btn_del = QPushButton("🗑️ Xóa")
        self.btn_del.clicked.connect(self._delete_selected)
        self.btn_open = QPushButton("📂 Thư mục")
        self.btn_open.clicked.connect(self._open_root)
        for b in (self.btn_play, self.btn_del, self.btn_open):
            rowb.addWidget(b)
        lay.addLayout(rowb)

        self.refresh()

    # API
    def refresh(self):
        self.lst.clear()
        if not self.audio_root.exists():
            return
        files = []
        for p in self.audio_root.rglob("*.mp3"):
            try:
                files.append((p.stat().st_mtime, p))
            except FileNotFoundError:
                pass
        files.sort(key=lambda t: t[0], reverse=True)
        for _, p in files:
            self._add_item(p, False)

    def add_item_top(self, p: Path): self._add_item(p, True)

    # Internals
    def _add_item(self, p: Path, insert_top: bool):
        if not p.exists():
            return
        try:
            st = p.stat()
            mtime = datetime.fromtimestamp(
                st.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            size = human_size(st.st_size)
            dur = human_duration(audio_duration_seconds(p))
        except Exception:
            mtime = size = dur = "?"
        text = f"{p.name}\n{mtime} · {dur} · {size}"
        it = QListWidgetItem(text)
        it.setData(Qt.UserRole, str(p))
        if insert_top:
            self.lst.insertItem(0, it)
            self.lst.setCurrentItem(it)
        else:
            self.lst.addItem(it)

    def _sel(self) -> Path | None:
        it = self.lst.currentItem()
        if not it:
            QMessageBox.information(self, "Chú ý", "Hãy chọn một file.")
            return None
        p = Path(it.data(Qt.UserRole))
        if not p.exists():
            QMessageBox.warning(self, "Không tìm thấy",
                                f"File không còn tồn tại:\n{p}")
            self.refresh()
            return None
        return p

    def _on_play_selected(self):
        p = self._sel()
        if p:
            self.playRequested.emit(p)

    def _delete_selected(self):
        p = self._sel()
        if not p:
            return
        ret = QMessageBox.question(self, "Xác nhận", f"Xóa {p.name} và .txt kèm theo?",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ret != QMessageBox.Yes:
            return
        try:
            for ext in (".mp3", ".txt"):
                f = p.with_suffix(ext)
                if f.exists():
                    f.unlink(missing_ok=True)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi xóa", str(e))

    def _open_root(self):
        root = self.audio_root
        if os.name == "nt":
            os.startfile(root)  # type: ignore[attr-defined]
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(root)))

    def _on_context_menu(self, pos):
        it = self.lst.itemAt(pos)
        if not it:
            return
        self.lst.setCurrentItem(it)
        menu = QMenu(self)
        menu.addAction("▶️ Phát", self._on_play_selected)
        menu.addAction("📂 Mở thư mục chứa",
                       lambda: self._open_containing_dir(Path(it.data(Qt.UserRole))))
        menu.addSeparator()
        menu.addAction("🗑️ Xóa (kèm .txt)", self._delete_selected)
        menu.exec(self.lst.mapToGlobal(pos))

    def _open_containing_dir(self, p: Path):
        folder = p.parent
        if os.name == "nt":
            try:
                os.startfile(folder)  # type: ignore[attr-defined]
            except Exception:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _clear_all(self):
        ret = QMessageBox.question(self, "Xác nhận", "Xóa tất cả lịch sử audio (mp3 + txt)?",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ret != QMessageBox.Yes:
            return
        cnt = 0
        for p in self.audio_root.rglob("*.mp3"):
            try:
                txt = p.with_suffix(".txt")
                if txt.exists():
                    txt.unlink(missing_ok=True)
                p.unlink(missing_ok=True)
                cnt += 1
            except Exception:
                pass
        self.refresh()
        QMessageBox.information(self, "Hoàn tất", f"Đã xóa {cnt} mục.")


# ========================= Tab TTS (gộp vào trái) =========================
class TTSTab(QWidget):
    def __init__(self, bus: AppBus):
        super().__init__()
        self.bus = bus
        self.worker_thread: QThread | None = None
        self.worker: EdgeTTSWorker | None = None

        self.audio_root = Path.cwd() / "audio"
        self.audio_root.mkdir(parents=True, exist_ok=True)

        # Player
        self.player = QMediaPlayer(self)
        self.audio_out = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_out)

        self._build_ui()
        try:
            _init_addStyle(self)
        except Exception:
            pass

        # Player signals
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.playbackStateChanged.connect(
            self._on_playback_state_changed)

    def _build_ui(self):
        root = QVBoxLayout(self)

        left = QVBoxLayout()
        left.addWidget(QLabel("Nội dung cần nói:"))
        self.txt = QTextEdit(placeholderText="Nhập văn bản tại đây…")
        self.txt.setPlainText("Xin chào! Đây là giọng nói tiếng Việt.")
        left.addWidget(self.txt)

        row = QHBoxLayout()
        row.addWidget(QLabel("Ngôn ngữ:"))
        self.cmb_lang = QComboBox()
        for label, code in [
            ("Vietnamese (vi)", "vi"), ("English US (en-US)", "en-US"),
            ("English UK (en-GB)", "en-GB"), ("Japanese (ja)", "ja"),
            ("Korean (ko)", "ko"), ("Chinese (zh-CN)", "zh-CN"),
            ("French (fr-FR)", "fr-FR"), ("German (de-DE)", "de-DE"),
            ("Spanish (es-ES)", "es-ES"),
        ]:
            self.cmb_lang.addItem(label, code)
        self.cmb_lang.setCurrentIndex(0)
        row.addWidget(self.cmb_lang)

        row.addWidget(QLabel("Giới tính:"))
        self.cmb_gender = QComboBox()
        self.cmb_gender.addItems(["Female", "Male", "Any"])
        self.cmb_gender.setCurrentText("Female")
        row.addWidget(self.cmb_gender)

        row.addWidget(QLabel("Tốc độ:"))
        self.sld_rate = QSlider(Qt.Horizontal)
        self.sld_rate.setRange(50, 250)
        self.sld_rate.setValue(150)
        self.sld_rate.setTickInterval(10)
        self.sld_rate.setTickPosition(QSlider.TicksBelow)
        self.sld_rate.setSingleStep(1)
        self.sld_rate.setPageStep(10)
        self.sld_rate.setFixedWidth(160)
        row.addWidget(self.sld_rate)

        self.lbl_rate_val = QLabel("150")
        self.sld_rate.valueChanged.connect(
            lambda v: self.lbl_rate_val.setText(str(v)))
        row.addWidget(self.lbl_rate_val)
        left.addLayout(row)

        btns = QHBoxLayout()
        self.btn_say = QPushButton("▶️ Phát")
        self.btn_save = QPushButton("💾 Lưu")
        self.btn_stop = QPushButton("⏹️ Dừng")
        btns.addWidget(self.btn_say)
        btns.addWidget(self.btn_save)
        btns.addWidget(self.btn_stop)
        left.addLayout(btns)

        # Nút bật/tắt drawer lịch sử (overlay bên phải)
        self.btn_toggle_history = QPushButton("📜 Lịch sử (bên phải)")
        self.btn_toggle_history.setCheckable(True)
        self.btn_toggle_history.toggled.connect(self.bus.toggle_history)
        left.addWidget(self.btn_toggle_history)

        self.lbl_status = QLabel("Sẵn sàng.")
        left.addWidget(self.lbl_status)
        root.addLayout(left)

        # Player bar
        player_bar = QHBoxLayout()
        self.player_panel = QFrame()
        pnl = QHBoxLayout(self.player_panel)
        pnl.setContentsMargins(8, 8, 8, 8)

        self.btn_player_play = QPushButton("⏵")
        self.btn_player_play.setFixedWidth(36)
        self.btn_player_play.clicked.connect(self._toggle_play_pause)
        pnl.addWidget(self.btn_player_play)

        self.lbl_time_cur = QLabel("0:00")
        self.lbl_time_tot = QLabel("/ 0:00")
        pnl.addWidget(self.lbl_time_cur)

        self.sld_position = QSlider(Qt.Horizontal)
        self.sld_position.setRange(0, 0)
        self.sld_position.sliderPressed.connect(self._position_slider_pressed)
        self.sld_position.sliderReleased.connect(
            self._position_slider_released)
        self.sld_position.sliderMoved.connect(self._position_slider_moved)
        pnl.addWidget(self.sld_position, stretch=1)
        pnl.addWidget(self.lbl_time_tot)

        self.lbl_vol = QLabel("🔊")
        pnl.addWidget(self.lbl_vol)
        self.sld_volume = QSlider(Qt.Horizontal)
        self.sld_volume.setRange(0, 100)
        self.sld_volume.setValue(80)
        self.sld_volume.setFixedWidth(140)
        self.sld_volume.valueChanged.connect(
            lambda v: self.audio_out.setVolume(v/100.0))
        pnl.addWidget(self.sld_volume)

        self.player_panel.hide()
        player_bar.addWidget(self.player_panel)
        root.addLayout(player_bar)

        # Connect worker buttons
        self.btn_say.clicked.connect(self.on_say)
        self.btn_save.clicked.connect(self.on_save)
        self.btn_stop.clicked.connect(self.on_stop)

        self._seeking = False

    # Worker control
    def on_say(self): self._start_worker(play_only=True)

    def on_save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Lưu file âm thanh", "tts_output.mp3", "MP3 Files (*.mp3)")
        if path:
            self._start_worker(play_only=False, save_path=path)

    def on_stop(self):
        self.player.stop()
        self.lbl_status.setText("Đã dừng.")
        self.bus.append_output.emit("Đã dừng phát.")

    def _start_worker(self, play_only=True, save_path=None):
        text = self.txt.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Thiếu nội dung",
                                "Hãy nhập văn bản cần đọc.")
            return
        lang_code = self.cmb_lang.currentData() or "vi"
        gender = self.cmb_gender.currentText()
        if gender == "Any":
            gender = "Female"
        rate = self.sld_rate.value()

        self.btn_say.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.lbl_status.setText("Đang xử lý…")
        # show progress (MainWindow quyết định hiện)
        self.bus.set_progress.emit(1)

        self.worker_thread = QThread()
        self.worker = EdgeTTSWorker(
            text, lang_code, gender, rate, save_path=save_path)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.status.connect(self._on_worker_status)
        self.worker.progress.connect(self.bus.set_progress)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self._finished_tts)
        self.worker.file_ready.connect(self._on_file_ready)
        self.worker_thread.start()

    def _on_worker_status(self, msg: str):
        self.lbl_status.setText(msg)
        self.bus.append_output.emit(msg)

    def _on_error(self, msg: str):
        QMessageBox.critical(self, "Lỗi", msg)
        self.bus.append_output.emit("Lỗi: " + msg)

    def _finished_tts(self):
        self.btn_say.setEnabled(True)
        self.btn_save.setEnabled(True)
        self.bus.set_progress.emit(100)
        self.bus.append_output.emit("Sẵn sàng.")
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread = None
            self.worker = None

    def _on_file_ready(self, path_str: str):
        p = Path(path_str)
        self._play_external(p)
        self.bus.add_history_path.emit(str(p))
        self.bus.append_output.emit(f"Đã tạo file: {p.name}")

    # Player helpers
    def _play_external(self, p: Path):
        self.player.setSource(QUrl.fromLocalFile(str(p)))
        self.player_panel.show()
        self.player.play()
        self.lbl_status.setText(f"Trình phát: {p.name}")

    def _toggle_play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _on_duration_changed(self, dur_ms: int):
        self.sld_position.setRange(0, max(0, dur_ms))
        self.lbl_time_tot.setText(f"/ {mmss(dur_ms)}")

    def _on_position_changed(self, pos_ms: int):
        if not self._seeking:
            self.sld_position.setValue(pos_ms)
        self.lbl_time_cur.setText(mmss(pos_ms))

    def _position_slider_pressed(self): self._seeking = True

    def _position_slider_released(self):
        self.player.setPosition(self.sld_position.value())
        self._seeking = False

    def _position_slider_moved(self, v: int):
        self.lbl_time_cur.setText(mmss(v))

    def _on_playback_state_changed(self, state):
        self.btn_player_play.setText(
            "⏸" if state == QMediaPlayer.PlayingState else "⏵")


# ========================= Key Manager (dưới tabs) =========================
class KeyManagerWidget(QGroupBox):
    def __init__(self, bus: AppBus, title="Quản lý API Keys", store_path: Path | None = None):
        super().__init__(title)
        self.bus = bus
        self.store_path = store_path or (Path.cwd() / "keys.json")
        lay = QFormLayout(self)
        self.edt_openai = QLineEdit()
        self.edt_openai.setEchoMode(QLineEdit.Password)
        self.edt_azure = QLineEdit()
        self.edt_azure.setEchoMode(QLineEdit.Password)
        self.btn_save = QPushButton("💾 Lưu")
        lay.addRow("OpenAI Key:", self.edt_openai)
        lay.addRow("Azure Key:", self.edt_azure)
        lay.addRow("", self.btn_save)
        self.btn_save.clicked.connect(self.save_keys)
        self.load_keys()

    def load_keys(self):
        if self.store_path.exists():
            try:
                data = json.load(open(self.store_path, "r", encoding="utf-8"))
                self.edt_openai.setText(data.get("openai", ""))
                self.edt_azure.setText(data.get("azure", ""))
                self.bus.append_output.emit("Đã nạp keys.")
            except Exception as e:
                self.bus.append_output.emit(f"Lỗi đọc keys: {e}")

    def save_keys(self):
        try:
            self.store_path.write_text(json.dumps({
                "openai": self.edt_openai.text().strip(),
                "azure": self.edt_azure.text().strip()
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            self.bus.append_output.emit(f"Đã lưu keys → {self.store_path}")
            QMessageBox.information(self, "Thành công", "Đã lưu keys.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", str(e))
            self.bus.append_output.emit("Lỗi lưu keys: " + str(e))


# ========================= Main Window =========================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Edge TTS · Drawer lịch sử bên phải")

        # Menu
        m_file = self.menuBar().addMenu("&File")
        m_file.addAction("Thoát", self.close)
        m_help = self.menuBar().addMenu("&Help")
        m_help.addAction("About", lambda: QMessageBox.information(
            self, "About", "Demo TTS với drawer lịch sử."))

        # Bus
        self.bus = AppBus()
        self.bus.append_output.connect(self._append_output)
        self.bus.set_progress.connect(self._set_progress)
        self.bus.add_history_path.connect(self._on_new_history_item)
        self.bus.toggle_history.connect(self._toggle_history_pane)

        # Splitter trái/phải (phần phải chỉ để nội dung chính; drawer nằm overlay)
        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        # ===== Trái: Tabs + Key + Output + Progress
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.tabs = QTabWidget()
        self.tab_tts = TTSTab(self.bus)
        self.tabs.addTab(self.tab_tts, "TTS")
        dummy = QWidget()
        dummy.setLayout(QVBoxLayout())
        dummy.layout().addWidget(QLabel("Tab khác…"))
        self.tabs.addTab(dummy, "Khác")
        left_layout.addWidget(self.tabs)

        self.key_mgr = KeyManagerWidget(self.bus)
        left_layout.addWidget(self.key_mgr)

        self.output_list = QListWidget()
        left_layout.addWidget(self.output_list)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.hide()  # ⟵ mặc định ẩn
        left_layout.addWidget(self.progress)

        splitter.addWidget(left)
        # panel phải chỉ là “đệm” để người dùng kéo tỉ lệ nếu muốn
        right_pad = QWidget()
        right_pad.setLayout(QVBoxLayout())
        splitter.addWidget(right_pad)
        splitter.setSizes([900, 200])

        try:
            _init_addStyle(self)
        except Exception:
            pass

        # ===== Overlay: Scrim + Drawer (không nằm trong splitter)
        self.scrim = Scrim(self)
        self.scrim.hide()
        self.scrim.clicked.connect(lambda: self._show_history_overlay(False))

        self.drawer = HistoryDrawer(self)
        self.drawer.hide()
        self.drawer.playRequested.connect(self.tab_tts._play_external)

    # overlay show/hide
    def _toggle_history_pane(self, show: bool):
        self._show_history_overlay(show)

    def _show_history_overlay(self, show: bool):
        w = self.drawer.width()
        h = self.height()
        if show:
            self.scrim.setGeometry(self.rect())
            self.scrim.show()
            self.scrim.fade_to(1.0, 160)
            self.drawer.setGeometry(self.width(), 0, w, h)
            self.drawer.show()
            self.drawer.raise_()
            anim = QPropertyAnimation(self.drawer, b"pos", self)
            anim.setDuration(220)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.setStartValue(self.drawer.pos())
            anim.setEndValue(QPoint(self.width()-w, 0))
            anim.start()
            self._anim_drawer = anim
        else:
            anim = QPropertyAnimation(self.drawer, b"pos", self)
            anim.setDuration(200)
            anim.setEasingCurve(QEasingCurve.InCubic)
            anim.setStartValue(self.drawer.pos())
            anim.setEndValue(QPoint(self.width(), 0))
            anim.finished.connect(lambda: self.drawer.hide())
            anim.start()
            self._anim_drawer = anim
            self.scrim.fade_to(0.0, 140)

            def _hide_if_done():
                if self.scrim.graphicsEffect().opacity() <= 0.01:
                    self.scrim.hide()
            self._anim_drawer.finished.connect(_hide_if_done)

    # progress & output (chung)
    def _append_output(self, text: str):
        self.output_list.addItem(text)
        self.output_list.scrollToBottom()

    def _set_progress(self, val: int):
        # show khi đang chạy, ẩn lại khi xong
        if 0 < val < 100 and not self.progress.isVisible():
            self.progress.show()
        self.progress.setValue(max(0, min(100, val)))
        if val >= 100 or val <= 0:
            QTimer.singleShot(250, self.progress.hide)

    def _on_new_history_item(self, path_str: str):
        if self.drawer.isVisible():
            self.drawer.add_item_top(Path(path_str))

    # đảm bảo overlay phủ đúng
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.scrim.setGeometry(self.rect())
        if self.drawer.isVisible():
            self.drawer.setGeometry(
                self.width()-self.drawer.width(), 0, self.drawer.width(), self.height())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
