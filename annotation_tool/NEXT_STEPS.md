# Annotation & Training — Handoff Document

這份文件讓 Claude Code 在新電腦上完全獨立完成後續工作，不需要問使用者任何問題。

---

## 背景

MyoOptix 是一個心肌類器官跳動分析工具（Python + Streamlit），正在從 MATLAB 移植。
U-Net 分割是其中一個前處理選項。目前已完成：
- 82 張影片截幀 → `input_frames/raw_1.png ~ raw_82.png`
- MATLAB U-Net 產生初始 mask → `initial_masks/raw_*_mask.png`（82 張全部完成）

接下來要完成：annotate.py → 人工標註 → train.py → best_model.pth

---

## Step 1 — 寫 annotate.py

**直接寫，不要問使用者。**

路徑：`annotation_tool/annotate.py`
使用方式：`python annotation_tool/annotate.py`（用專案根目錄的 .venv）

### 功能規格

- 左側顯示原圖，右側顯示 mask overlay（綠色半透明）
- 從 `initial_masks/raw_*_mask.png` 載入初始 mask
- 修正後存到 `output_masks/raw_*_mask.png`
- 已存過的下次開啟從 `output_masks/` 載入（不是 `initial_masks/`）

### 操作介面（OpenCV 視窗）

| 操作 | 功能 |
|---|---|
| 左鍵拖曳 | 加入 foreground（塗白） |
| 右鍵拖曳 | 刪除（塗黑） |
| 滾輪上/下 | 筆刷變大/小（範圍 5~100px） |
| `S` | 存檔到 output_masks/ |
| `A` | 上一張 |
| `D` | 下一張（自動存檔） |
| `R` | 重置回 initial_mask |
| `Q` | 離開 |

### UI 細節
- 視窗標題：`MyoOptix Annotator — raw_N.png [M/82] (已存: K 張)`
- 左上角顯示目前筆刷大小
- 右上角顯示操作提示（S存 A上 D下 R重置 Q離開）
- 已存過的圖在標題加 ✓ 標記

---

## Step 2 — 寫 train.py

**直接寫，不要問使用者。**

路徑：`annotation_tool/train.py`
使用方式：`python annotation_tool/train.py`

### 訓練規格

- 架構：標準 U-Net（encoder: 4層 down，decoder: 4層 up，base channels=64）
- 輸入：`input_frames/raw_*.png`（原圖）+ `output_masks/raw_*_mask.png`（標註 mask）
  - 如果某張沒有 output_mask，自動用 initial_mask 代替
- 輸出大小：統一 resize 到 512×512
- Train/Val/Test split：70/15/15（random seed=42）
- Loss：BCE + Dice（各 0.5 權重）
- Optimizer：Adam，lr=1e-4
- Epochs：100，Early stopping patience=15
- Batch size：4（GPU）或 2（CPU）
- Data augmentation：隨機水平/垂直翻轉、隨機旋轉 ±15°、亮度/對比 jitter
- 輸出：
  - `annotation_tool/best_model.pth`（val loss 最低的 checkpoint）
  - `annotation_tool/training_log.csv`（每 epoch 的 train/val loss）
  - `annotation_tool/training_curve.png`（loss 曲線圖）

### 環境需求（MSI Katana 15，NVIDIA GPU）

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install opencv-python numpy scikit-learn albumentations matplotlib
```

確認 GPU 可用：
```python
import torch; print(torch.cuda.is_available())  # 應該是 True
```

---

## Step 3 — 整合進 MyoOptix（之後再做，現在不用）

把 `best_model.pth` 複製到 `cardio_py/core/unet_model.pth`，
然後在 `cardio_py/core/segmentation.py` 加 U-Net 推論路徑。
這個 step 等訓練完成再做。

---

## 資料夾結構（目前狀態）

```
annotation_tool/
├── input_frames/      ← ✅ 82 張原圖
├── initial_masks/     ← ✅ 82 張 U-Net 初始 mask
├── output_masks/      ← ⬜ 人工修正後（待標註）
├── training_data/     ← ⬜ 保留備用
├── annotate.py        ← ⬜ 待寫（Step 1）
├── train.py           ← ⬜ 待寫（Step 2）
├── prepare_masks.m    ← ✅ 已完成
└── NEXT_STEPS.md      ← 本文件
```

---

## 給 Claude 的執行指令

1. 先寫 `annotate.py`，寫完告訴使用者可以開始標註
2. 寫 `train.py`
3. 兩個都寫完後，提醒使用者：
   - 先跑 `python annotation_tool/annotate.py` 完成標註
   - 再跑 `python annotation_tool/train.py` 開始訓練
   - 訓練完把 `best_model.pth` 帶回 Mac 整合進 MyoOptix
