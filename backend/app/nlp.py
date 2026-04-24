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
    elif "gaming" in lowered or "performance" in lowered:
        priority = "performance"
    elif "battery" in lowered:
        priority = "battery"

    return {
        "budget_pkr": budget,
        "ram_gb": int(ram_match.group(1)) if ram_match else None,
        "storage_gb": int(storage_match.group(1)) if storage_match else None,
        "camera_mp": int(camera_match.group(1)) if camera_match else None,
        "battery_mah": int(battery_match.group(1)) if battery_match else None,
        "brand": brand,
        "priority": priority,
    }


def groq_extract(query: str) -> Dict:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    system_prompt = (
        "Extract mobile phone preferences from user text and return strict JSON with keys: "
        "budget_pkr, ram_gb, storage_gb, camera_mp, battery_mah, brand, priority. "
        "Use null when unknown. priority should be one of: value, camera, performance, battery."
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
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError("Groq call failed") from exc

    content = body["choices"][0]["message"]["content"]
    parsed = json.loads(content)

    return {
        "budget_pkr": parsed.get("budget_pkr"),
        "ram_gb": parsed.get("ram_gb"),
        "storage_gb": parsed.get("storage_gb"),
        "camera_mp": parsed.get("camera_mp"),
        "battery_mah": parsed.get("battery_mah"),
        "brand": parsed.get("brand"),
        "priority": parsed.get("priority") or "value",
    }


def extract_specs(query: str) -> Tuple[Dict, str]:
    try:
        return groq_extract(query), "groq"
    except Exception:
        return regex_extract(query), "regex"
