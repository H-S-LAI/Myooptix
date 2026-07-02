from PyQt6.QtWidgets import QMainWindow, QStatusBar, QMessageBox
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QSize, QThread, pyqtSignal
from pathlib import Path

from .tab_dashboard import DashboardTab


class _UpdateCheckThread(QThread):
    result = pyqtSignal(object)  # dict | None

    def __init__(self, version: str):
        super().__init__()
        self._version = version

    def run(self):
        try:
            import updater
            self.result.emit(updater.check_for_update(self._version))
        except Exception:
            self.result.emit(None)


class MainWindow(QMainWindow):
    def __init__(self, video_root: str = "", project_name: str = ""):
        super().__init__()
        self.setWindowTitle(f"MyoOptix — {project_name}" if project_name else "MyoOptix")
        self.resize(1100, 720)
        self.setMinimumSize(QSize(860, 560))

        icon_path = Path(__file__).parent.parent / "assets" / "heart.svg"
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

        self._build_menu()

    def _build_menu(self):
        menubar = self.menuBar()
        help_menu = menubar.addMenu("Help")

        update_action = QAction("Check for Updates", self)
        update_action.triggered.connect(self._check_updates)
        help_menu.addAction(update_action)

        about_action = QAction("About MyoOptix", self)
        about_action.triggered.connect(self._about)
        help_menu.addAction(about_action)

    def _check_updates(self):
        self.status.showMessage("Checking for updates…")
        try:
            import version as v
            current = v.VERSION  # bare version for comparison (no hash)
        except Exception:
            current = "0.1.0"
        self._upd_thread = _UpdateCheckThread(current)
        self._upd_thread.result.connect(self._on_update_result)
        self._upd_thread.start()

    def _on_update_result(self, info):
        if info is None:
            self.status.showMessage("Already up to date (or no internet connection).")
        else:
            self.status.showMessage(f"New version available: {info['tag']}")
            from .dialog_update import UpdateAvailableDialog
            UpdateAvailableDialog(info, parent=self).exec()

    def _about(self):
        try:
            import version as v
            ver = v.get_version_string()
        except Exception:
            ver = "unknown"
        QMessageBox.about(
            self, "About MyoOptix",
            f"<b>MyoOptix</b> v{ver}<br>"
            "Cardiac Organoid Motion Analysis<br><br>"
            "Migrated from MATLAB to Python (PyQt6).<br>"
            "© TMU Lab",
        )

    def _open_review(self):
        from .dialog_review import ReviewDialog
        self._review_dlg = ReviewDialog(self)
        self._review_dlg.setModal(False)
        self._review_dlg.show()
        self._review_dlg.raise_()
