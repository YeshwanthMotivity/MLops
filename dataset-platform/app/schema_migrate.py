import pandas as pd
from app.config import REGISTRY, IMAGES_DB, SOURCES_DB, LABELS_DB, ANNOTATIONS_DB, EXCLUSIONS_DB

REGISTRY.mkdir(parents=True, exist_ok=True)


def ensure_table(file_path, required_columns):
    if not file_path.exists():
        print(f"Creating: {file_path.name}")
        df = pd.DataFrame(columns=required_columns)
        df.to_parquet(file_path, index=False)
        return

    print(f"Migrating: {file_path.name}")
    df = pd.read_parquet(file_path)

    # add missing columns
    for col in required_columns:
        if col not in df.columns:
            print(f"  Adding column: {col}")
            df[col] = None

    # keep existing data but enforce column order
    df = df.reindex(columns=required_columns)

    df.to_parquet(file_path, index=False)


# ---------- images ----------
ensure_table(
    IMAGES_DB,
    ["image_id", "path", "source_id", "ingested_at"]
)

# ---------- sources ----------
ensure_table(
    SOURCES_DB,
    ["source_id", "source_type", "source_name", "license", "customer_id"]
)

# ---------- labels ----------
ensure_table(
    LABELS_DB,
    ["image_id", "label", "label_set", "annotator", "confidence", "created_at", "active"]
)

# ---------- annotations ----------
ensure_table(
    ANNOTATIONS_DB,
    [
        "annotation_id",
        "image_id",
        "label",
        "label_set",
        "source_task",
        "x_min",
        "y_min",
        "x_max",
        "y_max",
        "format",
        "created_at"
    ]
)

# ---------- exclusions ----------
ensure_table(
    EXCLUSIONS_DB,
    ["image_id", "excluded_at", "excluded_by", "reason"]
)

print("\nSchema migration complete")

