APP_STYLE = """
/* ── Base ── */
QMainWindow, QDialog, QWidget {
    background-color: #f5f0e8;
    color: #3b3a32;
    font-family: "Segoe UI", -apple-system, sans-serif;
    font-size: 13px;
}

/* ── Menu / toolbar ── */
QMenuBar {
    background-color: #ede8de;
    color: #3b3a32;
    border-bottom: 1px solid #d6cfc2;
}
QMenuBar::item:selected { background-color: #d6cfc2; }

/* ── Buttons ── */
QPushButton {
    background-color: #ede8de;
    color: #3b3a32;
    border: 1px solid #c8c0b0;
    border-radius: 5px;
    padding: 6px 16px;
}
QPushButton:hover {
    background-color: #e0d9cc;
    border-color: #a09880;
}
QPushButton:pressed {
    background-color: #cfc8ba;
}
QPushButton[primary="true"] {
    background-color: #7c9c6e;
    color: #ffffff !important;
    border: none;
    font-weight: bold;
    padding: 7px 18px;
}
QPushButton[primary="true"]:hover {
    background-color: #6a8a5c;
    color: #ffffff;
}
QPushButton[danger="true"] {
    background-color: #f0ebe0;
    color: #c0392b !important;
    border: 1.5px solid #c0392b;
    font-weight: bold;
    padding: 7px 18px;
}
QPushButton[danger="true"]:hover {
    background-color: #fce8e6;
    color: #a93226;
    border-color: #a93226;
}

/* ── Inputs ── */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
    background-color: #faf7f2;
    border: 1px solid #c8c0b0;
    border-radius: 4px;
    padding: 5px 8px;
    color: #3b3a32;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border-color: #7c9c6e;
    background-color: #ffffff;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: #faf7f2;
    selection-background-color: #d6cfc2;
    border: 1px solid #c8c0b0;
    color: #3b3a32;
}

/* ── Table ── */
QTableWidget {
    background-color: #faf7f2;
    gridline-color: #e0d9cc;
    border: 1px solid #c8c0b0;
    border-radius: 5px;
}
QTableWidget::item { padding: 5px 10px; }
QTableWidget::item:selected {
    background-color: #d6cfc2;
    color: #3b3a32;
}
QHeaderView::section {
    background-color: #ede8de;
    color: #6b6456;
    padding: 6px 10px;
    border: none;
    border-right: 1px solid #d6cfc2;
    border-bottom: 1px solid #d6cfc2;
    font-weight: bold;
}

/* ── Slider ── */
QSlider::groove:horizontal {
    height: 4px;
    background: #c8c0b0;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #7c9c6e;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::sub-page:horizontal {
    background: #7c9c6e;
    border-radius: 2px;
}

/* ── ScrollBar ── */
QScrollBar:vertical {
    background: #ede8de;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #c8c0b0;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #a09880; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { height: 8px; background: #ede8de; }
QScrollBar::handle:horizontal { background: #c8c0b0; border-radius: 4px; }

/* ── GroupBox / card ── */
QGroupBox {
    border: 1px solid #d6cfc2;
    border-radius: 7px;
    margin-top: 10px;
    padding: 10px 12px 8px 12px;
    background-color: #faf7f2;
    color: #6b6456;
    font-size: 11px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #6b6456;
}

/* ── Progress bar ── */
QProgressBar {
    background-color: #e0d9cc;
    border: none;
    border-radius: 3px;
    height: 5px;
}
QProgressBar::chunk {
    background-color: #7c9c6e;
    border-radius: 3px;
}

/* ── Splitter ── */
QSplitter::handle { background: #d6cfc2; width: 1px; height: 1px; }

/* ── Status bar ── */
QStatusBar {
    background-color: #ede8de;
    color: #8a8070;
    font-size: 11px;
    border-top: 1px solid #d6cfc2;
}

/* ── Dialog ── */
QDialog {
    background-color: #f5f0e8;
}

/* ── Radio buttons (explicit indicator needed on Windows) ── */
QRadioButton {
    spacing: 6px;
    color: #3b3a32;
}
QRadioButton::indicator {
    width: 14px;
    height: 14px;
    border-radius: 7px;
    border: 2px solid #a09880;
    background-color: #faf7f2;
}
QRadioButton::indicator:checked {
    border: 2px solid #7c9c6e;
    background-color: #7c9c6e;
}
QRadioButton::indicator:hover {
    border-color: #7c9c6e;
}

/* ── Labels ── */
QLabel[heading="true"] {
    font-size: 20px;
    font-weight: bold;
    color: #3b3a32;
}
QLabel[subtitle="true"] {
    color: #8a8070;
    font-size: 11px;
}
QLabel[stat_value="true"] {
    font-size: 24px;
    font-weight: bold;
    color: #7c9c6e;
}
QLabel[stat_label="true"] {
    font-size: 11px;
    color: #8a8070;
}
"""
