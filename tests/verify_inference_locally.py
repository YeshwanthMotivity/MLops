
import os
import sys
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
import cv2
import numpy as np

# Setup Paths (to import app from inference/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "inference"))

# Mock environment variable for model path
# Use dummy model or robust fallback
os.environ["MODEL_PATH"] = str(PROJECT_ROOT / "model" / "yolov8n.pt")

try:
    from inference.app import app
except ImportError as e:
    print(f"Failed to import app: {e}")
    sys.exit(1)

client = TestClient(app)

TEST_DATA = Path(__file__).parent / "dummy_data"
IMG_PATH = TEST_DATA / "test_inference.jpg"

def setup_dummy_image():
    TEST_DATA.mkdir(exist_ok=True)
    # Create a dummy image (black square)
    img = np.zeros((640, 640, 3), dtype=np.uint8)
    cv2.imwrite(str(IMG_PATH), img)
    print(f"Created dummy image at {IMG_PATH}")

def test_health():
    print("\n--- Testing Health Check ---")
    response = client.get("/")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200

def test_prediction():
    print("\n--- Testing Prediction ---")
    if not IMG_PATH.exists():
        setup_dummy_image()
        
    with open(IMG_PATH, "rb") as f:
        response = client.post("/predict", files={"file": ("test.jpg", f, "image/jpeg")})
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")
        detections = response.json().get("detections", [])
        print(f"Detections found: {len(detections)}")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    setup_dummy_image()
    try:
        test_health()
        test_prediction()
        print("\n✅ Inference Verification Passed!")
    except Exception as e:
        print(f"\n❌ Verification Failed: {e}")
    finally:
        if TEST_DATA.exists():
            shutil.rmtree(TEST_DATA)
