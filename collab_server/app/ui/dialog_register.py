"""
Registration dialog — user applies for access.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from api_client import register, APIError


class _RegisterWorker(QThread):
    success = pyqtSignal(str)
    failure = pyqtSignal(str)

    def __init__(self, email, password, full_name, institution):
        super().__init__()
        self.email = email; self.password = password
        self.full_name = full_name; self.institution = institution

    def run(self):
        try:
            result = register(self.email, self.password, self.full_name, self.institution)
            self.success.emit(result.get("message", "Submitted."))
        except APIError as e:
            self.failure.emit(str(e))


class RegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Request Access — MyoOptix Collab")
        self.setFixedWidth(420)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 24)
        root.setSpacing(0)

        title = QLabel("Request Access")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #3b3a32;")
        root.addWidget(title)
        sub = QLabel("Fill in your details. You will receive an email when approved.")
        sub.setStyleSheet("font-size: 11px; color: #8a8070;")
        sub.setWordWrap(True)
        root.addWidget(sub)
        root.addSpacing(16)
        root.addWidget(self._divider())
        root.addSpacing(14)

        fields = [
            ("Full name",       "_f_name",  False, "e.g. Jane Smith"),
            ("Institution / School", "_f_inst", False, "e.g. National Taiwan University"),
            ("Email",           "_f_email", False, "your@email.com"),
            ("Password",        "_f_pw",    True,  "At least 8 characters"),
            ("Confirm password","_f_pw2",   True,  ""),
        ]
        for label, attr, is_pw, placeholder in fields:
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #6b6456;")
            root.addWidget(lbl)
            root.addSpacing(3)
            w = QLineEdit()
            w.setFixedHeight(34)
            if placeholder:
                w.setPlaceholderText(placeholder)
            if is_pw:
                w.setEchoMode(QLineEdit.EchoMode.Password)
            setattr(self, attr, w)
            root.addWidget(w)
            root.addSpacing(10)

        self._err = QLabel("")
        self._err.setStyleSheet("font-size: 11px; color: #c0392b;")
        self._err.setWordWrap(True)
        self._err.setVisible(False)
        root.addWidget(self._err)
        root.addSpacing(4)

        self._submit_btn = QPushButton("Submit Request")
        self._submit_btn.setProperty("primary", True)
        self._submit_btn.style().unpolish(self._submit_btn)
        self._submit_btn.style().polish(self._submit_btn)
        self._submit_btn.setFixedHeight(38)
        self._submit_btn.clicked.connect(self._submit)
        root.addWidget(self._submit_btn)

    def _divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #d6cfc2;")
        return line

    def _submit(self):
        name  = self._f_name.text().strip()
        inst  = self._f_inst.text().strip()
        email = self._f_email.text().strip()
        pw    = self._f_pw.text()
        pw2   = self._f_pw2.text()

        if not all([name, inst, email, pw]):
            self._show_err("Please fill in all fields.")
            return
        if len(pw) < 8:
            self._show_err("Password must be at least 8 characters.")
            return
        if pw != pw2:
            self._show_err("Passwords do not match.")
            return

        self._submit_btn.setEnabled(False)
        self._submit_btn.setText("Submitting…")
        self._err.setVisible(False)

        self._worker = _RegisterWorker(email, pw, name, inst)
        self._worker.success.connect(self._on_success)
        self._worker.failure.connect(self._on_failure)
        self._worker.start()

    def _on_success(self, msg: str):
        self._submit_btn.setEnabled(True)
        self._submit_btn.setText("Submit Request")
        # replace form with success message
        for i in reversed(range(self.layout().count())):
            item = self.layout().itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        root = self.layout()
        ok = QLabel("✓  Request submitted!")
        ok.setStyleSheet("font-size: 15px; font-weight: bold; color: #7c9c6e;")
        ok.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(ok)
        detail = QLabel(msg + "\n\nYou will receive an email once your account is approved.")
        detail.setWordWrap(True)
        detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        detail.setStyleSheet("font-size: 12px; color: #6b6456;")
        root.addWidget(detail)
        root.addSpacing(16)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn)
        self.adjustSize()

    def _on_failure(self, msg: str):
        self._submit_btn.setEnabled(True)
        self._submit_btn.setText("Submit Request")
        self._show_err(msg)

    def _show_err(self, msg: str):
        self._err.setText(msg)
        self._err.setVisible(True)
        self.adjustSize()
