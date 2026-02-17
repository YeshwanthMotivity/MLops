import pandas as pd
from pathlib import Path, PurePosixPath
from app.config import BATCHES, STORAGE, CVAT_IMAGE_ROOT


def get_cvat_image_paths(batch_id: str):
    """
    Map local storage paths to CVAT server_files paths.
    server_files expects paths relative to CVAT's share dir (/home/django/share/).
    CVAT_IMAGE_ROOT should be 'images' (the mount subfolder inside share).
    """
    manifest_path = BATCHES / batch_id / "manifest.parquet"

    if not manifest_path.exists():
        raise FileNotFoundError(f"Batch not found: {batch_id}")

    manifest = pd.read_parquet(manifest_path)

    return [
        PurePosixPath(CVAT_IMAGE_ROOT, Path(p).relative_to(STORAGE).as_posix()).as_posix()
        for p in manifest["path"]
    ]
