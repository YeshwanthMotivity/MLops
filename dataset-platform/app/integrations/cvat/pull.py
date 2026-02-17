"""
COCO JSON parser for CVAT annotation exports.

Converts CVAT's COCO 1.0 export format into rows for the
annotations and labels parquet tables.
"""

import json
import zipfile
import io
from uuid import uuid4
from pathlib import PurePosixPath
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))


def extract_coco_json(zip_bytes: bytes) -> dict:
    """Unzip CVAT export, find instances_default.json, return parsed dict."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        # CVAT COCO exports put annotations in annotations/instances_default.json
        target = None
        for name in zf.namelist():
            if name.endswith("instances_default.json"):
                target = name
                break

        if target is None:
            raise FileNotFoundError(
                f"No instances_default.json in export ZIP. Contents: {zf.namelist()}"
            )

        with zf.open(target) as f:
            return json.load(f)


def coco_filename_to_image_id(file_name: str) -> str:
    """
    Extract image_id from CVAT filename.

    CVAT file_name looks like 'images/0c/c3/0cc313...857.jpg'
    (the server_files path we sent). The stem is the SHA256 hash = our image_id.
    """
    return PurePosixPath(file_name).stem


def parse_coco_annotations(coco: dict, batch_id: str, label_set: str):
    """
    Parse COCO dict into (annotation_rows, label_rows).

    annotation_rows: list of dicts for annotations.parquet
    label_rows: list of dicts for labels.parquet (deduplicated per image+label)
    """
    now = datetime.now(IST).isoformat()

    # build COCO category_id -> name mapping
    cat_map = {c["id"]: c["name"] for c in coco.get("categories", [])}

    # build COCO image_id -> file_name mapping
    img_map = {img["id"]: img["file_name"] for img in coco.get("images", [])}

    annotation_rows = []
    seen_labels = set()  # (image_id, label) for dedup
    label_rows = []

    for ann in coco.get("annotations", []):
        coco_image_id = ann["image_id"]
        file_name = img_map.get(coco_image_id)
        if file_name is None:
            continue

        image_id = coco_filename_to_image_id(file_name)
        label = cat_map.get(ann["category_id"], "unknown")

        # COCO bbox: [x, y, w, h] (absolute pixels, top-left origin)
        x, y, w, h = ann["bbox"]
        x_min = x
        y_min = y
        x_max = x + w
        y_max = y + h

        annotation_rows.append({
            "annotation_id": str(uuid4()),
            "image_id": image_id,
            "label": label,
            "label_set": label_set,
            "source_task": batch_id,
            "x_min": x_min,
            "y_min": y_min,
            "x_max": x_max,
            "y_max": y_max,
            "format": "xyxy_abs",
            "created_at": now,
        })

        # deduplicate image-level labels within this batch
        key = (image_id, label)
        if key not in seen_labels:
            seen_labels.add(key)
            label_rows.append({
                "image_id": image_id,
                "label": label,
                "label_set": label_set,
                "annotator": "cvat",
                "confidence": None,
                "created_at": now,
                "active": True,
            })

    return annotation_rows, label_rows
