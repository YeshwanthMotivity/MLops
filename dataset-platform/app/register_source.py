import pandas as pd
import argparse
from uuid import uuid4

from app.config import SOURCES_DB

parser = argparse.ArgumentParser()
parser.add_argument("--type", required=True)
parser.add_argument("--name", required=True)
parser.add_argument("--license", required=True)
parser.add_argument("--customer-id", default=None)
args = parser.parse_args()

if SOURCES_DB.exists():
    df=pd.read_parquet(SOURCES_DB)
else:
    df=pd.DataFrame(columns=["source_id","source_type","source_name","license","customer_id"])

source_id=str(uuid4())

row=dict(
    source_id=source_id,
    source_type=args.type,
    source_name=args.name,
    license=args.license,
    customer_id=args.customer_id
)

df=pd.concat([df,pd.DataFrame([row])],ignore_index=True)
df.to_parquet(SOURCES_DB,index=False)

print("Registered source_id:",source_id)

