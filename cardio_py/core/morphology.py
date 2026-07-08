"""
Organoid morphology measurement from binary segmentation mask.
"""

import numpy as np


def compute_mask_morphology(mask: np.ndarray, scale_um_per_px: float) -> dict:
    """
    Compute equivalent diameter from a binary mask.

    Parameters
    ----------
    mask           : 2-D bool array (H, W)
    scale_um_per_px: µm per pixel (e.g. 2.915 for TCY_4X)

    Returns
    -------
    dict with keys:
        equivalent_diameter_um : float  (µm)
        area_um2               : float  (µm²)
    """
    area_px = float(np.count_nonzero(mask))
    if area_px == 0:
        return {"equivalent_diameter_um": float("nan"), "area_um2": float("nan")}

    area_um2 = area_px * (scale_um_per_px ** 2)
    equiv_diam_um = 2.0 * np.sqrt(area_um2 / np.pi)

    return {
        "equivalent_diameter_um": round(equiv_diam_um, 2),
        "area_um2": round(area_um2, 2),
    }
