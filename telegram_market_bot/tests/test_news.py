from telegram_market_bot.news import FeedSource, parse_feed


def test_parse_feed_macro_topics():
    xml = """<rss><channel><item><title>Fed giữ lãi suất, USD biến động</title><link>https://example.com/a</link><description>CPI hạ nhiệt</description><pubDate>Sun, 04 Oct 2026 06:00:00 +0000</pubDate></item></channel></rss>"""
    items = parse_feed(xml, FeedSource("Test", "https://example.com"))
    assert len(items) == 1
    assert "Lãi suất/Tiền tệ" in items[0].topics
    assert "Tỷ giá/USD" in items[0].topics
    assert "Lạm phát" in items[0].topics
