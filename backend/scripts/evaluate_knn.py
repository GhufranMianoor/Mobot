from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List, Tuple

from app.classifier import FEATURES, TIER_LABELS, LightweightKNN

BASE_DIR = Path(__file__).resolve().parent.parent
TRAINING_PATH = BASE_DIR / "data" / "training_data.json"


def load_samples() -> List[Dict]:
    with TRAINING_PATH.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload["samples"]


def split_data(samples: List[Dict], test_ratio: float = 0.2, seed: int = 42) -> Tuple[List[Dict], List[Dict]]:
    rows = samples[:]
    rng = random.Random(seed)
    rng.shuffle(rows)

    test_count = max(1, int(len(rows) * test_ratio))
    test_rows = rows[:test_count]
    train_rows = rows[test_count:]
    return train_rows, test_rows


def predict_label(knn: LightweightKNN, row: Dict) -> int:
    features = {feature: float(row[feature]) for feature in FEATURES}
    result = knn.predict(features)
    return result.label


def accuracy(y_true: List[int], y_pred: List[int]) -> float:
    if not y_true:
        return 0.0
    correct = sum(1 for a, b in zip(y_true, y_pred) if a == b)
    return correct / len(y_true)


def confusion_matrix(y_true: List[int], y_pred: List[int], labels: List[int]) -> List[List[int]]:
    index = {label: i for i, label in enumerate(labels)}
    matrix = [[0 for _ in labels] for _ in labels]

    for actual, predicted in zip(y_true, y_pred):
        matrix[index[actual]][index[predicted]] += 1

    return matrix


def classification_report(y_true: List[int], y_pred: List[int], labels: List[int]) -> str:
    lines = ["label\tprecision\trecall\tf1\tsupport"]

    for label in labels:
        tp = sum(1 for a, p in zip(y_true, y_pred) if a == label and p == label)
        fp = sum(1 for a, p in zip(y_true, y_pred) if a != label and p == label)
        fn = sum(1 for a, p in zip(y_true, y_pred) if a == label and p != label)
        support = sum(1 for a in y_true if a == label)

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

        lines.append(
            f"{TIER_LABELS[label]}\t{precision:.2f}\t\t{recall:.2f}\t{f1:.2f}\t{support}"
        )

    return "\n".join(lines)


def find_best_k(train_rows: List[Dict], test_rows: List[Dict]) -> Tuple[int, float]:
    k_values = [k for k in range(1, 12, 2) if k <= len(train_rows)]
    best_k = k_values[0]
    best_score = -1.0

    for k in k_values:
        knn = LightweightKNN(rows=train_rows, k=k)
        y_true = [int(r["tier_label"]) for r in test_rows]
        y_pred = [predict_label(knn, r) for r in test_rows]
        score = accuracy(y_true, y_pred)

        if score > best_score:
            best_score = score
            best_k = k

    return best_k, best_score


def main() -> None:
    samples = load_samples()
    train_rows, test_rows = split_data(samples)

    best_k, best_score = find_best_k(train_rows, test_rows)
    knn = LightweightKNN(rows=train_rows, k=best_k)

    y_true = [int(r["tier_label"]) for r in test_rows]
    y_pred = [predict_label(knn, r) for r in test_rows]

    labels = sorted(TIER_LABELS.keys())
    matrix = confusion_matrix(y_true, y_pred, labels)

    print(f"Train size: {len(train_rows)}")
    print(f"Test size: {len(test_rows)}")
    print(f"Best k: {best_k}")
    print(f"Accuracy: {best_score:.2%}")
    print("\nConfusion Matrix (rows=actual, cols=predicted):")

    header = "\t" + "\t".join(TIER_LABELS[l] for l in labels)
    print(header)
    for label, row in zip(labels, matrix):
        print(f"{TIER_LABELS[label]}\t" + "\t".join(str(v) for v in row))

    print("\nClassification Report:")
    print(classification_report(y_true, y_pred, labels))


if __name__ == "__main__":
    main()
