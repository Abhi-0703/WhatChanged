"""Unit tests for whatchanged.detect change_score."""

import cv2
import numpy as np
import pytest
from whatchanged.detect import change_score


def test_identical_frames():
    # Base synthetic frame: a gradient or texture to simulate a room scene
    base = np.zeros((240, 320, 3), dtype=np.uint8)
    base[:, :] = (100, 110, 120)
    # Add some pattern
    base[50:150, 50:150] = (150, 160, 170)

    score = change_score(base, base.copy())
    assert score < 0.1, f"Expected score < 0.1 for identical frames, got {score}"


def test_uniform_brightness_shift():
    # Base synthetic frame
    base = np.zeros((240, 320, 3), dtype=np.uint8)
    base[:, :] = (80, 80, 80)
    base[60:140, 60:140] = (120, 120, 120)

    # Shift brightness by +40 across all pixels
    shifted = np.clip(base.astype(np.int16) + 40, 0, 255).astype(np.uint8)

    score = change_score(base, shifted)
    assert score < 1.0, f"Expected score < 1.0 for uniform brightness shift (+40), got {score}"


def test_small_gaussian_noise():
    base = np.full((240, 320, 3), 128, dtype=np.uint8)
    # Add small Gaussian noise with standard deviation 4
    np.random.seed(42)
    noise = np.random.normal(0, 4, base.shape)
    noisy = np.clip(base.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    score = change_score(base, noisy)
    assert score < 1.0, f"Expected score < 1.0 for sensor noise, got {score}"


def test_20_percent_rectangle_added():
    base = np.full((240, 320, 3), 50, dtype=np.uint8)
    modified = base.copy()

    # Total area is 320 * 240 = 76,800.
    # 20% area = ~15,360 pixels. A rectangle of 160 x 100 is 16,000 pixels (~20.8% area)
    # Give it high contrast (white: 255 vs dark: 50)
    modified[70:170, 80:240] = (255, 255, 255)

    score = change_score(base, modified)
    assert score > 5.0, f"Expected score > 5.0 when 20% area object added, got {score}"


def test_roi_excludes_rectangle():
    base = np.full((240, 320, 3), 50, dtype=np.uint8)
    modified = base.copy()

    # Add object in the right half of the image: x from 0.6 to 0.9, y from 0.2 to 0.8
    total_w, total_h = 320, 240
    x1, x2 = int(0.6 * total_w), int(0.9 * total_w)
    y1, y2 = int(0.2 * total_h), int(0.8 * total_h)
    modified[y1:y2, x1:x2] = (255, 255, 255)

    # Set ROI to left half of the image: x in [0.0, 0.5], y in [0.0, 1.0]
    roi = (0.0, 0.0, 0.5, 1.0)

    score_without_roi = change_score(base, modified)
    score_with_roi = change_score(base, modified, roi=roi)

    assert score_without_roi > 5.0
    assert score_with_roi < 1.0, f"Expected score < 1.0 when ROI excludes change, got {score_with_roi}"
