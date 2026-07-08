import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap


class WelcomeDialog(QDialog):
    MODE_NEW   = "new"
    MODE_OPEN  = "open"
    MODE_QUICK = "quick"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MyoOptix")
        self.setFixedSize(440, 420)
        self.setWindowFlags(Qt.WindowType.Dialog)
        self.mode = None
        self._build_ui()

    def get_mode(self) -> str:
        return self.mode

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 36, 40, 32)
        root.setSpacing(10)

        # icon
        icon_lbl = QLabel()
        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icon.png")
        pix = QPixmap(icon_path)
        if not pix.isNull():
            pix.setDevicePixelRatio(2.0)
            icon_lbl.setPixmap(pix.scaled(144, 144, Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(icon_lbl)

        title = QLabel("MyoOptix")
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: #3b3a32;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel("Cardiac Organoid Motion Analysis")
        sub.setStyleSheet("font-size: 11px; color: #8a8070;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)
        root.addWidget(sub)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #d6cfc2;")
        root.addWidget(line)

        grant_lbl = QLabel(
            "Supported by 國家科學及技術委員會 補助專題研究計畫\n"
            "AI輔助與即時感測回饋之免疫藥物毒性分析晶片 NSTC 114-2640-B-038-001\n"
            "Grant PI: 李岡遠　Lab Director: 楊添鈞　Developer: 賴竑劭"
        )
        grant_lbl.setStyleSheet("font-size: 10px; color: #9a9080;")
        grant_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(grant_lbl)

        root.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)

        new_btn = QPushButton("＋  New Project")
        new_btn.setFixedHeight(48)
        new_btn.setProperty("primary", True)
        new_btn.style().unpolish(new_btn)
        new_btn.style().polish(new_btn)
        new_btn.clicked.connect(self._new_project)

        open_btn = QPushButton("📂  Open Project")
        open_btn.setFixedHeight(48)
        open_btn.clicked.connect(self._open_project)

        btn_row.addWidget(new_btn)
        btn_row.addWidget(open_btn)
        root.addLayout(btn_row)

        quick_btn = QPushButton("⚡  Quick Analysis  —  single video, no project")
        quick_btn.setFixedHeight(38)
        quick_btn.setStyleSheet(
            "QPushButton { font-size: 12px; color: #6b6456; background: #ede8de;"
            "border: 1px dashed #c8c0b0; border-radius: 5px; padding: 4px 12px; }"
            "QPushButton:hover { background: #e0d9cc; border-color: #a09880; }"
        )
        quick_btn.clicked.connect(self._quick_analysis)
        root.addWidget(quick_btn)

        root.addStretch()

    def _new_project(self):
        self.mode = self.MODE_NEW
        self.accept()

    def _open_project(self):
        self.mode = self.MODE_OPEN
        self.accept()

    def _quick_analysis(self):
        self.mode = self.MODE_QUICK
        self.accept()
