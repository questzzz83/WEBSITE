#!/usr/bin/env python3
"""
build_articles_page.py
Injects SITE_ARTICLES into articles/index.html (the archive page).
Run automatically by publish_article.py after each publish.
Can also be run manually: python build_articles_page.py
"""

import re, json, sys, subprocess
from pathlib import Path
from datetime import datetime

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR         = Path(__file__).parent
ARTICLES_DIR     = BASE_DIR / "articles"
ARTICLES_HTML    = ARTICLES_DIR / "index.html"
TEMPLATE_HTML    = BASE_DIR / "articles-template.html"

def inject(articles):
    # Decide which file to write to
    if ARTICLES_HTML.exists():
        target = ARTICLES_HTML
    elif TEMPLATE_HTML.exists():
        target = TEMPLATE_HTML
    else:
        print("  build_articles_page: no articles/index.html or articles-template.html found")
        print("  Create articles/index.html first (see articles-template.html)")
        return

    html        = target.read_text(encoding="utf-8")
    replacement = f"window.SITE_ARTICLES = {json.dumps(articles, ensure_ascii=False, indent=2)};"
    pattern     = r'window\.SITE_ARTICLES\s*=\s*\[[\s\S]*?\];'

    if re.search(pattern, html):
        html = re.sub(pattern, replacement, html)
    else:
        # First time — insert before the var ARTICLES line
        html = html.replace(
            'var ARTICLES = window.SITE_ARTICLES || [];',
            f'{replacement}\n  var ARTICLES = window.SITE_ARTICLES || [];'
        )

    target.write_text(html, encoding="utf-8")
    print(f"  build_articles_page: injected {len(articles)} articles -> {target.relative_to(BASE_DIR)} OK")

if __name__ == "__main__":
    # Re-use build_homepage's article extraction — no duplication
    sys.path.insert(0, str(BASE_DIR))
    from build_homepage import build_articles
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Building articles archive page...")
    arts = build_articles()
    print(f"  Found {len(arts)} articles")
    inject(arts)
    print("  Done.")
