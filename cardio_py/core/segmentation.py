"""
Segmentation
=============
ROI detection for cardiac organoid videos.

Method A: Otsu thresholding (always available)
Method B: U-Net deep learning (ResNet-34 encoder, trained on 73 annotated frames)

Ported from predictMyocardiumUNet.m / ExternalLab_Inference_v1.m
"""

import sys
import numpy as np
import cv2
from pathlib import Path
from scipy.ndimage import binary_fill_holes
from skimage.measure import label


def _resolve_weights() -> Path:
    if getattr(sys, "frozen", False):
        # PyInstaller 6+ puts bundled data under _internal/ (sys._MEIPASS).
        # Collab edition bundles the model there; main app downloads beside the exe.
        meipass_path = Path(getattr(sys, "_MEIPASS", "")) / "annotation_tool" / "best_model.pth"
        if meipass_path.exists():
            return meipass_path
        return Path(sys.executable).parent / "annotation_tool" / "best_model.pth"
    return Path(__file__).parent.parent.parent / "annotation_tool" / "best_model.pth"


_UNET_WEIGHTS = _resolve_weights()

# ImageNet normalisation constants (must match training)
_IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_IMAGENET_STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)

_unet_model = None  # lazy-loaded singleton


def _load_unet():
    global _unet_model
    if _unet_model is not None:
        return _unet_model
    try:
        import torch
        import segmentation_models_pytorch as smp
    except ImportError as e:
        raise ImportError(f"U-Net requires torch and segmentation-models-pytorch: {e}")

    ckpt = torch.load(str(_UNET_WEIGHTS), map_location="cpu", weights_only=False)
    cfg  = ckpt["config"]
    model = smp.Unet(
        encoder_name=cfg["encoder_name"],
        encoder_weights=None,
        in_channels=cfg["in_channels"],
        classes=cfg["classes"],
    )
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    _unet_model = model
    return model


def segment_unet(
    frame_rgb: np.ndarray,
    min_pct: float = 0.15,
    max_pct: float = 50.0,
    threshold: float = 0.5,
) -> tuple[list[np.ndarray], int]:
    """
    Segment organoids using the trained ResNet-34 U-Net.

    Parameters
    ----------
    frame_rgb : RGB image (H, W, 3)
    min_pct   : minimum ROI area as % of total pixels
    max_pct   : maximum ROI area as % of total pixels
    threshold : sigmoid threshold for binarisation (default 0.5)

    Returns
    -------
    masks  : list of boolean masks (H, W), one per ROI
    n_rois : number of ROIs found
    """
    import torch

    H, W = frame_rgb.shape[:2]
    model = _load_unet()

    # Pre-process: resize → normalise → NCHW tensor
    img = cv2.resize(frame_rgb, (512, 512)).astype(np.float32) / 255.0
    img = (img - _IMAGENET_MEAN) / _IMAGENET_STD
    tensor = torch.from_numpy(img.transpose(2, 0, 1)).unsqueeze(0)  # (1,3,512,512)

    with torch.no_grad():
        pred = torch.sigmoid(model(tensor))[0, 0].numpy()  # (512,512) float32

    # Resize back to original resolution
    pred_full = cv2.resize(pred, (W, H), interpolation=cv2.INTER_LINEAR)
    binary = pred_full >= threshold

    # Fill holes and filter by area (same logic as Otsu path)
    filled = binary_fill_holes(binary)
    total_pixels = H * W
    min_pixels = max(1, round(min_pct / 100 * total_pixels))
    max_pixels = round(max_pct / 100 * total_pixels)

    labeled = label(filled)
    masks = []
    for region_id in range(1, labeled.max() + 1):
        region = labeled == region_id
        area = int(region.sum())
        if area < min_pixels or area > max_pixels:
            continue
        masks.append(region)

    return masks, len(masks)


def segment_otsu(
    frame_rgb: np.ndarray,
    min_pct: float = 0.15,
    max_pct: float = 50.0,
) -> tuple[list[np.ndarray], int]:
    """
    Segment organoids using Otsu's thresholding.
    Matches MATLAB: graythresh → imbinarize → ~BW → imfill → bwareaopen(min) & ~bwareaopen(max)

    Assumes bright background / dark organoids.

    Parameters
    ----------
    frame_rgb : RGB image (H, W, 3)
    min_pct   : minimum ROI area as % of total pixels (default 0.15, same as MATLAB)
    max_pct   : maximum ROI area as % of total pixels (default 50.0, same as MATLAB)

    Returns
    -------
    masks  : list of boolean masks (H, W), one per ROI
    n_rois : number of ROIs found
    """
    gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)

    # Otsu threshold — matches MATLAB: graythresh → imbinarize → ~BW
    # Organoids are darker than surrounding cells; ~BW makes them foreground.
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    foreground = bw == 0  # ~BW: dark regions become True

    # Fill holes (MATLAB: imfill(~BW, 'holes'))
    filled = binary_fill_holes(foreground)

    # Convert % → pixels
    total_pixels = gray.size
    min_pixels = max(1, round(min_pct / 100 * total_pixels))
    max_pixels = round(max_pct / 100 * total_pixels)

    # Label and filter by area (matches MATLAB: bwareaopen(min) & ~bwareaopen(max))
    labeled = label(filled)
    masks = []
    for region_id in range(1, labeled.max() + 1):
        region = labeled == region_id
        area = int(region.sum())
        if area < min_pixels:
            continue
        if area > max_pixels:
            continue
        masks.append(region)

    return masks, len(masks)
