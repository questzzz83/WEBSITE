#!/usr/bin/env python3
"""
regenerate_image_meta.py
Re-fetches Unsplash metadata for all existing article images.
Run once from D:\website to restore missing .json files.
"""

from pathlib import Path
from fetch_article_image import get_article_image, IMAGES_DIR

# Map slug -> topic for search query building
SLUGS = {
    "best-balance-transfer-credit-cards":           "best balance transfer credit cards",
    "best-cash-isa-rates-uk-2026":                  "best cash ISA rates UK 2026",
    "best-credit-cards-for-building-credit-uk":     "best credit cards for building credit",
    "can-i-withdraw-my-lisa-savings-at-60-uk":      "LISA savings withdrawal",
    "current-mortgage-rate-coming-to-an-end":       "mortgage rates",
    "end-of-tax-year-checklist-uk-2026":            "tax year checklist",
    "every-money-change-april-2026-uk":             "money changes april 2026",
    "how-to-build-an-emergency-fund-uk-2026":       "emergency fund savings",
    "how-to-inherit-money-uk":                      "inheritance money uk",
    "how-to-protect-credit-score-after-death-of-a-parent-uk": "credit score protection",
    "how-to-save-10000-pounds-in-one-year-uk":      "save 10000 pounds",
    "pension-at-39-should-i-stop-working":          "pension retirement planning",
}

for slug, topic in SLUGS.items():
    jpg = IMAGES_DIR / f"{slug}.jpg"
    meta = IMAGES_DIR / f"{slug}.json"
    if not jpg.exists():
        print(f"SKIP (no jpg): {slug}")
        continue
    if meta.exists():
        print(f"SKIP (meta exists): {slug}")
        continue
    print(f"Fetching metadata: {slug}")
    # Delete jpg temporarily so fetch_unsplash runs fresh
    jpg.rename(IMAGES_DIR / f"{slug}.jpg.bak")
    result = get_article_image(topic, slug)
    if result:
        # Restore original jpg (keep the one we already have)
        bak = IMAGES_DIR / f"{slug}.jpg.bak"
        new_jpg = IMAGES_DIR / f"{slug}.jpg"
        if bak.exists():
            new_jpg.unlink(missing_ok=True)
            bak.rename(new_jpg)
        print(f"  OK: {result.get('credit_name')} -> {result.get('credit_url')}")
    else:
        # Restore backup if fetch failed
        bak = IMAGES_DIR / f"{slug}.jpg.bak"
        if bak.exists():
            bak.rename(IMAGES_DIR / f"{slug}.jpg")
        print(f"  FAILED: {slug}")

print("\nDone. Run rebuild_all.py next.")
