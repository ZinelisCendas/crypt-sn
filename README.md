# flipside_wallet_bot

Open-source Solana copy trading bot with safety checks and adaptive sizing.

The engine now uses the **Flipside Cooperation‑API** to fetch swap routes and submit transactions via HTTP rather than the WebSocket interface.

## Installation

```bash
pip install -r requirements.txt
```

This project now relies on the official `flipside` SDK.

## Environment Setup

```bash
cp .env.template .env
# edit .env and provide PRIVATE_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
```

## Quick Start

```bash
python main.py
pytest tests/smoke.py
```

### Running the checks

This project uses `ruff`, `black`, `mypy` and `pytest` for linting and tests. Run them locally before opening a pull request:

```bash
ruff check .
black --check .
mypy .
pytest -q
```


## Security

For larger deployments or balances above a few thousand USD, consider using a
hardware wallet or YubiHSM so that the private key never leaves secure
hardware.
