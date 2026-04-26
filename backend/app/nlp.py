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

BRAND_ALIASES = {
    "Samsung": ("samsung", "sumsung", "samung", "sam sung"),
    "Xiaomi": ("xiaomi", "xiomi", "redmi", "mi"),
    "Infinix": ("infinix", "infnix", "infinx"),
    "Tecno": ("tecno", "tekno", "tecnoo"),
    "Realme": ("realme", "relme", "real mi"),
    "Vivo": ("vivo", "vevo"),
    "Oppo": ("oppo", "opo"),
    "Apple": ("apple", "iphone", "iphon", "ifone"),
    "Google": ("google", "pixel", "pixle"),
    "OnePlus": ("oneplus", "one plus", "1plus", "oneplsu"),
    "Nokia": ("nokia", "nokiya"),
    "Motorola": ("motorola", "moto", "motrola"),
}


def _detect_deal_filter(query: str) -> str | None:
    lowered = query.lower()

    budget_friendly_tokens = (
        "sasta",
        "saste",
        "budget friendly",
        "budget-friendly",
        "value for money",
        "affordable",
        "cheap phone",
    )
    overpriced_tokens = (
        "overpriced",
        "over priced",
        "mehnga",
        "mahinga",
        "zyada price",
        "expensive",
    )
    great_tokens = ("great deal", "best deal", "cheap deal", "value deal")
    fair_tokens = (
        "fair price",
        "balanced",
        "theek price",
        "reasonable",
    )

    if any(token in lowered for token in ("not overpriced", "no overpriced", "without overpriced", "non overpriced")):
        return "Fair Price"
    if any(token in lowered for token in budget_friendly_tokens):
        return "Budget-Friendly"
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

    price_context_match = re.search(
        r"(?:rs\.?|pkr|rupees?|price|budget|under|below|within|less than|above|over|greater than|more than|at least|from)\s*(\d{4,6})",
        text,
    )
    if price_context_match:
        return int(price_context_match.group(1))

    numeric_match = re.search(r"(\d{4,6})\s*(?:rs\.?|pkr|rupees?)", text)
    if numeric_match:
        return int(numeric_match.group(1))

    return None


def _detect_brand(query: str) -> str | None:
    lowered = query.lower()

    for brand in BRANDS:
        if brand.lower() in lowered:
            return brand

    for brand, aliases in BRAND_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            return brand

    return None


def _detect_budget_mode(query: str) -> str:
    lowered = query.lower()

    min_budget_terms = (
        "above",
        "over",
        "greater than",
        "more than",
        "at least",
        "minimum",
        "starting from",
        "from",
    )
    max_budget_terms = (
        "under",
        "below",
        "less than",
        "within",
        "maximum",
        "upto",
        "up to",
    )

    if any(term in lowered for term in min_budget_terms):
        return "min"
    if any(term in lowered for term in max_budget_terms):
        return "max"
    return "max"


def regex_extract(query: str) -> Dict:
    budget = _extract_budget(query)

    ram_match = re.search(r"(\d{1,2})\s*gb\s*ram", query, flags=re.IGNORECASE)
    storage_match = re.search(r"(\d{2,4})\s*gb\s*(?:storage|rom)", query, flags=re.IGNORECASE)
    camera_match = re.search(r"(\d{2,3})\s*mp", query, flags=re.IGNORECASE)
    battery_match = re.search(r"(\d{4,5})\s*mah", query, flags=re.IGNORECASE)

    brand = _detect_brand(query)

    priority = "value"
    lowered = query.lower()
    camera_tokens = ("camera", "camra", "cam", "selfie", "photo")
    gaming_tokens = ("gaming", "game", "gamin", "pubg", "fps")
    performance_tokens = ("performance", "performnce", "speed", "fast", "chipset", "processor")
    business_tokens = ("business", "work", "office", "official")
    battery_tokens = ("battery", "battry", "backup", "back up")

    if any(token in lowered for token in camera_tokens):
        priority = "camera"
    elif any(token in lowered for token in gaming_tokens):
        priority = "gaming"
    elif any(token in lowered for token in performance_tokens):
        priority = "performance"
    elif any(token in lowered for token in business_tokens):
        priority = "business"
    elif any(token in lowered for token in battery_tokens):
        priority = "battery"

    intent_mode = _detect_intent_mode(query, brand)

    return {
        "budget_pkr": budget,
        "budget_mode": _detect_budget_mode(query),
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
    model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-haiku")

    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")

    system_prompt = (
        "You are an information extraction engine for a mobile phone recommender. "
        "Read the user text and output ONLY one valid JSON object with no markdown, no explanation, no extra keys. "
        "\n"
        "Schema (exact keys only): "
        "budget_pkr, budget_mode, ram_gb, storage_gb, camera_mp, battery_mah, brand, priority, intent_mode, deal_filter. "
        "\n"
        "Allowed values: "
        "priority in [value, camera, performance, gaming, business, battery]; "
        "intent_mode in [recommend, brand_list, all_list]; "
        "budget_mode in [min, max, null]; "
        "deal_filter in [Budget-Friendly, Great Deal, Fair Price, Overpriced, null]. "
        "\n"
        "Extraction rules: "
        "1) Use null for unknown/missing fields. "
        "2) budget_pkr must be an integer in PKR. Convert shorthand like 50k/50 K to 50000. "
        "3) If user says under/below/within/max/upto/up to => budget_mode=max. "
        "4) If user says above/over/from/at least/minimum/more than => budget_mode=min. "
        "5) If budget is missing, budget_mode should be null. "
        "6) Parse RAM/storage/camera/battery as integers only (e.g., 8GB -> 8, 108MP -> 108, 5000mAh -> 5000). "
        "7) brand should be a clean brand name if explicitly mentioned, otherwise null. "
        "8) intent_mode=brand_list when user asks to list/show/all phones of a specific brand. "
        "9) intent_mode=all_list when user asks to list/show/all phones without specifying a brand. "
        "10) Otherwise intent_mode=recommend. "
        "11) priority mapping hints: camera/photo/selfie -> camera; gaming/game -> gaming; performance/speed/fast/chipset -> performance; "
        "work/office/business -> business; battery/back-up/backup -> battery; else value. "
        "12) deal_filter mapping hints: cheap/affordable/budget friendly/value for money -> Budget-Friendly; "
        "great deal/best deal -> Great Deal; overpriced/expensive/mehnga -> Overpriced; fair/reasonable/theek price -> Fair Price. "
        "13) Understand Urdu and Roman Urdu phrasing. Common hints: sasta/sasti/affordable -> Budget-Friendly; mehnga/mahinga -> Overpriced; "
        "camera acha/zabardast camera -> camera priority; gaming ke liye/game k liye -> gaming priority; "
        "battery achi/backup acha/long battery -> battery priority; performance fast/chale smooth -> performance priority. "
        "14) Intent in Urdu/Roman Urdu: sab/sare/saare/list/dikhao/show all + brand => brand_list; "
        "sab phones/sare mobiles/all mobiles without brand => all_list; otherwise recommend. "
        "15) Budget in Urdu/Roman Urdu: andar/ke andar/tak/upto => budget_mode=max; upar/se zyada/kam az kam => budget_mode=min. "
        "16) Be robust to common typos and variant spellings (for example: sumsung/samung => Samsung, camra => camera, battry => battery, "
        "one plus => OnePlus, iphon => Apple). "
        "\n"
        "Output example format (values are examples only): "
        '{"budget_pkr":50000,"budget_mode":"max","ram_gb":8,"storage_gb":128,"camera_mp":50,"battery_mah":5000,"brand":"Samsung","priority":"camera","intent_mode":"recommend","deal_filter":null}'
    )

    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": 300,
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
    merged_budget_mode = regex_based.get("budget_mode") or parsed.get("budget_mode") or "max"
    merged_deal_filter = regex_based.get("deal_filter") or parsed.get("deal_filter")

    return {
        "budget_pkr": _pick_numeric("budget_pkr"),
        "budget_mode": merged_budget_mode,
        "ram_gb": _pick_numeric("ram_gb"),
        "storage_gb": _pick_numeric("storage_gb"),
        "camera_mp": _pick_numeric("camera_mp"),
        "battery_mah": _pick_numeric("battery_mah"),
        "brand": merged_brand,
        "priority": merged_priority,
        "intent_mode": _detect_intent_mode(query, merged_brand) or parsed.get("intent_mode") or "recommend",
        "requested_tier": _detect_requested_tier(query),
        "deal_filter": merged_deal_filter,
    }


def extract_specs(query: str) -> Tuple[Dict, str]:
    try:
        return openrouter_extract(query), "openrouter"
    except Exception:
        return regex_extract(query), "regex"
