"""Cheap change detector for What Changed?

Uses lightweight OpenCV operations with brightness normalization and optional ROI
to determine whether a scene has changed enough to warrant calling Gemma 4.
"""

from typing import Optional, Tuple
import cv2
import numpy as np


def change_score(
    prev: np.ndarray,
    curr: np.ndarray,
    *,
    size: Tuple[int, int] = (320, 240),
    blur: int = 21,
    pixel_threshold: int = 25,
    roi: Optional[Tuple[float, float, float, float]] = None,
) -> float:
    """Calculates the percentage of pixels that changed between two frames.

    Args:
        prev: The reference BGR frame (numpy array).
        curr: The current candidate BGR frame (numpy array).
        size: Target (width, height) to resize frames for fast comparison.
        blur: Kernel size for Gaussian blur (must be an odd integer).
        pixel_threshold: Minimum brightness difference (0-255) to consider a pixel changed.
        roi: Optional tuple (x, y, w, h) with values as fractions [0.0, 1.0].
             If provided, comparison is restricted to this region.

    Returns:
        float: Percentage of pixels changed in [0.0, 100.0].
    """
    if prev is None or curr is None or prev.size == 0 or curr.size == 0:
        return 0.0

    # 1. Resize to target size for consistent, fast computation
    prev_resized = cv2.resize(prev, size)
    curr_resized = cv2.resize(curr, size)

    # 2. Extract Region of Interest if provided
    if roi is not None:
        rx, ry, rw, rh = roi
        total_w, total_h = size

        x1 = max(0, min(total_w - 1, int(rx * total_w)))
        y1 = max(0, min(total_h - 1, int(ry * total_h)))
        x2 = max(x1 + 1, min(total_w, int((rx + rw) * total_w)))
        y2 = max(y1 + 1, min(total_h, int((ry + rh) * total_h)))

        prev_resized = prev_resized[y1:y2, x1:x2]
        curr_resized = curr_resized[y1:y2, x1:x2]

    # 3. Convert to grayscale
    if len(prev_resized.shape) == 3 and prev_resized.shape[2] == 3:
        prev_gray = cv2.cvtColor(prev_resized, cv2.COLOR_BGR2GRAY)
    else:
        prev_gray = prev_resized

    if len(curr_resized.shape) == 3 and curr_resized.shape[2] == 3:
        curr_gray = cv2.cvtColor(curr_resized, cv2.COLOR_BGR2GRAY)
    else:
        curr_gray = curr_resized

    # 4. Gaussian blur to suppress camera sensor noise
    k = blur if blur % 2 == 1 else blur + 1
    k = max(1, k)
    prev_blurred = cv2.GaussianBlur(prev_gray, (k, k), 0)
    curr_blurred = cv2.GaussianBlur(curr_gray, (k, k), 0)

    # 5. Brightness normalization: shift curr so its mean equals prev's mean
    # This prevents false alarms when room lights are toggled or sun shifts
    mean_prev = float(np.mean(prev_blurred))
    mean_curr = float(np.mean(curr_blurred))
    shift = mean_prev - mean_curr

    curr_norm = np.clip(curr_blurred.astype(np.float32) + shift, 0.0, 255.0).astype(np.uint8)

    # 6. Absolute difference and threshold count
    diff = cv2.absdiff(prev_blurred, curr_norm)
    changed_pixels = int(np.count_nonzero(diff > pixel_threshold))
    total_pixels = int(diff.size)

    if total_pixels == 0:
        return 0.0

    return float((changed_pixels / total_pixels) * 100.0)
