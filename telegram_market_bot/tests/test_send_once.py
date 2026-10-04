from types import SimpleNamespace

import pytest

from telegram_market_bot.send_once import _discover_chat_id


class FakeTelegram:
    def __init__(self, updates):
        self._updates = updates

    def updates(self, offset):
        assert offset is None
        return self._updates


def test_discover_chat_id_uses_latest_private_chat():
    bot = SimpleNamespace(
        telegram=FakeTelegram(
            [
                {"message": {"chat": {"id": -100123, "type": "supergroup"}}},
                {"message": {"chat": {"id": 111, "type": "private"}}},
                {"message": {"chat": {"id": 222, "type": "private"}}},
            ]
        )
    )
    assert _discover_chat_id(bot) == "222"


def test_discover_chat_id_fails_when_no_private_chat():
    bot = SimpleNamespace(
        telegram=FakeTelegram(
            [{"message": {"chat": {"id": -100123, "type": "supergroup"}}}]
        )
    )
    with pytest.raises(RuntimeError, match="gửi /start"):
        _discover_chat_id(bot)
