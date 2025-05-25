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
# optional HELIUS_API_KEY for priority fee estimates
```

## Quick Start

```bash
python main.py
pytest tests/smoke.py
```


## Security

For larger deployments or balances above a few thousand USD, consider using a
hardware wallet or YubiHSM so that the private key never leaves secure
hardware.
