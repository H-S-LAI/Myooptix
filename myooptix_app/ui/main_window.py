from PyQt6.QtWidgets import QMainWindow, QStatusBar
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize
from pathlib import Path

from .tab_dashboard import DashboardTab


class MainWindow(QMainWindow):
    def __init__(self, video_root: str = "", project_name: str = ""):
        super().__init__()
        self.setWindowTitle(f"MyoOptix — {project_name}" if project_name else "MyoOptix")
        self.resize(1100, 720)
        self.setMinimumSize(QSize(860, 560))

        _assets = Path(__file__).parent.parent / "assets"
        icon_path = _assets / "icon.png"
        if not icon_path.exists():
            icon_path = _assets / "heart.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.dashboard = DashboardTab(
            open_review_fn=self._open_review,
            video_root=video_root,
            project_name=project_name,
        )
        self.setCentralWidget(self.dashboard)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("MyoOptix ready")

    def _open_review(self):
        from .dialog_review import ReviewDialog
        self._review_dlg = ReviewDialog(self)
        self._review_dlg.setModal(False)
        self._review_dlg.show()
        self._review_dlg.raise_()
