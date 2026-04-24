from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


def _normalize(value: float, min_v: float, max_v: float) -> float:
    if max_v == min_v:
        return 1.0
    return (value - min_v) / (max_v - min_v)


def _tier_from_price(price: int) -> str:
    if price < 30000:
        return "Budget"
    if price <= 70000:
        return "Mid-Range"
    if price <= 150000:
        return "High-End"
    return "Premium"


class Recommender:
    def __init__(self, phones_path: Path) -> None:
        self.phones_path = phones_path
        self.phones = self._load_phones()

    def _load_phones(self) -> List[Dict]:
        with self.phones_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload["phones"]

    def recommend(self, specs: Dict, tier: str, top_k: int = 3) -> List[Dict]:
        budget = specs.get("budget_pkr")
        brand = specs.get("brand")

        candidates = [p for p in self.phones if _tier_from_price(int(p["price_pkr"])) == tier]

        if budget:
            candidates = [p for p in candidates if int(p["price_pkr"]) <= int(budget)]

        if brand:
            candidates = [p for p in candidates if p.get("brand", "").lower() == brand.lower()]

        if not candidates:
            candidates = [p for p in self.phones if _tier_from_price(int(p["price_pkr"])) == tier]

        if not candidates:
            return []

        prices = [int(p["price_pkr"]) for p in candidates]
        min_price, max_price = min(prices), max(prices)

        scored = []
        for p in candidates:
            ram = float(p.get("ram_gb") or 0)
            camera = float(p.get("camera_mp") or 0)
            battery = float(p.get("battery_mah") or 0)
            price = float(p.get("price_pkr") or 1)

            ram_score = ram / 16.0
            camera_score = camera / 108.0
            battery_score = battery / 7000.0
            normalized_price = _normalize(price, min_price, max_price) + 0.2

            value_score = (ram_score + camera_score + battery_score) / normalized_price
            scored.append((value_score, p))

        scored.sort(key=lambda item: item[0], reverse=True)

        results = []
        for _, phone in scored[:top_k]:
            results.append(
                {
                    "name": phone["name"],
                    "specs": (
                        f"{phone['ram_gb']}GB | {phone['storage_gb']}GB | "
                        f"{phone['camera_mp']}MP | {phone['battery_mah']}mAh"
                    ),
                    "price_pkr": int(phone["price_pkr"]),
                    "source": phone["source"],
                    "url": phone["url"],
                }
            )

        return results
