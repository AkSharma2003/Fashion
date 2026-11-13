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
    "banarasi": "banarasi", "kanjivaram": "kanjivaram", "kanjeevaram": "kanjivaram", "kanchipuram": "kanjivaram",
    "teal": "teal", "wine": "wine", "peach": "peach", "lavender": "lavender", "mustard": "mustard", "navy": "navy",
    "mint": "mint", "rust": "rust", "magenta": "magenta", "rani": "pink", "gold": "golden", "grey": "grey", "gray": "grey",
    "frock": "frock", "sherwani": "sherwani", "dhoti": "dhoti", "petticoat": "petticoat", "sharara": "sharara",
    "patiala": "patiala", "chikankari": "chikankari", "bandhani": "bandhani", "bandhej": "bandhani",
    "ladki": "girls", "girl": "girls", "girls": "girls", "ladka": "boys", "boy": "boys", "boys": "boys", "wedding": "wedding", "shaadi": "wedding", "shadi": "wedding",
    "party": "party", "festive": "festive", "tyohar": "festive", "daily": "daily", "office": "office", "casual": "casual",
}
COLOURS = {"red", "maroon", "blue", "green", "yellow", "pink", "black", "white", "orange", "purple", "golden", "silver", "cream",
           "beige", "teal", "wine", "peach", "lavender", "mustard", "navy", "mint", "rust", "magenta", "grey"}
STOP = {"a", "an", "the", "for", "and", "or", "with", "in", "of", "to", "me", "show", "i", "want", "need", "ke", "ka", "ki",
        "liye", "chahiye", "dikhao", "under", "below", "above", "less", "than", "rs", "inr", "rupees", "ka", "wala", "wali", "se", "kam",
        # Hinglish question and filler words that are not about the product itself
        "andar", "tak", "niche", "neeche", "upar", "hai", "hain", "kya", "koi", "ho", "mujhe", "hume", "humko", "do", "dena",
        "batao", "bataiye", "price", "rate", "cost", "kitne", "kitna", "kitni", "available", "milega", "milegi", "please",
        "pls", "you", "have", "any", "is", "are", "there", "what", "which", "can", "get", "buy", "your", "my", "mera",
        "meri", "also", "bhi", "aur", "ya", "per", "par", "budget", "max", "only", "sirf", "wale", "waale", "ji",
        "size", "sizes", "colour", "colours", "color", "colors", "rang", "design", "designs", "new", "naya", "nayi", "latest"}


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
