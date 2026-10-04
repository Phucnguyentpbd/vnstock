from __future__ import annotations

import logging

from telegram_market_bot.bot import Bot
from telegram_market_bot.config import Settings


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings.from_env()
    if not settings.telegram_chat_id:
        raise RuntimeError("Missing TELEGRAM_CHAT_ID")
    bot = Bot(settings)
    bot.telegram.send(settings.telegram_chat_id, bot.report())


if __name__ == "__main__":
    main()
