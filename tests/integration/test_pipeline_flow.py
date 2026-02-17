import pytest
from unittest.mock import MagicMock
import sys
import os

# Mock the ultralytics module BEFORE importing download_model
sys.modules["ultralytics"] = MagicMock()
from ultralytics import YOLO

# Import the script to test
from training.download_model import download_model

def test_download_model_logic(mocker, tmp_path):
    """Verify download_model attempts to instantiate YOLO with correct path."""
    
    # Mock os.path.exists to return False so it tries to download
    mocker.patch("os.path.exists", return_value=False)
    
    # Spy on the YOLO constructor
    yolo_mock = sys.modules["ultralytics"].YOLO
    
    download_model()
    
    # Verify it was called with the correct path
    yolo_mock.assert_called_with("/opt/training/yolov8n.pt")
