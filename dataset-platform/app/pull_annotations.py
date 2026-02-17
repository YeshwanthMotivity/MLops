"""
Pull annotations from CVAT and store in the parquet registry.

CLI:  python -m app.pull_annotations --batch-id batch_20260214_120200 [--task-id 6]

By default, only pulls when all CVAT jobs are completed/accepted.
Use --force to pull partial (in-progress) annotations.
Re-running replaces previous annotations for the same batch.
"""

import yaml
import pandas as pd
from app.config import BATCHES, ANNOTATIONS_DB, LABELS_DB
from app.integrations.cvat.client import CvatClient
from app.integrations.cvat.pull import extract_coco_json, parse_coco_annotations


def pull_annotations(batch_id: str, task_id: int = None, force: bool = False) -> int:
    """
    Pull annotations from CVAT for a batch and write to parquet.
    Returns count of annotations written (0 if no annotations found).

    - Checks job completion status before pulling (skip with force=True)
    - Re-pulling replaces old annotations for the same batch (safe to re-run)
    """

    # ---- read batch info ----
    info_path = BATCHES / batch_id / "info.yaml"
    if not info_path.exists():
        raise FileNotFoundError(f"Batch not found: {batch_id}")

    with open(info_path) as f:
        info = yaml.safe_load(f)

    label_set = info["label_set"]

    # resolve task_id: CLI flag > info.yaml
    if task_id is None:
        task_id = info.get("cvat_task_id")
    if task_id is None:
        raise ValueError(
            f"No cvat_task_id in {info_path}. "
            f"Use --task-id flag or re-run create_task to save it."
        )

    # ---- connect to CVAT ----
    client = CvatClient()

    # ---- check job completion ----
    if not force:
        jobs = client.get_task_jobs(task_id)
        total = len(jobs)
        done = sum(1 for j in jobs if j.get("state") == "completed")

        if total == 0:
            print(f"WARNING: task {task_id} has no jobs")
        elif done < total:
            print(f"Task {task_id}: {done}/{total} jobs completed (by state).")
            print(f"Use --force to pull incomplete annotations.")
            return 0

        print(f"Task {task_id}: {done}/{total} jobs completed")

    # ---- export from CVAT ----
    print(f"Pulling annotations for {batch_id} (task_id={task_id})...")
    rq_id = client.export_annotations(task_id)
    zip_bytes = client.download_export(rq_id)

    # ---- parse COCO JSON ----
    coco = extract_coco_json(zip_bytes)
    annotation_rows, label_rows = parse_coco_annotations(coco, batch_id, label_set)

    if not annotation_rows:
        print(f"WARNING: No annotations found in CVAT export for {batch_id}")
        return 0

    # ---- write annotations.parquet (replace strategy for this batch) ----
    new_annotations = pd.DataFrame(annotation_rows)

    if ANNOTATIONS_DB.exists():
        existing = pd.read_parquet(ANNOTATIONS_DB)
        # remove old annotations for this batch, then append fresh ones
        other_batches = existing[existing["source_task"] != batch_id]
        old_count = len(existing) - len(other_batches)
        if old_count > 0:
            print(f"Replacing {old_count} old annotations for {batch_id}")
        combined = pd.concat([other_batches, new_annotations], ignore_index=True)
    else:
        combined = new_annotations

    combined.to_parquet(ANNOTATIONS_DB, index=False)
    print(f"Wrote {len(annotation_rows)} annotations to {ANNOTATIONS_DB.name}")

    # ---- write labels.parquet (replace + dedup) ----
    new_labels = pd.DataFrame(label_rows)

    if LABELS_DB.exists():
        existing_labels = pd.read_parquet(LABELS_DB)
        # remove old labels from this batch's annotator+label_set combo
        # then dedup new labels against remaining
        other_labels = existing_labels[
            ~((existing_labels["label_set"] == label_set) &
              (existing_labels["annotator"] == "cvat") &
              (existing_labels["image_id"].isin(new_labels["image_id"])))
        ]
        combined_labels = pd.concat([other_labels, new_labels], ignore_index=True)
    else:
        combined_labels = new_labels

    combined_labels.to_parquet(LABELS_DB, index=False)
    print(f"Wrote {len(new_labels)} labels to {LABELS_DB.name}")

    return len(annotation_rows)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pull annotations from CVAT for a batch")
    parser.add_argument("--batch-id", required=True, help="Batch ID from batches/")
    parser.add_argument("--task-id", type=int, default=None, help="CVAT task ID (overrides info.yaml)")
    parser.add_argument("--force", action="store_true", help="Pull even if jobs are not completed")
    args = parser.parse_args()

    count = pull_annotations(args.batch_id, args.task_id, args.force)
    print(f"\nDone. {count} annotations pulled.")
