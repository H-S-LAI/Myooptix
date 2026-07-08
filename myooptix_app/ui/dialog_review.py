"""
Review dialog — loads a .pkl result and shows:
  Left panel: ROI overlay image, ROI nav, beat metrics, params, action buttons
  Right panel: matplotlib waveforms — BPM, MDP (CS/CE/RE), Force
"""

import sys
import json
import pickle
import numpy as np
import cv2
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QSlider, QSplitter, QSizePolicy, QWidget,
    QMessageBox, QFileDialog, QScrollArea,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QMouseEvent


# ── Clickable label ──────────────────────────────────────────────────────────

class _ClickableLabel(QLabel):
    clicked = pyqtSignal()
    def mousePressEvent(self, e: QMouseEvent):
        self.clicked.emit()


class _ZoomDialog(QDialog):
    """Full-size overlay popup — click anywhere to close."""
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("background: rgba(0,0,0,180);")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel()
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        screen = self.screen().availableGeometry() if self.screen() else None
        if screen:
            max_w = int(screen.width()  * 0.85)
            max_h = int(screen.height() * 0.85)
            lbl.setPixmap(pixmap.scaled(max_w, max_h,
                          Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation))
        else:
            lbl.setPixmap(pixmap)
        lay.addWidget(lbl)

    def mousePressEvent(self, e):
        self.accept()


# ── ROI overlay ──────────────────────────────────────────────────────────────

def _roi_overlay(frame_rgb: np.ndarray, roi_list: list, active_idx: int) -> np.ndarray:
    img = frame_rgb.copy()
    for i, roi in enumerate(roi_list):
        mask = roi.get('mask')
        if mask is None:
            continue
        color = (0, 220, 255) if i == active_idx else (220, 60, 60)
        lw = 3 if i == active_idx else 2
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        if not rows.any():
            continue
        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]
        bgr = (color[2], color[1], color[0])
        cv2.rectangle(img, (cmin, rmin), (cmax, rmax), bgr, lw + 1)
        cv2.putText(img, f"ROI {roi['roi_index']}",
                    (cmin, max(rmin - 10, 30)),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.4, bgr, 3)
    return img


def _ndarray_to_pixmap(arr: np.ndarray, max_w: int, max_h: int) -> QPixmap:
    h, w = arr.shape[:2]
    scale = min(max_w / w, max_h / h, 1.0)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    resized = cv2.resize(arr, (nw, nh))
    img = QImage(resized.data, nw, nh, nw * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(img)


# ── Summary image export (one PNG per ROI) ───────────────────────────────────

def _export_summary_images(stem: str, roi_list: list, frame_rgb, out_dir: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir.mkdir(exist_ok=True)

    for seq_idx, roi in enumerate(roi_list):
        roi_idx = seq_idx + 1          # sequential 1-based, matches Excel sheet numbering
        mdp        = roi.get('mdp')
        force_dict = roi.get('force', {})
        time       = roi.get('time', np.array([]))

        if mdp and len(mdp.signal_display) == len(time):
            sig = mdp.signal_display
        else:
            sig = roi.get('signal', roi.get('signal_x', np.array([])))

        f_trace = force_dict.get('global_trace', np.array([]))
        bpm     = 60 / mdp.IBI_avg if (mdp and mdp.IBI_avg > 0) else 0
        axis    = roi.get('dominant_axis', '?')
        flip    = ' · Flipped' if (mdp and mdp.is_flipped) else ''

        fig, axes = plt.subplots(1, 4, figsize=(18, 4),
                                 facecolor='#fafafa',
                                 gridspec_kw={'width_ratios': [1.2, 2, 2, 2]})
        fig.suptitle(
            f"{stem}  —  ROI {roi_idx}  [{axis}-axis{flip}]   BPM={bpm:.1f}",
            fontsize=12, fontweight='bold', color='#2a2a2a')

        # ── col 0: ROI overlay ───────────────────────────────────────────────
        ax0 = axes[0]
        if frame_rgb is not None:
            overlay = _roi_overlay(frame_rgb, roi_list, seq_idx)   # list position
            ax0.imshow(overlay)
        ax0.set_title(f"ROI {roi_idx} location", fontsize=9)
        ax0.axis('off')

        COLORS = {'main': '#4a7abf', 'peak': '#d03030',
                  'cs': '#2e8c2e', 'ce': '#3a6abf', 're': '#a030a0',
                  'force': '#b04040'}

        # ── col 1: BPM waveform ──────────────────────────────────────────────
        ax1 = axes[1]
        if len(time) and len(sig):
            mn = min(len(time), len(sig))
            ax1.plot(time[:mn], sig[:mn], color=COLORS['main'], lw=1.0)
            if mdp and mdp.HR > 0:
                yp = np.interp(mdp.peak_locs, time[:mn], sig[:mn])
                ax1.scatter(mdp.peak_locs, yp, color=COLORS['peak'], s=20, zorder=5,
                            label=f'Peaks (n={mdp.HR})')
        ax1.set_title(f"BPM={bpm:.1f}  HR={mdp.HR if mdp else '?'}", fontsize=9)
        ax1.set_xlabel('Time (s)', fontsize=8)
        ax1.set_ylabel('Velocity (µm/s)', fontsize=8)
        ax1.legend(fontsize=7)
        ax1.grid(alpha=0.25)

        # ── col 2: MDP (CS/CE/RE) ────────────────────────────────────────────
        ax2 = axes[2]
        if len(time) and len(sig):
            mn = min(len(time), len(sig))
            ax2.plot(time[:mn], sig[:mn], color=COLORS['main'], lw=1.0, alpha=0.8)
            if mdp and mdp.HR > 0:
                ax2.scatter(mdp.peak_locs,
                            np.interp(mdp.peak_locs, time[:mn], sig[:mn]),
                            color=COLORS['peak'], s=40, marker='*', zorder=6, label='Peak')
                for arr, c, m, lbl in [
                    (mdp.CS, COLORS['cs'], '>',  'CS'),
                    (mdp.CE, COLORS['ce'], '<',  'CE'),
                    (mdp.RE, COLORS['re'], '^',  'RE'),
                ]:
                    valid = arr[~np.isnan(arr)] if len(arr) > 0 else np.array([])
                    if len(valid):
                        ax2.scatter(valid, np.interp(valid, time[:mn], sig[:mn]),
                                    color=c, s=30, marker=m, zorder=5, label=lbl)
                if mdp:
                    st_ms = float(np.nanmean(mdp.ST)) * 1000 if len(mdp.ST) else float('nan')
                    dt_ms = float(np.nanmean(mdp.DT)) * 1000 if len(mdp.DT) else float('nan')
                    ax2.set_title(f"ST={st_ms:.0f} ms  DT={dt_ms:.0f} ms", fontsize=9)
        ax2.set_xlabel('Time (s)', fontsize=8)
        ax2.set_ylabel('Velocity (µm/s)', fontsize=8)
        ax2.legend(fontsize=7)
        ax2.grid(alpha=0.25)

        # ── col 3: Force ─────────────────────────────────────────────────────
        ax3 = axes[3]
        if len(time) and len(f_trace):
            mn = min(len(time), len(f_trace))
            ax3.plot(time[:mn], f_trace[:mn], color=COLORS['force'], lw=1.0)
            f_locs = force_dict.get('force_locs', np.array([]))
            f_vals = force_dict.get('force_vals', np.array([]))
            if len(f_locs):
                ax3.scatter(f_locs, f_vals, color=COLORS['peak'], s=20, zorder=5)
            ax3.set_title(
                f"Force avg={force_dict.get('contractility_mag', 0):.2f} µm/s", fontsize=9)
        ax3.set_xlabel('Time (s)', fontsize=8)
        ax3.set_ylabel('Force (µm/s)', fontsize=8)
        ax3.grid(alpha=0.25)

        for ax in axes[1:]:
            ax.tick_params(labelsize=7)

        fig.tight_layout(rect=[0, 0, 1, 0.93])
        out_path = out_dir / f"{stem}_ROI{roi_idx}_Summary.png"
        fig.savefig(str(out_path), dpi=150, bbox_inches='tight')
        plt.close(fig)


from PyQt6.QtCore import QThread
from .toast import Toast as _Toast


class _ExportWorker(QThread):
    success = pyqtSignal(int)   # n_rois
    error   = pyqtSignal(str)

    def __init__(self, pkl_path, roi_list, frame_rgb, proj_root):
        super().__init__()
        self._pkl_path  = pkl_path
        self._roi_list  = roi_list
        self._frame_rgb = frame_rgb
        self._proj_root = proj_root

    def run(self):
        import sys
        if self._proj_root not in sys.path:
            sys.path.insert(0, self._proj_root)
        try:
            from cardio_py.core.io import export_analysis_excel
            from pathlib import Path
            import json
            stem    = Path(self._pkl_path).stem
            out_dir = Path(self._pkl_path).parent.parent / "final_excel_exports"
            out_dir.mkdir(exist_ok=True)
            export_analysis_excel(str(out_dir / stem), self._roi_list, self._roi_list[0]['time'])
            _export_summary_images(stem, self._roi_list, self._frame_rgb,
                                   Path(self._pkl_path).parent.parent / "summary_images")
            sidecar = Path(self._pkl_path).with_suffix('.json')
            try:
                meta = json.loads(sidecar.read_text()) if sidecar.exists() else {}
            except Exception:
                meta = {}
            meta['status'] = 'Reviewed'
            sidecar.write_text(json.dumps(meta, indent=2))
            self.success.emit(len(self._roi_list))
        except Exception as e:
            self.error.emit(str(e))

# ── Matplotlib canvas ────────────────────────────────────────────────────────

def _make_canvas(roi_data: dict | None = None):
    import matplotlib
    matplotlib.use("QtAgg")
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure

    fig = Figure(facecolor="#faf7f2", tight_layout=dict(pad=1.2, h_pad=0.8))
    canvas = FigureCanvas(fig)
    canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    if roi_data is None:
        ax = fig.add_subplot(1, 1, 1)
        ax.text(0.5, 0.5, "No data", transform=ax.transAxes,
                ha='center', va='center', color='#8a8070', fontsize=12)
        ax.set_axis_off()
        canvas.draw()
        return canvas

    time       = roi_data.get('time', np.array([]))
    mdp        = roi_data.get('mdp')
    force_dict = roi_data.get('force', {})

    if mdp and len(mdp.signal_display) == len(time):
        sig = mdp.signal_display
    else:
        sig = roi_data.get('signal', roi_data.get('signal_x', np.array([])))

    f_trace = force_dict.get('global_trace', np.array([]))

    COLORS = {'main': '#4a7abf', 'peak': '#d03030',
              'cs': '#2e8c2e', 'ce': '#3a6abf', 're': '#a030a0',
              'force': '#b04040'}

    # ── subplot 1: BPM waveform ──────────────────────────────────────────────
    ax1 = fig.add_subplot(3, 1, 1)
    if len(time) and len(sig):
        mn = min(len(time), len(sig))
        ax1.plot(time[:mn], sig[:mn], color=COLORS['main'], lw=1.2, label='Velocity')
        if mdp and mdp.HR > 0:
            yp = np.interp(mdp.peak_locs, time[:mn], sig[:mn])
            ax1.scatter(mdp.peak_locs, yp, color=COLORS['peak'], s=30, zorder=5,
                        label=f'Peaks (n={mdp.HR})')
        bpm  = 60 / mdp.IBI_avg if (mdp and mdp.IBI_avg > 0) else 0
        flip = ' · Flipped' if (mdp and mdp.is_flipped) else ''
        ax1.set_title(
            f"ROI {roi_data.get('roi_index','?')} — [{roi_data.get('dominant_axis','?')}{flip}]"
            f"   BPM={bpm:.1f}  HR={mdp.HR if mdp else '?'}",
            fontsize=9, color='#3b3a32')
    ax1.set_ylabel('Velocity (µm/s)', fontsize=8, color='#6b6456')
    ax1.set_xticklabels([])
    ax1.legend(fontsize=7, loc='upper right')

    # ── subplot 2: MDP — CS / CE / RE ────────────────────────────────────────
    ax2 = fig.add_subplot(3, 1, 2)
    if len(time) and len(sig):
        mn = min(len(time), len(sig))
        ax2.plot(time[:mn], sig[:mn], color=COLORS['main'], lw=1.0, alpha=0.8)
        if mdp and mdp.HR > 0:
            ax2.scatter(mdp.peak_locs,
                        np.interp(mdp.peak_locs, time[:mn], sig[:mn]),
                        color=COLORS['peak'], s=50, marker='*', zorder=6, label='Peak')
            for arr, c, m, lbl in [
                (mdp.CS, COLORS['cs'], '>',  'CS'),
                (mdp.CE, COLORS['ce'], '<',  'CE'),
                (mdp.RE, COLORS['re'], '^',  'RE'),
            ]:
                valid = arr[~np.isnan(arr)] if len(arr) > 0 else np.array([])
                if len(valid):
                    ax2.scatter(valid, np.interp(valid, time[:mn], sig[:mn]),
                                color=c, s=40, marker=m, zorder=5, label=lbl)
            if mdp:
                st_ms = float(np.nanmean(mdp.ST)) * 1000 if len(mdp.ST) else float('nan')
                dt_ms = float(np.nanmean(mdp.DT)) * 1000 if len(mdp.DT) else float('nan')
                ax2.set_title(f"MDP  ST={st_ms:.0f} ms  DT={dt_ms:.0f} ms",
                              fontsize=9, color='#3b3a32')
    ax2.set_ylabel('Velocity (µm/s)', fontsize=8, color='#6b6456')
    ax2.set_xticklabels([])
    ax2.legend(fontsize=7, loc='upper right')

    # ── subplot 3: Force ─────────────────────────────────────────────────────
    ax3 = fig.add_subplot(3, 1, 3)
    if len(time) and len(f_trace):
        mn = min(len(time), len(f_trace))
        ax3.plot(time[:mn], f_trace[:mn], color=COLORS['force'], lw=1.2, label='Force')
        f_locs = force_dict.get('force_locs', np.array([]))
        f_vals = force_dict.get('force_vals', np.array([]))
        if len(f_locs):
            ax3.scatter(f_locs, f_vals, color=COLORS['peak'], s=30, zorder=5,
                        label=f"mean={force_dict.get('contractility_mag', 0):.2f}")
        ax3.set_title(
            f"Force  avg={force_dict.get('contractility_mag', 0):.2f} µm/s",
            fontsize=9, color='#3b3a32')
    ax3.set_xlabel('Time (s)', fontsize=8, color='#6b6456')
    ax3.set_ylabel('Force (µm/s)', fontsize=8, color='#6b6456')
    ax3.legend(fontsize=7, loc='upper right')

    for ax in (ax1, ax2, ax3):
        ax.set_facecolor("#fdfaf5")
        ax.tick_params(colors="#8a8070", labelsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor("#d6cfc2")
        ax.grid(alpha=0.25, color='#d6cfc2')

    canvas.draw()
    return canvas


# ── Dialog ──────────────────────────────────────────────────────────────────

class ReviewDialog(QDialog):
    def __init__(self, pkl_path: str = "", parent=None):
        super().__init__(parent)
        self._pkl_path = pkl_path
        self._data     = None
        self._roi_idx  = 0
        self._canvas   = None

        self._load_data()
        title = Path(pkl_path).stem if pkl_path else "Review"
        self.setWindowTitle(f"Review — {title}")
        self.resize(960, 620)
        self._splitter        = None
        self._metric_labels   = {}
        self._overlay_lbl     = None
        self._overlay_arr     = None   # full-res overlay ndarray for zoom
        self._exported        = False
        self._recompute_timer = QTimer(self)
        self._recompute_timer.setSingleShot(True)
        self._recompute_timer.setInterval(400)   # 400 ms debounce
        self._recompute_timer.timeout.connect(self._recompute)
        self._build_ui()
        QTimer.singleShot(100, self._add_canvas)

    def _load_data(self):
        if not self._pkl_path or not Path(self._pkl_path).exists():
            return
        try:
            with open(self._pkl_path, 'rb') as f:
                self._data = pickle.load(f)
        except Exception as e:
            print(f"ReviewDialog: cannot load pkl: {e}")

    # ── Build UI ────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # ════════════════════════════════════════════════════════════════════
        # Left panel
        # ════════════════════════════════════════════════════════════════════
        left = QWidget()
        left.setFixedWidth(280)
        left.setStyleSheet("background-color: #f0ebe0;")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(12, 12, 12, 12)
        lv.setSpacing(8)

        # ── ROI overlay image ────────────────────────────────────────────────
        ov_title = QLabel("ROI Locations")
        ov_title.setStyleSheet(
            "font-size: 12px; font-weight: bold; color: #6b6456; background: transparent;")
        lv.addWidget(ov_title)

        self._overlay_lbl = _ClickableLabel()
        self._overlay_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overlay_lbl.setStyleSheet(
            "background: #f5f0e8; border: 1px solid #d6cfc2; border-radius: 4px;")
        self._overlay_lbl.setMinimumHeight(160)
        self._overlay_lbl.setMaximumHeight(260)
        self._overlay_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self._overlay_lbl.clicked.connect(self._zoom_overlay)
        lv.addWidget(self._overlay_lbl)

        # ── ROI selector ────────────────────────────────────────────────────
        roi_box = QGroupBox("ROI")
        rb = QVBoxLayout(roi_box)
        rb.setSpacing(4)
        self.roi_combo = QComboBox()
        self._populate_roi_combo()
        self.roi_combo.currentIndexChanged.connect(self._on_roi_changed)
        rb.addWidget(self.roi_combo)
        nav = QHBoxLayout()
        prev_btn = QPushButton("◀  Prev")
        next_btn = QPushButton("Next  ▶")
        prev_btn.clicked.connect(lambda: self._step_roi(-1))
        next_btn.clicked.connect(lambda: self._step_roi(+1))
        nav.addWidget(prev_btn)
        nav.addWidget(next_btn)
        rb.addLayout(nav)
        lv.addWidget(roi_box)

        # ── Beat metrics ────────────────────────────────────────────────────
        metrics_box = QGroupBox("Beat Metrics")
        mb = QVBoxLayout(metrics_box)
        mb.setSpacing(4)
        for key, label in [("HR",       "HR (BPM)"),
                            ("ST",       "ST (ms)"),
                            ("DT",       "DT (ms)"),
                            ("Force",    "Force (µm/s)"),
                            ("ForceStd", "Contractility Std"),
                            ("Diameter", "Diameter (µm)")]:
            row = QHBoxLayout()
            lbl_w = QLabel(label)
            lbl_w.setStyleSheet("color: #6b6456; background: transparent; font-size: 11px;")
            val_w = QLabel("—")
            val_w.setStyleSheet(
                "color: #3b3a32; font-weight: bold; background: transparent; font-size: 11px;")
            val_w.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(lbl_w)
            row.addWidget(val_w)
            mb.addLayout(row)
            self._metric_labels[key] = val_w
        lv.addWidget(metrics_box)

        # ── Parameters ──────────────────────────────────────────────────────
        param_box = QGroupBox("Parameters")
        pb = QVBoxLayout(param_box)
        pb.setSpacing(4)

        k_row = QHBoxLayout()
        k_row.addWidget(self._tiny_lbl("K multiplier"))
        self._k_lbl = QLabel("1.0")
        self._k_lbl.setStyleSheet(
            "color: #7c9c6e; font-weight: bold; background: transparent; font-size: 11px;")
        k_row.addWidget(self._k_lbl)
        pb.addLayout(k_row)
        self._k_slider = QSlider(Qt.Orientation.Horizontal)
        self._k_slider.setRange(1, 50)
        self._k_slider.setValue(10)
        self._k_slider.valueChanged.connect(self._on_k_changed)
        pb.addWidget(self._k_slider)

        d_row = QHBoxLayout()
        d_row.addWidget(self._tiny_lbl("Min dist (s)"))
        self._d_lbl = QLabel("0.20 s")
        self._d_lbl.setStyleSheet(
            "color: #7c9c6e; font-weight: bold; background: transparent; font-size: 11px;")
        d_row.addWidget(self._d_lbl)
        pb.addLayout(d_row)
        self._d_slider = QSlider(Qt.Orientation.Horizontal)
        self._d_slider.setRange(1, 40)
        self._d_slider.setValue(4)
        self._d_slider.valueChanged.connect(self._on_d_changed)
        pb.addWidget(self._d_slider)
        lv.addWidget(param_box)

        lv.addStretch()

        # ── Action buttons ───────────────────────────────────────────────────
        del_btn = QPushButton("Delete ROI")
        del_btn.setFixedHeight(32)
        del_btn.setStyleSheet(
            "QPushButton { background: #f5f0e8; color: #c0392b; border: 1.5px solid #c0392b;"
            " border-radius: 5px; font-weight: bold; padding: 6px 16px; }"
            "QPushButton:hover { background: #fce8e6; border-color: #a93226; color: #a93226; }"
            "QPushButton:pressed { background: #f5d5d2; }"
        )
        del_btn.clicked.connect(self._delete_roi)
        lv.addWidget(del_btn)

        exp_btn = QPushButton("Export & Mark Reviewed")
        exp_btn.setFixedHeight(32)
        exp_btn.setStyleSheet(
            "QPushButton { background: #7c9c6e; color: #ffffff; border: none;"
            " border-radius: 5px; font-weight: bold; padding: 6px 16px; }"
            "QPushButton:hover { background: #6a8a5c; }"
            "QPushButton:pressed { background: #5a7a4c; }"
        )
        exp_btn.clicked.connect(self._export_and_review)
        lv.addWidget(exp_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(32)
        cancel_btn.clicked.connect(self.reject)
        lv.addWidget(cancel_btn)

        # ════════════════════════════════════════════════════════════════════
        # Right panel — matplotlib placeholder
        # ════════════════════════════════════════════════════════════════════
        self._canvas_placeholder = QWidget()
        self._canvas_placeholder.setStyleSheet("background-color: #faf7f2;")

        self._splitter.addWidget(left)
        self._splitter.addWidget(self._canvas_placeholder)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        root.addWidget(self._splitter)

        self._update_metrics()
        self._update_overlay()
        self._load_roi_params()

    def _tiny_lbl(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet("background: transparent; font-size: 11px; color: #6b6456;")
        return l

    # ── ROI helpers ─────────────────────────────────────────────────────────

    def _populate_roi_combo(self):
        self.roi_combo.blockSignals(True)
        self.roi_combo.clear()
        if self._data:
            for r in self._data.get('roi_list', []):
                axis = r.get('dominant_axis', '?')
                self.roi_combo.addItem(f"ROI {r['roi_index']} — {axis} axis")
        else:
            self.roi_combo.addItem("No data")
        self.roi_combo.blockSignals(False)

    def _current_roi(self) -> dict | None:
        if not self._data:
            return None
        roi_list = self._data.get('roi_list', [])
        if 0 <= self._roi_idx < len(roi_list):
            return roi_list[self._roi_idx]
        return None

    def _on_roi_changed(self, idx):
        self._roi_idx = idx
        self._update_metrics()
        self._update_overlay()
        self._load_roi_params()
        self._refresh_canvas()

    def _load_roi_params(self):
        """Load this ROI's saved k/d into the sliders without triggering recompute."""
        roi = self._current_roi()
        if roi is None:
            return
        default_k = self._data.get('params', {}).get('k_mult', 1.0) if self._data else 1.0
        default_d = self._data.get('params', {}).get('min_dist', 0.2) if self._data else 0.2
        k = roi.get('k', default_k)
        d = roi.get('d', default_d)
        self._recompute_timer.stop()
        self._k_slider.blockSignals(True)
        self._d_slider.blockSignals(True)
        self._k_slider.setValue(int(round(k * 10)))
        self._d_slider.setValue(int(round(d / 0.05)))
        self._k_lbl.setText(f"{k:.1f}")
        self._d_lbl.setText(f"{d:.2f} s")
        self._k_slider.blockSignals(False)
        self._d_slider.blockSignals(False)

    def _step_roi(self, delta):
        if not self._data:
            return
        n = len(self._data.get('roi_list', []))
        self._roi_idx = (self._roi_idx + delta) % max(n, 1)
        self.roi_combo.setCurrentIndex(self._roi_idx)

    def _on_k_changed(self, v):
        self._k_lbl.setText(f"{v/10:.1f}")
        self._recompute_timer.start()

    def _on_d_changed(self, v):
        self._d_lbl.setText(f"{v*0.05:.2f} s")
        self._recompute_timer.start()

    # ── Overlay image ────────────────────────────────────────────────────────

    def _update_overlay(self):
        if self._overlay_lbl is None or not self._data:
            return
        frame_rgb = self._data.get('frame_rgb')
        roi_list  = self._data.get('roi_list', [])
        if frame_rgb is None:
            self._overlay_lbl.setText("No frame")
            return
        self._overlay_arr = _roi_overlay(frame_rgb, roi_list, self._roi_idx)
        w = self._overlay_lbl.width()  or 256
        h = self._overlay_lbl.maximumHeight()
        pix = _ndarray_to_pixmap(self._overlay_arr, max_w=w - 4, max_h=h - 4)
        self._overlay_lbl.setPixmap(pix)

    def _zoom_overlay(self):
        if self._overlay_arr is None:
            return
        h, w = self._overlay_arr.shape[:2]
        img = QImage(self._overlay_arr.data, w, h, w * 3, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(img)
        dlg = _ZoomDialog(pix, self)
        dlg.exec()

    # ── Canvas ───────────────────────────────────────────────────────────────

    def _add_canvas(self):
        try:
            canvas = _make_canvas(self._current_roi())
            old = self._splitter.widget(1)
            self._splitter.replaceWidget(1, canvas)
            old.deleteLater()
            self._canvas = canvas
            self._update_overlay()
        except Exception as e:
            print(f"Canvas error: {e}")

    def _refresh_canvas(self):
        if self._canvas is None:
            return
        try:
            canvas = _make_canvas(self._current_roi())
            old = self._splitter.widget(1)
            self._splitter.replaceWidget(1, canvas)
            old.deleteLater()
            self._canvas = canvas
        except Exception as e:
            print(f"Canvas refresh error: {e}")

    # ── Metrics ──────────────────────────────────────────────────────────────

    def _update_metrics(self):
        roi = self._current_roi()
        if roi is None:
            for lbl in self._metric_labels.values():
                lbl.setText("—")
            return
        mdp   = roi.get('mdp')
        force = roi.get('force', {})
        if mdp:
            bpm = 60 / mdp.IBI_avg if mdp.IBI_avg > 0 else 0
            st  = float(np.nanmean(mdp.ST)) * 1000 if len(mdp.ST) else 0
            dt  = float(np.nanmean(mdp.DT)) * 1000 if len(mdp.DT) else 0
            self._metric_labels["HR"].setText(f"{bpm:.1f}")
            self._metric_labels["ST"].setText(f"{st:.0f}")
            self._metric_labels["DT"].setText(f"{dt:.0f}")
        fmag = force.get('contractility_mag', 0)
        fstd = float(np.nanstd(force['force_vals'])) if len(force.get('force_vals', [])) > 1 else 0
        self._metric_labels["Force"].setText(f"{fmag:.2f}")
        self._metric_labels["ForceStd"].setText(f"{fstd:.2f}")
        morph = roi.get('morphology', {})
        diam  = morph.get('equivalent_diameter_um', float('nan'))
        self._metric_labels["Diameter"].setText(f"{diam:.1f}" if diam == diam else "—")

    # ── Actions ──────────────────────────────────────────────────────────────

    def _recompute(self):
        if not self._data:
            return
        from PyQt6.QtWidgets import QApplication
        _t = _Toast("Recomputing…", self, kind="loading", duration=0)
        QApplication.processEvents()
        proj_root = str(Path(__file__).parent.parent.parent)
        if proj_root not in sys.path:
            sys.path.insert(0, proj_root)
        roi = self._current_roi()
        if roi is None:
            return
        k_mult   = self._k_slider.value() / 10.0
        min_dist = self._d_slider.value() * 0.05
        try:
            from cardio_py.core.mdp import calculate_mdp_metrics, select_dominant_signal
            from cardio_py.core.force import compute_contractility
            time   = roi['time']
            signal, axis = select_dominant_signal(roi['signal_x'], roi['signal_y'], time, k_mult, min_dist)
            mdp    = calculate_mdp_metrics(signal, time, k_mult, min_dist)
            force  = compute_contractility(roi['global_trace'], time, roi['frame_rate'], mdp.peak_locs)
            roi['dominant_axis'] = axis
            roi['signal']        = signal
            roi['mdp']           = mdp
            roi['force']         = force
            roi['k']             = k_mult
            roi['d']             = min_dist
            with open(self._pkl_path, 'wb') as f:
                pickle.dump(self._data, f)
            self._update_metrics()
            self._update_overlay()
            self._refresh_canvas()
            _t.deleteLater()
            _Toast(f"Recomputed  k={k_mult:.1f}  d={min_dist:.2f} s", self, kind="success")
        except Exception as e:
            _t.deleteLater()
            QMessageBox.critical(self, "Recompute error", str(e))

    def _delete_roi(self):
        if not self._data:
            return
        roi_list = self._data.get('roi_list', [])
        if not roi_list or self._roi_idx >= len(roi_list):
            return
        ans = QMessageBox.question(self, "Delete ROI",
            f"Delete ROI {roi_list[self._roi_idx]['roi_index']}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ans != QMessageBox.StandardButton.Yes:
            return
        roi_list.pop(self._roi_idx)
        for new_idx, roi in enumerate(roi_list, start=1):
            roi['roi_index'] = new_idx
        self._roi_idx = min(self._roi_idx, len(roi_list) - 1) if roi_list else 0
        with open(self._pkl_path, 'wb') as f:
            pickle.dump(self._data, f)
        self._populate_roi_combo()
        self._update_metrics()
        self._update_overlay()
        self._refresh_canvas()

    def _export_and_review(self):
        if not self._data:
            return
        roi_list  = self._data.get('roi_list', [])
        frame_rgb = self._data.get('frame_rgb')
        if not roi_list:
            QMessageBox.warning(self, "No ROIs", "No ROI data to export.")
            return

        self._export_toast = _Toast("Exporting…", self, kind="loading", duration=0)
        proj_root = str(Path(__file__).parent.parent.parent)

        self._export_worker = _ExportWorker(self._pkl_path, roi_list, frame_rgb, proj_root)
        self._export_worker.success.connect(self._on_export_done)
        self._export_worker.error.connect(self._on_export_error)
        self._export_worker.start()

    def _on_export_done(self, n):
        self._exported = True
        self._export_toast.deleteLater()
        _Toast(f"Saved {n} ROI(s) — Excel + summary images", self, kind="success")
        QTimer.singleShot(2400, self.accept)

    def _on_export_error(self, msg):
        self._export_toast.deleteLater()
        QMessageBox.critical(self, "Export error", msg)

    def closeEvent(self, event):
        if not self._exported:
            from PyQt6.QtWidgets import QMessageBox
            ans = QMessageBox.question(
                self, "Export not complete",
                "Results have not been exported yet.\nClose without exporting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        event.accept()
