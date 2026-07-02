"""
KLT Tracking Validation
========================
Runs Python KLT on Ctrl/After/1.mov and compares final metrics
(HR, IBI, Force) against the MATLAB golden standard.

Note: KLT implementations differ between OpenCV and MATLAB at the
pixel level, so we compare final *analysis* results, not raw signals.

Run:
    python cardio_py/tests/validate_tracking.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import numpy as np
import scipy.io
import cv2
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from cardio_py.core.tracking import track_video
from cardio_py.core.segmentation import segment_otsu
from cardio_py.core.mdp import calculate_mdp_metrics, select_dominant_signal
from cardio_py.core.force import compute_contractility

VIDEO_PATH = '/Users/ottiblai/Desktop/cardioproj/20260630_matlabtopython/Ctrl/After/1.mov'
MAT_PATH   = '/Users/ottiblai/Desktop/cardioproj/20260630_matlabtopython/Analysis_20260630/_mat_files_for_review/VID_0001_for_review.mat'
SCALE_UM_PX = 10000 / 1530   # placeholder — replace with real calibration

# ── MATLAB golden standard ────────────────────────────────────
mat = scipy.io.loadmat(
    '/Users/ottiblai/Desktop/cardioproj/20260630_matlabtopython/golden_standard.mat',
    squeeze_me=True, struct_as_record=False
)
g = mat['golden']
ref_HR    = int(g.PeakLocs.shape[0])
ref_IBI   = float(g.IBI_avg)
ref_force = float(g.Force)

print(f"\nMALTAB golden standard: HR={ref_HR}  IBI={ref_IBI:.4f}s  Force={ref_force:.4f} µm/s")

# ── Step 1: Load MATLAB masks from .mat (Manual ROI mode) ────
# VID_0001 was processed in Manual mode (roiPrefix='ROI'), so masks
# are hand-drawn bounding boxes stored in L_all_organoids.
print("\n[1/3] Loading ROI masks from MATLAB .mat file...")
mat_review = scipy.io.loadmat(MAT_PATH, squeeze_me=True, struct_as_record=False)
rd = mat_review['reviewData']
L = rd.L_all_organoids.astype(np.int32)
n_rois = int(L.max())
masks = [(L == i) for i in range(1, n_rois + 1)]
print(f"      Loaded {n_rois} ROI(s) from MATLAB mask")

# ── Step 2: KLT tracking ──────────────────────────────────────
print(f"[2/3] Running KLT tracking on {os.path.basename(VIDEO_PATH)}...")
results = track_video(VIDEO_PATH, masks, scale_um_per_px=SCALE_UM_PX)
r = results[0]
print(f"      Frames={r.n_frames}  Features={r.n_features}  FPS={r.frame_rate:.2f}")

# ── Step 3: MDP + Force ───────────────────────────────────────
print("[3/3] Running MDP + Force analysis...")
signal, axis = select_dominant_signal(r.signal_x, r.signal_y, r.time)
mdp    = calculate_mdp_metrics(signal, r.time)
force  = compute_contractility(r.signal_mag, r.time, r.frame_rate, mdp.peak_locs)

py_HR    = mdp.HR
py_IBI   = mdp.IBI_avg
py_force = force['contractility_mag']

# ── Results ───────────────────────────────────────────────────
print("\n" + "="*58)
print("  KLT Tracking Validation Results")
print("  (tolerance: HR ±2, IBI ±10%, Force ±20%)")
print("="*58)

hr_ok    = abs(py_HR - ref_HR) <= 2
ibi_ok   = abs(py_IBI - ref_IBI) / ref_IBI < 0.10
force_ok = abs(py_force - ref_force) / ref_force < 0.20

rows = [
    ("HR (peaks)",   py_HR,    ref_HR,    hr_ok,    ""),
    ("IBI_avg (s)",  py_IBI,   ref_IBI,   ibi_ok,   f"diff={abs(py_IBI-ref_IBI)*1000:.1f}ms"),
    ("Force (µm/s)", py_force, ref_force, force_ok, f"diff={abs(py_force-ref_force):.2f}"),
]
for name, got, expected, ok, note in rows:
    mark = '✅' if ok else '⚠️ '
    print(f"  {mark}  {name:20s}  Python={got:.4f}  MATLAB={expected:.4f}  {note}")

print("="*58 + "\n")

# ── Plot ──────────────────────────────────────────────────────
fig = plt.figure(figsize=(16, 10))
fig.suptitle("KLT Tracking Validation: Python vs MATLAB Golden Standard",
             fontsize=13, fontweight='bold')
gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.5, wspace=0.3)

# MATLAB reference signals
ref_sig_x = g.signal_X.astype(float)
ref_time   = g.time.astype(float)

# 1. Signal X comparison
ax1 = fig.add_subplot(gs[0, :])
ax1.plot(ref_time, ref_sig_x, color='orange', lw=1.2, alpha=0.8, label='MATLAB signal_X')
ax1.plot(r.time,   r.signal_x, color='steelblue', lw=1.0, alpha=0.8, label='Python signal_X')
ax1.set_xlabel('Time (s)')
ax1.set_ylabel('Velocity (µm/s)')
ax1.set_title('X-axis velocity signal comparison')
ax1.legend(fontsize=9)
ax1.grid(alpha=0.3)

# 2. MDP peaks on Python signal
ax2 = fig.add_subplot(gs[1, :])
ax2.plot(r.time, signal, color='steelblue', lw=1.0, label=f'Python {axis}-axis (dominant)')
ax2.scatter(mdp.peak_locs,
            [signal[np.argmin(np.abs(r.time - t))] for t in mdp.peak_locs],
            color='red', s=50, zorder=5, label=f'Peaks (n={py_HR})')
ax2.scatter(g.PeakLocs.astype(float),
            [ref_sig_x[np.argmin(np.abs(ref_time - t))] for t in g.PeakLocs],
            marker='x', color='orange', s=70, lw=2, zorder=6, label=f'MATLAB peaks (n={ref_HR})')
ax2.set_xlabel('Time (s)')
ax2.set_ylabel('Velocity (µm/s)')
ax2.set_title(f'Peak detection  |  Python HR={py_HR}  MATLAB HR={ref_HR}')
ax2.legend(fontsize=9)
ax2.grid(alpha=0.3)

# 3. Force trace
ax3 = fig.add_subplot(gs[2, 0])
ax3.plot(r.time, force['global_trace'], color='steelblue', lw=1.0, label='Python force trace')
ax3.scatter(force['force_locs'], force['force_vals'],
            color='red', s=40, zorder=5, label=f'Python peaks (mean={py_force:.1f})')
ax3.set_xlabel('Time (s)')
ax3.set_ylabel('Force (µm/s)')
ax3.set_title(f'Force trace  |  Python={py_force:.2f}  MATLAB={ref_force:.2f} µm/s')
ax3.legend(fontsize=9)
ax3.grid(alpha=0.3)

# 4. IBI comparison
ax4 = fig.add_subplot(gs[2, 1])
py_ibi_arr  = np.diff(mdp.peak_locs)
ref_ibi_arr = np.diff(g.PeakLocs.astype(float))
n = min(len(py_ibi_arr), len(ref_ibi_arr))
ax4.plot(ref_ibi_arr[:n], 'o-', color='orange', lw=1.5, label=f'MATLAB IBI (mean={ref_IBI:.3f}s)')
ax4.plot(py_ibi_arr[:n],  's--', color='steelblue', lw=1.5, label=f'Python IBI (mean={py_IBI:.3f}s)')
ax4.set_xlabel('Beat index')
ax4.set_ylabel('IBI (s)')
ax4.set_title('Inter-Beat Interval')
ax4.legend(fontsize=9)
ax4.grid(alpha=0.3)

plt.savefig('/Users/ottiblai/Desktop/cardioproj/20260630_matlabtopython/cardio_py/tests/validate_tracking.png',
            dpi=130, bbox_inches='tight')
print("Plot saved to cardio_py/tests/validate_tracking.png")
plt.show()
