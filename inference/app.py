
import os
import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
from ultralytics import YOLO

app = FastAPI(title="YOLOv8 Inference Service", version="1.0")

# Load Model
MODEL_PATH = os.getenv("MODEL_PATH", "/opt/model/best.pt")
# Fallback for local testing if volume not mounted
if not os.path.exists(MODEL_PATH) and os.path.exists("../model/yolov8n.pt"):
    MODEL_PATH = "../model/yolov8n.pt"

print(f"Loading model from: {MODEL_PATH}")
try:
    model = YOLO(MODEL_PATH)
except Exception as e:
    print(f"Error loading model: {e}")
    model = None

@app.get("/")
def health_check():
    return {"status": "healthy", "model_path": MODEL_PATH}

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    if not model:
        raise HTTPException(status_code=500, detail="Model not loaded")
    
    # Read image
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image format")

    # Run inference
    results = model(img)
    
    # Format results
    detections = []
    for r in results:
        for box in r.boxes:
            b = box.xyxy[0].tolist() # x1, y1, x2, y2
            conf = float(box.conf)
            cls = int(box.cls)
            name = model.names[cls]
            
            detections.append({
                "box": [round(x, 2) for x in b],
                "confidence": round(conf, 2),
                "class": cls,
                "name": name
            })
            
    return {"filename": file.filename, "detections": detections}
