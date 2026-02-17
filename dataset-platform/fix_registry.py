import pandas as pd
from pathlib import Path
import os

def fix_paths():
    registry_dir = Path("/opt/dataset-platform/registry/metadata")
    batches_dir = Path("/opt/dataset-platform/batches")
    storage_root = "/opt/storage/images"
    
    files_to_check = list(registry_dir.glob("*.parquet"))
    if batches_dir.exists():
        files_to_check.extend(list(batches_dir.rglob("manifest.parquet")))

    for pq in files_to_check:
        print(f"Checking {pq.name}...")
        df = pd.read_parquet(pq)
        
        if "path" in df.columns:
            def transform_path(p):
                if not isinstance(p, str):
                    return p
                
                # Replace backslashes with forward slashes
                p = p.replace('\\', '/')
                
                # If it looks like a correct container path already, keep it
                if p.startswith("/opt/storage") and "C:/" not in p:
                    return p
                
                p_obj = Path(p)
                parts = p_obj.parts
                if len(parts) >= 3:
                    # We expect .../sub1/sub2/file.ext
                    return f"{storage_root}/{parts[-3]}/{parts[-2]}/{parts[-1]}"
                
                return p # Fallback
                
                # Fallback: just filename
                return f"{storage_root}/{p_obj.name}"

            df["path"] = df["path"].apply(transform_path)
            df.to_parquet(pq, index=False)
            print(f"  Fixed paths in {pq.name}")

if __name__ == "__main__":
    fix_paths()
