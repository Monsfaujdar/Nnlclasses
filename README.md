# Nnlclasses — Telegram Bot

A Python Telegram bot for processing Telegram links and downloading/forwarding Telegram content.

## Features

- Pyrofork-based Telegram client/bot
- Login system using Telegram API credentials
- Processes single Telegram post links and post ranges
- Supports multiple Telegram links in one message
- Sequential queue processing with configurable waiting time
- Cancel an active queue with `/cancel`
- MongoDB-backed data storage
- Optional destination channel/supergroup configuration

## Requirements

- Python 3.10+
- Telegram `API_ID` and `API_HASH`
- Telegram `BOT_TOKEN`
- MongoDB connection URI
- A Telegram bot with the required permissions in the destination chat/channel

## Configuration

Set the environment variables required by `config.py`:

- `BOT_TOKEN`
- `API_ID`
- `API_HASH`
- `ADMINS`
- `DB_URI`
- `DB_NAME` (optional; defaults to `downbot`)
- `CHANNEL_ID` (optional)
- `WAITING_TIME` (optional; defaults to `20` seconds)
- `LOGIN_SYSTEM` (optional; defaults to `true`)
- `ERROR_MESSAGE` (optional; defaults to `true`)

Do not commit API keys, bot tokens, session strings, database credentials, or other secrets.

## Running

```bash
pip install -r requirements.txt
python3 bot.py
```

For a worker platform, use:

```bash
python3 bot.py
```

## Telegram usage

Send one or more Telegram links, for example:

```text
https://t.me/channel/101
https://t.me/channel/102
https://t.me/channel/103
```

Use `/cancel` to stop the current queue.

## License

This project is distributed under the MIT License. See `LICENSE` for details.
