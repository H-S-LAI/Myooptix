# MyoOptix — Windows Porting Guide

This document is for the agent continuing work on a Windows machine.
The goal is: (1) get the app running on Windows, (2) fix any UI layout issues, (3) package it as a standalone `.exe`.

---

## Project Background

MyoOptix is a PyQt6 desktop app for cardiac organoid video analysis, migrated from MATLAB to Python.
The active app is under `myooptix_app/`. Core algorithms are in `cardio_py/core/`.

### Key files
- `myooptix_app/main.py` — entry point
- `myooptix_app/ui/style.py` — all QSS styling (font, colors, layout)
- `myooptix_app/ui/dialog_new_project.py` — New Project dialog
- `myooptix_app/ui/dialog_open_project.py` — Open Project dialog (recent projects list)
- `cardio_py/core/mdp.py` — MDP peak detection + PCA axis selection
- `cardio_py/core/tracking.py` — KLT optical flow
- `cardio_py/core/force.py` — contractility / anchor search
- `cardio_py/core/segmentation.py` — Otsu + U-Net segmentation
- `annotation_tool/best_model.pth` — U-Net weights (required at runtime)

### Python environment (Windows)
The Mac `.venv/` uses Unix binaries and does NOT work on Windows.
A separate Windows venv is at `.venv_win/`.

To recreate it:
```
python -m venv .venv_win
.venv_win\Scripts\activate
pip install PyQt6 opencv-python numpy scipy pandas openpyxl scikit-image segmentation-models-pytorch torch matplotlib
```

### Running the app
Double-click `啟動 MyoOptix.bat` in the project root, or:
```
cd myooptix_app
..\\.venv_win\Scripts\python.exe main.py
```

---

## What was completed on Windows (2026-07-02)

### Step 1 — Environment ✅
- Created `.venv_win` with Python 3.13.6 (system Python)
- Installed all packages; torch 2.12.1+cpu pulled in automatically via segmentation-models-pytorch

### Step 2 — UI fixes ✅

**DPI scaling** (`main.py`):
```python
import os
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
```
Added before `QApplication` creation to prevent blurry/oversized widgets on 125%/150% displays.

**Radio button indicators invisible** (`ui/style.py`):
On Windows, `QWidget { background-color }` in global QSS wipes out the native radio button indicator circles. Fixed by adding explicit `QRadioButton::indicator` styles:
```css
QRadioButton::indicator { width: 14px; height: 14px; border-radius: 7px; ... }
QRadioButton::indicator:checked { background-color: #7c9c6e; }
```

**macOS hidden files in video list** (`cardio_py/core/io.py`):
`._3.mov`, `._synthetic_organoid.mp4` etc. were showing in the dashboard. Fixed in `scan_video_folder` — skip any file whose name starts with `._`.

### Step 3 — UX improvements ✅

**Launch shortcut** — `啟動 MyoOptix.bat` created at project root (same as Mac's `.command`).

**New Project dialog** (`ui/dialog_new_project.py`):
- Removed the separate "Video root" field in Auto scan mode — save location is now used as the video root automatically (they are always the same folder in practice)
- Project name auto-fills as `project_{folder_name}_{date}` when the user picks a save location (via Browse or by typing)

**Open Project dialog** (`ui/dialog_open_project.py`):
- Replaced drag-and-drop text field with a 2-column `QTreeWidget` showing **Project name** | **Location (root path)**
- Stale paths (no longer on this machine) are auto-removed from the list on open and saved back to config
- Browse button remains for projects not in the list

**Config format** (`main.py`):
- Changed from `{"last_project": "..."}` to `{"recent_projects": ["...", "..."]}` (up to 8 entries, most recent first)
- Backward compatible: old `last_project` key is read on first launch and migrated

### Step 4 — Cross-platform output validation ✅

Compared Windows output vs Mac output of same code (same videos, `Analysis_20260702` vs `project_20260630_matlabtopython_20260702`):

| Metric | Status |
|--------|--------|
| BPM, IBI_avg, HRV | Identical or < 0.003 difference |
| ST_s, DT_s | Within 0.01–0.15 s (floating point) |
| Contractility_Mag_um_s (mean per ROI) | Within **2.5%** |
| PeakHeight | Different by design — PCA angle varies 1–3° between platforms due to OpenCV float differences |

**Known edge case — Before_1 ROI 3:**
Mac detected 19 beats, Windows detected 18. Mac found one extra boundary beat at t=0.300s (start of video). This shifts BPM by 0.54 (34.15 vs 34.69, ~1.6%) and IBI_avg by 0.027 s. Not a bug — borderline case where PCA angle difference (99° vs 96°) causes one platform to detect a partial beat at the video edge. Mean Contractility for this ROI differs by 2.0 µm/s (2.5%).

---

## Step 3 — Packaging (TODO)

**Decision pending:** before packaging, need to decide on update strategy:
- **Option A**: distribute folder + `.bat`, update via git pull script (lightweight, recommended for lab use)
- **Option B**: PyInstaller standalone `.exe` (good for non-technical users, updates require full re-package ~1.5 GB)
- **Option C**: PyInstaller + GitHub Releases auto-updater (best long-term, most complex to build)

When ready to package with PyInstaller:
```
pip install pyinstaller
cd myooptix_app
pyinstaller myooptix.spec
```

Use a `.spec` file (not ready yet — create before packaging):
```python
a = Analysis(
    ['main.py'],
    datas=[
        ('../annotation_tool/best_model.pth', 'annotation_tool'),
        ('assets/', 'assets/'),
    ],
    hiddenimports=['segmentation_models_pytorch', 'timm'],
)
```

Known issues to handle:
- No `.ico` icon file yet (only `assets/heart.svg`) — convert to `.ico` before packaging
- `cv2` may need explicit DLL inclusion
- `torch` is ~1.5 GB in the bundle; confirm CPU-only version is installed

---

## What is already done (do not redo)

- PCA-based axis selection (replaces X/Y best-axis): `mdp.py` → `select_dominant_signal()`
- Contractility Std metric added to Excel exports and Review panel
- Scale (µm/px) now saved/loaded from `compute_settings.json` per project
- Close guard on ReviewDialog (prompts if not exported)
- All callers updated to use `select_dominant_signal`
- Windows venv at `.venv_win/` (do not delete)
- DPI fix and radio button fix already in code

## Known non-issues (intentional differences from MATLAB)

- PCA projection is Python-only; MATLAB used X/Y axis selection — this is intentional
- Baseline correction uses centered movmin (Python) vs trailing (MATLAB) — Before/After ratio cancels this out
- `Contractility_Std_um_s` column does not exist in MATLAB output — Python adds it
- Cross-platform Contractility difference ≤ 2.5% is normal (OpenCV float behavior)

---

## Contact / reference

User email: b101110099@tmu.edu.tw
MATLAB source (reference only, do not modify): `202260413_7.6.0_Bugfix/`
Golden standard data: `golden_standard.mat`, `golden_tracking.mat`
