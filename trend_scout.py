#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trend_scout.py
--------------
Runs BEFORE pipeline_v2.py every morning.

1. Searches BBC Money, Reddit r/UKPersonalFinance, MoneySavingExpert,
   Bank of England news, and Google Trends UK for hot topics today.
2. Asks Ollama to pick the single best topic for the blog.
3. If the topic is new, adds it permanently to pipeline_v2.py TOPICS list.
4. Injects it as the NEXT topic to be published (front of the queue).

Run order:
    python trend_scout.py && python pipeline_v2.py
"""

import os                # <<<‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑‑- 
import re, json, sys, time, requests
from datetime import date, datetime
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent
STATE_DIR = BASE_DIR / ".pipeline"
LOGS_DIR  = BASE_DIR / "logs"
STATE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

OLLAMA_URL  = "http://127.0.0.1:11434/api/chat"
SCOUT_MODEL = "phi3:mini"

# Ensure Ollama stores its models on the second drive
if not os.getenv("OLLAMA_HOME"):
    os.environ["OLLAMA_HOME"] = r"D:\ollama_data"
    Path(os.getenv("OLLAMA_HOME")).mkdir(parents=True, exist_ok=True)

# Sources to search -----------------------------------------------------------
SOURCES = [
    {
        "name": "BBC Money",
        "url" : "https://www.bbc.co.uk/news/business/market-data",
        "search": "https://www.bbc.co.uk/search?q=personal+finance+UK&filter=news",
    },
    {
        "name": "Reddit r/UKPersonalFinance",
        "url" : "https://www.reddit.com/r/UKPersonalFinance/hot.json?limit=10",
        "json": True,
    },
    {
        "name": "MoneySavingExpert",
        "url" : "https://www.moneysavingexpert.com/news/",
    },
    {
        "name": "Bank of England",
        "url" : "https://www.bankofengland.co.uk/news",
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; luispaiva-blog-scout/1.0)"
}

# ── LOGGING ────────────────────────────────────────────────────────────────
_log_path = LOGS_DIR / f"trend_scout_{date.today().isoformat()}.log"

def log(msg, level="INFO"):
    ts   = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    with open(_log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ── FETCH HEADLINES ---------------------------------------------------------
def fetch_source(source):
    """Return plain‑text headlines/titles from a source."""
    try:
        r = requests.get(source["url"], headers=HEADERS, timeout=15)
        r.raise_for_status()

        # Reddit JSON API
        if source.get("json"):
            data = r.json()
            posts = data.get("data", {}).get("children", [])
            titles = [p["data"]["title"] for p in posts if not p["data"].get("stickied")]
            log(f"  {source['name']}: {len(titles)} posts")
            return "\n".join(titles[:10])

        # Simple HTML scrape – pull <title>, <h1>, <h2>, <h3>
        text = r.text
        tags = re.findall(r'<(?:title|h[123])[^>]*>(.*?)</(?:title|h[123])>', text,
                          re.DOTALL | re.IGNORECASE)
        cleaned = []
        for t in tags:
            t = re.sub(r'<[^>]+>', '', t).strip()
            t = re.sub(r'\s+', ' ', t)
            if 10 < len(t) < 200:
                cleaned.append(t)
        log(f"  {source['name']}: {len(cleaned)} headlines")
        return "\n".join(cleaned[:15])
    except Exception as e:
        log(f"  {source['name']}: failed — {e}", "WARN")
        return ""

# ── LOAD EXISTING TOPICS ----------------------------------------------------
def load_existing_topics():
    """Read the TOPICS list from pipeline_v2.py."""
    pipeline = BASE_DIR / "pipeline_v2.py"
    text = pipeline.read_text(encoding="utf-8")
    m = re.search(r'TOPICS\s*=\s*\[(.*?)\]', text, re.DOTALL)
    if not m:
        return []
    raw = m.group(1)
    return re.findall(r'"([^"]+)"', raw)

def load_done_topics():
    done_path = STATE_DIR / "done_topics.txt"
    if not done_path.exists():
        return set()
    return set(done_path.read_text(encoding="utf-8").splitlines())

# ── ASK OLLAMA TO PICK BEST TOPIC -------------------------------------------
SCOUT_PROMPT = """You are a content strategist for luispaiva.co.uk — a UK personal finance blog.

Your job: read today's trending headlines from UK finance sources and pick the SINGLE best topic for a blog article TODAY.

RULES:
- Must be relevant to UK personal finance (savings, investing, ISAs, mortgages, credit cards, budgeting, pensions, tax, side‑income, banking, debt)
- Must be something a UK adult aged 25‑50 would search for RIGHT NOW
- Must NOT already be in the DONE TOPICS list
- Must NOT be breaking news or politics – focus on actionable money advice
- Output ONLY a JSON object, nothing else:
{
  "topic": "exact SEO‑friendly phrase",
  "reason": "one sentence why this is timely today",
  "is_new": true|false
}"""

def pick_trending_topic(headlines_text, existing_topics, done_topics):
    all_done = done_topics | set(existing_topics)

    user_msg = f"""TODAY'S TRENDING HEADLINES:
{headlines_text}

ALREADY DONE TOPICS (do NOT repeat):
{chr(10).join(sorted(all_done)[:30])}

EXISTING TOPICS IN PIPELINE (already planned):
{chr(10).join(sorted(existing_topics)[:20])}

Pick the SINGLE best topic to write about today."""
    payload = {
        "model": SCOUT_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": SCOUT_PROMPT},
            {"role": "user",   "content": user_msg},
        ],
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=120)
        r.raise_for_status()
        content = r.json()["message"]["content"].strip()
        m = re.search(r'\{.*?\}', content, re.DOTALL)
        if m:
            return json.loads(m.group())
        log(f"  Ollama response not valid JSON: {content[:200]}", "WARN")
    except Exception as e:
        log(f"  Ollama error: {e}", "ERROR")
    return None

# ── INJECT TOPIC INTO PIPELINE ---------------------------------------------
def add_topic_to_pipeline(topic):
    """Append a new topic line to the TOPICS list in pipeline_v2.py."""
    pipeline = BASE_DIR / "pipeline_v2.py"
    text = pipeline.read_text(encoding="utf-8")
    m = re.search(r'(TOPICS\s*=\s*\[)\s*\n', text)
    if not m:
        log("  Could not find TOPICS list in pipeline_v2.py", "ERROR")
        return False
    insert_at = m.end()
    new_line = f'    "{topic}",  # trending {date.today().isoformat()}\n'
    text = text[:insert_at] + new_line + text[insert_at:]
    pipeline.write_text(text, encoding="utf-8")
    log(f"  Added new topic to pipeline_v2.py: {topic}")
    return True

def inject_as_next_topic(topic):
    (STATE_DIR / "next_topic.txt").write_text(topic, encoding="utf-8")
    log(f"  Queued as next topic for the next pipeline run: {topic}")

# ── MAIN --------------------------------------------------------------------
def run():
    log("=" * 60)
    log("  TREND SCOUT")
    log(f"  {date.today().strftime('%A %d %B %Y')}")
    log("=" * 60)

    # -----------------------------------------------------------------
    # 1️⃣  Avoid re‑scouting the same day
    # -----------------------------------------------------------------
    scouted_path = STATE_DIR / f"trend_scouted_{date.today().isoformat()}.txt"
    if scouted_path.exists():
        already = scouted_path.read_text(encoding="utf-8").strip()
        log(f"  Already scouted today: {already}")
        log("  Skipping – pipeline will use this topic")
        return True

    # -----------------------------------------------------------------
    # 2️⃣  Fetch headlines from all sources
    # -----------------------------------------------------------------
    log("-- Fetching headlines...")
    all_headlines = []
    for src in SOURCES:
        txt = fetch_source(src)
        if txt:
            all_headlines.append(f"=== {src['name']} ===\n{txt}")
        time.sleep(1)   # polite pause

    if not all_headlines:
        log("  No headlines fetched – aborting", "WARN")
        return False

    headlines_blob = "\n\n".join(all_headlines)

    # -----------------------------------------------------------------
    # 3️⃣  Load state
    # -----------------------------------------------------------------
    existing_topics = load_existing_topics()
    done_topics     = load_done_topics()
    log(f"  Existing topics: {len(existing_topics)} | Done topics: {len(done_topics)}")

    # -----------------------------------------------------------------
    # 4️⃣  Ask Ollama for the best today
    # -----------------------------------------------------------------
    log("-- Asking Ollama to pick the best topic...")
    result = pick_trending_topic(headlines_blob, existing_topics, done_topics)

    if not result or not result.get("topic"):
        log("  No topic selected – aborting", "WARN")
        return False

    topic   = result["topic"].strip().lower()
    reason  = result.get("reason", "")
    is_new  = result.get("is_new", True)

    log(f"  Picked topic: {topic}")
    log(f"  Reason: {reason}")
    log(f"  Is new: {is_new}")

    # -----------------------------------------------------------------
    # 5️⃣  Add to pipeline if it truly is new
    # -----------------------------------------------------------------
    if is_new and topic not in existing_topics:
        add_topic_to_pipeline(topic)

    # -----------------------------------------------------------------
    # 6️⃣  Queue as next topic for the pipeline
    # -----------------------------------------------------------------
    inject_as_next_topic(topic)

    # -----------------------------------------------------------------
    # 7️⃣  Mark today as scouted
    # -----------------------------------------------------------------
    scouted_path.write_text(topic, encoding="utf-8")
    log("=" * 60)
    log(f"  TREND SCOUT COMPLETE – today's topic: {topic}")
    log("=" * 60)
    return True

if __name__ == "__main__":
    run()
