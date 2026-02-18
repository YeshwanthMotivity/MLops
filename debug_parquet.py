
import pandas as pd
import os

parquet_path = r"c:/Yash/mlops 1/mlops/dataset-platform/registry/metadata/images.parquet"
if os.path.exists(parquet_path):
    df = pd.read_parquet(parquet_path)
    print(df.head())
    print("-" * 20)
    print(df["path"].iloc[0] if not df.empty else "No data")
else:
    print(f"File not found: {parquet_path}")
