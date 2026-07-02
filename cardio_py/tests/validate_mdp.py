"""
MDP 驗證腳本
============
把 Python 版 MDP 結果和 MATLAB 黃金標準比對，並畫圖視覺化。

執行方式：
    python cardio_py/tests/validate_mdp.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import numpy as np
import scipy.io
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
matplotlib.rcParams['font.family'] = 'DejaVu Sans'
from cardio_py.core.mdp import calculate_mdp_metrics, select_dominant_signal

# ── 載入黃金標準 ──────────────────────────────────────────────
mat = scipy.io.loadmat(
    '/Users/ottiblai/Desktop/cardioproj/20260630_matlabtopython/golden_standard.mat',
    squeeze_me=True, struct_as_record=False
)
g = mat['golden']

time       = g.time.astype(float)
signal_x   = g.signal_X.astype(float)
signal_y   = g.signal_Y.astype(float)
glob_trace = g.Global_Trace.astype(float)

ref_HR         = int(g.HR) if hasattr(g, 'HR') else int(g.PeakLocs.shape[0])
ref_peak_locs  = g.PeakLocs.astype(float)
ref_IBI_avg    = float(g.IBI_avg)
ref_is_flipped = bool(g.isFlipped)
ref_ST         = g.ST.astype(float)
ref_DT         = g.DT.astype(float)
ref_force      = float(g.Force)

# ── 執行 Python MDP ───────────────────────────────────────────
signal, axis = select_dominant_signal(signal_x, signal_y, time)

mdp = calculate_mdp_metrics(signal, time, k_multiplier=1.0, min_peak_distance_sec=0.2)

# ── 數值比對 ──────────────────────────────────────────────────
PASS = '\033[92m[PASS]\033[0m'
FAIL = '\033[91m[FAIL]\033[0m'

print("\n" + "="*55)
print("  MDP 驗證結果")
print("="*55)

checks = [
    ("Dominant axis", axis, "X"),
    ("is_flipped",    mdp.is_flipped, ref_is_flipped),
    ("HR (peak count)", mdp.HR, ref_HR),
]
for name, got, expected in checks:
    ok = (got == expected)
    print(f"  {PASS if ok else FAIL}  {name:25s}  got={got}  expected={expected}")

# 數值比對（允許微小浮點差異）
tol_ibi   = 0.005   # 5ms
tol_st_dt = 0.005
tol_force = 0.5

ibi_ok    = abs(mdp.IBI_avg - ref_IBI_avg) < tol_ibi
print(f"  {'✅' if ibi_ok else '❌'}  {'IBI_avg':25s}  got={mdp.IBI_avg:.4f}  expected={ref_IBI_avg:.4f}  (tol±{tol_ibi})")

if len(mdp.ST) > 0 and len(ref_ST) > 0:
    st_diff = float(np.nanmean(np.abs(mdp.ST - ref_ST[:len(mdp.ST)])))
    dt_diff = float(np.nanmean(np.abs(mdp.DT - ref_DT[:len(mdp.DT)])))
    print(f"  {'✅' if st_diff < tol_st_dt else '❌'}  {'ST mean abs diff':25s}  {st_diff:.4f}s  (tol<{tol_st_dt})")
    print(f"  {'✅' if dt_diff < tol_st_dt else '❌'}  {'DT mean abs diff':25s}  {dt_diff:.4f}s  (tol<{tol_st_dt})")

print(f"\n  Peak locs: first={mdp.peak_locs[0]:.4f}s  last={mdp.peak_locs[-1]:.4f}s")
print(f"  MATLAB:    first={ref_peak_locs[0]:.4f}s  last={ref_peak_locs[-1]:.4f}s")
print("="*55 + "\n")

# ── 可視化 ────────────────────────────────────────────────────
fig = plt.figure(figsize=(16, 11))
fig.suptitle("MDP Validation: Python vs MATLAB Golden Standard", fontsize=13, fontweight='bold')
gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.55, wspace=0.32)

# 1. 速度波形 + 峰值比對
ax1 = fig.add_subplot(gs[0, :])
ax1.plot(time, signal, color='steelblue', lw=1.2, label='Velocity signal (X-axis)')
ax1.scatter(mdp.peak_locs, [signal[np.argmin(np.abs(time - t))] for t in mdp.peak_locs],
            color='red', s=60, zorder=5, label=f'Python peaks (n={mdp.HR})')
ax1.scatter(ref_peak_locs, [signal[np.argmin(np.abs(time - t))] for t in ref_peak_locs],
            marker='x', color='orange', s=80, lw=2, zorder=6, label=f'MATLAB peaks (n={ref_HR})')
ax1.set_xlabel('Time (s)')
ax1.set_ylabel('Velocity (µm/s)')
ax1.set_title(f'Waveform & Peak Detection  |  is_flipped={mdp.is_flipped}  |  HR={mdp.HR}')
ax1.legend(fontsize=9)
ax1.grid(alpha=0.3)

# 2. Peak 位置誤差（每個 beat）
ax2 = fig.add_subplot(gs[1, 0])
n_compare = min(len(mdp.peak_locs), len(ref_peak_locs))
errors = mdp.peak_locs[:n_compare] - ref_peak_locs[:n_compare]
ax2.bar(range(n_compare), errors * 1000, color='steelblue', edgecolor='navy', alpha=0.8)
ax2.axhline(0, color='red', lw=1)
ax2.set_xlabel('Beat index')
ax2.set_ylabel('Error (ms)')
ax2.set_title('Peak timing error (Python − MATLAB)')
ax2.grid(alpha=0.3)

# 3. ST 比對
ax3 = fig.add_subplot(gs[1, 1])
n_st = min(len(mdp.ST), len(ref_ST))
ax3.plot(range(n_st), ref_ST[:n_st] * 1000, 'o-', color='orange', label='MATLAB ST', lw=1.5)
ax3.plot(range(n_st), mdp.ST[:n_st] * 1000, 's--', color='steelblue', label='Python ST', lw=1.5)
ax3.set_xlabel('Beat index')
ax3.set_ylabel('ST (ms)')
ax3.set_title('Systolic Time (ST) comparison')
ax3.legend(fontsize=9)
ax3.grid(alpha=0.3)

# 4. DT 比對
ax4 = fig.add_subplot(gs[2, 0])
n_dt = min(len(mdp.DT), len(ref_DT))
ax4.plot(range(n_dt), ref_DT[:n_dt] * 1000, 'o-', color='orange', label='MATLAB DT', lw=1.5)
ax4.plot(range(n_dt), mdp.DT[:n_dt] * 1000, 's--', color='steelblue', label='Python DT', lw=1.5)
ax4.set_xlabel('Beat index')
ax4.set_ylabel('DT (ms)')
ax4.set_title('Diastolic Time (DT) comparison')
ax4.legend(fontsize=9)
ax4.grid(alpha=0.3)

# 5. IBI 分佈比對
ax5 = fig.add_subplot(gs[2, 1])
ref_ibi_arr = np.diff(ref_peak_locs)
py_ibi_arr  = np.diff(mdp.peak_locs)
ax5.plot(ref_ibi_arr, 'o-', color='orange', label=f'MATLAB IBI (mean={ref_IBI_avg:.3f}s)', lw=1.5)
ax5.plot(py_ibi_arr,  's--', color='steelblue', label=f'Python IBI (mean={mdp.IBI_avg:.3f}s)', lw=1.5)
ax5.set_xlabel('Beat interval index')
ax5.set_ylabel('IBI (s)')
ax5.set_title('Inter-Beat Interval comparison')
ax5.legend(fontsize=9)
ax5.grid(alpha=0.3)

plt.savefig('/Users/ottiblai/Desktop/cardioproj/20260630_matlabtopython/cardio_py/tests/validate_mdp.png',
            dpi=130, bbox_inches='tight')
print("Plot saved to cardio_py/tests/validate_mdp.png")
plt.show()
