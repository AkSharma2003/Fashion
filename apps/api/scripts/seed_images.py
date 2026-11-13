"""Give every product without a photo a clean illustration in its own colours (one per colour, up to 3).

    cd apps/api && python -m scripts.seed_images            # upload to image storage (R2) and save in the database
    cd apps/api && python -m scripts.seed_images --preview DIR   # only draw PNGs into DIR, upload nothing

These are drawings, not photos: replace them with real photos from Back office → Products when ready.
Products that already have an image are skipped, so it is safe to run again.
"""
import argparse
import math
import os
from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from sqlalchemy import select

import app.models_registry  # noqa: F401
from app.core.db import SessionLocal

W, H = 800, 1000
COLORS = {
    "red": "#C62828", "maroon": "#7B1E2B", "wine": "#5B1A33", "rani pink": "#D81B7A", "pink": "#F48FB1",
    "peach": "#FFB59A", "orange": "#EF6C00", "rust": "#A8441C", "mustard": "#D4A017", "yellow": "#FBC02D",
    "lemon": "#F3E66B", "green": "#2E7D32", "bottle green": "#0B4F2C", "parrot green": "#7CB342", "mint": "#A5D6A7",
    "teal": "#00796B", "sky blue": "#81D4FA", "blue": "#1565C0", "royal blue": "#283FA8", "navy": "#1A2A5A",
    "purple": "#6A1B9A", "lavender": "#C3B1E1", "magenta": "#B0006D", "black": "#1B1B1B", "grey": "#8A8A8A",
    "white": "#F7F7F4", "off white": "#F5F1E6", "cream": "#F3E5C0", "beige": "#D8C3A5", "brown": "#6D4C41",
    "gold": "#C9A227", "silver": "#BFC4CA",
}
MULTI = ["#C62828", "#FBC02D", "#2E7D32", "#1565C0", "#D81B7A"]
GOLD = (201, 162, 39)


def rgb(hex_: str) -> tuple[int, int, int]:
    hex_ = hex_.lstrip("#")
    return tuple(int(hex_[i:i + 2], 16) for i in (0, 2, 4))


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def colour_of(name: str):
    key = (name or "").strip().lower()
    if "multi" in key:
        return None
    return rgb(COLORS.get(key, "#B08B5B"))


def font(size, bold=False):
    for path in (["/System/Library/Fonts/Supplemental/Georgia Bold.ttf"] if bold else []) + [
            "/System/Library/Fonts/Supplemental/Georgia.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def background(base):
    """Soft studio backdrop tinted towards the garment colour."""
    img = Image.new("RGB", (W, H), (250, 246, 240))
    px = img.load()
    tint = base or (200, 160, 120)
    for y in range(H):
        t = y / H
        row = tuple(int(250 * (1 - 0.10 * t) * 0.88 + tint[i] * 0.12 * (0.4 + 0.6 * t)) for i in range(3))
        for x in range(W):
            px[x, y] = row
    d = ImageDraw.Draw(img)
    d.ellipse((140, 860, 660, 940), fill=shade(img.getpixel((400, 900)), 0.9))       # floor shadow
    return img


def motif_dots(d, box, colour, step=34, r=4):
    x0, y0, x1, y1 = box
    for y in range(int(y0) + step // 2, int(y1), step):
        off = (y // step) % 2 * step // 2
        for x in range(int(x0) + step // 2 + off, int(x1), step):
            d.ellipse((x - r, y - r, x + r, y + r), fill=colour)


def fill_multi(d, poly):
    d.polygon(poly, fill=MULTI[0])
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    band = (max(ys) - min(ys)) / len(MULTI)
    for i, c in enumerate(MULTI):
        d.rectangle((min(xs), min(ys) + i * band, max(xs), min(ys) + (i + 1) * band), fill=c)


def draw_saree(img, c):
    d = ImageDraw.Draw(img)
    base = c or rgb(MULTI[0])
    dark, light = shade(base, 0.72), shade(base, 1.15)
    body = [(300, 210), (500, 210), (560, 860), (240, 860)]                 # pleated drape
    d.polygon(body, fill=base)
    for i in range(7):                                                        # pleats
        x = 270 + i * 40
        d.line([(x + 20, 520), (x, 860)], fill=dark, width=3)
    d.rectangle((236, 830, 564, 860), fill=GOLD)                             # zari border at the hem
    pallu = [(300, 210), (500, 210), (610, 300), (640, 700), (560, 720), (470, 330)]   # pallu over the shoulder
    d.polygon(pallu, fill=light)
    motif_dots(d, (470, 300, 630, 700), shade(GOLD, 1.05), step=30, r=3)
    d.line([(500, 210), (610, 300), (640, 700)], fill=GOLD, width=14)
    d.line([(560, 720), (640, 700)], fill=GOLD, width=10)
    d.ellipse((350, 120, 450, 220), fill=(226, 196, 170))                    # head of the form
    d.rectangle((385, 200, 415, 230), fill=(226, 196, 170))


def draw_kurta(img, c, short=False, bottoms=True):
    d = ImageDraw.Draw(img)
    base = c or rgb(MULTI[3])
    dark = shade(base, 0.75)
    hem = 470 if short else 760
    body = [(330, 230), (470, 230), (520, 300), (600, 470), (560, 490), (520, 380), (560, hem), (240, hem),
            (280, 380), (240, 490), (200, 470), (280, 300)]
    d.polygon(body, fill=base)
    d.polygon([(370, 230), (430, 230), (400, 300)], fill=dark)               # neckline
    d.line([(400, 300), (400, 420)], fill=GOLD, width=6)                      # placket
    motif_dots(d, (270, 440, 530, hem - 20), shade(base, 1.25), step=40, r=4)
    d.rectangle((240, hem - 24, 560, hem), fill=GOLD)
    if not short and bottoms:
        d.polygon([(560, hem), (240, hem), (260, 860), (540, 860)], fill=shade(base, 0.9))   # salwar / pants
        d.line([(400, hem), (400, 860)], fill=dark, width=4)
        d.polygon([(470, 230), (520, 300), (330, 820), (290, 800)], fill=(*shade(base, 1.3), ))  # dupatta
    d.ellipse((350, 130, 450, 230), fill=(226, 196, 170))


def draw_lehenga(img, c, frock=False):
    d = ImageDraw.Draw(img)
    base = c or rgb(MULTI[4])
    top = shade(base, 0.85)
    d.polygon([(340, 300), (460, 300), (490, 430), (310, 430)], fill=top)    # choli / bodice
    skirt_top, skirt_bottom = 430, (740 if frock else 860)
    d.polygon([(310, skirt_top), (490, skirt_top), (620, skirt_bottom), (180, skirt_bottom)], fill=base)
    for i in range(9):
        x = 200 + i * 50
        d.line([(400 + (x - 400) * 0.25, skirt_top), (x, skirt_bottom)], fill=shade(base, 0.8), width=3)
    d.rectangle((180, skirt_bottom - 26, 620, skirt_bottom), fill=GOLD)
    motif_dots(d, (330, 440, 470, 520), shade(GOLD, 1.05), step=26, r=3)
    if frock:
        d.polygon([(380, 430), (420, 430), (440, 470), (360, 470)], fill=shade(base, 1.3))   # bow
    d.ellipse((355, 200, 445, 290), fill=(226, 196, 170))


def draw_petticoat(img, c):
    d = ImageDraw.Draw(img)
    base = c or rgb("#1B1B1B")
    d.polygon([(320, 260), (480, 260), (560, 820), (240, 820)], fill=base)
    for i in range(6):
        x = 260 + i * 56
        d.line([(330 + i * 28, 260), (x, 820)], fill=shade(base, 0.8), width=3)
    d.rectangle((316, 250, 484, 276), fill=shade(base, 0.7))
    d.line([(400, 276), (400, 330)], fill=shade(base, 1.4), width=4)


def draw_dupatta(img, c):
    d = ImageDraw.Draw(img)
    base = c
    poly = [(250, 180), (330, 160), (560, 820), (480, 850)]
    if base is None:
        fill_multi(d, poly)
        base = rgb(MULTI[0])
    else:
        d.polygon(poly, fill=base)
    d.line([(250, 180), (480, 850)], fill=GOLD, width=12)
    d.line([(330, 160), (560, 820)], fill=GOLD, width=12)
    for t in range(1, 9):
        x = 290 + t * 25
        y = 170 + t * 75
        d.regular_polygon((x, y, 14), 6, fill=shade(GOLD, 1.05) if c else (255, 255, 255))


def kind_of(product) -> str:
    """Category first (an "Anarkali Suit with Dupatta" is a suit), then words in the name."""
    n, cat = product.name.lower(), (product.category or "").lower()
    by_category = {"sarees": "saree", "blouse": "blouse", "petticoat": "petticoat", "dupatta": "dupatta",
                   "kurti": "kurti", "suits": "kurta"}
    if cat in by_category:
        return by_category[cat]
    if cat == "kids" or "kids" in n or "girls" in n or "boys" in n:
        if "frock" in n:
            return "frock"
        if "lehenga" in n:
            return "lehenga"
        return "kids_kurta"
    for word, kind in (("saree", "saree"), ("lehenga", "lehenga"), ("dupatta", "dupatta"), ("blouse", "blouse")):
        if word in n:
            return kind
    return "kurta"


def render(product, colour_name: str) -> bytes:
    c = colour_of(colour_name)
    img = background(c)
    kind = kind_of(product)
    {"saree": draw_saree, "petticoat": draw_petticoat, "dupatta": draw_dupatta,
     "lehenga": draw_lehenga, "frock": lambda i, x: draw_lehenga(i, x, frock=True),
     "blouse": lambda i, x: draw_kurta(i, x, short=True), "kurti": lambda i, x: draw_kurta(i, x, bottoms=False),
     "kids_kurta": draw_kurta, "kurta": draw_kurta}[kind](img, c)
    img = img.filter(ImageFilter.SMOOTH)
    d = ImageDraw.Draw(img)
    d.rectangle((0, H - 96, W, H), fill=(255, 255, 255))
    title = product.name if len(product.name) <= 34 else product.name[:33] + "…"
    f, f2 = font(30, bold=True), font(22)
    d.text((W / 2, H - 62), title, fill=(60, 30, 40), font=f, anchor="mm")
    d.text((W / 2, H - 26), f"{colour_name} · illustration", fill=(120, 110, 105), font=f2, anchor="mm")
    out = BytesIO()
    img.save(out, "JPEG", quality=88)
    return out.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", help="only write PNG files into this folder")
    args = parser.parse_args()
    from app.modules.assist import catalog_ai
    from app.modules.catalog.image_storage import upload_product_image
    from app.modules.catalog.models import Product, ProductImage
    from app.modules.inventory.models import ProductVariant

    done = skipped = 0
    with SessionLocal() as db:
        for p in db.scalars(select(Product).where(Product.is_active.is_(True)).order_by(Product.name)).all():
            if not args.preview and db.scalar(select(ProductImage.id).where(ProductImage.product_id == p.id).limit(1)):
                skipped += 1
                continue
            colours = []
            for v in db.scalars(select(ProductVariant).where(ProductVariant.product_id == p.id,
                                                             ProductVariant.is_active.is_(True))).all():
                if v.color and v.color not in colours:
                    colours.append(v.color)
            colours = colours[:3] or ["Gold"]
            first_bytes, first_key = None, None
            for colour in colours:
                data = render(p, colour)
                if args.preview:
                    os.makedirs(args.preview, exist_ok=True)
                    with open(os.path.join(args.preview, f"{p.sku}-{colour}.jpg".replace(" ", "_")), "wb") as fh:
                        fh.write(data)
                    continue
                meta = upload_product_image(data, "image/jpeg", f"{p.sku}-{colour}.jpg".replace(" ", "_"))
                db.add(ProductImage(product_id=p.id, **meta))
                if first_bytes is None:
                    first_bytes, first_key = data, meta["object_key"]
            if not args.preview:
                db.flush()
                sig = catalog_ai.refresh_index(db, p, fetch_images=False)          # photo search uses the colours
                sig.color_signature = catalog_ai.color_signature(first_bytes) or sig.color_signature
                sig.image_key = first_key
                db.commit()
            done += 1
    print(f"Images: {done} products {'drawn' if args.preview else 'done'}, {skipped} already had photos.")


if __name__ == "__main__":
    main()
