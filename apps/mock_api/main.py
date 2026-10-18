from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, HTTPException, Query

app = FastAPI(title="CDIP synthetic source (not a marketplace API)")


def synthetic_record(index: int) -> dict:
    return {
        "id": str(index),
        "shop_id": f"shop-{index % 3}",
        "updated_at": (datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=index)).isoformat(),
        "gross_amount": f"{100 + index % 100}.25",
        "currency": "VND",
        "status": "cancelled" if index % 17 == 0 else "completed",
        "deleted": False,
    }


@app.get("/health")
def health():
    return {"status": "ok", "synthetic": True}


@app.get("/orders")
def orders(
    cursor: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=5000),
    updated_since: datetime | None = None,
    count: int = Query(10000, ge=1, le=1000000),
):
    first = 0
    if updated_since:
        if updated_since.tzinfo is None:
            raise HTTPException(422, "Timezone required")
        first = max(0, int((updated_since - datetime(2026, 1, 1, tzinfo=UTC)).total_seconds()))
    start = max(cursor, first)
    end = min(start + limit, count)
    return {
        "items": [synthetic_record(i) for i in range(start, end)],
        "next_cursor": str(end) if end < count else None,
    }
