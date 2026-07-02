"""
MyoOptix U-Net Trainer
Architecture : U-Net + ResNet-34 encoder (ImageNet pretrained)
Usage        : python annotation_tool/train.py
Outputs      : best_model.pth / training_log.csv / training_curve.png
"""

import os, glob, re, csv, time, json, random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import segmentation_models_pytorch as smp
import albumentations as A
from albumentations.pytorch import ToTensorV2
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
from PIL import Image

# ── paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
FRAME_DIR     = os.path.join(SCRIPT_DIR, "input_frames")
OUT_MASK_DIR  = os.path.join(SCRIPT_DIR, "output_masks")
INIT_MASK_DIR = os.path.join(SCRIPT_DIR, "initial_masks")
FLAGS_PATH    = os.path.join(SCRIPT_DIR, "flags.json")
MODEL_PATH    = os.path.join(SCRIPT_DIR, "best_model.pth")
LOG_PATH      = os.path.join(SCRIPT_DIR, "training_log.csv")
CURVE_PATH    = os.path.join(SCRIPT_DIR, "training_curve.png")

IMG_SIZE = 512
SEED     = 42

# ── global seeding (reproducibility) ─────────────────────────────────────────
def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark     = False

# ── augmentation ──────────────────────────────────────────────────────────────
TRAIN_AUG = A.Compose([
    A.HorizontalFlip(p=0.5),
    A.VerticalFlip(p=0.5),
    A.Rotate(limit=15, p=0.5),
    A.ColorJitter(brightness=0.2, contrast=0.2, p=0.5),
    A.GaussNoise(std_range=(0.01, 0.05), p=0.3),
    A.Resize(IMG_SIZE, IMG_SIZE),
    A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ToTensorV2(),
])

VAL_AUG = A.Compose([
    A.Resize(IMG_SIZE, IMG_SIZE),
    A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ToTensorV2(),
])

# ── dataset ───────────────────────────────────────────────────────────────────
def natural_key(path):
    nums = re.findall(r"\d+", os.path.basename(path))
    return int(nums[-1]) if nums else 0


def load_flagged():
    if os.path.exists(FLAGS_PATH):
        return set(json.loads(open(FLAGS_PATH).read()).get("flagged", []))
    return set()


def collect_pairs():
    flagged  = load_flagged()
    frames   = sorted(glob.glob(os.path.join(FRAME_DIR, "raw_*.png")), key=natural_key)
    pairs, excluded = [], []
    for i, fp in enumerate(frames):
        if i in flagged:
            excluded.append(os.path.basename(fp))
            continue
        stem     = os.path.splitext(os.path.basename(fp))[0]
        out_mask = os.path.join(OUT_MASK_DIR,  stem + "_mask.png")
        ini_mask = os.path.join(INIT_MASK_DIR, stem + "_mask.png")
        if os.path.exists(out_mask):
            pairs.append((fp, out_mask))
        elif os.path.exists(ini_mask):
            pairs.append((fp, ini_mask))
    print(f"Excluded (flagged): {len(excluded)} — {excluded}")
    return pairs


class SegDataset(Dataset):
    def __init__(self, pairs, aug):
        self.pairs = pairs
        self.aug   = aug

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, idx):
        img_path, msk_path = self.pairs[idx]
        img = np.array(Image.open(img_path).convert("RGB"))
        msk = np.array(Image.open(msk_path).convert("L"))
        msk = (msk > 127).astype(np.float32)
        out = self.aug(image=img, mask=msk)
        return out["image"], out["mask"].unsqueeze(0)

# ── loss ──────────────────────────────────────────────────────────────────────
def bce_dice_loss(pred, target, eps=1e-6):
    bce   = nn.functional.binary_cross_entropy_with_logits(pred, target)
    p     = torch.sigmoid(pred)
    inter = (p * target).sum(dim=(2, 3))
    union = p.sum(dim=(2, 3)) + target.sum(dim=(2, 3))
    dice  = (1 - (2 * inter + eps) / (union + eps)).mean()
    return 0.5 * bce + 0.5 * dice

# ── metrics: accumulate TP/FP/FN per sample, compute once over full set ───────
# NOTE: pixel Accuracy is intentionally excluded — images are heavily background-
# dominated, so accuracy is inflated by TN and unreliable as a segmentation
# quality measure. Primary metrics: DSC and IoU (foreground-only). Sensitivity
# quantifies whether the model actually detects the organoid (TP rate).
class MetricAccumulator:
    def __init__(self, eps=1e-6):
        self.eps = eps
        self.tp, self.fp, self.fn = [], [], []

    def update(self, pred_logits, target, thresh=0.5):
        pred = (torch.sigmoid(pred_logits) > thresh).float()
        for i in range(pred.shape[0]):
            p, t = pred[i], target[i]
            self.tp.append((p * t).sum().item())
            self.fp.append((p * (1 - t)).sum().item())
            self.fn.append(((1 - p) * t).sum().item())

    def compute(self):
        e = self.eps
        dsc  = [(2*tp+e)/(2*tp+fp+fn+e)  for tp,fp,fn in zip(self.tp,self.fp,self.fn)]
        iou  = [(tp+e)/(tp+fp+fn+e)       for tp,fp,fn in zip(self.tp,self.fp,self.fn)]
        sens = [(tp+e)/(tp+fn+e)          for tp,fn    in zip(self.tp,self.fn)]
        prec = [(tp+e)/(tp+fp+e)          for tp,fp    in zip(self.tp,self.fp)]
        return (np.array(dsc), np.array(iou),
                np.array(sens), np.array(prec))

# ── train/val loop ────────────────────────────────────────────────────────────
def run_epoch(model, loader, optimizer, device, train=True):
    model.train(train)
    total_loss = 0.0
    acc = MetricAccumulator()
    with torch.set_grad_enabled(train):
        for imgs, masks in loader:
            imgs, masks = imgs.to(device), masks.to(device)
            preds = model(imgs)
            loss  = bce_dice_loss(preds, masks)
            if train:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            total_loss += loss.item() * len(imgs)
            acc.update(preds.detach(), masks)
    dsc_arr, iou_arr, _, _ = acc.compute()
    return total_loss / len(loader.dataset), dsc_arr.mean(), iou_arr.mean()

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    set_seed(SEED)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device : {device}")
    if device.type == "cuda":
        print(f"GPU    : {torch.cuda.get_device_name(0)}")

    pairs = collect_pairs()
    print(f"Valid samples : {len(pairs)}")
    if len(pairs) < 4:
        raise SystemExit("Too few samples (< 4). Please annotate first.")

    # 70 / 15 / 15 split (fixed seed for reproducibility)
    idx_all = list(range(len(pairs)))
    idx_train, idx_tmp  = train_test_split(idx_all, test_size=0.30, random_state=SEED)
    idx_val,   idx_test = train_test_split(idx_tmp, test_size=0.50, random_state=SEED)

    tr_pairs   = [pairs[i] for i in idx_train]
    val_pairs  = [pairs[i] for i in idx_val]
    test_pairs = [pairs[i] for i in idx_test]
    print(f"Split  : train={len(tr_pairs)}  val={len(val_pairs)}  test={len(test_pairs)}")

    batch = 4 if device.type == "cuda" else 2
    tr_loader   = DataLoader(SegDataset(tr_pairs,   TRAIN_AUG), batch_size=batch, shuffle=True,  num_workers=0)
    val_loader  = DataLoader(SegDataset(val_pairs,  VAL_AUG),   batch_size=batch, shuffle=False, num_workers=0)
    test_loader = DataLoader(SegDataset(test_pairs, VAL_AUG),   batch_size=batch, shuffle=False, num_workers=0)

    # U-Net + ResNet-34 encoder (ImageNet pretrained)
    CONFIG = dict(encoder_name="resnet34", encoder_weights="imagenet",
                  in_channels=3, classes=1, img_size=IMG_SIZE, seed=SEED)
    model = smp.Unet(**{k: v for k, v in CONFIG.items()
                        if k in ("encoder_name", "encoder_weights", "in_channels", "classes")}
                     ).to(device)
    print(f"Model  : U-Net / ResNet-34 encoder (ImageNet pretrained)")

    optimizer = optim.Adam(model.parameters(), lr=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

    EPOCHS   = 100
    PATIENCE = 15
    best_val = float("inf")
    no_improve = 0
    log_rows   = []

    print(f"\n{'Ep':>4}  {'TrLoss':>7}  {'TrDSC':>6}  {'VlLoss':>7}  {'VlDSC':>6}  {'VlIoU':>6}  {'sec':>5}")
    print("-" * 58)

    t_start = time.time()
    for epoch in range(1, EPOCHS + 1):
        t0 = time.time()
        tr_loss, tr_dsc, tr_iou = run_epoch(model, tr_loader,  optimizer, device, train=True)
        vl_loss, vl_dsc, vl_iou = run_epoch(model, val_loader, optimizer, device, train=False)
        scheduler.step(vl_loss)
        elapsed = time.time() - t0

        print(f"{epoch:4d}  {tr_loss:7.4f}  {tr_dsc:6.4f}  {vl_loss:7.4f}  {vl_dsc:6.4f}  {vl_iou:6.4f}  {elapsed:5.1f}s")
        log_rows.append(dict(epoch=epoch,
                             train_loss=tr_loss, train_dsc=tr_dsc,
                             val_loss=vl_loss,   val_dsc=vl_dsc, val_iou=vl_iou))

        if vl_loss < best_val:
            best_val   = vl_loss
            no_improve = 0
            # save weights + config together
            torch.save({"state_dict": model.state_dict(), "config": CONFIG}, MODEL_PATH)
        else:
            no_improve += 1
            if no_improve >= PATIENCE:
                print(f"\nEarly stopping at epoch {epoch}  (best val loss={best_val:.4f})")
                break

    total_time = time.time() - t_start
    print(f"\nTraining time : {total_time/60:.1f} min")

    # ── test evaluation (per-sample metrics) ─────────────────────────────────
    ckpt = torch.load(MODEL_PATH, map_location=device)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    test_acc = MetricAccumulator()
    with torch.no_grad():
        for imgs, masks in test_loader:
            imgs, masks = imgs.to(device), masks.to(device)
            test_acc.update(model(imgs), masks)

    dsc_arr, iou_arr, sens_arr, prec_arr = test_acc.compute()
    print(f"\n── Test Set Results (n={len(test_pairs)}, per-sample mean ± SD) ──")
    print(f"  DSC         : {dsc_arr.mean():.4f} ± {dsc_arr.std():.4f}")
    print(f"  IoU         : {iou_arr.mean():.4f} ± {iou_arr.std():.4f}")
    print(f"  Sensitivity : {sens_arr.mean():.4f} ± {sens_arr.std():.4f}")
    print(f"  Precision   : {prec_arr.mean():.4f} ± {prec_arr.std():.4f}")
    print(f"  (pixel Accuracy excluded — background-dominated images inflate this metric)")

    # ── save CSV ──────────────────────────────────────────────────────────────
    with open(LOG_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=log_rows[0].keys())
        w.writeheader(); w.writerows(log_rows)

    # ── plot curve ────────────────────────────────────────────────────────────
    eps_ = [r["epoch"]      for r in log_rows]
    tr_l = [r["train_loss"] for r in log_rows]
    vl_l = [r["val_loss"]   for r in log_rows]
    vl_d = [r["val_dsc"]    for r in log_rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    ax1.plot(eps_, tr_l, label="Train Loss"); ax1.plot(eps_, vl_l, label="Val Loss")
    ax1.set_xlabel("Epoch"); ax1.set_ylabel("BCE+Dice Loss")
    ax1.legend(); ax1.set_title("Loss Curve")
    ax2.plot(eps_, vl_d, color="green", label="Val DSC")
    ax2.set_xlabel("Epoch"); ax2.set_ylabel("DSC")
    ax2.legend(); ax2.set_title("Validation DSC")
    plt.tight_layout(); plt.savefig(CURVE_PATH, dpi=150); plt.close()

    print(f"\nOutputs:")
    print(f"  {MODEL_PATH}")
    print(f"  {LOG_PATH}")
    print(f"  {CURVE_PATH}")


if __name__ == "__main__":
    main()
