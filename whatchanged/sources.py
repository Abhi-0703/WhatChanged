"""Frame sources for What Changed?

Provides a unified interface across webcams, phone IP streams, video files,
and image folders (for testing and offline replay).
"""

from abc import ABC, abstractmethod
from pathlib import Path
import os
import glob
from typing import Optional
import cv2
import numpy as np


class FrameSource(ABC):
    """Abstract base class for all frame sources."""

    @abstractmethod
    def read(self) -> Optional[np.ndarray]:
        """Read the next BGR frame as a numpy array, or None if unavailable."""
        pass

    def close(self) -> None:
        """Release underlying resources (cameras, files, streams)."""
        pass

    def __enter__(self) -> "FrameSource":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


class WebcamSource(FrameSource):
    """Captures frames from a local webcam, clearing buffered frames."""

    def __init__(self, index: int = 0) -> None:
        self.index = index
        self._cap: Optional[cv2.VideoCapture] = None
        self._init_capture()

    def _init_capture(self) -> None:
        try:
            self._cap = cv2.VideoCapture(self.index)
        except Exception:
            self._cap = None

    def read(self) -> Optional[np.ndarray]:
        if self._cap is None or not self._cap.isOpened():
            self._init_capture()
            if self._cap is None or not self._cap.isOpened():
                return None

        try:
            # Discard 2 to 3 buffered frames to prevent stale reads
            for _ in range(2):
                self._cap.grab()
            ret, frame = self._cap.read()
            if ret and frame is not None and frame.size > 0:
                return frame
        except Exception:
            pass
        return None

    def close(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None


class UrlSource(FrameSource):
    """Reads frames from an IP camera stream or MJPEG/HTTP video endpoint."""

    def __init__(self, url: str) -> None:
        self.url = url
        self._cap: Optional[cv2.VideoCapture] = None
        self._init_capture()

    def _init_capture(self) -> None:
        try:
            self._cap = cv2.VideoCapture(self.url)
        except Exception:
            self._cap = None

    def read(self) -> Optional[np.ndarray]:
        if self._cap is None or not self._cap.isOpened():
            self._init_capture()
            if self._cap is None or not self._cap.isOpened():
                return None

        try:
            ret, frame = self._cap.read()
            if ret and frame is not None and frame.size > 0:
                return frame
        except Exception:
            pass
        return None

    def close(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None


class VideoFileSource(FrameSource):
    """Advances through a recorded video file, looping on completion."""

    def __init__(self, path: str | Path, step_seconds: float = 1.0) -> None:
        self.path = str(path)
        self.step_seconds = max(0.1, step_seconds)
        self._cap: Optional[cv2.VideoCapture] = None
        self._fps: float = 30.0
        self._init_capture()

    def _init_capture(self) -> None:
        try:
            self._cap = cv2.VideoCapture(self.path)
            if self._cap.isOpened():
                fps = self._cap.get(cv2.CAP_PROP_FPS)
                if fps and fps > 0:
                    self._fps = fps
        except Exception:
            self._cap = None

    def read(self) -> Optional[np.ndarray]:
        if self._cap is None or not self._cap.isOpened():
            self._init_capture()
            if self._cap is None or not self._cap.isOpened():
                return None

        try:
            # Advance by step_seconds
            current_frame = self._cap.get(cv2.CAP_PROP_POS_FRAMES)
            frames_to_advance = max(1, int(self._fps * self.step_seconds))

            ret, frame = self._cap.read()
            if not ret or frame is None:
                # Loop back to beginning
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self._cap.read()

            if ret and frame is not None:
                # Seek forward for next step
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame + frames_to_advance)
                return frame
        except Exception:
            pass
        return None

    def close(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None


class ImageFolderSource(FrameSource):
    """Steps through sorted images in a directory, looping indefinitely."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.files: list[Path] = []
        self._index: int = 0
        self._refresh_files()

    def _refresh_files(self) -> None:
        if not self.path.exists() or not self.path.is_dir():
            self.files = []
            return

        extensions = ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp")
        found: list[Path] = []
        for ext in extensions:
            found.extend(self.path.glob(ext))
            found.extend(self.path.glob(ext.upper()))

        # Deduplicate and sort alphabetically
        self.files = sorted(list(set(found)), key=lambda p: p.name)

    def read(self) -> Optional[np.ndarray]:
        if not self.files:
            self._refresh_files()
            if not self.files:
                return None

        file_path = self.files[self._index]
        self._index = (self._index + 1) % len(self.files)

        try:
            frame = cv2.imread(str(file_path))
            if frame is not None and frame.size > 0:
                return frame
        except Exception:
            pass
        return None

    def close(self) -> None:
        self._index = 0


def open_source(spec: str) -> FrameSource:
    """Factory creating the appropriate FrameSource from user input specification.

    - Digits ("0", "1") -> WebcamSource(index)
    - "http://" or "https://" -> UrlSource(url)
    - Existing Directory -> ImageFolderSource(path)
    - Existing File -> VideoFileSource(path)
    - Anything else -> raises ValueError
    """
    clean = spec.strip()
    if clean.isdigit():
        return WebcamSource(int(clean))

    if clean.startswith("http://") or clean.startswith("https://"):
        return UrlSource(clean)

    p = Path(clean)
    if p.exists():
        if p.is_dir():
            return ImageFolderSource(p)
        if p.is_file():
            return VideoFileSource(p)

    raise ValueError(f"Invalid or non-existent frame source specification: {spec}")
