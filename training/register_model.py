
import argparse
import os
import mlflow

def register_model(run_id, model_name):
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(tracking_uri)
    
    model_uri = f"runs:/{run_id}/weights/best.pt"
    print(f"🚀 Registering model '{model_name}' from run '{run_id}'...")
    print(f"   MLflow Tracking URI: {tracking_uri}")
    print(f"   Model URI: {model_uri}")
    
    if not run_id or run_id.lower() == "none" or len(run_id) < 10:
        print(f"❌ Error: Invalid Run ID received: '{run_id}'")
        exit(1)

    try:
        from mlflow.tracking import MlflowClient
        client = MlflowClient()
        run = client.get_run(run_id)
        print(f"✅ Found run: {run.info.run_id} ({run.info.lifecycle_stage})")
        
        # Use MlflowClient directly to avoid version mismatch
        # (mlflow.register_model in client v3.x calls endpoints not on server v2.x)
        try:
            client.create_registered_model(model_name)
            print(f"✅ Created new registered model: {model_name}")
        except Exception:
            print(f"ℹ️  Registered model '{model_name}' already exists, adding new version...")
        
        result = client.create_model_version(
            name=model_name,
            source=model_uri,
            run_id=run_id,
        )
        print(f"✅ Model registered successfully: {result.name} version {result.version}")
    except Exception as e:
        print(f"❌ Failed to register model: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", type=str, required=True, help="MLflow Run ID")
    parser.add_argument("--model-name", type=str, required=True, help="Name for the registered model")
    
    args = parser.parse_args()
    run_id = args.run_id.strip() if args.run_id else ""
    register_model(run_id, args.model_name.strip())
