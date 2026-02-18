
import os
import shutil
from pathlib import Path
import cv2
import numpy as np
import yaml
import subprocess

# Setup Paths
TEST_ROOT = Path(__file__).parent / "dummy_data"
IMAGES_TRAIN = TEST_ROOT / "images" / "train"
IMAGES_VAL = TEST_ROOT / "images" / "val"
LABELS_TRAIN = TEST_ROOT / "labels" / "train"
LABELS_VAL = TEST_ROOT / "labels" / "val"
YAML_PATH = TEST_ROOT / "dataset.yaml"

def setup_dummy_data():
    if TEST_ROOT.exists():
        shutil.rmtree(TEST_ROOT)
    
    for p in [IMAGES_TRAIN, IMAGES_VAL, LABELS_TRAIN, LABELS_VAL]:
        p.mkdir(parents=True, exist_ok=True)
        
    # Create dummy image (black square)
    img = np.zeros((64, 64, 3), dtype=np.uint8)
    cv2.imwrite(str(IMAGES_TRAIN / "img1.jpg"), img)
    cv2.imwrite(str(IMAGES_VAL / "img1.jpg"), img)
    
    # Create dummy label (class 0, center box)
    with open(LABELS_TRAIN / "img1.txt", "w") as f:
        f.write("0 0.5 0.5 0.5 0.5")
    with open(LABELS_VAL / "img1.txt", "w") as f:
        f.write("0 0.5 0.5 0.5 0.5")
        
    # Create YAML
    data = {
        "path": str(TEST_ROOT.absolute()),
        "train": "images/train",
        "val": "images/val",
        "names": {0: "dummy_class"}
    }
    
    with open(YAML_PATH, "w") as f:
        yaml.dump(data, f)
        
    print(f"✅ Dummy dataset created at {TEST_ROOT}")
    return YAML_PATH

def run_training_test(yaml_path):
    print("🚀 Running Training Test...")
    cmd = [
        "python", "training/train.py",
        "--data", str(yaml_path),
        "--epochs", "1",
        "--imgsz", "64",
        "--batch", "2"
    ]
    
    result = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='replace')
    
    if result.returncode == 0:
        print("✅ Training Verification Passed!")
        print(result.stdout)
    else:
        print("❌ Training Failed!")
        print(result.stderr)

if __name__ == "__main__":
    try:
        yaml_path = setup_dummy_data()
        run_training_test(yaml_path)
    finally:
        # Cleanup
        if TEST_ROOT.exists():
            shutil.rmtree(TEST_ROOT)
            print("🧹 Cleanup complete.")
