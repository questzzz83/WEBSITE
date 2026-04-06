# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Autonomous Blog Pipeline v2 -- luispaiva.co.uk
Agents: Scout -> Strategist -> [Writer DISABLED] -> Courier (Fridays)
Pipeline stops after Strategist and notifies via Telegram.
Article writing is done manually with Claude's help.
Run: python pipeline_v2.py
"""

import os, re, json, time, subprocess, requests, sys as _sys
from pathlib import Path as _Path
try:
    _notify_path = _Path(__file__).parent / "notify.py"
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("notify", _notify_path)
    _nm = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_nm)
    notify = _nm.notify
except Exception:
    def notify(msg): pass

from datetime import datetime, date
from pathlib import Path
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# -------------------------------------------------------------------------
# 0️⃣  ENSURE OLLAMA HOME POINTS TO D:\ollama_data (second drive)
# -------------------------------------------------------------------------
if not os.getenv("OLLAMA_HOME"):
    os.environ["OLLAMA_HOME"] = r"D:\ollama_data"
    os.makedirs(os.getenv("OLLAMA_HOME"), exist_ok=True)

# -- CONFIG --------------------------------------------------------------------
SITE_DOMAIN     = "www.luispaiva.co.uk"
GITHUB_USERNAME = "questzzz83"
GITHUB_REPO     = "WEBSITE"
GITHUB_BRANCH   = "main"
OLLAMA_URL      = "http://127.0.0.1:11434/api/chat"

# -------------------------------------------------------------------------
# 1️⃣  MODEL MAP – which model each agent uses
# -------------------------------------------------------------------------
# Writer can be switched to the ultra‑light phi3.5‑mini if you ever run out of VRAM.
# The default (llama3.1) gives the best creativity while still fitting on an 8 GB GPU
# when we limit GPU layers (see GPU_LAYER_MAP below).
MODELS = {
    "scout"      : "phi3:mini",   # short research brief / newsletter intro
    "strategist" : "llama3.1",      # article skeleton (good structure)
    "writer"     : "llama3.1",      # full 2 500‑word article (Option A)
    # "writer"   : "phi3.5-mini",  # <-- uncomment this line & comment above if you need the ultra‑light writer
    "gatekeeper" : "phi3:mini",    # QA / pass‑fail checker (tiny)
    "courier"    : "phi3:mini",   # Friday Money Brief newsletter
}

BEEHIIV_ENABLED        = True
BEEHIIV_API_KEY        = "rVl4Xe2jtnVftKXERBLlFRMIJD2zLLRLN1wnaR7NPU9w3ev5LDPjP61q6U9LFhxF"
BEEHIIV_PUBLICATION_ID = "pub_8bc3d4e7-0688-4182-8d13-041f31a4bab1"
BEEHIIV_SEND_AT        = "immediate"

MAX_QA_RETRIES  = 3
TARGET_LO       = 2500
TARGET_HI       = 3500

BASE_DIR  = Path(__file__).parent
DOCS_DIR  = BASE_DIR / "docs"
STATE_DIR = BASE_DIR / ".pipeline"
LOGS_DIR  = BASE_DIR / "logs"
NL_DIR    = BASE_DIR / "newsletters"

for _d in [DOCS_DIR, STATE_DIR, LOGS_DIR, NL_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------------
# 2️⃣  GPU‑LAYER MAP – how many layers may stay on the GPU
# -------------------------------------------------------------------------
# 4‑bit GGUF models still need a few GB of VRAM.
# We keep the heavy llama3.1 at 6 layers (~6‑7 GB VRAM); the tiny models stay
# fully on‑GPU.
GPU_LAYER_MAP = {
    "phi3.5-mini": 4,   # ~1.4 GB VRAM
    "llama3.1":    6,   # ~6‑7 GB VRAM, rest runs on CPU
    "phi3:mini":   3,   # < 1 GB VRAM
}

def _gpu_options(model_name: str):
    """Return the Ollama `options` dict for a given model."""
    base = model_name.split(":")[0]        # strip any tag (e.g. :q5_0)
    num_gpu = GPU_LAYER_MAP.get(base, 4)   # default 4 layers if unknown
    return {
        "num_gpu"   : num_gpu,
        "num_thread": 8,                   # use all 8 cores of the Ryzen 5 5600X
    }

# -- TOPICS -------------------------------------------------------------------
TOPICS = [
    "how to inherite money and use it wisely - a guide for british residents",  # trending 2026-04-06
    "best balance transfer credit cards for savings",  # trending 2026-04-05
    "guidance on clawback refunds - are you being fobbed off?",  # trending 2026-04-04
    "how best to handle a period out of work",  # trending 2026-04-03
    "how to protect credit score after death of a parent uk",  # trending 2026-04-02
    "current mortgage rate coming to an end",  # trending 2026-04-01
    "pension at 39 should i stop working",  # trending 2026-03-30
    # SAVINGS 2026
    "best high yield savings accounts UK 2026",
    "best easy access savings accounts UK 2026",
    "best fixed rate savings bonds UK 2026",
    "best notice savings accounts UK 2026",
    "best savings accounts for children UK 2026",
    "how to save 10000 pounds in one year UK 2026",
    "how to build an emergency fund UK 2026",
    "how much should you have in an emergency fund UK",
    "premium bonds vs savings accounts UK 2026",
    "best instant access savings accounts UK 2026",
    "how to save money on a low income UK 2026",
    "best savings accounts for over 50s UK 2026",
    "how to save for a house deposit UK 2026",
    "best regular savings accounts UK 2026",
    "how to automate your savings UK 2026",
    "best savings accounts for high earners UK 2026",
    "what happens to savings if bank collapses UK FSCS",
    "best cash ISA rates UK 2026",

    # INVESTING 2026
    "index funds vs ETFs for beginners UK 2026",
    "how to start investing with 100 pounds UK 2026",
    "best stocks and shares ISA accounts UK 2026",
    "best investment platforms UK 2026",
    "how to invest in the S&P 500 from UK 2026",
    "Vanguard vs Fidelity vs Hargreaves Lansdown UK 2026",
    "best global index funds UK 2026",
    "how to build a diversified portfolio UK 2026",
    "pound cost averaging explained UK 2026",
    "dividend investing for beginners UK 2026",
    "best REIT funds UK 2026",
    "active vs passive investing UK 2026",
    "best sustainable ESG funds UK 2026",
    "robo advisors UK 2026 best options",
    "how to invest a lump sum UK 2026",
    "how to rebalance investment portfolio UK",
    "best emerging market funds UK 2026",
    "investing during a recession UK guide 2026",
    "best bond funds UK 2026 for cautious investors",

    # ISA 2026
    "best stocks and shares ISA UK 2026 full comparison",
    "cash ISA vs stocks and shares ISA 2026 which is better",
    "how to transfer ISA to better provider UK 2026",
    "ISA allowance 2026 UK how to use it wisely",
    "best junior ISA accounts UK 2026",
    "pension vs ISA which to prioritise UK 2026",
    "what happens to ISA when you die UK 2026",
    "lifetime ISA UK 2026 rules and best providers",
    "innovative finance ISA UK 2026 is it worth it",
    "how to maximise ISA allowance UK 2026",
    "new ISA rules UK 2026 what has changed",

    # CREDIT CARDS 2026
    "best cashback credit cards UK 2026",
    "best balance transfer credit cards UK 2026",
    "best travel credit cards UK 2026",
    "best rewards credit cards UK 2026",
    "best credit cards for building credit UK 2026",
    "best 0 percent purchase credit cards UK 2026",
    "how to use a credit card responsibly UK 2026",
    "best credit cards for supermarket spending UK 2026",
    "how to avoid credit card interest UK 2026",
    "best business credit cards UK 2026",
    "American Express vs Visa vs Mastercard UK 2026",

    # CREDIT SCORE 2026
    "how to improve credit score fast UK 2026",
    "what is a good credit score UK 2026",
    "how to check credit score free UK 2026",
    "why did my credit score drop UK 2026",
    "how long does bad credit stay on file UK",
    "how to build credit from scratch UK 2026",
    "best credit builder cards UK 2026",
    "how to dispute credit report error UK 2026",
    "does checking credit score affect it UK 2026",

    # DEBT 2026
    "how to pay off credit card debt fast UK 2026",
    "debt avalanche vs debt snowball UK 2026",
    "how to get out of overdraft UK 2026",
    "best personal loans UK 2026 lowest rates",
    "how to consolidate debt UK 2026",
    "what happens if you cannot pay credit card UK",
    "debt management plan vs IVA UK 2026",
    "how to pay off mortgage early UK 2026",
    "student loan UK 2026 repayment plan 1 2 5",
    "how to write financial hardship letter UK",

    # MORTGAGES 2026
    "how to get a mortgage UK first time buyer 2026",
    "fixed vs variable rate mortgage UK 2026",
    "how much can you borrow mortgage UK 2026",
    "best mortgage brokers UK 2026",
    "how to remortgage UK 2026 step by step",
    "shared ownership mortgage UK 2026",
    "stamp duty UK 2026 rates and thresholds",
    "guarantor mortgage UK 2026 who qualifies",
    "how to save house deposit fast UK 2026",
    "mortgage rates forecast UK 2026",
    "interest only vs repayment mortgage UK 2026",
    "best mortgage deals UK 2026 five year fixed",

    # BUDGETING 2026
    "how to create a monthly budget UK 2026",
    "50 30 20 budget rule UK 2026",
    "best budgeting apps UK 2026",
    "zero based budgeting UK 2026 guide",
    "how to save money on groceries UK 2026",
    "how to cut household bills UK 2026",
    "how to save money on energy bills UK 2026",
    "how to do a no spend month UK 2026",
    "how to track spending UK 2026",
    "how to cancel unused subscriptions UK 2026",
    "envelope budgeting method UK 2026",
    "how to save money as a student UK 2026",
    "how to budget as a couple UK 2026",

    # INCOME AND SIDE HUSTLES 2026
    "passive income ideas UK 2026 that actually work",
    "how to negotiate salary UK 2026",
    "best side hustles UK 2026",
    "how to make money online UK 2026",
    "how to start a side hustle UK 2026",
    "how to make money from home UK 2026",
    "best cashback sites UK 2026 TopCashback vs Quidco",
    "how to rent out a room UK 2026 rules and tax",
    "how to sell on eBay UK 2026 beginners guide",
    "how to become a freelancer UK 2026",
    "AI tools to make money UK 2026",
    "how to make money from AI side hustle UK 2026",
    "best paid survey sites UK 2026",
    "how to make money from photography UK 2026",
    "dropshipping UK 2026 is it worth it",

    # PENSION AND RETIREMENT 2026
    "how does workplace pension work UK 2026",
    "how much to put in pension UK 2026 by age",
    "SIPP UK 2026 self invested personal pension guide",
    "how to consolidate pensions UK 2026",
    "state pension UK 2026 how much will you get",
    "pension vs ISA UK 2026 which wins for retirement",
    "best private pension providers UK 2026",
    "FIRE movement UK 2026 how to retire early",
    "how to trace lost pensions UK 2026",
    "pension tax relief UK 2026 how to claim",
    "pension age changes UK 2026 what you need to know",
    "defined benefit vs defined contribution pension UK 2026",
    "how much do you need to retire UK 2026",
    "annuity vs drawdown UK 2026",

    # TAX 2026
    "income tax UK 2026 rates and thresholds explained",
    "how to do self assessment tax return UK 2026",
    "capital gains tax UK 2026 rates and allowances",
    "inheritance tax UK 2026 thresholds and planning",
    "national insurance UK 2026 rates explained",
    "how to claim tax back PAYE UK 2026",
    "tax on savings interest UK 2026",
    "how to reduce tax bill UK 2026 legal strategies",
    "tax on rental income UK 2026 landlord guide",
    "marriage allowance UK 2026 how to claim",
    "tax free allowances UK 2026 full list",
    "spring budget 2026 UK what it means for your money",

    # INSURANCE 2026
    "best life insurance UK 2026",
    "income protection insurance UK 2026 is it worth it",
    "critical illness cover UK 2026",
    "best home insurance UK 2026",
    "best car insurance UK 2026 how to save money",
    "travel insurance UK 2026 what you need",
    "health insurance vs NHS UK 2026",
    "how to reduce insurance premiums UK 2026",
    "best pet insurance UK 2026",

    # BANKING 2026
    "best current accounts UK 2026 with switching bonuses",
    "best bank accounts for students UK 2026",
    "best online banks UK 2026 Monzo Starling Revolut",
    "how to switch bank accounts UK 2026",
    "Monzo vs Starling 2026 which is better",
    "best business bank accounts UK 2026",
    "how to open bank account bad credit UK 2026",
    "best multi currency accounts UK 2026",
    "Chase UK bank account 2026 review",
    "bank switching bonuses UK 2026 free cash offers",
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

CRITICAL LENGTH REQUIREMENT: The article MUST be 2,500 words minimum. This is non‑negotiable.
Count your words as you write. If you finish under 2,500 words, you have failed.

HOW TO REACH 2,500 WORDS:
- Introduction: 200-250 words
- Each H2 section: 350-450 words minimum
- With 6 sections that is already 2,300+ words
- Add real UK examples, specific numbers, step‑by‑step instructions in every section
- Never write a section in under 300 words
- Expand every point with a concrete UK example or specific data

RULES:
1. Total words: 2,500 minimum. Count carefully. Under 2,500 = automatic failure.
2. Fill every DIRECTIVE block then delete the comment
3. Replace [AFFILIATE:N] with real markdown links: [Product Name](https://url)
4. Replace [TABLE] with a markdown table (min 4 columns, 5 data rows, real UK data)
5. Replace [CTA] with a 2‑3 sentence friendly call‑to‑action
6. Primary keyword in: H1, first sentence, at least 2 H2s
7. Paragraphs: 2‑3 sentences max
8. UK‑specific: GBP signs, real UK providers, UK rates and rules
9. Every section must have at least one specific UK example with real numbers
10. Add a META DESCRIPTION on line 2 of the article (after the version comment):
    META_DESCRIPTION: [exactly 150‑155 characters, contains primary keyword, describes what reader will learn]
11. Add a FAQ section near the end with exactly 5 questions and answers:
    ## Frequently Asked Questions
    **Q: [common question about the topic]**
    A: [2‑3 sentence answer with specific UK details]
    (repeat for 5 questions)
12. Final line must be exactly:
    *Affiliate disclosure: This article contains affiliate links. We may earn a small commission at no extra cost to you. Always do your own research before making financial decisions.*

When fixing after QA FAIL:
- If word count is low: expand EVERY section by adding more detail, examples, and UK‑specific data
- Do not rewrite passing sections -- only expand them
- Increment <!-- version: N --> at top

Output ONLY the article. Nothing before it. Nothing after it.""",
    "gatekeeper": """You are Gatekeeper, a QA agent for luispaiva.co.uk. You are strict and impartial.
You receive a brief and article. You return ONLY this exact format:

STATUS: PASS | FAIL
CYCLE: [N]
WORD COUNT: [exact]

CHECKS:
[OK or FAIL] Word count minimum 2500: [actual -- FAIL if under 2500, no exceptions, count every word]
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

FAIL if ANY check is FAIL. PASS only if ALL are OK.
CRITICAL: Word count under 2500 is ALWAYS a FAIL. No exceptions. Count every single word.""",
    "courier": """You are Courier, the newsletter writer for luispaiva.co.uk.
Every Friday you write "The Friday Money Brief" -- a practical, punchy UK money email.
Tone: a financially-savvy friend sharing the week's best money insight. Warm, direct, no fluff.

You receive a list of published articles. Pick the most useful or timely as the lead story.

RULES:
1. Greeting must be "Hi there," -- never use a specific name
2. Only link to articles that actually exist in the list provided -- never invent URLs
3. Subject line: max 50 chars, factual, not clickbait
4. 300-400 words total
5. One specific UK number, rate, or example in the lead section
6. "Also this week" section: only include articles from the list, skip if fewer than 2

Output ONLY the newsletter content in this exact format:

---BRIEF START---
SUBJECT: [max 50 chars]
PREVIEW: [max 90 chars -- teaser that continues the subject]

---

Hi there,

[HOOK -- one punchy sentence with the most interesting fact from the lead article]

[BRIDGE -- one sentence on why UK readers should care right now]

**[Lead Article Title]([URL])**

[4-5 sentences covering the key insight. Include one specific UK number, rate, or rule. End with a reason to click through.]

-> [Read the full guide]([URL])

---

**Also this week:**
- **[Article 2 Title]([URL])** -- [one sentence on why it matters]
- **[Article 3 Title]([URL])** -- [one sentence on why it matters]

---

Until next Friday,
Luis Paiva
luispaiva.co.uk

*You're receiving this because you subscribed at luispaiva.co.uk.
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


# -- BRIEF QUALITY CHECK -------------------------------------------------------
FAKE_ORG_PATTERNS = [
    r"pension rights protection service",
    r"\bprps\b",
    r"\bmapes\b",
    r"money and pensions enquiry service",
    r"clawbackadviceuk\.com",
    r"clawbake",
    r"pensionsadviceukservices",
    r"clawbackrecovery",
]
GARBLED_TITLE_PATTERNS = [
    r"navelled",
    r"fair right answers",
]

def validate_brief(brief, topic):
    b = brief.lower()
    for pat in FAKE_ORG_PATTERNS:
        if re.search(pat, b, re.IGNORECASE):
            return False, "Hallucinated source detected: " + pat
    for pat in GARBLED_TITLE_PATTERNS:
        if re.search(pat, b, re.IGNORECASE):
            return False, "Garbled brief language: " + pat
    if word_count(brief) < 80:
        return False, "Brief too short (%d words)" % word_count(brief)
    topic_words = [w for w in topic.lower().split() if len(w) > 4]
    matches = sum(1 for w in topic_words if w in b)
    if topic_words and matches == 0:
        return False, "Brief has no overlap with topic"
    return True, "OK"

def rescount_topic(bad_topic):
    """Re-run trend_scout to get a fresh topic after a bad brief."""
    log("  Re-running Trend Scout for a fresh topic...", "WARN")
    scouted_lock = STATE_DIR / ("trend_scouted_" + today_iso() + ".txt")
    if scouted_lock.exists():
        scouted_lock.unlink()
    next_path = STATE_DIR / "next_topic.txt"
    if next_path.exists():
        next_path.unlink()
    done_path = STATE_DIR / "done_topics.txt"
    with open(done_path, "a", encoding="utf-8") as f:
        f.write(bad_topic + "\n")
    scout_script = BASE_DIR / "trend_scout.py"
    if not scout_script.exists():
        log("  trend_scout.py not found - falling back to static list", "WARN")
        return None
    r = subprocess.run(
        ["python", str(scout_script)],
        cwd=BASE_DIR, capture_output=True, text=True, timeout=180
    )
    if r.returncode != 0:
        log("  Trend Scout failed: " + r.stderr.strip()[:200], "ERROR")
        return None
    if next_path.exists():
        new_topic = next_path.read_text(encoding="utf-8").strip()
        log("  New topic from Scout: " + new_topic)
        return new_topic
    log("  Trend Scout ran but produced no topic", "WARN")
    return None

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
                time.sleep(5)
                return
        except Exception:
            pass
    log("  VRAM poll timeout – waiting extra 20s", "WARN")
    time.sleep(20)

def call_agent(agent, user_msg, retries=2):
    global _last_model_used
    model = MODELS[agent]

    if _last_model_used and _last_model_used != model:
        log(f"  Switching model: {_last_model_used} -> {model}")
        unload_model(_last_model_used)
        time.sleep(20)

    log(f"  -> {agent} ({model}) thinking...")
    payload = {
        "model"      : model,
        "stream"     : False,
        "messages"   : [
            {"role": "system", "content": PROMPTS[agent]},
            {"role": "user",   "content": user_msg},
        ],
        "keep_alive" : "5m",
        "options"    : _gpu_options(model),   # <-- per‑model GPU options
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

    if next_path.exists():
        trending = next_path.read_text(encoding="utf-8").strip()
        if trending and trending not in done:
            log(f"  Topic (trending): {trending}")
            with open(done_path, "a", encoding="utf-8") as f:
                f.write(trending + "\n")
            next_path.unlink()
            return trending
        next_path.unlink()

    strategy_path = STATE_DIR / "strategy_latest.md"
    if strategy_path.exists():
        strategy = strategy_path.read_text(encoding="utf-8")
        # Match old format "### 1. Title" and new emoji format "### 🔴 Priority 1 — Title"
        rec_titles = re.findall(r"###\s+[^\w\n]*(?:Priority\s+\d+\s+[\u2014-]\s+|\d+\.\s+)(.+)", strategy)
        for title in rec_titles:
            title = title.strip()
            if title not in done:
                log(f"  Topic (strategy room): {title}")
                with open(done_path, "a", encoding="utf-8") as f:
                    f.write(title + "\n")
                return title

    remaining = [t for t in TOPICS if t not in done]
    if not remaining:
        log("All topics exhausted – add more to TOPICS list", "WARN")
        return None
    topic = remaining[0]
    with open(done_path, "a", encoding="utf-8") as f:
        f.write(topic + "\n")
    log(f"  Topic (static list): {topic}")
    return topic

# -- GIT -----------------------------------------------------------------------
def git_push(commit_msg):
    log(f"  Pushing: {commit_msg}")
    # Pull remote first to avoid rejection; theirs wins on conflict
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

# -- PIPELINE ------------------------------------------------------------------
def run_article_pipeline():
    log("== ARTICLE PIPELINE ======================================")

    # Skip if already published today
    if state_read_json(f"delivery_{today_iso()}").get("published"):
        log("  Already published today – skipping")
        return True

    # -----------------------------------------------------------------
    # 1️⃣ Scout – research brief
    # -----------------------------------------------------------------
    log("-- Phase 1 - Scout")
    topic = pick_topic()
    if not topic:
        return False
    brief = call_agent("scout", f"Research this topic for a UK personal finance blog: {topic}")
    if not brief:
        return False

    # Validate brief quality – catch hallucinated sources / garbled output
    MAX_TOPIC_RETRIES = 2
    for _retry in range(MAX_TOPIC_RETRIES):
        ok, reason = validate_brief(brief, topic)
        if ok:
            break
        log(f"  Brief quality check FAILED: {reason}", "WARN")
        new_topic = rescount_topic(topic)
        if not new_topic or new_topic == topic:
            log("  Could not get a fresh topic – skipping today", "ERROR")
            notify("Pipeline skipped – Scout produced bad brief and no fallback topic found")
            return False
        topic = new_topic
        log(f"  Retrying with new topic: {topic}")
        brief = call_agent("scout", f"Research this topic for a UK personal finance blog: {topic}")
        if not brief:
            return False
    else:
        ok, reason = validate_brief(brief, topic)
        if not ok:
            log(f"  Brief still invalid after {MAX_TOPIC_RETRIES} retries: {reason}", "ERROR")
            notify("Pipeline skipped – could not get a valid brief after retries")
            return False

    state_write("current_brief", brief)
    state_write("current_topic", topic)

    # -----------------------------------------------------------------
    # 2️⃣ Strategist – article skeleton
    # -----------------------------------------------------------------
    log("-- Phase 2 - Strategist")
    skeleton = call_agent("strategist", f"Create an article skeleton from this brief:\n\n{brief}")
    if not skeleton:
        return False
    state_write("current_skeleton", skeleton)

    # -----------------------------------------------------------------
    # 3️⃣ Writer – DISABLED (manual authoring with Claude)
    # -----------------------------------------------------------------
    log("-- Phase 3 - Writer DISABLED")
    log("  Brief and skeleton saved. Write the article manually using Claude.")
    log(f"  Brief : .pipeline/current_brief.txt")
    log(f"  Skeleton: .pipeline/current_skeleton.txt")
    log(f"  Topic : {topic}")
    notify(
        f"\U0001F4DD Pipeline ready for manual writing\n\n"
        f"Topic: {topic}\n"
        f"Brief: .pipeline/current_brief.txt\n"
        f"Skeleton: .pipeline/current_skeleton.txt\n\n"
        f"Write article → save to docs/{slug(topic)}.md → run publish_article.py"
    )
    log("== PIPELINE PAUSED – awaiting manual article ================")
    return True

# -- NEWSLETTER ---------------------------------------------------------------
def run_newsletter_pipeline():
    log("== NEWSLETTER PIPELINE =============================")
    week_key = f"newsletter_week_{date.today().isocalendar()[1]}"
    if state_read(week_key) == "sent":
        log("  Already sent this week – skipping")
        return True

    history = state_read_json("article_history")
    articles = history.get("articles", [])[:7]
    if len(articles) < 2:
        log("  Not enough recent articles for a newsletter", "WARN")
        return False

    # Build a simple list of article info for the prompt
    article_list = ""
    for i, a in enumerate(articles, 1):
        article_list += f"\nArticle {i}:\nTitle: {a['topic']}\nURL: {a['url']}\n"

    prompt = f"""Write this week's Friday Money Brief newsletter.

USE THE EXACT URLs below – never invent placeholders.

{article_list}

Remember: subject line ≤ 50 chars, 300‑400 words total, include 1 UK‑specific number in the lead section."""
    result = call_agent("courier", prompt)
    if not result:
        return False

    # Clean up the output (the agent already follows the exact format, but we
    # strip any stray leading/trailing whitespace)
    match = re.search(r"---BRIEF START---(.*?)---BRIEF END---", result, re.DOTALL)
    content = match.group(1).strip() if match else result.strip()

    # Save the newsletter markdown
    nl_path = NL_DIR / f"newsletter-{today_iso()}.md"
    nl_path.write_text(content, encoding="utf-8")
    (NL_DIR / "latest.md").write_text(content, encoding="utf-8")
    log(f"  Saved newsletter: newsletters/newsletter-{today_iso()}.md")

    # (Optional) send to Beehiiv – keep the original function unchanged
    if BEEHIIV_ENABLED and "YOUR_API" not in BEEHIIV_API_KEY:
        _send_beehiiv("The Friday Money Brief",
                      "Your weekly UK money roundup",
                      content)
        state_write(week_key, "sent")
    else:
        log("  Beehiiv not configured – newsletter saved locally only")

    git_push("auto: add weekly newsletter")
    notify("Newsletter ready – copy from newsletters/ folder to Beehiiv")
    return True

def _send_beehiiv(subject, preview, body_md):
    # (original implementation – unchanged)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', body_md)
    html = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', html)
    html = re.sub(r'^-> (.+)$', r'<p>-> \1</p>', html, flags=re.MULTILINE)
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'\n{2,}', '</p><p>', html)
    html = f"<p>{html}</p>"
    url = f"https://api.beehiiv.com/v2/publications/{BEEHIIV_PUBLICATION_ID}/posts"
    headers = {"Authorization": f"Bearer {BEEHIIV_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "publication_id": BEEHIIV_PUBLICATION_ID,
        "title": subject,
        "subject_line": subject,
        "preview_text": preview,
        "content_html": html,
        "content_text": body_md,
        "status": "draft",
        "web_enabled": True,
        "authors": [{"name": "Luis Paiva"}],
        "audience": "free",
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
def run(force_newsletter=False):
    log("=" * 60)
    log(f"  BLOG PIPELINE  |  {SITE_DOMAIN}")
    log(f"  {date.today().strftime('%A %d %B %Y')}")
    log("=" * 60)

    if is_friday() or force_newsletter:
        run_newsletter_pipeline()

    if not force_newsletter:
        notify(f"Pipeline starting – {date.today().strftime('%A %d %B')}")
        run_article_pipeline()

if __name__ == "__main__":
    import sys as _sys
    force_nl = "--newsletter" in _sys.argv
    run(force_newsletter=force_nl)
