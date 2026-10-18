import argparse
import csv
from pathlib import Path

from apps.mock_api.main import synthetic_record

parser = argparse.ArgumentParser()
parser.add_argument("--rows", type=int, choices=[10000, 100000, 300000, 1000000], default=10000)
parser.add_argument("--output", type=Path, default=Path(".local/orders.csv"))
args = parser.parse_args()
args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open("w", encoding="utf-8", newline="") as handle:
    fields = list(synthetic_record(0))
    fields.remove("deleted")
    writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for i in range(args.rows):
        writer.writerow(synthetic_record(i))
print(f"Generated {args.rows} synthetic rows at {args.output}")
