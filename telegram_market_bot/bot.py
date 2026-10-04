from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from telegram_market_bot.config import Settings
from telegram_market_bot.market import VnstockMarketCollector
from telegram_market_bot.news import MacroNewsCollector

LOGGER = logging.getLogger(__name__)


def _money(v: float) -> str:
    if abs(v) >= 1_000_000_000_000:
        return f"{v / 1_000_000_000_000:.2f} nghìn tỷ"
    if abs(v) >= 1_000_000_000:
        return f"{v / 1_000_000_000:.1f} tỷ"
    return f"{v:,.0f}"


def _volume(v: float) -> str:
    return f"{v / 1_000_000:.1f} triệu cp" if abs(v) >= 1_000_000 else f"{v:,.0f} cp"


def _split(text: str, limit: int = 3800) -> list[str]:
    if len(text) <= limit:
        return [text]
    out, current = [], ""
    for line in text.split("\n"):
        candidate = f"{current}\n{line}".strip() if current else line
        if len(candidate) <= limit:
            current = candidate
        else:
            if current:
                out.append(current)
            current = line
    if current:
        out.append(current)
    return out


class SubscriberStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)

    def list(self) -> list[str]:
        if not self.path.exists():
            return []
        try:
            return [str(x) for x in json.loads(self.path.read_text(encoding="utf-8"))]
        except (OSError, json.JSONDecodeError):
            return []

    def _write(self, values: set[str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(sorted(values), indent=2), encoding="utf-8")

    def add(self, chat_id: int | str) -> None:
        values = set(self.list())
        values.add(str(chat_id))
        self._write(values)

    def remove(self, chat_id: int | str) -> None:
        values = set(self.list())
        values.discard(str(chat_id))
        self._write(values)


class TelegramClient:
    def __init__(self, token: str, timeout: int = 15) -> None:
        self.base = f"https://api.telegram.org/bot{token}"
        self.timeout = timeout
        self.session = requests.Session()

    def updates(self, offset: int | None) -> list[dict]:
        params = {"timeout": 25, "allowed_updates": '["message"]'}
        if offset is not None:
            params["offset"] = offset
        r = self.session.get(f"{self.base}/getUpdates", params=params, timeout=40)
        r.raise_for_status()
        return r.json().get("result", [])

    def send(self, chat_id: int | str, text: str) -> None:
        for chunk in _split(text):
            r = self.session.post(
                f"{self.base}/sendMessage",
                json={"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True},
                timeout=self.timeout,
            )
            r.raise_for_status()


class Bot:
    def __init__(self, settings: Settings) -> None:
        self.s = settings
        self.telegram = TelegramClient(settings.telegram_token, settings.request_timeout)
        self.store = SubscriberStore(settings.subscribers_file)
        self.market = VnstockMarketCollector()
        self.news = MacroNewsCollector(settings.request_timeout)
        self.offset = None
        self.last_sent = None

        if settings.telegram_chat_id:
            self.store.add(settings.telegram_chat_id)

    def report(self) -> str:
        d = self.market.collect()
        news = self.news.fetch(self.s.news_lookback_hours, self.s.max_news_items)
        now = datetime.now(ZoneInfo(self.s.timezone))
        lines = [
            f"🌅 BẢN TIN THỊ TRƯỜNG SÁNG — {now:%d/%m/%Y %H:%M}",
            f"Phiên gần nhất: {d.session_date or 'N/A'}",
            "",
            "1) DIỄN BIẾN PHIÊN GẦN NHẤT",
        ]
        for x in d.indices:
            ratio = f" | KL {x.volume_vs_20d:.2f}x TB20" if x.volume_vs_20d else ""
            lines.append(f"• {x.symbol}: {x.close:,.2f} ({x.change:+.2f} | {x.percent_change:+.2f}%){ratio}")
        lines += [
            "",
            "2) ĐỘ RỘNG & DÒNG TIỀN",
            f"• HOSE: {d.advancers} tăng / {d.decliners} giảm / {d.unchanged} đứng giá",
            f"• GTGD: {_money(d.total_value)} | KL: {_volume(d.total_volume)}",
            f"• Khối ngoại (ước): {_volume(d.foreign_net_volume)} | {_money(d.foreign_net_value_est)}",
        ]
        for title, rows, metric in (
            ("🚀 Tăng mạnh", d.gainers, "pct"),
            ("📉 Giảm mạnh", d.losers, "pct"),
            ("💰 Thanh khoản cao", d.liquidity, "value"),
        ):
            lines += ["", title]
            for row in rows:
                detail = (
                    f"{float(row.get('percent_change', 0)):+.2f}%"
                    if metric == "pct"
                    else _money(float(row.get("total_value", 0)))
                )
                lines.append(f"• {row.get('symbol')}: {detail}")
        lines += ["", "3) VĨ MÔ & TIN QUA ĐÊM / 24–30 GIỜ GẦN NHẤT"]
        if not news:
            lines.append("• Chưa lấy được tin mới.")
        for item in news:
            tags = f" [{' / '.join(item.topics[:2])}]" if item.topics else ""
            lines.append(f"• {item.title}{tags}")
            if item.summary:
                lines.append(f"  {item.summary}")
            if item.link:
                lines.append(f"  {item.source} — {item.link}")
        lines += [
            "",
            "⚠️ Tổng hợp tự động để theo dõi thị trường, không phải khuyến nghị mua/bán.",
        ]
        return "\n".join(lines)

    def news_report(self) -> str:
        items = self.news.fetch(self.s.news_lookback_hours, self.s.max_news_items)
        lines = ["🌐 TIN VĨ MÔ ĐÁNG CHÚ Ý"]
        for item in items:
            tags = f" [{' / '.join(item.topics[:2])}]" if item.topics else ""
            lines += [f"\n• {item.title}{tags}", f"  {item.source} — {item.link}"]
        return "\n".join(lines)

    def handle(self, message: dict) -> None:
        chat_id = (message.get("chat") or {}).get("id")
        if chat_id is None:
            return
        text = str(message.get("text", "")).strip()
        cmd = text.split()[0].split("@")[0].lower() if text else ""
        if cmd == "/start":
            self.store.add(chat_id)
            self.telegram.send(
                chat_id,
                f"✅ Đã đăng ký. Bot gửi bản tin lúc "
                f"{self.s.report_hour:02d}:{self.s.report_minute:02d} mỗi ngày. "
                "Dùng /today, /news, /stop.",
            )
        elif cmd in {"/today", "/market"}:
            self.telegram.send(chat_id, self.report())
        elif cmd == "/news":
            self.telegram.send(chat_id, self.news_report())
        elif cmd == "/stop":
            self.store.remove(chat_id)
            self.telegram.send(chat_id, "🛑 Đã hủy đăng ký.")
        elif cmd == "/help":
            self.telegram.send(chat_id, "/start /today /market /news /stop /help")

    def scheduled(self) -> None:
        now = datetime.now(ZoneInfo(self.s.timezone))
        if (now.hour, now.minute) < (self.s.report_hour, self.s.report_minute):
            return
        key = now.date().isoformat()
        if self.last_sent == key:
            return
        subscribers = self.store.list()
        if not subscribers:
            self.last_sent = key
            return
        report = self.report()
        for chat_id in subscribers:
            self.telegram.send(chat_id, report)
        self.last_sent = key

    def run(self) -> None:
        while True:
            try:
                for update in self.telegram.updates(self.offset):
                    self.offset = int(update.get("update_id", 0)) + 1
                    if update.get("message"):
                        self.handle(update["message"])
                self.scheduled()
            except requests.RequestException:
                LOGGER.exception("Telegram/network error")
                time.sleep(5)
            except Exception:
                LOGGER.exception("Bot error")
                time.sleep(5)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    Bot(Settings.from_env()).run()


if __name__ == "__main__":
    main()
