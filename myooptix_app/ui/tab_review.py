import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QSlider, QSplitter, QSizePolicy,
)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


def _mock_signal(hr=60, duration=5.0, fs=100.0):
    t = np.linspace(0, duration, int(duration * fs))
    period = 60.0 / hr
    sig = np.zeros_like(t)
    for beat_t in np.arange(0, duration, period):
        sig += np.exp(-((t - beat_t) ** 2) / (2 * 0.02**2))
    sig -= sig.min()
    sig /= sig.max() + 1e-9
    return t, sig


class WaveformCanvas(FigureCanvas):
    def __init__(self):
        self.fig = Figure(facecolor="#181825", tight_layout=True)
        super().__init__(self.fig)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._draw_mock()

    def _draw_mock(self):
        self.fig.clear()
        axes_specs = [
            ("Displacement (X)", "#89b4fa"),
            ("Displacement (Y)", "#a6e3a1"),
            ("Magnitude",        "#f9e2af"),
            ("Force",            "#f38ba8"),
        ]
        n = len(axes_specs)
        for i, (title, color) in enumerate(axes_specs):
            ax = self.fig.add_subplot(n, 1, i + 1)
            t, sig = _mock_signal(hr=60 + i * 3)
            ax.plot(t, sig, color=color, linewidth=1.2)
            ax.set_facecolor("#1e1e2e")
            ax.set_ylabel(title, color="#6c7086", fontsize=8)
            ax.tick_params(colors="#6c7086", labelsize=7)
            for spine in ax.spines.values():
                spine.set_edgecolor("#313244")
            if i < n - 1:
                ax.set_xticklabels([])
        self.fig.axes[-1].set_xlabel("Time (s)", color="#6c7086", fontsize=8)
        self.draw()


class ReviewTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left panel: controls ──
        left = QWidget()
        left.setFixedWidth(260)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(16, 16, 8, 16)
        lv.setSpacing(12)

        # ROI selector
        roi_box = QGroupBox("ROI")
        rb = QVBoxLayout(roi_box)
        self.roi_combo = QComboBox()
        self.roi_combo.addItems(["ROI 1 — X axis", "ROI 1 — Y axis", "ROI 2 — X axis"])
        rb.addWidget(self.roi_combo)
        nav_row = QHBoxLayout()
        self.prev_btn = QPushButton("◀ Prev")
        self.next_btn = QPushButton("Next ▶")
        nav_row.addWidget(self.prev_btn)
        nav_row.addWidget(self.next_btn)
        rb.addLayout(nav_row)
        lv.addWidget(roi_box)

        # Metrics
        metrics_box = QGroupBox("Beat Metrics")
        mb = QVBoxLayout(metrics_box)
        for label, value in [
            ("HR (BPM)", "62"),
            ("ST (ms)",  "145"),
            ("DT (ms)",  "312"),
            ("IBI (ms)", "967"),
            ("Force (µN)", "0.84"),
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            val_lbl = QLabel(value)
            val_lbl.setStyleSheet("color: #89b4fa; font-weight: bold;")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(val_lbl)
            mb.addLayout(row)
        lv.addWidget(metrics_box)

        # Parameters
        param_box = QGroupBox("Parameters")
        pb = QVBoxLayout(param_box)
        for pname, lo, hi, val in [("K mult", 0, 30, 10), ("Min dist (s×10)", 1, 10, 2)]:
            pb.addWidget(QLabel(pname))
            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(lo, hi)
            sl.setValue(val)
            pb.addWidget(sl)
        lv.addWidget(param_box)

        lv.addStretch()

        # Action buttons
        self.delete_btn = QPushButton("🗑  Delete ROI")
        self.delete_btn.setProperty("danger", True)
        self.delete_btn.style().unpolish(self.delete_btn)
        self.delete_btn.style().polish(self.delete_btn)
        self.export_btn = QPushButton("⬇  Export Excel")
        self.export_btn.setProperty("primary", True)
        self.export_btn.style().unpolish(self.export_btn)
        self.export_btn.style().polish(self.export_btn)
        self.mark_btn = QPushButton("✓  Mark Reviewed")
        for b in (self.delete_btn, self.export_btn, self.mark_btn):
            b.setFixedHeight(34)
            lv.addWidget(b)

        # ── Right panel: waveform ──
        self.canvas = WaveformCanvas()

        splitter.addWidget(left)
        splitter.addWidget(self.canvas)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter)
