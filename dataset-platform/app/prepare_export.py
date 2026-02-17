"""
Prepare training-ready exports from the annotation registry.

CLI (inline args):
  python -m app.prepare_export --label-set vehicle_detection --format yolo --split 0.8 --seed 42

CLI (config file — recommended for reproducibility):
  python -m app.prepare_export --config queries/vehicle_detection_v1.yaml
"""

import json
import re
import shutil
import yaml
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from pathlib import Path
from PIL import Image

from app.config import ANNOTATIONS_DB, IMAGES_DB, EXCLUSIONS_DB, EXPORTS, STORAGE

IST = timezone(timedelta(hours=5, minutes=30))


def _next_version(export_base: Path) -> int:
    """Find the next version number for an export directory."""
    existing = [
        d.name for d in export_base.parent.iterdir()
        if d.is_dir() and d.name.startswith(export_base.name)
    ] if export_base.parent.exists() else []

    versions = []
    for name in existing:
        m = re.search(r"_v(\d+)$", name)
        if m:
            versions.append(int(m.group(1)))

    return max(versions, default=0) + 1


def _train_val_split(image_ids: list, split_ratio: float, seed: int):
    """Deterministic train/val split by image."""
    rng = np.random.RandomState(seed)
    shuffled = sorted(image_ids)  # sort first for determinism
    rng.shuffle(shuffled)
    n_train = int(len(shuffled) * split_ratio)
    return shuffled[:n_train], shuffled[n_train:]


def _get_image_dimensions(image_path: Path) -> tuple[int, int]:
    """Return (width, height) of an image using PIL."""
    with Image.open(image_path) as img:
        return img.size  # (width, height)


def _build_yolo(annotations: pd.DataFrame, images: pd.DataFrame,
                class_to_idx: dict, train_ids: list, val_ids: list,
                export_dir: Path):
    """Build YOLO format export."""
    for split_name, split_ids in [("train", train_ids), ("val", val_ids)]:
        img_dir = export_dir / "images" / split_name
        lbl_dir = export_dir / "labels" / split_name
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        split_imgs = images[images["image_id"].isin(split_ids)]

        for _, row in split_imgs.iterrows():
            image_id = row["image_id"]
            src_path = Path(row["path"])

            if not src_path.exists():
                print(f"  WARNING: image not found: {src_path}")
                continue

            # copy image
            dst_img = img_dir / f"{image_id}.jpg"
            shutil.copy2(src_path, dst_img)

            # get dimensions for normalization
            w_img, h_img = _get_image_dimensions(src_path)

            # write YOLO label file
            img_anns = annotations[annotations["image_id"] == image_id]
            lines = []
            for _, ann in img_anns.iterrows():
                cls_idx = class_to_idx[ann["label"]]
                # xyxy_abs -> cx, cy, w, h (normalized)
                x_min, y_min = ann["x_min"], ann["y_min"]
                x_max, y_max = ann["x_max"], ann["y_max"]
                cx = ((x_min + x_max) / 2) / w_img
                cy = ((y_min + y_max) / 2) / h_img
                bw = (x_max - x_min) / w_img
                bh = (y_max - y_min) / h_img
                lines.append(f"{cls_idx} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")

            with open(lbl_dir / f"{image_id}.txt", "w") as f:
                f.write("\n".join(lines))

    # dataset.yaml (YOLOv5/v8 compatible)
    class_names = {v: k for k, v in class_to_idx.items()}
    dataset_yaml = {
        "path": str(export_dir.resolve()),
        "train": "images/train",
        "val": "images/val",
        "nc": len(class_to_idx),
        "names": class_names,
    }
    with open(export_dir / "dataset.yaml", "w") as f:
        yaml.dump(dataset_yaml, f, sort_keys=False)


def _build_coco(annotations: pd.DataFrame, images: pd.DataFrame,
                class_to_idx: dict, train_ids: list, val_ids: list,
                export_dir: Path):
    """Build COCO format export."""
    categories = [{"id": idx, "name": name} for name, idx in class_to_idx.items()]

    for split_name, split_ids in [("train", train_ids), ("val", val_ids)]:
        img_dir = export_dir / "images" / split_name
        ann_dir = export_dir / "annotations"
        img_dir.mkdir(parents=True, exist_ok=True)
        ann_dir.mkdir(parents=True, exist_ok=True)

        split_imgs = images[images["image_id"].isin(split_ids)]

        coco_images = []
        coco_annotations = []
        ann_id_counter = 1

        for img_idx, (_, row) in enumerate(split_imgs.iterrows()):
            image_id = row["image_id"]
            src_path = Path(row["path"])

            if not src_path.exists():
                print(f"  WARNING: image not found: {src_path}")
                continue

            # copy image
            dst_img = img_dir / f"{image_id}.jpg"
            shutil.copy2(src_path, dst_img)

            w_img, h_img = _get_image_dimensions(src_path)

            coco_images.append({
                "id": img_idx + 1,
                "file_name": f"{image_id}.jpg",
                "width": w_img,
                "height": h_img,
            })

            # annotations for this image
            img_anns = annotations[annotations["image_id"] == image_id]
            for _, ann in img_anns.iterrows():
                x_min, y_min = ann["x_min"], ann["y_min"]
                x_max, y_max = ann["x_max"], ann["y_max"]
                w = x_max - x_min
                h = y_max - y_min
                coco_annotations.append({
                    "id": ann_id_counter,
                    "image_id": img_idx + 1,
                    "category_id": class_to_idx[ann["label"]],
                    "bbox": [x_min, y_min, w, h],
                    "area": w * h,
                    "iscrowd": 0,
                })
                ann_id_counter += 1

        coco_dict = {
            "images": coco_images,
            "annotations": coco_annotations,
            "categories": categories,
        }

        with open(ann_dir / f"instances_{split_name}.json", "w") as f:
            json.dump(coco_dict, f, indent=2)


def prepare_export(label_set: str, fmt: str = "yolo",
                   split_ratio: float = 0.8, seed: int = 42,
                   sources: list = None, exclude_labels: list = None,
                   min_annotations: int = None,
                   image_ids_file: str = None) -> Path:
    """
    Query registry and build a training-ready export.
    Returns the export directory path.
    """

    # ---- load annotations for this label_set ----
    if not ANNOTATIONS_DB.exists():
        print(f"WARNING: No annotations found at {ANNOTATIONS_DB}. Creating dummy export for testing.")
        annotations = pd.DataFrame(columns=["image_id", "label", "x_min", "y_min", "x_max", "y_max", "label_set"])
    else:
        annotations = pd.read_parquet(ANNOTATIONS_DB)
        annotations = annotations[annotations["label_set"] == label_set]

    if annotations.empty:
        print(f"WARNING: No annotations found for label_set '{label_set}'. Proceeding with empty export.")

    # ---- load images ----
    if not IMAGES_DB.exists():
        print(f"WARNING: No images registry found at {IMAGES_DB}. Proceeding with empty images df.")
        images = pd.DataFrame(columns=["image_id", "path", "source", "ingested_at"])
    else:
        images = pd.read_parquet(IMAGES_DB)

    # ---- apply exclusions ----
    if EXCLUSIONS_DB.exists():
        exclusions = pd.read_parquet(EXCLUSIONS_DB)
        if not exclusions.empty:
            excluded_ids = exclusions["image_id"].unique().tolist()
            images = images[~images["image_id"].isin(excluded_ids)]
            annotations = annotations[~annotations["image_id"].isin(excluded_ids)]
            print(f"Excluded {len(excluded_ids)} images from exclusions registry")

    # ---- apply filters ----
    if sources:
        images = images[images["source"].isin(sources)]
        annotations = annotations[annotations["image_id"].isin(images["image_id"])]
        print(f"Filtered to sources: {sources}")

    if exclude_labels:
        annotations = annotations[~annotations["label"].isin(exclude_labels)]
        print(f"Excluded labels: {exclude_labels}")

    if image_ids_file:
        ids_path = Path(image_ids_file)
        if not ids_path.is_absolute():
            ids_path = Path(STORAGE).parent.parent / ids_path
        selected_ids = [line.strip() for line in ids_path.read_text().splitlines() if line.strip()]
        images = images[images["image_id"].isin(selected_ids)]
        annotations = annotations[annotations["image_id"].isin(selected_ids)]
        print(f"Filtered to {len(selected_ids)} image IDs from {ids_path}")

    # filter to only images that have annotations
    annotated_ids = annotations["image_id"].unique().tolist()
    images = images[images["image_id"].isin(annotated_ids)]

    if min_annotations:
        ann_counts = annotations.groupby("image_id").size()
        valid_ids = ann_counts[ann_counts >= min_annotations].index.tolist()
        images = images[images["image_id"].isin(valid_ids)]
        annotations = annotations[annotations["image_id"].isin(valid_ids)]
        annotated_ids = [i for i in annotated_ids if i in valid_ids]
        print(f"Filtered to images with >= {min_annotations} annotations")

    print(f"Found {len(annotations)} annotations across {len(images)} images")

    # ---- build class mapping ----
    class_names = sorted(annotations["label"].unique())
    class_to_idx = {name: idx for idx, name in enumerate(class_names)}
    print(f"Classes: {class_to_idx}")

    # ---- auto-version export dir ----
    EXPORTS.mkdir(parents=True, exist_ok=True)
    export_base = EXPORTS / label_set
    version = _next_version(export_base)
    export_dir = EXPORTS / f"{label_set}_v{version}"
    export_dir.mkdir(parents=True, exist_ok=True)
    print(f"Export directory: {export_dir}")

    # ---- train/val split ----
    train_ids, val_ids = _train_val_split(annotated_ids, split_ratio, seed)
    print(f"Split: {len(train_ids)} train / {len(val_ids)} val")

    # ---- build format ----
    if fmt == "yolo":
        _build_yolo(annotations, images, class_to_idx, train_ids, val_ids, export_dir)
    elif fmt == "coco":
        _build_coco(annotations, images, class_to_idx, train_ids, val_ids, export_dir)
    else:
        raise ValueError(f"Unsupported format: {fmt}. Use 'yolo' or 'coco'.")

    # ---- export metadata ----
    export_info = {
        "label_set": label_set,
        "format": fmt,
        "version": version,
        "split_ratio": split_ratio,
        "seed": seed,
        "num_images": len(images),
        "num_annotations": len(annotations),
        "num_train": len(train_ids),
        "num_val": len(val_ids),
        "classes": class_names,
        "created_at": datetime.now(IST).isoformat(),
    }
    with open(export_dir / "export_info.yaml", "w") as f:
        yaml.dump(export_info, f, sort_keys=False)

    print(f"\nExport complete: {export_dir}")
    return export_dir


def _load_config(config_path: str) -> dict:
    """Load export config from a YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path) as f:
        cfg = yaml.safe_load(f)
    print(f"Loaded config: {path}")
    return cfg


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Prepare training export from annotation registry")
    parser.add_argument("--config", help="Path to YAML query config file")
    parser.add_argument("--label-set", help="Label set to export")
    parser.add_argument("--format", default="yolo", choices=["yolo", "coco"], help="Export format")
    parser.add_argument("--split", type=float, default=0.8, help="Train/val split ratio")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for split")
    args = parser.parse_args()

    if args.config:
        cfg = _load_config(args.config)
        prepare_export(
            label_set=cfg["label_set"],
            fmt=cfg.get("format", "yolo"),
            split_ratio=cfg.get("split", 0.8),
            seed=cfg.get("seed", 42),
            sources=cfg.get("sources"),
            exclude_labels=cfg.get("exclude_labels"),
            min_annotations=cfg.get("min_annotations"),
            image_ids_file=cfg.get("image_ids_file"),
        )
    else:
        if not args.label_set:
            parser.error("--label-set is required when not using --config")
        prepare_export(args.label_set, args.format, args.split, args.seed)
