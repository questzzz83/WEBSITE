#!/usr/bin/env python3
"""
build_homepage.py
Scans docs/*.md, extracts title + excerpt from each,
injects SITE_ARTICLES array into index.html.
Run automatically by pipeline_v2.py after each publish.
"""

import re, json
from pathlib import Path
from datetime import datetime

BASE_DIR   = Path(__file__).parent
DOCS_DIR   = BASE_DIR / "docs"
INDEX_HTML = BASE_DIR / "index.html"
SKIP       = {"CNAME", ".gitkeep", "index.md", "privacy.md", "about.md"}

def extract_title(text, fallback):
    m = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
    if m:
        return re.sub(r'\s*<!--.*?-->', '', m.group(1)).strip()
    return fallback.replace('-', ' ').title()

def extract_excerpt(text, words=40):
    text = re.sub(r'^---.*?---\s*', '', text, flags=re.DOTALL)
    text = re.sub(r'^#{1,}\s+.+\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'\*{1,2}(.+?)\*{1,2}', r'\1', text)
    text = re.sub(r'`[^`]+`', '', text)
    text = re.sub(r'\n{2,}', '\n', text).strip()
    tokens = text.split()
    return (' '.join(tokens[:words]) + '…') if len(tokens) > words else ' '.join(tokens)

def build_articles():
    articles = []
    for md in sorted(DOCS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        if md.name in SKIP: continue
        text    = md.read_text(encoding="utf-8")
        sl      = md.stem
        title   = extract_title(text, sl)
        excerpt = extract_excerpt(text)
        if not excerpt: continue
        articles.append({"title": title, "slug": sl, "excerpt": excerpt})
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
            'const ARTICLES = window.SITE_ARTICLES || [];',
            f'{replacement}\n    const ARTICLES = window.SITE_ARTICLES || [];'
        )
    INDEX_HTML.write_text(html, encoding="utf-8")
    print(f"  build_homepage: injected {len(articles)} articles ✓")

if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Building homepage...")
    arts = build_articles()
    print(f"  Found {len(arts)} articles")
    inject(arts)
    print("  Done.")
