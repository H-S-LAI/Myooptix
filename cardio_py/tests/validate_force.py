"""
Force (Contractility) Validation
=================================
Compares Python anchor search results against MATLAB golden standard.

Run:
    python cardio_py/tests/validate_force.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import numpy as np
import scipy.io
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from cardio_py.core.mdp import calculate_mdp_metrics, select_dominant_signal
from cardio_py.core.force import compute_contractility

# ── Load golden standard ──────────────────────────────────────
mat = scipy.io.loadmat(
    '/Users/ottiblai/Desktop/cardioproj/20260630_matlabtopython/golden_standard.mat',
    squeeze_me=True, struct_as_record=False
)
g = mat['golden']

time        = g.time.astype(float)
signal_x    = g.signal_X.astype(float)
signal_y    = g.signal_Y.astype(float)
glob_trace  = g.Global_Trace.astype(float)   # already baseline-corrected by MATLAB
frame_rate  = float(g.frameRate)

ref_force_vals = g.Global_Peaks_Vals.astype(float)
ref_force_locs = g.Global_Peaks_Locs.astype(float)
ref_contractility = float(g.Force)

# MATLAB golden standard first 5 values (from user confirmation)
ref_first5_vals = np.array([77.4720, 72.7265, 70.2241, 71.9629, 74.3517])
ref_first5_locs = np.array([1.0677,  2.3023,  3.5702,  4.8048,  6.0727])

# ── Run Python pipeline ───────────────────────────────────────
signal, axis = select_dominant_signal(signal_x, signal_y, time)
mdp    = calculate_mdp_metrics(signal, time, k_multiplier=1.0, min_peak_distance_sec=0.2)

# Raw KLT magnitude from golden standard (not yet baseline-corrected)
# golden_standard stores the already-corrected Global_Trace, so we use it directly
# for anchor search (same as MATLAB does in the review GUI)
result = compute_contractility(
    klt_magnitude=glob_trace,   # already corrected — skip baseline step
    time=time,
    frame_rate=frame_rate,
    peak_locs=mdp.peak_locs,
    window_sec=0.25,
    baseline_window_sec=1.0,
)

# ── Numerical comparison ──────────────────────────────────────
TOL_FORCE = 0.5    # µm/s
TOL_LOC   = 0.005  # s

print("\n" + "="*55)
print("  Force Validation Results")
print("="*55)

contractility_ok = abs(result['contractility_mag'] - ref_contractility) < TOL_FORCE
print(f"  {'✅' if contractility_ok else '❌'}  "
      f"{'Contractility_Mag':30s}  "
      f"got={result['contractility_mag']:.4f}  "
      f"expected={ref_contractility:.4f}  (tol±{TOL_FORCE})")

n_peaks_ok = len(result['force_vals']) == len(ref_force_vals)
print(f"  {'✅' if n_peaks_ok else '❌'}  "
      f"{'Force peak count':30s}  "
      f"got={len(result['force_vals'])}  expected={len(ref_force_vals)}")

# First 5 peaks
print("\n  First 5 beats comparison:")
print(f"  {'Beat':>5}  {'Py val':>10}  {'MATLAB val':>10}  {'Diff':>8}  {'Py loc':>8}  {'MATLAB loc':>10}  {'Loc diff':>10}")
for i in range(5):
    v_py  = result['force_vals'][i]
    v_ref = ref_first5_vals[i]
    l_py  = result['force_locs'][i]
    l_ref = ref_first5_locs[i]
    ok = '✅' if abs(v_py - v_ref) < TOL_FORCE else '❌'
    print(f"  {ok} {i+1:>3}  {v_py:>10.4f}  {v_ref:>10.4f}  {v_py-v_ref:>+8.4f}  {l_py:>8.4f}  {l_ref:>10.4f}  {l_py-l_ref:>+10.4f}")

print("="*55 + "\n")

# ── Plot ──────────────────────────────────────────────────────
fig = plt.figure(figsize=(16, 9))
fig.suptitle("Force Validation: Python vs MATLAB Golden Standard", fontsize=13, fontweight='bold')
gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.30)

# 1. Global force trace + peaks
ax1 = fig.add_subplot(gs[0, :])
ax1.plot(time, glob_trace, color='steelblue', lw=1.2, label='Global Force Trace (baseline-corrected)')
ax1.scatter(result['force_locs'], result['force_vals'],
            color='red', s=60, zorder=5, label=f'Python peaks (n={len(result["force_vals"])})')
ax1.scatter(ref_force_locs, ref_force_vals,
            marker='x', color='orange', s=80, lw=2, zorder=6, label=f'MATLAB peaks (n={len(ref_force_vals)})')
ax1.set_xlabel('Time (s)')
ax1.set_ylabel('Force (µm/s)')
ax1.set_title(f'Global Force Trace & Anchor Search  |  '
              f'Python={result["contractility_mag"]:.2f}  MATLAB={ref_contractility:.2f} µm/s')
ax1.legend(fontsize=9)
ax1.grid(alpha=0.3)

# 2. Per-beat force values
ax2 = fig.add_subplot(gs[1, 0])
n = min(len(result['force_vals']), len(ref_force_vals))
ax2.plot(range(n), ref_force_vals[:n], 'o-', color='orange', label='MATLAB force', lw=1.5)
ax2.plot(range(n), result['force_vals'][:n], 's--', color='steelblue', label='Python force', lw=1.5)
ax2.set_xlabel('Beat index')
ax2.set_ylabel('Force (µm/s)')
ax2.set_title('Per-beat contractility')
ax2.legend(fontsize=9)
ax2.grid(alpha=0.3)

# 3. Per-beat force error
ax3 = fig.add_subplot(gs[1, 1])
errors = result['force_vals'][:n] - ref_force_vals[:n]
ax3.bar(range(n), errors, color='steelblue', edgecolor='navy', alpha=0.8)
ax3.axhline(0, color='red', lw=1)
ax3.set_xlabel('Beat index')
ax3.set_ylabel('Error (µm/s)')
ax3.set_title('Force error (Python − MATLAB)')
ax3.grid(alpha=0.3)

plt.savefig('/Users/ottiblai/Desktop/cardioproj/20260630_matlabtopython/cardio_py/tests/validate_force.png',
            dpi=130, bbox_inches='tight')
print("Plot saved to cardio_py/tests/validate_force.png")
plt.show()
