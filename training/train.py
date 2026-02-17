
import argparse
import time
import os

def train(data_config, epochs, imgsz):
    print(f"Mock Training Started...")
    print(f"Data Config: {data_config}")
    print(f"Epochs: {epochs}")
    print(f"Image Size: {imgsz}")
    
    # Simulate training time
    time.sleep(5)
    
    # Simulate output
    print("Training complete.")
    print(f"Model saved to runs/detect/train/weights/best.pt")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--imgsz", type=int, default=640)
    
    args = parser.parse_args()
    train(args.data, args.epochs, args.imgsz)
