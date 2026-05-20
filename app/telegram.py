"""Thin Telegram Bot API client (sendMessage only — keep it lean)."""

from __future__ import annotations

import os

import httpx


async def send_message(chat_id: str, text: str, parse_mode: str = "Markdown") -> tuple[bool, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return False, "TELEGRAM_BOT_TOKEN not set"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        })
        if resp.status_code == 200:
            return True, "ok"
        return False, f"{resp.status_code}: {resp.text[:200]}"
