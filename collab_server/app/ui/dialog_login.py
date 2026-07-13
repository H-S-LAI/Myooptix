"""
Login dialog — shown on startup if no valid token found.
Emits logged_in(token, email) on success.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from api_client import login, APIError


class _LoginWorker(QThread):
    success = pyqtSignal(str, str)   # token, email
    failure = pyqtSignal(str)        # error message

    def __init__(self, email, password):
        super().__init__()
        self.email    = email
        self.password = password

    def run(self):
        try:
            result = login(self.email, self.password)
            self.success.emit(result["token"], self.email)
        except APIError as e:
            self.failure.emit(str(e))


class LoginDialog(QDialog):
    logged_in = pyqtSignal(str, str)   # token, email

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MyoOptix")
        self.setFixedWidth(480)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 32, 36, 28)
        root.setSpacing(0)

        # ── header ───────────────────────────────────────────────────────────
        assets = Path(__file__).parent.parent / "assets"
        icon_path = assets / "icon.png"
        if icon_path.exists():
            icon = QLabel()
            px = QPixmap(str(icon_path))
            px.setDevicePixelRatio(2.0)
            icon.setPixmap(px.scaled(80, 80,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            root.addWidget(icon)
            root.addSpacing(8)

        title = QLabel("MyoOptix")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #3b3a32;")
        root.addWidget(title)

        sub = QLabel("Cardiac Organoid Motion Analysis")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("font-size: 12px; color: #8a8070;")
        root.addWidget(sub)
        root.addSpacing(10)

        _gs = "font-size: 10px; color: #b0a898; background: transparent;"
        for text in (
            "Supported by 國家科學及技術委員會 補助專題研究計畫",
            "AI輔助與即時感測回饋之免疫藥物毒性分析晶片  NSTC 114-2640-B-038-001",
            "Grant PI: 李岡遠　Lab Director: 楊添鈞　Developer: 賴竑劭",
        ):
            lbl = QLabel(text)
            lbl.setStyleSheet(_gs)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setWordWrap(True)
            root.addWidget(lbl)

        root.addSpacing(14)
        root.addWidget(self._divider())
        root.addSpacing(16)

        # ── fields ───────────────────────────────────────────────────────────
        lbl_email = QLabel("Email")
        lbl_email.setStyleSheet("font-size: 11px; font-weight: bold; color: #6b6456;")
        root.addWidget(lbl_email)
        root.addSpacing(4)
        self._email = QLineEdit()
        self._email.setPlaceholderText("your@email.com")
        self._email.setFixedHeight(36)
        root.addWidget(self._email)
        root.addSpacing(12)

        lbl_pw = QLabel("Password")
        lbl_pw.setStyleSheet("font-size: 11px; font-weight: bold; color: #6b6456;")
        root.addWidget(lbl_pw)
        root.addSpacing(4)
        self._password = QLineEdit()
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._password.setPlaceholderText("••••••••")
        self._password.setFixedHeight(36)
        self._password.returnPressed.connect(self._do_login)
        root.addWidget(self._password)
        root.addSpacing(6)

        # ── error label ──────────────────────────────────────────────────────
        self._err = QLabel("")
        self._err.setStyleSheet("font-size: 11px; color: #c0392b;")
        self._err.setWordWrap(True)
        self._err.setVisible(False)
        root.addWidget(self._err)
        root.addSpacing(16)

        # ── login button ─────────────────────────────────────────────────────
        self._login_btn = QPushButton("Sign in")
        self._login_btn.setProperty("primary", True)
        self._login_btn.style().unpolish(self._login_btn)
        self._login_btn.style().polish(self._login_btn)
        self._login_btn.setFixedHeight(38)
        self._login_btn.clicked.connect(self._do_login)
        root.addWidget(self._login_btn)
        root.addSpacing(12)

        root.addWidget(self._divider())
        root.addSpacing(12)

        # ── register link ─────────────────────────────────────────────────────
        reg_row = QHBoxLayout()
        reg_row.addStretch()
        reg_lbl = QLabel("Don't have an account?")
        reg_lbl.setStyleSheet("font-size: 11px; color: #8a8070;")
        reg_row.addWidget(reg_lbl)
        reg_btn = QPushButton("Request access")
        reg_btn.setFlat(True)
        reg_btn.setStyleSheet(
            "font-size: 11px; color: #7c9c6e; font-weight: bold;"
            "border: none; background: transparent; padding: 0;"
        )
        reg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reg_btn.clicked.connect(self._open_register)
        reg_row.addWidget(reg_btn)
        reg_row.addStretch()
        root.addLayout(reg_row)

    def _divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #d6cfc2;")
        return line

    def _do_login(self):
        email = self._email.text().strip()
        pw    = self._password.text()
        if not email or not pw:
            self._show_err("Please enter your email and password.")
            return

        self._login_btn.setEnabled(False)
        self._login_btn.setText("Signing in…")
        self._err.setVisible(False)

        self._worker = _LoginWorker(email, pw)
        self._worker.success.connect(self._on_success)
        self._worker.failure.connect(self._on_failure)
        self._worker.start()

    def _on_success(self, token: str, email: str):
        self._login_btn.setEnabled(True)
        self._login_btn.setText("Sign in")
        self.hide()
        self.logged_in.emit(token, email)

    def _on_failure(self, msg: str):
        self._login_btn.setEnabled(True)
        self._login_btn.setText("Sign in")
        self._show_err(msg)

    def _show_err(self, msg: str):
        self._err.setText(msg)
        self._err.setVisible(True)
        self.adjustSize()

    def _open_register(self):
        from .dialog_register import RegisterDialog
        dlg = RegisterDialog(self)
        dlg.exec()
