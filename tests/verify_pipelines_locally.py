
import sys
import os
import subprocess
from pathlib import Path
import time

# Setup Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "dataset-platform"))
sys.path.append(str(PROJECT_ROOT))

# Import App Logic
try:
    from app.ingest import ingest
except ImportError as e:
    print(f"Error importing app logic: {e}")
    sys.exit(1)

def run_cmd(cmd, description):
    print(f"Running: {description}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Failed: {result.stderr}")
        return False
    print("✅ Success")
    return True

def verify_labeling_automation():
    print("\nXXX 1. VERIFYING LABELING AUTOMATION (Ingest -> DVC Commit) XXX")
    
    # 1. Create dummy data
    incoming = PROJECT_ROOT / "dataset-platform" / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    
    dummy_file = incoming / "test_verification.jpg"
    with open(dummy_file, "w") as f:
        f.write(f"verification_data_{time.time()}")
    print(f"Created dummy file: {dummy_file}")
    
    # 2. Run Ingest
    print("Running Application Ingest Logic...")
    try:
        count = ingest("manual_verification")
        print(f"Ingested {count} files.")
    except Exception as e:
        print(f"❌ Ingest crashed: {e}")
        return

    # 3. Run Pipeline Commands (Simulating BashOperator)
    # Note: adjusting paths since we are running from 'tests/' or root, but commands assume specific CWD
    
    # dvc add storage
    cmd_dvc = f"cd {PROJECT_ROOT} && dvc add storage && dvc push"
    if not run_cmd(cmd_dvc, "DVC Add & Push"): return
    
    # git commit
    # Windows requires double quotes for commit messages
    cmd_git = f"cd {PROJECT_ROOT} && git add storage.dvc && git commit -m \"Auto-commit: Local Verification Test\""
    if not run_cmd(cmd_git, "Git Commit"): return
    
    print("✅ Labeling Automation Verified.")

def verify_training_automation():
    print("\nXXX 2. VERIFYING TRAINING AUTOMATION (DVC Checkout) XXX")
    
    # Simulate the checkout task
    cmd_checkout = f"cd {PROJECT_ROOT} && dvc checkout"
    if not run_cmd(cmd_checkout, "DVC Checkout"): return
    
    print("✅ Training Automation Verified.")

if __name__ == "__main__":
    verify_labeling_automation()
    verify_training_automation()
