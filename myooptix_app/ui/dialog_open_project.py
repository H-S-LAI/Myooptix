import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QFrame, QMessageBox, QFileDialog,
    QHeaderView,
)
from PyQt6.QtCore import Qt

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.json"
PKL_DIR = "_pkl_for_review"


class OpenProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Open Project")
        self.setMinimumWidth(640)
        self.resize(720, 400)
        self.project_root = ""
        self.video_root   = ""
        self._build_ui()
        self._load_recent()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 24)
        root.setSpacing(12)

        title = QLabel("Open Project")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #3b3a32;")
        root.addWidget(title)

        root.addWidget(self._divider())

        lbl = QLabel("Recent projects  (double-click to open):")
        lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #6b6456;")
        root.addWidget(lbl)

        self._tree = QTreeWidget()
        self._tree.setColumnCount(2)
        self._tree.setHeaderLabels(["Project", "Location"])
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._tree.setRootIsDecorated(False)
        self._tree.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        self._tree.setMinimumHeight(180)
        self._tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #c8c0b0;
                border-radius: 5px;
                background: #faf7f2;
                font-size: 13px;
                outline: none;
            }
            QTreeWidget::item {
                padding: 7px 10px;
            }
            QTreeWidget::item:selected {
                background: #d6cfc2;
                color: #3b3a32;
            }
            QTreeWidget::item:hover {
                background: #ede8de;
            }
            QHeaderView::section {
                background-color: #ede8de;
                color: #6b6456;
                padding: 5px 10px;
                border: none;
                border-right: 1px solid #d6cfc2;
                border-bottom: 1px solid #d6cfc2;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        self._tree.currentItemChanged.connect(self._on_selection_changed)
        self._tree.itemDoubleClicked.connect(lambda _item, _col: self._open())
        root.addWidget(self._tree)

        root.addWidget(self._divider())

        browse_row = QHBoxLayout()
        browse_lbl = QLabel("Not in the list?")
        browse_lbl.setStyleSheet("font-size: 12px; color: #6b6456;")
        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedWidth(90)
        browse_btn.clicked.connect(self._browse)
        browse_row.addWidget(browse_lbl)
        browse_row.addStretch()
        browse_row.addWidget(browse_btn)
        root.addLayout(browse_row)

        btn_row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        self._open_btn = QPushButton("Open")
        self._open_btn.setProperty("primary", True)
        self._open_btn.style().unpolish(self._open_btn)
        self._open_btn.style().polish(self._open_btn)
        self._open_btn.setFixedHeight(34)
        self._open_btn.setEnabled(False)
        self._open_btn.clicked.connect(self._open)
        btn_row.addStretch()
        btn_row.addWidget(cancel)
        btn_row.addWidget(self._open_btn)
        root.addLayout(btn_row)

    def _divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #d6cfc2;")
        return line

    def _load_recent(self):
        try:
            cfg = json.loads(CONFIG_PATH.read_text())
            raw = cfg.get("recent_projects", [])
            if not raw and cfg.get("last_project"):
                raw = [cfg["last_project"]]
        except Exception:
            cfg = {}
            raw = []

        # Remove paths no longer on this machine and save back
        recent = [p for p in raw if (Path(p) / PKL_DIR).exists()]
        if recent != raw:
            cfg["recent_projects"] = recent
            try:
                CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
            except Exception:
                pass

        if not recent:
            placeholder = QTreeWidgetItem(["No recent projects", ""])
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            placeholder.setForeground(0, Qt.GlobalColor.gray)
            self._tree.addTopLevelItem(placeholder)
            return

        for path in recent:
            p = Path(path)
            item = QTreeWidgetItem([p.name, str(p.parent)])
            item.setData(0, Qt.ItemDataRole.UserRole, path)
            item.setToolTip(1, path)
            self._tree.addTopLevelItem(item)

        self._tree.setCurrentItem(self._tree.topLevelItem(0))

    def _on_selection_changed(self, current, _previous):
        has = current is not None and current.data(0, Qt.ItemDataRole.UserRole) is not None
        self._open_btn.setEnabled(has)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select project folder")
        if path:
            self._validate_and_open(path)

    def _open(self):
        item = self._tree.currentItem()
        if not item:
            return
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path:
            return
        self._validate_and_open(path)

    def _validate_and_open(self, path: str):
        p = Path(path)
        if not (p / PKL_DIR).exists():
            QMessageBox.warning(
                self, "Not a project folder",
                f"Could not find  _pkl_for_review/  in:\n{path}\n\n"
                "Please select the correct project folder."
            )
            return
        self.project_root = path
        self.video_root   = str(p.parent)
        self.accept()
