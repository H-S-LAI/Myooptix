"""
MyoOptix U-Net Trainer — 5-Fold Cross-Validation
Architecture : U-Net + ResNet-34 encoder (ImageNet pretrained)
Usage        : python annotation_tool/train_kfold.py
Outputs      : kfold_results.csv / kfold_curve.png / fold_{k}_best.pth (×5)

Each fold: train on ~58 samples, evaluate on ~15.
Final report: per-sample mean ± SD aggregated across all 73 samples.
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
from sklearn.model_selection import KFold
import matplotlib.pyplot as plt
from PIL import Image

# ── paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
FRAME_DIR     = os.path.join(SCRIPT_DIR, "input_frames")
OUT_MASK_DIR  = os.path.join(SCRIPT_DIR, "output_masks")
INIT_MASK_DIR = os.path.join(SCRIPT_DIR, "initial_masks")
FLAGS_PATH    = os.path.join(SCRIPT_DIR, "flags.json")
RESULTS_PATH  = os.path.join(SCRIPT_DIR, "kfold_results.csv")
CURVE_PATH    = os.path.join(SCRIPT_DIR, "kfold_curve.png")

IMG_SIZE = 512
SEED     = 42
N_FOLDS  = 5
EPOCHS   = 100
PATIENCE = 15

CONFIG = dict(encoder_name="resnet34", encoder_weights="imagenet",
              in_channels=3, classes=1, img_size=IMG_SIZE,
              seed=SEED, n_folds=N_FOLDS)

# ── reproducibility ───────────────────────────────────────────────────────────
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
            excluded.append(os.path.basename(fp)); continue
        stem     = os.path.splitext(os.path.basename(fp))[0]
        out_mask = os.path.join(OUT_MASK_DIR,  stem + "_mask.png")
        ini_mask = os.path.join(INIT_MASK_DIR, stem + "_mask.png")
        if os.path.exists(out_mask):   pairs.append((fp, out_mask))
        elif os.path.exists(ini_mask): pairs.append((fp, ini_mask))
    print(f"Excluded (flagged) : {len(excluded)} — {excluded}")
    return pairs

class SegDataset(Dataset):
    def __init__(self, pairs, aug):
        self.pairs = pairs; self.aug = aug
    def __len__(self): return len(self.pairs)
    def __getitem__(self, idx):
        img_path, msk_path = self.pairs[idx]
        img = np.array(Image.open(img_path).convert("RGB"))
        msk = (np.array(Image.open(msk_path).convert("L")) > 127).astype(np.float32)
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

# ── metrics: per-sample accumulator ──────────────────────────────────────────
# NOTE: pixel Accuracy excluded — background-dominated images inflate this metric.
# Primary metrics: DSC, IoU (foreground-only). Sensitivity = TP/(TP+FN) directly
# measures whether the model detects the organoid.
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
        dsc  = [(2*tp+e)/(2*tp+fp+fn+e) for tp,fp,fn in zip(self.tp,self.fp,self.fn)]
        iou  = [(tp+e)/(tp+fp+fn+e)     for tp,fp,fn in zip(self.tp,self.fp,self.fn)]
        sens = [(tp+e)/(tp+fn+e)        for tp,fn    in zip(self.tp,self.fn)]
        prec = [(tp+e)/(tp+fp+e)        for tp,fp    in zip(self.tp,self.fp)]
        return (np.array(dsc), np.array(iou), np.array(sens), np.array(prec))

    def per_sample(self):
        dsc, iou, sens, prec = self.compute()
        return (dsc.mean(), dsc.std(), iou.mean(), iou.std())

# ── single-fold training ──────────────────────────────────────────────────────
def train_fold(fold, tr_pairs, val_pairs, device, batch):
    model_path = os.path.join(SCRIPT_DIR, f"fold_{fold}_best.pth")

    tr_loader  = DataLoader(SegDataset(tr_pairs,  TRAIN_AUG), batch_size=batch, shuffle=True,  num_workers=0)
    val_loader = DataLoader(SegDataset(val_pairs, VAL_AUG),   batch_size=batch, shuffle=False, num_workers=0)

    model = smp.Unet(encoder_name="resnet34", encoder_weights="imagenet",
                     in_channels=3, classes=1).to(device)
    optimizer = optim.Adam(model.parameters(), lr=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

    best_val, no_improve = float("inf"), 0
    fold_log = []

    for epoch in range(1, EPOCHS + 1):
        # train
        model.train()
        tr_loss = 0.0
        for imgs, masks in tr_loader:
            imgs, masks = imgs.to(device), masks.to(device)
            loss = bce_dice_loss(model(imgs), masks)
            optimizer.zero_grad(); loss.backward(); optimizer.step()
            tr_loss += loss.item() * len(imgs)
        tr_loss /= len(tr_loader.dataset)

        # val
        model.eval()
        vl_loss, vl_acc = 0.0, MetricAccumulator()
        with torch.no_grad():
            for imgs, masks in val_loader:
                imgs, masks = imgs.to(device), masks.to(device)
                preds = model(imgs)
                vl_loss += bce_dice_loss(preds, masks).item() * len(imgs)
                vl_acc.update(preds, masks)
        vl_loss /= len(val_loader.dataset)
        vl_dsc, _, vl_iou, _, _, _ = vl_acc.per_sample()
        scheduler.step(vl_loss)

        fold_log.append((epoch, tr_loss, vl_loss, vl_dsc, vl_iou))
        print(f"  [{fold}/{N_FOLDS}] ep={epoch:3d}  tr={tr_loss:.4f}  vl={vl_loss:.4f}  dsc={vl_dsc:.4f}  iou={vl_iou:.4f}")

        if vl_loss < best_val:
            best_val = vl_loss; no_improve = 0
            torch.save({"state_dict": model.state_dict(), "config": CONFIG}, model_path)
        else:
            no_improve += 1
            if no_improve >= PATIENCE:
                print(f"  [{fold}/{N_FOLDS}] Early stopping at epoch {epoch}")
                break

    # evaluate best model on this fold's val set (= held-out test for this fold)
    ckpt = torch.load(model_path, map_location=device)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    test_acc = MetricAccumulator()
    with torch.no_grad():
        for imgs, masks in val_loader:
            imgs, masks = imgs.to(device), masks.to(device)
            test_acc.update(model(imgs), masks)

    dsc_arr, iou_arr, sens_arr, prec_arr = test_acc.compute()
    return dsc_arr, iou_arr, sens_arr, prec_arr, fold_log

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    set_seed(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device : {device}")
    if device.type == "cuda":
        print(f"GPU    : {torch.cuda.get_device_name(0)}")

    pairs = collect_pairs()
    print(f"Valid samples : {len(pairs)}")
    if len(pairs) < N_FOLDS * 2:
        raise SystemExit(f"Need at least {N_FOLDS*2} samples for {N_FOLDS}-fold CV.")

    batch = 4 if device.type == "cuda" else 2
    kf    = KFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)

    all_dsc, all_iou, all_sens, all_prec = [], [], [], []
    all_logs = []
    t_total  = time.time()

    for fold, (tr_idx, val_idx) in enumerate(kf.split(pairs), start=1):
        tr_pairs  = [pairs[i] for i in tr_idx]
        val_pairs = [pairs[i] for i in val_idx]
        print(f"\n── Fold {fold}/{N_FOLDS}  (train={len(tr_pairs)}, val={len(val_pairs)}) ──")

        set_seed(SEED + fold)
        t0 = time.time()
        dsc_arr, iou_arr, sens_arr, prec_arr, fold_log = train_fold(
            fold, tr_pairs, val_pairs, device, batch)
        elapsed = time.time() - t0

        all_dsc.extend(dsc_arr);  all_iou.extend(iou_arr)
        all_sens.extend(sens_arr); all_prec.extend(prec_arr)
        all_logs.append(fold_log)
        print(f"  Fold {fold} done in {elapsed/60:.1f} min  "
              f"DSC={dsc_arr.mean():.4f}±{dsc_arr.std():.4f}  "
              f"Sens={sens_arr.mean():.4f}±{sens_arr.std():.4f}")

    total_time = time.time() - t_total
    all_dsc  = np.array(all_dsc)
    all_iou  = np.array(all_iou)
    all_sens = np.array(all_sens)
    all_prec = np.array(all_prec)

    print(f"\n{'='*58}")
    print(f"5-Fold CV Results  (n={len(all_dsc)} total samples, per-sample mean ± SD)")
    print(f"  DSC         : {all_dsc.mean():.4f} ± {all_dsc.std():.4f}")
    print(f"  IoU         : {all_iou.mean():.4f} ± {all_iou.std():.4f}")
    print(f"  Sensitivity : {all_sens.mean():.4f} ± {all_sens.std():.4f}")
    print(f"  Precision   : {all_prec.mean():.4f} ± {all_prec.std():.4f}")
    print(f"  Total time  : {total_time/60:.1f} min")
    print(f"{'='*58}")

    # ── save per-fold summary CSV ─────────────────────────────────────────────
    rows = []
    offset = 0
    for fold, (tr_idx, val_idx) in enumerate(kf.split(pairs), start=1):
        n = len(val_idx)
        d = all_dsc[offset:offset+n]
        s = all_sens[offset:offset+n]
        rows.append({"fold": fold, "n_val": n,
                     "dsc_mean":  round(d.mean(), 4), "dsc_std":  round(d.std(),  4),
                     "sens_mean": round(s.mean(), 4), "sens_std": round(s.std(), 4)})
        offset += n
    with open(RESULTS_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["fold","n_val",
                                          "dsc_mean","dsc_std",
                                          "sens_mean","sens_std"])
        w.writeheader(); w.writerows(rows)

    # ── plot: loss curves per fold ────────────────────────────────────────────
    fig, axes = plt.subplots(1, N_FOLDS, figsize=(4 * N_FOLDS, 4), sharey=True)
    for fold_i, (ax, log) in enumerate(zip(axes, all_logs), start=1):
        eps  = [r[0] for r in log]
        tr_l = [r[1] for r in log]
        vl_l = [r[2] for r in log]
        ax.plot(eps, tr_l, label="Train"); ax.plot(eps, vl_l, label="Val")
        ax.set_title(f"Fold {fold_i}"); ax.set_xlabel("Epoch")
        if fold_i == 1: ax.set_ylabel("BCE+Dice Loss")
        ax.legend(fontsize=7)
    plt.suptitle("5-Fold CV Loss Curves", y=1.02)
    plt.tight_layout(); plt.savefig(CURVE_PATH, dpi=150, bbox_inches="tight"); plt.close()

    print(f"\nOutputs:")
    print(f"  {RESULTS_PATH}")
    print(f"  {CURVE_PATH}")
    print(f"  fold_1_best.pth … fold_{N_FOLDS}_best.pth")


if __name__ == "__main__":
    main()
