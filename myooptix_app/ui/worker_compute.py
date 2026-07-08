"""
Background worker for batch video compute.
"""

import sys
import pickle
import numpy as np
import cv2
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

PKL_DIR = "_pkl_for_review"


def _get_pkl_path(video_path: str, project_root: str) -> str:
    p = Path(video_path)
    pkl_dir = Path(project_root) / PKL_DIR
    pkl_dir.mkdir(exist_ok=True)
    return str(pkl_dir / f"{p.parent.name}_{p.stem}.pkl")


def _compute_one(video_path, masks, scale_um_per_px, k_mult, min_dist, stage_cb=None):
    proj_root = str(Path(__file__).parent.parent.parent)
    if proj_root not in sys.path:
        sys.path.insert(0, proj_root)

    from cardio_py.core.tracking import track_video
    from cardio_py.core.mdp import calculate_mdp_metrics, select_dominant_signal
    from cardio_py.core.force import compute_contractility
    from cardio_py.core.morphology import compute_mask_morphology

    if stage_cb:
        stage_cb("KLT tracking…")
    results = track_video(video_path, masks, scale_um_per_px=scale_um_per_px)

    roi_list = []
    for i, r in enumerate(results):
        if stage_cb:
            stage_cb(f"MDP analysis — ROI {i+1}…")
        signal, axis = select_dominant_signal(r.signal_x, r.signal_y, r.time, k_mult, min_dist)
        mdp    = calculate_mdp_metrics(signal, r.time, k_mult, min_dist)
        force  = compute_contractility(r.signal_mag, r.time, r.frame_rate, mdp.peak_locs)
        morph  = compute_mask_morphology(masks[i], scale_um_per_px)
        roi_list.append({
            'roi_index':     i + 1,
            'dominant_axis': axis,
            'signal_x':      r.signal_x,
            'signal_y':      r.signal_y,
            'signal':        signal,
            'global_trace':  force['global_trace'],
            'time':          r.time,
            'frame_rate':    r.frame_rate,
            'mdp':            mdp,
            'force':          force,
            'mask':           masks[i],
            'morphology':     morph,
            'k':              k_mult,
            'd':              min_dist,
        })

    cap = cv2.VideoCapture(video_path)
    _, f = cap.read()
    cap.release()
    frame_rgb = cv2.cvtColor(f, cv2.COLOR_BGR2RGB) if f is not None else None

    return {
        'video_path': video_path,
        'frame_rgb':  frame_rgb,
        'roi_list':   roi_list,
        'params': {
            'k_mult':          k_mult,
            'min_dist':        min_dist,
            'scale_um_per_px': scale_um_per_px,
        },
        'status': 'Computed',
    }


class ComputeWorker(QThread):
    """
    Signals:
        progress(current, total, stem)        — video index update
        stage(stem, msg)                      — fine-grained stage info
        video_done(stem, n_rois, bpm, overlay_bytes, w, h)
        error(stem, msg)
        finished()
    """
    progress   = pyqtSignal(int, int, str)
    stage      = pyqtSignal(str, str)
    video_done = pyqtSignal(str, int, float, bytes, int, int)
    error      = pyqtSignal(str, str)
    finished   = pyqtSignal()

    def __init__(self, video_paths, project_root, seg_method,
                 scale, k_mult, min_dist,
                 otsu_min_pct=0.15, otsu_max_pct=50.0, parent=None):
        super().__init__(parent)
        self.video_paths  = video_paths
        self.project_root = project_root
        self.seg_method   = seg_method
        self.scale        = scale
        self.k_mult       = k_mult
        self.min_dist     = min_dist
        self.otsu_min_pct = otsu_min_pct
        self.otsu_max_pct = otsu_max_pct
        self._abort       = False

    def abort(self):
        self._abort = True

    def run(self):
        proj_root = str(Path(__file__).parent.parent.parent)
        if proj_root not in sys.path:
            sys.path.insert(0, proj_root)

        total = len(self.video_paths)
        for idx, vp in enumerate(self.video_paths):
            if self._abort:
                break

            p    = Path(vp)
            stem = f"{p.parent.name}_{p.stem}"
            self.progress.emit(idx, total, stem)

            try:
                self.stage.emit(stem, "Segmentation…")
                masks, frame_rgb = self._get_masks(vp)
                if not masks:
                    raise RuntimeError("No ROIs found")

                def _cb(msg):
                    self.stage.emit(stem, msg)

                data = _compute_one(vp, masks, self.scale, self.k_mult, self.min_dist,
                                    stage_cb=_cb)

                pkl_path = _get_pkl_path(vp, self.project_root)
                with open(pkl_path, 'wb') as f:
                    pickle.dump(data, f)

                rois = data['roi_list']
                bpm  = 0.0
                if rois:
                    m = rois[0]['mdp']
                    bpm = 60 / m.IBI_avg if m.IBI_avg > 0 else 0.0

                # build overlay image
                overlay_bytes = b""
                ow, oh = 0, 0
                if frame_rgb is not None:
                    overlay = frame_rgb.copy()
                    colors = [(255,80,80),(80,200,80),(80,120,255),(200,200,60)]
                    for i, roi in enumerate(rois):
                        mask = roi.get('mask')
                        if mask is None:
                            continue
                        rows_ = np.any(mask, axis=1)
                        cols_ = np.any(mask, axis=0)
                        if not rows_.any():
                            continue
                        rmin, rmax = np.where(rows_)[0][[0,-1]]
                        cmin, cmax = np.where(cols_)[0][[0,-1]]
                        c = colors[i % len(colors)]
                        cv2.rectangle(overlay, (cmin,rmin),(cmax,rmax),(c[2],c[1],c[0]),3)
                        cv2.putText(overlay, f"ROI {roi['roi_index']}",
                                    (cmin, max(rmin-10,20)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (c[2],c[1],c[0]), 2)
                    oh, ow = overlay.shape[:2]
                    overlay_bytes = overlay.tobytes()

                self.video_done.emit(stem, len(rois), bpm, overlay_bytes, ow, oh)

            except Exception as e:
                self.error.emit(stem, str(e))

        self.progress.emit(total, total, "Done")
        self.finished.emit()

    def _get_masks(self, vp: str):
        from cardio_py.core.io import read_first_frame
        frame, _ = read_first_frame(vp)

        if self.seg_method == "unet":
            from cardio_py.core.segmentation import segment_unet
            masks, _ = segment_unet(frame, min_pct=self.otsu_min_pct, max_pct=self.otsu_max_pct)
        else:
            from cardio_py.core.segmentation import segment_otsu
            masks, _ = segment_otsu(frame, min_pct=self.otsu_min_pct, max_pct=self.otsu_max_pct)

        return masks, frame
