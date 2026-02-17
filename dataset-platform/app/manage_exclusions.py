"""
Manage image exclusions in the registry.

CLI:
  python -m app.manage_exclusions add --image-ids abc123 def456 --reason "blurry images"
  python -m app.manage_exclusions remove --image-ids abc123
  python -m app.manage_exclusions list
"""

import pandas as pd
from datetime import datetime, timezone, timedelta
from app.config import EXCLUSIONS_DB, IMAGES_DB

IST = timezone(timedelta(hours=5, minutes=30))


def _load_exclusions() -> pd.DataFrame:
    if EXCLUSIONS_DB.exists():
        return pd.read_parquet(EXCLUSIONS_DB)
    return pd.DataFrame(columns=["image_id", "reason", "excluded_at"])


def _save_exclusions(df: pd.DataFrame):
    EXCLUSIONS_DB.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(EXCLUSIONS_DB, index=False)


def add_exclusions(image_ids: list[str], reason: str = "manual"):
    """Add images to the exclusion list."""
    excl = _load_exclusions()

    # validate image IDs exist
    if IMAGES_DB.exists():
        images = pd.read_parquet(IMAGES_DB)
        valid_ids = set(images["image_id"].tolist())
        invalid = [i for i in image_ids if i not in valid_ids]
        if invalid:
            print(f"WARNING: image IDs not found in registry: {invalid}")
            image_ids = [i for i in image_ids if i in valid_ids]

    already_excluded = set(excl["image_id"].tolist())
    new_ids = [i for i in image_ids if i not in already_excluded]
    skipped = [i for i in image_ids if i in already_excluded]

    if skipped:
        print(f"Already excluded (skipped): {len(skipped)}")

    if not new_ids:
        print("No new exclusions to add.")
        return

    now = datetime.now(IST).isoformat()
    new_rows = pd.DataFrame([
        {"image_id": iid, "reason": reason, "excluded_at": now}
        for iid in new_ids
    ])

    excl = pd.concat([excl, new_rows], ignore_index=True)
    _save_exclusions(excl)
    print(f"Excluded {len(new_ids)} images. Total exclusions: {len(excl)}")


def remove_exclusions(image_ids: list[str]):
    """Remove images from the exclusion list."""
    excl = _load_exclusions()
    if excl.empty:
        print("No exclusions to remove.")
        return

    before = len(excl)
    excl = excl[~excl["image_id"].isin(image_ids)]
    _save_exclusions(excl)
    removed = before - len(excl)
    print(f"Removed {removed} exclusions. Total exclusions: {len(excl)}")


def list_exclusions():
    """List all excluded images."""
    excl = _load_exclusions()
    if excl.empty:
        print("No exclusions.")
        return

    print(f"Total exclusions: {len(excl)}\n")
    for _, row in excl.iterrows():
        print(f"  {row['image_id'][:12]}...  reason={row['reason']}  at={row['excluded_at']}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manage image exclusions")
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add", help="Exclude images")
    add_p.add_argument("--image-ids", nargs="+", required=True, help="Image IDs to exclude")
    add_p.add_argument("--reason", default="manual", help="Reason for exclusion")

    rm_p = sub.add_parser("remove", help="Remove exclusions")
    rm_p.add_argument("--image-ids", nargs="+", required=True, help="Image IDs to un-exclude")

    sub.add_parser("list", help="List all exclusions")

    args = parser.parse_args()

    if args.command == "add":
        add_exclusions(args.image_ids, args.reason)
    elif args.command == "remove":
        remove_exclusions(args.image_ids)
    elif args.command == "list":
        list_exclusions()
