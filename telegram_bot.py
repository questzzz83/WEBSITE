#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
telegram_bot.py
Lightweight Telegram command bot for luispaiva.co.uk blog pipeline.
No LLM — instant command matching and execution.

Install:  pip install python-telegram-bot
Run:      python telegram_bot.py
Auto-run: add to Windows startup or run as background process
"""

import sys, os, re, json, subprocess, threading
from datetime import date, datetime
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from telegram import Update
    from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
except ImportError:
    print("Installing python-telegram-bot...")
    subprocess.run([sys.executable, "-m", "pip", "install", "python-telegram-bot", "--break-system-packages"], check=True)
    from telegram import Update
    from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

# ── Config ─────────────────────────────────────────────────────────────────────

BOT_TOKEN   = ""
WEBSITE_DIR = Path("D:/Website")
DOCS_DIR    = WEBSITE_DIR / "docs"
STATE_DIR   = WEBSITE_DIR / ".pipeline"
LOGS_DIR    = WEBSITE_DIR / "logs"
NL_DIR      = WEBSITE_DIR / "newsletters"

# ── Helpers ────────────────────────────────────────────────────────────────────

def run_script(script_path, args=None):
    """Run a Python script and return output."""
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)
    try:
        r = subprocess.run(
            cmd, cwd=str(WEBSITE_DIR),
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=3600
        )
        out = (r.stdout + r.stderr).strip()
        return out[-3000:] if len(out) > 3000 else out
    except subprocess.TimeoutExpired:
        return "Script timed out after 1 hour"
    except Exception as e:
        return f"Error: {e}"

def count_articles():
    skip = {".gitkeep", "index.md", "privacy.md", "about.md"}
    return len([f for f in DOCS_DIR.glob("*.md") if f.name not in skip])

def last_published():
    skip = {".gitkeep", "index.md", "privacy.md", "about.md"}
    mds = [f for f in DOCS_DIR.glob("*.md") if f.name not in skip]
    if not mds:
        return "none"
    latest = max(mds, key=lambda f: f.stat().st_mtime)
    return latest.stem.replace("-", " ").title()

def today_log_tail(n=20):
    log_file = LOGS_DIR / f"pipeline_{date.today().isoformat()}.log"
    if not log_file.exists():
        return "No log for today yet."
    lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-n:])

def next_topics(n=5):
    done_path = STATE_DIR / "done_topics.txt"
    done = set(done_path.read_text(encoding="utf-8").splitlines()) if done_path.exists() else set()

    topics = []

    # Strategy room first
    strategy_path = STATE_DIR / "strategy_latest.md"
    if strategy_path.exists():
        strategy = strategy_path.read_text(encoding="utf-8")
        rec = re.findall(r"### \d+\. (.+)", strategy)
        for t in rec:
            if t.strip() not in done:
                topics.append(f"[strategy] {t.strip()}")
            if len(topics) >= n:
                return topics

    # Static list fallback - read from pipeline_v2.py
    pipeline = WEBSITE_DIR / "pipeline_v2.py"
    if pipeline.exists():
        code = pipeline.read_text(encoding="utf-8")
        m = re.search(r'TOPICS\s*=\s*\[(.*?)\]', code, re.DOTALL)
        if m:
            all_topics = re.findall(r'"([^"]+)"', m.group(1))
            for t in all_topics:
                if t not in done and len(topics) < n:
                    topics.append(f"[static] {t}")

    return topics[:n]

def strategy_files():
    files = sorted(STATE_DIR.glob("strategy_*.md"), reverse=True)
    if not files:
        return "No strategy files found."
    lines = []
    for f in files[:5]:
        content = f.read_text(encoding="utf-8")
        first_line = content.split("\n")[0].replace("#", "").strip()
        lines.append(f"- {f.name}: {first_line}")
    return "\n".join(lines)

def get_brief():
    path = STATE_DIR / "strategy_latest.md"
    if not path.exists():
        return "No strategy file found. Run `strategy` first."
    content = path.read_text(encoding="utf-8")
    # Extract recommended articles section
    m = re.search(r'## Recommended Articles.*?(?=## |---|\Z)', content, re.DOTALL)
    if m:
        return m.group(0).strip()[:2000]
    return content[:2000]

def get_newsletter():
    # Get latest newsletter
    files = sorted(NL_DIR.glob("newsletter-*.md"), reverse=True) if NL_DIR.exists() else []
    if not files:
        return "No newsletter found. Run `newsletter` first."
    return files[0].read_text(encoding="utf-8", errors="replace")[:3000]

# ── Command Handlers ───────────────────────────────────────────────────────────

async def cmd_pipeline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Running trend scout and pipeline... This takes ~30 minutes. I'll update you at each phase.")

    def run():
        # Run trend scout
        out1 = run_script(WEBSITE_DIR / "trend_scout.py")
        # Extract topic from output
        topic_match = re.search(r'Topic.*?:\s*(.+)', out1)
        topic = topic_match.group(1).strip() if topic_match else "unknown"

        import asyncio
        asyncio.run(update.message.reply_text(f"Scout done — today's topic: {topic}"))

        # Run pipeline
        out2 = run_script(WEBSITE_DIR / "pipeline_v2.py")

        # Extract key lines
        lines = out2.splitlines()
        key = [l for l in lines if any(x in l for x in ["PASS", "FAIL", "Published", "ERROR", "words", "pushed"])]
        summary = "\n".join(key[-10:]) if key else out2[-1000:]

        asyncio.run(update.message.reply_text(f"Pipeline complete:\n{summary}"))

    threading.Thread(target=run, daemon=True).start()

async def cmd_newsletter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Writing newsletter...")

    def run():
        # Delete today's newsletter so it reruns
        nl_file = NL_DIR / f"newsletter-{date.today().isoformat()}.md"
        if nl_file.exists():
            nl_file.unlink()

        out = run_script(WEBSITE_DIR / "pipeline_v2.py", ["--newsletter"])
        content = get_newsletter()

        import asyncio
        asyncio.run(update.message.reply_text(f"Newsletter ready:\n\n{content[:3000]}"))

    threading.Thread(target=run, daemon=True).start()

async def cmd_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Running strategy room... Takes ~10 minutes.")

    def run():
        out = run_script(WEBSITE_DIR / "strategy_room.py", ["--force"])
        brief = get_brief()
        import asyncio
        asyncio.run(update.message.reply_text(f"Strategy room done:\n\n{brief[:2000]}"))

    threading.Thread(target=run, daemon=True).start()

async def cmd_brief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_brief())

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    n = count_articles()
    last = last_published()
    log_tail = today_log_tail(5)
    msg = f"Articles: {n}\nLast published: {last}\n\nToday's log:\n{log_tail}"
    await update.message.reply_text(msg)

async def cmd_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(today_log_tail(20))

async def cmd_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topics = next_topics(5)
    if not topics:
        await update.message.reply_text("No topics queued.")
        return
    msg = "Next 5 topics:\n" + "\n".join(f"{i+1}. {t}" for i, t in enumerate(topics))
    await update.message.reply_text(msg)

async def cmd_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(strategy_files())

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""Ink commands:
/pipeline   - run trend scout + full pipeline
/newsletter - write this week's newsletter
/strategy   - run strategy room brainstorm
/brief      - show this week's recommended topics
/status     - articles count + last published
/log        - last 20 lines of today's log
/topics     - next 5 topics in queue
/files      - list strategy files
/help       - show this list

You can also just type the command without the slash.""")

# ── Message Router ─────────────────────────────────────────────────────────────

COMMAND_MAP = {
    "pipeline": cmd_pipeline,
    "pipe":     cmd_pipeline,
    "newsletter": cmd_newsletter,
    "news":     cmd_newsletter,
    "strategy": cmd_strategy,
    "brief":    cmd_brief,
    "status":   cmd_status,
    "log":      cmd_log,
    "topics":   cmd_topics,
    "topic":    cmd_topics,
    "files":    cmd_files,
    "strategy files": cmd_files,
    "help":     cmd_help,
}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip().lower().lstrip("/")

    # Exact match first
    if text in COMMAND_MAP:
        await COMMAND_MAP[text](update, context)
        return

    # Partial match
    for key, handler in COMMAND_MAP.items():
        if text.startswith(key) or key.startswith(text):
            await handler(update, context)
            return

    # Unknown
    await cmd_help(update, context)

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Ink bot starting...")
    app = Application.builder().token(BOT_TOKEN).build()

    # Register /commands
    for cmd in ["pipeline", "newsletter", "strategy", "brief", "status", "log", "topics", "files", "help"]:
        app.add_handler(CommandHandler(cmd, COMMAND_MAP.get(cmd, cmd_help)))

    # Catch all text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Ink bot ready. Send /help to your bot.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
