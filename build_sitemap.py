#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_sitemap.py
Generates sitemap.xml from all published articles.
Run automatically by pipeline_v2.py after each publish.
Can also be run manually: python build_sitemap.py
"""

import sys
from pathlib import Path
from datetime import date, datetime

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR  = Path(__file__).parent
DOCS_DIR  = BASE_DIR / "docs"
SITEMAP   = BASE_DIR / "sitemap.xml"
DOMAIN    = "https://www.luispaiva.co.uk"
SKIP      = {".gitkeep", "index.md", "privacy.md", "about.md"}

def build_sitemap():
    today = date.today().isoformat()

    # Static pages
    static = [
        {"url": "/",            "priority": "1.0", "changefreq": "daily"},
        {"url": "/about",       "priority": "0.5", "changefreq": "monthly"},
        {"url": "/newsletter",  "priority": "0.6", "changefreq": "weekly"},
        {"url": "/privacy",     "priority": "0.3", "changefreq": "yearly"},
    ]

    # Articles
    articles = []
    for md in sorted(DOCS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        if md.name in SKIP:
            continue
        slug    = md.stem
        lastmod = datetime.fromtimestamp(md.stat().st_mtime).strftime("%Y-%m-%d")
        articles.append({"slug": slug, "lastmod": lastmod})

    # Build XML
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    for page in static:
        lines.append("  <url>")
        lines.append(f"    <loc>{DOMAIN}{page['url']}/</loc>")
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
