"""
Quick Analysis dialog for Collab Edition.
Same analysis logic as main app, but:
- Calls /auth/verify before starting (token check)
- Calls /log/analysis after completion
- No project management — outputs to <video_folder>/<video_stem>/
"""

import sys
import time
import pickle
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QButtonGroup, QRadioButton, QFrame, QFileDialog,
    QProgressBar, QTextEdit, QApplication,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

APP_DIR = Path(__file__).parent.parent  # app/
sys.path.insert(0, str(APP_DIR))
from api_client import log_analysis, verify, APIError


# ── Network Monitor ───────────────────────────────────────────────────────────

class _NetMonitor(QThread):
    online  = pyqtSignal()
    offline = pyqtSignal()

    def __init__(self, token: str, interval: int = 10):
        super().__init__()
        self._token    = token
        self._interval = interval
        self._running  = True
        self._was_online = True

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            try:
                verify(self._token)
                if not self._was_online:
                    self._was_online = True
                    self.online.emit()
            except APIError as e:
                msg = str(e).lower()
                # token expired = server reachable, don't treat as offline
                if "cannot reach" in msg or "connection" in msg or "timeout" in msg:
                    if self._was_online:
                        self._was_online = False
                        self.offline.emit()
            except Exception:
                pass
            for _ in range(self._interval * 10):
                if not self._running:
                    return
                time.sleep(0.1)


# ── Analysis Worker ───────────────────────────────────────────────────────────

class _QuickWorker(QThread):
    stage    = pyqtSignal(str)
    finished = pyqtSignal(str, float)   # pkl_path, elapsed_sec
    error    = pyqtSignal(str)

    def __init__(self, video_path, seg_method, min_pct, max_pct, roi_boxes, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.seg_method = seg_method
        self.min_pct    = min_pct
        self.max_pct    = max_pct
        self.roi_boxes  = roi_boxes
        self._abort     = False

    def abort(self):
        self._abort = True

    def run(self):
        t0 = time.time()
        try:
            # cardio_py is bundled inside app/
            app_dir = str(Path(__file__).parent.parent)
            if app_dir not in sys.path:
                sys.path.insert(0, app_dir)

            import numpy as np
            from cardio_py.core.io         import read_first_frame
            from cardio_py.core.tracking   import track_video
            from cardio_py.core.mdp        import calculate_mdp_metrics, select_dominant_signal
            from cardio_py.core.force      import compute_contractility
            from cardio_py.core.morphology import compute_mask_morphology

            vp   = Path(self.video_path)
            out_dir = vp.parent / vp.stem
            out_dir.mkdir(parents=True, exist_ok=True)
            pkl_dir = out_dir / "_pkl_for_review"
            pkl_dir.mkdir(exist_ok=True)
            pkl_path = pkl_dir / f"{vp.stem}.pkl"

            self.stage.emit("Reading video…")
            frame_rgb, frame_rate = read_first_frame(self.video_path)

            # ── segmentation ─────────────────────────────────────────────────
            masks = []
            if self.seg_method == "manual":
                self.stage.emit("Manual ROI — converting boxes…")
                h, w = frame_rgb.shape[:2]
                for (x, y, bw, bh) in self.roi_boxes:
                    m = np.zeros((h, w), dtype=bool)
                    m[y:y+bh, x:x+bw] = True
                    masks.append(m)
            else:
                self.stage.emit("Segmentation…")
                if self.seg_method == "unet":
                    from cardio_py.core.segmentation import segment_unet
                    masks, _ = segment_unet(frame_rgb, min_pct=self.min_pct, max_pct=self.max_pct)
                else:
                    from cardio_py.core.segmentation import segment_otsu
                    masks, _ = segment_otsu(frame_rgb, min_pct=self.min_pct, max_pct=self.max_pct)

            if not masks:
                self.error.emit("No ROIs found. Try adjusting the area filter or use Manual mode.")
                return

            # ── KLT tracking ─────────────────────────────────────────────────
            self.stage.emit(f"KLT tracking ({len(masks)} ROI(s))…")
            scale   = 2.915
            results = track_video(self.video_path, masks, scale_um_per_px=scale)

            # ── MDP + force ───────────────────────────────────────────────────
            roi_list = []
            for i, tr in enumerate(results):
                if self._abort:
                    return
                self.stage.emit(f"MDP analysis ROI {i+1}/{len(results)}…")
                signal, axis = select_dominant_signal(tr.signal_x, tr.signal_y, tr.time)
                mdp   = calculate_mdp_metrics(signal, tr.time)
                force = compute_contractility(tr.signal_mag, tr.time, frame_rate, mdp.peak_locs)
                morph = compute_mask_morphology(masks[i], scale)
                roi_list.append({
                    'roi_index': i + 1, 'dominant_axis': axis,
                    'signal_x': tr.signal_x, 'signal_y': tr.signal_y,
                    'signal': signal, 'global_trace': force['global_trace'],
                    'time': tr.time, 'frame_rate': frame_rate,
                    'mdp': mdp, 'force': force, 'mask': masks[i],
                    'morphology': morph, 'k': 1.0, 'd': 0.7,
                })

            self.stage.emit("Saving results…")
            data = {
                'video_path': self.video_path,
                'frame_rgb':  frame_rgb,
                'roi_list':   roi_list,
                'params':     {'k_mult': 1.0, 'min_dist': 0.7, 'scale_um_per_px': scale},
                'status':     'Computed',
            }
            with open(pkl_path, 'wb') as f:
                pickle.dump(data, f)

            elapsed = time.time() - t0
            self.finished.emit(str(pkl_path), elapsed)

        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n{traceback.format_exc()}")


# ── Dialog ────────────────────────────────────────────────────────────────────

class QuickAnalysisDialog(QDialog):
    def __init__(self, token: str, user_info: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MyoOptix")
        self.setMinimumWidth(500)
        self.setAcceptDrops(True)
        self._token      = token
        self._user_info  = user_info
        self._video_path = ""
        self._worker     = None
        self._roi_boxes  = []
        self._online     = True
        self._build_ui()
        self._start_net_monitor()

    # ── drag & drop ──────────────────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if Path(path).suffix.lower() in ('.mov', '.mp4', '.avi'):
                self._set_video(path)

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(10)

        # offline banner (hidden by default)
        self._offline_banner = QLabel("No connection — reconnecting…")
        self._offline_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._offline_banner.setStyleSheet(
            "background: #c0392b; color: #fff; font-size: 11px; font-weight: bold;"
            "padding: 6px; border-radius: 6px;")
        self._offline_banner.setVisible(False)
        root.addWidget(self._offline_banner)

        # header
        hdr = QHBoxLayout()
        title = QLabel("Quick Analysis")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #3b3a32;")
        hdr.addWidget(title)
        hdr.addStretch()
        name = self._user_info.get("full_name", "")
        inst = self._user_info.get("institution", "")
        user_lbl = QLabel(f"{name}  ·  {inst}")
        user_lbl.setStyleSheet("font-size: 11px; color: #8a8070;")
        hdr.addWidget(user_lbl)
        hdr.addSpacing(12)
        logout_btn = QPushButton("Sign out")
        logout_btn.setStyleSheet(
            "QPushButton { font-size: 11px; color: #8a8070; background: transparent;"
            "border: 1px solid #d6cfc2; border-radius: 5px; padding: 3px 10px; }"
            "QPushButton:hover { color: #c0392b; border-color: #c0392b; }"
        )
        logout_btn.clicked.connect(self._logout)
        hdr.addWidget(logout_btn)
        root.addLayout(hdr)
        root.addWidget(self._divider())

        # drop zone
        self._drop_lbl = QLabel("Drop a video file here\nor click Browse")
        self._drop_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_lbl.setStyleSheet(
            "background: #ede8de; border: 2px dashed #c8c0b0; border-radius: 8px;"
            "color: #8a8070; font-size: 13px; padding: 24px;")
        self._drop_lbl.setMinimumHeight(80)
        root.addWidget(self._drop_lbl)

        browse_row = QHBoxLayout()
        browse_row.addStretch()
        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedWidth(100)
        browse_btn.clicked.connect(self._browse)
        browse_row.addWidget(browse_btn)
        root.addLayout(browse_row)

        root.addWidget(self._divider())

        # segmentation method
        seg_lbl = QLabel("Segmentation method")
        seg_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #6b6456;")
        root.addWidget(seg_lbl)

        self._seg_group = QButtonGroup(self)
        self._rb_unet   = QRadioButton("U-Net (deep learning)")
        self._rb_otsu   = QRadioButton("Otsu (auto-threshold)")
        self._rb_manual = QRadioButton("Manual — draw ROIs on first frame")
        self._rb_unet.setChecked(True)
        for i, rb in enumerate([self._rb_unet, self._rb_otsu, self._rb_manual]):
            self._seg_group.addButton(rb, i)
            root.addWidget(rb)

        root.addWidget(self._divider())

        # progress
        self._status_lbl = QLabel("Ready.")
        self._status_lbl.setStyleSheet("font-size: 11px; color: #6b6456;")
        root.addWidget(self._status_lbl)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setFixedHeight(8)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(80)
        self._log.setStyleSheet(
            "background: #faf7f2; border: 1px solid #d6cfc2; border-radius: 4px;"
            "font-family: monospace; font-size: 11px;")
        self._log.setVisible(False)
        root.addWidget(self._log)

        root.addWidget(self._divider())

        # buttons
        btn_row = QHBoxLayout()
        self._cancel_btn = QPushButton("Close")
        self._cancel_btn.clicked.connect(self._cancel)
        self._run_btn = QPushButton("▶  Run")
        self._run_btn.setProperty("primary", True)
        self._run_btn.style().unpolish(self._run_btn)
        self._run_btn.style().polish(self._run_btn)
        self._run_btn.setFixedHeight(34)
        self._run_btn.clicked.connect(self._run)
        btn_row.addStretch()
        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._run_btn)
        root.addLayout(btn_row)

        self.adjustSize()

    def _divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #d6cfc2;")
        return line

    # ── network monitor ───────────────────────────────────────────────────────

    def _start_net_monitor(self):
        self._net_monitor = _NetMonitor(self._token)
        self._net_monitor.offline.connect(self._on_offline)
        self._net_monitor.online.connect(self._on_online)
        self._net_monitor.start()

    def _on_offline(self):
        self._online = False
        self._offline_banner.setVisible(True)
        if not (self._worker and self._worker.isRunning()):
            self._run_btn.setEnabled(False)
        self.adjustSize()

    def _on_online(self):
        self._online = True
        self._offline_banner.setVisible(False)
        if not (self._worker and self._worker.isRunning()):
            self._run_btn.setEnabled(True)
        self.adjustSize()

    # ── actions ───────────────────────────────────────────────────────────────

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select video", "",
            "Video files (*.mov *.mp4 *.avi);;All files (*)")
        if path:
            self._set_video(path)

    def _set_video(self, path: str):
        self._video_path = path
        name = Path(path).name
        self._drop_lbl.setText(f"📹  {name}")
        self._drop_lbl.setStyleSheet(
            "background: #e8f0e8; border: 2px solid #80b880; border-radius: 8px;"
            "color: #2a6a2a; font-size: 12px; padding: 24px;")
        self._roi_boxes = []

    def _run(self):
        if not self._video_path:
            self._status_lbl.setText("Please select a video file first.")
            return

        roi_boxes = []
        if self._rb_manual.isChecked():
            try:
                from cardio_py.core.io          import read_first_frame
                from cardio_py.core.roi_selector import select_rois
                frame_rgb, _ = read_first_frame(self._video_path)
                roi_boxes = select_rois(frame_rgb,
                                        window_title=f"ROI Selector — {Path(self._video_path).name}")
            except Exception as e:
                self._status_lbl.setText(f"ROI selector error: {e}")
                return
            if not roi_boxes:
                self._status_lbl.setText("No ROIs drawn. Cancelled.")
                return

        seg_method = ("unet" if self._rb_unet.isChecked() else
                      "otsu" if self._rb_otsu.isChecked() else "manual")

        self._run_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._log.setVisible(True)
        self._status_lbl.setText("Running…")

        self._worker = _QuickWorker(
            video_path=self._video_path, seg_method=seg_method,
            min_pct=0.15, max_pct=50.0, roi_boxes=roi_boxes,
        )
        self._worker.stage.connect(self._on_stage)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_stage(self, msg: str):
        self._status_lbl.setText(msg)
        self._log.append(msg)

    def _on_finished(self, pkl_path: str, elapsed: float):
        self._progress.setVisible(False)
        self._status_lbl.setText("Done — opening Review…")
        self._log.append(f"✓ Saved: {pkl_path}")

        # ── log to API (non-blocking, best-effort) ────────────────────────────
        vp = Path(self._video_path)
        try:
            size_mb = vp.stat().st_size / 1_048_576
        except Exception:
            size_mb = 0.0
        try:
            log_analysis(self._token, vp.name, size_mb, elapsed)
        except Exception:
            pass  # don't block user if logging fails

        QApplication.processEvents()

        # ── open Review (uses bundled ui/dialog_review.py) ───────────────────
        try:
            from ui.dialog_review import ReviewDialog
            dlg = ReviewDialog(pkl_path=pkl_path, parent=self.parent())
            self.hide()
            dlg.exec()
            self.show()
        except Exception as e:
            import traceback
            msg = f"Could not open Review:\n{e}\n\n{traceback.format_exc()}"
            print(msg)
            self._status_lbl.setText(f"Error: {e}")
            self._log.append(msg)
            self._run_btn.setEnabled(True)
            return

        # reset for next video
        self._run_btn.setEnabled(self._online)
        self._progress.setVisible(False)
        self._log.setVisible(False)
        self._video_path = ""
        self._drop_lbl.setText("Drop a video file here\nor click Browse")
        self._drop_lbl.setStyleSheet(
            "background: #ede8de; border: 2px dashed #c8c0b0; border-radius: 8px;"
            "color: #8a8070; font-size: 13px; padding: 24px;")
        self._status_lbl.setText("Ready.")

    def _on_error(self, msg: str):
        self._progress.setVisible(False)
        self._run_btn.setEnabled(self._online)
        self._status_lbl.setText("Error — see log.")
        self._log.append(f"✗ {msg}")

    def _logout(self):
        if self._worker and self._worker.isRunning():
            return  # don't allow logout while running
        import token_store
        token_store.clear()
        if hasattr(self, "_net_monitor"):
            self._net_monitor.stop()
            self._net_monitor.wait()
        self.reject()

    def _cancel(self):
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._worker.wait()
        self.reject()

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._worker.wait()
        if hasattr(self, "_net_monitor"):
            self._net_monitor.stop()
            self._net_monitor.wait()
        event.accept()
