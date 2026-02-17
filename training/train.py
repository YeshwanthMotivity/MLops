
import argparse
import time
import os

def train(data_config, epochs, imgsz):
    print(f"Mock Training Started...")
    print(f"Data Config: {data_config}")
    print(f"Epochs: {epochs}")
    print(f"Image Size: {imgsz}")

    # Initialize MLflow
    import mlflow
    
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
        
        # Simulate training time
        time.sleep(2)
        
        # Log metrics
        for epoch in range(epochs):
            loss = 1.0 / (epoch + 1)
            accuracy = 0.5 + (epoch * 0.1)
            mlflow.log_metric("loss", loss, step=epoch)
            mlflow.log_metric("accuracy", accuracy, step=epoch)
            print(f"Epoch {epoch+1}/{epochs}: loss={loss:.4f}, accuracy={accuracy:.4f}")
            time.sleep(0.5)
            
        print("Training complete.")
        
        # Log simulated model artifact
        os.makedirs("runs/detect/train/weights", exist_ok=True)
        with open("runs/detect/train/weights/best.pt", "w") as f:
            f.write("dummy model content")
            
        mlflow.log_artifact("runs/detect/train/weights/best.pt")
        print(f"Model saved to runs/detect/train/weights/best.pt and logged to MLflow")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--imgsz", type=int, default=640)
    
    args = parser.parse_args()
    train(args.data, args.epochs, args.imgsz)
