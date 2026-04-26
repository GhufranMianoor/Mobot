from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PHONES_JSON = DATA_DIR / "phones.json"
TRAINING_CSV = DATA_DIR / "training_mobile_specs.csv"
MERGED_CSV = DATA_DIR / "training_merged_clean.csv"


def _is_unreal_model(name: str, brand: str) -> bool:
    n = (name or "").strip().lower()

    # iPhone sanity: keep modern generations only for this dataset window.
    if "iphone" in n:
        m = re.search(r"iphone\s+(\d{1,3})", n)
        if not m:
            return True
        generation = int(m.group(1))
        if generation < 11 or generation > 17:
            return True

    # Common synthetic high-number patterns observed in this dataset.
    for m in re.finditer(r"\b([a-z]+)\s*(\d{2,3})\b", n):
        series = m.group(1)
        num = int(m.group(2))

        if series in {
            "vision",
            "zero",
            "note",
            "edge",
            "hot",
            "x",
            "pop",
            "phantom",
            "spark",
            "reno",
            "smart",
            "magic",
            "camon",
            "nova",
            "mate",
            "nord",
            "narzo",
        } and num >= 25:
            return True

        if series in {"a", "f", "m", "s", "v", "y", "t"} and "galaxy" in n and num >= 26:
            return True

    if re.search(r"\b(find\s*x\s*2[5-9]|find\s*x\s*[3-9]\d)\b", n):
        return True

    return False


def _clean_json_phones() -> tuple[int, int]:
    payload = json.loads(PHONES_JSON.read_text(encoding="utf-8"))
    phones = payload.get("phones", [])

    cleaned = [p for p in phones if not _is_unreal_model(str(p.get("name") or ""), str(p.get("brand") or ""))]

    payload["phones"] = cleaned
    payload["record_count"] = len(cleaned)
    PHONES_JSON.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return len(phones), len(cleaned)


def _clean_csv(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0

    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return 0, 0

    fieldnames = list(rows[0].keys())
    cleaned = [
        r
        for r in rows
        if not _is_unreal_model(str(r.get("name") or ""), str(r.get("brand") or ""))
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned)

    return len(rows), len(cleaned)


def run() -> None:
    p_before, p_after = _clean_json_phones()
    t_before, t_after = _clean_csv(TRAINING_CSV)
    m_before, m_after = _clean_csv(MERGED_CSV)

    print(f"phones.json: {p_before} -> {p_after} (removed {p_before - p_after})")
    print(f"training_mobile_specs.csv: {t_before} -> {t_after} (removed {t_before - t_after})")
    print(f"training_merged_clean.csv: {m_before} -> {m_after} (removed {m_before - m_after})")


if __name__ == "__main__":
    run()
