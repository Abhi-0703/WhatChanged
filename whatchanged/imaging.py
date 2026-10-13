"""Image processing utilities for What Changed?

Handles downscaling, JPEG encoding, and side-by-side comparative stitching
for vision models.
"""

from typing import Tuple
import cv2
import numpy as np


def to_jpeg_bytes(frame: np.ndarray, max_side: int = 768, quality: int = 85) -> bytes:
    """Resizes frame so max dimension <= max_side and encodes as JPEG bytes."""
    if frame is None or frame.size == 0:
        return b""

    h, w = frame.shape[:2]
    if max(h, w) > max_side:
        scale = max_side / float(max(h, w))
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
    else:
        resized = frame

    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    success, buffer = cv2.imencode(".jpg", resized, encode_params)
    if not success:
        return b""
    return bytes(buffer)


def side_by_side(before: np.ndarray, after: np.ndarray) -> np.ndarray:
    """Stitches before and after frames side-by-side with clear visual headers."""
    if before is None or before.size == 0:
        return after if after is not None else np.zeros((100, 100, 3), dtype=np.uint8)
    if after is None or after.size == 0:
        return before

    # Match heights
    h1, w1 = before.shape[:2]
    h2, w2 = after.shape[:2]
    target_h = min(h1, h2)

    if h1 != target_h:
        new_w1 = max(1, int(w1 * (target_h / float(h1))))
        b_resized = cv2.resize(before, (new_w1, target_h), interpolation=cv2.INTER_AREA)
    else:
        b_resized = before.copy()

    if h2 != target_h:
        new_w2 = max(1, int(w2 * (target_h / float(h2))))
        a_resized = cv2.resize(after, (new_w2, target_h), interpolation=cv2.INTER_AREA)
    else:
        a_resized = after.copy()

    # Draw headers on both panels
    def annotate(img: np.ndarray, text: str, color_bg=(0, 0, 0), color_fg=(255, 255, 255)) -> np.ndarray:
        out = img.copy()
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.7
        thickness = 2
        (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
        # Background bar
        cv2.rectangle(out, (0, 0), (out.shape[1], th + 18), color_bg, -1)
        # Centered or padded text
        cv2.putText(out, text, (10, th + 10), font, scale, color_fg, thickness, cv2.LINE_AA)
        return out

    b_annotated = annotate(b_resized, "BEFORE", color_bg=(30, 30, 30), color_fg=(200, 200, 255))
    a_annotated = annotate(a_resized, "AFTER", color_bg=(20, 50, 20), color_fg=(150, 255, 150))

    # Horizontal concatenation with a 4px separator
    sep = np.full((target_h, 4, 3), (80, 80, 80), dtype=np.uint8)
    stitched = np.hstack([b_annotated, sep, a_annotated])
    return stitched
