
import argparse
import os
import shutil
from pathlib import Path
from ultralytics import YOLO
import mlflow

# Default paths
MODEL_PATH = os.getenv("MODEL_PATH", "/opt/mlops/model/yolov8n.pt")
RUNS_DIR = Path("/opt/mlops/training/runs")

def train(data_config, epochs, imgsz, batch_size, register_name=None):
    print(f"🚀 Starting Training...")
    print(f"   Model: {MODEL_PATH}")
    print(f"   Data: {data_config}")
    print(f"   Epochs: {epochs}")
    print(f"   ImgSz: {imgsz}")

    # 1. Setup MLflow
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("YOLOv8_Training")
    
    print(f"   MLflow Tracking URI: {tracking_uri}")

    # 2. Load Model
    # Ensure model file exists, or let YOLO download it
    if not os.path.exists(MODEL_PATH):
        print(f"⚠️ Model not found at {MODEL_PATH}, YOLO will attempt download.")
    
    model = YOLO(MODEL_PATH)

    # 3. Train with MLflow Context
    with mlflow.start_run() as run:
        # Log Hyperparameters
        mlflow.log_params({
            "epochs": epochs,
            "imgsz": imgsz,
            "batch_size": batch_size,
            "model_path": MODEL_PATH,
            "data_config": data_config
        })

        # Run Training
        # project=RUNS_DIR ensures results go to /opt/training/runs/train (or train2, train3...)
        results = model.train(
            data=data_config,
            epochs=epochs,
            imgsz=imgsz,
            batch=batch_size,
            project=str(RUNS_DIR),
            name="train",
            exist_ok=True, # Overwrite 'train' folder to save space in POC
        )

        # 4. Log Metrics
        # access results.box.map50, results.box.map, etc.
        metrics = {
            "map50": results.box.map50,
            "map50-95": results.box.map,
            "precision": results.box.mp,
            "recall": results.box.mr
        }
        mlflow.log_metrics(metrics)
        print(f"✅ Training Complete. Metrics: {metrics}")

        # 5. Log Artifacts
        # The best model is typically at runs/train/weights/best.pt
        best_weight_path = RUNS_DIR / "train" / "weights" / "best.pt"
        
        if best_weight_path.exists():
            print(f"   Logging artifact: {best_weight_path}")
            mlflow.log_artifact(str(best_weight_path), artifact_path="weights")
            
            # Also log the confusion matrix if it exists
            confusion_matrix = RUNS_DIR / "train" / "confusion_matrix.png"
            if confusion_matrix.exists():
                mlflow.log_artifact(str(confusion_matrix))

            # 6. Output Run ID for Airflow
            print(f"MLFLOW_RUN_ID: {run.info.run_id}")
            return run.info.run_id
        else:
            print("❌ Error: Could not find best.pt to log.")
            exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True, help="Path to dataset.yaml")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--register-name", type=str, default=None, help="Model name for MLflow Registry")
    
    args = parser.parse_args()
    
    # Ensure runs dir exists
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        train(args.data, args.epochs, args.imgsz, args.batch, args.register_name)
    except Exception as e:
        print(f"❌ Training Failed: {e}")
        exit(1)
