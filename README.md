# gmgn_wallet_bot

Open-source Solana copy trading bot.

## Installation

```bash
pip install -r requirements.txt
```

## Environment Setup

```bash
cp .env.template .env
# edit .env and provide PRIVATE_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
```

## Quick Start

```bash
python gmgn_wallet_bot.py mirror --seed trending --min-profit 5
```

## Smoke Test

Verify the bot starts correctly using the smoke test:

```bash
pytest tests/smoke.py
```

The test should complete in a few seconds with no failures.
