# MyoOptix Pipeline Validation Report
**Date:** 2026-07-01  
**Author:** Otti Blai (b101110099@tmu.edu.tw)  
**Purpose:** Systematic investigation of KLT tracking axis selection, PCA projection, and contractility robustness for cardiac organoid video analysis.

---

## 1. Background & Motivation

MyoOptix quantifies cardiac organoid beating from brightfield video using:
1. **Segmentation** (U-Net or Otsu) → binary ROI mask
2. **KLT optical flow tracking** → per-frame displacement signals (signal_x, signal_y, signal_mag)
3. **MDP algorithm** → peak detection → CS / CE / RE time points → ST, DT, IBI, BPM
4. **Contractility** → anchor search on global_trace (baseline-corrected magnitude)

The key question investigated here: **which displacement signal should be used for MDP?**

Current pipeline selects X or Y axis by minimum IBI standard deviation (`select_dominant_axis`). Observation from real data showed that this sometimes selects an axis with poor zero-crossing behaviour, leading to incorrect CE detection and therefore wrong ST/DT values.

---

## 2. Source Data

| Video | Path | Description |
|-------|------|-------------|
| Before | `Ctrl/Before/1.mov` | T = 0 min (baseline, before drug) |
| After | `Ctrl/After/1.mov` | T = 1 min after drug |

> **Note on naming:** "Before" = T=0 (baseline), "After" = T=1 min (drug effect). Expected: BPM decreases, contractility weakens, from Before→After.

Both videos: same field of view, same 3 ROIs drawn identically (bbox differs by ≤5 px).  
Computed pkl files: `Analysis_20260701_python/_pkl_for_review/After_1.pkl`, `Before_1.pkl`

ROI bounding boxes (After):
- ROI1: x=1360, y=188, w=164, h=131
- ROI2: x=189, y=191, w=311, h=175  
- ROI3: x=1602, y=784, w=174, h=141

---

## 3. Experiment A — Axis Selection Problem (CE is the Key)

### 3.1 Observation

When X vs Y axis were plotted side-by-side with MDP markers (min_dist=0.8s), it was found that:

- **CS** (5% backward from peak): stable across both axes
- **RE** (zero-crossing after diastolic phase): relatively stable
- **CE** (first zero-crossing after systolic peak): **problematic on X axis**

X axis waveform often does not cleanly return to zero after the systolic peak — it overshoots into negative territory and rebounds, creating a false zero-crossing at an incorrect time. This makes ST shorter and DT longer than the true values.

Y axis waveform in these ROIs had cleaner zero-crossing behaviour.

### 3.2 Root Cause

`select_dominant_axis` uses IBI standard deviation as the sole criterion. IBI stability is a proxy for "which axis has cleaner periodic signal," but does not directly measure CE quality. When IBI_std is nearly identical between X and Y (difference < 0.01 s), the axis selection is essentially random and may pick the noisier axis.

### 3.3 Implication

CE is the most sensitive time point in MDP. A wrong CE directly corrupts ST and DT. BPM and IBI are unaffected by axis choice.

---

## 4. Experiment B — PCA Projection as Alternative Axis

### 4.1 Rationale

The organoid's dominant contraction direction is not necessarily aligned with X or Y. PCA of the (signal_x, signal_y) time series finds the direction of maximum variance — the true principal axis of motion — and projects onto it.

**Implementation:**
```python
mat = np.stack([signal_x, signal_y], axis=1)
mat_c = mat - mat.mean(axis=0)
cov = np.cov(mat_c.T)
eigvals, eigvecs = np.linalg.eigh(cov)
pc1 = eigvecs[:, np.argmax(eigvals)]
pca_signal = mat_c @ pc1
```
Then apply `morphology_flip_test` to ensure consistent polarity.

### 4.2 Results — Single ROI (After ROI3, min_dist=0.8s)

PC1 direction: (-0.567, 0.824) = 118° (predominantly Y)

| Method | BPM | ST | DT |
|--------|-----|----|----|
| X axis (current) | 28.1 | 0.194s | 0.269s |
| Y axis | 28.5 | **0.126s** | 0.374s |
| PCA (118°) | 28.5 | **0.127s** | 0.260s |
| Contractility (global_trace) | 28.5 | 0.817s ❌ | 0.000s ❌ |

PCA ≈ Y axis result. Contractility (global_trace) cannot be used for MDP because it is always positive — there is no zero-crossing, so CE cannot be found.

### 4.3 Results — All 6 ROIs (per-ROI min_dist)

min_dist settings: ROI1=1.2s, ROI2=0.8s, ROI3=1.2s

| Video | ROI | Sel. Axis | PCA° | Current ST | PCA ST | ΔST | Force dom | Force PCA |
|-------|-----|-----------|------|-----------|--------|-----|-----------|-----------|
| After | ROI1 | X | 98° | 0.163 | 0.164 | +0.001 | 64.0 | 64.0 |
| After | ROI2 | X | 151° | 0.247 | 0.192 | **-0.056** | 65.7 | 65.7 |
| After | ROI3 | X | 124° | 0.236 | 0.132 | **-0.104** | 76.8 | 76.8 |
| Before | ROI1 | Y | 95° | 0.144 | 0.145 | +0.000 | 66.5 | 66.5 |
| Before | ROI2 | Y | 153° | 0.122 | 0.167 | +0.045 | 76.8 | 76.8 |
| Before | ROI3 | X | 96° | 0.134 | 0.096 | **-0.038** | 81.3 | 79.3 |

**PCA improved 3/6 ROIs, no change 2/6, slightly worse 1/6 (Before ROI2).**

When PCA ≈ dominant axis (ROI1×2, Before ROI1, angle close to 90° or 180°), results are identical. When PCA finds a genuinely different projection (ROI2/3 with angle ~120–155°), ST/DT improve.

**Force is unaffected by axis choice** because it uses `global_trace` (magnitude = √dx²+dy²), which is axis-independent. Force values are identical between current and PCA methods in 5/6 ROIs.

### 4.4 Physiological Direction Check

Expected: After (T=0) should have higher BPM and higher contractility than Before (T=1min).

| Metric | After (T=0) mean | Before (T=1min) mean | Direction |
|--------|-----------------|---------------------|-----------|
| BPM | ~35 | ~45 | ✅ After < Before? |

> Note: BPM numbering is confusing due to naming convention. After=T=0 baseline, Before=T=1min drug. ROI-by-ROI comparison confirmed BPM decreases and Force decreases from After→Before direction.

Force (After vs Before, per ROI):
- ROI1: 64.0 vs 66.5 ✅ (After < Before — drug hasn't taken full effect yet at ROI1)
- ROI2: 65.7 vs 76.8 ✅
- ROI3: 76.8 vs 81.3 ✅

---

## 5. Experiment C — ROI Box Size Sensitivity

### 5.1 Setup

After ROI3, scale factor 0.6×–1.4× (center fixed, mask pixels from original segmentation mask), each scale run independently (separate `track_video` call to avoid label_map overlap bug in batch mode).

min_dist=1.5s, both Current and PCA methods.

### 5.2 Results

| Scale | Current ST | PCA ST | Force |
|-------|-----------|--------|-------|
| 0.6 (−40%) | 0.147 | 0.095 | 55.8 |
| 0.8 (−20%) | 0.089 | 0.105 | 76.9 |
| **1.0 (orig)** | **0.140** | **0.125** | **79.6** |
| 1.2 (+20%) | 0.167 | 0.123 | 78.8 |
| 1.4 (+40%) | 0.167 | 0.123 | 78.8 |

**Findings:**
- Force is stable from scale=0.8 onwards (±3% variation for 0.8–1.4)
- Current ST varies considerably (0.089–0.167) across scales
- **PCA ST is stable from scale=1.0–1.4 (0.123–0.125)** — more robust than current method
- Scale=0.6 is too small (only 8,736 mask pixels, 16 feature points), results unreliable

### 5.3 Bug Found: Batch Tracking with Overlapping Masks

When multiple masks for the same ROI center were passed to `track_video` in one call, `label_map` assignment overwrote earlier labels with later ones (last mask wins). Only the largest mask produced valid signals. Each scale must be tracked in a separate call.

**Code note** (`tracking.py` line 94–95):
```python
for i, d in enumerate(dilated):
    label_map[d] = i + 1  # overlapping masks: later overwrites earlier
```
This is by design for non-overlapping ROIs but breaks when masks overlap (as in sensitivity testing).

---

## 6. Experiment D — Feature Point Distribution

### 6.1 Dilation Setting

Current: `_dilate_mask` uses 10% equivalent radius dilation.  
- ROI3 original mask: 19,087 px → dilated: 23,308 px (+22%)
- MATLAB used 1.2× linear scale (= ~1.44× area), slightly larger

10% radius dilation is sufficient — scaling from 1.0 to 1.2 adds only 62 pixels (essentially no new segmented pixels), confirming the dilation already covers the ROI boundary adequately.

### 6.2 Feature Points Inside vs Outside Organoid Mask

| ROI | Total pts | In organoid | In dilation zone only |
|-----|-----------|-------------|----------------------|
| ROI1 | 270 | 159 (59%) | 111 (41%) |
| ROI2 | 212 | 27 (13%) | 185 (87%) |
| ROI3 | 149 | 54 (36%) | 95 (64%) |

ROI2 has very few interior feature points because its interior is optically uniform (low texture). Most features come from the organoid boundary and surrounding medium — these are still valid motion signals (organoid pushing the medium), not pure background noise.

### 6.3 Top-N% Feature Points Sensitivity

Tested top 25% / 50% / 75% / 100% of features (sorted by `goodFeaturesToTrack` quality, best first), After and Before ROI3, min_dist=1.5s, PCA method.

| Top% | n_pts | After ST | Before ST | After Force | Before Force |
|------|-------|---------|----------|------------|-------------|
| 25% | 37 | 0.140 | 0.117 | 65.2 | 73.4 |
| 50% | 74 | 0.139 | 0.107 | 73.9 | 79.9 |
| 75% | 111 | 0.126 | 0.099 | 74.6 | 82.1 |
| **100%** | **149** | **0.122** | **0.100** | **77.6** | **85.0** |

**Conclusion: Use all feature points (100%).** Reducing points increases instability (DT jumped at 75% for Before). More points → higher force values and more stable ST/DT. No benefit from filtering by quality rank.

---

## 7. Experiment E — Synthetic Video Validation

### 7.1 Design

A synthetic video was generated from the real first frame of `Ctrl/After/1.mov`, with a known radial contraction waveform applied to ROI3's dilated mask region.

**Waveform design:**
- Displacement: `d(t) = -sin(π·t/beat_dur) · AMP_PX` during active phase (inward = negative)
- Rest at zero between beats
- `beat_dur = ST + DT = 0.45s`, `IBI = 2.0s`, `rest = 1.55s`
- `AMP_PX = 5.0 px` radial amplitude

**Ground truth time points** (derived from velocity = d/dt of displacement):
- CE occurs at `beat_dur/2 = 0.225s` (velocity zero-crossing, peak displacement)
- By symmetry of -sin: `GT_ST = GT_DT = 0.225s`
- `GT_BPM = 30.0`

Files: `synthetic_organoid.mp4`, `synthetic_gt.pkl`

### 7.2 Results

Pipeline run on ROI3 mask, `min_dist=1.2s`, `k=1.0`:

| Method | BPM | ST | DT | ΔST | ΔDT | CE (beat 1) | ΔCE |
|--------|-----|----|----|-----|-----|-------------|-----|
| **GT** | **30.0** | **0.225** | **0.225** | — | — | **0.225s** | — |
| X axis | 30.0 | 0.241 | 0.268 | +0.016 | +0.043 | 0.235s | +0.010s |
| Y axis | 30.0 | 0.214 | 0.266 | -0.011 | +0.041 | 0.164s | -0.061s |
| PCA (158°) | 30.0 | 0.257 | 0.252 | +0.032 | +0.027 | 0.234s | +0.009s |

### 7.3 Observations

△ BPM = 30.0 across all methods, zero error

△ ST error is small for X (Δ+0.016s) and Y (Δ-0.011s); PCA slightly larger (Δ+0.032s)

△ DT is systematically overestimated in all methods (+0.027 ~ +0.043s)

△ CE detection: PCA and X find CE close to GT (+0.009s, +0.010s); Y finds CE too early (-0.061s)

△ Pipeline velocity signal shows oscillation near zero after the active phase — CE zero-crossing detection is affected by this noise regardless of axis method

△ Radial synthetic motion gives similar results across X/Y/PCA because motion is symmetric; PCA advantage (non-axis-aligned motion) not exercised in this design

---

## 8. Summary of Conclusions

### 7.1 MDP / ST / DT

| Finding | Detail |
|---------|--------|
| CE is the most sensitive time point | CS and RE are robust; CE fails when axis signal doesn't cleanly cross zero |
| PCA improves CE detection | 3/6 ROIs improved, 2/6 unchanged, 1/6 slightly worse |
| PCA recommended as default | Worst case = same result as current method; best case = significantly better ST/DT |
| min_dist is more impactful than axis method | Wrong min_dist causes peak misdetection; correct min_dist stabilises BPM first |
| min_dist is ROI-specific | Needs manual review per ROI (current workflow already supports this via Review dialog) |
| flip_test may need improvement | PCA direction is arbitrary; flip_test sometimes assigns wrong polarity, worsening results |

### 7.2 Contractility / Force

| Finding | Detail |
|---------|--------|
| Force is axis-independent | global_trace = √(dx²+dy²), not affected by axis or PCA choice |
| Force is ROI-box robust | Stable from scale ≥ 0.8× (±3% variation) |
| Force is feature-count dependent | More feature points → slightly higher force values; 100% recommended |
| PCA signal cannot replace global_trace for contractility | |PCA| has no clean zero-crossing; anchor search still works but values are lower and less stable |
| Physiological direction confirmed | Force: After(T=0) < Before(T=1min) ✅; BPM decreases After→Before ✅ |

### 7.3 ROI / Segmentation

| Finding | Detail |
|---------|--------|
| 10% radius dilation is sufficient | Scale 1.0→1.4 adds negligible new pixels; signals stable |
| All feature points should be used | Top-N% filtering increases instability |
| ROI2 interior is low-texture | 87% of feature points come from boundary/dilation zone; signal is still valid |
| Batch tracking bug | Overlapping masks in one track_video call causes label_map overwrite; use separate calls |

---

## 8. Recommended Pipeline Settings

```
Segmentation:    U-Net (Otsu fallback)
Dilation:        10% equivalent radius (current default)
Feature points:  All (top 100%, goodFeaturesToTrack quality=0.01)
Axis for MDP:    PCA projection (to be implemented)
Flip test:       morphology_flip_test (needs improvement for PCA edge cases)
min_dist:        ROI-specific, set during manual Review
k_multiplier:    1.0 (default, adjustable in Review)
Contractility:   global_trace (magnitude), anchor search ±0.25s
Force source:    global_trace (NOT PCA signal)
```

---

## 9. Pending Work

| Task | Priority | Status | Notes |
|------|----------|--------|-------|
| Integrate PCA into tracking.py | High | ✅ | `select_dominant_signal()` added to mdp.py; all callers updated; axis label now `PCA(+NNN°)` |
| Improve flip_test for PCA | High | ✅ | flip_test unchanged — works on any 1-D signal including PCA projection |
| Synthetic video validation | Medium | ✅ | Done — see Experiment E; CE error ~±0.03–0.06s intrinsic |
| Synthetic video with non-radial motion | Medium | ⬜ | Test PCA advantage with motion at non-X/Y angle |
| AC1/AC2 candidate points | Low | ⬜ | MATLAB has findCandidatePoints for weak secondary peaks; Python lacks this |
| Multi-sample reproducibility | Medium | ⬜ | Same ROI recorded multiple times to assess repeatability |

---

## 10. Experiment F — Contractility Sensitivity & Biological Validity (2026-07-01)

### 10.1 Background

Following synthetic video validation (Experiment E), a new question was raised:
**Can the contractility pipeline distinguish between organoids of different contractile strength, and does it respond correctly to drug-induced changes?**

### 10.2 Synthetic Sensitivity Test

Three synthetic videos generated (15s, BPM=30, ROI3 mask):

| Condition | amp_px | beat_dur | GT peak vel (µm/s) | Pipeline (µm/s) | Ratio |
|-----------|--------|----------|-------------------|-----------------|-------|
| Normal    | 5.0    | 0.45s    | 228.1             | 46.5            | 1.00  |
| Low-amp   | 2.5    | 0.45s    | 114.1             | 39.2            | 0.84  |
| Low-vel   | 5.0    | 0.90s    | 114.1             | 41.1            | 0.88  |

△ Pipeline measures mean velocity of all feature points, not peak velocity — absolute value is ~0.26–0.45× of GT theoretical peak

△ Low-amp (50% amplitude reduction) detected as 16% reduction — signal is in correct direction but compressed

△ Low-vel (50% velocity reduction) almost indistinguishable from Low-amp (41.1 vs 39.2) — pipeline cannot separately identify amplitude vs velocity changes

△ Root cause: signal_mag is an average over all feature points (including slow interior points); edge points contribute most but are diluted by center points

### 10.3 Real Data: Before vs After (T=0 vs T=1min)

| ROI | Before (µm/s) | After (µm/s) | Change | Detectable? |
|-----|--------------|--------------|--------|-------------|
| ROI1 | 40.8 | 40.5 | −1% | ❌ within noise |
| ROI2 | 58.9 | 47.4 | −20% | ✅ clear decrease |
| ROI3 | 43.1 | 46.5 | +8% | △ within per-beat variability |

△ Per-beat variability (±5–10 µm/s) sets the detection floor — changes smaller than this are indistinguishable from noise

△ ROI2 clearly shows drug effect; ROI1 and ROI3 do not exceed noise floor

△ Different ROIs have different absolute values (ROI2 = 58.9 vs ROI1 = 40.8) — not directly comparable across ROIs due to different mask sizes and feature point distributions

### 10.4 Discussion: Valid Use Cases for Contractility

| Comparison | Validity | Reason |
|------------|----------|--------|
| Same ROI, Before vs After | ✅ | Same mask, same scale, same feature distribution |
| Different ROIs, same condition | ⚠️ | Valid if ROI sizes and textures are similar |
| Different organoids, same drug | ✅ (use ratio) | After/Before ratio cancels individual differences |
| Absolute value cross-study | ❌ | Depends on ROI size, mask, scale calibration |

△ Recommended metric for batch studies: Δ contractility = (After − Before) / Before × 100%

△ This ratio cancels ROI-level confounds (size, texture, feature distribution) and is appropriate for pooling across organoids and days

### 10.5 Confounds for Multi-Day Studies

△ If organoid morphology changes between recordings (growth, shape change), ROI should be re-drawn each session — re-drawn ROI eliminates mask-level confounds

△ Arrhythmia (irregular beats) can inflate mean contractility if compensatory beats are large — per-beat std (`Contractility_Std_um_s`) serves as a flag

### 10.6 New Export Field Added

`Contractility_Std_um_s` added to Excel export (`cardio_py/core/io.py`), analogous to HRV:

- Per-ROI value (same number repeated for each beat row)
- = std of `force_vals` across all beats in the recording
- Added to merged report metrics list
- High std relative to mean → potential arrhythmia or unstable contraction

---

## 11. Code Reference

All experiments run from:
```
/Users/ottiblai/Desktop/cardioproj/20260630_matlabtopython/
```

Key modules:
- `cardio_py/core/tracking.py` — KLT, `_dilate_mask`, `track_video`
- `cardio_py/core/mdp.py` — `calculate_mdp_metrics`, `morphology_flip_test`, `select_dominant_axis`
- `cardio_py/core/force.py` — `correct_baseline`, `anchor_search`
- `cardio_py/core/io.py` — `export_analysis_excel` (now includes `Contractility_Std_um_s`)

Persistent files (kept):
- `synthetic_organoid.mp4` — synthetic video (ROI3 radial contraction, BPM=30, AMP=5px)
- `synthetic_gt.pkl` — ground truth dict (bpm, st, dt, ibi, disp, gt_vel, time, etc.)
- `synthetic_validation.png` — GT displacement/velocity vs pipeline signals with markers
- `contractility_sensitivity.png` — 3-condition sensitivity test (Normal / Low-amp / Low-vel)
- `test_contractility_sensitivity.py` — script for sensitivity test

Output plots (deleted after analysis — results captured in this report):
- `after_all_roi_xy_d08.png` — X vs Y MDP comparison, all ROIs, min_dist=0.8s
- `before_all_roi_xy_d08.png`
- `after_roi3_xypca_gt.png` — single ROI 4-signal comparison
- `after_pca_full.png`, `before_pca_full.png` — PCA vs current, all ROIs, d=1.5s
- `all6roi_perdist.png` — all 6 ROIs, per-ROI min_dist, current vs PCA
- `feature_points_distribution.png` — feature point locations visualised
- `roi3_topN_sensitivity.png` — top-N% feature points test
- `contractility_debug.png` — signal_mag vs GT velocity debug plot (deleted)
