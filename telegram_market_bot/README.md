# Telegram Market Digest Bot

Bot Telegram cá nhân dùng **vnstock** để tóm tắt diễn biến thị trường Việt Nam và gom tin vĩ mô có khả năng ảnh hưởng đến thị trường.

## Chức năng

- `/today` hoặc `/market`: VN-Index, VN30, HNX, UPCOM, độ rộng HOSE, thanh khoản, top tăng/giảm, top thanh khoản, khối ngoại ước tính.
- `/news`: tin vĩ mô mới.
- `/start`: đăng ký chat hiện tại nhận bản tin tự động.
- `/stop`: hủy đăng ký.
- Tự gửi lúc **16:10 Asia/Ho_Chi_Minh, Thứ 2–Thứ 6**.
- Nếu không có phiên mới (nghỉ lễ/cuối tuần), mặc định không gửi dữ liệu cũ.

## Nguồn tin mặc định

- CafeF: Vĩ mô - Đầu tư, Tài chính - Ngân hàng, Chứng khoán, Tài chính quốc tế.
- VnExpress Kinh doanh.
- Google News RSS cho các truy vấn vĩ mô Việt Nam và quốc tế.

Bot chỉ giữ tiêu đề, mô tả ngắn và link nguồn; không sao chép toàn bài.

## Chạy local

1. Telegram -> `@BotFather` -> `/newbot` -> lấy token.
2. Đặt biến môi trường:

PowerShell:

```powershell
$env:TELEGRAM_BOT_TOKEN="TOKEN_CUA_BAN"
python -m telegram_market_bot.bot
```

Linux/macOS:

```bash
export TELEGRAM_BOT_TOKEN="TOKEN_CUA_BAN"
python -m telegram_market_bot.bot
```

3. Mở chat với bot và gửi `/start`.

## Docker

Chạy từ thư mục gốc repo:

```bash
docker build -f telegram_market_bot/Dockerfile -t vnstock-market-bot .
docker run -d --restart unless-stopped \
  --name vnstock-market-bot \
  -e TELEGRAM_BOT_TOKEN="TOKEN_CUA_BAN" \
  -v "$(pwd)/bot-data:/app/data" \
  vnstock-market-bot
```

## Biến cấu hình

- `REPORT_HOUR=16`
- `REPORT_MINUTE=10`
- `NEWS_LOOKBACK_HOURS=30`
- `MAX_NEWS_ITEMS=8`
- `BOT_TIMEZONE=Asia/Ho_Chi_Minh`
- `SKIP_IF_MARKET_STALE=true`

> Đây là bản tin tổng hợp tự động, không phải khuyến nghị đầu tư. Repo vnstock có giấy phép tùy chỉnh cho mục đích cá nhân/nghiên cứu phi thương mại; nếu triển khai thương mại cần kiểm tra điều khoản/cấp phép của dự án.
