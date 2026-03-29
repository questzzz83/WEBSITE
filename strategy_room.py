#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
strategy_room.py
Weekly multi-agent brainstorming session for luispaiva.co.uk.
Agents research trending UK finance topics, debate angles, and produce
a strategy file with recommended article ideas for the week.

Run manually:  python strategy_room.py
Auto-run:      Monday 08:00 via OpenClaw cron
Output:        .pipeline/strategy_YYYY-MM-DD.md
               .pipeline/strategy_latest.md (always latest)
"""

import re, json, time, requests, sys
from pathlib import Path as _Path
try:
    _nm_path = _Path(__file__).parent / "notify.py"
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("notify", _nm_path)
    _nm = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_nm)
    notify = _nm.notify
except Exception:
    def notify(msg): pass
from datetime import date, datetime
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR   = Path(__file__).parent
DOCS_DIR   = BASE_DIR / "docs"
STATE_DIR  = BASE_DIR / ".pipeline"
LOGS_DIR   = BASE_DIR / "logs"
STATE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

OLLAMA_URL  = "http://127.0.0.1:11434/api/chat"
SITE_DOMAIN = "www.luispaiva.co.uk"
SITE_NICHE  = "UK personal finance"

MODELS = {
    "scout":      "llama3.1:8b",
    "strategist": "qwen2.5-coder:7b",
    "writer":     "llama3.1:8b",
    "gatekeeper": "llama3.1:8b",
}

# ── Logging ────────────────────────────────────────────────────────────────────

log_path = LOGS_DIR / f"strategy_{date.today().isoformat()}.log"

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ── Ollama ─────────────────────────────────────────────────────────────────────

def call_model(model, system_prompt, user_prompt, max_retries=2):
    payload = {
        "model": model,
        "stream": False,
        "options": {"num_ctx": 8192, "num_gpu": 12, "temperature": 0.7},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ]
    }
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.post(OLLAMA_URL, json=payload, timeout=180)
            r.raise_for_status()
            return r.json()["message"]["content"].strip()
        except Exception as e:
            log(f"  Model {model} attempt {attempt} failed: {e}", "WARN")
            if attempt < max_retries:
                time.sleep(5)
    return None

# ── Web Research ───────────────────────────────────────────────────────────────

def search_trending(query):
    """Search DuckDuckGo for trending UK finance topics."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        r = requests.get(url, headers=headers, timeout=10)
        # Extract snippets
        snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', r.text)
        snippets = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets[:8]]
        return "\n".join(f"- {s}" for s in snippets if s)
    except Exception as e:
        log(f"  Search failed: {e}", "WARN")
        return ""

def get_existing_topics():
    """Get list of already published article topics."""
    topics = []
    for md in DOCS_DIR.glob("*.md"):
        if md.name in {".gitkeep", "index.md"}:
            continue
        slug = md.stem.replace("-", " ")
        topics.append(slug)
    return topics

# ── Strategy Room Agents ───────────────────────────────────────────────────────

def run_scout():
    """Scout researches what's trending in UK personal finance right now."""
    log("-- Scout: Researching trending UK finance topics...")

    queries = [
        "UK personal finance news 2026",
        "UK money saving tips trending 2026",
        "UK interest rates savings accounts 2026",
        "UK budget tax changes 2026",
        "UK mortgage rates March 2026",
    ]

    research = ""
    for q in queries:
        results = search_trending(q)
        if results:
            research += f"\nSearch: {q}\n{results}\n"

    if not research:
        research = "Search unavailable - using model knowledge of UK finance trends."

    system = """You are Scout, a UK personal finance research agent.
Your job: identify the top 8 most relevant and timely UK personal finance topics RIGHT NOW.
Focus on topics that real UK adults are actively searching for or worried about in 2026.
Be specific - include actual UK products, rates, providers, and policy changes."""

    prompt = f"""Based on this research, identify the 8 most relevant UK personal finance topics for March/April 2026.

RESEARCH:
{research}

EXISTING PUBLISHED ARTICLES (do not suggest these):
{chr(10).join('- ' + t for t in get_existing_topics())}

Output format - TRENDING TOPICS:
1. [Topic] - [Why it's relevant now, one sentence]
2. [Topic] - [Why it's relevant now, one sentence]
...8 topics total"""

    result = call_model(MODELS["scout"], system, prompt)
    log(f"  Scout done ({len(result.split()) if result else 0} words)")
    return result

def run_strategist(scout_report):
    """Strategist analyses gaps and selects the best 5 topics."""
    log("-- Strategist: Analysing gaps and opportunities...")

    system = """You are Strategist, a content strategy expert for luispaiva.co.uk.
Your job: select the 5 best article topics from the scout's research.
Criteria: high search volume, not yet covered, UK-specific, actionable for readers, good affiliate potential."""

    prompt = f"""Scout's trending topic research:
{scout_report}

Select the TOP 5 article opportunities. For each provide:
- Title (as it would appear as an H1)
- Target keyword (what people search for)
- Why now (one sentence on timeliness)
- Affiliate angle (what UK products/services to recommend)
- Estimated reader value: High/Medium

Format:
TOPIC 1:
Title: [title]
Keyword: [keyword]
Why now: [reason]
Affiliate: [products]
Value: [High/Medium]

(repeat for 5 topics)"""

    result = call_model(MODELS["strategist"], system, prompt)
    log(f"  Strategist done ({len(result.split()) if result else 0} words)")
    return result

def run_writer_angles(strategy_report):
    """Writer suggests creative angles and hooks for each topic."""
    log("-- Writer: Brainstorming angles and hooks...")

    system = """You are Writer, the content writer for luispaiva.co.uk.
Your job: for each proposed topic, suggest a compelling angle and opening hook.
Think about what will make UK readers click and keep reading."""

    prompt = f"""For each of these proposed topics, suggest:
- A compelling article angle (the unique take)
- An opening hook sentence (first line that grabs attention)
- One real UK example or statistic to open with

TOPICS:
{strategy_report}

Keep each suggestion concise - 2-3 sentences per topic."""

    result = call_model(MODELS["writer"], system, prompt)
    log(f"  Writer done ({len(result.split()) if result else 0} words)")
    return result

def run_gatekeeper(all_reports):
    """Gatekeeper reviews and produces the final strategy document."""
    log("-- Gatekeeper: Producing final strategy document...")

    system = """You are Gatekeeper, the editorial director for luispaiva.co.uk.
Your job: review all agent inputs and produce a clean, actionable strategy document.
Be critical - reject weak ideas, keep only what will genuinely help UK readers."""

    today = date.today().strftime("%d %B %Y")

    prompt = f"""Review the following research and brainstorming from our agents.
Produce a final strategy document for the week of {today}.

AGENT REPORTS:
{all_reports}

Output this exact format:

# Strategy Room - {today}

## Trending This Week
[3-5 bullet points on what's hot in UK finance right now]

## Content Gaps Identified
[3-5 topics we haven't covered that readers are searching for]

## Recommended Articles This Week
[Top 3 article recommendations, ranked by priority]

### 1. [Article Title]
- **Keyword:** [target keyword]
- **Why now:** [one sentence]
- **Hook:** [opening sentence]
- **Affiliate potential:** [products to mention]
- **Priority:** High

### 2. [Article Title]
[same format]

### 3. [Article Title]
[same format]

## Ideas for Later
[2-3 good ideas that aren't urgent right now]

## Rejected Ideas
[Ideas that were considered but rejected, with one-line reason]

---
*Generated by Strategy Room agents on {today}*"""

    result = call_model(MODELS["gatekeeper"], system, prompt)
    log(f"  Gatekeeper done ({len(result.split()) if result else 0} words)")
    return result

# ── Main ───────────────────────────────────────────────────────────────────────

def run_strategy_room():
    log("=" * 60)
    log(f"  STRATEGY ROOM  |  {SITE_DOMAIN}")
    log(f"  {date.today().strftime('%A %d %B %Y')}")
    log("=" * 60)

    # Check if already ran this week
    week_key = f"strategy_week_{date.today().isocalendar()[1]}"
    state_file = STATE_DIR / "strategy_state.json"
    state = {}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    if state.get(week_key) == "done" and "--force" not in sys.argv:
        log("  Already ran this week -- use --force to override")
        return

    # Run agents
    scout_report = run_scout()
    if not scout_report:
        log("  Scout failed -- aborting", "ERROR")
        return

    strategy_report = run_strategist(scout_report)
    if not strategy_report:
        log("  Strategist failed -- aborting", "ERROR")
        return

    writer_angles = run_writer_angles(strategy_report)
    if not writer_angles:
        log("  Writer failed -- aborting", "ERROR")
        return

    all_reports = f"""SCOUT RESEARCH:
{scout_report}

STRATEGIST SELECTION:
{strategy_report}

WRITER ANGLES:
{writer_angles}"""

    final_doc = run_gatekeeper(all_reports)
    if not final_doc:
        log("  Gatekeeper failed -- aborting", "ERROR")
        return

    # Save
    today_str = date.today().isoformat()
    out_path = STATE_DIR / f"strategy_{today_str}.md"
    latest_path = STATE_DIR / "strategy_latest.md"

    out_path.write_text(final_doc, encoding="utf-8")
    latest_path.write_text(final_doc, encoding="utf-8")

    log(f"  Saved: .pipeline/strategy_{today_str}.md")

    # Mark as done
    state[week_key] = "done"
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    log("=" * 60)
    log("  STRATEGY ROOM COMPLETE")
    log("=" * 60)

    # Notify
    recs = re.findall(r"### \d+\. (.+)", final_doc)
    rec_list = "\n".join(f"- {r}" for r in recs[:3])
    notify(f"Strategy Room done. This week's topics:\n{rec_list}")

    # Print preview
    lines = final_doc.split("\n")
    log("\n" + "\n".join(lines[:20]))

    return final_doc


if __name__ == "__main__":
    run_strategy_room()
