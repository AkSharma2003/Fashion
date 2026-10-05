"""Safety check for AI-written WhatsApp text (SRS FR-WAP-02).

The AI only writes the words. Every amount, date and name is a placeholder like {amount} that WE fill
from the database. If the AI text is not exactly right, return None and send the standard template.
"""
import re

PLACEHOLDER = re.compile(r"\{[a-z_]+\}")


def validate_and_fill(text: str, required: list[str], values: dict[str, str]) -> str | None:
    """required: placeholders that must appear, e.g. ['{amount}', '{new_balance}'].
    values: real values by name without braces, e.g. {'amount': 'Rs 1,499'}.
    Returns the final message, or None if the AI text is unsafe."""
    found = set(PLACEHOLDER.findall(text))
    if found != set(required):
        return None  # missing or unknown placeholder
    if re.search(r"\d", PLACEHOLDER.sub("", text)):
        return None  # the model wrote its own number
    final = text
    for placeholder in found:
        name = placeholder.strip("{}")
        if name not in values:
            return None
        final = final.replace(placeholder, values[name])
    return final
