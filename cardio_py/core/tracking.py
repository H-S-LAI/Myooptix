"""
KLT Feature Tracking
=====================
Tracks cardiac organoid motion across video frames using the
Kanade-Lucas-Tomasi (KLT) optical flow algorithm.

Ported from computeMyocardium_v1.m / runManualAnalysis_v1.m

Output signals are in µm/s (converted from pixels/frame via scale_um_per_px
and frame_rate).
"""

import numpy as np
import cv2
from dataclasses import dataclass, field


# Default KLT parameters matching MATLAB vision.PointTracker
_LK_PARAMS = dict(
    winSize=(21, 21),
    maxLevel=3,
    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
)

_FEATURE_PARAMS = dict(
    maxCorners=500,
    qualityLevel=0.01,
    minDistance=5,
    blockSize=3,
)


@dataclass
class TrackingResult:
    """Per-ROI KLT tracking output."""
    signal_x: np.ndarray = field(default_factory=lambda: np.array([]))  # µm/s
    signal_y: np.ndarray = field(default_factory=lambda: np.array([]))  # µm/s
    signal_mag: np.ndarray = field(default_factory=lambda: np.array([]))  # µm/s
    time: np.ndarray = field(default_factory=lambda: np.array([]))       # s
    frame_rate: float = 0.0
    n_frames: int = 0
    n_features: int = 0


def _dilate_mask(mask: np.ndarray, dilation_ratio: float = 0.10) -> np.ndarray:
    """
    Dilate a binary ROI mask by ~10% of its equivalent radius.
    Matches MATLAB: se = strel('disk', ceil(radius * 0.10))
    """
    props = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    area = props[2][1, cv2.CC_STAT_AREA] if props[0] > 1 else mask.sum()
    radius = np.sqrt(area / np.pi)
    dilation_r = max(1, int(np.ceil(radius * dilation_ratio)))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * dilation_r + 1, 2 * dilation_r + 1))
    return cv2.dilate(mask.astype(np.uint8), kernel).astype(bool)


def track_video(
    video_path: str,
    roi_masks: list[np.ndarray],
    scale_um_per_px: float,
    max_bidirectional_error: float = 2.0,
) -> list[TrackingResult]:
    """
    Run KLT tracking on a video for a list of ROI binary masks.

    Parameters
    ----------
    video_path             : path to .mov/.mp4/.avi
    roi_masks              : list of boolean masks, one per ROI, shape (H, W)
    scale_um_per_px        : µm per pixel (from microscope calibration)
    max_bidirectional_error: max forward-backward tracking error (pixels)

    Returns
    -------
    List of TrackingResult, one per ROI
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Cannot open video: {video_path}")

    frame_rate = cap.get(cv2.CAP_PROP_FPS)
    n_rois = len(roi_masks)

    # Read first frame
    ret, frame0 = cap.read()
    if not ret:
        raise IOError("Cannot read first frame")
    gray0 = cv2.cvtColor(frame0, cv2.COLOR_BGR2GRAY)

    # Build dilated masks and combined label map
    dilated = [_dilate_mask(m) for m in roi_masks]
    label_map = np.zeros(gray0.shape, dtype=np.int32)
    for i, d in enumerate(dilated):
        label_map[d] = i + 1   # 1-indexed, 0 = background

    # Detect features on masked first frame
    masked0 = gray0.copy()
    masked0[label_map == 0] = 0
    pts0 = cv2.goodFeaturesToTrack(masked0, **_FEATURE_PARAMS)

    if pts0 is None:
        cap.release()
        return [TrackingResult(frame_rate=frame_rate) for _ in range(n_rois)]

    pts0 = pts0.reshape(-1, 2)

    # Assign each feature to a ROI
    pt_ids = np.array([
        label_map[min(int(round(y)), gray0.shape[0] - 1),
                  min(int(round(x)), gray0.shape[1] - 1)]
        for x, y in pts0
    ])
    valid = pt_ids > 0
    pts0 = pts0[valid]
    pt_ids = pt_ids[valid]

    n_features = len(pts0)

    # Storage: (n_rois,) lists of per-frame values
    klt_x   = [[] for _ in range(n_rois)]
    klt_y   = [[] for _ in range(n_rois)]
    klt_mag = [[] for _ in range(n_rois)]

    prev_pts = pts0.copy().astype(np.float32).reshape(-1, 1, 2)
    prev_gray = gray0.copy()

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Forward tracking
        next_pts, status_fwd, _ = cv2.calcOpticalFlowPyrLK(
            prev_gray, gray, prev_pts, None, **_LK_PARAMS
        )

        # Backward tracking (bidirectional error check)
        back_pts, status_bwd, _ = cv2.calcOpticalFlowPyrLK(
            gray, prev_gray, next_pts, None, **_LK_PARAMS
        )

        # A point is valid if both forward and backward tracking succeed
        # and the round-trip error is within threshold
        fwd_ok = status_fwd.ravel().astype(bool)
        bwd_ok = status_bwd.ravel().astype(bool)
        back_err = np.linalg.norm(
            (prev_pts.reshape(-1, 2) - back_pts.reshape(-1, 2)), axis=1
        )
        is_found = fwd_ok & bwd_ok & (back_err < max_bidirectional_error)

        curr_pts = next_pts.reshape(-1, 2)
        prev_flat = prev_pts.reshape(-1, 2)

        dx = curr_pts[:, 0] - prev_flat[:, 0]
        dy = curr_pts[:, 1] - prev_flat[:, 1]
        d_mag = np.sqrt(dx ** 2 + dy ** 2)

        for i in range(n_rois):
            in_roi = (pt_ids == i + 1) & is_found
            if in_roi.any():
                klt_x[i].append(float(dx[in_roi].mean()))
                klt_y[i].append(float(dy[in_roi].mean()))
                klt_mag[i].append(float(d_mag[in_roi].mean()))
            else:
                klt_x[i].append(0.0)
                klt_y[i].append(0.0)
                klt_mag[i].append(0.0)

        prev_pts = next_pts
        prev_gray = gray

    cap.release()

    n_frames = len(klt_x[0])
    time_vec = np.arange(1, n_frames + 1) / frame_rate

    results = []
    for i in range(n_rois):
        x_arr   = np.array(klt_x[i],   dtype=float)
        y_arr   = np.array(klt_y[i],   dtype=float)
        mag_arr = np.array(klt_mag[i], dtype=float)

        # Convert pixels/frame → µm/s
        sig_x   = x_arr   * frame_rate * scale_um_per_px
        sig_y   = y_arr   * frame_rate * scale_um_per_px
        sig_mag = mag_arr * frame_rate * scale_um_per_px

        results.append(TrackingResult(
            signal_x=sig_x,
            signal_y=sig_y,
            signal_mag=sig_mag,
            time=time_vec,
            frame_rate=frame_rate,
            n_frames=n_frames,
            n_features=n_features,
        ))

    return results
