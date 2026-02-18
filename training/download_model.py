import os
from ultralytics import YOLO

def download_model():
    print("Downloading YOLOv8n model...")
    # Save to /opt/mlops/training so it persists via volume mount
    model_path = "/opt/mlops/training/yolov8n.pt"
    if os.path.exists(model_path):
         print(f"Model already exists at {model_path}")
         return
         
    model = YOLO(model_path) # This will download to the path
    print(f"Model downloaded successfully to {model_path}")

if __name__ == "__main__":
    download_model()
