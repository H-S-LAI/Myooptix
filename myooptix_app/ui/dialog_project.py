from datetime import date
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt


PKL_DIR = "_pkl_for_review"


def scan_projects(video_root: str) -> list[str]:
    root = Path(video_root)
    if not root.is_dir():
        return []
    return sorted(
        d.name for d in root.iterdir()
        if d.is_dir() and (d / PKL_DIR).exists()
    )


def create_project(video_root: str, name: str) -> str:
    """Create project under video_root/name, or if name is already an absolute path use it directly."""
    p = Path(name)
    proj_path = p if p.is_absolute() else Path(video_root) / name
    for sub in (PKL_DIR, "final_excel_exports", "_Merged_Reports"):
        (proj_path / sub).mkdir(parents=True, exist_ok=True)
    return str(proj_path)


class ProjectDialog(QDialog):
    def __init__(self, video_root: str, parent=None):
        super().__init__(parent)
        self.video_root   = video_root
        self.project_name = ""
        self.setWindowTitle("Select Project")
        self.setFixedSize(420, 380)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(14)

        title = QLabel("Select or Create Project")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #3b3a32;")
        root.addWidget(title)

        sub = QLabel(f"Root: {self.video_root}")
        sub.setStyleSheet("font-size: 11px; color: #8a8070;")
        sub.setWordWrap(True)
        root.addWidget(sub)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #d6cfc2;")
        root.addWidget(line)

        projects = scan_projects(self.video_root)

        if projects:
            lbl = QLabel("Existing projects:")
            lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #6b6456;")
            root.addWidget(lbl)

            self.list_widget = QListWidget()
            self.list_widget.setStyleSheet(
                "QListWidget { background: #faf7f2; border: 1px solid #d6cfc2; border-radius: 5px; }"
                "QListWidget::item { padding: 7px 10px; }"
                "QListWidget::item:selected { background: #d6f0d6; color: #2a6a2a; }"
            )
            for p in projects:
                self.list_widget.addItem(QListWidgetItem(p))
            self.list_widget.setCurrentRow(0)
            self.list_widget.itemDoubleClicked.connect(self._open_selected)
            root.addWidget(self.list_widget)

            open_btn = QPushButton("Open Selected")
            open_btn.setProperty("primary", True)
            open_btn.style().unpolish(open_btn)
            open_btn.style().polish(open_btn)
            open_btn.setFixedHeight(32)
            open_btn.clicked.connect(self._open_selected)
            root.addWidget(open_btn)

            line2 = QFrame()
            line2.setFrameShape(QFrame.Shape.HLine)
            line2.setStyleSheet("color: #d6cfc2;")
            root.addWidget(line2)
        else:
            self.list_widget = None
            no_lbl = QLabel("No existing projects found.")
            no_lbl.setStyleSheet("color: #8a8070; font-size: 12px;")
            root.addWidget(no_lbl)

        # Create new
        new_lbl = QLabel("Create new project:")
        new_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #6b6456;")
        root.addWidget(new_lbl)

        new_row = QHBoxLayout()
        default_name = f"Analysis_{date.today().strftime('%Y%m%d')}"
        self.new_name_edit = QLineEdit(default_name)
        create_btn = QPushButton("Create")
        create_btn.setFixedWidth(70)
        create_btn.clicked.connect(self._create_project)
        new_row.addWidget(self.new_name_edit)
        new_row.addWidget(create_btn)
        root.addLayout(new_row)

    def _open_selected(self):
        if self.list_widget and self.list_widget.currentItem():
            self.project_name = self.list_widget.currentItem().text()
            self.accept()

    def _create_project(self):
        name = self.new_name_edit.text().strip()
        if not name:
            return
        if (Path(self.video_root) / name).exists():
            QMessageBox.warning(self, "Already exists", f'"{name}" already exists.')
            return
        create_project(self.video_root, name)
        self.project_name = name
        self.accept()
