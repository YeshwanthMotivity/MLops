import pandas as pd
import yaml
from datetime import datetime, timezone, timedelta
from app.select_images import select_unlabeled
from app.config import BATCHES

IST = timezone(timedelta(hours=5, minutes=30))

def create_batch(label_set, limit=10):
    # select images for labeling
    selected = select_unlabeled(label_set, limit)

    if selected.empty:
        print("No images available for labeling")
        return None

    # create batch id (IST timestamp)
    now = datetime.now(IST)
    batch_id = f"batch_{now.strftime('%Y%m%d_%H%M%S')}"
    batch_dir = BATCHES / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)

    # create CVAT-friendly filenames
    manifest = selected.copy()
    manifest["cvat_name"] = [f"{i:06}.jpg" for i in range(len(manifest))]

    # save manifest (dataset snapshot)
    manifest.to_parquet(batch_dir / "manifest.parquet", index=False)

    # file list for CVAT (shared storage paths)
    with open(batch_dir / "filelist.txt", "w") as f:
        for p in manifest["path"]:
            f.write(f"{p}\n")

    # batch metadata
    info = {
        "batch_id": batch_id,
        "label_set": label_set,
        "created_at": now.isoformat(),
        "num_images": len(manifest),
    }

    with open(batch_dir / "info.yaml", "w") as f:
        yaml.dump(info, f)

    print(f"Batch created: {batch_id} ({len(manifest)} images)")
    return batch_id


if __name__ == "__main__":
    import sys
    create_batch(sys.argv[1], 10)

