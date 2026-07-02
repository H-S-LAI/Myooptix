"""
roi_selector.py
===============
Interactive ROI drawing tool using OpenCV.

Usage
-----
    from cardio_py.core.roi_selector import select_rois

    rois = select_rois(frame_rgb)
    # rois: list of (x, y, w, h) tuples, or [] if cancelled

Controls
--------
    Left-drag   : draw a new bounding box
    Right-click : delete the box under the cursor
    C           : confirm and return ROIs
    R           : reset (clear all boxes)
    Q / Esc     : cancel (return empty list)
"""

import cv2
import numpy as np


_BOX_COLOR     = (0, 200, 80)    # green
_BOX_THICKNESS = 2
_LABEL_COLOR   = (0, 200, 80)
_ACTIVE_COLOR  = (80, 160, 255)  # blue while dragging
_FONT          = cv2.FONT_HERSHEY_SIMPLEX
_FONT_SCALE    = 0.6
_FONT_THICK    = 1


def _draw(canvas, boxes, active_box=None):
    overlay = canvas.copy()
    h, w = canvas.shape[:2]

    for i, (x, y, bw, bh) in enumerate(boxes):
        cv2.rectangle(overlay, (x, y), (x + bw, y + bh), _BOX_COLOR, _BOX_THICKNESS)
        label = f"ROI {i + 1}"
        (tw, th), _ = cv2.getTextSize(label, _FONT, _FONT_SCALE, _FONT_THICK)
        lx = max(x, 0)
        ly = max(y - 6, th + 4)
        cv2.rectangle(overlay, (lx, ly - th - 4), (lx + tw + 4, ly), _BOX_COLOR, -1)
        cv2.putText(overlay, label, (lx + 2, ly - 2), _FONT, _FONT_SCALE, (0, 0, 0), _FONT_THICK)

    if active_box is not None:
        x, y, bw, bh = active_box
        cv2.rectangle(overlay, (x, y), (x + bw, y + bh), _ACTIVE_COLOR, _BOX_THICKNESS)

    # top bar: Save & Compute button + ROI count
    top_h = 36
    cv2.rectangle(overlay, (0, 0), (w, top_h), (30, 30, 30), -1)

    btn_label = "[ C ]  Save & Compute"
    (bw, bh), _ = cv2.getTextSize(btn_label, _FONT, 0.58, 1)
    btn_x, btn_y = 10, top_h // 2 + bh // 2
    btn_color = (50, 180, 80) if boxes else (100, 100, 100)
    cv2.putText(overlay, btn_label, (btn_x, btn_y), _FONT, 0.58, btn_color, 1)

    count_txt = f"{len(boxes)} ROI(s)"
    (cw, _), _ = cv2.getTextSize(count_txt, _FONT, 0.55, 1)
    cv2.putText(overlay, count_txt, (w - cw - 10, top_h // 2 + bh // 2),
                _FONT, 0.55, (255, 255, 100), 1)

    # help bar at bottom
    bar_h = 28
    cv2.rectangle(overlay, (0, h - bar_h), (w, h), (30, 30, 30), -1)
    hint = "Left-drag: draw | Right-click: delete | C: save & compute | R: reset | Q: cancel"
    cv2.putText(overlay, hint, (8, h - 8), _FONT, 0.48, (220, 220, 220), 1)

    return overlay


def _hit_box(boxes, px, py):
    """Return index of box containing point (px, py), or -1."""
    for i, (x, y, bw, bh) in enumerate(boxes):
        if x <= px <= x + bw and y <= py <= y + bh:
            return i
    return -1


def select_rois(frame_rgb: np.ndarray, window_title: str = "MyoOptix — ROI Selector") -> list[tuple]:
    """
    Open an OpenCV window for interactive ROI selection.

    Parameters
    ----------
    frame_rgb    : RGB image (H, W, 3)
    window_title : window title string

    Returns
    -------
    list of (x, y, w, h) tuples (empty if cancelled)
    """
    canvas = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
    boxes  = []

    TOP_H = 36  # height of the clickable button bar

    state = {
        "dragging": False,
        "start":    (0, 0),
        "cur":      (0, 0),
        "action":   None,   # "confirm" | "reset" | "cancel"
    }

    def mouse_cb(event, x, y, flags, _param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # clicking inside the top bar triggers Save & Compute
            if y < TOP_H:
                if boxes:
                    state["action"] = "confirm"
                return
            state["dragging"] = True
            state["start"] = (x, y)
            state["cur"]   = (x, y)

        elif event == cv2.EVENT_MOUSEMOVE and state["dragging"]:
            state["cur"] = (x, y)

        elif event == cv2.EVENT_LBUTTONUP and state["dragging"]:
            state["dragging"] = False
            x0, y0 = state["start"]
            bw, bh = abs(x - x0), abs(y - y0)
            if bw > 5 and bh > 5:
                boxes.append((min(x0, x), min(y0, y), bw, bh))

        elif event == cv2.EVENT_RBUTTONDOWN:
            if y >= TOP_H:
                idx = _hit_box(boxes, x, y)
                if idx >= 0:
                    boxes.pop(idx)

    cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_title, min(frame_rgb.shape[1], 1280), min(frame_rgb.shape[0] + TOP_H, 820))
    cv2.setMouseCallback(window_title, mouse_cb)

    result = []
    while True:
        if state["action"] == "confirm":
            result = list(boxes)
            break
        elif state["action"] == "cancel":
            result = []
            break
        state["action"] = None

        active = None
        if state["dragging"]:
            x0, y0 = state["start"]
            x1, y1 = state["cur"]
            active = (min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))

        display = _draw(canvas, boxes, active_box=active)
        cv2.imshow(window_title, display)

        key = cv2.waitKey(16) & 0xFF
        if key == ord('c') or key == ord('C'):
            result = list(boxes)
            break
        elif key == ord('r') or key == ord('R'):
            boxes.clear()
        elif key == ord('q') or key == ord('Q') or key == 27:
            result = []
            break

    cv2.destroyWindow(window_title)
    return result
