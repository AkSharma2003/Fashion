"""Add a starter catalogue for the three shops (safe to run again: existing SKUs are skipped).

    cd apps/api && python -m scripts.seed_catalog

Sarees are stocked in Sethi Saree Sansar, suits in Sethi Suit, kidswear in Sethi Kids. Prices include GST
(the rate comes from the GST slabs in Settings). Photos are added later from Back office → Products.
"""
from sqlalchemy import select

import app.models_registry  # noqa: F401
from app.core.db import SessionLocal
from app.modules.assist import catalog_ai
from app.modules.catalog.models import Product
from app.modules.inventory import stock
from app.modules.inventory.models import Barcode, ProductVariant
from app.modules.shops.service import ensure_default_shops

R = 100  # paise per rupee

# (shop, sku, name, category, price ₹, mrp ₹, hsn, fall_pico, description, [(size, colour, stock), ...])
CATALOG = [
    # ---- Sethi Saree Sansar
    ("SSS", "SSS-BAN-001", "Banarasi Silk Saree with Zari Border", "Sarees", 6499, 7999, "5007", True,
     "Pure Banarasi silk with a heavy gold zari border and woven pallu. Comes with an unstitched blouse piece.",
     [("Free", "Maroon", 4), ("Free", "Royal Blue", 3), ("Free", "Bottle Green", 2)]),
    ("SSS", "SSS-KAN-002", "Kanjeevaram Silk Saree", "Sarees", 12999, 15999, "5007", True,
     "Traditional Kanjeevaram silk with temple border and contrast pallu. A wedding favourite.",
     [("Free", "Red", 2), ("Free", "Mustard", 2)]),
    ("SSS", "SSS-COT-003", "Handloom Cotton Saree", "Sarees", 1299, 1599, "5208", True,
     "Soft, breathable handloom cotton for daily and office wear. Easy to drape and wash.",
     [("Free", "Off White", 6), ("Free", "Sky Blue", 5), ("Free", "Peach", 4)]),
    ("SSS", "SSS-CHF-004", "Printed Chiffon Saree", "Sarees", 899, 1199, "5407", False,
     "Light floral-print chiffon, ideal for summer and small functions.",
     [("Free", "Pink", 8), ("Free", "Lavender", 6)]),
    ("SSS", "SSS-GEO-005", "Georgette Party Wear Saree with Sequins", "Sarees", 3499, 4299, "5407", True,
     "Georgette with hand-done sequin work and a ready blouse in size 38.",
     [("Free", "Black", 3), ("Free", "Wine", 3), ("Free", "Gold", 2)]),
    ("SSS", "SSS-BAN-006", "Bandhani Gajji Silk Saree", "Sarees", 4999, 5999, "5007", True,
     "Hand-tied Gujarati bandhani on gajji silk with a zari pallu.",
     [("Free", "Rani Pink", 3), ("Free", "Green", 2)]),
    ("SSS", "SSS-BLS-007", "Ready-made Silk Blouse", "Blouse", 799, 999, "6206", False,
     "Lined art-silk blouse with back hooks; goes with most silk sarees.",
     [("34", "Gold", 3), ("36", "Gold", 4), ("38", "Gold", 4), ("40", "Gold", 2), ("36", "Maroon", 3), ("38", "Maroon", 3)]),
    ("SSS", "SSS-PTC-008", "Cotton Petticoat", "Petticoat", 349, 399, "6208", False,
     "Six-panel cotton petticoat with drawstring.",
     [("Free", "Black", 10), ("Free", "White", 10), ("Free", "Maroon", 6), ("Free", "Beige", 6)]),

    # ---- Sethi Suit
    ("SS", "SS-ANK-001", "Anarkali Suit with Dupatta", "Suits", 2999, 3699, "6204", False,
     "Flared georgette Anarkali with embroidered yoke, churidar and net dupatta.",
     [("S", "Teal", 2), ("M", "Teal", 3), ("L", "Teal", 3), ("XL", "Teal", 2), ("M", "Wine", 2), ("L", "Wine", 2)]),
    ("SS", "SS-STR-002", "Straight Cotton Kurta Set", "Suits", 1499, 1899, "6204", False,
     "Printed straight kurta with matching pants and mulmul dupatta. Everyday comfort.",
     [("S", "Mustard", 3), ("M", "Mustard", 4), ("L", "Mustard", 4), ("XL", "Mustard", 2),
      ("M", "Navy", 3), ("L", "Navy", 3)]),
    ("SS", "SS-PAT-003", "Patiala Salwar Suit", "Suits", 1899, 2299, "6204", False,
     "Cotton-silk kurta with a full Patiala salwar and phulkari-style dupatta.",
     [("M", "Orange", 3), ("L", "Orange", 3), ("XL", "Orange", 2), ("M", "Parrot Green", 2), ("L", "Parrot Green", 2)]),
    ("SS", "SS-SHR-004", "Sharara Suit Set", "Suits", 3999, 4999, "6204", False,
     "Short kurti with flared sharara and gota-work dupatta for festivals and mehndi.",
     [("S", "Mint", 2), ("M", "Mint", 2), ("L", "Mint", 2), ("M", "Pink", 2), ("L", "Pink", 2)]),
    ("SS", "SS-CHK-005", "Chikankari Kurta", "Kurti", 1699, 1999, "6206", False,
     "Lucknowi chikankari on soft georgette, with a cotton slip.",
     [("S", "White", 3), ("M", "White", 4), ("L", "White", 4), ("XL", "White", 2), ("M", "Lemon", 2), ("L", "Lemon", 2)]),
    ("SS", "SS-DUP-006", "Phulkari Dupatta", "Dupatta", 999, 1299, "6214", False,
     "Hand-embroidered phulkari dupatta, pairs with plain suits.",
     [("Free", "Multicolour", 6), ("Free", "Red", 4)]),

    # ---- Sethi Kids
    ("SK", "SK-LEH-001", "Girls Lehenga Choli", "Kids", 1799, 2199, "6104", False,
     "Festive lehenga with mirror-work choli and dupatta for girls.",
     [("2-3Y", "Pink", 2), ("4-5Y", "Pink", 3), ("6-7Y", "Pink", 3), ("8-9Y", "Pink", 2),
      ("4-5Y", "Yellow", 2), ("6-7Y", "Yellow", 2)]),
    ("SK", "SK-KUR-002", "Boys Kurta Pajama Set", "Kids", 1199, 1499, "6203", False,
     "Cotton-silk kurta with pajama for festivals and pujas.",
     [("2-3Y", "Cream", 3), ("4-5Y", "Cream", 4), ("6-7Y", "Cream", 4), ("8-9Y", "Cream", 3),
      ("4-5Y", "Royal Blue", 2), ("6-7Y", "Royal Blue", 2)]),
    ("SK", "SK-FRK-003", "Girls Party Frock", "Kids", 999, 1299, "6104", False,
     "Net frock with satin lining and a bow at the waist.",
     [("2-3Y", "Peach", 3), ("4-5Y", "Peach", 3), ("6-7Y", "Peach", 2), ("4-5Y", "Lavender", 2)]),
    ("SK", "SK-SHR-004", "Boys Sherwani Set", "Kids", 2499, 2999, "6203", False,
     "Brocade sherwani with churidar and stole for weddings.",
     [("4-5Y", "Gold", 2), ("6-7Y", "Gold", 2), ("8-9Y", "Gold", 2), ("6-7Y", "Maroon", 2)]),
    ("SK", "SK-DHT-005", "Kids Dhoti Kurta", "Kids", 799, 999, "6203", False,
     "Ready-to-wear dhoti with elastic waist and a short kurta.",
     [("1-2Y", "Yellow", 3), ("2-3Y", "Yellow", 3), ("4-5Y", "Yellow", 3), ("2-3Y", "Orange", 2)]),
]


def main() -> None:
    added = skipped = 0
    with SessionLocal() as db:
        shops = {s.code: s for s in ensure_default_shops(db)}
        for shop_code, sku, name, category, price, mrp, hsn, fall_pico, desc, variants in CATALOG:
            if db.scalar(select(Product).where(Product.sku == sku)):
                skipped += 1
                continue
            product = Product(name=name, sku=sku, category=category, description=desc,
                              selling_price_paise=price * R, mrp_paise=mrp * R, hsn_code=hsn,
                              fall_pico_eligible=fall_pico, is_active=True)
            db.add(product)
            db.flush()
            for size, colour, qty in variants:
                vsku = f"{sku}-{size}-{colour}".upper().replace(" ", "")[:64]
                variant = ProductVariant(product_id=product.id, sku=vsku, size=size, color=colour, is_active=True,
                                         cost_paise=round(price * 0.6) * R)
                db.add(variant)
                db.flush()
                db.add(Barcode(variant_id=variant.id, code=vsku))
                stock.move(db, variant.id, qty, "opening", source="adjustment", reason="Starter catalogue",
                           shop_id=shops[shop_code].id)
            catalog_ai.refresh_index(db, product, fetch_images=False)   # search and recommendations
            added += 1
        db.commit()
    print(f"Catalogue: {added} products added, {skipped} already there.")


if __name__ == "__main__":
    main()
