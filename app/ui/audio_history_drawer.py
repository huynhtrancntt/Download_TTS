from PySide6.QtCore import Qt, Signal, QPoint, QUrl, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, QMessageBox, QMenu
from PySide6.QtGui import QDesktopServices

import os
from pathlib import Path
from datetime import datetime

from app.core.config import AppConfig


def _human_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(max(0, num_bytes))
    for u in units:
        if size < 1024.0 or u == units[-1]:
            return f"{size:.0f} {u}" if u == "B" else f"{size:.2f} {u}"
        size /= 1024.0


class AudioHistoryDrawer(QFrame):
    """Right-side sliding drawer listing exported MP3 files with actions."""

    playRequested = Signal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AudioHistoryDrawer")
        self.setStyleSheet("""
        #AudioHistoryDrawer { background-color:#0f172a; border-left:1px solid rgba(255,255,255,0.08); }
        QListWidget { background:#0f172a; border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:8px; }
        QListWidget::item { border-bottom:1px solid rgba(255,255,255,0.06); padding:10px 6px; }
        QListWidget::item:selected { background:rgba(255,255,255,0.06); }
        QPushButton { border-radius:8px; padding:6px 10px; }
        """)
        self.setFixedWidth(420)
        self.audio_root = Path(AppConfig.OUTPUT_DIR)

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

    def add_item_top(self, p: Path):
        self._add_item(p, True)

    def _add_item(self, p: Path, insert_top: bool):
        if not p.exists():
            return
        try:
            st = p.stat()
            mtime = datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            size = _human_size(st.st_size)
            dur = "?"
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
            QMessageBox.warning(self, "Không tìm thấy", f"File không còn tồn tại:\n{p}")
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
        ret = QMessageBox.question(self, "Xác nhận", f"Xóa {p.name}?",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ret != QMessageBox.Yes:
            return
        try:
            if p.exists():
                p.unlink(missing_ok=True)
            # Also remove sidecar .txt if present
            pt = p.with_suffix('.txt')
            if pt.exists():
                pt.unlink(missing_ok=True)
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


