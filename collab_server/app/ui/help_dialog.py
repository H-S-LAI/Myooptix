"""Per-screen help: a small ? button and the dialog it opens."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTextBrowser, QToolButton,
)
from PyQt6.QtCore import Qt

from .help_texts import HELP


class HelpDialog(QDialog):
    def __init__(self, key: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Help / 說明")
        self.setMinimumSize(620, 560)
        self.setStyleSheet("QDialog { background: #faf8f3; }")

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)

        body = QTextBrowser()
        body.setOpenExternalLinks(True)
        body.setHtml(HELP.get(key, "<p>No help for this screen.</p>"))
        body.setStyleSheet(
            "QTextBrowser { background: #ffffff; border: 1px solid #e0dbd0;"
            " border-radius: 6px; padding: 10px; }"
        )
        root.addWidget(body)

        row = QHBoxLayout()
        row.addStretch()
        close = QPushButton("Close  關閉")
        close.setStyleSheet(
            "QPushButton { background: #7c9c6e; color: #ffffff; border: none;"
            " border-radius: 5px; padding: 7px 20px; font-size: 12px; font-weight: bold; }"
            "QPushButton:hover { background: #6b8a5e; }"
        )
        close.clicked.connect(self.accept)
        row.addWidget(close)
        root.addLayout(row)


def help_button(parent, key: str) -> QToolButton:
    """Small ? button that opens this screen's help."""
    btn = QToolButton(parent)
    btn.setText("?")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setToolTip("Help / 說明")
    btn.setFixedSize(22, 22)
    btn.setStyleSheet(
        "QToolButton { background: #f0ebe0; color: #6b6456; border: 1px solid #d6cfc2;"
        " border-radius: 11px; font-size: 13px; font-weight: bold; }"
        "QToolButton:hover { background: #7c9c6e; color: #ffffff; border-color: #7c9c6e; }"
    )
    btn.clicked.connect(lambda: HelpDialog(key, parent).exec())
    return btn
