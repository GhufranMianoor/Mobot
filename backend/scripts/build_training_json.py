from __future__ import annotations

import csv
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MERGED_CSV = DATA_DIR / "training_merged_clean.csv"
OUT_JSON = DATA_DIR / "training_data.json"


def _to_int(value: str | None, default: int = 0) -> int:
    if value is None:
        return default
    value = str(value).strip()
    if not value:
        return default
    try:
        return int(float(value))
    except ValueError:
        return default


def _clamp_processor_tier(value: int) -> int:
    return max(0, min(2, value))


def _row_to_sample(row: dict) -> dict:
    return {
        "ram_gb": max(1, _to_int(row.get("ram_gb"), 4)),
        "storage_gb": max(8, _to_int(row.get("storage_gb"), 64)),
        "camera_mp": max(2, _to_int(row.get("camera_mp"), 13)),
        "battery_mah": max(1200, _to_int(row.get("battery_mah"), 4000)),
        "processor_tier": _clamp_processor_tier(_to_int(row.get("processor_tier"), 0)),
        "tier_label": max(0, min(3, _to_int(row.get("tier_label"), 0))),
    }


def build() -> None:
    if not MERGED_CSV.exists():
        raise FileNotFoundError(f"Merged dataset not found: {MERGED_CSV}")

    samples = []
    with MERGED_CSV.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            samples.append(_row_to_sample(row))

    payload = {"samples": samples}
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=True, indent=2)

    print(f"Training rows written: {len(samples)}")
    print(f"Output: {OUT_JSON}")


if __name__ == "__main__":
    build()
