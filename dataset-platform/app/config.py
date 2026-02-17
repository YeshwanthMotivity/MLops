from pathlib import Path
import os
from dotenv import load_dotenv

# Load .env file if present (local dev), ignored in production
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ---------------- Data Root ----------------
# Local dev:  defaults to dataset-platform/ (project root)
# Airflow:    set DATASET_PLATFORM_ROOT=/opt/dataset-platform
# Training:   set DATASET_PLATFORM_ROOT=/datasets
_default_root = Path(__file__).resolve().parent.parent
ROOT = Path(os.getenv("DATASET_PLATFORM_ROOT", str(_default_root)))

# ---------------- Data Paths ----------------
STORAGE = Path(os.getenv("STORAGE_ROOT", str(ROOT.parent / "storage" / "images")))
REGISTRY = ROOT / "registry" / "metadata"

IMAGES_DB = REGISTRY / "images.parquet"
LABELS_DB = REGISTRY / "labels.parquet"
ANNOTATIONS_DB = REGISTRY / "annotations.parquet"
SOURCES_DB = REGISTRY / "sources.parquet"
EXCLUSIONS_DB = REGISTRY / "exclusions.parquet"

INCOMING = ROOT / "incoming"
BATCHES = ROOT / "batches"
EXPORTS = ROOT / "exports"
QUERIES = ROOT / "queries"


# ---------------- MLflow ----------------
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")

# ---------------- CVAT ----------------
CVAT_URL = os.getenv("CVAT_URL")
CVAT_USERNAME = os.getenv("CVAT_USERNAME")
CVAT_PASSWORD = os.getenv("CVAT_PASSWORD")
# relative to CVAT's share dir (/home/django/share/)
CVAT_IMAGE_ROOT = os.getenv("CVAT_IMAGE_ROOT", "images")

