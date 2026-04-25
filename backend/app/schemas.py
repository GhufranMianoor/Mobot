from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ChatHistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    history: List[ChatHistoryItem] = Field(default_factory=list)


class PhoneRecommendation(BaseModel):
    name: str
    specs: str
    price_pkr: int
    source: str
    url: str


class ChatResponse(BaseModel):
    reply: str
    tier: str
    confidence: float
    nlp_source: Literal["openrouter", "regex"]
    intent_mode: Literal["recommend", "brand_list", "all_list"]
    knn_used: bool
    phones: List[PhoneRecommendation]


class HealthResponse(BaseModel):
    status: str
    openrouter_configured: bool
    cache_age_hours: float
    phones_indexed: int


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)


class SearchResultItem(BaseModel):
    name: str
    specs: str
    price_pkr: int
    source: str
    url: str
    actual_tier: str
    predicted_tier: str
    deal_badge: Literal["Great Deal", "Fair Price", "Overpriced"]


class SearchResponse(BaseModel):
    query: str
    summary: str
    tier_used: str
    predicted_tier: Optional[str] = None
    nlp_source: Literal["openrouter", "regex"]
    total_results: int
    results: List[SearchResultItem]
