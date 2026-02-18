import pandas as pd
from pathlib import Path
from app.config import IMAGES_DB, EXCLUSIONS_DB

def clear_backlog():
    # Define the cutoff (ignore everything before today)
    cutoff = "2026-02-18T00:00:00"

    print(f"Reading images from {IMAGES_DB}...")
    images = pd.read_parquet(IMAGES_DB)
    
    # Filter for images ingested before today
    to_exclude = images[images["ingested_at"] < cutoff]
    
    if to_exclude.empty:
        print("No older images found to exclude.")
        return

    print(f"Found {len(to_exclude)} older images to exclude.")

    # Update exclusions
    if EXCLUSIONS_DB.exists():
        exclusions = pd.read_parquet(EXCLUSIONS_DB)
        df_final = pd.concat([exclusions, to_exclude[["image_id"]]], ignore_index=True).drop_duplicates()
    else:
        df_final = to_exclude[["image_id"]]

    # Ensure parent dir exists
    EXCLUSIONS_DB.parent.mkdir(parents=True, exist_ok=True)
    
    df_final.to_parquet(EXCLUSIONS_DB, index=False)
    print(f"SUCCESS: Excluded {len(to_exclude)} older images from labeling queue.")

if __name__ == "__main__":
    clear_backlog()
