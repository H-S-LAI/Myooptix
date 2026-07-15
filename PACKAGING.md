# MyoOptix — Packaging Guide

每次打包前請先 `git pull` 確保 code 是最新的。

---

## 主版 (Main App)

### Windows

```bat
cd myooptix_app
..\..\.venv_win\Scripts\activate
pyinstaller myooptix.spec --noconfirm
```

輸出：`myooptix_app/dist/MyoOptix/`

**打包後乾淨測試（必做）：**
1. 把 `dist/MyoOptix/` 複製到 Desktop 獨立資料夾（如 `TestMyoOptix_vX.X.X`）
2. 啟動 `MyoOptix.exe`
3. 確認 checklist：
   - [ ] App icon 正確（主視窗 + 所有 dialog）
   - [ ] Quick Analysis → 有 preset dropdown + scale spinbox + "+ Save"
   - [ ] Batch Compute → 選 U-Net → Run 一個影片 → 不報錯
   - [ ] Update 通知：把 `_internal/version.py` 的 VERSION 改成 `0.0.1` → 重啟 → 確認彈出正確 update dialog（不是 collab 版）

**打包完成後：**
```bat
cd myooptix_app\dist
powershell Compress-Archive -Path MyoOptix\* -DestinationPath MyoOptix-win.zip -CompressionLevel Optimal
```
上傳 `MyoOptix-win.zip` 到 GitHub release `vX.X.X`。

---

### Mac

```bash
cd myooptix_app
source ../../.venv/bin/activate
pyinstaller myooptix_mac.spec --noconfirm
```

輸出：`myooptix_app/dist/MyoOptix.app`

打包完成後：
```bash
cd myooptix_app/dist
zip -r MyoOptix-mac.zip MyoOptix.app
```
上傳 `MyoOptix-mac.zip` 到 GitHub release `vX.X.X`。

---

## Collab Edition

### Windows

```bat
cd collab_server\app
..\..\..\.venv_win\Scripts\activate
pyinstaller myooptix_collab_win.spec --noconfirm
```

輸出：`collab_server/app/dist/MyoOptix/`

```bat
cd collab_server\app\dist
powershell Compress-Archive -Path MyoOptix\* -DestinationPath MyoOptix-collab-v1.0.0-win.zip -CompressionLevel Optimal
```
上傳到 GitHub release `collab-v1.0.0`（Pre-release）。

### Mac

```bash
cd collab_server/app
source ../../../.venv/bin/activate
pyinstaller myooptix_collab_mac.spec --noconfirm
```

---

## Release Checklist

- [ ] `version.py` 已 bump（先問過後再改）
- [ ] DEVLOG 已更新
- [ ] `git commit` + `git push` 完成
- [ ] 兩平台都打包並測試
- [ ] GitHub Release 建立，zip 上傳
- [ ] `lab.html` 下載連結更新（主版）或 `index.html` 更新（Collab）
- [ ] Collab release 維持 Pre-release 狀態（不可設為 Latest）

---

## 常見問題

**UNet 找不到 model**
- 確認 spec 的 datas 有包含 `annotation_tool/best_model.pth`
- 主版：model 應在 `_internal/annotation_tool/best_model.pth`

**Update 通知顯示 Collab 版**
- 確認 `collab-vX.X.X` release 是 Pre-release 狀態
- `updater.py` 的 `check_for_update` 只認 `vX.Y.Z` 格式的 tag

**Icon 顯示錯誤（心形）**
- 確認 `myooptix_app/assets/icon.png` 存在
- `main_window.py` 和 `main.py` 都要有 icon.png fallback 邏輯
