from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

FEATURES = ["ram_gb", "storage_gb", "camera_mp", "battery_mah", "processor_tier"]
TIER_LABELS = {
    0: "Budget",
    1: "Mid-Range",
    2: "High-End",
    3: "Premium",
}


@dataclass
class PredictionResult:
    label: int
    tier: str
    confidence: float


class LightweightKNN:
    def __init__(self, data_path: Path | None = None, k: int = 5, rows: List[Dict] | None = None) -> None:
        self.data_path = data_path
        self.k = k
        if rows is not None:
            self.rows = rows
        else:
            if self.data_path is None:
                raise ValueError("Either data_path or rows must be provided")
            self.rows = self._load_data()
        self.feature_stats = self._feature_min_max()

    def _load_data(self) -> List[Dict]:
        with self.data_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload["samples"]

    def _feature_min_max(self) -> Dict[str, Tuple[float, float]]:
        stats: Dict[str, Tuple[float, float]] = {}
        for feature in FEATURES:
            values = [float(row[feature]) for row in self.rows]
            stats[feature] = (min(values), max(values))
        return stats

    def _normalize(self, feature: str, value: float) -> float:
        min_v, max_v = self.feature_stats[feature]
        if max_v == min_v:
            return 0.0
        return (value - min_v) / (max_v - min_v)

    def _vectorize(self, record: Dict) -> List[float]:
        return [self._normalize(feature, float(record.get(feature, 0))) for feature in FEATURES]

    def _distance(self, a: List[float], b: List[float]) -> float:
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def predict(self, query_features: Dict[str, float]) -> PredictionResult:
        query_vec = self._vectorize(query_features)
        distances: List[Tuple[float, int]] = []

        for row in self.rows:
            row_vec = self._vectorize(row)
            dist = self._distance(query_vec, row_vec)
            distances.append((dist, int(row["tier_label"])))

        distances.sort(key=lambda item: item[0])
        neighbors = distances[: self.k]
        votes = Counter(label for _, label in neighbors)

        winner, winner_count = votes.most_common(1)[0]
        confidence = winner_count / max(1, len(neighbors))

        return PredictionResult(
            label=winner,
            tier=TIER_LABELS.get(winner, "Mid-Range"),
            confidence=round(confidence, 2),
        )
