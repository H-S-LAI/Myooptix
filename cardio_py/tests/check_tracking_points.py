"""
追蹤點偵測的自我驗證（不依賴 MATLAB 輸出）。

檢查三件事，全部以程式自身的行為為準：
  1. 每顆 ROI 都分到足夠的追蹤點，且沒有 500 點的全域上限
  2. 追蹤點落在類器官本體上（舊版把背景塗黑，角點全部出現在 ROI 邊界外緣）
  3. 同一支影片中，拿掉一顆 ROI 不會改變其他顆的點數（舊版會互相排擠）

用法：python cardio_py/tests/check_tracking_points.py [影片路徑] [舊版 tracking.py 路徑]
舊版路徑可省略；給了就一併做新舊對照。
"""
import sys, os, importlib.util
import warnings; warnings.filterwarnings('ignore')
import numpy as np, cv2

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from cardio_py.core.io import read_first_frame
from cardio_py.core.segmentation import segment_unet
import cardio_py.core.tracking as new_trk

VIDEO = sys.argv[1] if len(sys.argv) > 1 else '/Users/ottiblai/Desktop/cardioproj/files/ctrl/D4/1.MOV'
OLD   = sys.argv[2] if len(sys.argv) > 2 else None

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def points_per_roi(mod, gray, masks):
    """重現該版本的找點方式，回傳每顆 ROI 的點座標。"""
    dil = [mod._dilate_mask(m) for m in masks]
    lm = np.zeros(gray.shape, np.int32)
    for i, d in enumerate(dil): lm[d] = i + 1
    fp = mod._FEATURE_PARAMS
    if fp['maxCorners'] > 0:                       # 舊版：整張塗黑後一次找點
        g = gray.copy(); g[lm == 0] = 0
        p = cv2.goodFeaturesToTrack(g, **fp)
        if p is None: return [np.empty((0, 2)) for _ in masks]
        p = p.reshape(-1, 2)
        ids = lm[np.minimum(np.round(p[:, 1]).astype(int), gray.shape[0] - 1),
                 np.minimum(np.round(p[:, 0]).astype(int), gray.shape[1] - 1)]
        return [p[ids == i + 1] for i in range(len(masks))]
    out = []                                        # 新版：每顆各自以 mask 找點
    for i in range(len(masks)):
        p = cv2.goodFeaturesToTrack(gray, mask=(lm == i + 1).astype(np.uint8) * 255, **fp)
        out.append(np.empty((0, 2)) if p is None else p.reshape(-1, 2))
    return out

def in_body(pts, mask):
    if len(pts) == 0: return float('nan')
    h, w = mask.shape
    return float(np.mean([mask[min(int(round(y)), h - 1), min(int(round(x)), w - 1)] for x, y in pts]))

frame, fps = read_first_frame(VIDEO)
gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
masks, n = segment_unet(frame, min_pct=0.15, max_pct=50.0)
print(f"影片 {os.path.basename(VIDEO)}｜U-Net 切出 {n} 顆\n")

new_pts = points_per_roi(new_trk, gray, masks)
old_pts = points_per_roi(load(OLD, 'trk_old'), gray, masks) if OLD else None

hdr = f"{'ROI':>4s}{'新版點數':>9s}{'新版在體內':>11s}"
if OLD: hdr += f"{'舊版點數':>9s}{'舊版在體內':>11s}{'倍數':>7s}"
print(hdr)
for i, m in enumerate(masks):
    line = f"{i+1:>4d}{len(new_pts[i]):>9d}{in_body(new_pts[i], m)*100:>10.0f}%"
    if OLD:
        o = len(old_pts[i]); r = (len(new_pts[i]) / o) if o else float('inf')
        line += f"{o:>9d}{in_body(old_pts[i], m)*100:>10.0f}%{r:>7.1f}x"
    print(line)

nn = [len(p) for p in new_pts]
print(f"\n新版：總點數 {sum(nn)}，最少的一顆 {min(nn)} 點，落在體內中位數 "
      f"{np.nanmedian([in_body(p, m) for p, m in zip(new_pts, masks)])*100:.0f}%")
if OLD:
    oo = [len(p) for p in old_pts]
    print(f"舊版：總點數 {sum(oo)}（500 點上限），最少的一顆 {min(oo)} 點，落在體內中位數 "
          f"{np.nanmedian([in_body(p, m) for p, m in zip(old_pts, masks)])*100:.0f}%")

print("\n=== 拿掉一顆 ROI，其他顆的點數會不會變 ===")
drop = int(np.argmax([len(p) for p in new_pts]))
sub = [m for j, m in enumerate(masks) if j != drop]
for name, mod, full, label in ([('新版', new_trk, new_pts, '新版')] +
                               ([('舊版', load(OLD, 'trk_old2'), old_pts, '舊版')] if OLD else [])):
    sub_pts = points_per_roi(mod, gray, sub)
    before = [len(p) for j, p in enumerate(full) if j != drop]
    after  = [len(p) for p in sub_pts]
    changed = sum(1 for a, b in zip(before, after) if a != b)
    print(f"  {label}：拿掉第 {drop+1} 顆後，其餘 {len(before)} 顆中有 {changed} 顆點數改變")

ok = min(nn) > 0 and np.nanmedian([in_body(p, m) for p, m in zip(new_pts, masks)]) > 0.5
print("\n結果:", "通過" if ok else "不通過")
sys.exit(0 if ok else 1)
