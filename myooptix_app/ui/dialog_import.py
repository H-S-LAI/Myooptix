import shutil
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame, QMessageBox, QApplication,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from .toast import Toast


class ImportDialog(QDialog):
    """
    Let the user pick any video files, assign Exp and Day labels,
    then copy them into project_root/Exp/Day/filename.
    """
    def __init__(self, project_root: str, parent=None):
        super().__init__(parent)
        self.project_root = project_root
        self.setWindowTitle("Import Videos")
        self.resize(780, 500)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(12)

        title = QLabel("Import Video Files")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #3b3a32;")
        root.addWidget(title)

        hint = QLabel(
            "Select video files, then fill in the Exp and Day columns. "
            "Files will be copied to  root / Exp / Day / filename."
        )
        hint.setStyleSheet("font-size: 11px; color: #8a8070;")
        hint.setWordWrap(True)
        root.addWidget(hint)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #d6cfc2;")
        root.addWidget(line)

        # ── Add files button ──
        add_row = QHBoxLayout()
        add_btn = QPushButton("+ Add Files…")
        add_btn.setFixedWidth(120)
        add_btn.clicked.connect(self._add_files)
        clear_btn = QPushButton("Clear All")
        clear_btn.setFixedWidth(90)
        clear_btn.clicked.connect(self._clear)
        add_row.addWidget(add_btn)
        add_row.addWidget(clear_btn)
        add_row.addStretch()
        root.addLayout(add_row)

        # ── Table ──
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["File", "Exp", "Day"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 130)
        self.table.setColumnWidth(2, 100)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        root.addWidget(self.table)

        # ── Batch fill row ──
        fill_lbl = QLabel("Apply to all rows:")
        fill_lbl.setStyleSheet("font-size: 11px; color: #6b6456;")
        self.batch_exp = QLineEdit()
        self.batch_exp.setPlaceholderText("Exp name (e.g. Ctrl)")
        self.batch_day = QLineEdit()
        self.batch_day.setPlaceholderText("Day (e.g. Before)")
        apply_btn = QPushButton("Apply")
        apply_btn.setFixedWidth(70)
        apply_btn.clicked.connect(self._batch_apply)

        fill_row = QHBoxLayout()
        fill_row.addWidget(fill_lbl)
        fill_row.addWidget(self.batch_exp)
        fill_row.addWidget(self.batch_day)
        fill_row.addWidget(apply_btn)
        root.addLayout(fill_row)

        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet("color: #d6cfc2;")
        root.addWidget(line2)

        # ── Buttons ──
        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        self.import_btn = QPushButton("Import & Copy Files")
        self.import_btn.setProperty("primary", True)
        self.import_btn.style().unpolish(self.import_btn)
        self.import_btn.style().polish(self.import_btn)
        self.import_btn.setFixedHeight(34)
        self.import_btn.clicked.connect(self._do_import)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self.import_btn)
        root.addLayout(btn_row)

    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select video files", "",
            "Videos (*.mov *.mp4 *.avi *.MOV *.MP4 *.AVI)"
        )
        for f in files:
            self._add_row(f)

    def _add_row(self, filepath: str):
        r = self.table.rowCount()
        self.table.insertRow(r)
        # File (read-only)
        fname_item = QTableWidgetItem(Path(filepath).name)
        fname_item.setFlags(fname_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        fname_item.setData(Qt.ItemDataRole.UserRole, filepath)
        fname_item.setToolTip(filepath)
        self.table.setItem(r, 0, fname_item)
        # Exp and Day (editable)
        self.table.setItem(r, 1, QTableWidgetItem(""))
        self.table.setItem(r, 2, QTableWidgetItem(""))

    def _clear(self):
        self.table.setRowCount(0)

    def _batch_apply(self):
        exp = self.batch_exp.text().strip()
        day = self.batch_day.text().strip()
        for r in range(self.table.rowCount()):
            if exp:
                self.table.item(r, 1).setText(exp)
            if day:
                self.table.item(r, 2).setText(day)

    def _do_import(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "No files", "Please add video files first.")
            return

        _t = Toast("Copying files…", self, kind="loading", duration=0)
        QApplication.processEvents()

        errors = []
        copied = 0
        for r in range(self.table.rowCount()):
            src  = self.table.item(r, 0).data(Qt.ItemDataRole.UserRole)
            exp  = self.table.item(r, 1).text().strip()
            day  = self.table.item(r, 2).text().strip()
            if not exp or not day:
                errors.append(f"Row {r+1}: missing Exp or Day")
                self.table.item(r, 1).setBackground(QColor("#fde0de") if not exp else QColor("#faf7f2"))
                self.table.item(r, 2).setBackground(QColor("#fde0de") if not day else QColor("#faf7f2"))
                continue
            dst_dir = Path(self.project_root) / exp / day
            dst_dir.mkdir(parents=True, exist_ok=True)
            dst = dst_dir / Path(src).name
            try:
                shutil.copy2(src, dst)
                copied += 1
                self.table.item(r, 0).setBackground(QColor("#d6f0d6"))
            except Exception as e:
                errors.append(f"{Path(src).name}: {e}")

        _t.close()

        if errors:
            QMessageBox.warning(self, "Some errors",
                "\n".join(errors) + f"\n\n{copied} file(s) copied successfully.")

        if copied > 0:
            Toast(f"{copied} file(s) copied", self, kind="success")
            QMessageBox.information(
                self, "Import Complete",
                f"✓  {copied} file(s) copied to:\n{self.project_root}\n\n"
                "Your original files have not been moved or deleted."
            )
            self.accept()
