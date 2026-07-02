"""
MyoOptix Annotator — single overlay, lasso mode
"""

import cv2
import numpy as np
import os, glob, re, json, time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FRAME_DIR  = os.path.join(SCRIPT_DIR, "input_frames")
INIT_DIR   = os.path.join(SCRIPT_DIR, "initial_masks")
OUT_DIR    = os.path.join(SCRIPT_DIR, "output_masks")
FLAGS_PATH = os.path.join(SCRIPT_DIR, "flags.json")

os.makedirs(OUT_DIR, exist_ok=True)

WIN_W = 1280
WIN_H = 720

def natural_key(p):
    nums = re.findall(r"\d+", os.path.basename(p))
    return int(nums[-1]) if nums else 0

frame_paths = sorted(glob.glob(os.path.join(FRAME_DIR, "raw_*.png")), key=natural_key)
N = len(frame_paths)
if N == 0:
    raise SystemExit(f"No images found: {FRAME_DIR}")

# ── persistent state ──────────────────────────────────────────────────────────
saved_set   = set()
flagged_set = set()

def load_flags():
    if os.path.exists(FLAGS_PATH):
        d = json.loads(open(FLAGS_PATH).read())
        return set(d.get("flagged", []))
    return set()

def save_flags():
    with open(FLAGS_PATH, "w") as f:
        json.dump({"flagged": sorted(flagged_set)}, f, indent=2)

flagged_set = load_flags()

# ── current image state ───────────────────────────────────────────────────────
current_idx = 0
frame_img   = None
mask        = None
undo_stack  = []          # list of mask snapshots (np.ndarray)
save_flash  = 0.0         # timestamp of last save (for flash message)

# display params (updated on image load)
disp_x0 = disp_y0 = 0
disp_w = WIN_W
disp_h = WIN_H
scale  = 1.0

# lasso state (coords in original image space)
lasso_pts  = []
lasso_mode = None   # "add" | "remove" | None

UNDO_LIMIT = 30


def stem_of(idx):
    return os.path.splitext(os.path.basename(frame_paths[idx]))[0]


def compute_display_params(img_h, img_w):
    global disp_x0, disp_y0, disp_w, disp_h, scale
    s = min(WIN_W / img_w, WIN_H / img_h)
    scale   = s
    disp_w  = int(img_w * s)
    disp_h  = int(img_h * s)
    disp_x0 = (WIN_W - disp_w) // 2
    disp_y0 = (WIN_H - disp_h) // 2


def d2i(dx, dy):
    img_h, img_w = frame_img.shape[:2]
    ix = int((dx - disp_x0) / scale)
    iy = int((dy - disp_y0) / scale)
    return max(0, min(img_w - 1, ix)), max(0, min(img_h - 1, iy))


def i2d(ix, iy):
    return int(ix * scale + disp_x0), int(iy * scale + disp_y0)


def push_undo():
    undo_stack.append(mask.copy())
    if len(undo_stack) > UNDO_LIMIT:
        undo_stack.pop(0)


def load_mask(idx):
    stem = stem_of(idx)
    out  = os.path.join(OUT_DIR,  stem + "_mask.png")
    ini  = os.path.join(INIT_DIR, stem + "_mask.png")
    src  = out if os.path.exists(out) else ini
    if os.path.exists(src):
        m = cv2.imread(src, cv2.IMREAD_GRAYSCALE)
        _, m = cv2.threshold(m, 127, 255, cv2.THRESH_BINARY)
        if os.path.exists(out):
            saved_set.add(idx)
        return m
    h, w = frame_img.shape[:2]
    return np.zeros((h, w), dtype=np.uint8)


def save_mask(idx):
    global save_flash
    cv2.imwrite(os.path.join(OUT_DIR, stem_of(idx) + "_mask.png"), mask)
    saved_set.add(idx)
    save_flash = time.time()


def build_display():
    overlay = frame_img.copy()
    green   = np.zeros_like(overlay)
    green[mask > 127] = (0, 200, 0)
    blended = cv2.addWeighted(overlay, 1.0, green, 0.45, 0)

    scaled = cv2.resize(blended, (disp_w, disp_h), interpolation=cv2.INTER_LINEAR)

    canvas = np.zeros((WIN_H, WIN_W, 3), dtype=np.uint8)
    canvas[disp_y0:disp_y0 + disp_h, disp_x0:disp_x0 + disp_w] = scaled

    # lasso preview
    if len(lasso_pts) >= 2:
        dpts  = np.array([i2d(p[0], p[1]) for p in lasso_pts], dtype=np.int32)
        color = (50, 255, 50) if lasso_mode == "add" else (50, 50, 255)
        cv2.polylines(canvas, [dpts], False, color, 2, cv2.LINE_AA)
        cv2.circle(canvas, tuple(dpts[0]), 5, color, -1)

    # hint text
    undo_hint = f"  Z:Undo({len(undo_stack)})" if undo_stack else "  Z:Undo"
    hints = [
        "LClick:Add  RClick:Remove" + undo_hint,
        "S:Save  A:Prev  D:Next(save)  R:Reset  F:Flag  Q:Quit",
    ]
    for i, t in enumerate(hints):
        cv2.putText(canvas, t, (disp_x0 + 8, disp_y0 + 28 + i * 26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 240, 240), 2, cv2.LINE_AA)

    # save flash (show "SAVED!" for 1.5 s)
    if time.time() - save_flash < 1.5:
        msg = "SAVED!"
        (tw, th), _ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 1.6, 3)
        tx = disp_x0 + (disp_w - tw) // 2
        ty = disp_y0 + (disp_h + th) // 2
        cv2.putText(canvas, msg, (tx, ty),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 0),   6, cv2.LINE_AA)
        cv2.putText(canvas, msg, (tx, ty),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.6, (80, 255, 80), 3, cv2.LINE_AA)

    return canvas


def refresh():
    disp = build_display()
    stem = stem_of(current_idx)
    k    = len(saved_set)
    marks = ("  [saved]" if current_idx in saved_set else "") + \
            ("  [FLAG]"  if current_idx in flagged_set else "")
    cv2.setWindowTitle("annotator",
        f"MyoOptix  {stem}.png  [{current_idx+1}/{N}]  saved:{k}{marks}")
    cv2.imshow("annotator", disp)


def go_to(idx, autosave=False):
    global current_idx, frame_img, mask, lasso_pts, lasso_mode
    if autosave:
        save_mask(current_idx)
    lasso_pts  = []
    lasso_mode = None
    undo_stack.clear()
    current_idx = idx % N
    frame_img   = cv2.imread(frame_paths[current_idx])
    compute_display_params(*frame_img.shape[:2])
    mask = load_mask(current_idx)
    refresh()


# ── mouse callback ────────────────────────────────────────────────────────────
def mouse_cb(event, x, y, flags, param):
    global lasso_pts, lasso_mode, mask

    if event == cv2.EVENT_LBUTTONDOWN:
        push_undo()
        lasso_pts  = [d2i(x, y)]
        lasso_mode = "add"

    elif event == cv2.EVENT_RBUTTONDOWN:
        push_undo()
        lasso_pts  = [d2i(x, y)]
        lasso_mode = "remove"

    elif event == cv2.EVENT_MOUSEMOVE and lasso_mode is not None:
        lasso_pts.append(d2i(x, y))
        refresh()

    elif event in (cv2.EVENT_LBUTTONUP, cv2.EVENT_RBUTTONUP):
        if lasso_mode is not None and len(lasso_pts) >= 3:
            pts   = np.array(lasso_pts, dtype=np.int32)
            color = 255 if lasso_mode == "add" else 0
            cv2.fillPoly(mask, [pts], color)
        else:
            # too few points → discard this undo snapshot
            if undo_stack:
                undo_stack.pop()
        lasso_pts  = []
        lasso_mode = None
        refresh()


# ── main loop ─────────────────────────────────────────────────────────────────
cv2.namedWindow("annotator", cv2.WINDOW_AUTOSIZE)
cv2.setMouseCallback("annotator", mouse_cb)

go_to(0)

while True:
    key = cv2.waitKey(20) & 0xFF

    if key in (ord('q'), ord('Q'), 27):
        break
    elif key in (ord('s'), ord('S')):
        save_mask(current_idx)
        refresh()
    elif key in (ord('d'), ord('D')):
        go_to(current_idx + 1, autosave=True)
    elif key in (ord('a'), ord('A')):
        go_to(current_idx - 1)
    elif key in (ord('z'), ord('Z')):
        if undo_stack:
            mask = undo_stack.pop()
            refresh()
    elif key in (ord('r'), ord('R')):
        stem = stem_of(current_idx)
        ini  = os.path.join(INIT_DIR, stem + "_mask.png")
        push_undo()
        if os.path.exists(ini):
            m = cv2.imread(ini, cv2.IMREAD_GRAYSCALE)
            _, mask = cv2.threshold(m, 127, 255, cv2.THRESH_BINARY)
        else:
            mask = np.zeros(frame_img.shape[:2], dtype=np.uint8)
        refresh()
    elif key in (ord('f'), ord('F')):
        if current_idx in flagged_set:
            flagged_set.discard(current_idx)
        else:
            flagged_set.add(current_idx)
        save_flags()
        refresh()

cv2.destroyAllWindows()
print(f"Done  saved={len(saved_set)}/{N}  flagged={len(flagged_set)}")
