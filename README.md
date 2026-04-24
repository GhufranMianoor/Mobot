# Mobot

AI-Driven Mobile Phone Price Tier Classifier and Recommender (Chatbot Edition)

Version: v2.0 (Lightweight)
Date: April 2026
Status: Draft - Updated (Gemini Removed)

## 1. Project Overview

### 1.1 Summary
Mobot is a lightweight conversational web app that helps Pakistani users find high-value mobile phones within budget. Users ask in plain English or Urdu-English mixed language, and the system:

1. extracts preferences from text,
2. predicts a price tier with a lightweight k-NN model,
3. returns top 3 phone recommendations from cached Pakistani market data.

### 1.2 Problem Statement
Pakistani buyers struggle with:

- too many device options,
- inconsistent prices across websites,
- no intelligent conversational shortlist.

### 1.3 Solution
A single chatbot UI backed by FastAPI:

- OpenRouter-hosted Llama models are the primary extraction layer.
- Regex parser is the fallback if OpenRouter fails or is unavailable.
- A lightweight, in-project k-NN implementation predicts budget tier.
- Cached JSON phone data is filtered and ranked to return top options.

## 2. Goals and Non-Goals

### 2.1 Goals
- Deliver a working chatbot UI (HTML/CSS/Vanilla JS).
- Build a FastAPI backend with `POST /chat` and `GET /health`.
- Keep dependencies minimal and startup fast.
- Support Urdu-English mixed budget and spec queries.
- Return ranked top-3 phones with links.

### 2.2 Non-Goals
- No authentication.
- No on-demand scraping during user request.
- No checkout/payment flow.
- No native mobile app.
- No tablets/accessories.

## 3. Lightweight Architecture

### 3.1 Tech Stack
- Frontend: HTML5, CSS3, Vanilla JS
- Backend: Python 3.11+, FastAPI, Uvicorn
- NLP: OpenRouter API (primary), Regex fallback
- Classifier: Custom in-memory k-NN (no heavy ML runtime required)
- Data Store: JSON files (`phones.json`, `training_data.json`)

### 3.2 Request Pipeline
1. User submits message from chat UI.
2. Frontend sends `POST /chat`.
3. Backend extracts specs via OpenRouter.
4. If OpenRouter fails/times out, backend uses regex parser.
5. k-NN predicts tier.
6. Recommender filters + ranks cached phones.
7. API returns top 3 results and metadata.

### 3.3 NLP Fallback Logic
```python
try:
		specs = openrouter_extract(query)
		nlp_source = "openrouter"
except Exception:
		specs = regex_extract(query)
		nlp_source = "regex"
```

## 4. Feature Specifications

### 4.1 Spec Extraction Output
Target schema:

```json
{
	"budget_pkr": 50000,
	"ram_gb": 8,
	"storage_gb": null,
	"camera_mp": null,
	"battery_mah": null,
	"brand": null,
	"priority": "camera"
}
```

### 4.2 Price Tier Classifier
Tiers:

- Budget: < 30,000
- Mid-Range: 30,000 to 70,000
- High-End: 70,000 to 150,000
- Premium: > 150,000

Features used:

- `ram_gb`
- `storage_gb`
- `camera_mp`
- `battery_mah`
- `processor_tier` (0 to 2)

Classifier:

- k-NN (k=5 by default)
- Euclidean distance on normalized features
- Confidence = vote share of winning class

### 4.3 Ranking Formula

```text
value_score = (ram_score + camera_score + battery_score) / normalized_price
```

Top 3 by `value_score` are returned.

### 4.4 Chat UI
- Conversational bubbles
- Typing indicator
- Result cards with tier badge and confidence
- Quick-reply chips
- Responsive desktop/mobile layout
- `nlp_source` shown in result card

## 5. Data Strategy

### 5.1 Sources
- HamariWeb
- WhatMobile
- MegaPK

### 5.2 Storage
- Cached in `backend/data/phones.json`
- Deduped by model name
- Lowest known price retained

### 5.3 Fields
Each phone record contains:

- `name`, `brand`, `ram_gb`, `storage_gb`, `camera_mp`, `battery_mah`,
- `processor_tier`, `price_pkr`, `source`, `url`, `scraped_at`

## 6. API Specification

### 6.1 POST /chat
Request:

```json
{
	"message": "Samsung ke alaawa koi acha phone 8GB RAM 50k ke andar",
	"history": []
}
```

Response:

```json
{
	"reply": "Top Mid-Range options near your needs:",
	"tier": "Mid-Range",
	"confidence": 0.8,
	"nlp_source": "openrouter",
	"phones": [
		{
			"name": "Phone Name",
			"specs": "8GB | 128GB | 50MP | 5000mAh",
			"price_pkr": 49999,
			"source": "WhatMobile",
			"url": "https://example.com"
		}
	]
}
```

### 6.2 GET /health
Response:

```json
{
	"status": "ok",
	"openrouter_configured": false,
	"cache_age_hours": 1.2,
	"phones_indexed": 120
}
```

## 7. Non-Functional Targets
- P95 response latency: < 2 seconds (local cached data)
- Cold start: < 3 seconds on dev machine
- Minimal dependencies, no heavy framework stack
- Browser support: latest Chrome/Firefox/Safari

## 8. Milestones
1. Train and validate lightweight k-NN dataset.
2. Prepare cached phone dataset.
3. Build FastAPI `/chat` and `/health`.
4. Build frontend chatbot.
5. End-to-end integration and demo testing.

## 9. Risks and Mitigations
- OpenRouter unavailable: regex fallback keeps system functional.
- Stale scrape data: serve last successful cache.
- Lower classifier quality: tune `k`, improve normalization and training examples.

## 10. Project Structure (Current)

```text
Mobot/
	README.md
	backend/
		app/
		data/
		requirements.txt
	frontend/
		index.html
		styles.css
		app.js
```

## 11. Quick Start

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
python -m http.server 5500
```

Open `http://localhost:5500`.

Set optional OpenRouter key for smarter extraction:

```bash
export OPENROUTER_API_KEY="your_key_here"
```

## 12. Data Refresh (Step 1)

Run cache updater script:

```bash
cd backend
python scripts/scrape_and_update_cache.py
```

Daily scheduler example is provided in:

`backend/scripts/cron_daily_cache_update.example`

## 13. k-NN Evaluation (Step 2)

Run evaluation (80/20 split, best-k search, confusion matrix, report):

```bash
cd backend
PYTHONPATH=. python scripts/evaluate_knn.py
```

## 14. k-NN Model Check File

Run sanity checks with predefined feature cases:

```bash
cd backend
PYTHONPATH=. python scripts/check_knn_model.py
```

## 15. Scraped Training CSV

Generate a larger CSV dataset from WhatMobile for model training:

```bash
cd backend
PYTHONPATH=. python scripts/scrape_whatmobile_to_training_csv.py
```

Output file:

`backend/data/training_mobile_specs.csv`

## 16. External Dataset + Merge

Added external market dataset file:

`backend/data/amazon_market_dataset.csv`

Generate merged clean training set (existing scrape + external):

```bash
cd backend
PYTHONPATH=. python scripts/merge_training_sources.py
```

Merged output:

`backend/data/training_merged_clean.csv`