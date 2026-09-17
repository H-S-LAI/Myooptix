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

### Windows 交接
`git pull`，然後照下方 Windows 打包說明做。`collab_server/app/` 就是要打包的資料夾，先把 `myooptix_app/assets/icon.png` 複製到 `collab_server/app/assets/`。

### Windows 打包（待完成）
- 需要在 Windows 建立獨立 venv（同主版環境）
- 建立 `myooptix_collab_win.spec`（參考主版 `myooptix.spec`，但 pathex 指向 `app/`）
- 輸出命名：`MyoOptix-collab-v1.0.0-win.zip`
- 上傳至 GitHub release `collab-v1.0.0`，檔名：`MyoOptix-collab-v1.0.0-win.zip`
- 上傳完通知 Mac 更新 `docs/index.html` Windows 下載連結

### 網站 & 基礎建設
- 購買 `myooptix.com` 域名，設定 Cloudflare DNS
- GitHub Pages 從 `docs/` 部署，custom domain `myooptix.com`（HTTPS）
- `myooptix.com` → collab 申請頁（`docs/index.html`）
- `myooptix.com/lab.html` → 主版下載頁（隱藏，不公開連結）
- Brevo 負責 transactional email，sender `noreply@myooptix.com`，DKIM/SPF 已驗證

### 已完成
- Mac v1.0.0 打包 → 上傳至 GitHub `collab-v1.0.0` release
- `myooptix.com` 首頁 Mac 下載連結已更新
- Admin 後台：approve/reject/suspend/activate/新增/刪除使用者/清除 rejected requests
- 網路斷線監控：10 秒 verify 一次，斷線鎖定 Run 按鈕並顯示紅色 banner

## 2026-07-15 Mac — v0.4.1 + Collab v1.1.0 Mac 打包完成

- `myooptix_mac.spec`：補上 `annotation_tool/best_model.pth` 到 datas（與 Windows spec 對齊），
  修正 `hooksconfig`、`bootloader_ignore_signals`、`upx_exclude` 欄位，版本號更新至 0.4.1
- `collab_server/app/myooptix_collab_mac.spec`：修正 `cardio_py` 路徑（改用 `REPO_ROOT`，
  原本錯誤指向 app 目錄），補上 `annotation_tool/best_model.pth`，版本號更新至 1.1.0
- 已上傳 GitHub Release：
  - `v0.4.1`：`MyoOptix-v0.4.1-mac.zip`（1.07 GB，含 model）
  - `collab-v1.1.0`：`MyoOptix-collab-v1.1.0-mac.zip`（1.19 GB，含 model）
- `docs/lab.html`：更新下載大小提示（Win ~400 MB / Mac ~1 GB）

## 2026-07-15 Windows — Collab Edition v1.1.0

- `collab_server/app/ui/dialog_quick.py`：新增顯微鏡 preset dropdown + Scale (µm/pixel) spinbox + "+ Save" 按鈕
  - Worker 的 scale 從 hardcode `2.915` 改為由 dialog 傳入
  - Preset 讀寫 `assets/presets.json`（與主版共用格式）
- 下次打包時 release tag 用 `collab-v1.1.0`（Windows + Mac 各自上傳後通知對方）

---

## 2026-07-15 Windows — v0.4.1 Update 通知版本比較修正

- `updater.py` `check_for_update`：版本比較從字串 `!=` 改為 semantic `>`
  （tuple 比較），避免本機版本比 GitHub 新時仍跳出 update dialog
- version: 0.4.0 → 0.4.1
- commit: 見下方 v0.4.0 後續

---

## 2026-07-15 Windows — v0.4.0 新功能 + Bug 修正

### 新功能
- **Quick Analysis 顯微鏡換算輸入**：新增 Scale (µm/pixel) spinbox + "+ Save" 按鈕，
  讓外部實驗室可以輸入自己的換算值並儲存為 preset（與 Batch Compute 一致）
- **Merge Report 新增 Equivalent Diameter**：`_Merged_Reports` 輸出現在包含 `Equivalent_Diameter_um` 欄位

### Bug 修正
- **App icon 修正**：`main_window.py` 硬寫 `heart.svg`，導致所有子 dialog（Batch Compute 等）
  顯示紅心而非 MyoOptix logo。改為優先讀 `icon.png`，fallback 才用 `heart.svg`
- `myooptix_app/assets/icon.png` 新增 logo 檔（從 `docs/icon.png` 複製）

### 打包注意
- 需重新打包 Windows v0.4.0 exe
- Mac 也需 pull 後重新打包（同樣有 icon + diameter 修正）

### commit: `289bce1`

---

## 2026-07-15 Windows — 跨版本 Bug 修正（v0.3.1 → 需重新打包）

### 問題根因
在乾淨 Windows 機器上測試 v0.3.1 時發現兩個 bug：

**Bug 1 — UNet model 找不到（FileNotFoundError）**
- 根本原因：PyInstaller 6.x 新增 `_internal/` 目錄，導致 `segmentation.py` 的
  `Path(__file__).parent.parent.parent` 解析到 `_internal/` 而非 exe 資料夾。
  v0.2.0 時 PyInstaller 無此層，路徑剛好正確，所以才沒發現。
- 開發機不會出錯，因為有舊的 model 檔案或 `__file__` 解析結果不同。
- 修正：`cardio_py/core/segmentation.py` 改用 `_resolve_weights()`，
  先檢查 `sys._MEIPASS/annotation_tool/`（collab 打包路徑），
  再 fallback 到 `exe_folder/annotation_tool/`（主版下載路徑）。

**Bug 2 — Update 通知顯示 Collab 版**
- 根本原因：`collab-v1.0.0` release 上傳後被 GitHub 標為 Latest，
  `updater.py` 呼叫 `/releases/latest` 就拿到 collab tag。
- 修正：`check_for_update` 改為查 `/releases` 列表並以 `^v\d+\.\d+\.\d+$` 過濾，
  只對主版 tag 反應。
- 另修正 `download_app_update`：改為依序嘗試
  `MyoOptix-{tag}-{platform}.zip`（有版本號）→ `MyoOptix-{platform}.zip`（無版本號），
  解決 Mac/Windows 資產命名不一致問題。
- GitHub 上已將 `collab-v1.0.0` 改為 Pre-release。

### 其他修正
- `myooptix.spec`：加入 `annotation_tool/best_model.pth` 到 datas，model 隨 exe 打包，
  不再需要首次啟動下載。
- `main.py`：移除 `ModelDownloadDialog` 啟動檢查（model 已打包）。
- commit: `f790cd1`

### Mac 注意事項
1. 下次打包 Mac 版時請 `git pull`，`segmentation.py` 已修正路徑解析。
2. `myooptix_mac.spec` 也需要加 `annotation_tool/best_model.pth` 到 datas（同 Windows）。
3. 建議版本號升至 **v0.3.2** 反映這些修正。
4. 未來 GitHub release 命名請統一：Mac 用 `MyoOptix-mac.zip`（不加版本號），
   Windows 用 `MyoOptix-win.zip`，讓 updater 不需猜測。

### 如何在乾淨機器驗證（避免再次漏掉）
- 把 `dist/MyoOptix/` 複製到 Desktop 獨立資料夾，刪除其中 `annotation_tool/`，
  再啟動 exe — 模擬乾淨安裝。
- 把 `version.py` 改成 `0.0.1` 再打包測試 update 通知。

---

## 2026-07-13 Windows — Collab Edition v1.0.0 Windows 打包 ✅

**Windows 端完成 Collab Edition 打包並上傳至 GitHub。**

### 完成項目
- 建立 `collab_server/app/myooptix_collab_win.spec`（PyInstaller onedir spec）
  - `cardio_py/` 以 datas 方式明確打包（Mac 端用 symlink，Windows 端直接指向 repo root）
  - `annotation_tool/best_model.pth` 打包至 `_internal/annotation_tool/`（符合 `segmentation.py` 路徑解析）
  - `assets/`, `ui/`, `api_client.py`, `token_store.py` 全部包入
- 修正 `collab_server/app/main.py`：加入 `REPO_ROOT = APP_DIR.parent.parent` 並 `sys.path.insert(0, REPO_ROOT)`，讓 from-source 執行時能找到 `cardio_py`
- 修正 `collab_server/app/assets/icon.png`：從 `docs/icon.png` 複製（原本 `heart.svg` fallback 顯示錯誤 icon）
- 放大 `collab_server/app/ui/dialog_login.py`：width 480→640, icon 80×80→140×140, title 22→30px, 所有欄位字型/高度放大（使用者反映太小）

### 打包指令（Windows）
```bat
cd collab_server\app
.venv_win\Scripts\activate
pyinstaller myooptix_collab_win.spec --noconfirm
# → dist/MyoOptix/  (889 MB uncompressed)
# → zip → MyoOptix-collab-v1.0.0-win.zip (379 MB)
```

### 已上傳
- `MyoOptix-collab-v1.0.0-win.zip` → GitHub release `collab-v1.0.0` ✅
- 壓縮後 379 MB，解壓 880 MB（含 `_internal/annotation_tool/best_model.pth` 93.4 MB）

### 待 Mac 處理
- 更新 `docs/index.html` Windows 下載按鈕（目前 "Coming soon" disabled）→ 改為 `collab-v1.0.0` release 連結

---

## 2026-07-12 Windows — v0.3.1 code review + Quick Analysis preset + Windows packaging

- Pulled Mac v0.3.0 commits (morphology, toast, presets, PCA, UI polish)
- Fixed `toast.py`: `close()` crashed when `self._anim is None` (duration=0 toast) — changed `hasattr` check to `is not None`
- Added microscope preset dropdown to `dialog_quick.py` (was hardcoded TCY_4X 2.915 µm/px) — now reads `presets.json`, passes selected scale to worker
- Bumped version to v0.3.1 (Windows-side fixes warrant a patch bump)
- Built `MyoOptix-win.zip` via `myooptix.spec` — uploaded to GitHub v0.3.1 release

## 2026-07-27 Windows — v0.5.0：PKL stem collision fix、Group fix、Lock Flip

### Bug 修正

**Bug 1 — PKL stem 碰撞（同名影片互覆）**
- 根本原因：`Ctrl/After/1.mov` 和 `doxo/After/1.mov` 都產生 stem `After_1`，
  後算的影片 pkl 會蓋掉前一個，導致 Ctrl 的資料遺失。
- 修正：`worker_compute.py` 新增 `_make_stem(video_path, video_root)` —
  stem 改為包含 exp 前綴（`Ctrl_After_1`、`doxo_After_1`），跨資料夾不再碰撞。
- 向下相容：`tab_dashboard.py` `_scan_rows` 對舊 pkl（無前綴）做 fallback —
  只要該 old stem 沒有碰撞（count == 1），自動沿用舊 pkl，不強制重跑。

**Bug 2 — Merge Report GROUP 顯示 project name 而非 exp 群組**
- 根本原因：`_generate_report` 寫死用 `self._project_name` 作為 Group；
  舊的 `stem_to_exp` 中繼修法因 stem 碰撞，doxo 的 stem 仍覆蓋 Ctrl。
- 修正：`_generate_report` 改用 `stem_to_row`（有效 stem → row），
  Group 從 `row['exp']`（`scan_video_folder` 解析的資料夾名稱）直接取得。

**Bug 3 — Review 開啟錯誤 pkl**
- 根本原因：`_open_review_selected` 仍用 `{parent}_{stem}` 舊格式找 pkl。
- 修正：改用 `path_to_stem_rev` dict（effective stem from `_scan_rows`）查找。

**Bug 4 — `video_root` 未傳入 Compute pipeline**
- `ComputeDialog.__init__` 加 `video_root: str = ""` 參數
- `ComputeWorker.__init__` 加 `video_root: str = ""` 參數
- `_batch_compute` 傳入 `video_root=self._video_root`

### 新功能

**Lock Flip（Review dialog）**
- `dialog_review.py`：新增 "Lock Flip" 按鈕；按下後鎖定目前 flip 狀態，
  重新計算 MDP 時不再讓 `morphology_flip_test` 覆蓋使用者的選擇。
- `cardio_py/core/mdp.py`：`calculate_mdp_metrics` 加入 `force_flipped: bool | None` 參數，
  `None` = 自動偵測（預設），`True/False` = 強制指定，供 Review dialog 傳入。

### 版本
- `version.py`: 0.4.1 → 0.5.0

---

## 2026-07-02 Mac — Algorithm + Analysis

- Integrated PCA as default axis selection (`mdp.py`: `select_dominant_signal()`)
- Added `Contractility_Std_um_s` to Excel exports and Review panel beat metrics
- Removed IBI from Review beat metrics panel
- Fixed scale (µm/px) not loading from `compute_settings.json` in dashboard
- Added close guard on ReviewDialog (prompts if not exported)
- Updated all callers to use `select_dominant_signal` (worker, review, quick, validate scripts)
- Ran Before/After analysis on `Analysis_20260702` — pipeline confirmed working
- Verified PCA angle stability: ROI shift ±20% → angle change ±10° (acceptable)

---

## 2026-08-03 Mac — 跨平台設定與文件同步

- 新增 `.gitattributes`：統一兩台機器的換行。預設 `* text=auto eol=lf`（寫在 repo 層級，
  不依賴各機器的 `core.autocrlf`）；`.bat`/`.cmd`/`.ps1` 強制 CRLF；`.command`/`.sh` 強制 LF；
  影像、影片、`.mat`/`.pkl`/`.npy` 宣告為 binary
  - **Windows 端 pull 前請先 commit 或 stash**。pull 後若出現大量 modified，那是換行被重寫，
    執行 `git add --renormalize .` 即可回到乾淨，不要把它混進功能 commit
  - 實際只有 `annotation_tool/flags.json` 與 `training_log.csv` 由 CRLF 轉 LF，內容零改動
- `RELEASE_STATUS.md` 補上 v0.5.0（win ✅ 389MB / mac ⏳ 未上傳），並註明**判斷依據是 Release
  的 assets，不是 Release 標題**（`collab-v1.1.0` 標題寫「(Windows)」但兩平台 zip 都在）
- `WINDOWS_PORTING.md` 移除「Step 3 — Packaging (TODO)」整段。該決策早已定案（PyInstaller +
  GitHub Releases）並多次發版，`.spec` 與 icon 問題皆已解決。改為指向 `PACKAGING.md` 與
  `RELEASE_STATUS.md`，並補上兩條產品線的區別表
- `handover/` 曾短暫存在後移除。跨機交接一律走本檔（DEVLOG），不另開平行管道

### 待確認（Mac 端）
- 上傳 Mac v0.5.0 zip：`gh release upload v0.5.0 myooptix_app/MyoOptix-v0.5.0-mac.zip`，
  完成後把 `RELEASE_STATUS.md` 的 ⏳ 改為 ✅
- `20260712_myooptix_collab_server/` 是 Offline 舊專案且已與 `collab_server/` 分岔
  （各有對方沒有的檔案）。**兩端都不要改那個資料夾**，待使用者決定封存或刪除

---

## 2026-09-14 Mac — 修正追蹤點偵測方式（影響收縮強度）

- `cardio_py/core/tracking.py`：找點改成每顆 ROI 用 `goodFeaturesToTrack(..., mask=該顆範圍)` 在**原始畫面**上各自找，
  `maxCorners` 500 → 0（不限數量）
  - 舊做法：把 ROI 以外塗黑、整張圖找點只取最強的 500 點。塗黑邊界會形成最強的假角點，
    點幾乎全落在 ROI 外框（類器官本體外）；視野擁擠時每顆只分到個位數的點
- 影響
  - BPM、IBI、Interbeat segment 等時間類特徵幾乎不變
  - **Contractility 會變**（擁擠視野修改前後 0.66～2.59 倍，不是固定倍率）
  - **v0.5.0 以前算的 Contractility 不能與此版直接比較**；已用 v0.5.0 分析、要比收縮強度的資料需重跑
  - 每支影片計算時間約為原本的 1.2～2.2 倍
- 輸入輸出格式不變。重新分析請開新專案（在同一專案重新 compute，報表仍會用舊的 Excel）
- 驗證：5 支 Ctrl 測試影片修改前後對照；0116 HD/LD 以此版實跑並 review。紀錄在 workspace 的 `20260909_appbugfix/`（不在 repo 內）
- 版本號尚未更新，發版時再處理
- 已知且與本次無關：`cardio_py/tests/validate_tracking.py` 找不到 mat 檔無法執行；`validate_mdp.py` 修改前即有 4 項 FAIL

## 2026-09-14 Mac — 修正 Mac 上掃不到大寫副檔名影片

- `cardio_py/core/io.py` `scan_video_folder`：原本用 `rglob('*.mov')`，在 macOS 上區分大小寫，`1.MOV` 會被略過
  （Windows 不區分大小寫，不受影響）。改為列出所有檔案後以小寫副檔名比對
- 影響實例：`20250815` 批 94 支 `.MOV` 全部掃不到；`LAI0116/2026_01_16` 27 支只掃到 22 支
- 驗證：20250815 掃到 94、0116 掃到 27、Ctrl 測試資料夾 8，無重複
- 修正後需重新開啟 app 才會生效
## 2026-09-17 Mac — v0.5.0 Mac 版重新打包上傳、網站 Mac 下載說明

- **v0.5.0 Mac zip 已上傳**（`MyoOptix-v0.5.0-mac.zip`，366 MB）
  - 7/28 的原 Mac zip 在 macOS 26.2 一啟動就崩潰（QtCore 載入時 SIGSEGV），而且 spec 為 `icon=None`、
    版本號寫死 `0.4.1`，所以沒上傳過
  - 從 `v0.5.0` tag 重新打包（只修 spec 的 icon 與版本號）；app 內 `cardio_py` 逐檔與 tag 一致；
    手動開啟跑 Quick Analysis，結果與 v0.5.0 原始碼重算完全相同；上傳後 GitHub SHA-256 與本機一致
  - 舊的崩潰 zip（原在 `myooptix_app/MyoOptix-v0.5.0-mac.zip`，未進版控）已移到垃圾桶
- `myooptix_mac.spec`：icon 改為 `assets/MyoOptix.icns`；`CFBundleShortVersionString` 改為自動讀 `version.py`
  （已用新 spec 實際打包確認）
- `PACKAGING.md`：Mac 壓縮改用 `zip -r -y -X`（原指令沒保留符號連結，zip 變 ~1 GB）；補上 Mac 打包後測試清單
- `docs/lab.html`：點「Download for Mac」先顯示首次開啟說明視窗（macOS 可能擋下未公證的 app →
  系統設定 → 隱私權與安全性 → 強制打開）；Mac 大小改為 ~370 MB；兩平台 zip 皆內建模型，移除「首次啟動下載模型」
- `CLAUDE.md`：網站實際由 Vercel 提供（原寫 GitHub Pages）
- 已知問題：v0.5.0 關閉 app 時可能閃退（`sys.exit` 後清除 QApplication 時 SIGSEGV，結果已存檔不受影響）；
  推測與 Quick Analysis 後遞迴呼叫 `main()` 有關，尚未修。Windows 端請留意是否也會發生

### 追蹤點與 `.MOV` 修正（見上方 2026-09-14 兩則）
- `7bdedff`、`a64e009` 已於 2026-09-17 合併進 Mac 本機 `main`；Contractility 數值會改變，預計隨 v0.5.1 發布

### Windows 端注意
- 本次 push 帶入 8/3 的 `.gitattributes`：**pull 前先 commit 或 stash**；pull 後若大量檔案顯示 modified，
  執行 `git add --renormalize .`

### v0.5.1 發版清單（預計 2026-09-18，發版前先問使用者）
內容：追蹤點偵測修正（`7bdedff`）＋ Mac `.MOV` 掃描修正（`a64e009`）；可考慮一起修 BUG-07（關閉時閃退）
1. [ ] `version.py` → `0.5.1`（Mac spec 會自動讀；Windows spec 是否需改待確認）
2. [ ] `docs/lab.html`：版本 badge、兩個下載連結改 v0.5.1、檔案大小
3. [ ] DEVLOG、`RELEASE_STATUS.md` 更新；commit → `git push origin main` → `git tag v0.5.1` → `git push origin v0.5.1`
4. [ ] Mac：依 `PACKAGING.md` 打包 → **手動雙擊測試**（Quick Analysis 跑完、關閉後查當機報告）→ `zip -r -y -X` → 上傳並核對 SHA-256
5. [ ] **Windows**：pull（先 commit/stash；必要時 `git add --renormalize .`）→ 打包 → 測試 → 上傳 `MyoOptix-v0.5.1-win.zip`
6. [ ] `gh release create v0.5.1`，發版說明必須寫：**Contractility 算法改變，數值不能與 v0.5.0 以前直接比較**；BPM 等時間類指標大致不變
7. [ ] 兩個 zip 都上傳後才推 `lab.html` 的連結（避免網站連到不存在的檔案）；推完打開 myooptix.com/lab.html 確認
