"""Create synthetic sources through the authenticated API; idempotent by name."""

import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()
base = os.environ.get("CDIP_API_URL", "http://localhost:8000")
with httpx.Client(
    base_url=base, headers={"Authorization": "Bearer " + os.environ["CDIP_ADMIN_TOKEN"]}, timeout=30
) as client:
    client.get("/api/v1/health").raise_for_status()
    existing_response = client.get("/api/v1/sources", params={"limit": 200})
    existing_response.raise_for_status()
    existing = {row["name"]: row["id"] for row in existing_response.json()["items"]}
    for name in ("mock-source.json", "csv-source.json"):
        body = json.loads((Path("configs") / name).read_text())
        if body["name"] not in existing:
            response = client.post("/api/v1/sources", json=body)
            response.raise_for_status()
            source_id = response.json()["id"]
        else:
            source_id = existing[body["name"]]
        response = client.post(f"/api/v1/sources/{source_id}/sync")
        response.raise_for_status()
        print(json.dumps({"source": body["name"], **response.json()}))
