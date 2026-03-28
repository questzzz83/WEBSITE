# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Autonomous Blog Pipeline v2 -- luispaiva.co.uk
Agents: Scout -> Strategist -> Writer -> Gatekeeper -> Courier (Fridays)
Run: python pipeline_v2.py
"""

import os, re, json, time, subprocess, requests
from datetime import datetime, date
from pathlib import Path
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# -- CONFIG --------------------------------------------------------------------

SITE_DOMAIN     = "www.luispaiva.co.uk"
GITHUB_USERNAME = "questzzz83"
GITHUB_REPO     = "WEBSITE"
GITHUB_BRANCH   = "main"
OLLAMA_URL      = "http://127.0.0.1:11434/api/chat"

MODELS = {
    "scout"      : "llama3.1:8b",
    "strategist" : "qwen2.5-coder:7b",
    "writer"     : "qwen2.5-coder:7b",
    "gatekeeper" : "llama3.1:8b",
    "courier"    : "llama3.1:8b",
}

BEEHIIV_ENABLED        = False
BEEHIIV_API_KEY        = "YOUR_API_KEY_HERE"
BEEHIIV_PUBLICATION_ID = "YOUR_PUBLICATION_ID_HERE"
BEEHIIV_SEND_AT        = "immediate"

MAX_QA_RETRIES  = 3
TARGET_LO       = 1500
TARGET_HI       = 2500

BASE_DIR  = Path(__file__).parent
DOCS_DIR  = BASE_DIR / "docs"
STATE_DIR = BASE_DIR / ".pipeline"
LOGS_DIR  = BASE_DIR / "logs"
NL_DIR    = BASE_DIR / "newsletters"

for _d in [DOCS_DIR, STATE_DIR, LOGS_DIR, NL_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# -- TOPICS -------------------------------------------------------------------

TOPICS = [
    "best high yield savings accounts UK 2025",
    "best easy access savings accounts UK 2025",
    "best fixed rate savings bonds UK 2025",
    "how to save 10000 pounds in one year UK",
    "how to build an emergency fund from scratch UK",
    "premium bonds vs savings accounts UK which is better",
    "how to save money on a low income UK",
    "how to save for a house deposit UK first time buyer",
    "best regular savings accounts UK 2025",
    "index funds vs ETFs for beginners UK",
    "how to start investing with 100 pounds UK",
    "best stocks and shares ISA accounts UK 2025",
    "best investment platforms UK for beginners 2025",
    "how to invest in the S&P 500 from UK",
    "Vanguard vs Fidelity vs Hargreaves Lansdown UK comparison",
    "best global index funds to buy UK 2025",
    "how to build a diversified investment portfolio UK",
    "pound cost averaging explained UK beginners guide",
    "dividend investing for beginners UK 2025",
    "best stocks and shares ISA UK 2025 full comparison",
    "lifetime ISA vs help to buy ISA which is better UK",
    "cash ISA vs stocks and shares ISA which should you choose",
    "ISA allowance 2025 UK how to use it wisely",
    "best junior ISA accounts UK 2025",
    "pension vs ISA which should you prioritise UK",
    "best cashback credit cards for everyday spending UK",
    "best balance transfer credit cards UK 2025",
    "best travel credit cards UK no foreign fees 2025",
    "best 0 percent purchase credit cards UK 2025",
    "how to use a credit card responsibly UK beginners guide",
    "how to improve your credit score in 90 days UK",
    "what is a good credit score UK Experian Equifax TransUnion",
    "how to check your credit score for free UK 2025",
    "how to build credit from scratch UK no credit history",
    "how to pay off credit card debt fast UK",
    "debt avalanche vs debt snowball which is better UK",
    "how to get out of your overdraft permanently UK",
    "best personal loans UK low interest 2025",
    "how to consolidate debt UK step by step guide",
    "student loan UK repayment explained plan 1 plan 2 plan 5",
    "how to get a mortgage UK first time buyer complete guide",
    "fixed rate vs variable rate mortgage UK which is better",
    "how much can you borrow for a mortgage UK 2025",
    "best mortgage brokers UK 2025 free vs paid",
    "how to remortgage UK step by step guide 2025",
    "stamp duty UK 2025 how much will you pay",
    "how to create a monthly budget that actually works UK",
    "50 30 20 budget rule UK does it work",
    "best budgeting apps UK 2025",
    "zero based budgeting UK complete guide",
    "how to save money on groceries UK practical tips",
    "how to cut household bills UK 2025",
    "how to save money on energy bills UK 2025",
    "how to do a no spend month UK complete guide",
    "passive income ideas that actually work UK 2025",
    "how to negotiate a higher salary UK step by step",
    "best side hustles UK 2025 that actually pay",
    "how to make money online UK legitimate ways 2025",
    "best cashback sites UK 2025 TopCashback vs Quidco",
    "how does a workplace pension work UK explained",
    "how much should you put in your pension UK by age",
    "self invested personal pension SIPP UK complete guide",
    "state pension UK 2025 how much will you get",
    "how early retirement works UK FIRE movement explained",
    "how much do you need to retire UK 2025 honest answer",
    "how does income tax work UK 2025 simple explanation",
    "how to do your self assessment tax return UK 2025",
    "capital gains tax UK 2025 how to reduce your bill",
    "how to claim tax back UK PAYE employees guide",
    "tax on savings interest UK 2025 what you need to know",
    "best life insurance UK 2025 how to choose",
    "income protection insurance UK is it worth it",
    "best home insurance UK 2025 how to save money",
    "best car insurance UK 2025 how to get cheapest quote",
    "best current accounts UK 2025 with switching bonuses",
    "best online banks UK 2025 Monzo Starling Revolut compared",
    "Monzo vs Starling which is better UK 2025",
    "best business bank accounts UK for sole traders 2025",
]

# -- SYSTEM PROMPTS ------------------------------------------------------------

PROMPTS = {

"scout": """You are Scout, a research agent for a UK personal finance blog at luispaiva.co.uk.
You receive a topic. You return a research brief. Nothing else.

Output ONLY this exact markdown -- no preamble, no sign-off:

# BRIEF
## TOPIC
[restate topic in 10 words max]
## READER INTENT
[one sentence -- what problem is the reader solving?]
## PRIMARY KEYWORD
[best SEO keyword -- must appear verbatim in the H1 title]
## SECONDARY KEYWORDS
- [keyword]
- [keyword]
- [keyword]
- [keyword]
## ARTICLE ANGLE
[one sentence -- what makes this article different from every other one on this topic?]
## STRUCTURE
- H2: [heading]
- H2: [heading]
- H2: [heading]
- H2: [heading]
- H2: [heading]
- H2: [heading]
## AFFILIATE OPPORTUNITIES
- Name: [real UK product] | URL: [real URL] | Why: [one sentence]
- Name: [real UK product] | URL: [real URL] | Why: [one sentence]
- Name: [real UK product] | URL: [real URL] | Why: [one sentence]
## KEY FACTS
- [UK-specific stat with source name]
- [UK-specific stat with source name]
- [UK-specific stat with source name]
## TONE NOTES
[2 sentences on voice and style for this specific topic]""",

"strategist": """You are Strategist, a content architect for a UK personal finance blog at luispaiva.co.uk.
You receive a research brief. You return an article skeleton. Nothing else.

Rules:
- H1 must be <=60 characters and contain the primary keyword exactly
- META description: 150-160 characters, contains primary keyword
- Each H2 gets a DIRECTIVE comment with: Goal, Angle, Tone, Words, Must, Avoid
- Place [AFFILIATE:1] [AFFILIATE:2] [AFFILIATE:3] where product links belong
- Place [TABLE] once in the middle third with column headers specified
- Place [CTA] at the very end

Output ONLY the skeleton in markdown. No preamble. No sign-off.""",

"writer": """You are Writer, a content writer for luispaiva.co.uk -- a UK personal finance blog.
Voice: like a financially-savvy friend giving honest advice over coffee.
You receive a brief and skeleton. You return the complete article. Nothing else.

RULES:
1. Total words: 1500-2500 (count carefully)
2. Fill every DIRECTIVE block then delete the comment
3. Replace [AFFILIATE:N] with real markdown links: [Product Name](https://url)
4. Replace [TABLE] with a markdown table (min 4 columns, 5 data rows, real UK data)
5. Replace [CTA] with a 2-3 sentence friendly call-to-action
6. Primary keyword in: H1, first sentence, at least 2 H2s
7. Paragraphs: 2-3 sentences max
8. UK-specific: GBP signs, real UK providers, UK rates
9. Final line must be exactly:
   *Affiliate disclosure: This article contains affiliate links. We may earn a small commission at no extra cost to you. Always do your own research before making financial decisions.*

When fixing after QA FAIL:
- Fix only what failed -- do not rewrite passing sections
- Increment <!-- version: N --> at top

Output ONLY the article. Nothing before it. Nothing after it.""",

"gatekeeper": """You are Gatekeeper, a QA agent for luispaiva.co.uk. You are strict and impartial.
You receive a brief and article. You return ONLY this exact format:

STATUS: PASS | FAIL
CYCLE: [N]
WORD COUNT: [exact]

CHECKS:
[OK or FAIL] Word count 1500-2500: [actual]
[OK or FAIL] H1 contains primary keyword: [quote both]
[OK or FAIL] Primary keyword in first sentence: yes/no
[OK or FAIL] No DIRECTIVE comments remaining: yes/no
[OK or FAIL] No [AFFILIATE:N] placeholders: yes/no
[OK or FAIL] No [TABLE] placeholder: yes/no
[OK or FAIL] No [CTA] placeholder: yes/no
[OK or FAIL] Comparison table present (>=4 cols, >=5 rows): yes/no
[OK or FAIL] Affiliate disclaimer at end: yes/no
[OK or FAIL] No broken markdown links: yes/no
[OK or FAIL] Paragraphs <=3 sentences: yes/no
[OK or FAIL] UK-specific content (GBP signs, UK providers): yes/no

ISSUES:
[each FAIL with exact problem and exact fix needed]
[if PASS: None]

VERDICT: [one sentence]

FAIL if ANY check is FAIL. PASS only if ALL are OK.""",

"courier": """You are Courier, the newsletter writer for luispaiva.co.uk.
Every Friday you write "The Friday Money Brief" -- one short email, under 450 words.
Tone: a smart friend texting you the week's best money tip. Warm, direct, no fluff.

You receive a list of this week's articles. Pick the most compelling as the lead.

Output ONLY the content between the markers:

---BRIEF START---
SUBJECT: [max 50 chars -- factual, no clickbait]
PREVIEW: [max 90 chars -- continues subject naturally]

---

Hi [FIRST_NAME],

[HOOK -- one punchy sentence with the most interesting UK money fact from the lead article]

[BRIDGE -- one sentence connecting hook to why the reader should care]

**[Lead article title as bold link: [Title](URL)]**

[3-4 sentences on the key insight. One specific UK number or rate. End with reason to click.]

-> [Read the full guide](URL)

---

**Also this week:**
- [Article 2 as link](URL) -- [one sentence why it matters]
- [Article 3 as link](URL) -- [one sentence why it matters]

---

Until next Friday,
Luis

*Sent because you subscribed at luispaiva.co.uk.
[Unsubscribe]() | [Privacy Policy](https://luispaiva.co.uk/privacy)*

---BRIEF END---""",
}

# -- HELPERS -------------------------------------------------------------------

_log_path = LOGS_DIR / f"pipeline_{date.today().isoformat()}.log"

def log(msg, level="INFO"):
    ts   = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    with open(_log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def state_read(key):
    p = STATE_DIR / f"{key}.txt"
    return p.read_text(encoding="utf-8").strip() if p.exists() else ""

def state_write(key, value):
    (STATE_DIR / f"{key}.txt").write_text(value, encoding="utf-8")

def state_read_json(key):
    p = STATE_DIR / f"{key}.json"
    if not p.exists(): return {}
    try: return json.loads(p.read_text(encoding="utf-8"))
    except: return {}

def state_write_json(key, value):
    (STATE_DIR / f"{key}.json").write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")

def slug(text):
    s = text.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    return s[:60]

def word_count(text):
    return len(text.split())

def is_friday():
    return date.today().weekday() == 4

def today_iso():
    return date.today().isoformat()

# -- OLLAMA --------------------------------------------------------------------

_last_model_used = None

def unload_model(model):
    """Tell Ollama to unload a model and poll until VRAM is actually clear."""
    try:
        requests.post(
            OLLAMA_URL.replace("/api/chat", "/api/generate"),
            json={"model": model, "keep_alive": 0},
            timeout=15
        )
        log(f"  Unloaded {model} from VRAM")
    except Exception:
        pass

    # Poll /api/ps until model is gone from loaded list (max 60s)
    for i in range(20):
        time.sleep(3)
        try:
            r = requests.get(
                OLLAMA_URL.replace("/api/chat", "/api/ps"),
                timeout=10
            )
            loaded = [m.get("name", "") for m in r.json().get("models", [])]
            if not any(model.split(":")[0] in m for m in loaded):
                log(f"  VRAM clear confirmed after {(i+1)*3}s")
                time.sleep(5)  # extra buffer after confirmation
                return
        except Exception:
            pass
    log("  VRAM poll timeout -- waiting 20s extra", "WARN")
    time.sleep(20)

def call_agent(agent, user_msg, retries=2):
    global _last_model_used
    model = MODELS[agent]

    # If switching models, unload previous and wait for VRAM to clear
    if _last_model_used and _last_model_used != model:
        log(f"  Switching model: {_last_model_used} -> {model}")
        unload_model(_last_model_used)
        time.sleep(20)  # wait for VRAM to fully clear on 8GB GPU

    log(f"  -> {agent} ({model}) thinking...")
    payload = {
        "model"   : model,
        "stream"  : False,
        "messages": [
            {"role": "system", "content": PROMPTS[agent]},
            {"role": "user",   "content": user_msg},
        ],
        "keep_alive": "5m",
        "options": {
            "num_gpu"   : 12,   # conservative split for 8GB VRAM
            "num_thread": 8,    # CPU threads for remaining layers
        },
    }
    for attempt in range(1, retries + 2):
        try:
            r = requests.post(OLLAMA_URL, json=payload, timeout=600)
            r.raise_for_status()
            content = r.json()["message"]["content"]
            log(f"  OK {agent} done ({word_count(content)} words)")
            _last_model_used = model
            return content
        except requests.exceptions.Timeout:
            log(f"  FAIL {agent} timed out (attempt {attempt})", "WARN")
        except Exception as e:
            log(f"  FAIL {agent} error: {e} (attempt {attempt})", "WARN")
        if attempt <= retries:
            time.sleep(5)
    log(f"  FAIL {agent} failed after all attempts", "ERROR")
    return None

# -- TOPIC ---------------------------------------------------------------------

def pick_topic():
    done_path = STATE_DIR / "done_topics.txt"
    next_path = STATE_DIR / "next_topic.txt"
    done      = set(done_path.read_text(encoding="utf-8").splitlines()) if done_path.exists() else set()

    # Check if trend_scout.py queued a trending topic for today
    if next_path.exists():
        trending = next_path.read_text(encoding="utf-8").strip()
        if trending and trending not in done:
            log(f"  Topic (trending): {trending}")
            with open(done_path, "a", encoding="utf-8") as f:
                f.write(trending + "\n")
            next_path.unlink()
            return trending
        next_path.unlink()

    # Fall back to static list
    remaining = [t for t in TOPICS if t not in done]
    if not remaining:
        log("All topics exhausted -- add more to TOPICS list", "WARN")
        return None
    topic = remaining[0]
    with open(done_path, "a", encoding="utf-8") as f:
        f.write(topic + "\n")
    log(f"  Topic (static list): {topic}")
    return topic

# -- GIT -----------------------------------------------------------------------

def git_push(commit_msg):
    log(f"  Pushing: {commit_msg}")
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
    log("  Pushed OK -- Vercel deploying...")
    return True

# -- PIPELINE ------------------------------------------------------------------

def run_article_pipeline():
    log("== ARTICLE PIPELINE ======================================")

    # Check already done today
    if state_read_json(f"delivery_{today_iso()}").get("published"):
        log("  Already published today -- skipping")
        return True

    # 1. Scout
    log("-- Phase 1 - Scout")
    topic = pick_topic()
    if not topic: return False
    brief = call_agent("scout", f"Research this topic for a UK personal finance blog: {topic}")
    if not brief: return False
    state_write("current_brief", brief)
    state_write("current_topic", topic)
    log("  Brief saved OK")

    # 2. Strategist
    log("-- Phase 2 - Strategist")
    skeleton = call_agent("strategist", f"Create an article skeleton from this brief:\n\n{brief}")
    if not skeleton: return False
    state_write("current_skeleton", skeleton)
    log("  Skeleton saved OK")

    # 3. Writer
    log("-- Phase 3 - Writer")
    draft = call_agent("writer", f"Write the full article.\n\nBRIEF:\n{brief}\n\nSKELETON:\n{skeleton}")
    if not draft: return False
    state_write("current_draft", draft)
    log(f"  Draft: {word_count(draft)} words OK")

    # 4. Gatekeeper QA loop
    current = draft
    qa_status = "FAIL"
    cycle = 1
    for cycle in range(1, MAX_QA_RETRIES + 1):
        log(f"-- Phase 4 - Gatekeeper (cycle {cycle}/{MAX_QA_RETRIES})")
        qa = call_agent("gatekeeper", f"Review cycle {cycle}.\n\nBRIEF:\n{brief}\n\nARTICLE:\n{current}")
        if not qa: break
        state_write("last_qa_report", qa)
        if "STATUS: PASS" in qa:
            qa_status = "PASS"
            log("  Gatekeeper: PASS OK")
            break
        log(f"  Gatekeeper: FAIL -- sending back to Writer")
        if cycle < MAX_QA_RETRIES:
            fixed = call_agent("writer", f"Fix this article based on QA feedback.\n\nBRIEF:\n{brief}\n\nARTICLE:\n{current}\n\nQA REPORT:\n{qa}")
            if fixed:
                current = fixed
                state_write("current_draft", fixed)
        else:
            log("  Max QA cycles reached -- publishing with warnings", "WARN")
            qa_status = "FORCED"

    # 5. Publish
    log("-- Phase 5 - Publish")
    filename = slug(topic) + ".md"
    dest = DOCS_DIR / filename
    dest.write_text(current, encoding="utf-8")
    log(f"  Saved: docs/{filename}")

    # Rebuild homepage
    build_script = BASE_DIR / "build_homepage.py"
    if build_script.exists():
        r = subprocess.run(["python", str(build_script)], cwd=BASE_DIR, capture_output=True, text=True)
        if r.returncode == 0: log("  Homepage rebuilt OK")
        else: log(f"  Homepage rebuild warning: {r.stderr.strip()}", "WARN")

    # Record delivery
    delivery = {
        "topic"    : topic,
        "filename" : filename,
        "slug"     : slug(topic),
        "url"      : f"https://{SITE_DOMAIN}/{slug(topic)}/",
        "words"    : word_count(current),
        "qa_status": qa_status,
        "qa_cycles": cycle,
        "published": datetime.now().isoformat(),
    }
    state_write_json(f"delivery_{today_iso()}", delivery)

    # Update article history for newsletter
    history = state_read_json("article_history") or {"articles": []}
    history["articles"].insert(0, delivery)
    history["articles"] = history["articles"][:30]
    state_write_json("article_history", history)

    git_push(f"auto: publish -- {topic[:50]}")
    log(f"  URL: {delivery['url']}")
    log(f"== PIPELINE COMPLETE [{qa_status}] ==========================")
    return True

# -- NEWSLETTER ----------------------------------------------------------------

def run_newsletter_pipeline():
    log("== NEWSLETTER PIPELINE ====================================")
    week_key = f"newsletter_week_{date.today().isocalendar()[1]}"
    if state_read(week_key) == "sent":
        log("  Already sent this week -- skipping")
        return True

    history = state_read_json("article_history")
    articles = history.get("articles", [])[:7]
    if len(articles) < 2:
        log("  Not enough articles yet (need >=2)", "WARN")
        return False

    article_list = ""
    for i, a in enumerate(articles, 1):
        path = DOCS_DIR / a["filename"]
        summary = " ".join(path.read_text(encoding="utf-8").split()[:200]) if path.exists() else ""
        article_list += f"\nArticle {i}:\nTitle: {a['topic'].title()}\nURL: {a['url']}\nSummary: {summary}\n"

    result = call_agent("courier", f"Write this week's Friday newsletter:\n{article_list}")
    if not result: return False

    match   = re.search(r"---BRIEF START---(.*?)---BRIEF END---", result, re.DOTALL)
    content = match.group(1).strip() if match else result.strip()

    subject = "The Friday Money Brief"
    preview = "Your weekly personal finance roundup from luispaiva.co.uk"
    for line in content.splitlines():
        if line.startswith("SUBJECT:"): subject = line.replace("SUBJECT:", "").strip()
        elif line.startswith("PREVIEW:"): preview = line.replace("PREVIEW:", "").strip()

    body = "\n".join(l for l in content.splitlines()
                     if not l.startswith("SUBJECT:") and not l.startswith("PREVIEW:")).strip()

    nl_path = NL_DIR / f"newsletter-{today_iso()}.md"
    nl_path.write_text(content, encoding="utf-8")
    (NL_DIR / "latest.md").write_text(content, encoding="utf-8")
    log(f"  Saved: newsletters/newsletter-{today_iso()}.md")

    if BEEHIIV_ENABLED and "YOUR_API" not in BEEHIIV_API_KEY:
        _send_beehiiv(subject, preview, body)
        state_write(week_key, "sent")
    else:
        log("  Beehiiv not configured -- saved locally only")

    git_push("auto: add weekly newsletter")
    log("== NEWSLETTER COMPLETE ====================================")
    return True

def _send_beehiiv(subject, preview, body_md):
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', body_md)
    html = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', html)
    html = re.sub(r'^-> (.+)$', r'<p>-> \1</p>', html, flags=re.MULTILINE)
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'\n{2,}', '</p><p>', html)
    html = f"<p>{html}</p>"
    url = f"https://api.beehiiv.com/v2/publications/{BEEHIIV_PUBLICATION_ID}/posts"
    headers = {"Authorization": f"Bearer {BEEHIIV_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "publication_id": BEEHIIV_PUBLICATION_ID, "subject_line": subject,
        "preview_text": preview, "content_html": html, "content_text": body_md,
        "status": "confirmed", "web_enabled": True, "authors": [{"name": "Luis Paiva"}], "audience": "free",
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        if r.status_code in (200, 201):
            log(f"  Beehiiv: sent OK id={r.json().get('data',{}).get('id','?')}")
            return True
        log(f"  Beehiiv: HTTP {r.status_code}: {r.text[:200]}", "ERROR")
    except Exception as e:
        log(f"  Beehiiv error: {e}", "ERROR")
    return False

# -- MAIN ----------------------------------------------------------------------

def run():
    log("=" * 60)
    log(f"  BLOG PIPELINE  |  {SITE_DOMAIN}")
    log(f"  {date.today().strftime('%A %d %B %Y')}")
    log("=" * 60)

    if is_friday():
        run_newsletter_pipeline()

    run_article_pipeline()

if __name__ == "__main__":
    run()
