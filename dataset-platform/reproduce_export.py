
import pandas as pd
import shutil
from pathlib import Path
from app.prepare_export import _build_yolo, _build_coco

# Mock config
ROOT = Path("mock_root")
STORAGE = ROOT / "storage"
INCOMING = ROOT / "incoming"
EXPORTS = ROOT / "exports"

# Create mock environment
if ROOT.exists():
    shutil.rmtree(ROOT)
STORAGE.mkdir(parents=True)
INCOMING.mkdir(parents=True)
EXPORTS.mkdir(parents=True)

# Create a dummy image in STORAGE (sharded)
image_id = "0cc313885c938470904ae457982ac31a3f9757c431d3884dbf1dbca8a10dc857"
shard_1 = image_id[:2]
shard_2 = image_id[2:4]
img_path = STORAGE / shard_1 / shard_2 / f"{image_id}.jpg"
img_path.parent.mkdir(parents=True, exist_ok=True)
with open(img_path, "wb") as f:
    f.write(b"fake image content")

# Create a dummy image in INCOMING
image_id_incoming = "incoming_test_image"
incoming_path = INCOMING / f"{image_id_incoming}.jpg"
with open(incoming_path, "wb") as f:
    f.write(b"fake incoming image content")

# Mock DataFrames
# 1. Image in STORAGE but path in DB is wrong
# 2. Image in INCOMING but path in DB is wrong
images = pd.DataFrame([
    {
        "image_id": image_id,
        "path": "/wrong/path/to/storage/" + image_id + ".jpg"
    },
    {
        "image_id": image_id_incoming,
        "path": "/wrong/path/to/incoming/" + image_id_incoming + ".jpg"
    }
])

annotations = pd.DataFrame([
    {
        "image_id": image_id,
        "label": "car",
        "x_min": 10, "y_min": 10, "x_max": 100, "y_max": 100
    },
    {
        "image_id": image_id_incoming,
        "label": "car",
        "x_min": 20, "y_min": 20, "x_max": 200, "y_max": 200
    }
])

class_to_idx = {"car": 0}
train_ids = [image_id, image_id_incoming]
val_ids = []

# Update config in prepare_export (monkeypatching for test)
import app.prepare_export as pe
pe.STORAGE = STORAGE
pe.INCOMING = INCOMING

# Run _build_yolo
print("Testing _build_yolo...")
try:
    _build_yolo(annotations, images, class_to_idx, train_ids, val_ids, EXPORTS)
    print(" _build_yolo executed.")
    
    # Verify files exist in export
    exported_img_1 = EXPORTS / "images" / "train" / f"{image_id}.jpg"
    exported_img_2 = EXPORTS / "images" / "train" / f"{image_id_incoming}.jpg"
    
    if exported_img_1.exists():
        print(f"PASS: Found exported image from STORAGE: {exported_img_1}")
    else:
        print(f"FAIL: Missing exported image from STORAGE: {exported_img_1}")
        
    if exported_img_2.exists():
        print(f"PASS: Found exported image from INCOMING: {exported_img_2}")
    else:
        print(f"FAIL: Missing exported image from INCOMING: {exported_img_2}")

except Exception as e:
    print(f"FAIL: _build_yolo crashed: {e}")

# Cleanup
# shutil.rmtree(ROOT)
