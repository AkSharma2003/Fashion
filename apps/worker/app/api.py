import os

import httpx

API_URL = os.getenv("API_INTERNAL_URL", "http://localhost:8000/api/v1/internal").rstrip("/")
KEY = os.getenv("INTERNAL_API_KEY", "")


def call(path: str, timeout: float = 120) -> dict:
    response = httpx.post(f"{API_URL}/{path.lstrip('/')}", headers={"X-Internal-Key": KEY}, timeout=timeout)
    response.raise_for_status()
    return response.json()
