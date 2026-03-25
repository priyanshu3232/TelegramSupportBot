# Telegram bot setup

This project uses `python-telegram-bot` and currently supports:

- `/start`
- `/help`

## 1) Install dependencies

```bash
pip install -r requirements.txt
```

## 2) Set your bot token

Create a bot with [@BotFather](https://t.me/BotFather), then set `BOT_TOKEN`.

PowerShell:

```powershell
$env:BOT_TOKEN="7980268883:AAGCt-kFTnXh7ng3PVSTd02SsFkHSaCwiaA"
```

CMD:

```cmd
set BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
```

## 3) Run the bot

```bash
python bot.py
```
