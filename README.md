# Mobot

AI-Driven Mobile Phone Price Tier Classifier and Recommender

Version: v2.0 (Lightweight)
Date: April 2026
Status: Draft - Updated

## 1. Project Overview

### 1.1 Summary
Mobot is a lightweight web app (conversational-style UI optional) that helps Pakistani users find high-value mobile phones within budget. Users ask in plain English or Urdu-English mixed language, and the system:

1. extracts preferences from text,
2. predicts a price tier with a lightweight k-NN model,
3. returns ranked phone recommendations from cached Pakistani market data.

### 1.2 Problem Statement
Pakistani buyers struggle with:

- too many device options,
- inconsistent prices across websites,
- no intelligent conversational shortlist.

### 1.3 Solution
A web UI backed by FastAPI (conversational-style interface optional):

- NLP extractor is configurable; an external LLM provider may be used but is not required. A built-in regex extractor is included as a fallback.
- A lightweight, in-project k-NN implementation predicts price tiers.
- Cached JSON phone data is filtered and ranked to return recommended options.

## 2. Goals and Non-Goals

### 2.1 Goals
-- Deliver a working web UI (HTML/CSS/Vanilla JS). The interface supports conversational-style interactions but the system is API-driven.
-- Build a FastAPI backend with `POST /chat` and `GET /health`.
- Keep dependencies minimal and startup fast.
- Support Urdu-English mixed budget and spec queries.
- Return ranked top-3 phones with links.
-- Deliver a working web UI (HTML/CSS/Vanilla JS). The interface is search-engine style (search box, autocomplete, filters) and the system is API-driven.

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
-- NLP: Configurable extractor (external LLM optional), Regex fallback
- Classifier: Custom in-memory k-NN (no heavy ML runtime required)
- Data Store: JSON files (`phones.json`, `training_data.json`)

### 3.2 Request Pipeline
1. User submits message from the frontend UI.
2. Frontend sends `POST /chat` (or other API endpoint as configured).
3. Backend extracts specs using the configured NLP extractor (external provider optional) or the built-in regex parser.
4. k-NN predicts tier.
5. Recommender filters + ranks cached phones.
6. API returns ranked results and metadata.

### 3.3 NLP Fallback Logic
```python
try:
    specs = external_nlp_extract(query)  # optional external provider
    nlp_source = "external"
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
- `nlp_source` shown in result card when available
### 4.4 Frontend UI
- Search box with optional autocomplete and quick filters
- Result list with cards showing tier badge, confidence, price, and source
- Sorting and filtering controls (budget, brand, deal filters)
- Responsive desktop/mobile layout
- `nlp_source` shown in result card when available

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
	"nlp_source": "gemini",
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
	"gemini_configured": false,
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
- Gemini unavailable: regex fallback keeps system functional.
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

Set your Gemini key for smarter extraction:

```bash
export GEMINI_API_KEY="your_key_here"
```

## 12. Data Refresh & Notes

This repository has been cleaned to keep only runtime artifacts. The app requires the following data files in `backend/data`:

- `training_data.json` — pre-built training samples used by the in-project classifier
- `phones.json` — cached, deduped market data used by the recommender

Several auxiliary CSVs and ad-hoc scripts that were previously used to build the training dataset have been removed to declutter the repo. If you need to recreate or extend the training set, the helper scripts used previously are archived outside this repo (contact the maintainer) or you can rebuild by collecting source CSVs and producing `training_data.json`.

To update the cached phone dataset in a deployed system, run your own scraper or update process and replace `backend/data/phones.json`. The API exposes diagnostics and a k-NN sanity endpoint (`GET /knn/diagnostics`) which can be used to validate the classifier behavior.

## 13. Deployment (unchanged)

Recommended path: one Docker web service that serves both the frontend and backend.

### Local Docker test

```bash
docker build -t mobot .
docker run --rm -p 8000:8000 -e GEMINI_API_KEY="your_key_here" mobot
```

Open `http://localhost:8000`.

### Render

1. Push the repo to GitHub.
2. Create a new Render Web Service from the repo.
3. Render will read [render.yaml](render.yaml) and build the Docker image.
4. Set `GEMINI_API_KEY` in Render environment variables.
5. Deploy and open the service URL.
6. Optionally set `GEMINI_MODEL` (for example, `gemini-2.0-flash-lite`) in Render environment variables.

Notes:

- The frontend is served from the same app, so no separate static site is needed.
- `GEMINI_API_KEY` is required for Gemini-based extraction; without it, the regex fallback is used.
- If you use another platform, the Dockerfile can be reused as-is.

## 14. Model evaluation & diagnostics

The repository exposes runtime diagnostics via the API. Useful endpoints:

- `GET /knn/diagnostics` — small sanity checks and class distribution

For offline evaluation, the previous helper scripts were removed; you can perform evaluation programmatically by importing `app.classifier.LightweightKNN` and writing a short evaluation script (for example, perform an 80/20 split on `training_data.json` and compute accuracy/confusion matrix). The codebase still contains a lightweight evaluation flow within `backend/app/classifier.py` utilities such as `select_best_k()`.