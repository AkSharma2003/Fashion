"""WearVerse AI service (SRS 6). The main API calls it with short timeouts and always has a fallback.

It never receives full phone numbers, addresses, salary, balances or payment data. Data-driven features
(recommendations, forecasts, visual search) run inside the main API on its own data; this service does the
language work. Every reply carries `source` ("ai" or "fallback") and `usage` for the monthly cost cap.
"""
import os

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app import features
from app.llm import MODEL
from app.messages.compose import compose

app = FastAPI(title="WearVerse AI service")


def enabled(name: str) -> bool:
    return os.getenv(f"AI_FEATURE_{name.upper()}", "on") != "off"


class ComposeIn(BaseModel):
    purpose: str = Field(max_length=32)
    language: str = Field(default="hinglish", pattern="^(english|hindi|hinglish)$")
    tone: str = Field(default="polite", max_length=16)
    first_name: str = Field(default="{first_name}", max_length=40)
    placeholders: list[str] = Field(max_length=12)


class ChatIn(BaseModel):
    question: str = Field(max_length=1000)
    language: str = "english"
    history: list[dict] = Field(default_factory=list, max_length=12)
    context: dict = Field(default_factory=dict)


class SearchIn(BaseModel):
    query: str = Field(max_length=200)


class DescribeIn(BaseModel):
    facts: dict
    notes: str = Field(default="", max_length=500)
    language: str = "english"


class PosterIn(BaseModel):
    brief: str = Field(max_length=300)
    language: str = "english"


class BuyingIn(BaseModel):
    facts: dict


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": MODEL, "key_configured": bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("AI_API_KEY"))}


@app.post("/ai/message/compose")
def message_compose(payload: ComposeIn) -> dict:
    if not enabled("message"):
        return {"text": None, "source": "fallback"}
    text, source, usage = compose(payload.purpose, payload.language, payload.tone, payload.placeholders)
    return {"text": text, "source": source, "usage": usage}


@app.post("/ai/chat")
def chat(payload: ChatIn) -> dict:
    if not enabled("chat"):
        return {"text": None, "source": "fallback"}
    data, usage = features.chat(payload.question, payload.language, payload.history, payload.context)
    return {**data, "usage": usage}


@app.post("/ai/search/parse")
def search_parse(payload: SearchIn) -> dict:
    data, usage = features.parse_search(payload.query)
    return {**data, "usage": usage}


@app.post("/ai/describe")
def describe(payload: DescribeIn) -> dict:
    data, usage = features.describe(payload.facts, payload.notes, payload.language)
    return {**data, "usage": usage}


@app.post("/ai/poster/copy")
def poster_copy(payload: PosterIn) -> dict:
    data, usage = features.poster_copy(payload.brief, payload.language)
    return {**data, "usage": usage}


@app.post("/ai/buying/summary")
def buying_summary(payload: BuyingIn) -> dict:
    data, usage = features.buying_summary(payload.facts)
    return {**data, "usage": usage}
