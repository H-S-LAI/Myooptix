# Handover — 2026-08-03（跨平台設定，給 Windows 端）

這份不是功能開發交接，是**設定與文件層面的整理**。Mac 端做的，會影響 Windows 端 pull 之後的行為。
同日另有 `handover_20260803.md`（功能面），兩份請一起看。

---

## ⚠️ 先做這件事：pull 之前先把工作存好

本次新增了 `.gitattributes`，並對既有檔案做過一次換行正規化（`git add --renormalize .`）。

Windows 端 pull 之後，git 可能把一批檔案標成「已修改」——那是換行被重寫，不是內容變了。

```bat
:: 1. 先確保沒有未提交的工作
git status
git stash            :: 有的話先收起來

:: 2. 拉取
git pull

:: 3. 確認工作區乾淨（若仍有一堆 modified，執行下面這行讓 git 重新套用規則）
git add --renormalize .
git status           :: 應該回到乾淨

:: 4. 還原剛剛收起來的工作
git stash pop
```

**不要**在看到大量 modified 時直接 commit，那會把換行變更混進你的功能 commit 裡。

---

## 本次改了什麼

### 1. 新增 `.gitattributes`（commit `fc30af0`）

之前沒有這個檔，所以同一個檔案在 Mac 和 Windows 上會被判定為整檔變更，diff 全是換行雜訊。

規則：

| 檔案 | 換行 | 理由 |
|---|---|---|
| 預設（`.py`、`.md`、`.json`、`.csv`…） | LF | repo 內外都用 LF，不依賴各機器的 `core.autocrlf` |
| `.bat` `.cmd` `.ps1` | **CRLF** | cmd.exe 對 LF 容忍有限，出現 label / goto / 多行 if 會解析錯誤 |
| `.command` `.sh` | LF | macOS/Linux 啟動腳本 |
| 影像、影片、`.mat` `.pkl` `.npy` `.h5` | binary | 不做轉換，也不產生文字 diff |

**你不需要在 Windows 上設定 `core.autocrlf`。** 這份設定寫在 repo 層級，會覆蓋機器設定，
新加入的人 clone 下來行為就一致。

實際只有 `annotation_tool/flags.json` 和 `annotation_tool/training_log.csv` 原本是 CRLF，
已轉為 LF，內容零改動。

### 2. `RELEASE_STATUS.md` 補上 v0.5.0

原本表格停在 `collab-v1.1.0`，缺了目前 Latest 的 v0.5.0。已依 GitHub 實際 assets 補上：

- v0.5.0 Windows zip ✅ 已上傳（389 MB）
- v0.5.0 Mac zip ⏳ **尚未上傳**，本地檔在 `myooptix_app/MyoOptix-v0.5.0-mac.zip`

也加了一條註記：**判斷有沒有上傳要看 assets，不要看 Release 標題。**
`collab-v1.1.0` 標題寫「(Windows)」但兩個平台的 zip 都在，容易誤判。查證用：

```bat
gh release view v0.5.0 --json assets --jq ".assets[].name"
```

### 3. `WINDOWS_PORTING.md` 移除過期段落

原本的「Step 3 — Packaging (TODO)」還在說「更新策略決策待定」「`.spec` 檔尚未建立」
「還沒有 `.ico`」——這些**早就完成了**，兩條產品線都已多次發版。

該段已改為指向 `PACKAGING.md`（打包步驟）與 `RELEASE_STATUS.md`（發版狀態），
並補上兩條產品線的區別表。**不要再重做那個決策。**

---

## 順帶查到、但沒有動的事

### `20260712_myooptix_collab_server/` 是舊的，且已與正本分岔

正本是本 repo 內的 `collab_server/`。那個獨立資料夾對應的 Railway 專案已 Offline
（見 `handover_20260803.md`）。兩邊目前的差異：

- 獨立資料夾多了 `app/cardio_py/`
- 正本多了 `app/myooptix_collab_win.spec`
- `main.py`、`myooptix_collab_mac.spec`、`ui/dialog_login.py`、`ui/dialog_quick.py` 內容不同

**Windows 端不要去改那個資料夾。** 要不要刪除或封存尚未決定，等使用者確認。

### 未追蹤檔案是刻意的

`111核定清單_李岡遠.pdf`、`MyoOptix-v0.5.0-mac.zip`、`project_..._20260708/`、
`project_..._20260715/`、`scale/` 都是刻意不進版控，不要 commit 進去。

---

## 待辦（延續前一份 handover）

1. **上傳 Mac v0.5.0 zip** — Mac 端執行，Windows 端不用管
   ```bash
   gh release upload v0.5.0 myooptix_app/MyoOptix-v0.5.0-mac.zip
   ```
   上傳後把 `RELEASE_STATUS.md` 的 ⏳ 改成 ✅
2. Railway GitHub 自動部署有時不觸發，需手動 `railway up`

---

## 一個機制上的提醒

Claude 的 **auto memory 綁單一機器，不會跨機同步**（官方明載 "Files are not shared across
machines"）。所以 Windows 端那個 Claude 的記憶，和 Mac 這邊完全不相通。

**凡是兩台機器都要知道的事，一律寫進 repo 的文件**（`CLAUDE.md`、`WINDOWS_PORTING.md`、
`PACKAGING.md`、`RELEASE_STATUS.md`、`handover/`），靠 git 同步。
寫在記憶裡的東西，另一台永遠看不到。
