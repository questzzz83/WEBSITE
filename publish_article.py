#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publish_article.py
------------------
Manually publishes an article you've already written (with Claude's help).

Workflow:
  1. python trend_scout.py          -- finds today's topic
  2. Ask Claude to write the article
  3. Save the .md file to docs/<slug>.md
  4. python publish_article.py <slug>

What this script does:
  - Fetches hero image (Unsplash → Pexels)
  - Builds article HTML  →  <slug>/index.html
  - Rebuilds homepage    →  index.html
  - Rebuilds sitemap     →  sitemap.xml
  - Git push             →  triggers Vercel deploy
  - Sends Telegram notification

Usage:
  python publish_article.py every-money-change-april-2026-uk
  python publish_article.py                                    <- auto-detects newest .md
"""

import re, json, sys, subprocess
from pathlib import Path
from datetime import date, datetime

BASE_DIR   = Path(__file__).parent
DOCS_DIR   = BASE_DIR / "docs"
IMAGES_DIR = BASE_DIR / "images"
STATE_DIR  = BASE_DIR / ".pipeline"
LOGS_DIR   = BASE_DIR / "logs"

GITHUB_BRANCH = "main"
SITE_DOMAIN   = "www.luispaiva.co.uk"

SKIP = {".gitkeep", "index.md", "privacy.md", "about.md"}

# ── LOGGING ───────────────────────────────────────────────────────────
_log_path = LOGS_DIR / f"publish_{date.today().isoformat()}.log"

def log(msg, level="INFO"):
    ts   = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(_log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ── NOTIFY ────────────────────────────────────────────────────────────
def notify(msg):
    try:
        notify_path = BASE_DIR / "notify.py"
        import importlib.util as ilu
        spec = ilu.spec_from_file_location("notify", notify_path)
        nm = ilu.module_from_spec(spec)
        spec.loader.exec_module(nm)
        nm.notify(msg)
    except Exception:
        pass

# ── HELPERS ───────────────────────────────────────────────────────────
def slug_from_filename(md_path):
    return md_path.stem

def get_pub_date(md_path):
    text = md_path.read_text(encoding="utf-8")
    m = re.search(r'^PUB_DATE:\s*(\d{4}-\d{2}-\d{2})', text, re.MULTILINE)
    if m:
        return date.fromisoformat(m.group(1))
    return date.today()

def topic_from_slug(slug):
    """Best-effort human topic from slug."""
    return slug.replace("-", " ")

def find_newest_md():
    """Return the most recently modified .md in docs/ that isn't a skip file."""
    candidates = [
        f for f in DOCS_DIR.glob("*.md")
        if f.name not in SKIP
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda f: f.stat().st_mtime)

def git_push(commit_msg):
    log(f"  Pushing: {commit_msg}")

    # Pull remote changes first (theirs wins on conflict) to avoid rejection
    r = subprocess.run(
        ["git", "pull", "--no-rebase", "-X", "theirs", "origin", GITHUB_BRANCH],
        cwd=BASE_DIR, capture_output=True, text=True
    )
    if r.returncode != 0:
        log(f"  git pull warning: {r.stderr.strip()}", "WARN")
    else:
        log("  Pulled remote OK")

    for cmd in [
        ["git", "add", "-A"],
        ["git", "commit", "-m", commit_msg],
        ["git", "push", "origin", GITHUB_BRANCH],
    ]:
        r = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
        if r.returncode != 0:
            if "nothing to commit" in r.stdout + r.stderr:
                log("  Nothing to commit")
                return True
            log(f"  git error: {r.stderr.strip()}", "ERROR")
            return False
    log("  Pushed OK – Vercel deploying...")
    return True

# ── MAIN ──────────────────────────────────────────────────────────────
def publish(slug=None):
    log("=" * 60)
    log(f"  MANUAL PUBLISH  |  {SITE_DOMAIN}")
    log(f"  {date.today().strftime('%A %d %B %Y')}")
    log("=" * 60)

    # ── Resolve the markdown file ──────────────────────────────────────
    if slug:
        md_path = DOCS_DIR / f"{slug}.md"
        if not md_path.exists():
            log(f"  ERROR: docs/{slug}.md not found", "ERROR")
            sys.exit(1)
    else:
        md_path = find_newest_md()
        if not md_path:
            log("  ERROR: No markdown files found in docs/", "ERROR")
            sys.exit(1)
        slug = slug_from_filename(md_path)
        log(f"  Auto-detected newest article: {slug}")

    content  = md_path.read_text(encoding="utf-8")
    pub_date = get_pub_date(md_path)
    topic    = topic_from_slug(slug)

    log(f"  Slug    : {slug}")
    log(f"  PubDate : {pub_date}")
    log(f"  Words   : {len(content.split())}")

    # ── Ensure PUB_DATE header exists ─────────────────────────────────
    if not content.startswith("PUB_DATE:"):
        content = f"PUB_DATE: {pub_date.isoformat()}\n" + content
        md_path.write_text(content, encoding="utf-8")
        log("  PUB_DATE header added to markdown")

    # ── Hero image ────────────────────────────────────────────────────
    log("-- Fetching hero image...")
    image_meta = None
    try:
        from fetch_article_image import get_article_image
        image_meta = get_article_image(topic, slug)
        if image_meta:
            log(f"  Image OK: {image_meta.get('source','?')} – {image_meta.get('query','')}")
        else:
            log("  No hero image found", "WARN")
    except Exception as e:
        log(f"  Image step failed: {e}", "WARN")

    # ── Build article HTML ────────────────────────────────────────────
    log("-- Building article HTML...")
    try:
        from build_article import build_article_html
        slug_dir = BASE_DIR / slug
        slug_dir.mkdir(parents=True, exist_ok=True)
        html = build_article_html(topic, slug, content,
                                  pub_date=pub_date,
                                  image_meta=image_meta)
        (slug_dir / "index.html").write_text(html, encoding="utf-8")
        log(f"  Saved: {slug}/index.html")
    except Exception as e:
        log(f"  HTML build failed: {e}", "ERROR")
        sys.exit(1)

    # ── Rebuild homepage ──────────────────────────────────────────────
    log("-- Rebuilding homepage...")
    r = subprocess.run(["python", str(BASE_DIR / "build_homepage.py")],
                       cwd=BASE_DIR, capture_output=True, text=True)
    if r.returncode == 0:
        log("  Homepage OK")
    else:
        log(f"  Homepage error: {r.stderr.strip()}", "WARN")

    # ── Rebuild sitemap ───────────────────────────────────────────────
    log("-- Rebuilding sitemap...")
    r = subprocess.run(["python", str(BASE_DIR / "build_sitemap.py")],
                       cwd=BASE_DIR, capture_output=True, text=True)
    if r.returncode == 0:
        log("  Sitemap OK")
    else:
        log(f"  Sitemap error: {r.stderr.strip()}", "WARN")

    # ── Rebuild articles archive ──────────────────────────────────────
    log("-- Rebuilding articles archive...")
    r = subprocess.run(["python", str(BASE_DIR / "build_articles_page.py")],
                       cwd=BASE_DIR, capture_output=True, text=True)
    if r.returncode == 0:
        log("  Articles archive OK")
    else:
        log(f"  Articles archive error: {r.stderr.strip()}", "WARN")

    # ── Update article history (used by newsletter) ───────────────────
    history_path = STATE_DIR / "article_history.json"
    history = {"articles": []}
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    delivery = {
        "topic"    : topic,
        "filename" : f"{slug}.md",
        "slug"     : slug,
        "url"      : f"https://{SITE_DOMAIN}/{slug}/",
        "words"    : len(content.split()),
        "qa_status": "MANUAL",
        "published": datetime.now().isoformat(),
    }
    history.setdefault("articles", []).insert(0, delivery)
    history["articles"] = history["articles"][:30]
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    log("  Article history updated")

    # ── Git push ──────────────────────────────────────────────────────
    log("-- Pushing to GitHub...")
    git_push(f"auto: publish -- {topic[:50]}")

    # ── Done ──────────────────────────────────────────────────────────
    url = f"https://{SITE_DOMAIN}/{slug}/"
    log("=" * 60)
    log(f"  PUBLISHED: {url}")
    log("=" * 60)
    notify(f"Published: {topic[:50]}\n{url}")
    return True


if __name__ == "__main__":
    target_slug = sys.argv[1].strip("/") if len(sys.argv) > 1 else None
    publish(target_slug)
