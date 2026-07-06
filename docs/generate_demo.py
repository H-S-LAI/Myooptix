"""
Export static demo assets from a pre-computed pkl for the website.
Run from repo root:
  python docs/generate_demo.py
"""
import sys, json, pickle
import numpy as np
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PKL  = Path(r"C:\Users\LAI\Desktop\20260630_matlabtopython\testresults\_pkl_for_review\1.pkl")
OUT  = ROOT / "docs" / "demo_assets"
OUT.mkdir(parents=True, exist_ok=True)

with open(PKL, "rb") as f:
    d = pickle.load(f)

frame_rgb = d["frame_rgb"]          # (H, W, 3)
roi_list  = d["roi_list"]

COLORS = ["#1e3a8a", "#3558b8", "#c25c4e"]   # navy / navy-light / red per ROI (palette B)

# ── frame.jpg: first frame + ROI contours ────────────────────────────────────
frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
for i, roi in enumerate(roi_list):
    mask = roi["mask"].astype(np.uint8)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hex_c = COLORS[i % len(COLORS)].lstrip("#")
    bgr   = tuple(int(hex_c[j:j+2], 16) for j in (4, 2, 0))
    cv2.drawContours(frame_bgr, contours, -1, bgr, 2)
    # label
    ys, xs = np.where(roi["mask"])
    cx, cy = int(xs.mean()), int(ys.mean())
    cv2.putText(frame_bgr, f"ROI {i+1}", (cx-20, cy),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, bgr, 2)
cv2.imwrite(str(OUT / "frame.jpg"), frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 88])
print("Saved frame.jpg")

# ── waveform.png: all 3 ROI signals stacked ──────────────────────────────────
CHART_BG  = "#f8f7f4"
CHART_MUT = "#6b6f7d"
CHART_SPL = "#dddbd5"

fig, axes = plt.subplots(3, 1, figsize=(9, 5), facecolor=CHART_BG,
                         gridspec_kw={"hspace": 0.15})
for i, (roi, ax) in enumerate(zip(roi_list, axes)):
    time   = roi["time"]
    mdp    = roi["mdp"]
    color  = COLORS[i]
    signal = mdp.signal_display if len(mdp.signal_display) == len(time) else roi.get("signal", np.array([]))

    ax.set_facecolor(CHART_BG)
    ax.plot(time, signal, color=color, linewidth=1.2, alpha=0.9)

    if mdp.peak_locs is not None and len(mdp.peak_locs):
        pv = np.interp(mdp.peak_locs, time, signal)
        ax.scatter(mdp.peak_locs, pv, color=color, s=20, zorder=5, alpha=0.85)

    ax.set_ylabel(f"ROI {i+1}", color=CHART_MUT, fontsize=8, labelpad=4)
    ax.tick_params(colors=CHART_MUT, labelsize=7)
    for spine in ax.spines.values():
        spine.set_edgecolor(CHART_SPL)
    if i < 2:
        ax.set_xticklabels([])

axes[-1].set_xlabel("Time (s)", color=CHART_MUT, fontsize=8)
fig.tight_layout(pad=0.6)
fig.savefig(OUT / "waveform.png", dpi=130, facecolor=fig.get_facecolor())
plt.close(fig)
print("Saved waveform.png")

# ── force.png: contractility traces ──────────────────────────────────────────
fig, axes = plt.subplots(3, 1, figsize=(9, 4), facecolor=CHART_BG,
                         gridspec_kw={"hspace": 0.15})
for i, (roi, ax) in enumerate(zip(roi_list, axes)):
    time  = roi["time"]
    gtrace = roi.get("force", {}).get("global_trace")
    color  = COLORS[i]
    ax.set_facecolor(CHART_BG)
    if gtrace is not None and len(gtrace) == len(time):
        ax.plot(time, gtrace, color=color, linewidth=1.1, alpha=0.9)
    ax.set_ylabel(f"ROI {i+1}", color=CHART_MUT, fontsize=8, labelpad=4)
    ax.tick_params(colors=CHART_MUT, labelsize=7)
    for spine in ax.spines.values():
        spine.set_edgecolor(CHART_SPL)
    if i < 2:
        ax.set_xticklabels([])

axes[-1].set_xlabel("Time (s)", color=CHART_MUT, fontsize=8)
fig.tight_layout(pad=0.6)
fig.savefig(OUT / "force.png", dpi=130, facecolor=fig.get_facecolor())
plt.close(fig)
print("Saved force.png")

# ── summary.json ─────────────────────────────────────────────────────────────
rois_summary = []
for i, roi in enumerate(roi_list):
    mdp   = roi["mdp"]
    fvals = roi.get("force", {}).get("force_vals", [])
    rois_summary.append({
        "roi": i + 1,
        "bpm": int(mdp.HR),
        "beats": int(len(mdp.peak_locs)),
        "ibi_avg_ms": round(float(mdp.IBI_avg) * 1000, 1),
        "hrv_ms": round(float(np.std(mdp.Interbeat) * 1000), 1) if len(mdp.Interbeat) else 0,
        "contractility_mean": round(float(np.mean(fvals)), 1) if len(fvals) else None,
        "color": COLORS[i],
    })

(OUT / "summary.json").write_text(json.dumps({"rois": rois_summary}, indent=2))
print("Saved summary.json")
print("\nROI summary:")
for r in rois_summary:
    print(f"  ROI {r['roi']}: {r['bpm']} BPM  contractility {r['contractility_mean']} µm/s")
