import hashlib
import shutil
import argparse
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

from app.config import STORAGE, REGISTRY, INCOMING, IMAGES_DB


# ---------------- Helpers ----------------
def sha256(file_path: Path) -> str:
    """Compute deterministic image id"""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def ingest(source_id: str) -> int:
    """Ingest images from incoming directory into dataset registry.

    Returns the number of newly ingested images.
    """
    # Ensure dirs
    STORAGE.mkdir(parents=True, exist_ok=True)
    REGISTRY.mkdir(parents=True, exist_ok=True)
    INCOMING.mkdir(parents=True, exist_ok=True)

    # Load existing registry
    if IMAGES_DB.exists():
        df_existing = pd.read_parquet(IMAGES_DB)
    else:
        df_existing = pd.DataFrame(
            columns=["image_id", "path", "source_id", "ingested_at"]
        )

    existing_ids = set(df_existing["image_id"].tolist())

    # Ingest
    new_rows = []

    for img in INCOMING.iterdir():

        # Skip folders and Windows metadata
        if not img.is_file() or "Zone.Identifier" in img.name:
            continue

        image_id = sha256(img)

        # Skip duplicates
        if image_id in existing_ids:
            print(f"SKIPPED (already registered): {img.name}")
            img.unlink()  # remove from incoming
            continue

        ext = img.suffix.lower()

        # hashed folder layout
        sub1 = image_id[:2]
        sub2 = image_id[2:4]

        dest_dir = STORAGE / sub1 / sub2
        dest_dir.mkdir(parents=True, exist_ok=True)

        dest_path = dest_dir / f"{image_id}{ext}"

        # move file into canonical storage
        shutil.move(img, dest_path)
        print(f"INGESTED: {img.name}")

        new_rows.append({
            "image_id": image_id,
            "path": str(dest_path),
            "source_id": source_id,
            "ingested_at": datetime.now(timezone.utc).isoformat()
        })

    # Update registry
    if new_rows:
        df_new = pd.DataFrame(new_rows)
        df_final = pd.concat([df_existing, df_new], ignore_index=True)
        df_final.to_parquet(IMAGES_DB, index=False)
        print(f"{len(new_rows)} new images registered.")
    else:
        print("No new images found.")

    return len(new_rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest images into dataset registry")
    parser.add_argument("--source-id", required=True, help="Source UUID from sources.parquet")
    args = parser.parse_args()
    ingest(args.source_id)
