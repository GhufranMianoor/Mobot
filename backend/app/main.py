from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .classifier import LightweightKNN, select_best_k
from .nlp import extract_specs
from .recommender import Recommender
from .schemas import ChatRequest, ChatResponse, HealthResponse, SearchRequest, SearchResponse

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PHONES_PATH = DATA_DIR / "phones.json"
TRAINING_PATH = DATA_DIR / "training_data.json"

app = FastAPI(title="Mobot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_base_classifier = LightweightKNN(TRAINING_PATH)
_best_k = select_best_k(_base_classifier.rows)
classifier = LightweightKNN(rows=_base_classifier.rows, k=_best_k)
recommender = Recommender(PHONES_PATH)


def _tier_from_budget(budget: int) -> str:
    if budget < 30000:
        return "Budget"
    if budget <= 70000:
        return "Mid-Range"
    if budget <= 150000:
        return "High-End"
    return "Premium"


def _tier_from_price(price: int) -> str:
    if price < 30000:
        return "Budget"
    if price <= 70000:
        return "Mid-Range"
    if price <= 150000:
        return "High-End"
    return "Premium"


def _deal_badge(actual_tier: str, predicted_tier: str) -> str:
    rank = {"Budget": 0, "Mid-Range": 1, "High-End": 2, "Premium": 3}
    actual = rank.get(actual_tier, 1)
    predicted = rank.get(predicted_tier, 1)

    if predicted > actual:
        return "Great Deal"
    if predicted < actual:
        return "Overpriced"
    return "Fair Price"


def _build_feature_vector(specs: Dict) -> Dict[str, float]:
    return {
        "ram_gb": float(specs.get("ram_gb") or 6),
        "storage_gb": float(specs.get("storage_gb") or 128),
        "camera_mp": float(specs.get("camera_mp") or 50),
        "battery_mah": float(specs.get("battery_mah") or 5000),
        "processor_tier": 1.0,
    }


def _select_tier_from_specs(specs: Dict, intent_mode: str) -> tuple[Optional[str], float, bool]:
    budget = specs.get("budget_pkr")
    requested_tier = specs.get("requested_tier")

    if intent_mode in {"brand_list", "all_list"}:
        return None, 1.0, False
    if requested_tier in {"Budget", "Mid-Range", "High-End", "Premium"}:
        return requested_tier, 0.95, False
    if budget is not None:
        return _tier_from_budget(int(budget)), 0.92, False

    # No explicit budget/tier context: search across all tiers instead of forcing Mid-Range.
    return None, 0.85, False


def _natural_reply(specs: Dict, phones: list[Dict], tier: str, intent_mode: str, knn_used: bool) -> str:
    brand = specs.get("brand")
    budget = specs.get("budget_pkr")
    priority = specs.get("priority")

    if intent_mode == "brand_list" and brand:
        return f"I found {len(phones)} {brand} options based on your request."

    if intent_mode == "all_list":
        return f"I listed all available phones ({len(phones)} total) as you asked."

    if not phones:
        if brand and budget:
            return f"I could not find close {brand} matches within about Rs. {int(budget):,}. Try increasing the budget or relaxing constraints."
        if budget:
            return f"I could not find strong matches near Rs. {int(budget):,}. Try a slightly wider budget range."
        return "I could not find close matches for that prompt. Try adding budget, brand, or priority."

    context = []
    if brand:
        context.append(f"{brand} focus")
    if budget:
        context.append(f"budget around Rs. {int(budget):,}")
    if priority and priority != "value":
        context.append(f"{priority} priority")

    context_str = ", ".join(context) if context else "your request"
    model_path = "k-NN tier prediction" if knn_used else "rule-based tiering"
    return f"Based on {context_str}, here are the best {tier} matches I found using {model_path}."


@app.get("/knn/diagnostics")
def knn_diagnostics() -> Dict:
    test_cases = [
        {
            "name": "Budget sanity",
            "expected": "Budget",
            "features": {
                "ram_gb": 3,
                "storage_gb": 32,
                "camera_mp": 13,
                "battery_mah": 4000,
                "processor_tier": 0,
            },
        },
        {
            "name": "Mid-range sanity",
            "expected": "Mid-Range",
            "features": {
                "ram_gb": 8,
                "storage_gb": 128,
                "camera_mp": 64,
                "battery_mah": 5000,
                "processor_tier": 1,
            },
        },
        {
            "name": "High-end sanity",
            "expected": "High-End",
            "features": {
                "ram_gb": 12,
                "storage_gb": 256,
                "camera_mp": 50,
                "battery_mah": 5000,
                "processor_tier": 2,
            },
        },
        {
            "name": "Premium sanity",
            "expected": "Premium",
            "features": {
                "ram_gb": 16,
                "storage_gb": 512,
                "camera_mp": 200,
                "battery_mah": 5000,
                "processor_tier": 2,
            },
        },
    ]

    checks = []
    pass_count = 0
    for case in test_cases:
        prediction = classifier.predict(case["features"])
        passed = prediction.tier == case["expected"]
        pass_count += 1 if passed else 0
        checks.append(
            {
                "name": case["name"],
                "expected": case["expected"],
                "predicted": prediction.tier,
                "confidence": prediction.confidence,
                "passed": passed,
            }
        )

    class_distribution = dict(Counter(int(row["tier_label"]) for row in classifier.rows))
    pretty_distribution = {
        "Budget": class_distribution.get(0, 0),
        "Mid-Range": class_distribution.get(1, 0),
        "High-End": class_distribution.get(2, 0),
        "Premium": class_distribution.get(3, 0),
    }

    return {
        "status": "ok",
        "dataset_samples": len(classifier.rows),
        "k": classifier.k,
        "k_candidates_checked": [k for k in range(1, min(11, len(classifier.rows)) + 1, 2)],
        "pass_count": pass_count,
        "total_checks": len(test_cases),
        "all_passed": pass_count == len(test_cases),
        "class_distribution": pretty_distribution,
        "checks": checks,
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    with PHONES_PATH.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    phones = payload.get("phones", [])
    latest = max((p.get("scraped_at") for p in phones), default=None)

    cache_age_hours = 0.0
    if latest:
        scraped_at = datetime.fromisoformat(latest)
        cache_age_hours = (datetime.now(timezone.utc) - scraped_at).total_seconds() / 3600

    return HealthResponse(
        status="ok",
        openrouter_configured=bool(__import__("os").getenv("OPENROUTER_API_KEY", "").strip()),
        cache_age_hours=round(cache_age_hours, 2),
        phones_indexed=len(phones),
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    specs, nlp_source = extract_specs(request.message)
    intent_mode = (specs.get("intent_mode") or "recommend").lower()
    brand = specs.get("brand")
    tier, confidence, knn_used = _select_tier_from_specs(specs, intent_mode)

    phones = recommender.recommend(specs=specs, tier=tier, top_k=3)

    response_tier = tier or "Any"

    if intent_mode == "brand_list" and brand:
        confidence = 1.0
        response_tier = f"{brand} phones"
    elif intent_mode == "all_list":
        confidence = 1.0
        response_tier = "All phones"

    reply = _natural_reply(
        specs=specs,
        phones=phones,
        tier=response_tier,
        intent_mode=intent_mode,
        knn_used=knn_used,
    )

    return ChatResponse(
        reply=reply,
        tier=response_tier,
        confidence=confidence,
        nlp_source=nlp_source,
        intent_mode=intent_mode if intent_mode in {"recommend", "brand_list", "all_list"} else "recommend",
        knn_used=knn_used,
        phones=phones,
    )


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest) -> SearchResponse:
    specs, nlp_source = extract_specs(request.query)
    intent_mode = (specs.get("intent_mode") or "recommend").lower()
    tier, _, _ = _select_tier_from_specs(specs, intent_mode)
    deal_filter = specs.get("deal_filter")

    results = recommender.recommend(specs=specs, tier=tier, top_k=24)
    phones_by_name = {p.get("name"): p for p in recommender.phones}

    enriched = []
    for phone in results:
        raw = phones_by_name.get(phone.get("name"), {})
        features = {
            "ram_gb": float(raw.get("ram_gb") or 6),
            "storage_gb": float(raw.get("storage_gb") or 128),
            "camera_mp": float(raw.get("camera_mp") or 50),
            "battery_mah": float(raw.get("battery_mah") or 5000),
            "processor_tier": float(raw.get("processor_tier") or 1),
        }
        predicted_tier = classifier.predict(features).tier
        actual_tier = _tier_from_price(int(phone.get("price_pkr") or 0))

        enriched.append(
            {
                "name": phone["name"],
                "specs": phone["specs"],
                "price_pkr": int(phone["price_pkr"]),
                "source": phone["source"],
                "url": phone["url"],
                "actual_tier": actual_tier,
                "predicted_tier": predicted_tier,
                "deal_badge": _deal_badge(actual_tier, predicted_tier),
            }
        )

    if deal_filter in {"Great Deal", "Fair Price", "Overpriced"}:
        enriched = [item for item in enriched if item.get("deal_badge") == deal_filter]

    if intent_mode == "all_list" and deal_filter:
        summary = f"Showing all {deal_filter.lower()} phones ({len(enriched)} results)."
    elif intent_mode == "all_list":
        summary = f"Showing all phones ({len(enriched)} results)."
    elif intent_mode == "brand_list" and specs.get("brand"):
        summary = f"Showing {len(enriched)} {specs['brand']} phones."
    elif deal_filter:
        summary = f"Found {len(enriched)} {deal_filter.lower()} results for your search."
    else:
        summary = f"Found {len(enriched)} results for your search."

    return SearchResponse(
        query=request.query,
        summary=summary,
        tier_used=tier or "Any",
        nlp_source=nlp_source,
        total_results=len(enriched),
        results=enriched,
    )
