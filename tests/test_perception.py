"""Unit tests for Perception and Computer Vision Pipeline."""
import pytest
import numpy as np
from src.perception.colour_segmentation import ColourSegmenter
from src.perception.calibrate import CameraCalibrator
from src.perception.perception_node import PerceptionPipeline


def test_camera_calibrator_transform_roundtrip():
    """Asserts that pixel_to_world and world_to_pixel round trip accurately."""
    calibrator = CameraCalibrator()
    sample_pixels = [
        (320.0, 240.0), # Center
        (100.0, 100.0), # Top left
        (540.0, 380.0), # Bottom right
    ]
    for px, py in sample_pixels:
        wx, wy = calibrator.pixel_to_world(px, py)
        re_px, re_py = calibrator.world_to_pixel(wx, wy)
        assert abs(re_px - px) < 1.0, f"Pixel X roundtrip error: {px} vs {re_px}"
        assert abs(re_py - py) < 1.0, f"Pixel Y roundtrip error: {py} vs {re_py}"


def test_synthetic_detection():
    """Asserts that PerceptionPipeline correctly identifies blocks and mats."""
    pipeline = PerceptionPipeline()
    detections = pipeline.process_frame()

    assert len(detections) >= 4, f"Expected at least 4 objects, found {len(detections)}"

    names = {d.name for d in detections}
    assert "red_block" in names
    assert "green_block" in names
    assert "blue_mat" in names
    assert "yellow_mat" in names

    # Verify world coordinate ranges
    for d in detections:
        assert -150.0 <= d.world_x <= 150.0
        assert 50.0 <= d.world_y <= 250.0
        assert d.world_z > 0.0


def test_get_object_lookup():
    """Asserts that get_object retrieves accurate object by name."""
    pipeline = PerceptionPipeline()
    pipeline.process_frame()

    red_obj = pipeline.get_object("red_block")
    assert red_obj is not None
    assert red_obj.color == "red"
    assert red_obj.obj_type == "block"

    non_existent = pipeline.get_object("non_existent_item")
    assert non_existent is None
