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
1.  Upload images to `incoming/`.
2.  Trigger `labeling_pipeline` DAG.
3.  **Result:** Images ingested, sent to CVAT, annotated, pulled, and **Committed to DVC**.

### B. Training Workflow (Airflow)
1.  Trigger `training_pipeline` DAG.
2.  **Result:** DVC checks out data, exports dataset, runs YOLOv8 training.
3.  **Check:** View metrics in MLflow and find `best.pt` in `model/`.

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
