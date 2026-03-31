#!/usr/bin/env python3
"""
rebuild_all.py
Rebuilds all article HTML pages.
Reads PUB_DATE from each .md file (line: PUB_DATE: YYYY-MM-DD).
Falls back to file mtime if not present.
"""
import re
from pathlib import Path
from datetime import datetime, date
import sys

sys.path.insert(0, str(Path(__file__).parent))
from build_article import build_article_html

BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / "docs"
SKIP = {".gitkeep", "index.md", "privacy.md", "about.md"}

def get_pub_date(md_path):
    text = md_path.read_text(encoding="utf-8")
    m = re.search(r'^PUB_DATE:\s*(\d{4}-\d{2}-\d{2})', text, re.MULTILINE)
    if m:
        return date.fromisoformat(m.group(1))
    return datetime.fromtimestamp(md_path.stat().st_mtime).date()

for md_file in DOCS_DIR.glob("*.md"):
    if md_file.name in SKIP:
        continue
    slug = md_file.stem
    content = md_file.read_text(encoding="utf-8")
    pub_date = get_pub_date(md_file)
    html = build_article_html(slug.replace("-", " "), slug, content, pub_date=pub_date)
    out_dir = BASE_DIR / slug
    out_dir.mkdir(exist_ok=True)
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    print(f"Built: {slug}  [{pub_date}]")
