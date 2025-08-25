# -*- coding: utf-8 -*-
import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QFileDialog, QHBoxLayout,
    QAbstractItemView
)
from PySide6.QtWidgets import QHeaderView
from app.workers.translate_workers import MultiThreadTranslateWorker
from PySide6.QtWidgets import QProgressBar


def parse_srt(text: str):
    """Trả về danh sách [(index, timestamp, content), ...] nếu hợp lệ."""
    blocks = text.strip().split("\n\n")

    timestamp_pattern = re.compile(
        r"^\d{2}:\d{2}:\d{2},\d{3}\s-->\s\d{2}:\d{2}:\d{2},\d{3}$"
    )

    results = []

    for i, block in enumerate(blocks, start=1):
        lines = block.strip().splitlines()

        if len(lines) < 3:
            return None

        if not lines[0].isdigit() or int(lines[0]) != i:
            return None

        if not timestamp_pattern.match(lines[1]):
            return None

        content = " ".join(lines[2:])
        results.append((i, lines[1], content))

    return results


class SRTChecker(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kiểm tra, Chỉnh sửa & Dịch SRT")
        self.resize(800, 500)

        layout = QVBoxLayout(self)

        # Ô nhập nội dung
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Dán nội dung SRT vào đây...")
        layout.addWidget(self.text_edit)

        # Nút kiểm tra
        self.btn_check = QPushButton("Kiểm tra & Hiển thị")
        self.btn_check.clicked.connect(self.check_and_show)
        layout.addWidget(self.btn_check)

        # Bảng hiển thị (thêm cột Dịch)
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Thời gian", "Nội dung", "Dịch"])
        self.table.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.table.setWordWrap(True)
        # Tự giãn cột nội dung và dịch theo chiều ngang, tự tính chiều cao dòng
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(
            0, QHeaderView.ResizeToContents)  # Thời gian
        header.setSectionResizeMode(
            1, QHeaderView.Stretch)           # Nội dung
        header.setSectionResizeMode(2, QHeaderView.Stretch)           # Dịch
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        layout.addWidget(self.table)

        # Nhóm nút dịch
        btn_layout = QHBoxLayout()
        self.btn_translate_all = QPushButton("Dịch tất cả")
        self.btn_translate_all.clicked.connect(self.translate_all)
        btn_layout.addWidget(self.btn_translate_all)

        layout.addLayout(btn_layout)

        # Nút mở và lưu
        btn_file_layout = QHBoxLayout()
        self.btn_open = QPushButton("Mở file SRT…")
        self.btn_open.clicked.connect(self.open_srt)
        btn_file_layout.addWidget(self.btn_open)

        self.btn_save = QPushButton("Lưu ra file SRT (có dịch)")
        self.btn_save.clicked.connect(self.save_srt)
        btn_file_layout.addWidget(self.btn_save)
        layout.addLayout(btn_file_layout)

        # Thanh tiến trình dịch
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

    def check_and_show(self):
        text = self.text_edit.toPlainText()
        result = parse_srt(text)

        if result is None:
            QMessageBox.warning(
                self, "Kết quả", "❌ Không phải định dạng SRT hợp lệ")
            return

        self.table.setRowCount(len(result))
        for row, (_index, timestamp, content) in enumerate(result):
            self.table.setItem(row, 0, QTableWidgetItem(timestamp))
            self.table.setItem(row, 1, QTableWidgetItem(content))
            self.table.setItem(row, 2, QTableWidgetItem("")
                               )  # cột dịch ban đầu trống
        self.table.resizeRowsToContents()

    def _on_row_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        timestamp_item = self.table.item(row, 0)
        content_item = self.table.item(row, 1)
        trans_item = self.table.item(row, 2)
        timestamp = timestamp_item.text() if timestamp_item else ""
        content = content_item.text() if content_item else ""
        trans = trans_item.text() if trans_item else ""

        # Bind về ô nhập: ưu tiên hiển thị nội dung gốc, kèm bản dịch nếu có
        display = content
        if trans.strip():
            display = f"{content}\n\n[Dịch]\n{trans}"
        # self.text_edit.setPlainText(display)

    def get_table_data(self):
        rows = self.table.rowCount()
        cols = self.table.columnCount()
        data = []
        for row in range(rows):
            row_data = []
            for col in range(cols):
                item = self.table.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)
        return data

    def export_to_srt(self):
        """Xuất ra SRT: dùng chỉ cột Dịch nếu có, bỏ STT (bảng đã có)."""
        data = self.get_table_data()  # Mỗi hàng: [timestamp, content, trans]
        srt_lines = []
        for idx, (timestamp, content, trans) in enumerate(data, start=1):
            srt_lines.append(str(idx))
            srt_lines.append(timestamp)
            text_line = (trans or "").strip() or (content or "")
            srt_lines.append(text_line)
            srt_lines.append("")
        return "\n".join(srt_lines)

    def save_srt(self):
        srt_text = self.export_to_srt()
        filename, _ = QFileDialog.getSaveFileName(
            self, "Lưu file SRT", "", "Subtitle Files (*.srt)")
        if filename:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(srt_text)
            QMessageBox.information(
                self, "Thành công", f"✅ Đã lưu file:\n{filename}")

    def open_srt(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Mở file SRT", "", "Subtitle Files (*.srt)")
        if not filename:
            return
        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # Fallback nếu không phải utf-8
            with open(filename, "r", encoding="cp1252", errors="replace") as f:
                content = f.read()
        self.text_edit.setPlainText(content)
        self.check_and_show()

    def translate_all(self):
        """Dùng TranslateWorker để dịch tất cả (EN→VI)"""
        rows = self.table.rowCount()
        if rows == 0:
            QMessageBox.information(
                self, "Thông báo", "Không có dữ liệu để dịch")
            return

        contents = []
        for row in range(rows):
            item = self.table.item(row, 1)  # cột Nội dung
            contents.append(item.text() if item else "")
        # Khởi tạo worker dịch: Google Translate, EN -> VI
        self.translate_worker = MultiThreadTranslateWorker(
            text="",
            source_lang="en",
            target_lang="vi",
            service="Google Translate",
            api_key="",
            max_len=500,
            workers=4,
            custom_prompt="",
            input_type="srt",
            chunks=contents
        )

        # Cập nhật UI theo tiến trình
        self.btn_translate_all.setEnabled(False)
        self.progress_bar.setRange(0, rows)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        def on_segment_translated(original: str, translated: str, index: int):
            row_idx = index - 1
            if 0 <= row_idx < self.table.rowCount():
                self.table.setItem(row_idx, 2, QTableWidgetItem(translated))
                self.table.resizeRowToContents(row_idx)

        def on_progress(completed: int, total: int):
            # Update range in case of chunking differences
            self.progress_bar.setRange(0, max(1, total))
            self.progress_bar.setValue(completed)

        def on_done():
            self.btn_translate_all.setEnabled(True)
            self.progress_bar.setValue(self.progress_bar.maximum())
            self.progress_bar.setVisible(False)
            QMessageBox.information(
                self, "Hoàn tất", "✅ Đã dịch xong tất cả dòng")

        def on_error(msg: str):
            self.btn_translate_all.setEnabled(True)
            QMessageBox.warning(self, "Lỗi", msg)
            self.progress_bar.setVisible(False)

        self.translate_worker.segment_translated.connect(on_segment_translated)
        self.translate_worker.progress.connect(on_progress)
        self.translate_worker.all_done.connect(on_done)
        self.translate_worker.error.connect(on_error)
        self.translate_worker.start()

    # Removed per request: per-line translation feature


class SRTTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.viewer = SRTChecker()
        layout.addWidget(self.viewer)
        self.setLayout(layout)

    def load_text(self, text: str):
        if hasattr(self.viewer, 'text_edit'):
            self.viewer.text_edit.setPlainText(text)
