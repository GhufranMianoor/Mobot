from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional


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

    def recommend(self, specs: Dict, tier: Optional[str], top_k: int = 3) -> List[Dict]:
        budget = specs.get("budget_pkr")
        brand = specs.get("brand")
        ram_gb = specs.get("ram_gb")
        storage_gb = specs.get("storage_gb")
        camera_mp = specs.get("camera_mp")
        battery_mah = specs.get("battery_mah")
        has_explicit_feature_filters = any(value is not None for value in (ram_gb, storage_gb, camera_mp, battery_mah))
        priority = (specs.get("priority") or "value").lower()
        intent_mode = (specs.get("intent_mode") or "recommend").lower()

        if intent_mode == "all_list":
            candidates = sorted(self.phones, key=lambda p: int(p.get("price_pkr") or 0))
            return [
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
                for phone in candidates
            ]

        if intent_mode == "brand_list" and brand:
            candidates = [p for p in self.phones if p.get("brand", "").lower() == brand.lower()]
            candidates.sort(key=lambda p: int(p.get("price_pkr") or 0))

            return [
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
                for phone in candidates
            ]

        if tier:
            candidates = [p for p in self.phones if _tier_from_price(int(p["price_pkr"])) == tier]
        else:
            candidates = list(self.phones)

        if ram_gb is not None:
            candidates = [p for p in candidates if int(p.get("ram_gb") or 0) >= int(ram_gb)]

        if storage_gb is not None:
            candidates = [p for p in candidates if int(p.get("storage_gb") or 0) >= int(storage_gb)]

        if camera_mp is not None:
            candidates = [p for p in candidates if int(p.get("camera_mp") or 0) >= int(camera_mp)]

        if battery_mah is not None:
            candidates = [p for p in candidates if int(p.get("battery_mah") or 0) >= int(battery_mah)]

        if budget:
            budget_candidates = [p for p in candidates if int(p["price_pkr"]) <= int(budget)]
            if budget_candidates:
                candidates = budget_candidates
            else:
                # If tier + budget gives no phones, broaden search to any phone under budget.
                candidates = [p for p in self.phones if int(p["price_pkr"]) <= int(budget)]

        if brand:
            candidates = [p for p in candidates if p.get("brand", "").lower() == brand.lower()]

        if not candidates and tier and not has_explicit_feature_filters:
            candidates = [p for p in self.phones if _tier_from_price(int(p["price_pkr"])) == tier]

        if not candidates:
            return []

        intent_boosts = {
            "value": {"ram": 1.0, "camera": 1.0, "battery": 1.0},
            "camera": {"ram": 0.75, "camera": 1.55, "battery": 0.85},
            "performance": {"ram": 1.45, "camera": 0.8, "battery": 0.9},
            "gaming": {"ram": 1.55, "camera": 0.7, "battery": 1.15},
            "business": {"ram": 1.1, "camera": 0.8, "battery": 1.05},
            "battery": {"ram": 0.8, "camera": 0.75, "battery": 1.6},
        }

        weight_map = {
            "value": {"ram": 1.0, "camera": 1.0, "battery": 1.0, "price": 1.25, "budget_fit": 0.9},
            "camera": {"ram": 0.7, "camera": 1.7, "battery": 0.6, "price": 1.0, "budget_fit": 0.6},
            "performance": {"ram": 1.8, "camera": 0.7, "battery": 0.8, "price": 0.9, "budget_fit": 0.6},
            "gaming": {"ram": 1.7, "camera": 0.65, "battery": 1.2, "price": 0.95, "budget_fit": 0.75},
            "business": {"ram": 1.1, "camera": 0.8, "battery": 1.0, "price": 1.1, "budget_fit": 0.85},
            "battery": {"ram": 0.8, "camera": 0.7, "battery": 1.9, "price": 1.0, "budget_fit": 0.7},
        }
        weights = weight_map.get(priority, weight_map["value"])
        intent_weights = intent_boosts.get(priority, intent_boosts["value"])

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

            budget_fit_score = 0.5
            if budget:
                budget_val = float(budget)
                budget_fit_score = max(0.0, 1.0 - abs(price - budget_val) / max(1.0, budget_val))

            weighted_quality = (
                weights["ram"] * ram_score
                + weights["camera"] * camera_score
                + weights["battery"] * battery_score
                + weights["budget_fit"] * budget_fit_score
            )
            intent_alignment = (
                intent_weights["ram"] * ram_score
                + intent_weights["camera"] * camera_score
                + intent_weights["battery"] * battery_score
            )
            value_score = (weighted_quality * 0.7 + intent_alignment * 0.3) / (normalized_price * weights["price"])
            intent_priority = {
                "camera": (camera_score, battery_score, value_score),
                "performance": (ram_score, battery_score, value_score),
                "gaming": (ram_score, battery_score, value_score),
                "business": (battery_score, ram_score, value_score),
                "battery": (battery_score, ram_score, value_score),
                "value": (value_score, budget_fit_score, battery_score),
            }.get(priority, (value_score, budget_fit_score, battery_score))
            scored.append((intent_priority, value_score, p))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)

        results = []
        for _, _, phone in scored[:top_k]:
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
