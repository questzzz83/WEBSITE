---
name: blog-publisher
description: Runs the autonomous blog publishing pipeline for luispaiva.co.uk. Researches a UK personal finance topic, writes a full SEO article using local Ollama models, QA checks it, and publishes to GitHub (Vercel auto-deploys). Also sends the Friday newsletter via Beehiiv.
user-invocable: true
---

# Blog Publisher

This skill runs the full autonomous article pipeline for luispaiva.co.uk.

## What it does

1. Picks the next unpublished topic from the topic bank
2. Scout researches it and writes a brief
3. Strategist builds the article skeleton
4. Writer produces the full 1,500–2,500 word article
5. Gatekeeper QA checks it — auto-fixes and retries on fail
6. Publishes to docs/, rebuilds the homepage, git pushes to GitHub
7. Vercel auto-deploys to luispaiva.co.uk
8. On Fridays — also writes and sends the weekly newsletter

## How to run

From Telegram, message Ink:
- "Run the pipeline"
- "Publish a new article"

Or it runs automatically every day at 07:00 via cron.

## Manual run

```
python D:/Website/pipeline_v2.py
```

## Output locations

- Article: D:/Website/docs/<slug>.md
- Log: D:/Website/logs/pipeline_YYYY-MM-DD.log
- State: D:/Website/.pipeline/ (git-ignored)
- Newsletter: D:/Website/newsletters/latest.md

## Requirements

- Ollama running at http://127.0.0.1:11434
- Models: llama3.1:8b, llama3.2:3b, qwen2.5-coder:7b
- Git configured with push access to questzzz83/WEBSITE
- Python 3.10+ with requests installed
