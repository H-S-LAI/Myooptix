"""
Batch Compute dialog.
"""

import json
import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QButtonGroup, QRadioButton, QDoubleSpinBox, QProgressBar,
    QTextEdit, QFrame, QSizePolicy, QApplication, QWidget, QComboBox,
    QInputDialog, QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap

_PRESETS_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "presets.json")


def _load_presets():
    try:
        with open(_PRESETS_PATH) as f:
            return json.load(f)["presets"]
    except Exception:
        return [{"name": "TCY_4X", "scale": 2.915}, {"name": "TCY_10X", "scale": 1.175}]


def _save_presets(presets):
    try:
        with open(_PRESETS_PATH, "w") as f:
            json.dump({"presets": presets}, f, indent=2)
    except Exception:
        pass


def _spinrow(parent_lay, label, value, mn, mx, step, decimals, width=160):
    row = QHBoxLayout()
    lbl = QLabel(label)
    lbl.setFixedWidth(width)
    lbl.setStyleSheet("background: transparent;")
    spin = QDoubleSpinBox()
    spin.setRange(mn, mx)
    spin.setSingleStep(step)
    spin.setDecimals(decimals)
    spin.setValue(value)
    row.addWidget(lbl)
    row.addWidget(spin)
    parent_lay.addLayout(row)
    return spin


class ComputeDialog(QDialog):
    def __init__(self, video_paths, project_root, scale, k_mult, min_dist, parent=None):
        super().__init__(parent)
        self.video_paths  = video_paths
        self.project_root = project_root
        self._scale       = scale
        self._worker      = None
        self._preview_idx = 0

        self._presets = _load_presets()

        self.setWindowTitle("Batch Compute")
        self.setMinimumWidth(480)
        self._build_ui()
        self._load_settings()
        self.adjustSize()

    def _refresh_combo(self):
        self._combo_preset.blockSignals(True)
        self._combo_preset.clear()
        for p in self._presets:
            self._combo_preset.addItem(f"{p['name']}  ({p['scale']} µm/px)")
        self._combo_preset.blockSignals(False)

    def _settings_path(self):
        import os
        return os.path.join(self.project_root, "compute_settings.json")

    def _load_settings(self):
        p = self._settings_path()
        if not os.path.exists(p):
            return
        try:
            s = json.loads(open(p).read())
            if s.get("seg_method") == "otsu":
                self._rb_otsu.setChecked(True)
            else:
                self._rb_unet.setChecked(True)
            if "min_pct" in s:
                self._spin_min_pct.setValue(s["min_pct"])
            if "max_pct" in s:
                self._spin_max_pct.setValue(s["max_pct"])
            if "scale" in s:
                loaded = s["scale"]
                # try to match a preset
                matched = False
                for i, preset in enumerate(self._presets):
                    if abs(preset["scale"] - loaded) < 0.001:
                        self._combo_preset.setCurrentIndex(i)
                        matched = True
                        break
                if not matched:
                    self._spin_scale.blockSignals(True)
                    self._spin_scale.setValue(loaded)
                    self._spin_scale.blockSignals(False)
                    self._spin_scale.setEnabled(True)
                    self._combo_preset.blockSignals(True)
                    self._combo_preset.setCurrentIndex(-1)
                    self._combo_preset.blockSignals(False)
                    self._preset_hint.setVisible(True)
        except Exception:
            pass

    def _save_settings(self):
        import json
        s = {
            "seg_method": "unet" if self._rb_unet.isChecked() else "otsu",
            "min_pct":    self._spin_min_pct.value(),
            "max_pct":    self._spin_max_pct.value(),
            "scale":      self._spin_scale.value(),
        }
        try:
            with open(self._settings_path(), "w") as f:
                json.dump(s, f, indent=2)
        except Exception:
            pass

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(12)

        # Title
        title = QLabel(f"Batch Compute  —  {len(self.video_paths)} video(s)")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #3b3a32;")
        root.addWidget(title)
        root.addWidget(self._divider())

        # ── Segmentation method ──
        seg_lbl = QLabel("Segmentation method")
        seg_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #6b6456;")
        root.addWidget(seg_lbl)

        self._seg_group = QButtonGroup(self)
        self._rb_otsu = QRadioButton("Auto — Otsu")
        self._rb_unet = QRadioButton("Auto — U-Net (deep learning)")
        self._rb_unet.setChecked(True)
        self._seg_group.addButton(self._rb_otsu, 0)
        self._seg_group.addButton(self._rb_unet, 1)

        radio_row = QHBoxLayout()
        rb_col = QVBoxLayout()
        rb_col.setSpacing(4)
        rb_col.addWidget(self._rb_otsu)
        rb_col.addWidget(self._rb_unet)
        radio_row.addLayout(rb_col)
        radio_row.addStretch()
        self._preview_btn = QPushButton("Preview")
        self._preview_btn.setFixedSize(110, 30)
        self._preview_btn.setCheckable(True)
        self._preview_btn.toggled.connect(self._toggle_preview)
        radio_row.addWidget(self._preview_btn, alignment=Qt.AlignmentFlag.AlignTop)
        root.addLayout(radio_row)

        # Preview body (hidden by default)
        self._preview_body = QWidget()
        pb_lay = QVBoxLayout(self._preview_body)
        pb_lay.setContentsMargins(0, 4, 0, 0)
        pb_lay.setSpacing(6)

        # nav row
        nav_row = QHBoxLayout()
        self._prev_frame_btn = QPushButton("◀")
        self._prev_frame_btn.setFixedWidth(32)
        self._prev_frame_btn.clicked.connect(lambda: self._step_preview(-1))
        self._next_frame_btn = QPushButton("▶")
        self._next_frame_btn.setFixedWidth(32)
        self._next_frame_btn.clicked.connect(lambda: self._step_preview(+1))
        self._preview_name_lbl = QLabel("")
        self._preview_name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_name_lbl.setStyleSheet("font-size: 11px; color: #6b6456;")
        nav_row.addWidget(self._prev_frame_btn)
        nav_row.addWidget(self._preview_name_lbl)
        nav_row.addWidget(self._next_frame_btn)
        pb_lay.addLayout(nav_row)

        # area filter (inside preview)
        area_toggle = QPushButton("▶  Area filter  (% of pixels)  —  0.15% ~ 50%")
        area_toggle.setCheckable(True)
        area_toggle.setStyleSheet(
            "QPushButton { text-align: left; padding: 4px 8px; background: #ede8de;"
            "border: 1px solid #d6cfc2; border-radius: 4px; font-size: 11px; color: #6b6456; }"
            "QPushButton:checked { background: #e0d9cc; }"
        )
        self._area_body = QWidget()
        area_body_lay = QVBoxLayout(self._area_body)
        area_body_lay.setContentsMargins(8, 2, 8, 2)
        self._spin_min_pct = _spinrow(area_body_lay, "Min area (%)", 0.15, 0.01, 20.0, 0.05, 2)
        self._spin_max_pct = _spinrow(area_body_lay, "Max area (%)", 50.0, 1.0, 99.0, 1.0, 1)
        self._area_body.setVisible(False)

        def _toggle_area(checked):
            self._area_body.setVisible(checked)
            t = area_toggle.text()
            area_toggle.setText(("▼" if checked else "▶") + t[1:])
            self.adjustSize()

        area_toggle.toggled.connect(_toggle_area)
        pb_lay.addWidget(area_toggle)
        pb_lay.addWidget(self._area_body)

        # image label
        self._preview_lbl = QLabel()
        self._preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_lbl.setStyleSheet(
            "background: #f0ebe0; border: 1px solid #d6cfc2; border-radius: 4px;")
        self._preview_lbl.setMinimumHeight(180)
        pb_lay.addWidget(self._preview_lbl)

        self._preview_body.setVisible(False)
        root.addWidget(self._preview_body)

        root.addWidget(self._divider())

        # ── Scale / Preset ──
        scale_lbl = QLabel("Analysis parameters")
        scale_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #6b6456;")
        root.addWidget(scale_lbl)

        # Row 1: preset combo
        preset_row = QHBoxLayout()
        preset_lbl = QLabel("Microscope preset")
        preset_lbl.setFixedWidth(160)
        self._combo_preset = QComboBox()
        preset_row.addWidget(preset_lbl)
        preset_row.addWidget(self._combo_preset, 1)
        root.addLayout(preset_row)

        # Row 2: scale spinbox + save button inline
        scale_row = QHBoxLayout()
        lbl = QLabel("Scale (µm/pixel)")
        lbl.setFixedWidth(160)
        self._spin_scale = QDoubleSpinBox()
        self._spin_scale.setRange(0.001, 100.0)
        self._spin_scale.setSingleStep(0.001)
        self._spin_scale.setDecimals(6)
        self._spin_scale.setValue(self._scale)
        self._add_preset_btn = QPushButton("+ Save")
        self._add_preset_btn.setToolTip("Save current scale as a new preset")
        self._add_preset_btn.setFixedSize(72, 28)
        scale_row.addWidget(lbl)
        scale_row.addWidget(self._spin_scale, 1)
        scale_row.addSpacing(6)
        scale_row.addWidget(self._add_preset_btn)
        root.addLayout(scale_row)

        # hint label
        self._preset_hint = QLabel("Unsaved — press Save preset to keep this value")
        self._preset_hint.setStyleSheet("font-size: 10px; color: #9a9080; padding-left: 164px;")
        self._preset_hint.setVisible(False)
        root.addWidget(self._preset_hint)

        self._refresh_combo()

        def _on_preset(idx):
            if idx < 0 or idx >= len(self._presets):
                return
            val = self._presets[idx]["scale"]
            self._spin_scale.blockSignals(True)
            self._spin_scale.setValue(val)
            self._spin_scale.blockSignals(False)
            self._preset_hint.setVisible(False)

        def _on_scale_edited():
            self._combo_preset.blockSignals(True)
            self._combo_preset.setCurrentIndex(-1)
            self._combo_preset.blockSignals(False)
            self._preset_hint.setVisible(True)

        self._combo_preset.currentIndexChanged.connect(_on_preset)
        self._spin_scale.valueChanged.connect(_on_scale_edited)

        def _add_preset():
            val = self._spin_scale.value()
            name, ok = QInputDialog.getText(
                self, "Save Preset", "Preset name:", text=f"Custom_{val:.3f}")
            if not ok or not name.strip():
                return
            name = name.strip()
            # replace if same name exists
            self._presets = [p for p in self._presets if p["name"] != name]
            self._presets.append({"name": name, "scale": val})
            _save_presets(self._presets)
            self._refresh_combo()
            # select newly added
            for i, p in enumerate(self._presets):
                if p["name"] == name:
                    self._combo_preset.setCurrentIndex(i)
                    break

        self._add_preset_btn.clicked.connect(_add_preset)

        # init: select TCY_4X by default (index 0)
        self._combo_preset.setCurrentIndex(0)
        _on_preset(0)

        root.addWidget(self._divider())

        # ── Progress ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(self.video_paths))
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        root.addWidget(self.progress_bar)

        self.status_lbl = QLabel("Ready.")
        self.status_lbl.setStyleSheet("font-size: 11px; color: #6b6456;")
        root.addWidget(self.status_lbl)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(100)
        self.log.setStyleSheet(
            "background: #faf7f2; border: 1px solid #d6cfc2; border-radius: 4px;"
            "font-family: monospace; font-size: 11px;")
        root.addWidget(self.log)

        # result overlay image
        self._result_lbl = QLabel()
        self._result_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_lbl.setStyleSheet(
            "background: #f0ebe0; border: 1px solid #d6cfc2; border-radius: 4px;")
        self._result_lbl.setVisible(False)
        root.addWidget(self._result_lbl)

        root.addWidget(self._divider())

        # ── Buttons ──
        btn_row = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._cancel)
        self.run_btn = QPushButton("▶  Run")
        self.run_btn.setProperty("primary", True)
        self.run_btn.style().unpolish(self.run_btn)
        self.run_btn.style().polish(self.run_btn)
        self.run_btn.setFixedHeight(34)
        self.run_btn.clicked.connect(self._run)
        btn_row.addStretch()
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.run_btn)
        root.addLayout(btn_row)

    def _divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #d6cfc2;")
        return line

    # ── Preview ─────────────────────────────────────────────────────────────

    def _toggle_preview(self, checked: bool):
        self._preview_body.setVisible(checked)
        self._preview_btn.setText("Hide preview" if checked else "Preview")
        if checked:
            self._run_preview(self._preview_idx)
        else:
            self._preview_lbl.clear()
            self._preview_lbl.setMinimumHeight(0)
            self._preview_lbl.setFixedHeight(0)
        self.adjustSize()

    def _step_preview(self, delta: int):
        self._preview_idx = (self._preview_idx + delta) % len(self.video_paths)
        self._run_preview(self._preview_idx)

    def _run_preview(self, idx: int):
        import sys, cv2, numpy as np
        proj_root = str(__import__('pathlib').Path(__file__).parent.parent.parent)
        if proj_root not in sys.path:
            sys.path.insert(0, proj_root)

        vp = self.video_paths[idx]
        from pathlib import Path as _P
        self._preview_name_lbl.setText(f"{idx+1} / {len(self.video_paths)}  —  {_P(vp).name}")
        self._preview_lbl.setText("Running segmentation…")
        self._preview_lbl.setMinimumHeight(180)
        QApplication.processEvents()

        try:
            from cardio_py.core.io import read_first_frame
            frame, _ = read_first_frame(vp)

            min_pct = self._spin_min_pct.value()
            max_pct = self._spin_max_pct.value()
            if self._rb_unet.isChecked():
                from cardio_py.core.segmentation import segment_unet
                masks, n = segment_unet(frame, min_pct=min_pct, max_pct=max_pct)
            else:
                from cardio_py.core.segmentation import segment_otsu
                masks, n = segment_otsu(frame, min_pct=min_pct, max_pct=max_pct)

            if n == 0:
                self._preview_lbl.setText(
                    f"No ROIs found  (min={min_pct:.2f}%  max={max_pct:.1f}%)\nTry adjusting the area filter.")
                return

            overlay = frame.copy()
            colors = [(255, 80, 80), (80, 200, 80), (80, 120, 255), (200, 200, 60)]
            for i, mask in enumerate(masks):
                rows_ = np.any(mask, axis=1)
                cols_ = np.any(mask, axis=0)
                if not rows_.any():
                    continue
                rmin, rmax = np.where(rows_)[0][[0, -1]]
                cmin, cmax = np.where(cols_)[0][[0, -1]]
                c = colors[i % len(colors)]
                cv2.rectangle(overlay, (cmin, rmin), (cmax, rmax), (c[2], c[1], c[0]), 3)
                cv2.putText(overlay, f"ROI {i+1}", (cmin, max(rmin - 10, 20)),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (c[2], c[1], c[0]), 2)

            h, w = overlay.shape[:2]
            max_w = self._preview_lbl.width() or 480
            scale = max_w / w
            nh, nw = int(h * scale), int(w * scale)
            overlay_resized = cv2.resize(overlay, (nw, nh))
            img = QImage(overlay_resized.data, nw, nh, nw * 3, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(img)
            self._preview_lbl.setPixmap(pixmap)
            self._preview_lbl.setMinimumHeight(nh)
            self._preview_lbl.setFixedHeight(nh)
            self.adjustSize()

        except Exception as e:
            self._preview_lbl.setText(f"Error: {e}")

    # ── Run ──────────────────────────────────────────────────────────────────

    def _run(self):
        from .worker_compute import ComputeWorker
        self._save_settings()
        seg_method = "unet" if self._rb_unet.isChecked() else "otsu"
        self._worker = ComputeWorker(
            video_paths=self.video_paths,
            project_root=self.project_root,
            seg_method=seg_method,
            scale=self._spin_scale.value(),
            k_mult=1.0,
            min_dist=0.2,
            otsu_min_pct=self._spin_min_pct.value(),
            otsu_max_pct=self._spin_max_pct.value(),
            parent=self,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.stage.connect(self._on_stage)
        self._worker.video_done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_finished)
        self.run_btn.setEnabled(False)
        self._worker.start()

    def _on_progress(self, current, total, stem):
        self.progress_bar.setValue(current)
        if current < total:
            self.status_lbl.setText(f"({current+1}/{total})  {stem}  —  starting…")

    def _on_stage(self, stem, msg):
        self.status_lbl.setText(f"{stem}  —  {msg}")

    def _on_done(self, stem, n_rois, bpm, overlay_bytes, ow, oh):
        self.log.append(f"✓  {stem}  —  {n_rois} ROI(s)  |  BPM ≈ {bpm:.1f}")
        if overlay_bytes and ow > 0 and oh > 0:
            import numpy as np, cv2
            arr = np.frombuffer(overlay_bytes, dtype=np.uint8).reshape(oh, ow, 3)
            arr = arr.copy()
            cv2.putText(arr, stem, (12, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 3)
            cv2.putText(arr, stem, (12, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (40, 40, 40), 1)
            img = QImage(arr.tobytes(), ow, oh, ow * 3, QImage.Format.Format_RGB888)
            max_w = self.width() - 56
            max_h = 200
            scale_w = max_w / ow
            scale_h = max_h / oh
            scale = min(scale_w, scale_h)
            nw, nh = int(ow * scale), int(oh * scale)
            pix = QPixmap.fromImage(img).scaled(nw, nh, Qt.AspectRatioMode.KeepAspectRatio,
                                                Qt.TransformationMode.SmoothTransformation)
            self._result_lbl.setPixmap(pix)
            self._result_lbl.setFixedHeight(nh)
            self._result_lbl.setVisible(True)
            self.adjustSize()

    def _on_error(self, stem, msg):
        self.log.append(f"✗  {stem}  —  {msg}")

    def _on_finished(self):
        self.status_lbl.setText("All done.")
        self.run_btn.setText("Close")
        self.run_btn.setEnabled(True)
        self.run_btn.clicked.disconnect()
        self.run_btn.clicked.connect(self.accept)
        self.cancel_btn.setEnabled(False)

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
