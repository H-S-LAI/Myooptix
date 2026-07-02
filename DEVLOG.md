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

## 2026-07-02 Mac — Auto-update + Packaging

- Built `MyoOptix.app` with PyInstaller (`myooptix_mac.spec`) — 791 MB
- Added `download_app_update()` to `updater.py`: downloads platform zip to Desktop
- `dialog_update.py`: UpdateAvailableDialog now auto-downloads instead of opening browser
- `main.py`: checks for update on every launch (silent if no network, timeout 5s)
- Update flow: launch → detect new version → Download button → zip saved to Desktop → user replaces old .app

## 2026-07-02 Windows — Sync Mac changes + Windows fix

- Pulled Mac commits (3 new: `download_app_update`, startup update check, `myooptix_mac.spec`)
- No merge conflicts — fast-forward clean
- Fixed `dialog_update.py`: `_on_finished` was Mac-only (Finder reveal + `.app` wording)
  - Added Windows branch: `explorer /select,<path>` reveal + "replace the old MyoOptix folder / run MyoOptix.exe" instructions
- **Asset naming note for future releases**: `updater.py` now expects `MyoOptix-win.zip` (Windows) and `MyoOptix-mac.zip` (Mac) — old `MyoOptix_v0.1.0_Windows.zip` naming is deprecated; next release must use the new names
- Pushed: commit `18ee392`

## 2026-07-02 Mac — Algorithm + Analysis

- Integrated PCA as default axis selection (`mdp.py`: `select_dominant_signal()`)
- Added `Contractility_Std_um_s` to Excel exports and Review panel beat metrics
- Removed IBI from Review beat metrics panel
- Fixed scale (µm/px) not loading from `compute_settings.json` in dashboard
- Added close guard on ReviewDialog (prompts if not exported)
- Updated all callers to use `select_dominant_signal` (worker, review, quick, validate scripts)
- Ran Before/After analysis on `Analysis_20260702` — pipeline confirmed working
- Verified PCA angle stability: ROI shift ±20% → angle change ±10° (acceptable)
