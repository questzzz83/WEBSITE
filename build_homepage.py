#!/usr/bin/env python3
"""
build_homepage.py
Scans docs/*.md, extracts title + excerpt from each,
injects SITE_ARTICLES array into index.html.
Run automatically by pipeline_v2.py after each publish.
"""

import re, json
from pathlib import Path
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8","utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime, date as _date

BASE_DIR   = Path(__file__).parent
DOCS_DIR   = BASE_DIR / "docs"
INDEX_HTML = BASE_DIR / "index.html"
SKIP       = {"CNAME", ".gitkeep", "index.md", "privacy.md", "about.md"}

# Fallback dates for articles that predate the PUB_DATE system.
# New articles written by the pipeline will have PUB_DATE in the .md file
# and won't need an entry here.
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
        return _date.fromisoformat(m.group(1))
    if slug in DATE_OVERRIDES:
        return DATE_OVERRIDES[slug]
    return datetime.fromtimestamp(md_path.stat().st_mtime).date()

def extract_title(text, fallback):
    m = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
    if m:
        return re.sub(r'\s*<!--.*?-->', '', m.group(1)).strip()
    return fallback.replace('-', ' ').title()

def extract_excerpt(text, words=40):
    text = re.sub(r'^PUB_DATE:.*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^META_DESCRIPTION:.*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^<!--.*?-->\s*', '', text, flags=re.DOTALL|re.MULTILINE)
    text = re.sub(r'^---.*?---\s*', '', text, flags=re.DOTALL)
    text = re.sub(r'^#{1,}\s+.+\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'\*{1,2}(.+?)\*{1,2}', r'\1', text)
    text = re.sub(r'`[^`]+`', '', text)
    text = re.sub(r'\n{2,}', '\n', text).strip()
    tokens = text.split()
    return (' '.join(tokens[:words]) + '...') if len(tokens) > words else ' '.join(tokens)

def build_articles():
    articles = []
    for md in DOCS_DIR.glob("*.md"):
        if md.name in SKIP: continue
        text    = md.read_text(encoding="utf-8")
        sl      = md.stem
        title   = extract_title(text, sl)
        excerpt = extract_excerpt(text)
        if not excerpt: continue
        pub   = get_pub_date(md)
        mdate = pub.strftime("%d %b %Y")
        articles.append({"title": title, "slug": sl, "excerpt": excerpt, "date": mdate, "_pub": pub})
    # Newest first — hero slot [0], sidebar [1-3], grid [4+]
    articles.sort(key=lambda a: a["_pub"], reverse=True)
    for a in articles:
        del a["_pub"]
    return articles

def inject(articles):
    if not INDEX_HTML.exists():
        print(f"  build_homepage: {INDEX_HTML} not found")
        return
    html        = INDEX_HTML.read_text(encoding="utf-8")
    replacement = f"window.SITE_ARTICLES = {json.dumps(articles, ensure_ascii=False, indent=2)};"
    pattern     = r'window\.SITE_ARTICLES\s*=\s*\[[\s\S]*?\];'
    if re.search(pattern, html):
        html = re.sub(pattern, replacement, html)
    else:
        html = html.replace(
            'var ARTICLES = window.SITE_ARTICLES || [];',
            f'{replacement}\n  var ARTICLES = window.SITE_ARTICLES || [];'
        )
    INDEX_HTML.write_text(html, encoding="utf-8")
    print(f"  build_homepage: injected {len(articles)} articles OK")

if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Building homepage...")
    arts = build_articles()
    print(f"  Found {len(arts)} articles")
    for a in arts:
        print(f"    [{a['date']}] {a['slug']}")
    inject(arts)
    print("  Done.")
