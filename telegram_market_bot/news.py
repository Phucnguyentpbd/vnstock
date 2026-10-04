from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import quote_plus

import requests


@dataclass(frozen=True)
class FeedSource:
    name: str
    url: str
    weight: int = 1


@dataclass
class NewsItem:
    source: str
    title: str
    link: str
    published: datetime
    summary: str
    topics: list[str]
    score: float


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def _strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(value or ""))).strip()


def _truncate(value: str, limit: int = 220) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    return value if len(value) <= limit else value[: limit - 1].rsplit(" ", 1)[0] + "…"


DEFAULT_SOURCES = [
    FeedSource("CafeF Vĩ mô", "https://cafef.vn/vi-mo-dau-tu.rss", 4),
    FeedSource("CafeF Tài chính-NH", "https://cafef.vn/tai-chinh-ngan-hang.rss", 3),
    FeedSource("CafeF Chứng khoán", "https://cafef.vn/thi-truong-chung-khoan.rss", 3),
    FeedSource("CafeF Quốc tế", "https://cafef.vn/tai-chinh-quoc-te.rss", 3),
    FeedSource("VnExpress Kinh doanh", "https://vnexpress.net/rss/kinh-doanh.rss", 3),
    FeedSource(
        "Google News VN vĩ mô",
        "https://news.google.com/rss/search?q="
        + quote_plus("Việt Nam lãi suất tỷ giá GDP CPI đầu tư công")
        + "&hl=vi&gl=VN&ceid=VN:vi",
        2,
    ),
    FeedSource(
        "Google News quốc tế",
        "https://news.google.com/rss/search?q="
        + quote_plus("Federal Reserve inflation oil China economy markets")
        + "&hl=en-US&gl=US&ceid=US:en",
        2,
    ),
]

TOPICS = {
    "Lãi suất/Tiền tệ": ("lai suat", "fed", "fomc", "tien te"),
    "Tỷ giá/USD": ("ty gia", "usd", "dxy", "vnd", "yuan"),
    "Lạm phát": ("lam phat", "cpi", "ppi"),
    "Tăng trưởng": ("gdp", "pmi", "tang truong", "xuat khau", "nhap khau"),
    "Đầu tư công": ("dau tu cong", "giai ngan", "cao toc", "ha tang"),
    "Ngân hàng/Tín dụng": ("tin dung", "ngan hang", "no xau"),
    "Dầu/Hàng hóa": ("gia dau", "brent", "wti", "opec", "vang"),
    "Bất động sản": ("bat dong san", "trai phieu doanh nghiep"),
    "Chính sách": ("chinh phu", "bo tai chinh", "ngan hang nha nuoc", "nghi dinh"),
    "Địa chính trị": ("xung dot", "ukraine", "iran", "tariff", "thue quan"),
}
HIGH_IMPACT = ("fed", "lai suat", "ty gia", "usd", "cpi", "gdp", "pmi", "dau tu cong", "gia dau", "tariff")


def _parse_date(value: str) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            return datetime.now(timezone.utc)


def _text(node: ET.Element, names: set[str]) -> str:
    for child in node:
        tag = child.tag.rsplit("}", 1)[-1].lower()
        if tag in names and child.text:
            return child.text.strip()
    return ""


def parse_feed(xml_text: str, source: FeedSource) -> list[NewsItem]:
    root = ET.fromstring(xml_text)
    items: list[NewsItem] = []
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1].lower() not in {"item", "entry"}:
            continue
        title = _text(node, {"title"})
        if not title:
            continue
        link = _text(node, {"link"})
        if not link:
            for child in node:
                if child.tag.rsplit("}", 1)[-1].lower() == "link":
                    link = child.attrib.get("href", "")
                    if link:
                        break
        summary = _strip_html(_text(node, {"description", "summary", "content", "encoded"}))
        published = _parse_date(_text(node, {"pubdate", "published", "updated", "date"}))
        normalized = _normalize(f"{title} {summary}")
        topics = [name for name, keys in TOPICS.items() if any(k in normalized for k in keys)]
        score = source.weight + 2 * sum(k in normalized for k in HIGH_IMPACT) + len(topics)
        items.append(NewsItem(source.name, _strip_html(title), link, published, _truncate(summary), topics, float(score)))
    return items


class MacroNewsCollector:
    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 VnstockMarketDigestBot/0.1"})

    def fetch(self, lookback_hours: int = 30, max_items: int = 8) -> list[NewsItem]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        collected: list[NewsItem] = []
        for source in DEFAULT_SOURCES:
            try:
                response = self.session.get(source.url, timeout=self.timeout)
                response.raise_for_status()
                collected.extend(parse_feed(response.text, source))
            except (requests.RequestException, ET.ParseError):
                continue

        deduped: dict[str, NewsItem] = {}
        now = datetime.now(timezone.utc)
        for item in collected:
            if item.published < cutoff:
                continue
            key = _normalize(item.title)
            age = max((now - item.published).total_seconds() / 3600, 0)
            item.score += max(0.0, 3.0 - age / 10)
            current = deduped.get(key)
            if current is None or item.score > current.score:
                deduped[key] = item
        return sorted(deduped.values(), key=lambda x: (x.score, x.published), reverse=True)[:max_items]
