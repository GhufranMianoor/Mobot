from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

IN_CSV = DATA_DIR / "user_supplied_phones.csv"
PHONES_JSON = DATA_DIR / "phones.json"
TRAINING_CSV = DATA_DIR / "training_mobile_specs.csv"


def _to_int(value: str | None, default: int = 0) -> int:
    try:
        if value is None or str(value).strip() == "":
            return default
        return int(float(str(value).strip()))
    except ValueError:
        return default


def _tier_label(price: int) -> int:
    if price < 30000:
        return 0
    if price <= 70000:
        return 1
    if price <= 150000:
        return 2
    return 3


def _normalize_source(value: str | None) -> str:
    v = (value or "").strip().lower()
    if v == "whatmobile":
        return "WhatMobile"
    if v == "hamariweb":
        return "HamariWeb"
    if v == "megapk":
        return "MegaPK"
    return (value or "UserData").strip() or "UserData"


def _source_url(source: str) -> str:
    if source == "WhatMobile":
        return "https://www.whatmobile.com.pk"
    if source == "HamariWeb":
        return "https://hamariweb.com"
    if source == "MegaPK":
        return "https://megapk.com"
    return ""


def _is_supported_iphone(name: str, brand: str) -> bool:
    brand_norm = (brand or "").strip().lower()
    name_norm = (name or "").strip().lower()

    if brand_norm != "apple" and "iphone" not in name_norm:
        return True

    match = re.search(r"\biphone\s+(\d{1,3})\b", name_norm)
    if not match:
        return True
    return int(match.group(1)) <= 17


def load_csv_rows() -> list[dict]:
    if not IN_CSV.exists():
        raise FileNotFoundError(
            f"Input file not found: {IN_CSV}\n"
            "Save your pasted dataset to backend/data/user_supplied_phones.csv first."
        )

    rows: list[dict] = []
    with IN_CSV.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            name = (row.get("model_name") or "").strip()
            brand = (row.get("brand") or "Unknown").strip()
            if not name:
                continue
            if not _is_supported_iphone(name, brand):
                continue

            source = _normalize_source(row.get("source"))
            scraped_at = (row.get("scraped_at") or "").strip() or datetime.now(timezone.utc).isoformat()

            rows.append(
                {
                    "name": name,
                    "brand": brand,
                    "ram_gb": _to_int(row.get("ram_gb"), 4),
                    "storage_gb": _to_int(row.get("storage_gb"), 64),
                    "camera_mp": _to_int(row.get("camera_mp"), 13),
                    "battery_mah": _to_int(row.get("battery_mah"), 4000),
                    "processor_tier": max(0, min(2, _to_int(row.get("processor_tier"), 1))),
                    "price_pkr": max(1, _to_int(row.get("price_pkr"), 1)),
                    "source": source,
                    "url": _source_url(source),
                    "scraped_at": scraped_at,
                }
            )
    return rows


def merge_phones(rows: list[dict]) -> int:
    payload = {"phones": []}
    if PHONES_JSON.exists():
        payload = json.loads(PHONES_JSON.read_text(encoding="utf-8"))

    best: dict[str, dict] = {}
    for phone in payload.get("phones", []):
        best[phone["name"].strip().lower()] = phone

    for phone in rows:
        key = phone["name"].strip().lower()
        prev = best.get(key)
        if not prev or int(phone["price_pkr"]) < int(prev.get("price_pkr", 10**12)):
            best[key] = phone

    merged = sorted(best.values(), key=lambda item: int(item.get("price_pkr", 0)))
    PHONES_JSON.write_text(json.dumps({"phones": merged}, ensure_ascii=True, indent=2), encoding="utf-8")
    return len(merged)


def append_training_rows(rows: list[dict]) -> int:
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

    existing: list[dict] = []
    if TRAINING_CSV.exists():
        with TRAINING_CSV.open("r", encoding="utf-8", newline="") as f:
            existing = list(csv.DictReader(f))

    merged: dict[str, dict] = {r.get("name", "").strip().lower(): r for r in existing if r.get("name")}
    for phone in rows:
        key = phone["name"].strip().lower()
        merged[key] = {
            "name": phone["name"],
            "brand": phone["brand"],
            "price_pkr": str(phone["price_pkr"]),
            "ram_gb": str(phone["ram_gb"]),
            "storage_gb": str(phone["storage_gb"]),
            "camera_mp": str(phone["camera_mp"]),
            "battery_mah": str(phone["battery_mah"]),
            "processor_tier": str(phone["processor_tier"]),
            "tier_label": str(_tier_label(int(phone["price_pkr"]))),
            "source": phone["source"],
            "source_url": phone["url"],
        }

    rows_out = sorted(merged.values(), key=lambda item: int(item.get("price_pkr", 0)))
    with TRAINING_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)
    return len(rows_out)


def main() -> None:
    rows = load_csv_rows()
    phones_count = merge_phones(rows)
    training_count = append_training_rows(rows)

    print(f"Imported rows: {len(rows)}")
    print(f"phones.json total: {phones_count}")
    print(f"training_mobile_specs.csv total: {training_count}")


if __name__ == "__main__":
    main()
