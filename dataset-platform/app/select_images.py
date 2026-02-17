import pandas as pd
from app.config import IMAGES_DB, LABELS_DB, EXCLUSIONS_DB

def select_unlabeled(label_set: str, limit: int = 50):
    """
    Select images that do not yet have labels for the given label_set.
    Also skips excluded images.
    """

    # load images registry
    if not IMAGES_DB.exists():
        print("No images registry found")
        return pd.DataFrame(columns=["image_id", "path"])

    images = pd.read_parquet(IMAGES_DB)

    # remove excluded images
    if EXCLUSIONS_DB.exists():
        exclusions = pd.read_parquet(EXCLUSIONS_DB)
        excluded_ids = exclusions["image_id"].unique()
        images = images[~images["image_id"].isin(excluded_ids)]

    # remove already labeled images for this label_set
    if LABELS_DB.exists():
        labels = pd.read_parquet(LABELS_DB)

        labeled_ids = labels[
            (labels["label_set"] == label_set) &
            (labels["active"] != False)
        ]["image_id"].unique()

        images = images[~images["image_id"].isin(labeled_ids)]

    # oldest first (important for continuous ingestion)
    images = images.sort_values("ingested_at")

    return images.head(limit)[["image_id", "path"]]


if __name__ == "__main__":
    import sys
    label_set = sys.argv[1]
    result = select_unlabeled(label_set, 10)
    print(result)

