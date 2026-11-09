# ADR 0004: AI through one gateway, always with a fallback

Status: accepted

- Every AI call from the API goes through `assist/gateway.ask`: feature switch, shared monthly budget (alert at
  80%), short timeout, usage and cost logged in `ai_usage`. Any failure returns `None`.
- Every feature has a non-AI answer: templates, bestsellers, rule-based search, FAQ, computed reorder lists.
- AI never decides money, stock, balances or order status. Numbers in AI text must appear in the facts given to
  it (`numbers_ok`, the WhatsApp validator); otherwise the AI text is thrown away.
- Claude is called only from `apps/ai-service` with the official Anthropic SDK; the model is set by
  `AI_MODEL_TEXT`.
- Recommendations, visual search, size help and forecasts use the shop's own data and simple statistics, not a
  paid model, to keep cost near zero.

Why: SRS 6.2 and test T32 — the shop must keep billing and selling when the AI provider is slow, down or over
budget, and a wrong amount in a customer message is worse than a plain message.

Consequence: features look plainer without AI but never break. Visual search is colour/pattern based; a deeper
image model can be added behind the same endpoint later.
