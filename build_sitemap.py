#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_sitemap.py
Generates sitemap.xml from all published articles.
Run automatically by pipeline_v2.py after each publish.
Can also be run manually: python build_sitemap.py
"""

import sys, re
from pathlib import Path
from datetime import date, datetime

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR  = Path(__file__).parent
DOCS_DIR  = BASE_DIR / "docs"
SITEMAP   = BASE_DIR / "sitemap.xml"
DOMAIN    = "https://www.luispaiva.co.uk"
SKIP      = {".gitkeep", "index.md", "privacy.md", "about.md"}

# Must match DATE_OVERRIDES in build_homepage.py
from datetime import date as _date
DATE_OVERRIDES = {
    "pension-at-39-should-i-stop-working":        _date(2026, 3, 28),
    "can-i-withdraw-my-lisa-savings-at-60-uk":    _date(2026, 3, 29),
    "how-to-save-10000-pounds-in-one-year-uk":    _date(2026, 3, 30),
    "end-of-tax-year-checklist-uk-2026":          _date(2026, 3, 31),
}

def get_pub_date(md_path):
    """Read PUB_DATE from md file, fall back to DATE_OVERRIDES, then mtime."""
    slug = md_path.stem
    text = md_path.read_text(encoding="utf-8")
    m = re.search(r'^PUB_DATE:\s*(\d{4}-\d{2}-\d{2})', text, re.MULTILINE)
    if m:
        return m.group(1)
    if slug in DATE_OVERRIDES:
        return DATE_OVERRIDES[slug].isoformat()
    return datetime.fromtimestamp(md_path.stat().st_mtime).strftime("%Y-%m-%d")

def build_sitemap():
    today = date.today().isoformat()

    # Static pages — use today as lastmod (they change with each deploy)
    static = [
    	{"url": "",                          "priority": "1.0", "changefreq": "daily"},
     	{"url": "/about",                    "priority": "0.5", "changefreq": "monthly"},
    	{"url": "/newsletter",               "priority": "0.6", "changefreq": "weekly"},
    	{"url": "/privacy",                  "priority": "0.3", "changefreq": "yearly"},
    	{"url": "/calculators",              "priority": "0.9", "changefreq": "monthly"},
    	{"url": "/take-home-pay-calculator", "priority": "0.8", "changefreq": "monthly"},
    ]

    # Articles
    articles = []
    for md in sorted(DOCS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        if md.name in SKIP:
            continue
        slug    = md.stem
        lastmod = get_pub_date(md)
        articles.append({"slug": slug, "lastmod": lastmod})

    # Build XML
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    for page in static:
        lines.append("  <url>")
        lines.append(f"    <loc>{DOMAIN}{page['url']}/</loc>")  # no double slash
        lines.append(f"    <lastmod>{today}</lastmod>")
        lines.append(f"    <changefreq>{page['changefreq']}</changefreq>")
        lines.append(f"    <priority>{page['priority']}</priority>")
        lines.append("  </url>")

    for a in articles:
        lines.append("  <url>")
        lines.append(f"    <loc>{DOMAIN}/{a['slug']}/</loc>")
        lines.append(f"    <lastmod>{a['lastmod']}</lastmod>")
        lines.append(f"    <changefreq>monthly</changefreq>")
        lines.append(f"    <priority>0.8</priority>")
        lines.append("  </url>")

    lines.append("</urlset>")

    xml = "\n".join(lines)
    SITEMAP.write_text(xml, encoding="utf-8")
    print(f"  Sitemap: {len(articles)} articles + {len(static)} pages -> sitemap.xml OK")
    return len(articles)

if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Building sitemap...")
    n = build_sitemap()
    print(f"  Done. {n} articles indexed.")
