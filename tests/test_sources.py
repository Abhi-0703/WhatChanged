"""Unit tests for whatchanged.sources."""

import cv2
import numpy as np
import pytest
from whatchanged.sources import ImageFolderSource, open_source


def test_open_source_invalid():
    with pytest.raises(ValueError, match="Invalid or non-existent frame source"):
        open_source("nonexistent_folder_or_file_12345")


def test_open_source_webcam_spec():
    source = open_source("0")
    assert hasattr(source, "read")
    source.close()


def test_image_folder_source_order_and_loop(tmp_path):
    # Create 3 synthetic test images in tmp_path
    img1 = np.full((100, 100, 3), 10, dtype=np.uint8)
    img2 = np.full((100, 100, 3), 20, dtype=np.uint8)
    img3 = np.full((100, 100, 3), 30, dtype=np.uint8)

    cv2.imwrite(str(tmp_path / "01.png"), img1)
    cv2.imwrite(str(tmp_path / "02.png"), img2)
    cv2.imwrite(str(tmp_path / "03.png"), img3)

    source = ImageFolderSource(tmp_path)
    assert len(source.files) == 3

    # Read all three frames and verify pixel values
    f1 = source.read()
    assert f1 is not None
    assert f1[0, 0, 0] == 10

    f2 = source.read()
    assert f2 is not None
    assert f2[0, 0, 0] == 20

    f3 = source.read()
    assert f3 is not None
    assert f3[0, 0, 0] == 30

    # Test looping back to the first frame
    f4 = source.read()
    assert f4 is not None
    assert f4[0, 0, 0] == 10

    source.close()


def test_open_source_with_folder(tmp_path):
    img = np.zeros((50, 50, 3), dtype=np.uint8)
    cv2.imwrite(str(tmp_path / "test.jpg"), img)

    source = open_source(str(tmp_path))
    assert isinstance(source, ImageFolderSource)
    frame = source.read()
    assert frame is not None
    source.close()
