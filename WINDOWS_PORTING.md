# MyoOptix — Windows Porting & Packaging Guide

This document records everything done on the Windows machine (2026-07-02) and what to do next.

---

## Project Background

MyoOptix is a PyQt6 desktop app for cardiac organoid video analysis, migrated from MATLAB to Python.
- Active app: `myooptix_app/`
- Core algorithms: `cardio_py/core/`
- GitHub repo: `https://github.com/H-S-LAI/Myooptix` (public)
- Clean repo folder on this machine: `C:\Users\LAI\Desktop\myooptix\`
- Development folder (venv, MATLAB source, test data): `C:\Users\LAI\Desktop\20260630_matlabtopython\`

---

## Environment

### Windows venv
The Mac `.venv/` has Unix binaries and does **not** work on Windows.
The Windows venv is at `C:\Users\LAI\Desktop\20260630_matlabtopython\.venv_win\`.

To recreate from scratch:
```
python -m venv .venv_win
.venv_win\Scripts\activate
pip install PyQt6 opencv-python numpy scipy pandas openpyxl scikit-image segmentation-models-pytorch torch matplotlib pyinstaller
```

Installed versions (2026-07-02): Python 3.13.6, torch 2.12.1+cpu (CPU-only, important for bundle size).

### Running from source
```
cd C:\Users\LAI\Desktop\20260630_matlabtopython\myooptix_app
..\\.venv_win\Scripts\python.exe main.py
```
Or double-click `啟動 MyoOptix.bat` in the repo root (opens the clean repo's app using the dev venv).

---

## What Was Done (2026-07-02)

### 1 — Windows UI Fixes ✅

**DPI scaling** (`main.py` line 7):
```python
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
```
Prevents blurry/oversized widgets at 125%/150% display scaling.

**Radio button indicators invisible** (`ui/style.py`):
On Windows, `QWidget { background-color }` in global QSS suppresses native radio button circles.
Fixed with explicit `QRadioButton::indicator` CSS block.

**macOS hidden files in video list** (`cardio_py/core/io.py`):
`._3.mov`, `._synthetic_organoid.mp4` were appearing in the dashboard.
Fixed: `scan_video_folder` now skips any filename starting with `._`.

### 2 — UX Improvements ✅

**New Project dialog** (`ui/dialog_new_project.py`):
- Removed separate "Video root" field — in Auto scan mode, save folder = video root (always true in practice)
- Project name auto-fills as `project_{folder_name}_{YYYYMMDD}` when user picks a save location

**Open Project dialog** (`ui/dialog_open_project.py`):
- Replaced drag-and-drop field with 2-column `QTreeWidget`: **Project name** | **Location**
- Stale paths are auto-removed on open and saved back to `config.json`
- Browse button retained for unlisted projects

**Config format** (`main.py`):
- `config.json` now stores `{"recent_projects": [...]}` (up to 8 entries, most recent first)
- Backward compatible with old `{"last_project": "..."}` format

**Launch shortcut** — `啟動 MyoOptix.bat` at repo root (Windows equivalent of Mac's `.command`).

### 3 — Cross-Platform Output Validation ✅

Compared Windows vs Mac output (same videos, same code):

| Metric | Result |
|--------|--------|
| BPM, IBI_avg, HRV | Identical or < 0.003 difference |
| ST_s, DT_s | Within 0.01–0.15 s (floating point) |
| Contractility_Mag_um_s (mean per ROI) | Within **2.5%** |
| PeakHeight | Intentionally different — PCA angle varies 1–3° across platforms |

**Known edge case — Before_1 ROI 3:**
Mac found 19 beats, Windows found 18. One extra boundary beat at t=0.300 s due to PCA angle difference (99° vs 96°). BPM difference 0.54 (~1.6%), Contractility difference 2.0 µm/s (2.5%). Not a bug.

### 4 — Auto-Update & Model Download ✅

New files added to repo:

**`myooptix_app/updater.py`**
- `weights_exist()` — checks if `annotation_tool/best_model.pth` is present
- `check_for_update(version)` — queries GitHub Releases API, returns new version info or None
- `download_weights(progress_cb)` — downloads `best_model.pth` from `model-weights` release
- Path logic handles both source-run and frozen (PyInstaller) exe correctly

**`myooptix_app/ui/dialog_update.py`**
- `ModelDownloadDialog` — shown at startup if `best_model.pth` is missing; has progress bar
- `UpdateAvailableDialog` — shown by Help → Check for Updates; opens browser to release page

**`myooptix_app/ui/main_window.py`** — Help menu added:
- Help → Check for Updates (background thread, non-blocking)
- Help → About (shows version + git hash when running from source)

**`main.py`** — checks for weights before showing Welcome dialog; shows download dialog if missing.

### 5 — Version System ✅

**`version.py`** (repo root):
```python
VERSION = "0.1.0"

def get_version_string() -> str:
    # Returns "0.1.0 (abc1234)" from source, "0.1.0" from frozen exe
```

- Change only `VERSION` when releasing a new version
- About dialog shows git hash automatically when running from source (useful for debugging which exact commit is running)
- Frozen exe shows bare version (no git available inside bundle)

### 6 — PyInstaller Packaging ✅

**Spec file**: `myooptix_app/myooptix.spec`

Build command (run from `myooptix_app/`):
```
.venv_win\Scripts\pyinstaller.exe myooptix.spec
```

Build result: `myooptix_app/dist/MyoOptix/` — 786 MB folder, 3913 files.
Largest components: `torch_cpu.dll` 293 MB, `cv2.pyd` 82 MB.

**What is bundled:** Python 3.13 runtime, PyQt6, torch (CPU-only), OpenCV, scipy, numpy, pandas, skimage, segmentation-models-pytorch, timm, matplotlib, cardio_py, all UI modules.

**What is NOT bundled:** `annotation_tool/best_model.pth` (downloaded at runtime from GitHub Releases).

**Frozen path logic** (`segmentation.py`, `updater.py`):
```python
if getattr(sys, "frozen", False):
    base = Path(sys.executable).parent   # next to the .exe
else:
    base = Path(__file__).parent.parent.parent  # repo root
```

**Test result:** exe ran successfully from an isolated folder with `PYTHONPATH=""` and `PYTHONHOME=""` — confirmed no Python installation required on target machine.

Distribution zip: `MyoOptix_v0.1.0_Windows.zip` — 292 MB.

### 7 — GitHub Releases ✅

Repository: `https://github.com/H-S-LAI/Myooptix` (public)

| Tag | Asset | Size | Purpose |
|-----|-------|------|---------|
| `model-weights` | `best_model.pth` | 93 MB | Auto-downloaded by app on first launch |
| `v0.1.0` | `MyoOptix_v0.1.0_Windows.zip` | 292 MB | Distributed to lab members |

**End-user install steps (no Python needed):**
1. Download `MyoOptix_v0.1.0_Windows.zip` from GitHub Releases
2. Extract anywhere
3. Double-click `MyoOptix.exe`
4. First launch: click Download to fetch model weights (~93 MB, one-time)
5. Done

---

## How to Release a New Version

1. Make code changes, test
2. Update `VERSION = "x.y.z"` in `version.py`
3. `git add . && git commit -m "release: vx.y.z" && git push`
4. Re-run PyInstaller: `.venv_win\Scripts\pyinstaller.exe myooptix_app\myooptix.spec`
5. Zip the dist: `Compress-Archive dist\MyoOptix MyoOptix_vx.y.z_Windows.zip`
6. GitHub → New Release → tag `vx.y.z` → upload zip
7. App's Help → Check for Updates will detect the new tag and prompt users

---

## Pending / Recommended Next Steps

### High priority

**① Demo / self-test button**
Add a "Run Demo Test" button (Welcome screen or Help menu) that:
- Loads `demo/Before_1.mp4` (needs to be added to `.spec` datas)
- Runs Quick Analysis with default params on ROI 1
- Shows result — confirms the exe is working correctly on a new machine
- `demo/Before_1.mp4` is already in the repo (4.7 MB, 960×540)

**② Mac `.app` packaging**
On the Mac, run PyInstaller with an equivalent spec:
```
pip install pyinstaller
cd myooptix_app
pyinstaller myooptix.spec
```
Produce `MyoOptix_v0.1.0_Mac.zip` and upload to the same v0.1.0 Release.
The spec's `datas` and `pathex` are already cross-platform — only the output exe name differs.

### Lower priority

**③ App icon (.ico)**
Only `assets/heart.svg` exists. Convert to `.ico` (256×256) and set `icon=` in the spec before next packaging run. Tools: `cairosvg` + `Pillow`, or an online SVG-to-ICO converter.

**④ Installer (optional)**
For a more polished distribution, wrap the dist folder with NSIS or Inno Setup to create a proper Windows installer with Start Menu shortcut and uninstaller. Only needed if lab members find the "extract and run" approach confusing.

**⑤ Automated build (optional)**
Add a GitHub Actions workflow (`.github/workflows/build.yml`) that builds the exe automatically on each push to `main`, so you don't have to rebuild manually on every release.

---

## Known Non-Issues (Intentional Differences from MATLAB)

- PCA projection is Python-only; MATLAB used X/Y axis selection — intentional
- Baseline correction uses centered movmin (Python) vs trailing (MATLAB) — Before/After ratio cancels this out
- `Contractility_Std_um_s` column does not exist in MATLAB output — Python adds it
- Cross-platform Contractility difference ≤ 2.5% is normal (OpenCV float behavior)
- `tensorboard` not installed — PyInstaller warning is harmless

---

## Contact / Reference

- User email: b101110099@tmu.edu.tw
- MATLAB source (reference only, do not modify): `202260413_7.6.0_Bugfix/`
- Golden standard data: `golden_standard.mat`, `golden_tracking.mat`
- GitHub repo: `https://github.com/H-S-LAI/Myooptix`
