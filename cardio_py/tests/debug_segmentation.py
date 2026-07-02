"""
Debug segmentation — compare Python Otsu mask with MATLAB golden standard mask.
Run: python cardio_py/tests/debug_segmentation.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import numpy as np
import scipy.io
import cv2
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from cardio_py.core.segmentation import segment_otsu

VIDEO_PATH = '/Users/ottiblai/Desktop/cardioproj/20260630_matlabtopython/Ctrl/After/1.mov'

# Load golden standard (contains MATLAB's L_all_organoids mask)
mat_review = scipy.io.loadmat(
    '/Users/ottiblai/Desktop/cardioproj/20260630_matlabtopython/Analysis_20260630/_mat_files_for_review/VID_0001_for_review.mat',
    squeeze_me=True, struct_as_record=False
)
rd = mat_review['reviewData']
matlab_mask = rd.L_all_organoids.astype(np.int32)   # labeled mask
matlab_frame = rd.frame1                              # uint8 RGB from MATLAB

# Read first frame from video
cap = cv2.VideoCapture(VIDEO_PATH)
ret, frame_bgr = cap.read()
cap.release()
frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

# Run Python Otsu segmentation
py_masks, n_rois = segment_otsu(frame_rgb, min_pixels=5000)
print(f"Python found {n_rois} ROI(s)")
print(f"MATLAB mask unique labels: {np.unique(matlab_mask)}")
print(f"Frame shape: {frame_rgb.shape}  MATLAB frame shape: {matlab_frame.shape}")

# Build Python labeled mask for display
py_labeled = np.zeros(frame_rgb.shape[:2], dtype=np.int32)
for i, m in enumerate(py_masks):
    py_labeled[m] = i + 1

# ── Plot ──────────────────────────────────────────────────────
fig = plt.figure(figsize=(16, 10))
fig.suptitle("Segmentation Debug: Python Otsu vs MATLAB", fontsize=13, fontweight='bold')
gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.35, wspace=0.25)

# 1. Raw frame (Python)
ax1 = fig.add_subplot(gs[0, 0])
ax1.imshow(frame_rgb)
ax1.set_title('Input frame (Python read)')
ax1.axis('off')

# 2. Python Otsu mask
ax2 = fig.add_subplot(gs[0, 1])
ax2.imshow(frame_rgb)
ax2.imshow(py_labeled > 0, alpha=0.4, cmap='Reds')
ax2.set_title(f'Python Otsu mask ({n_rois} ROI)')
ax2.axis('off')

# 3. MATLAB mask
ax3 = fig.add_subplot(gs[0, 2])
ax3.imshow(matlab_frame)
ax3.imshow(matlab_mask > 0, alpha=0.4, cmap='Blues')
n_matlab = int(matlab_mask.max())
ax3.set_title(f'MATLAB mask ({n_matlab} ROI)')
ax3.axis('off')

# 4. Grayscale histogram (to see why Otsu threshold differs)
ax4 = fig.add_subplot(gs[1, 0])
gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
thresh_val, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
ax4.hist(gray.ravel(), bins=256, color='steelblue', alpha=0.7)
ax4.axvline(thresh_val, color='red', lw=2, label=f'Otsu threshold={thresh_val}')
ax4.set_title('Grayscale histogram + Otsu threshold')
ax4.set_xlabel('Pixel value')
ax4.legend()
ax4.grid(alpha=0.3)

# 5. Overlay comparison side by side
ax5 = fig.add_subplot(gs[1, 1])
diff = (py_labeled > 0).astype(int) - (matlab_mask > 0).astype(int)
im = ax5.imshow(diff, cmap='RdBu', vmin=-1, vmax=1)
ax5.set_title('Mask diff: Red=Python only, Blue=MATLAB only')
ax5.axis('off')
plt.colorbar(im, ax=ax5, fraction=0.046)

# 6. Area stats
ax6 = fig.add_subplot(gs[1, 2])
py_areas  = [int(m.sum()) for m in py_masks]
mat_areas = [int((matlab_mask == i).sum()) for i in range(1, n_matlab + 1)]
x = np.arange(max(len(py_areas), len(mat_areas)))
w = 0.35
ax6.bar(x[:len(py_areas)]  - w/2, py_areas,  w, label='Python', color='steelblue', alpha=0.8)
ax6.bar(x[:len(mat_areas)] + w/2, mat_areas, w, label='MATLAB',  color='orange',   alpha=0.8)
ax6.set_xlabel('ROI index')
ax6.set_ylabel('Area (pixels)')
ax6.set_title('ROI area comparison')
ax6.legend()
ax6.grid(alpha=0.3)

print(f"\nPython ROI areas: {py_areas}")
print(f"MATLAB ROI areas: {mat_areas}")

plt.savefig('/Users/ottiblai/Desktop/cardioproj/20260630_matlabtopython/cardio_py/tests/debug_segmentation.png',
            dpi=130, bbox_inches='tight')
print("Plot saved to cardio_py/tests/debug_segmentation.png")
plt.show()
