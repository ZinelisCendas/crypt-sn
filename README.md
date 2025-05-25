# gmgn_wallet_bot

Open-source Solana copy trading bot.

## Quick Start

```bash
pip install -r requirements.txt   # aiohttp websockets pandas prometheus-client gmgnai-wrapper
cp .env.template .env             # fill PRIVATE_KEY etc.
python gmgn_wallet_bot.py mirror --seed trending --min-profit 5
```

## Running Tests

Execute the unit tests with `pytest`:

```bash
pytest -q
```
