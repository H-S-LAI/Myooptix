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

## 2026-07-08 Mac — Welcome UI + min_dist + toast system

- `dialog_welcome.py`: subtitle font 11→14px, credit font 10→12px, window title cleared, size 440×420→520×460, credit split into 3 separate labels for clean alignment
- `cardio_py/core/mdp.py`: all 4 function defaults `min_peak_distance_sec` 0.2→0.7 s
- `myooptix_app/ui/tab_dashboard.py`: `min_dist` 0.2→0.7 in `_batch_compute`
- `myooptix_app/ui/dialog_quick.py`: `'d'` and `'min_dist'` 0.2→0.7 in roi dict + params
- `myooptix_app/ui/dialog_compute.py`: `min_dist` 0.2→0.7 in `_run()`

## 2026-07-08 Mac — v0.3.0 Features + Packaging

- Added `cardio_py/core/morphology.py`: `compute_mask_morphology()` computes equivalent diameter (µm) and area (µm²) from first-frame segmentation mask
- `cardio_py/core/io.py`: added `Equivalent_Diameter_um` column to Excel analysis export
- `cardio_py/core/mdp.py`: `min_peak_distance_sec` default 0.2 → 0.7 s
- `myooptix_app/ui/toast.py` (new): shared toast notification widget; `duration=0` for loading toasts (no animation, shows immediately even during main-thread work)
- Dashboard `refresh()` moved to `_ScanWorker` (QThread) — "Scanning…" toast now visible
- Review export moved to `_ExportWorker` (QThread) — "Exporting…" toast now visible
- `dialog_compute.py`: microscope presets (TCY_4X / TCY_10X), custom preset save, min_dist corrected to 0.7
- `dialog_welcome.py`: subtitle 14px, credit 12px, window title cleared, size 520×460
- `docs/index.html`: version badge updated to v0.3.0, Mac download link updated
- Built `MyoOptix_v0.3.0_Mac.zip` (841 MB) via `myooptix_mac.spec`
- Released: GitHub v0.3.0 tag, Mac ✅, Windows ⏳

## 2026-07-13 Mac — Collab Edition v1.0.0 (separate app, separate server)

**新增獨立的 Collab Edition，供外部研究者申請使用。Windows 需另行打包（見下方 Windows 打包說明）。**

### 架構概覽
- **Server**: `20260712_myooptix_collab_server/` — FastAPI + Railway + PostgreSQL
  - `main.py` — API server（register/login/verify/admin endpoints）
  - `static/admin.html` — 管理後台（https://pleasant-miracle-production-95c3.up.railway.app/web/admin.html）
- **App**: `20260712_myooptix_collab_server/app/` — 獨立 PyQt6 app
  - `main.py` — entry point（token verify → login → QuickAnalysis）
  - `ui/dialog_login.py` — 登入畫面（含 icon.png + credit）
  - `ui/dialog_register.py` — 申請帳號
  - `ui/dialog_quick.py` — Quick Analysis（含網路監控每 10 秒 verify）
  - `ui/dialog_review.py` — Review
  - `api_client.py` — HTTP wrapper
  - `token_store.py` — 本地 token 存取
  - `assets/icon.png` — MyoOptix logo（從主版複製）
  - `assets/model/best_model.pth` — U-Net 模型
  - `myooptix_collab_mac.spec` — Mac PyInstaller spec

### Mac 打包
```bash
cd 20260712_myooptix_collab_server/app
source ../../20260630_matlabtopython/.venv/bin/activate
pyinstaller myooptix_collab_mac.spec --noconfirm
# → dist/MyoOptix.app
```

### Windows 打包（待完成）
- 需要在 Windows 建立獨立 venv（同主版環境）
- 建立 `myooptix_collab_win.spec`（參考主版 `myooptix.spec`，但 pathex 指向 `app/`）
- 輸出命名：`MyoOptix-collab-v1.0.0-win.zip`
- 上傳至 GitHub release `collab-v1.0.0`，檔名：`MyoOptix-collab-v1.0.0-win.zip`
- 上傳完通知 Mac 更新 `docs/index.html` Windows 下載連結

### 已完成
- Mac v1.0.0 打包 → 上傳至 GitHub `collab-v1.0.0` release
- `myooptix.com` 首頁 Mac 下載連結已更新
- Admin 後台：approve/reject/suspend/activate/新增/刪除使用者/清除 rejected requests
- 網路斷線監控：10 秒 verify 一次，斷線鎖定 Run 按鈕並顯示紅色 banner

---

## 2026-07-12 Windows — v0.3.1 code review + Quick Analysis preset + Windows packaging

- Pulled Mac v0.3.0 commits (morphology, toast, presets, PCA, UI polish)
- Fixed `toast.py`: `close()` crashed when `self._anim is None` (duration=0 toast) — changed `hasattr` check to `is not None`
- Added microscope preset dropdown to `dialog_quick.py` (was hardcoded TCY_4X 2.915 µm/px) — now reads `presets.json`, passes selected scale to worker
- Bumped version to v0.3.1 (Windows-side fixes warrant a patch bump)
- Built `MyoOptix-win.zip` via `myooptix.spec` — uploaded to GitHub v0.3.1 release

## 2026-07-02 Mac — Algorithm + Analysis

- Integrated PCA as default axis selection (`mdp.py`: `select_dominant_signal()`)
- Added `Contractility_Std_um_s` to Excel exports and Review panel beat metrics
- Removed IBI from Review beat metrics panel
- Fixed scale (µm/px) not loading from `compute_settings.json` in dashboard
- Added close guard on ReviewDialog (prompts if not exported)
- Updated all callers to use `select_dominant_signal` (worker, review, quick, validate scripts)
- Ran Before/After analysis on `Analysis_20260702` — pipeline confirmed working
- Verified PCA angle stability: ROI shift ±20% → angle change ±10° (acceptable)
