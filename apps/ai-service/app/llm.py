"""One place that calls Claude. Returns (text, usage); text is None on any failure so callers fall back."""
import json
import logging
import os
import re

import anthropic

log = logging.getLogger("wearverse.ai.llm")
MODEL = os.getenv("AI_MODEL_TEXT", "claude-opus-5-5")
_client: anthropic.Anthropic | None = None


def client() -> anthropic.Anthropic | None:
    global _client
    key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("AI_API_KEY")
    if _client is None and key:
        _client = anthropic.Anthropic(api_key=key, max_retries=0)
    return _client


def complete(*, system: str, content, max_tokens: int = 1024, timeout: float = 2.5,
             effort: str = "low") -> tuple[str | None, dict]:
    c = client()
    if c is None:
        return None, {}
    try:
        response = c.with_options(timeout=timeout).beta.messages.create(
            model=MODEL, max_tokens=max_tokens, system=system,
            output_config={"effort": effort},
            betas=["server-side-fallback-2026-07-01"], extra_body={"fallbacks": "default"},
            messages=[{"role": "user", "content": content}],
        )
    except anthropic.APIStatusError as exc:
        log.warning("AI error %s", exc.status_code)
        return None, {}
    except (anthropic.APIConnectionError, anthropic.APITimeoutError):
        log.info("AI slow or unreachable")
        return None, {}
    usage = {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
    if response.stop_reason == "refusal":
        return None, usage
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    return (text or None), usage


def parse_json(text: str | None) -> dict | list | None:
    """Accept a bare JSON reply or one inside ```json fences."""
    if not text:
        return None
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    raw = match.group(1) if match else text
    start = min([i for i in (raw.find("{"), raw.find("[")) if i >= 0], default=-1)
    if start < 0:
        return None
    try:
        return json.loads(raw[start:])
    except json.JSONDecodeError:
        end = max(raw.rfind("}"), raw.rfind("]"))
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            return None
