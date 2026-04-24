from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PRIMARY_CSV = DATA_DIR / "training_mobile_specs.csv"
EXTERNAL_CSV = DATA_DIR / "amazon_market_dataset.csv"
OUT_CSV = DATA_DIR / "training_merged_clean.csv"


def _as_int(value: str | None, default: int = 0) -> int:
    if not value:
        return default
    m = re.search(r"\d+", value)
    if not m:
        return default
    return int(m.group(0))


def _price_from_text(value: str | None) -> int:
    if not value:
        return 0
    cleaned = value.replace(",", "")
    m = re.search(r"(\d{4,8})", cleaned)
    if not m:
        return 0
    return int(m.group(1))


def _tier_label(price: int) -> int:
    if price < 30000:
        return 0
    if price <= 70000:
        return 1
    if price <= 150000:
        return 2
    return 3


def _looks_like_phone(title: str) -> bool:
    t = title.lower()
    bad_tokens = [
        "earbuds",
        "headphones",
        "booster",
        "holder",
        "tripod",
        "plan",
        "sim card",
        "memory card",
        "case",
        "screen protector",
        "ring light",
        "book",
        "amplifier",
        "cable",
    ]
    if any(tok in t for tok in bad_tokens):
        return False
    return "phone" in t or "smartphone" in t or "galaxy" in t or "iphone" in t or "pixel" in t


def _processor_tier_from_title(title: str, is_premium: int) -> int:
    t = title.lower()
    if is_premium or "ultra" in t or "snapdragon 8" in t or "pro" in t:
        return 2
    if "5g" in t or "plus" in t:
        return 1
    return 0


def load_primary_rows() -> List[Dict]:
    if not PRIMARY_CSV.exists():
        return []
    with PRIMARY_CSV.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_external_rows() -> List[Dict]:
    if not EXTERNAL_CSV.exists():
        return []

    rows: List[Dict] = []
    with EXTERNAL_CSV.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            title = (row.get("title") or "").strip()
            if not title or not _looks_like_phone(title):
                continue

            price = _price_from_text(row.get("price"))
            if price <= 0:
                continue

            storage = _as_int(row.get("storage_gb"), 128)
            ram = _as_int(row.get("ram_gb"), 6)
            if ram <= 0:
                ram = 6

            is_premium = _as_int(row.get("is_premium"), 0)
            has_5g = _as_int(row.get("has_5g"), 0)
            camera = 50 if has_5g else 13
            battery = 5000
            processor = _processor_tier_from_title(title, is_premium)

            rows.append(
                {
                    "name": title,
                    "brand": (row.get("brand") or "Unknown").strip(),
                    "price_pkr": str(price),
                    "ram_gb": str(ram),
                    "storage_gb": str(storage),
                    "camera_mp": str(camera),
                    "battery_mah": str(battery),
                    "processor_tier": str(processor),
                    "tier_label": str(_tier_label(price)),
                    "source": "ExternalMarket",
                    "source_url": "",
                }
            )

    return rows


def dedupe(rows: List[Dict]) -> List[Dict]:
    best: Dict[str, Dict] = {}
    for row in rows:
        key = (row.get("name") or "").strip().lower()
        if not key:
            continue

        if key not in best:
            best[key] = row
            continue

        curr_price = _as_int(row.get("price_pkr"), 0)
        prev_price = _as_int(best[key].get("price_pkr"), 0)
        if curr_price and (not prev_price or curr_price < prev_price):
            best[key] = row

    return list(best.values())


def run() -> None:
    primary = load_primary_rows()
    external = load_external_rows()
    merged = dedupe([*primary, *external])

    if not merged:
        print("No rows available to merge.")
        return

    fieldnames = [
        "name",
        "brand",
        "price_pkr",
        "ram_gb",
        "storage_gb",
        "camera_mp",
        "battery_mah",
        "processor_tier",
        "tier_label",
        "source",
        "source_url",
    ]

    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged)

    print(f"Merged rows: {len(merged)}")
    print(f"External accepted rows: {len(external)}")
    print(f"Output: {OUT_CSV}")


if __name__ == "__main__":
    run()
