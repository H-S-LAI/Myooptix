"""
Update dialogs: model-weight downloader and app-update notifier.
"""
import webbrowser

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QMessageBox,
    QProgressBar, QPushButton, QTextEdit, QVBoxLayout,
)


class _AppDownloadThread(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(str)   # path to downloaded zip
    error    = pyqtSignal(str)

    def __init__(self, tag: str):
        super().__init__()
        self._tag = tag

    def run(self):
        try:
            from updater import download_app_update
            dest = download_app_update(
                self._tag,
                progress_cb=lambda r, t: self.progress.emit(r, t),
            )
            self.finished.emit(str(dest))
        except Exception as exc:
            self.error.emit(str(exc))


class _DownloadThread(QThread):
    progress = pyqtSignal(int, int)  # received, total
    finished = pyqtSignal()
    error    = pyqtSignal(str)

    def run(self):
        try:
            from updater import download_weights
            download_weights(progress_cb=lambda r, t: self.progress.emit(r, t))
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))


class ModelDownloadDialog(QDialog):
    """Shown on first launch when best_model.pth is missing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Model Weights Required")
        self.setFixedSize(440, 210)
        self.setWindowFlags(Qt.WindowType.Dialog)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(28, 22, 28, 22)

        self._lbl = QLabel(
            "U-Net model weights (<b>best_model.pth</b>, ~93 MB) are needed\n"
            "for automatic ROI segmentation.\n\n"
            "Download now, or skip to use Otsu thresholding instead."
        )
        self._lbl.setWordWrap(True)
        lay.addWidget(self._lbl)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setVisible(False)
        lay.addWidget(self._bar)

        btn_row = QHBoxLayout()
        self._dl_btn = QPushButton("Download  (~93 MB)")
        self._dl_btn.setProperty("primary", True)
        self._dl_btn.style().unpolish(self._dl_btn)
        self._dl_btn.style().polish(self._dl_btn)
        self._dl_btn.clicked.connect(self._start)

        skip_btn = QPushButton("Skip — use Otsu only")
        skip_btn.clicked.connect(self.reject)

        btn_row.addWidget(self._dl_btn)
        btn_row.addWidget(skip_btn)
        lay.addLayout(btn_row)

    def _start(self):
        self._dl_btn.setEnabled(False)
        self._bar.setVisible(True)
        self._lbl.setText("Connecting to GitHub…")
        self._thread = _DownloadThread()
        self._thread.progress.connect(self._on_progress)
        self._thread.finished.connect(self.accept)
        self._thread.error.connect(self._on_error)
        self._thread.start()

    def _on_progress(self, received: int, total: int):
        mb = received / 1_048_576
        if total > 0:
            self._bar.setValue(int(received / total * 100))
            self._lbl.setText(f"Downloading…  {mb:.1f} / {total/1_048_576:.0f} MB")
        else:
            self._lbl.setText(f"Downloading…  {mb:.1f} MB")

    def _on_error(self, msg: str):
        QMessageBox.critical(self, "Download failed", msg)
        self._dl_btn.setEnabled(True)
        self._bar.setVisible(False)
        self._lbl.setText(
            "Download failed. Check your internet connection.\n"
            "You can skip and use Otsu segmentation instead."
        )


class UpdateAvailableDialog(QDialog):
    """Shown when a newer GitHub Release is detected."""

    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Update Available")
        self.setFixedSize(480, 300)
        self._info = info
        self._build(info)

    def _build(self, info: dict):
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.setContentsMargins(28, 22, 28, 22)

        lay.addWidget(QLabel(f"<b>New version available: {info['tag']}</b>"))

        notes = QTextEdit()
        notes.setReadOnly(True)
        notes.setPlainText(info.get("body", "(No release notes)"))
        lay.addWidget(notes)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setVisible(False)
        lay.addWidget(self._bar)

        self._status = QLabel("")
        self._status.setVisible(False)
        lay.addWidget(self._status)

        btn_row = QHBoxLayout()
        self._dl_btn = QPushButton("Download Update")
        self._dl_btn.setProperty("primary", True)
        self._dl_btn.style().unpolish(self._dl_btn)
        self._dl_btn.style().polish(self._dl_btn)
        self._dl_btn.clicked.connect(self._start_download)

        later_btn = QPushButton("Later")
        later_btn.clicked.connect(self.reject)

        btn_row.addWidget(self._dl_btn)
        btn_row.addWidget(later_btn)
        lay.addLayout(btn_row)

    def _start_download(self):
        self._dl_btn.setEnabled(False)
        self._bar.setVisible(True)
        self._status.setVisible(True)
        self._status.setText("Connecting…")
        self._thread = _AppDownloadThread(self._info["tag"])
        self._thread.progress.connect(self._on_progress)
        self._thread.finished.connect(self._on_finished)
        self._thread.error.connect(self._on_error)
        self._thread.start()

    def _on_progress(self, received: int, total: int):
        mb = received / 1_048_576
        if total > 0:
            self._bar.setValue(int(received / total * 100))
            self._status.setText(f"Downloading…  {mb:.1f} / {total/1_048_576:.0f} MB")
        else:
            self._status.setText(f"Downloading…  {mb:.1f} MB")

    def _on_finished(self, path: str):
        self._bar.setValue(100)
        import platform, subprocess
        if platform.system() == "Darwin":
            subprocess.Popen(["open", "-R", path])  # reveal in Finder
        QMessageBox.information(
            self, "Download Complete",
            f"New version downloaded to your Desktop:\n{path}\n\n"
            "Please:\n"
            "1. Close this app\n"
            "2. Open the zip and replace the old MyoOptix.app\n"
            "3. Relaunch"
        )
        self.accept()

    def _on_error(self, msg: str):
        QMessageBox.critical(self, "Download failed", msg)
        self._dl_btn.setEnabled(True)
        self._bar.setVisible(False)
        self._status.setVisible(False)
