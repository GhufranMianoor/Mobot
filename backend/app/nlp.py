from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Tuple

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

BRANDS = [
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
]


def _detect_deal_filter(query: str) -> str | None:
    lowered = query.lower()

    overpriced_tokens = (
        "overpriced",
        "over priced",
        "mehnga",
        "mahinga",
        "zyada price",
        "expensive",
    )
    great_tokens = (
        "great deal",
        "best deal",
        "sasta",
        "cheap deal",
        "value deal",
    )
    fair_tokens = (
        "fair price",
        "balanced",
        "theek price",
        "reasonable",
    )

    if any(token in lowered for token in overpriced_tokens):
        return "Overpriced"
    if any(token in lowered for token in great_tokens):
        return "Great Deal"
    if any(token in lowered for token in fair_tokens):
        return "Fair Price"
    return None


def _detect_requested_tier(query: str) -> str | None:
    lowered = query.lower()

    if any(token in lowered for token in ("premium", "flagship", "ultra")):
        return "Premium"
    if any(token in lowered for token in ("high-end", "high end", "top tier")):
        return "High-End"
    if any(token in lowered for token in ("mid-range", "mid range", "middle range")):
        return "Mid-Range"
    if any(token in lowered for token in ("budget", "entry-level", "entry level", "cheap")):
        return "Budget"

    return None


def _detect_intent_mode(query: str, brand: str | None) -> str:
    lowered = query.lower()
    brand_list_terms = ("all ", "list ", "show ", "display ", "every ", "saare", "sare", "dikhao")

    if _detect_requested_tier(query) is not None:
        return "recommend"

    if brand and any(term in lowered for term in brand_list_terms):
        return "brand_list"

    if any(term in lowered for term in brand_list_terms) and ("phone" in lowered or "phones" in lowered or "mobile" in lowered):
        return "all_list"

    return "recommend"


def _extract_budget(raw: str) -> int | None:
    text = raw.lower()

    # Matches values like 50k, 80 k, rs 70000, 70,000
    k_match = re.search(r"(\d{1,3})\s*k", text)
    if k_match:
        return int(k_match.group(1)) * 1000

    numeric_match = re.search(r"(?:rs\.?\s*)?(\d{4,6})", text)
    if numeric_match:
        return int(numeric_match.group(1))

    return None


def regex_extract(query: str) -> Dict:
    budget = _extract_budget(query)

    ram_match = re.search(r"(\d{1,2})\s*gb\s*ram", query, flags=re.IGNORECASE)
    storage_match = re.search(r"(\d{2,4})\s*gb\s*(?:storage|rom)", query, flags=re.IGNORECASE)
    camera_match = re.search(r"(\d{2,3})\s*mp", query, flags=re.IGNORECASE)
    battery_match = re.search(r"(\d{4,5})\s*mah", query, flags=re.IGNORECASE)

    brand = None
    for b in BRANDS:
        if b.lower() in query.lower():
            brand = b
            break

    priority = "value"
    lowered = query.lower()
    if "camera" in lowered:
        priority = "camera"
    elif "gaming" in lowered:
        priority = "gaming"
    elif "performance" in lowered:
        priority = "performance"
    elif "business" in lowered or "work" in lowered:
        priority = "business"
    elif "battery" in lowered:
        priority = "battery"

    intent_mode = _detect_intent_mode(query, brand)

    return {
        "budget_pkr": budget,
        "ram_gb": int(ram_match.group(1)) if ram_match else None,
        "storage_gb": int(storage_match.group(1)) if storage_match else None,
        "camera_mp": int(camera_match.group(1)) if camera_match else None,
        "battery_mah": int(battery_match.group(1)) if battery_match else None,
        "brand": brand,
        "priority": priority,
        "intent_mode": intent_mode,
        "requested_tier": _detect_requested_tier(query),
        "deal_filter": _detect_deal_filter(query),
    }


def openrouter_extract(query: str) -> Dict:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")

    system_prompt = (
        "Extract mobile phone preferences from user text and return strict JSON with keys: "
        "budget_pkr, ram_gb, storage_gb, camera_mp, battery_mah, brand, priority, intent_mode, deal_filter. "
        "Use null when unknown. priority should be one of: value, camera, performance, gaming, business, battery. "
        "intent_mode should be one of recommend, brand_list, all_list. "
        "deal_filter should be one of Great Deal, Fair Price, Overpriced, or null. "
        "Use brand_list when the user asks for all/list/show/display/every phone from a specific brand. "
        "Use all_list when the user asks for all/list/show/display/every phones without naming a brand."
    )

    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ],
        "response_format": {"type": "json_object"},
    }

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "http://localhost"),
            "X-Title": os.getenv("OPENROUTER_APP_NAME", "Mobot"),
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError("OpenRouter call failed") from exc

    content = body["choices"][0]["message"]["content"]
    parsed = json.loads(content)

    regex_based = regex_extract(query)

    def _pick_numeric(key: str):
        return regex_based.get(key) if regex_based.get(key) is not None else parsed.get(key)

    merged_brand = regex_based.get("brand") or parsed.get("brand")
    merged_priority = (
        regex_based.get("priority")
        if regex_based.get("priority") and regex_based.get("priority") != "value"
        else (parsed.get("priority") or regex_based.get("priority") or "value")
    )

    return {
        "budget_pkr": _pick_numeric("budget_pkr"),
        "ram_gb": _pick_numeric("ram_gb"),
        "storage_gb": _pick_numeric("storage_gb"),
        "camera_mp": _pick_numeric("camera_mp"),
        "battery_mah": _pick_numeric("battery_mah"),
        "brand": merged_brand,
        "priority": merged_priority,
        "intent_mode": _detect_intent_mode(query, merged_brand) or parsed.get("intent_mode") or "recommend",
        "requested_tier": _detect_requested_tier(query),
        "deal_filter": _detect_deal_filter(query) or parsed.get("deal_filter"),
    }


def extract_specs(query: str) -> Tuple[Dict, str]:
    try:
        return openrouter_extract(query), "openrouter"
    except Exception:
        return regex_extract(query), "regex"
