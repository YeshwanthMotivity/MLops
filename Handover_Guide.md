# MLOps Platform Handover Guide

## 🎯 Executive Summary
The MLOps platform is now **Feature Complete** according to the PPT requirements. It provides an end-to-end automated workflow for managing datasets, training YOLOv8 models, and serving predictions.

**Key Capabilities:**
*   **Data Management:** SHA256 deduplication, DVC versioning, and Metadata Registry.
*   **Automation:** Airflow DAGs for Labeling (CVAT) and Training integration.
*   **Model Training:** Real YOLOv8 training logic with MLflow tracking.
*   **Inference:** FastAPI service for real-time predictions.
*   **Security:** Fernet Key verified.

---

## 🚀 Quick Start
### 1. Start the Stack
```powershell
docker compose up -d --build
```
*Note: First run may take 5-10 mins to build Airflow & Inference images.*

### 2. Access Interfaces
*   **Airflow:** [http://localhost:8081](http://localhost:8081) (admin/admin)
*   **MLflow:** [http://localhost:5000](http://localhost:5000)
*   **Inference API:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 Verification Workflows

### A. Labeling Workflow (Airflow)
**Goal:** Automate data ingestion, annotation (CVAT), and versioning.

**Typical Inputs (JSON Configuration):**
```json
{
  "source_id": "manual_upload",   // Source of images
  "batch_size": 10,               // Number of images to label
  "cvat_project": "MyProject",    // Project name in CVAT
  "labels": ["car", "truck"]      // Labels to use
}
```

**Steps to Test:**
1.  Place images in `mlops/dataset-platform/incoming/`.
2.  Go to Airflow UI -> `labeling_pipeline` -> **Trigger DAG w/ Config**.
3.  Paste the JSON above (optional, defaults exist).
4.  **Verify:**
    *   **CVAT:** New task appears at [localhost:8080](http://localhost:8080).
    *   **Storage:** Annotations saved to `storage/images`.
    *   **Git/DVC:** New commit created with message "Auto-commit...".

### B. Training Workflow (Airflow)
**Goal:** Train YOLOv8 model on versioned data.

**Typical Inputs (JSON Configuration):**
```json
{
  "version": "HEAD",              // Git version tag/branch (optional)
  "epochs": 10,                   // Training epochs
  "model_name": "YOLOv8_Demo",    // Name for MLflow registry
  "split": 0.8                    // Train/Val split ratio
}
```

**Steps to Test:**
1.  Go to Airflow UI -> `training_pipeline` -> **Trigger DAG w/ Config**.
2.  **Verify:**
    *   **Airflow:** Wait for `train_model` task to complete (~5-10 mins).
    *   **MLflow:** Check [localhost:5000](http://localhost:5000) for loss curves.
    *   **Artifacts:** Model saved to `mlops/model/best.pt`.


### C. Inference Workflow (API)
Send an image to the running service:
```powershell
curl -X POST "http://localhost:8000/predict" -F "file=@test.jpg"
```
Or use the Swagger UI at `/docs`.

---

## 📂 Project Structure (Final)
```
mlops/
├── dags/                  # Auto-Labeling & Training Pipelines
├── dataset-platform/      # Core Data Logic (Ingest, Registry)
├── training/              # YOLOv8 Training Script
├── inference/             # FastAPI Inference Service (NEW)
├── storage/               # DVC Data Store
├── model/                 # Shared Model Volume
└── docker-compose.yaml    # Infrastructure Definition
```

## 🛡️ Maintenance
*   **Security:** `AIRFLOW__CORE__FERNET_KEY` is set in `.env`. Rotate periodically.
*   **Dependencies:** `requirements.txt` contains core packages. Update as needed.
*   **Logs:** Check `docker compose logs -f` for debugging.
