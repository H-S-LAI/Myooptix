"""
MyoOptix — 預測結果可視化
Usage: python annotation_tool/visualize.py
       python annotation_tool/visualize.py --model fold_1_best.pth --n 8
"""

import os, glob, re, argparse
import numpy as np
import torch
import segmentation_models_pytorch as smp
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from PIL import Image
import albumentations as A
from albumentations.pytorch import ToTensorV2

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
FRAME_DIR     = os.path.join(SCRIPT_DIR, "input_frames")
OUT_MASK_DIR  = os.path.join(SCRIPT_DIR, "output_masks")
INIT_MASK_DIR = os.path.join(SCRIPT_DIR, "initial_masks")
IMG_SIZE      = 512

TRANSFORM = A.Compose([
    A.Resize(IMG_SIZE, IMG_SIZE),
    A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ToTensorV2(),
])

def natural_key(p):
    nums = re.findall(r"\d+", os.path.basename(p))
    return int(nums[-1]) if nums else 0

def load_model(model_path, device):
    ckpt  = torch.load(model_path, map_location=device)
    cfg   = ckpt.get("config", {})
    model = smp.Unet(
        encoder_name    = cfg.get("encoder_name", "resnet34"),
        encoder_weights = None,
        in_channels     = cfg.get("in_channels", 3),
        classes         = cfg.get("classes", 1),
    ).to(device)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    return model

def predict(model, img_np, device):
    out   = TRANSFORM(image=img_np)
    x     = out["image"].unsqueeze(0).to(device)
    with torch.no_grad():
        pred = torch.sigmoid(model(x))[0, 0].cpu().numpy()
    return (pred > 0.5).astype(np.uint8)

def overlay(img, mask, color, alpha=0.45):
    out = img.copy().astype(float)
    for c, v in zip(range(3), color):
        out[:, :, c] = np.where(mask > 0,
                                out[:, :, c] * (1 - alpha) + v * alpha,
                                out[:, :, c])
    return out.astype(np.uint8)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="fold_1_best.pth")
    parser.add_argument("--n",     type=int, default=6)
    parser.add_argument("--out",   default="preview.png")
    args = parser.parse_args()

    model_path = os.path.join(SCRIPT_DIR, args.model)
    if not os.path.exists(model_path):
        # fallback to best_model.pth
        model_path = os.path.join(SCRIPT_DIR, "best_model.pth")
        print(f"Using fallback: {model_path}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model  = load_model(model_path, device)
    print(f"Loaded: {os.path.basename(model_path)}  ({device})")

    frames = sorted(glob.glob(os.path.join(FRAME_DIR, "raw_*.png")), key=natural_key)
    # pick evenly spaced samples
    step    = max(1, len(frames) // args.n)
    samples = frames[::step][:args.n]

    ncols = 3
    nrows = len(samples)
    fig, axes = plt.subplots(nrows, ncols, figsize=(ncols * 4, nrows * 3.5))
    if nrows == 1:
        axes = [axes]

    for row, fp in enumerate(samples):
        stem = os.path.splitext(os.path.basename(fp))[0]

        # load image
        img = np.array(Image.open(fp).convert("RGB"))
        h0, w0 = img.shape[:2]

        # load ground truth mask
        gt_path = os.path.join(OUT_MASK_DIR,  stem + "_mask.png")
        if not os.path.exists(gt_path):
            gt_path = os.path.join(INIT_MASK_DIR, stem + "_mask.png")
        gt = (np.array(Image.open(gt_path).convert("L")) > 127).astype(np.uint8) \
             if os.path.exists(gt_path) else np.zeros((h0, w0), dtype=np.uint8)

        # predict (resize back to original size for display)
        pred_512 = predict(model, img, device)
        pred = np.array(Image.fromarray(pred_512 * 255).resize((w0, h0),
                        Image.NEAREST)) > 127

        # DSC for this image
        tp = (pred & gt.astype(bool)).sum()
        fp = (pred & ~gt.astype(bool)).sum()
        fn = (~pred & gt.astype(bool)).sum()
        dsc = (2 * tp + 1e-6) / (2 * tp + fp + fn + 1e-6)

        # col 0: original
        axes[row][0].imshow(img)
        axes[row][0].set_title(f"{stem}", fontsize=8)
        axes[row][0].axis("off")

        # col 1: ground truth overlay (green)
        axes[row][1].imshow(overlay(img, gt, (0, 220, 0)))
        axes[row][1].set_title("Ground Truth", fontsize=8)
        axes[row][1].axis("off")

        # col 2: prediction overlay (blue) + DSC
        axes[row][2].imshow(overlay(img, pred.astype(np.uint8), (30, 144, 255)))
        axes[row][2].set_title(f"Prediction  DSC={dsc:.3f}", fontsize=8)
        axes[row][2].axis("off")

    # column headers
    for ax, title in zip(axes[0], ["Original", "Ground Truth (green)",
                                    "Prediction (blue)"]):
        ax.set_title(title, fontsize=9, fontweight="bold")

    plt.suptitle(f"U-Net Segmentation Preview  —  {os.path.basename(model_path)}",
                 fontsize=11, y=1.01)
    plt.tight_layout()
    out_path = os.path.join(SCRIPT_DIR, args.out)
    plt.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")

if __name__ == "__main__":
    main()
