#!/usr/bin/env python3
"""
build_articles_page.py
Injects SITE_ARTICLES into articles/index.html (the archive page).
Run automatically by publish_article.py after each publish.
Can also be run manually: python build_articles_page.py
"""

import re, json, sys
from pathlib import Path
from datetime import datetime

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR      = Path(__file__).parent
ARTICLES_HTML = BASE_DIR / "articles" / "index.html"

def inject(articles):
    if not ARTICLES_HTML.exists():
        print(f"  ERROR: articles/index.html not found at {ARTICLES_HTML}")
        print(f"  Make sure articles/index.html exists in your project folder")
        return

    # Read as bytes to detect and preserve Windows CRLF line endings
    raw        = ARTICLES_HTML.read_bytes()
    is_windows = b'\r\n' in raw
    html       = raw.decode("utf-8")

    replacement = f"window.SITE_ARTICLES = {json.dumps(articles, ensure_ascii=False, indent=2)};"
    pattern     = r'window\.SITE_ARTICLES\s*=\s*\[[\s\S]*?\];'

    if re.search(pattern, html):
        html = re.sub(pattern, replacement, html)
    else:
        # First inject — insert before the var ARTICLES line
        html = html.replace(
            'var ARTICLES = window.SITE_ARTICLES || [];',
            f'{replacement}\n  var ARTICLES = window.SITE_ARTICLES || [];'
        )

    # Restore original line endings
    if is_windows:
        output = html.replace('\r\n', '\n').replace('\n', '\r\n').encode("utf-8")
    else:
        output = html.encode("utf-8")

    ARTICLES_HTML.write_bytes(output)
    print(f"  build_articles_page: injected {len(articles)} articles -> articles/index.html OK")
    print(f"  Line endings: {'Windows CRLF' if is_windows else 'Unix LF'}")

if __name__ == "__main__":
    sys.path.insert(0, str(BASE_DIR))
    from build_homepage import build_articles
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Building articles archive page...")
    print(f"  Looking for articles/index.html at: {ARTICLES_HTML}")
    arts = build_articles()
    if not arts:
        print("  No articles found")
        sys.exit(1)
    print(f"  Found {len(arts)} articles")
    inject(arts)
    print("  Done.")
