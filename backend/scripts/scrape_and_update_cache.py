from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CACHE_FILE = DATA_DIR / "phones.json"
TIMEOUT = 10

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


@dataclass
class PhoneRecord:
    name: str
    brand: str
    ram_gb: int
    storage_gb: int
    camera_mp: int
    battery_mah: int
    processor_tier: int
    price_pkr: int
    source: str
    url: str
    scraped_at: str

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "brand": self.brand,
            "ram_gb": self.ram_gb,
            "storage_gb": self.storage_gb,
            "camera_mp": self.camera_mp,
            "battery_mah": self.battery_mah,
            "processor_tier": self.processor_tier,
            "price_pkr": self.price_pkr,
            "source": self.source,
            "url": self.url,
            "scraped_at": self.scraped_at,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_price(text: str) -> Optional[int]:
    cleaned = text.replace(",", "")
    match = re.search(r"(\d{4,7})", cleaned)
    if not match:
        return None
    return int(match.group(1))


def _extract_specs_from_name(name: str) -> Dict[str, int]:
    lower = name.lower()

    ram = 6
    storage = 128
    camera = 50
    battery = 5000

    ram_match = re.search(r"(\d{1,2})\s*gb\s*ram", lower)
    storage_match = re.search(r"(\d{2,4})\s*gb", lower)
    camera_match = re.search(r"(\d{2,3})\s*mp", lower)

    if ram_match:
        ram = int(ram_match.group(1))
    if storage_match:
        storage = int(storage_match.group(1))
    if camera_match:
        camera = int(camera_match.group(1))

    return {
        "ram_gb": ram,
        "storage_gb": storage,
        "camera_mp": camera,
        "battery_mah": battery,
        "processor_tier": 1,
    }


def _guess_brand(name: str) -> str:
    known = [
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
    ]
    for brand in known:
        if brand.lower() in name.lower():
            return brand
    return "Unknown"


def _build_record(name: str, price: int, source: str, url: str) -> PhoneRecord:
    specs = _extract_specs_from_name(name)
    return PhoneRecord(
        name=name.strip(),
        brand=_guess_brand(name),
        ram_gb=specs["ram_gb"],
        storage_gb=specs["storage_gb"],
        camera_mp=specs["camera_mp"],
        battery_mah=specs["battery_mah"],
        processor_tier=specs["processor_tier"],
        price_pkr=price,
        source=source,
        url=url,
        scraped_at=_now_iso(),
    )


def _safe_get(url: str) -> Optional[str]:
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if response.status_code != 200:
            return None
        return response.text
    except requests.RequestException:
        return None


def scrape_whatmobile() -> List[PhoneRecord]:
    url = "https://www.whatmobile.com.pk/"
    html = _safe_get(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    records: List[PhoneRecord] = []

    for item in soup.select(".mobile, .product, .post")[:30]:
        name_node = item.select_one("h2, h3, .title, a")
        price_node = item.select_one(".price, .Price, .rs, .amount")

        if not name_node or not price_node:
            continue

        name = name_node.get_text(" ", strip=True)
        price = _extract_price(price_node.get_text(" ", strip=True))
        link = name_node.get("href") if name_node.name == "a" else None
        if not link:
            link = url

        if not name or price is None:
            continue

        records.append(_build_record(name=name, price=price, source="WhatMobile", url=link))

    return records


def scrape_hamariweb() -> List[PhoneRecord]:
    url = "https://hamariweb.com/mobiles/"
    html = _safe_get(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    records: List[PhoneRecord] = []

    for item in soup.select(".mobile-card, .item, .post")[:30]:
        name_node = item.select_one("h2, h3, .title, a")
        price_node = item.select_one(".price, .Price, .amount")

        if not name_node or not price_node:
            continue

        name = name_node.get_text(" ", strip=True)
        price = _extract_price(price_node.get_text(" ", strip=True))
        link = name_node.get("href") if name_node.name == "a" else None
        if not link:
            link = url

        if not name or price is None:
            continue

        records.append(_build_record(name=name, price=price, source="HamariWeb", url=link))

    return records


def scrape_megapk() -> List[PhoneRecord]:
    url = "https://www.megapk.com/"
    html = _safe_get(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    records: List[PhoneRecord] = []

    for item in soup.select(".product, .product-item, .item")[:30]:
        name_node = item.select_one("h2, h3, .title, a")
        price_node = item.select_one(".price, .amount")

        if not name_node or not price_node:
            continue

        name = name_node.get_text(" ", strip=True)
        price = _extract_price(price_node.get_text(" ", strip=True))
        link = name_node.get("href") if name_node.name == "a" else None
        if not link:
            link = url

        if not name or price is None:
            continue

        records.append(_build_record(name=name, price=price, source="MegaPK", url=link))

    return records


def _load_existing() -> List[Dict]:
    if not CACHE_FILE.exists():
        return []

    with CACHE_FILE.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("phones", [])


def _dedupe_by_name_keep_lowest(records: Iterable[Dict]) -> List[Dict]:
    best: Dict[str, Dict] = {}

    for row in records:
        key = row["name"].strip().lower()
        if key not in best:
            best[key] = row
            continue

        if int(row["price_pkr"]) < int(best[key]["price_pkr"]):
            best[key] = row

    return sorted(best.values(), key=lambda r: (int(r["price_pkr"]), r["name"]))


def run() -> None:
    print("Starting scrape and cache update...")

    existing = _load_existing()

    live: List[PhoneRecord] = []
    live.extend(scrape_whatmobile())
    live.extend(scrape_hamariweb())
    live.extend(scrape_megapk())

    live_dicts = [r.to_dict() for r in live]

    if not live_dicts:
        print("No live records collected. Keeping existing cache unchanged.")
        print(f"Current cache records: {len(existing)}")
        return

    merged = _dedupe_by_name_keep_lowest([*existing, *live_dicts])

    payload = {
        "phones": merged,
        "updated_at": _now_iso(),
        "sources": ["WhatMobile", "HamariWeb", "MegaPK"],
        "record_count": len(merged),
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with CACHE_FILE.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Cache updated successfully. Total records: {len(merged)}")


if __name__ == "__main__":
    run()
