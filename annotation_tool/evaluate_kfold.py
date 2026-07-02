"""
MyoOptix — 5-Fold Evaluation (no retraining)
Loads each fold's saved model, evaluates on its held-out set,
reports DSC / IoU / Sensitivity / Precision across all 73 samples.
Usage: python annotation_tool/evaluate_kfold.py
"""

import os, glob, re, json
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
import segmentation_models_pytorch as smp
import albumentations as A
from albumentations.pytorch import ToTensorV2
from sklearn.model_selection import KFold
from PIL import Image

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
FRAME_DIR     = os.path.join(SCRIPT_DIR, "input_frames")
OUT_MASK_DIR  = os.path.join(SCRIPT_DIR, "output_masks")
INIT_MASK_DIR = os.path.join(SCRIPT_DIR, "initial_masks")
FLAGS_PATH    = os.path.join(SCRIPT_DIR, "flags.json")

IMG_SIZE = 512
SEED     = 42
N_FOLDS  = 5

VAL_AUG = A.Compose([
    A.Resize(IMG_SIZE, IMG_SIZE),
    A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ToTensorV2(),
])

def natural_key(p):
    nums = re.findall(r"\d+", os.path.basename(p))
    return int(nums[-1]) if nums else 0

def collect_pairs():
    flagged = set()
    if os.path.exists(FLAGS_PATH):
        flagged = set(json.loads(open(FLAGS_PATH).read()).get("flagged", []))
    frames = sorted(glob.glob(os.path.join(FRAME_DIR, "raw_*.png")), key=natural_key)
    pairs  = []
    for i, fp in enumerate(frames):
        if i in flagged: continue
        stem     = os.path.splitext(os.path.basename(fp))[0]
        out_mask = os.path.join(OUT_MASK_DIR,  stem + "_mask.png")
        ini_mask = os.path.join(INIT_MASK_DIR, stem + "_mask.png")
        if   os.path.exists(out_mask): pairs.append((fp, out_mask))
        elif os.path.exists(ini_mask): pairs.append((fp, ini_mask))
    return pairs

class SegDataset(Dataset):
    def __init__(self, pairs, aug):
        self.pairs = pairs; self.aug = aug
    def __len__(self): return len(self.pairs)
    def __getitem__(self, idx):
        img = np.array(Image.open(self.pairs[idx][0]).convert("RGB"))
        msk = (np.array(Image.open(self.pairs[idx][1]).convert("L")) > 127).astype(np.float32)
        out = self.aug(image=img, mask=msk)
        return out["image"], out["mask"].unsqueeze(0)

def eval_fold(model_path, val_pairs, device):
    ckpt = torch.load(model_path, map_location=device)
    cfg  = ckpt.get("config", {})
    model = smp.Unet(
        encoder_name    = cfg.get("encoder_name", "resnet34"),
        encoder_weights = None,
        in_channels     = cfg.get("in_channels", 3),
        classes         = cfg.get("classes", 1),
    ).to(device)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()

    loader = DataLoader(SegDataset(val_pairs, VAL_AUG),
                        batch_size=4, shuffle=False, num_workers=0)
    eps = 1e-6
    tp_all, fp_all, fn_all = [], [], []
    with torch.no_grad():
        for imgs, masks in loader:
            imgs, masks = imgs.to(device), masks.to(device)
            preds = (torch.sigmoid(model(imgs)) > 0.5).float()
            for i in range(preds.shape[0]):
                p, t = preds[i], masks[i]
                tp_all.append((p * t).sum().item())
                fp_all.append((p * (1 - t)).sum().item())
                fn_all.append(((1 - p) * t).sum().item())

    dsc  = np.array([(2*tp+eps)/(2*tp+fp+fn+eps) for tp,fp,fn in zip(tp_all,fp_all,fn_all)])
    iou  = np.array([(tp+eps)/(tp+fp+fn+eps)     for tp,fp,fn in zip(tp_all,fp_all,fn_all)])
    sens = np.array([(tp+eps)/(tp+fn+eps)         for tp,fn    in zip(tp_all,fn_all)])
    prec = np.array([(tp+eps)/(tp+fp+eps)         for tp,fp    in zip(tp_all,fp_all)])
    return dsc, iou, sens, prec

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}\n")

    pairs = collect_pairs()
    kf    = KFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)

    all_dsc, all_iou, all_sens, all_prec = [], [], [], []

    print(f"{'Fold':>5}  {'n':>4}  {'DSC':>12}  {'IoU':>12}  {'Sens':>12}  {'Prec':>12}")
    print("-" * 65)

    for fold, (_, val_idx) in enumerate(kf.split(pairs), start=1):
        model_path = os.path.join(SCRIPT_DIR, f"fold_{fold}_best.pth")
        if not os.path.exists(model_path):
            print(f"  Fold {fold}: model not found, skipping")
            continue

        val_pairs = [pairs[i] for i in val_idx]
        dsc, iou, sens, prec = eval_fold(model_path, val_pairs, device)

        all_dsc.extend(dsc);  all_iou.extend(iou)
        all_sens.extend(sens); all_prec.extend(prec)

        print(f"  {fold:>3}   {len(val_pairs):>4}  "
              f"{dsc.mean():.4f}±{dsc.std():.4f}  "
              f"{iou.mean():.4f}±{iou.std():.4f}  "
              f"{sens.mean():.4f}±{sens.std():.4f}  "
              f"{prec.mean():.4f}±{prec.std():.4f}")

    all_dsc  = np.array(all_dsc)
    all_iou  = np.array(all_iou)
    all_sens = np.array(all_sens)
    all_prec = np.array(all_prec)

    print("=" * 65)
    print(f"5-Fold CV  (n={len(all_dsc)}, per-sample mean ± SD)\n")
    print(f"  DSC         : {all_dsc.mean():.4f} ± {all_dsc.std():.4f}")
    print(f"  IoU         : {all_iou.mean():.4f} ± {all_iou.std():.4f}")
    print(f"  Sensitivity : {all_sens.mean():.4f} ± {all_sens.std():.4f}")
    print(f"  Precision   : {all_prec.mean():.4f} ± {all_prec.std():.4f}")
    print("=" * 65)

if __name__ == "__main__":
    main()
