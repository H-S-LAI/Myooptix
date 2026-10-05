# Release Status

Tracks which platform has packaged and uploaded each version.
Both sides should update this file before pushing a release.

| Version | Windows zip | Mac zip | Notes |
|---------|-------------|---------|-------|
| v0.1.0 | ✅ `MyoOptix_v0.1.0_Windows.zip` | ❌ not uploaded | Old asset naming — auto-update won't work from this version |
| v0.2.0 | ✅ `MyoOptix-win.zip` | ✅ `MyoOptix-mac.zip` | |
| v0.3.0 | ❌ skipped  | ✅ `MyoOptix_v0.3.0_Mac.zip` | Mac-only; superseded by v0.3.1 |
| v0.3.1 | ✅ `MyoOptix-v0.3.1-win.zip` | ✅ `MyoOptix-v0.3.1-mac.zip` | Quick Analysis preset, toast close() fix |
| v0.4.1 | ✅ `MyoOptix-v0.4.1-win.zip` | ✅ `MyoOptix-v0.4.1-mac.zip` | Scale preset UI, semantic version check |
| collab-v1.0.0 | ✅ `MyoOptix-collab-v1.0.0-win.zip` | ✅ `MyoOptix-collab-v1.0.0-mac.zip` | Collab Edition — separate app+server, see DEVLOG |
| collab-v1.1.0 | ✅ `MyoOptix-collab-v1.1.0-win.zip` | ✅ `MyoOptix-collab-v1.1.0-mac.zip` | Collab: microscope scale preset UI |
| **v0.5.1** | ⏳ **待在 Windows 打包** | ✅ 已打包待上傳（`myooptix_app/MyoOptix-v0.5.1-mac.zip`，367 MB，2026-10-05） | 追蹤點偵測修正＋Mac `.MOV` 掃描修正。**Contractility 數值與 v0.5.0 不可直接比較**；專案檔格式不變，舊專案可直接開啟（但內容仍是舊版算的，要重新 Batch Compute 才會更新）|
| **v0.5.0** | ✅ `MyoOptix-v0.5.0-win.zip` (389 MB) | ✅ `MyoOptix-v0.5.0-mac.zip` (366 MB，2026-09-17) | 主版，目前 Latest。Mac 版 7/28 的原 zip 在 macOS 26.2 啟動即崩潰（QtCore 載入時 SIGSEGV），且 spec 為 `icon=None`、版本寫死 0.4.1；2026-09-17 自 `v0.5.0` 標籤重新打包（僅修 spec 的 icon 與版本號），核對程式碼與標籤一致、Quick Analysis 結果與原始碼重算完全相同後上傳 |

> 表格狀態以 GitHub Release 的實際 assets 為準，不以 Release 標題為準。
> 標題可能寫「(Windows)」但兩個平台的 zip 都已上傳（collab-v1.0.0 / v1.1.0 即是如此）。
> 查證指令：`gh release view <tag> --json assets --jq '.assets[].name'`

## Checklist for each new release

1. Both sides pull latest `main`
2. Bump `VERSION` in `version.py` (one side does this, pushes, other side pulls)
3. Each platform runs PyInstaller from that exact commit
4. Windows uploads `MyoOptix-vX.Y.Z-win.zip` to the GitHub Release tag
5. Mac uploads `MyoOptix-vX.Y.Z-mac.zip` to the same tag
6. Update this table: ⏳ → ✅
7. Push `RELEASE_STATUS.md`
