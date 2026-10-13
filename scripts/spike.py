"""Integration spike script: evaluates two-image vs side-by-side mode on Gemma 4."""

import argparse
from pathlib import Path
import sys
import time

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from whatchanged.config import Settings
from whatchanged.backends import get_backend
from whatchanged.imaging import to_jpeg_bytes, side_by_side


def create_spike_images() -> tuple[np.ndarray, np.ndarray]:
    """Generates a synthetic before/after image pair: an object added on a desk."""
    # BEFORE frame: clean desk surface
    before = np.full((480, 640, 3), 180, dtype=np.uint8)
    # Add wood desk grain/shadows
    before[240:, :] = 140

    # AFTER frame: bright blue notebook added on the desk
    after = before.copy()
    after[280:420, 260:440] = (220, 100, 30)  # BGR blue object

    return before, after


def main():
    parser = argparse.ArgumentParser(description="Spike test for Gemma 4 vision backends")
    parser.add_argument("--backend", default="ollama", choices=["ollama", "gemini", "fake"])
    parser.add_argument("--mode", default="side_by_side", choices=["side_by_side", "two_images"])
    args = parser.parse_args()

    settings = Settings.from_env()
    settings.backend = args.backend
    settings.image_mode = args.mode

    print(f"=== Running Spike Test ===")
    print(f"Backend: {settings.backend}")
    print(f"Image Mode: {settings.image_mode}")
    print(f"Ollama Model: {settings.ollama_model} at {settings.ollama_host}")
    print(f"Gemini Model: {settings.gemini_model}")

    backend = get_backend(args.backend, settings)
    is_avail, msg = backend.is_available()
    print(f"Backend availability check: {is_avail} ({msg})")

    before, after = create_spike_images()
    rules = ["notify me if an object is placed on the desk"]

    print("Sending request to backend...")
    t0 = time.time()
    report = backend.describe_change(before, after, rules)
    latency_ms = int((time.time() - t0) * 1000)

    print(f"\n--- Result ({latency_ms} ms) ---")
    print(f"Parse Error: {report.parse_error}")
    print(f"Changes: {report.changes}")
    print(f"Triggered Rule IDs: {report.triggered_rule_ids}")
    print(f"Raw Output: {report.raw[:300]}")
    print("=========================")


if __name__ == "__main__":
    main()
