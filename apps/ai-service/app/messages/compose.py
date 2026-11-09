"""AI-0: WhatsApp bill / reminder wording (SRS 6.1-6.3).

The model only writes words around placeholders like {amount}. It never sees real
amounts, balances, phone numbers or full names. The main API fills the placeholders
and rejects the text if any other number appears, so a bad answer only costs a template.
"""
import logging
import os
import re

import anthropic

log = logging.getLogger("wearverse.ai.compose")

MODEL = os.getenv("AI_MODEL_TEXT", "claude-opus-5-5")
TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "2.5"))  # API waits 3s; answer before that
PLACEHOLDER = re.compile(r"\{[a-z_]+\}")

SYSTEM = """You write short WhatsApp messages for WearVerse, an Indian fashion shop, to its own customers.
Rules:
- Use every placeholder you are given exactly once, written exactly as given (for example {amount}).
- Never write any digit or number yourself; amounts, dates and bill numbers come only from placeholders.
- Do not invent offers, dates, penalties or facts. Do not add links other than {pay_link}.
- One or two sentences, warm and respectful, no emojis, no hashtags.
- Reply with the message text only."""

LANGUAGE_HINT = {
    "hinglish": "Write in Hinglish (Hindi words in Roman script), like 'Namaste {first_name} ji'.",
    "hindi": "Write in Hindi using Devanagari script.",
    "english": "Write in simple Indian English.",
}

PURPOSE_HINT = {
    "khata_bill": "Tell the customer a credit (khata) bill was made, show previous and new balance, and offer the pay-from-home link.",
    "payment_receipt": "Thank the customer for the payment and show the remaining balance.",
    "reminder": "Gently remind the customer of the pending balance and offer the payment link. Never sound threatening.",
    "fall_pico_ready": "Tell the customer the fall-pico work on their saree is ready for pickup.",
    "order_confirmed": "Confirm the online order.",
    "return_credit": "Tell the customer the return amount was credited to their khata and show the new balance.",
}

_client: anthropic.Anthropic | None = None


def client() -> anthropic.Anthropic | None:
    global _client
    if _client is None and (os.getenv("ANTHROPIC_API_KEY") or os.getenv("AI_API_KEY")):
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY") or os.getenv("AI_API_KEY"),
                                      timeout=TIMEOUT_SECONDS, max_retries=0)
    return _client


def is_safe(text: str, placeholders: list[str]) -> bool:
    found = PLACEHOLDER.findall(text)
    if sorted(set(found)) != sorted(set(placeholders)):
        return False
    return not re.search(r"\d", PLACEHOLDER.sub("", text))


def compose(purpose: str, language: str, tone: str, placeholders: list[str]) -> tuple[str | None, str, dict]:
    """Returns (text, source). source is 'ai' or 'fallback' (caller sends its template)."""
    c = client()
    if c is None or purpose not in PURPOSE_HINT:
        return None, "fallback", {}
    prompt = (f"{PURPOSE_HINT[purpose]} {LANGUAGE_HINT.get(language, LANGUAGE_HINT['hinglish'])} "
              f"Tone: {tone}. Placeholders to use: {' '.join(placeholders)}")
    try:
        response = c.beta.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM,
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            extra_body={"fallbacks": "default"},
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.RateLimitError:
        log.warning("AI rate limited; template used")
        return None, "fallback", {}
    except anthropic.APIStatusError as exc:
        log.warning("AI error %s; template used", exc.status_code)
        return None, "fallback", {}
    except (anthropic.APIConnectionError, anthropic.APITimeoutError):
        log.info("AI slow or unreachable; template used")
        return None, "fallback", {}
    usage = {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
    if response.stop_reason == "refusal":
        return None, "fallback", usage
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if not text or not is_safe(text, placeholders):
        return None, "fallback", usage
    return text, "ai", usage
