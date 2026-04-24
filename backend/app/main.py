from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .classifier import LightweightKNN
from .nlp import extract_specs
from .recommender import Recommender
from .schemas import ChatRequest, ChatResponse, HealthResponse

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

classifier = LightweightKNN(TRAINING_PATH)
recommender = Recommender(PHONES_PATH)


def _build_feature_vector(specs: Dict) -> Dict[str, float]:
    return {
        "ram_gb": float(specs.get("ram_gb") or 6),
        "storage_gb": float(specs.get("storage_gb") or 128),
        "camera_mp": float(specs.get("camera_mp") or 50),
        "battery_mah": float(specs.get("battery_mah") or 5000),
        "processor_tier": 1.0,
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
        groq_configured=bool(__import__("os").getenv("GROQ_API_KEY", "").strip()),
        cache_age_hours=round(cache_age_hours, 2),
        phones_indexed=len(phones),
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    specs, nlp_source = extract_specs(request.message)
    features = _build_feature_vector(specs)
    prediction = classifier.predict(features)

    phones = recommender.recommend(specs=specs, tier=prediction.tier, top_k=3)

    if phones:
        reply = f"Top {prediction.tier} options for your query:"
    else:
        reply = "I could not find close matches right now. Try broadening your budget or brand preference."

    return ChatResponse(
        reply=reply,
        tier=prediction.tier,
        confidence=prediction.confidence,
        nlp_source=nlp_source,
        phones=phones,
    )
