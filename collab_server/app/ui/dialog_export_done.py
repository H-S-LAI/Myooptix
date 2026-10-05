"""Shown after a successful export — replaces the easily-missed toast."""

import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt


def _open_folder(path: Path):
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        elif os.name == "nt":
            os.startfile(str(path))          # noqa: S606  (Windows only)
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        pass


class ExportDoneDialog(QDialog):
    """
    n_rois     : how many ROIs were written
    out_root   : folder that contains final_excel_exports/ and summary_images/
    stem       : video stem, used for the file names shown
    """

    def __init__(self, n_rois: int, out_root: Path, stem: str, parent=None):
        super().__init__(parent)
        self._out_root = Path(out_root)
        self.setWindowTitle("Export complete / 匯出完成")
        self.setMinimumWidth(520)
        self.setStyleSheet("QDialog { background: #faf8f3; }")

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(2)

        head = QLabel("✓  匯出完成　Export complete")
        head.setStyleSheet("font-size: 17px; font-weight: bold; color: #4a7a52;")
        root.addWidget(head)
        root.addSpacing(10)

        sub = QLabel(f"{n_rois} 顆類器官已輸出　·　{n_rois} ROI(s) exported")
        sub.setStyleSheet("font-size: 12px; color: #6b6456;")
        root.addWidget(sub)
        root.addSpacing(12)

        for title, items in (
            ("Excel", [f"{stem}_analysis_results.xlsx", f"{stem}_raw_data.xlsx"]),
            ("Summary images", [f"{stem}_ROI*_Summary.png  ({n_rois} 張 / files)"]),
        ):
            t = QLabel(title)
            t.setStyleSheet("font-size: 11px; font-weight: bold; color: #3b5a8a;")
            root.addWidget(t)
            for it in items:
                f = QLabel("   " + it)
                f.setStyleSheet("font-size: 11px; color: #6b6456;")
                root.addWidget(f)
            root.addSpacing(8)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #e0dbd0;")
        root.addWidget(line)
        root.addSpacing(8)

        where = QLabel("儲存位置　Saved to")
        where.setStyleSheet("font-size: 11px; font-weight: bold; color: #3b5a8a;")
        root.addWidget(where)

        path_lbl = QLabel(str(self._out_root))
        path_lbl.setWordWrap(True)
        path_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        path_lbl.setStyleSheet(
            "font-size: 11px; color: #3b3a32; background: #f4f1e8;"
            "border: 1px solid #e0dbd0; border-radius: 4px; padding: 7px 9px;"
        )
        root.addWidget(path_lbl)
        root.addSpacing(16)

        row = QHBoxLayout()
        open_btn = QPushButton("開啟資料夾  Open folder")
        open_btn.setStyleSheet(
            "QPushButton { background: #f0ebe0; color: #6b6456; border: 1px solid #c8c0b0;"
            " border-radius: 5px; padding: 8px 16px; font-size: 12px; font-weight: bold; }"
            "QPushButton:hover { background: #e0dbd0; }"
        )
        open_btn.clicked.connect(lambda: _open_folder(self._out_root))
        row.addWidget(open_btn)
        row.addStretch()
        done = QPushButton("完成  Done")
        done.setDefault(True)
        done.setStyleSheet(
            "QPushButton { background: #7c9c6e; color: #ffffff; border: none;"
            " border-radius: 5px; padding: 8px 24px; font-size: 12px; font-weight: bold; }"
            "QPushButton:hover { background: #6b8a5e; }"
        )
        done.clicked.connect(self.accept)
        row.addWidget(done)
        root.addLayout(row)
