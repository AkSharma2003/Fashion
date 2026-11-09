"""Description writer (AI-5) and banner / poster maker (AI-6).

Staff always review the text before publishing. Poster text is exactly what staff typed: the template
engine draws it; the model only suggests words, never draws text into an image.
"""
from html import escape
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.app_settings import get_setting
from app.core.errors import not_found
from app.modules.assist import gateway
from app.modules.assist.text import tokenize
from app.modules.catalog.image_storage import get_product_image_url
from app.modules.catalog.models import Product, ProductImage
from app.modules.inventory.models import ProductVariant


def product_facts(db: Session, product: Product) -> dict:
    variants = db.scalars(select(ProductVariant).where(ProductVariant.product_id == product.id, ProductVariant.is_active.is_(True))).all()
    image = db.scalar(select(ProductImage).where(ProductImage.product_id == product.id).order_by(ProductImage.created_at))
    return {"name": product.name, "category": product.category, "current_description": product.description or "",
            "colours": sorted({v.color for v in variants if v.color}), "sizes": sorted({v.size for v in variants if v.size}),
            "fall_pico": product.fall_pico_eligible,
            "image_url": get_product_image_url(image.object_key) if image else None}


def describe(db: Session, product_id: UUID, notes: str | None, language: str = "english") -> dict:
    product = db.get(Product, product_id)
    if product is None:
        raise not_found("Product")
    facts = product_facts(db, product)
    ai = gateway.ask(db, "describe", "/ai/describe", {"facts": facts, "notes": notes or "", "language": language}, timeout=30)
    if ai and isinstance(ai.get("title"), str) and isinstance(ai.get("description"), str):
        tags = [t for t in ai.get("tags") or [] if isinstance(t, str)][:12]
        return {"title": ai["title"][:200], "description": ai["description"][:2000], "tags": tags, "source": "ai"}
    words = [w for w in tokenize(f"{product.name} {notes or ''}") if len(w) > 2]
    colours = ", ".join(facts["colours"]) or "beautiful shades"
    desc = (f"{product.name} from WearVerse. Available in {colours}"
            + (f", sizes {', '.join(facts['sizes'])}" if facts["sizes"] else "")
            + ". " + (notes.strip() + " " if notes else "")
            + ("Free fall-pico on this saree. " if facts["fall_pico"] else "")
            + "Hand-picked at our shop, shipped across India.")
    return {"title": product.name, "description": desc[:2000], "tags": sorted(set(words + [product.category.lower()]))[:12],
            "source": "fallback"}


THEMES = {
    "festive": {"bg1": "#5b2333", "bg2": "#8c3a4f", "text": "#FFF7E8", "accent": "#C9A66B"},
    "wedding": {"bg1": "#6b0f1a", "bg2": "#b91646", "text": "#FFF3D6", "accent": "#E8C170"},
    "sale": {"bg1": "#111111", "bg2": "#3a3a3a", "text": "#FFFFFF", "accent": "#F9AB00"},
    "fresh": {"bg1": "#F5ECEE", "bg2": "#FBF7F6", "text": "#2B1A20", "accent": "#5b2333"},
}
SIZES = {"square": (1080, 1080), "story": (1080, 1920), "banner": (1920, 640)}


def suggest_copy(db: Session, brief: str, language: str) -> dict:
    ai = gateway.ask(db, "poster", "/ai/poster/copy", {"brief": brief, "language": language}, timeout=15)
    if ai and isinstance(ai.get("options"), list):
        return {"options": [o for o in ai["options"] if isinstance(o, dict)][:4], "source": "ai"}
    return {"options": [{"headline": brief[:40], "subline": "Visit WearVerse today"}], "source": "fallback"}


def _wrap(text: str, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        if len(line) + len(word) + 1 > width and line:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines[:4]


def render_poster(db: Session, *, headline: str, subline: str, footer: str | None, product_ids: list[UUID],
                  theme: str, size: str) -> str:
    """SVG poster: exact text from staff + product photos. Staff download it as SVG or PNG."""
    w, h = SIZES.get(size, SIZES["square"])
    t = THEMES.get(theme, THEMES["festive"])
    shop = escape(str(get_setting(db, "shop_name") or "WearVerse"))
    photos = []
    for pid in product_ids[:3]:
        image = db.scalar(select(ProductImage).where(ProductImage.product_id == pid).order_by(ProductImage.created_at))
        url = get_product_image_url(image.object_key) if image else None
        if url:
            photos.append(url)
    head_size = int(min(w, h) * (0.085 if size != "banner" else 0.12))
    head_lines = _wrap(headline, 18 if size != "banner" else 28)
    text_x = w * 0.07
    head_y = h * (0.16 if size != "banner" else 0.3)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
             f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["bg1"]}"/><stop offset="1" stop-color="{t["bg2"]}"/></linearGradient></defs>',
             f'<rect width="{w}" height="{h}" fill="url(#g)"/>',
             f'<rect x="{w*0.03}" y="{h*0.03}" width="{w*0.94}" height="{h*0.94}" fill="none" stroke="{t["accent"]}" stroke-width="4"/>']
    for i, line in enumerate(head_lines):
        parts.append(f'<text x="{text_x}" y="{head_y + i * head_size * 1.15}" font-family="Playfair Display, Georgia, serif" '
                     f'font-size="{head_size}" font-weight="700" fill="{t["text"]}">{escape(line)}</text>')
    sub_y = head_y + len(head_lines) * head_size * 1.15 + head_size * 0.3
    parts.append(f'<text x="{text_x}" y="{sub_y}" font-family="Inter, Arial, sans-serif" font-size="{head_size*0.42}" fill="{t["accent"]}">{escape(subline)}</text>')
    if photos:
        area_top = sub_y + head_size * 0.6 if size != "banner" else h * 0.1
        if size == "banner":
            pw, ph, px0 = w * 0.18, h * 0.8, w * 0.42
            for i, url in enumerate(photos):
                parts.append(f'<image href="{escape(url)}" x="{px0 + i*(pw+w*0.02)}" y="{h*0.1}" width="{pw}" height="{ph}" preserveAspectRatio="xMidYMid slice"/>')
        else:
            gap = w * 0.03
            pw = (w * 0.86 - gap * (len(photos) - 1)) / len(photos)
            ph = h * 0.82 - area_top
            for i, url in enumerate(photos):
                parts.append(f'<image href="{escape(url)}" x="{text_x + i*(pw+gap)}" y="{area_top}" width="{pw}" height="{ph}" preserveAspectRatio="xMidYMid slice"/>')
    parts.append(f'<text x="{w/2}" y="{h*0.93}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="{head_size*0.36}" '
                 f'fill="{t["text"]}">{escape(footer or "")}{" · " if footer else ""}{shop}</text>')
    parts.append("</svg>")
    return "".join(parts)
