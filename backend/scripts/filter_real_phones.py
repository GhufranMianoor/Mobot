from __future__ import annotations

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PHONES_JSON = DATA_DIR / "phones.json"

ALLOWED_SOURCES = {"WhatMobile", "HamariWeb", "MegaPK"}

ROOT_URLS = {
    "https://www.whatmobile.com.pk",
    "https://hamariweb.com",
    "https://mega.pk",
    "https://megapk.com",
    "https://www.megapk.com",
    "https://www.megapk.com.pk",
}

KNOWN_BRANDS = {
    "Samsung",
    "Xiaomi",
    "Infinix",
    "Tecno",
    "Realme",
    "Vivo",
    "Oppo",
    "Apple",
    "Google",
    "OnePlus",
    "Nokia",
    "Motorola",
    "Itel",
    "Sparx",
    "Honor",
    "Huawei",
}


def _looks_like_real_name(name: str) -> bool:
    n = name.strip()
    if len(n) < 4:
        return False
    if not re.search(r"[A-Za-z]", n):
        return False
    if re.search(r"\b(test|dummy|sample|unknown|null)\b", n, flags=re.IGNORECASE):
        return False

    # iPhone sanity guard to drop clearly synthetic generations.
    m = re.search(r"\biphone\s+(\d{1,3})\b", n, flags=re.IGNORECASE)
    if m and int(m.group(1)) > 17:
        return False

    return True


def _is_concrete_product_url(url: str) -> bool:
    u = (url or "").strip()
    if not u:
        return False

    u_no_slash = u.rstrip("/")
    if u_no_slash in ROOT_URLS:
        return False

    # Require a path segment after the host so it points to a product/listing page.
    return "/" in u.removeprefix("https://").removeprefix("http://")


def _valid_row(row: dict) -> bool:
    source = str(row.get("source") or "").strip()
    brand = str(row.get("brand") or "").strip()
    name = str(row.get("name") or "").strip()
    url = str(row.get("url") or "").strip()

    if source not in ALLOWED_SOURCES:
        return False
    if brand not in KNOWN_BRANDS:
        return False
    if not _looks_like_real_name(name):
        return False
    if not _is_concrete_product_url(url):
        return False

    try:
        price = int(row.get("price_pkr") or 0)
    except (TypeError, ValueError):
        return False
    if price < 4000 or price > 700000:
        return False

    return True


def run() -> None:
    payload = json.loads(PHONES_JSON.read_text(encoding="utf-8"))
    phones = payload.get("phones", [])

    kept = [p for p in phones if _valid_row(p)]

    # Deduplicate by name and keep lowest price.
    best: dict[str, dict] = {}
    for row in kept:
        key = str(row.get("name") or "").strip().lower()
        if not key:
            continue
        prev = best.get(key)
        if not prev or int(row["price_pkr"]) < int(prev["price_pkr"]):
            best[key] = row

    out = sorted(best.values(), key=lambda r: (int(r.get("price_pkr") or 0), str(r.get("name") or "")))

    payload["phones"] = out
    payload["record_count"] = len(out)
    PHONES_JSON.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    print(f"Original rows: {len(phones)}")
    print(f"Kept rows: {len(out)}")
    print(f"Removed rows: {len(phones) - len(out)}")


if __name__ == "__main__":
    run()
