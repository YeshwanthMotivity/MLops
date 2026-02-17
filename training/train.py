
import argparse
import os
from ultralytics import YOLO

MODEL_PATH = os.getenv("MODEL_PATH", "/opt/model/yolov8n.pt")

def train(data_config, epochs, imgsz):
    print(f"Loading model from: {MODEL_PATH}")
    print(f"Data Config: {data_config}")
    print(f"Epochs: {epochs}")
    print(f"Image Size: {imgsz}")

    # Initialize MLflow
    import mlflow
    import time
    
    # Set tracking URI if not set in env (default to localhost for local testing)
    if not os.environ.get("MLFLOW_TRACKING_URI"):
        mlflow.set_tracking_uri("http://localhost:5000")
        
    print(f"Tracking URI: {mlflow.get_tracking_uri()}")

    mlflow.set_experiment("yolo_training")
    
    with mlflow.start_run():
        # Log parameters
        mlflow.log_param("epochs", epochs)
        mlflow.log_param("imgsz", imgsz)
        mlflow.log_param("data_config", data_config)
        
        model = YOLO(MODEL_PATH)
        
        results = model.train(
            data=data_config,
            epochs=epochs,
            imgsz=imgsz,
            project="/opt/training/runs",
            name="train",
            exist_ok=True,
        )
        
        print("Training complete.")
        best_path = "/opt/training/runs/train/weights/best.pt"
        
        if os.path.exists(best_path):
            mlflow.log_artifact(best_path)
            print(f"Model saved to {best_path} and logged to MLflow")
        
        return best_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--imgsz", type=int, default=640)
    
    args = parser.parse_args()
    train(args.data, args.epochs, args.imgsz)

