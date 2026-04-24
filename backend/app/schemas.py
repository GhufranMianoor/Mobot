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
    nlp_source: Literal["groq", "regex"]
    phones: List[PhoneRecommendation]


class HealthResponse(BaseModel):
    status: str
    groq_configured: bool
    cache_age_hours: float
    phones_indexed: int
