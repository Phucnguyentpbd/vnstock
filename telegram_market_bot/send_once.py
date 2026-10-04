from __future__ import annotations

import logging

from telegram_market_bot.bot import Bot
from telegram_market_bot.config import Settings


def _discover_chat_id(bot: Bot) -> str:
    updates = bot.telegram.updates(None)
    for update in reversed(updates):
        message = update.get("message") or update.get("edited_message") or {}
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        chat_type = chat.get("type")
        if chat_id is not None and chat_type in {None, "private"}:
            return str(chat_id)

    raise RuntimeError(
        "Không tìm thấy chat Telegram. Hãy mở bot, gửi /start một lần rồi chạy lại workflow."
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    settings = Settings.from_env()
    bot = Bot(settings)
    chat_id = settings.telegram_chat_id or _discover_chat_id(bot)
    bot.telegram.send(chat_id, bot.report())


if __name__ == "__main__":
    main()
