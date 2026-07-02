from datetime import date
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QFrame, QButtonGroup, QRadioButton,
    QMessageBox,
)
from PyQt6.QtCore import Qt

from .dialog_project import create_project

PKL_DIR = "_pkl_for_review"


class NewProjectDialog(QDialog):
    LOAD_SCAN   = "scan"
    LOAD_IMPORT = "import"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.setMinimumWidth(700)
        self.resize(720, 320)
        self.project_root = ""
        self.load_mode    = self.LOAD_SCAN
        self.video_root   = ""
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 24)
        root.setSpacing(14)

        title = QLabel("New Project")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #3b3a32;")
        root.addWidget(title)

        root.addWidget(self._divider())

        # ── 1. Project folder ──
        lbl1 = QLabel("1.  Where should the project folder be saved?")
        lbl1.setStyleSheet("font-size: 12px; font-weight: bold; color: #6b6456;")
        root.addWidget(lbl1)

        proj_row = QHBoxLayout()
        self.proj_edit = QLineEdit()
        self.proj_edit.setPlaceholderText("/path/to/save/project")
        browse1 = QPushButton("Browse…")
        browse1.setFixedWidth(90)
        browse1.clicked.connect(self._browse_proj)
        self.proj_edit.textChanged.connect(self._auto_fill_name)
        proj_row.addWidget(self.proj_edit)
        proj_row.addWidget(browse1)
        root.addLayout(proj_row)

        name_row = QHBoxLayout()
        name_lbl = QLabel("Project name:")
        name_lbl.setFixedWidth(100)
        name_row.addWidget(name_lbl)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("auto-filled when you pick a folder")
        name_row.addWidget(self.name_edit)
        root.addLayout(name_row)

        root.addWidget(self._divider())

        # ── 2. Load mode ──
        lbl2 = QLabel("2.  How would you like to load videos?")
        lbl2.setStyleSheet("font-size: 12px; font-weight: bold; color: #6b6456;")
        root.addWidget(lbl2)

        self._mode_group = QButtonGroup(self)
        self._radio_scan = QRadioButton(
            "Auto scan  —  scan the save folder for  Exp / Day / file.mov  structure"
        )
        self._radio_scan.setChecked(True)
        self._radio_import = QRadioButton("Manual import  —  select files and assign Exp / Day")
        self._mode_group.addButton(self._radio_scan,   0)
        self._mode_group.addButton(self._radio_import, 1)

        root.addWidget(self._radio_scan)
        root.addWidget(self._radio_import)

        root.addStretch()

        # ── Buttons ──
        btn_row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        create = QPushButton("Create Project")
        create.setProperty("primary", True)
        create.style().unpolish(create)
        create.style().polish(create)
        create.setFixedHeight(34)
        create.clicked.connect(self._create)
        btn_row.addStretch()
        btn_row.addWidget(cancel)
        btn_row.addWidget(create)
        root.addLayout(btn_row)

    def _divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #d6cfc2;")
        return line

    def _browse_proj(self):
        path = QFileDialog.getExistingDirectory(self, "Select save location")
        if path:
            self.proj_edit.setText(path)

    def _auto_fill_name(self, path: str):
        p = Path(path.strip())
        if p.is_dir():
            self.name_edit.setText(f"project_{p.name}_{date.today().strftime('%Y%m%d')}")

    def _create(self):
        save_dir = self.proj_edit.text().strip()
        name     = self.name_edit.text().strip()
        if not save_dir or not name:
            QMessageBox.warning(self, "Missing info", "Please fill in the save location and project name.")
            return

        full_path = Path(save_dir) / name
        create_project(str(full_path.parent), name)

        self.project_root = str(full_path)
        self.load_mode    = self.LOAD_SCAN if self._radio_scan.isChecked() else self.LOAD_IMPORT
        # In scan mode the save folder is also the video root
        self.video_root   = save_dir if self._radio_scan.isChecked() else ""
        self.accept()
