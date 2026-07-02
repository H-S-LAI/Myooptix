"""
Force (Contractility) Analysis
================================
Anchor Search: for each MDP peak, find the maximum Global Force value
within a ±window around that peak time.

Global_Trace = baseline-corrected KLT magnitude trace (µm/s).
Baseline correction uses a 1-second moving minimum window.
"""

import numpy as np


def correct_baseline(trace: np.ndarray, frame_rate: float, window_sec: float = 1.0) -> np.ndarray:
    """
    Subtract a moving-minimum baseline from the raw KLT magnitude trace.
    Equivalent to MATLAB: baseline = movmin(trace, round(window_sec * frameRate))
    """
    win = max(1, round(window_sec * frame_rate))
    n = len(trace)
    baseline = np.empty(n)

    # Centered moving minimum (same behaviour as MATLAB movmin default)
    half = win // 2
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i - half + win)
        baseline[i] = trace[lo:hi].min()

    corrected = trace - baseline
    corrected[corrected < 0] = 0.0
    return corrected


def anchor_search(
    global_trace: np.ndarray,
    time: np.ndarray,
    peak_locs: np.ndarray,
    window_sec: float = 0.25,
) -> tuple[np.ndarray, np.ndarray]:
    """
    For each MDP peak location, search ±window_sec for the maximum
    value in global_trace.

    Returns
    -------
    force_vals : (n_peaks,) array of force magnitudes (µm/s)
    force_locs : (n_peaks,) array of times where those maxima occur (s)
    """
    force_vals = np.empty(len(peak_locs))
    force_locs = np.empty(len(peak_locs))

    for k, t_center in enumerate(peak_locs):
        in_window = (time >= t_center - window_sec) & (time <= t_center + window_sec)
        if in_window.any():
            idx_win = np.where(in_window)[0]
            idx_max = idx_win[np.argmax(global_trace[idx_win])]
            force_vals[k] = global_trace[idx_max]
            force_locs[k] = time[idx_max]
        else:
            idx_exact = int(np.argmin(np.abs(time - t_center)))
            force_vals[k] = global_trace[idx_exact]
            force_locs[k] = time[idx_exact]

    return force_vals, force_locs


def compute_contractility(
    klt_magnitude: np.ndarray,
    time: np.ndarray,
    frame_rate: float,
    peak_locs: np.ndarray,
    window_sec: float = 0.25,
    baseline_window_sec: float = 1.0,
) -> dict:
    """
    Full contractility pipeline for one ROI.

    Parameters
    ----------
    klt_magnitude       : raw KLT displacement magnitude trace (µm/s)
    time                : time vector (s)
    frame_rate          : video frame rate (fps)
    peak_locs           : MDP peak times (s) from calculate_mdp_metrics
    window_sec          : anchor search half-window (default 0.25 s)
    baseline_window_sec : moving-min window for baseline correction (default 1.0 s)

    Returns
    -------
    dict with keys:
      global_trace        : baseline-corrected force trace
      force_vals          : per-beat peak force values (µm/s)
      force_locs          : per-beat peak force times (s)
      contractility_mag   : mean force across all beats (µm/s)
    """
    global_trace = correct_baseline(klt_magnitude, frame_rate, baseline_window_sec)

    if len(peak_locs) == 0:
        return {
            "global_trace": global_trace,
            "force_vals": np.array([]),
            "force_locs": np.array([]),
            "contractility_mag": 0.0,
        }

    force_vals, force_locs = anchor_search(global_trace, time, peak_locs, window_sec)

    return {
        "global_trace": global_trace,
        "force_vals": force_vals,
        "force_locs": force_locs,
        "contractility_mag": float(np.mean(force_vals)),
    }
