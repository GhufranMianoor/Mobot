from __future__ import annotations

from pathlib import Path

from app.classifier import LightweightKNN

BASE_DIR = Path(__file__).resolve().parent.parent
TRAINING_PATH = BASE_DIR / "data" / "training_data.json"


def main() -> None:
    knn = LightweightKNN(data_path=TRAINING_PATH, k=5)

    test_cases = [
        {
            "name": "Budget user",
            "features": {
                "ram_gb": 4,
                "storage_gb": 64,
                "camera_mp": 13,
                "battery_mah": 5000,
                "processor_tier": 0,
            },
        },
        {
            "name": "Mid-range camera",
            "features": {
                "ram_gb": 8,
                "storage_gb": 128,
                "camera_mp": 64,
                "battery_mah": 5000,
                "processor_tier": 1,
            },
        },
        {
            "name": "High-end performer",
            "features": {
                "ram_gb": 12,
                "storage_gb": 256,
                "camera_mp": 50,
                "battery_mah": 5000,
                "processor_tier": 2,
            },
        },
        {
            "name": "Premium flagship",
            "features": {
                "ram_gb": 16,
                "storage_gb": 512,
                "camera_mp": 200,
                "battery_mah": 5000,
                "processor_tier": 2,
            },
        },
    ]

    print("k-NN sanity check")
    print("=" * 50)

    for case in test_cases:
        result = knn.predict(case["features"])
        print(
            f"{case['name']}: {result.tier} "
            f"(label={result.label}, confidence={result.confidence:.2f})"
        )


if __name__ == "__main__":
    main()
