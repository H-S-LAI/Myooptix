"""
MDP (Motion Detection Peak) Algorithm
======================================
Core signal analysis for cardiac organoid contractility.
Ported from computeMyocardium_v1.m / reviewMyocardium_v1.m

Metrics extracted per beat:
  - CS  : Contraction Start  (velocity crosses 5% of peak, going up)
  - CE  : Contraction End    (velocity crosses zero, going down)
  - RE  : Relaxation End     (velocity crosses 5% of trough, going up)
  - ST  : Systolic Time      = CE - CS
  - DT  : Diastolic Time     = RE - CE
  - IBI : Inter-Beat Interval (time between consecutive CS events)
"""

import numpy as np
from scipy.signal import find_peaks
from dataclasses import dataclass, field


@dataclass
class BeatMetrics:
    """Results for a single ROI signal."""
    HR: int = 0
    IBI_avg: float = float("nan")
    is_flipped: bool = False
    peak_locs: np.ndarray = field(default_factory=lambda: np.array([]))
    peaks: np.ndarray = field(default_factory=lambda: np.array([]))
    CS: np.ndarray = field(default_factory=lambda: np.array([]))
    CE: np.ndarray = field(default_factory=lambda: np.array([]))
    RE: np.ndarray = field(default_factory=lambda: np.array([]))
    ST: np.ndarray = field(default_factory=lambda: np.array([]))
    DT: np.ndarray = field(default_factory=lambda: np.array([]))
    Interbeat: np.ndarray = field(default_factory=lambda: np.array([]))
    signal_display: np.ndarray = field(default_factory=lambda: np.array([]))  # flip-corrected signal for plotting


def morphology_flip_test(
    time: np.ndarray,
    velocity: np.ndarray,
    min_height: float,
    min_distance_sec: float,
) -> tuple[bool, np.ndarray]:
    """
    Detect whether the waveform is inverted and flip it if needed.
    Returns (is_flipped, corrected_velocity).

    Logic: a contraction waveform should have positive peak flanked by
    negative troughs on both sides. If the left trough is closer than
    the right, the signal is upside-down.
    """
    dt = time[1] - time[0]
    min_dist_samples = max(1, int(min_distance_sec / dt))

    if min_height <= 0:
        min_height = max(0.1 * np.std(velocity), 1e-3)

    pos_idx, _ = find_peaks(velocity, height=min_height, distance=min_dist_samples)
    neg_idx, _ = find_peaks(-velocity, height=min_height, distance=min_dist_samples)

    is_flipped = False

    if len(pos_idx) == 0 or len(neg_idx) < 2:
        # Fallback: compare absolute min vs max in the interior of the signal
        interior_mask = (time > 1.0) & (time < time[-1] - 1.0)
        v_sub = velocity[interior_mask] if interior_mask.any() else velocity
        if abs(v_sub.min()) > v_sub.max():
            is_flipped = True
    else:
        # Find the positive peak nearest to the temporal midpoint
        t_mid = (time[0] + time[-1]) / 2.0
        t_pos = time[pos_idx]
        t_neg = time[neg_idx]
        closest_pos = t_pos[np.argmin(np.abs(t_pos - t_mid))]

        neg_left = t_neg[t_neg < closest_pos]
        neg_right = t_neg[t_neg > closest_pos]

        if len(neg_left) > 0 and len(neg_right) > 0:
            dist_left = closest_pos - neg_left.max()
            dist_right = neg_right.min() - closest_pos
            if dist_left <= dist_right:
                is_flipped = True

    return is_flipped, (-velocity if is_flipped else velocity)


def _interp_crossing_time(
    time: np.ndarray, velocity: np.ndarray, idx1: int, idx2: int, target: float
) -> float:
    """Sub-sample interpolation to find exact crossing time."""
    t1, v1 = time[idx1], velocity[idx1]
    t2, v2 = time[idx2], velocity[idx2]
    if v2 == v1:
        return t1
    frac = (target - v1) / (v2 - v1)
    return t1 + frac * (t2 - t1)


def _find_zero_crossings(
    time: np.ndarray, velocity: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """
    Returns (crossing_times, crossing_types) where:
      type 1 = negative-to-positive (rising through zero)
      type 2 = positive-to-negative (falling through zero)
    """
    sign_v = np.sign(velocity)
    sign_v[sign_v == 0] = -1
    diff_sign = np.diff(sign_v)
    indices = np.sort(
        np.concatenate([np.where(diff_sign > 0)[0], np.where(diff_sign < 0)[0]])
    )

    if len(indices) == 0:
        return np.array([]), np.array([])

    zc_times = np.zeros(len(indices))
    zc_types = np.zeros(len(indices), dtype=int)

    for i, idx in enumerate(indices):
        t1, v1 = time[idx], velocity[idx]
        t2, v2 = time[idx + 1], velocity[idx + 1]
        zc_times[i] = t1 - v1 * (t2 - t1) / (v2 - v1)
        zc_types[i] = 1 if v1 < 0 else 2

    return zc_times, zc_types


def _dynamic_pairing(
    peak_locs: np.ndarray,
    zc_times: np.ndarray,
    zc_types: np.ndarray,
    time: np.ndarray,
    velocity: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    For each peak, find CS, CE, RE via sub-sample interpolation.

    CS: scan backward from peak until velocity <= 5% of peak (or <= 0)
    CE: next falling-through-zero crossing after the peak
    RE: scan forward from valley until velocity >= 5% of trough (or >= 0)
    """
    n = len(peak_locs)
    t_end = time[-1]
    t_CS = np.full(n, np.nan)
    t_CE = np.full(n, np.nan)
    t_RE = np.full(n, np.nan)

    # Pre-extract falling zero-crossings (type 2) for CE detection
    zc2_times = zc_times[zc_types == 2] if len(zc_times) > 0 else np.array([])

    for i, p_t in enumerate(peak_locs):
        idx_p = np.argmin(np.abs(time - p_t))
        peak_val = velocity[idx_p]
        target_h = 0.05 * peak_val

        # --- CS: scan backward ---
        found_cs = False
        for k in range(idx_p, -1, -1):
            v_curr = velocity[k]
            if v_curr <= target_h:
                t_CS[i] = _interp_crossing_time(time, velocity, k, min(k + 1, len(time) - 1), target_h)
                found_cs = True
                break
            if v_curr <= 0:
                t_CS[i] = _interp_crossing_time(time, velocity, k, min(k + 1, len(time) - 1), 0.0)
                found_cs = True
                break
            if i > 0 and time[k] <= peak_locs[i - 1]:
                break
            if k == 0:
                t_CS[i] = time[0]
                found_cs = True
        if not found_cs:
            t_CS[i] = np.nan

        # --- CE: next falling zero-crossing after peak ---
        after = zc2_times[zc2_times > p_t]
        t_CE[i] = after.min() if len(after) > 0 else np.nan

        if np.isnan(t_CE[i]):
            continue

        # --- RE: find valley after CE, scan forward until 5% of trough ---
        t_next = peak_locs[i + 1] if i < n - 1 else t_end
        idx_s = np.argmin(np.abs(time - t_CE[i]))
        idx_e = np.argmin(np.abs(time - t_next))

        if idx_e > idx_s:
            segment = velocity[idx_s:idx_e]
            idx_valley = idx_s + int(np.argmin(segment))
            valley_val = velocity[idx_valley]
            target_re = 0.05 * valley_val

            found_re = False
            for k in range(idx_valley, len(time)):
                v_curr = velocity[k]
                if v_curr >= target_re:
                    t_RE[i] = _interp_crossing_time(time, velocity, max(k - 1, 0), k, target_re)
                    found_re = True
                    break
                if v_curr >= 0:
                    t_RE[i] = _interp_crossing_time(time, velocity, max(k - 1, 0), k, 0.0)
                    found_re = True
                    break
                if time[k] >= t_next:
                    break
            if not found_re:
                t_RE[i] = t_next

    return t_CS, t_CE, t_RE


def calculate_mdp_metrics(
    signal: np.ndarray,
    time: np.ndarray,
    k_multiplier: float = 1.0,
    min_peak_distance_sec: float = 0.2,
) -> BeatMetrics:
    """
    Full MDP analysis for one signal (X or Y axis velocity).

    Parameters
    ----------
    signal               : velocity trace (µm/s), shape (N,)
    time                 : time vector (s), shape (N,)
    k_multiplier         : peak height threshold = k * std(signal)
    min_peak_distance_sec: minimum time between peaks (seconds)

    Returns
    -------
    BeatMetrics dataclass with all per-beat results
    """
    result = BeatMetrics()

    dt = time[1] - time[0]
    min_dist_samples = max(1, int(min_peak_distance_sec / dt))

    min_height = k_multiplier * np.std(signal)
    is_flipped, dom_sig = morphology_flip_test(time, signal, min_height, min_peak_distance_sec)
    result.is_flipped = is_flipped
    result.signal_display = dom_sig

    min_height_final = max(k_multiplier * np.std(dom_sig), 1e-3)
    peak_idx, _ = find_peaks(dom_sig, height=min_height_final, distance=min_dist_samples)

    result.HR = len(peak_idx)
    if result.HR == 0:
        return result

    result.peak_locs = time[peak_idx]
    result.peaks = dom_sig[peak_idx]

    if result.HR > 1:
        result.IBI_avg = float(np.mean(np.diff(result.peak_locs)))

    # CS / CE / RE
    try:
        zc_times, zc_types = _find_zero_crossings(time, dom_sig)
        t_CS, t_CE, t_RE = _dynamic_pairing(result.peak_locs, zc_times, zc_types, time, dom_sig)

        result.CS = t_CS
        result.CE = t_CE
        result.RE = t_RE
        result.ST = t_CE - t_CS
        result.DT = t_RE - t_CE

        n = result.HR
        ib = np.full(n, np.nan)
        if n > 1:
            ib[:-1] = t_CS[1:] - t_RE[:-1]
        result.Interbeat = ib

    except Exception:
        pass

    return result


def evaluate_signal_mdp(
    signal: np.ndarray,
    time: np.ndarray,
    k_multiplier: float = 1.0,
    min_peak_distance_sec: float = 0.2,
) -> dict:
    """
    Quick evaluation for axis selection (X vs Y).
    Returns dict with HR, IBI_std, is_valid.
    """
    dt = time[1] - time[0]
    min_dist_samples = max(1, int(min_peak_distance_sec / dt))
    min_height = k_multiplier * np.std(signal)
    _, dom_sig = morphology_flip_test(time, signal, min_height, min_peak_distance_sec)
    min_height_final = max(k_multiplier * np.std(dom_sig), 1e-3)
    peak_idx, _ = find_peaks(dom_sig, height=min_height_final, distance=min_dist_samples)
    hr = len(peak_idx)
    ibi_std = float(np.std(np.diff(time[peak_idx]))) if hr >= 2 else float("inf")
    return {"HR": hr, "IBI_std": ibi_std, "is_valid": hr >= 3}


def select_dominant_axis(
    signal_x: np.ndarray,
    signal_y: np.ndarray,
    time: np.ndarray,
    k_multiplier: float = 1.0,
    min_peak_distance_sec: float = 0.2,
) -> str:
    """
    Pick the axis (X or Y) with more stable beat rhythm (lower IBI std).
    Returns 'X' or 'Y'.
    """
    mx = evaluate_signal_mdp(signal_x, time, k_multiplier, min_peak_distance_sec)
    my = evaluate_signal_mdp(signal_y, time, k_multiplier, min_peak_distance_sec)

    if mx["is_valid"] and my["is_valid"]:
        return "X" if mx["IBI_std"] < my["IBI_std"] else "Y"
    if mx["is_valid"]:
        return "X"
    if my["is_valid"]:
        return "Y"
    return "X" if np.std(signal_x) > np.std(signal_y) else "Y"


def pca_projection(
    signal_x: np.ndarray,
    signal_y: np.ndarray,
) -> tuple[np.ndarray, float]:
    """
    Project (signal_x, signal_y) onto the first principal component.

    Returns
    -------
    pca_signal : 1-D array, projection onto PC1 (same length as input)
    angle_deg  : angle of PC1 in degrees (0° = pure X, 90° = pure Y)
    """
    mat = np.stack([signal_x, signal_y], axis=1).astype(float)
    mat_c = mat - mat.mean(axis=0)
    cov = np.cov(mat_c.T)
    eigvals, eigvecs = np.linalg.eigh(cov)
    pc1 = eigvecs[:, np.argmax(eigvals)]
    proj = mat_c @ pc1
    angle_deg = float(np.degrees(np.arctan2(pc1[1], pc1[0])))
    return proj, angle_deg


def select_dominant_signal(
    signal_x: np.ndarray,
    signal_y: np.ndarray,
    time: np.ndarray,
    k_multiplier: float = 1.0,
    min_peak_distance_sec: float = 0.2,
    method: str = "pca",
) -> tuple[np.ndarray, str]:
    """
    Select the best signal for MDP analysis.

    Parameters
    ----------
    method : 'pca'  — project onto first principal component (default)
             'axis' — pick X or Y by lower IBI std (legacy behaviour)

    Returns
    -------
    signal     : 1-D velocity array to pass to calculate_mdp_metrics
    axis_label : human-readable label stored in roi['dominant_axis']
                 e.g. 'PCA(+34°)' or 'X' / 'Y'
    """
    if method == "pca":
        proj, angle = pca_projection(signal_x, signal_y)
        sign = "+" if angle >= 0 else ""
        label = f"PCA({sign}{angle:.0f}°)"
        return proj, label

    # fallback: legacy axis selection
    axis = select_dominant_axis(signal_x, signal_y, time,
                                k_multiplier, min_peak_distance_sec)
    sig = signal_x if axis == "X" else signal_y
    return sig, axis
