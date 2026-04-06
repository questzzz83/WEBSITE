#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
strategy_room.py
Weekly multi-agent brainstorming session for luispaiva.co.uk.
Agents research trending UK finance topics, debate angles, and produce
a strategy file with recommended article ideas for the week.

Run manually:  python strategy_room.py
Auto-run:      Monday 08:00 via Windows Task Scheduler
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

# Search queries covering the full breadth of UK personal finance
SEARCH_QUERIES = [
    "UK personal finance news April 2026",
    "Bank of England interest rate decision 2026",
    "HMRC tax changes UK 2026",
    "UK mortgage rates April 2026",
    "UK savings accounts best rates 2026",
    "UK cost of living April 2026",
    "UK benefits Universal Credit changes 2026",
    "UK pension changes 2026",
    "UK credit card debt interest rates 2026",
    "UK side hustle income tax rules 2026",
]

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
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        r = requests.get(url, headers=headers, timeout=10)
        snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', r.text)
        snippets = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets[:6]]
        titles   = re.findall(r'<a class="result__a"[^>]*>(.*?)</a>', r.text)
        titles   = [re.sub(r'<[^>]+>', '', t).strip() for t in titles[:6]]
        combined = []
        for title, snippet in zip(titles, snippets):
            if title and snippet:
                combined.append(f"  • {title}: {snippet}")
            elif snippet:
                combined.append(f"  • {snippet}")
        return "\n".join(combined)
    except Exception as e:
        log(f"  Search failed for '{query}': {e}", "WARN")
        return ""

def get_done_topics():
    """Read done_topics.txt — the authoritative list of published/planned topics."""
    done_file = BASE_DIR / "done_topics.txt"
    topics = []
    if done_file.exists():
        for line in done_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                topics.append(line)
    # Also sweep docs/ for anything not yet in done_topics.txt
    for md in DOCS_DIR.glob("*.md"):
        if md.name in {".gitkeep", "index.md", "privacy.md", "about.md"}:
            continue
        slug_topic = md.stem.replace("-", " ")
        if slug_topic not in topics:
            topics.append(slug_topic)
    return topics

def get_seasonal_context():
    """Return relevant seasonal/calendar context for today's date."""
    today = date.today()
    month = today.month
    day   = today.day
    contexts = []

    if month == 3 and day >= 20:
        contexts.append("End of tax year approaching (5 April) — ISA allowance, pension contributions, capital gains")
    if month == 4 and day <= 10:
        contexts.append("New tax year just started — ISA allowances reset, new thresholds, PAYE code changes")
    if month in (1, 2):
        contexts.append("Self-assessment season — 31 Jan deadline recently passed or approaching")
    if month in (10, 11):
        contexts.append("Autumn Budget season — tax, benefits, and allowance changes expected")
    if month == 3:
        contexts.append("Spring Statement period — OBR forecasts and potential policy announcements")
    if month in (4, 5):
        contexts.append("Spring financial review — good time to switch savings accounts, review pensions")
    if month in (11, 12):
        contexts.append("Christmas spending pressure, gift budgeting, January debt hangover preparation")
    if month == 1:
        contexts.append("New Year financial resolutions — budgeting, debt payoff, saving goals")
    if month in (8, 9):
        contexts.append("Back to school costs, summer debt recovery, energy bill season approaching")

    return "\n".join(f"- {c}" for c in contexts) if contexts else "- No major seasonal finance events this week"

# ── Strategy Room Agents ───────────────────────────────────────────────────────

def run_scout():
    """Scout researches what's trending in UK personal finance right now."""
    log("-- Scout: Researching trending UK finance topics...")

    research_blocks = []
    for query in SEARCH_QUERIES:
        results = search_trending(query)
        if results:
            research_blocks.append(f"QUERY: {query}\n{results}")
        time.sleep(0.5)

    research = "\n\n".join(research_blocks) if research_blocks else \
        "Search unavailable — use model knowledge of UK finance trends for April 2026."

    done_topics = get_done_topics()
    seasonal    = get_seasonal_context()
    today_str   = date.today().strftime("%d %B %Y")

    system = """You are Scout, a sharp UK personal finance research analyst for luispaiva.co.uk.
Your job: identify the 10 most timely, high-demand UK personal finance topics people are searching for RIGHT NOW.
Focus on what real UK adults aged 25-55 are worried about or making decisions on this specific week.
Be concrete — mention actual UK providers, rates, policy deadlines, and real numbers where possible.
Reject vague or evergreen topics. Every suggestion must feel urgent and specific to this moment."""

    prompt = f"""Today is {today_str}.

SEASONAL CONTEXT:
{seasonal}

WEB RESEARCH:
{research}

ALREADY PUBLISHED — do not suggest these:
{chr(10).join('- ' + t for t in done_topics)}

Identify the 10 best UK personal finance topics to write about THIS WEEK.

For each topic:
TOPIC 1: [topic as a natural search phrase]
Timely because: [concrete reason specific to this week]
Intent: [Informational / Transactional / Navigational]
Affiliate potential: [Yes / No / Maybe]

(repeat for all 10 topics)"""

    result = call_model(MODELS["scout"], system, prompt)
    log(f"  Scout done ({len(result.split()) if result else 0} words)")
    return result


def run_strategist(scout_report):
    """Strategist scores and selects the best 5 topics with full briefs."""
    log("-- Strategist: Scoring and selecting top topics...")

    done_topics = get_done_topics()
    today_str   = date.today().strftime("%d %B %Y")

    system = """You are Strategist, the content director for luispaiva.co.uk — a UK personal finance blog.
Your job: select and score the 5 best topics from Scout's list.
Scoring criteria: reader demand, affiliate potential, UK specificity, not yet published, SEO opportunity.
For each selected topic produce a full content brief the editor can hand directly to a writer."""

    prompt = f"""Today is {today_str}.

Scout's research:
{scout_report}

Already published (must not duplicate):
{chr(10).join('- ' + t for t in done_topics)}

Select the TOP 5 article opportunities. Rank them by priority (1 = publish this week).

For each:

TOPIC [n]:
Title: [exact H1 as it would appear on site]
Slug: [url-slug-format]
Target keyword: [primary keyword, 3-6 words]
Secondary keywords: [2-3 related phrases, comma separated]
Why now: [one concrete sentence on timeliness]
Reader pain point: [what problem this solves]
Affiliate angle: [specific UK products/providers to recommend]
Monetisation: High / Medium / Low
SEO difficulty: Easy / Medium / Hard
Priority: [1-5]

(repeat for all 5)"""

    result = call_model(MODELS["strategist"], system, prompt)
    log(f"  Strategist done ({len(result.split()) if result else 0} words)")
    return result


def run_writer_angles(strategy_report):
    """Writer adds hooks, FAQ suggestions, and meta descriptions."""
    log("-- Writer: Adding hooks, FAQs, and meta descriptions...")

    system = """You are Writer, the content writer for luispaiva.co.uk.
Your job: for each proposed article, produce the creative brief elements.
Be specific — use real UK figures, actual provider names, and concrete reader scenarios.
Think about what makes someone click on a Google result over MoneySavingExpert or MoneySuperMarket."""

    prompt = f"""For each proposed article below, provide:

1. Opening hook (first 1-2 sentences — must immediately grab a UK reader's attention)
2. Unique angle (our specific take that differentiates from MSE/MoneySuperMarket)
3. Three FAQ questions (phrased exactly as readers would type them into Google)
4. Suggested H2 structure (4-6 section headings in logical order)
5. Meta description (max 155 characters, includes primary keyword, compelling click-through)

ARTICLES:
{strategy_report}

Be UK-specific throughout. Reference actual providers, rates, and regulations."""

    result = call_model(MODELS["writer"], system, prompt)
    log(f"  Writer done ({len(result.split()) if result else 0} words)")
    return result


def run_gatekeeper(all_reports):
    """Gatekeeper produces the final clean strategy document."""
    log("-- Gatekeeper: Producing final strategy document...")

    today_str = date.today().strftime("%d %B %Y")
    week_num  = date.today().isocalendar()[1]
    seasonal  = get_seasonal_context()

    system = """You are Gatekeeper, the editorial director for luispaiva.co.uk.
Your job: synthesise all agent inputs into a clean, actionable weekly strategy document.
Be critical — only include what is genuinely useful. Cut anything vague, generic, or already covered.
Note: the pipeline writer agent is disabled. Articles are written manually by the editor using Claude.
This document is used directly by the editor to decide what to write each day this week."""

    prompt = f"""Today is {today_str} (Week {week_num}).

SEASONAL CONTEXT:
{seasonal}

ALL AGENT REPORTS:
{all_reports}

Produce the final strategy document in this EXACT format — do not add extra sections:

# Strategy Room — {today_str}

## Market Pulse
[5-6 bullet points on what's actually happening in UK finance this week — rates, news, policy, deadlines]

## Content Gaps Identified
[3-4 topics readers are searching for that we haven't covered — one sentence each]

## This Week's Articles

### 🔴 Priority 1 — [Article Title]
- **Slug:** `[slug-format]`
- **Keyword:** [primary keyword]
- **Why this week:** [one concrete sentence]
- **Hook:** [opening 1-2 sentences of the article]
- **Angle:** [what makes our take different from MSE/Uswitch]
- **H2 structure:** [H2 1] / [H2 2] / [H2 3] / [H2 4] / [H2 5]
- **FAQs:** [Q1] | [Q2] | [Q3]
- **Affiliates:** [specific UK products/providers]
- **Meta:** [≤155 char meta description]

### 🟡 Priority 2 — [Article Title]
[same format]

### 🟢 Priority 3 — [Article Title]
[same format]

## Backlog
- **[Topic]** — [why it's good but not urgent this week]
- **[Topic]** — [reason]
- **[Topic]** — [reason]

## Rejected
- **[Topic]** — [one-line reason]
- **[Topic]** — [reason]

---
*Strategy Room — {today_str} | Writer agent disabled — manual authoring with Claude*"""

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
    week_key   = f"strategy_week_{date.today().isocalendar()[1]}"
    state_file = STATE_DIR / "strategy_state.json"
    state = {}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    if state.get(week_key) == "done" and "--force" not in sys.argv:
        log("  Already ran this week — use --force to override")
        latest = STATE_DIR / "strategy_latest.md"
        if latest.exists():
            log(f"  Latest: {latest}")
        return

    # Run agents
    scout_report = run_scout()
    if not scout_report:
        log("  Scout failed -- aborting", "ERROR")
        notify("Strategy Room failed at Scout stage")
        return

    strategy_report = run_strategist(scout_report)
    if not strategy_report:
        log("  Strategist failed -- aborting", "ERROR")
        notify("Strategy Room failed at Strategist stage")
        return

    writer_angles = run_writer_angles(strategy_report)
    if not writer_angles:
        log("  Writer failed -- aborting", "ERROR")
        notify("Strategy Room failed at Writer stage")
        return

    all_reports = f"""=== SCOUT RESEARCH ===
{scout_report}

=== STRATEGIST SELECTION & SCORING ===
{strategy_report}

=== WRITER ANGLES, HOOKS & META ===
{writer_angles}"""

    final_doc = run_gatekeeper(all_reports)
    if not final_doc:
        log("  Gatekeeper failed -- aborting", "ERROR")
        notify("Strategy Room failed at Gatekeeper stage")
        return

    # Save
    today_str   = date.today().isoformat()
    out_path    = STATE_DIR / f"strategy_{today_str}.md"
    latest_path = STATE_DIR / "strategy_latest.md"

    out_path.write_text(final_doc, encoding="utf-8")
    latest_path.write_text(final_doc, encoding="utf-8")
    log(f"  Saved: .pipeline/strategy_{today_str}.md")
    log(f"  Saved: .pipeline/strategy_latest.md")

    # Mark week as done
    state[week_key] = "done"
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    log("=" * 60)
    log("  STRATEGY ROOM COMPLETE")
    log("=" * 60)

    # Telegram summary
    recs = re.findall(r"Priority \d+ — (.+)", final_doc)
    rec_list = "\n".join(f"• {r.strip()}" for r in recs[:3])
    notify(
        f"📋 Strategy Room — {date.today().strftime('%d %b %Y')}\n\n"
        f"This week's priorities:\n{rec_list}\n\n"
        f"Full doc: .pipeline/strategy_latest.md"
    )

    # Preview first 35 lines
    preview = "\n".join(final_doc.split("\n")[:35])
    log(f"\nPREVIEW:\n{preview}\n[...]\n")

    return final_doc


if __name__ == "__main__":
    run_strategy_room()
