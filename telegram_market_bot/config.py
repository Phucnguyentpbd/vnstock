from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    telegram_chat_id: str | None = None
    timezone: str = "Asia/Ho_Chi_Minh"
    report_hour: int = 7
    report_minute: int = 30
    news_lookback_hours: int = 30
    max_news_items: int = 8
    request_timeout: int = 15
    subscribers_file: str = "data/subscribers.json"

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("Missing TELEGRAM_BOT_TOKEN")
        return cls(
            telegram_token=token,
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID") or None,
            timezone=os.getenv("BOT_TIMEZONE", "Asia/Ho_Chi_Minh"),
            report_hour=int(os.getenv("REPORT_HOUR", "7")),
            report_minute=int(os.getenv("REPORT_MINUTE", "30")),
            news_lookback_hours=int(os.getenv("NEWS_LOOKBACK_HOURS", "30")),
            max_news_items=int(os.getenv("MAX_NEWS_ITEMS", "8")),
            request_timeout=int(os.getenv("REQUEST_TIMEOUT", "15")),
            subscribers_file=os.getenv("SUBSCRIBERS_FILE", "data/subscribers.json"),
        )
