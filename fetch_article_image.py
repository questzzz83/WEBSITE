#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_article_image.py
----------------------
Fetches a relevant hero image for an article from Unsplash (primary)
or Pexels (fallback). Downloads and saves to images/<slug>.jpg in the repo.

Called by pipeline_v2.py after the article is written and approved.
"""

import re, json, time, urllib.request, urllib.parse, os, sys
from pathlib import Path
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────────────
UNSPLASH_KEY = "3pPhBhUEqaxLaxLP3SFXos6H9HHyFOcla8VxkXvi03U"
PEXELS_KEY   = "dCoWcM6tDSYzqeTjtgTHKXjxv3XB3kgdWvOSkkodrQfMC9IN8SFFXUzk"

BASE_DIR   = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"
IMAGES_DIR.mkdir(exist_ok=True)

HEADERS = {"User-Agent": "luispaiva-blog/1.0"}

# ── KEYWORD EXTRACTION ────────────────────────────────────────────────
# Maps article categories/keywords to better image search terms
# Generic finance photos work better than overly specific ones
SEARCH_MAP = {
    "isa":            "savings account money jar",
    "lisa":           "savings piggy bank money",
    "pension":        "retirement planning coins",
    "retirement":     "retirement relaxing garden",
    "fire":           "financial freedom calculator",
    "savings":        "savings money coins jar",
    "save":           "coins saving money jar",
    "invest":         "stock market charts growth",
    "mortgage":       "house keys property uk",
    "credit":         "credit card wallet payment",
    "debt":           "calculator budget planning",
    "budget":         "budget planning notebook",
    "tax":            "tax forms calculator desk",
    "income":         "salary payslip money",
    "salary":         "payslip money desk",
    "side hustle":    "laptop coffee working desk",
    "insurance":      "umbrella protection family",
    "banking":        "bank card smartphone payment",
    "cashback":       "shopping bags money saving",
    "money":          "money pound sterling coins",
}

def build_search_query(topic, slug):
    """Build a good image search query from the article topic/slug."""
    topic_lower = topic.lower()
    slug_lower  = slug.lower()

    # Try keyword map first
    for keyword, query in SEARCH_MAP.items():
        if keyword in topic_lower or keyword in slug_lower:
            return query

    # Fallback: take first 3 meaningful words from topic
    words = re.sub(r'[^a-z\s]', '', topic_lower).split()
    stopwords = {'how', 'to', 'the', 'a', 'an', 'and', 'or', 'for',
                 'in', 'on', 'at', 'of', 'with', 'uk', 'is', 'are',
                 'you', 'your', 'my', 'i', 'best', 'what', 'why',
                 '2024', '2025', '2026', 'guide', 'vs', 'should'}
    keywords = [w for w in words if w not in stopwords][:3]
    return ' '.join(keywords) if keywords else "personal finance money"


# ── UNSPLASH ──────────────────────────────────────────────────────────
def fetch_unsplash(query, slug):
    """Fetch image from Unsplash. Returns local path or None."""
    try:
        params = urllib.parse.urlencode({
            "query":       query,
            "per_page":    5,
            "orientation": "landscape",
            "content_filter": "high",
        })
        url = f"https://api.unsplash.com/search/photos?{params}"
        req = urllib.request.Request(url, headers={
            **HEADERS,
            "Authorization": f"Client-ID {UNSPLASH_KEY}"
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())

        results = data.get("results", [])
        if not results:
            return None, None, None

        # Pick first result
        photo     = results[0]
        image_url = photo["urls"]["regular"]  # ~1080px wide
        credit    = photo["user"]["name"]
        credit_url = photo["user"]["links"]["html"] + "?utm_source=luispaiva&utm_medium=referral"
        photo_url  = photo["links"]["html"] + "?utm_source=luispaiva&utm_medium=referral"

        # Download
        local_path = _download(image_url, slug, "unsplash")
        if local_path:
            # Trigger download event (Unsplash API requirement)
            try:
                dl_url = photo["links"]["download_location"]
                dl_req = urllib.request.Request(dl_url, headers={
                    **HEADERS, "Authorization": f"Client-ID {UNSPLASH_KEY}"
                })
                urllib.request.urlopen(dl_req, timeout=10)
            except Exception:
                pass
            return local_path, credit, credit_url

    except Exception as e:
        print(f"  [image] Unsplash error: {e}", file=sys.stderr)
    return None, None, None


# ── PEXELS ────────────────────────────────────────────────────────────
def fetch_pexels(query, slug):
    """Fetch image from Pexels. Returns local path or None."""
    try:
        params = urllib.parse.urlencode({
            "query":       query,
            "per_page":    5,
            "orientation": "landscape",
            "size":        "large",
        })
        url = f"https://api.pexels.com/v1/search?{params}"
        req = urllib.request.Request(url, headers={
            **HEADERS,
            "Authorization": PEXELS_KEY
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())

        photos = data.get("photos", [])
        if not photos:
            return None, None, None

        photo      = photos[0]
        image_url  = photo["src"]["large"]   # ~940px wide
        credit     = photo["photographer"]
        credit_url = photo["photographer_url"]

        local_path = _download(image_url, slug, "pexels")
        if local_path:
            return local_path, credit, credit_url

    except Exception as e:
        print(f"  [image] Pexels error: {e}", file=sys.stderr)
    return None, None, None


# ── DOWNLOAD ─────────────────────────────────────────────────────────
def _download(url, slug, source):
    """Download image to images/<slug>.jpg. Returns path or None."""
    dest = IMAGES_DIR / f"{slug}.jpg"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        if len(data) < 5000:
            return None  # suspiciously small
        dest.write_bytes(data)
        print(f"  [image] Downloaded from {source}: images/{slug}.jpg ({len(data)//1024}KB)")
        return dest
    except Exception as e:
        print(f"  [image] Download error: {e}", file=sys.stderr)
    return None


# ── MAIN ENTRY POINT ──────────────────────────────────────────────────
def get_article_image(topic, slug):
    """
    Main function called by pipeline_v2.py.
    Returns dict with: path, credit_name, credit_url, source
    Or None if both APIs fail.
    """
    # Skip if image already exists
    existing = IMAGES_DIR / f"{slug}.jpg"
    if existing.exists() and existing.stat().st_size > 5000:
        print(f"  [image] Using cached: images/{slug}.jpg")
        # Load metadata if available
        meta_path = IMAGES_DIR / f"{slug}.json"
        if meta_path.exists():
            try:
                return json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"path": str(existing), "credit_name": "", "credit_url": "", "source": "cached"}

    query = build_search_query(topic, slug)
    print(f"  [image] Searching for: '{query}'")

    # Try Unsplash first
    path, credit, credit_url = fetch_unsplash(query, slug)
    source = "Unsplash"

    # Fallback to Pexels
    if not path:
        print(f"  [image] Unsplash failed, trying Pexels...")
        path, credit, credit_url = fetch_pexels(query, slug)
        source = "Pexels"

    if not path:
        print(f"  [image] Both APIs failed — article will have no hero image")
        return None

    result = {
        "path":        str(path),
        "credit_name": credit or "",
        "credit_url":  credit_url or "",
        "source":      source,
        "query":       query,
    }

    # Save metadata
    meta_path = IMAGES_DIR / f"{slug}.json"
    meta_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    return result


if __name__ == "__main__":
    # Test
    import sys
    topic = sys.argv[1] if len(sys.argv) > 1 else "best cash ISA rates UK 2026"
    slug  = sys.argv[2] if len(sys.argv) > 2 else "best-cash-isa-rates-uk-2026"
    result = get_article_image(topic, slug)
    print(json.dumps(result, indent=2))
