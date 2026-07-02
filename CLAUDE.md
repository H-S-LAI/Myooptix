# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MyoOptix — cardiac organoid video analysis tool migrated from MATLAB to Python.
Active app is a PyQt6 desktop app under `myooptix_app/`. Core algorithms are in `cardio_py/core/`.
MATLAB source (reference only) lives under `202260413_7.6.0_Bugfix/`.

## Folder Structure

```
20260630_matlabtopython/
├── myooptix_app/          ← Active PyQt6 desktop app (main development)
│   ├── main.py            ← Entry point
│   ├── assets/
│   └── ui/
│       ├── style.py
│       ├── main_window.py
│       ├── tab_dashboard.py
│       ├── dialog_welcome.py
│       ├── dialog_quick.py    ← Quick Analysis (single video, no project)
│       ├── dialog_compute.py
│       ├── dialog_review.py
│       ├── dialog_new_project.py
│       ├── dialog_open_project.py
│       ├── dialog_project.py
│       ├── dialog_import.py
│       └── worker_compute.py
├── cardio_py/             ← Core algorithms (shared by app and validation)
│   ├── core/
│   │   ├── mdp.py         ← MDP peak detection, flip test, CS/CE/RE
│   │   ├── tracking.py    ← KLT optical flow
│   │   ├── force.py       ← Contractility / anchor search
│   │   ├── segmentation.py← Otsu + U-Net segmentation
│   │   ├── io.py          ← Video scan, Excel export
│   │   └── roi_selector.py← OpenCV interactive ROI drawing
│   └── tests/             ← Validation scripts against golden_standard.mat
├── annotation_tool/       ← U-Net training tool (done, best_model.pth ready)
├── 202260413_7.6.0_Bugfix/← MATLAB source (reference only, do not modify)
├── Ctrl/                  ← Test video data (After/Before folders)
├── Analysis_20260630/     ← Test project folder for benchmarking
├── golden_standard.mat    ← Golden data for algorithm validation
├── golden_tracking.mat
├── _archive/              ← Deprecated code (Streamlit app, old pages)
└── 啟動 MyoOptix.command  ← Launch script
```

## Running the PyQt6 App

```bash
source .venv/bin/activate
cd myooptix_app
python main.py
```

## Validation Scripts

Run against `golden_standard.mat` to verify algorithm correctness after changes:

```bash
source .venv/bin/activate
python cardio_py/tests/validate_mdp.py       # MDP peaks, ST, DT, IBI
python cardio_py/tests/validate_tracking.py  # KLT tracking → HR, IBI, Force
python cardio_py/tests/validate_force.py     # Anchor search contractility
```

## Running the MATLAB App (reference)

```matlab
ProjectDashboard_v1      % main GUI
Diagnose_Environment_v1  % check required toolboxes
```

Required toolboxes: Image Processing, Computer Vision, Deep Learning (U-Net; Otsu fallback), Parallel Computing (`parfor`), Statistics and Machine Learning.

## Data Flow

```
Video files  →  segmentation.py  →  binary masks
                      ↓
              tracking.py        →  TrackingResult (signal_x, signal_y, signal_mag)
                      ↓
              mdp.py             →  BeatMetrics (HR, peak_locs, CS, CE, RE, ST, DT, IBI)
                      ↓
              force.py           →  contractility dict (global_trace, force_vals, contractility_mag)
                      ↓
        {project}/_pkl_for_review/{stem}.pkl   ← serialised result
        {project}/_pkl_for_review/{stem}.json  ← sidecar: status field
                      ↓
        {project}/final_excel_exports/{stem}_analysis_results.xlsx
        {project}/final_excel_exports/{stem}_raw_data.xlsx
                      ↓
        {project}/_Merged_Reports/{name}.xlsx  ← Universal Results + Grouped by Time
```

Quick Analysis output goes to `{video_folder}/{video_stem}/` instead of a project folder.

## Core Algorithms (`cardio_py/core/`)

**`mdp.py`**
- `morphology_flip_test` — detects inverted waveform; flipped when left trough is closer than right trough to nearest positive peak
- `calculate_mdp_metrics` — flip test → `find_peaks` → `_dynamic_pairing` (CS/CE/RE via 5%-threshold sub-sample interpolation)
- `select_dominant_axis` — picks X or Y by lower IBI std
- `BeatMetrics.peak_locs` — **in seconds** (not sample index); `time[peak_idx]` at line 252

**`tracking.py`** — `cv2.calcOpticalFlowPyrLK` with bidirectional error check (max 2 px). Masks dilated ~10% equivalent radius. Output in µm/s.

**`force.py`** — `correct_baseline`: centered moving-min (1 s window). `anchor_search`: ±0.25 s around each MDP peak.

**`segmentation.py`** — Otsu: dark organoid on bright background, binarise → invert → fill holes → area filter. U-Net: `smp.Unet` ResNet-34, weights at `annotation_tool/best_model.pth`.

**`roi_selector.py`** — OpenCV interactive ROI drawing. Click top green bar (or press C) to confirm, right-click to delete a box, R to reset, Q to cancel.

## Computed Result Format (`.pkl`)

```python
{
  'video_path': str,
  'frame_rgb':  np.ndarray,   # first frame (H,W,3)
  'roi_list':   list[dict],
  'params':     {'k_mult', 'min_dist', 'scale_um_per_px'},
  'status':     'Computed' | 'Reviewed',
}
```
Each ROI dict: `roi_index`, `dominant_axis`, `signal_x`, `signal_y`, `signal`, `global_trace`, `time`, `frame_rate`, `mdp` (BeatMetrics), `force` (dict), `mask`, `k`, `d`.
Status transitions written to `.json` sidecar only — never re-pickle BeatMetrics.

## Key Constants

| Constant | Value | Location |
|---|---|---|
| `K_MULTIPLIER` | 1.0 | `calculate_mdp_metrics` default |
| `MIN_PEAK_DIST_SEC` | 0.2 s | `calculate_mdp_metrics` default |
| `pixelsToMicrons` | 10000/1530 | `ComputeDialog` / `dialog_quick.py` |
| Anchor search window | ±0.25 s | `force.py anchor_search` |
| KLT dilation | ~10% equivalent radius | `tracking.py _dilate_mask` |
| Baseline correction window | 1 s | `force.py correct_baseline` |
| Bidirectional error threshold | 2 px | `tracking.py track_video` |

## MATLAB → Python Equivalents

| MATLAB | Python |
|--------|--------|
| `VideoReader` / `readFrame` | `cv2.VideoCapture` |
| `vision.PointTracker` (KLT) | `cv2.calcOpticalFlowPyrLK` |
| `semanticseg` (U-Net) | `smp.Unet` ResNet-34 (retrained) |
| `findpeaks` | `scipy.signal.find_peaks` |
| `bwareaopen`, `imdilate`, `bwlabel` | `skimage` / `cv2` |
| `uifigure` / `uiaxes` | PyQt6 |
| `writetable` | `pandas.DataFrame.to_excel` |
| `movmin` | centered sliding minimum loop |

## _archive/ Contents

| 項目 | 說明 |
|------|------|
| `app.py` | 舊 Streamlit 入口，已廢棄 |
| `Analysis_AAA/` | 舊測試專案資料夾 |
| `Analysis_Python/` | 舊測試專案資料夾 |
| `cardio_py_pages/` | 舊 Streamlit 頁面模組（_dashboard, _review, _compute, _report） |
