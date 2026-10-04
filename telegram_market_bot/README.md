# Telegram Market Digest Bot

Bot Telegram cá nhân dùng **vnstock** để tóm tắt diễn biến thị trường Việt Nam và gom tin vĩ mô có khả năng ảnh hưởng đến thị trường.

## Lịch mặc định

Bot gửi **07:30 sáng mỗi ngày theo Asia/Ho_Chi_Minh**.

Bản tin sáng dùng:
- phiên giao dịch gần nhất;
- độ rộng, thanh khoản, top tăng/giảm và khối ngoại của phiên gần nhất;
- tin vĩ mô trong khoảng 30 giờ gần nhất để bắt các diễn biến qua đêm.

## Cách setup dễ nhất — không cần biết Chat ID

Workflow `.github/workflows/telegram-market-daily.yml` chạy lúc **00:30 UTC = 07:30 Việt Nam** mỗi ngày.

Chỉ cần tạo **1 GitHub Secret**:

`Settings → Secrets and variables → Actions → New repository secret`

- Name: `TELEGRAM_BOT_TOKEN`
- Secret: token mới lấy từ BotFather

Sau đó:
1. Mở bot trên Telegram.
2. Gửi cho bot một tin `/start`.
3. Vào **Actions → Telegram Daily Market Report → Run workflow** để thử ngay.

Nếu không có `TELEGRAM_CHAT_ID`, bot sẽ tự đọc tin nhắn gần nhất gửi cho bot và lấy Chat ID của cuộc trò chuyện riêng đó. Vì vậy không cần tự mở API `getUpdates` hay copy Chat ID thủ công.

> Không ghi token trực tiếp vào code, README, workflow hay file .env được commit.

## Chức năng

- `/today` hoặc `/market`: tạo bản tin ngay khi chạy bot dạng service.
- `/news`: chỉ lấy tin vĩ mô.
- `/start`: đăng ký chat nếu bot chạy dạng service 24/7.
- `/stop`: hủy đăng ký.

## Chạy dạng bot 24/7

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

## Docker

```bash
docker build -f telegram_market_bot/Dockerfile -t vnstock-market-bot .
docker run -d --restart unless-stopped \
  --name vnstock-market-bot \
  -e TELEGRAM_BOT_TOKEN="TOKEN_CUA_BAN" \
  -v "$(pwd)/bot-data:/app/data" \
  vnstock-market-bot
```

## Cấu hình mặc định

- `REPORT_HOUR=7`
- `REPORT_MINUTE=30`
- `NEWS_LOOKBACK_HOURS=30`
- `MAX_NEWS_ITEMS=8`
- `BOT_TIMEZONE=Asia/Ho_Chi_Minh`

> Đây là bản tin tổng hợp tự động, không phải khuyến nghị đầu tư. Repo vnstock có giấy phép tùy chỉnh cho mục đích cá nhân/nghiên cứu phi thương mại; nếu triển khai thương mại cần kiểm tra điều khoản/cấp phép của dự án.
