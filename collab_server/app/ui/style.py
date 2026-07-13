APP_STYLE = """
QMainWindow, QDialog, QWidget {
    background-color: #f5f0e8;
    color: #3b3a32;
    font-family: "Segoe UI", -apple-system, sans-serif;
    font-size: 14px;
}
QPushButton {
    background-color: #ede8de;
    color: #3b3a32;
    border: 1px solid #c8c0b0;
    border-radius: 5px;
    padding: 6px 16px;
}
QPushButton:hover { background-color: #e0d9cc; border-color: #a09880; }
QPushButton:pressed { background-color: #cfc8ba; }
QPushButton:disabled { color: #b0a898; border-color: #d6cfc2; }
QPushButton[primary="true"] {
    background-color: #7c9c6e;
    color: #ffffff;
    border: none;
    font-weight: bold;
    padding: 7px 18px;
}
QPushButton[primary="true"]:hover { background-color: #6a8a5c; }
QPushButton[primary="true"]:disabled { background-color: #a8bfa0; }
QLineEdit, QTextEdit {
    background-color: #faf7f2;
    border: 1px solid #c8c0b0;
    border-radius: 4px;
    padding: 5px 8px;
    color: #3b3a32;
}
QLineEdit:focus, QTextEdit:focus {
    border-color: #7c9c6e;
    background-color: #ffffff;
}
QRadioButton { spacing: 8px; color: #3b3a32; padding: 3px 0; }
QRadioButton::indicator {
    width: 14px; height: 14px; border-radius: 7px;
    border: 2px solid #a09880; background-color: #faf7f2;
}
QRadioButton::indicator:checked { border: 2px solid #7c9c6e; background-color: #7c9c6e; }
QProgressBar {
    background-color: #e0d9cc; border: none; border-radius: 3px; height: 5px;
}
QProgressBar::chunk { background-color: #7c9c6e; border-radius: 3px; }
QScrollBar:vertical { background: #ede8de; width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #c8c0b0; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #a09880; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


def build_style(assets_dir: str) -> str:
    return APP_STYLE
