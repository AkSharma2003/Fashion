"""Text helpers for search and similarity. Understands common Hindi / Hinglish shop words."""
import re

SYNONYMS = {
    # categories
    "saree": "saree", "sarees": "saree", "sari": "saree", "saris": "saree", "saadi": "saree", "sadi": "saree", "saari": "saree", "साड़ी": "saree",
    "suit": "suit", "suits": "suit", "salwar": "suit", "kameez": "suit", "anarkali": "anarkali", "सूट": "suit",
    "kurti": "kurti", "kurtis": "kurti", "kurta": "kurta", "kurtas": "kurta", "lehenga": "lehenga", "lehnga": "lehenga",
    "dupatta": "dupatta", "chunni": "dupatta", "blouse": "blouse", "kids": "kids", "bachcha": "kids", "baccha": "kids", "child": "kids", "children": "kids",
    # colours
    "red": "red", "lal": "red", "laal": "red", "maroon": "maroon", "blue": "blue", "neela": "blue", "nila": "blue",
    "green": "green", "hara": "green", "yellow": "yellow", "peela": "yellow", "pila": "yellow", "pink": "pink", "gulabi": "pink",
    "black": "black", "kala": "black", "kaala": "black", "white": "white", "safed": "white", "orange": "orange", "kesari": "orange",
    "purple": "purple", "baingani": "purple", "golden": "golden", "sunehra": "golden", "silver": "silver", "cream": "cream", "beige": "beige",
    # fabrics and occasions
    "silk": "silk", "resham": "silk", "cotton": "cotton", "suti": "cotton", "georgette": "georgette", "chiffon": "chiffon",
    "banarasi": "banarasi", "kanjivaram": "kanjivaram", "wedding": "wedding", "shaadi": "wedding", "shadi": "wedding",
    "party": "party", "festive": "festive", "tyohar": "festive", "daily": "daily", "office": "office", "casual": "casual",
}
COLOURS = {"red", "maroon", "blue", "green", "yellow", "pink", "black", "white", "orange", "purple", "golden", "silver", "cream", "beige"}
STOP = {"a", "an", "the", "for", "and", "or", "with", "in", "of", "to", "me", "show", "i", "want", "need", "ke", "ka", "ki",
        "liye", "chahiye", "dikhao", "under", "below", "above", "less", "than", "rs", "inr", "rupees", "ka", "wala", "wali", "se", "kam"}


def tokenize(text: str | None) -> list[str]:
    words = re.findall(r"[a-zA-Zऀ-ॿ]+", (text or "").lower())
    out = []
    for w in words:
        w = SYNONYMS.get(w, w)
        if w not in STOP and len(w) > 1:
            out.append(w)
    return out


def jaccard(a: list[str] | set[str], b: list[str] | set[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)
