#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notify.py
Simple Telegram notification helper.
Import and call: notify("your message")
"""

import requests, sys

BOT_TOKEN = "8756748955:AAF5VgEkmrUKHwrKnpFAYczu9tmTdtnG4fs"
CHAT_ID   = "5523349075"

def notify(message):
    """Send a Telegram message to Luis."""
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"},
            timeout=10
        )
    except Exception as e:
        print(f"Notify failed: {e}")

if __name__ == "__main__":
    # Test: python notify.py "hello"
    msg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Test notification from luispaiva.co.uk"
    notify(msg)
    print(f"Sent: {msg}")
