"""
Quick Analysis dialog.

Flow:
  1. User drops / browses a single video file
  2. Selects segmentation method: U-Net / Otsu / Manual
  3. Clicks Run → segment + track + MDP + force
  4. Results saved to  <video_folder>/<video_stem>/  as a pkl
  5. ReviewDialog opens automatically
"""

import sys
import pickle
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QButtonGroup, QRadioButton, QFrame, QFileDialog,
    QProgressBar, QTextEdit, QApplication,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent


# ── Worker ────────────────────────────────────────────────────────────────────

class _QuickWorker(QThread):
    stage    = pyqtSignal(str)          # stage message
    finished = pyqtSignal(str)          # pkl_path on success
    error    = pyqtSignal(str)          # error message

    def __init__(self, video_path: str, seg_method: str,
                 min_pct: float, max_pct: float,
                 roi_boxes: list,       # [(x,y,w,h),...] for manual, else []
                 parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.seg_method = seg_method    # "unet" | "otsu" | "manual"
        self.min_pct    = min_pct
        self.max_pct    = max_pct
        self.roi_boxes  = roi_boxes
        self._abort     = False

    def abort(self):
        self._abort = True

    def run(self):
        try:
            # ── ensure cardio_py importable ──────────────────────────────────
            proj_root = str(Path(__file__).parent.parent.parent)
            if proj_root not in sys.path:
                sys.path.insert(0, proj_root)

            import numpy as np
            from cardio_py.core.io       import read_first_frame
            from cardio_py.core.tracking import track_video
            from cardio_py.core.mdp      import calculate_mdp_metrics, select_dominant_signal
            from cardio_py.core.force    import compute_contractility

            vp   = Path(self.video_path)
            stem = vp.stem

            # output dir: <video_folder>/<video_stem>/
            out_dir = vp.parent / stem
            out_dir.mkdir(parents=True, exist_ok=True)
            pkl_dir = out_dir / "_pkl_for_review"
            pkl_dir.mkdir(exist_ok=True)
            pkl_path = pkl_dir / f"{stem}.pkl"

            # ── read first frame ─────────────────────────────────────────────
            self.stage.emit("Reading video…")
            frame_rgb, frame_rate = read_first_frame(self.video_path)

            # ── segmentation ─────────────────────────────────────────────────
            masks = []
            if self.seg_method == "manual":
                self.stage.emit("Manual ROI — converting boxes to masks…")
                h, w = frame_rgb.shape[:2]
                for (x, y, bw, bh) in self.roi_boxes:
                    m = np.zeros((h, w), dtype=bool)
                    m[y:y+bh, x:x+bw] = True
                    masks.append(m)
            else:
                self.stage.emit("Segmentation…")
                if self.seg_method == "unet":
                    from cardio_py.core.segmentation import segment_unet
                    masks, _ = segment_unet(frame_rgb,
                                            min_pct=self.min_pct,
                                            max_pct=self.max_pct)
                else:
                    from cardio_py.core.segmentation import segment_otsu
                    masks, _ = segment_otsu(frame_rgb,
                                            min_pct=self.min_pct,
                                            max_pct=self.max_pct)

            if not masks:
                self.error.emit("No ROIs found. Try adjusting the area filter or use Manual mode.")
                return

            # ── KLT tracking ─────────────────────────────────────────────────
            self.stage.emit(f"KLT tracking  ({len(masks)} ROI(s))…")
            scale = 2.915  # TCY_4X default
            results = track_video(self.video_path, masks, scale_um_per_px=scale)

            # ── MDP + force per ROI ──────────────────────────────────────────
            roi_list = []
            for i, tr in enumerate(results):
                if self._abort:
                    return
                self.stage.emit(f"MDP analysis  ROI {i+1}/{len(results)}…")
                time      = tr.time
                signal_x  = tr.signal_x
                signal_y  = tr.signal_y
                signal_mag = tr.signal_mag

                signal, axis = select_dominant_signal(signal_x, signal_y, time)

                mdp   = calculate_mdp_metrics(signal, time)
                force = compute_contractility(signal_mag, time, frame_rate, mdp.peak_locs)

                roi_list.append({
                    'roi_index':     i,
                    'dominant_axis': axis,
                    'signal_x':      signal_x,
                    'signal_y':      signal_y,
                    'signal':        signal,
                    'global_trace':  force['global_trace'],
                    'time':          time,
                    'frame_rate':    frame_rate,
                    'mdp':           mdp,
                    'force':         force,
                    'mask':          masks[i],
                    'k':             1.0,
                    'd':             0.2,
                })

            # ── save pkl ─────────────────────────────────────────────────────
            self.stage.emit("Saving results…")
            data = {
                'video_path': self.video_path,
                'frame_rgb':  frame_rgb,
                'roi_list':   roi_list,
                'params':     {
                    'k_mult':         1.0,
                    'min_dist':       0.2,
                    'scale_um_per_px': scale,
                },
                'status': 'Computed',
            }
            with open(pkl_path, 'wb') as f:
                pickle.dump(data, f)

            self.finished.emit(str(pkl_path))

        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n{traceback.format_exc()}")


# ── Dialog ────────────────────────────────────────────────────────────────────

class QuickAnalysisDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick Analysis")
        self.setMinimumWidth(480)
        self.setAcceptDrops(True)
        self._video_path = ""
        self._worker     = None
        self._roi_boxes  = []   # filled when Manual mode is used before Run
        self._build_ui()

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
        root.setSpacing(12)

        title = QLabel("⚡  Quick Analysis")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #3b3a32;")
        root.addWidget(title)
        root.addWidget(self._divider())

        # ── drop zone ────────────────────────────────────────────────────────
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

        # ── segmentation method ───────────────────────────────────────────────
        seg_lbl = QLabel("Segmentation method")
        seg_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #6b6456;")
        root.addWidget(seg_lbl)

        self._seg_group = QButtonGroup(self)
        self._rb_unet   = QRadioButton("U-Net (deep learning)")
        self._rb_otsu   = QRadioButton("Otsu (auto-threshold)")
        self._rb_manual = QRadioButton("Manual  —  draw ROIs on first frame")
        self._rb_unet.setChecked(True)
        for i, rb in enumerate([self._rb_unet, self._rb_otsu, self._rb_manual]):
            self._seg_group.addButton(rb, i)
            root.addWidget(rb)

        root.addWidget(self._divider())

        # ── progress ──────────────────────────────────────────────────────────
        self._status_lbl = QLabel("Ready.")
        self._status_lbl.setStyleSheet("font-size: 11px; color: #6b6456;")
        root.addWidget(self._status_lbl)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)   # indeterminate
        self._progress.setFixedHeight(8)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(90)
        self._log.setStyleSheet(
            "background: #faf7f2; border: 1px solid #d6cfc2; border-radius: 4px;"
            "font-family: monospace; font-size: 11px;")
        self._log.setVisible(False)
        root.addWidget(self._log)

        root.addWidget(self._divider())

        # ── buttons ───────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self._cancel_btn = QPushButton("Cancel")
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
        self._roi_boxes = []   # reset manual boxes when video changes

    def _run(self):
        if not self._video_path:
            self._status_lbl.setText("Please select a video file first.")
            return

        roi_boxes = []

        # ── Manual: open OpenCV ROI selector before computing ─────────────────
        if self._rb_manual.isChecked():
            try:
                proj_root = str(Path(__file__).parent.parent.parent)
                if proj_root not in sys.path:
                    sys.path.insert(0, proj_root)
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

        seg_method = "unet" if self._rb_unet.isChecked() else \
                     "otsu" if self._rb_otsu.isChecked() else "manual"

        self._run_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._log.setVisible(True)
        self._status_lbl.setText("Running…")

        self._worker = _QuickWorker(
            video_path  = self._video_path,
            seg_method  = seg_method,
            min_pct     = 0.15,
            max_pct     = 50.0,
            roi_boxes   = roi_boxes,
        )
        self._worker.stage.connect(self._on_stage)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_stage(self, msg: str):
        self._status_lbl.setText(msg)
        self._log.append(msg)

    def _on_finished(self, pkl_path: str):
        self._progress.setVisible(False)
        self._status_lbl.setText("Done — opening Review…")
        self._log.append(f"✓ Saved: {pkl_path}")
        QApplication.processEvents()

        from .dialog_review import ReviewDialog
        dlg = ReviewDialog(pkl_path=pkl_path, parent=self.parent())
        self.accept()
        dlg.exec()

    def _on_error(self, msg: str):
        self._progress.setVisible(False)
        self._run_btn.setEnabled(True)
        self._status_lbl.setText("Error — see log.")
        self._log.append(f"✗ {msg}")

    def _cancel(self):
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._worker.wait()
        self.reject()

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._worker.wait()
        event.accept()
