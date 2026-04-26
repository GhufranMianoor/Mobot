from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "training_mobile_specs.csv"
PHONES_CACHE_PATH = DATA_DIR / "phones.json"

BASE_URL = "https://www.whatmobile.com.pk"
HOME_URL = f"{BASE_URL}/"
TIMEOUT = 12
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


@dataclass
class PhoneRow:
    name: str
    brand: str
    price_pkr: int
    ram_gb: int
    storage_gb: int
    camera_mp: int
    battery_mah: int
    processor_tier: int
    tier_label: int
    source: str
    source_url: str


def _safe_get(url: str) -> Optional[str]:
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if response.status_code != 200:
            return None
        return response.text
    except requests.RequestException:
        return None


def _extract_int(pattern: str, text: str) -> Optional[int]:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1))


def _price_to_tier_label(price: int) -> int:
    if price < 30000:
        return 0
    if price <= 70000:
        return 1
    if price <= 150000:
        return 2
    return 3


def _processor_tier_from_text(text: str) -> int:
    lowered = text.lower()

    high_tokens = [
        "snapdragon 8",
        "dimensity 9000",
        "dimensity 8000",
        "apple a1",
        "apple a17",
        "apple a18",
        "tensor g3",
        "tensor g4",
        "exynos 2400",
    ]
    mid_tokens = [
        "snapdragon 7",
        "snapdragon 6",
        "dimensity 700",
        "dimensity 800",
        "dimensity 900",
        "helio g99",
        "helio g95",
        "exynos 1",
    ]

    if any(token in lowered for token in high_tokens):
        return 2
    if any(token in lowered for token in mid_tokens):
        return 1
    return 0


def _extract_specs(detail_html: str) -> tuple[int, int, int, int, int]:
    soup = BeautifulSoup(detail_html, "html.parser")

    def row_value(label: str) -> str:
        header = soup.find("td", string=re.compile(rf"^{re.escape(label)}$", re.IGNORECASE))
        if not header:
            return ""
        value_node = header.find_next_sibling("td")
        if not value_node:
            return ""
        return value_node.get_text(" ", strip=True)

    memory_text = row_value("Memory")
    camera_text = row_value("Camera")
    battery_text = row_value("Battery")
    cpu_text = row_value("CPU")

    ram_gb = _extract_int(r"(\d{1,2})\s*GB\s*RAM", memory_text) or 6
    storage_gb = _extract_int(r"(\d{2,4})\s*GB\s*,?\s*Built", memory_text)
    if storage_gb is None:
        storage_gb = _extract_int(r"(\d{2,4})\s*GB", memory_text) or 128

    camera_mp = _extract_int(r"(\d{1,3})\s*MP", camera_text) or 50
    battery_mah = _extract_int(r"(\d{4,5})\s*mAh", battery_text) or 5000
    processor_tier = _processor_tier_from_text(cpu_text)

    return ram_gb, storage_gb, camera_mp, battery_mah, processor_tier


def scrape_phone_links() -> List[tuple[str, int, str]]:
    html = _safe_get(HOME_URL)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    rows: List[tuple[str, int, str]] = []

    for card in soup.select("li.product"):
        link = card.select_one("a.BiggerText")
        price_node = card.select_one("span.PriceFont")

        if not link or not price_node:
            continue

        name = link.get_text(" ", strip=True).replace("\n", " ").strip()
        href = link.get("href", "").strip()
        if not href:
            continue

        if href.startswith("/"):
            url = f"{BASE_URL}{href}"
        elif href.startswith("http"):
            url = href
        else:
            url = f"{BASE_URL}/{href}"

        price_match = re.search(r"(\d[\d,]{3,})", price_node.get_text(" ", strip=True))
        if not price_match:
            continue
        price = int(price_match.group(1).replace(",", ""))

        rows.append((name, price, url))

    unique = {}
    for name, price, url in rows:
        key = name.lower().strip()
        if key not in unique:
            unique[key] = (name, price, url)

    return list(unique.values())


def scrape_megapk_live() -> List[PhoneRow]:
    # MegaPK domain may be unavailable or parked; keep this as best-effort live scrape.
    urls = [
        "https://mega.pk/mobile-phones",
    ]

    rows: List[PhoneRow] = []
    for url in urls:
        html = _safe_get(url)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".product, .product-item, .item")
        for card in cards:
            name_node = card.select_one("h2, h3, .title, a")
            price_node = card.select_one(".price, .amount")
            if not name_node or not price_node:
                continue

            name = name_node.get_text(" ", strip=True)
            price_match = re.search(r"(\d[\d,]{3,})", price_node.get_text(" ", strip=True))
            if not price_match:
                continue

            href = name_node.get("href", "").strip()
            if href.startswith("http"):
                link = href
            elif href.startswith("/"):
                link = f"https://mega.pk{href}"
            else:
                link = url

            price = int(price_match.group(1).replace(",", ""))
            brand = name.split(" ")[0].strip()
            rows.append(
                PhoneRow(
                    name=name,
                    brand=brand,
                    price_pkr=price,
                    ram_gb=6,
                    storage_gb=128,
                    camera_mp=50,
                    battery_mah=5000,
                    processor_tier=1,
                    tier_label=_price_to_tier_label(price),
                    source="MegaPK",
                    source_url=link,
                )
            )

    return rows


def load_megapk_from_cache() -> List[PhoneRow]:
    if not PHONES_CACHE_PATH.exists():
        return []

    with PHONES_CACHE_PATH.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    phones = payload.get("phones", [])
    rows: List[PhoneRow] = []
    for phone in phones:
        source = str(phone.get("source", ""))
        if "megapk" not in source.lower():
            continue

        name = str(phone.get("name", "")).strip()
        if not name:
            continue

        price = int(phone.get("price_pkr") or 0)
        if price <= 0:
            continue

        rows.append(
            PhoneRow(
                name=name,
                brand=str(phone.get("brand") or name.split(" ")[0]),
                price_pkr=price,
                ram_gb=int(phone.get("ram_gb") or 6),
                storage_gb=int(phone.get("storage_gb") or 128),
                camera_mp=int(phone.get("camera_mp") or 50),
                battery_mah=int(phone.get("battery_mah") or 5000),
                processor_tier=int(phone.get("processor_tier") or 1),
                tier_label=_price_to_tier_label(price),
                source="MegaPK",
                source_url=str(phone.get("url") or "https://mega.pk"),
            )
        )

    return rows


def _dedupe_rows(rows: List[PhoneRow]) -> List[PhoneRow]:
    best: Dict[str, PhoneRow] = {}
    for row in rows:
        key = row.name.strip().lower()
        existing = best.get(key)
        if existing is None or row.price_pkr < existing.price_pkr:
            best[key] = row
    return list(best.values())


def run() -> None:
    print("Collecting phones from WhatMobile...")

    phones = scrape_phone_links()

    out_rows: List[PhoneRow] = []

    for idx, (name, price, url) in enumerate(phones, start=1):
        detail_html = _safe_get(url)
        if not detail_html:
            continue

        ram_gb, storage_gb, camera_mp, battery_mah, processor_tier = _extract_specs(detail_html)

        brand = name.split(" ")[0].strip()
        out_rows.append(
            PhoneRow(
                name=name,
                brand=brand,
                price_pkr=price,
                ram_gb=ram_gb,
                storage_gb=storage_gb,
                camera_mp=camera_mp,
                battery_mah=battery_mah,
                processor_tier=processor_tier,
                tier_label=_price_to_tier_label(price),
                source="WhatMobile",
                source_url=url,
            )
        )

        if idx % 10 == 0:
            print(f"Processed {idx} phones...")

    megapk_live_rows = scrape_megapk_live()
    if megapk_live_rows:
        print(f"Collected {len(megapk_live_rows)} live rows from MegaPK.")
    else:
        print("No live MegaPK rows collected; loading MegaPK entries from cache...")

    megapk_cache_rows = load_megapk_from_cache()
    if megapk_cache_rows:
        print(f"Loaded {len(megapk_cache_rows)} MegaPK rows from cache.")

    out_rows.extend(megapk_live_rows)
    out_rows.extend(megapk_cache_rows)
    out_rows = _dedupe_rows(out_rows)

    if not out_rows:
        print("No rows with usable specs extracted.")
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
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
        )

        for row in out_rows:
            writer.writerow(
                [
                    row.name,
                    row.brand,
                    row.price_pkr,
                    row.ram_gb,
                    row.storage_gb,
                    row.camera_mp,
                    row.battery_mah,
                    row.processor_tier,
                    row.tier_label,
                    row.source,
                    row.source_url,
                ]
            )

    print(f"Training CSV generated: {CSV_PATH}")
    print(f"Total rows: {len(out_rows)}")


if __name__ == "__main__":
    run()
