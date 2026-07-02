# MyoOptix — Dev Log

Cross-platform development log. Both Mac and Windows agents should append here when making significant changes.
Format: `## [date] [platform] — summary`, then bullet points.
After appending, commit and push so the other side can pull and see.

---

## 2026-07-02 Windows — Environment + UI + Packaging prep

- Created `.venv_win` (Python 3.13.6, torch CPU)
- Fixed radio button indicators invisible on Windows (`style.py`)
- Added DPI scaling fix (`main.py`: `QT_AUTO_SCREEN_SCALE_FACTOR=1`)
- Fixed macOS hidden files (`._*.mov`) appearing in video list (`io.py`)
- Simplified New Project dialog: auto-fills project name, removed separate video root field
- Replaced Open Project text field with 2-column recent projects tree
- Config format changed: `last_project` → `recent_projects` list (max 8)
- Added `updater.py` + `dialog_update.py`: GitHub Releases weight download + update check
- Created `啟動 MyoOptix.bat` launch shortcut
- Created `myooptix.spec` (PyInstaller spec, not yet tested)
- Validated cross-platform output: BPM/HRV identical, Contractility ≤2.5% diff (normal)

## 2026-07-02 Mac — Algorithm + Analysis

- Integrated PCA as default axis selection (`mdp.py`: `select_dominant_signal()`)
- Added `Contractility_Std_um_s` to Excel exports and Review panel beat metrics
- Removed IBI from Review beat metrics panel
- Fixed scale (µm/px) not loading from `compute_settings.json` in dashboard
- Added close guard on ReviewDialog (prompts if not exported)
- Updated all callers to use `select_dominant_signal` (worker, review, quick, validate scripts)
- Ran Before/After analysis on `Analysis_20260702` — pipeline confirmed working
- Verified PCA angle stability: ROI shift ±20% → angle change ±10° (acceptable)
