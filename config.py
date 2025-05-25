from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

PRIV_KEY = os.getenv("PRIVATE_KEY", "")
TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELE_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", 8))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", 25))
GLOBAL_DD_PCT = float(os.getenv("GLOBAL_DD_PCT", 20))
MAX_KELLY_F = float(os.getenv("MAX_KELLY_F", 0.25))
ATR_LOOKBACK_MIN = int(os.getenv("ATR_LOOKBACK_MIN", 1440))
PRUNE_INTERVAL_H = float(os.getenv("PRUNE_INTERVAL_H", 6))
JUPITER_URL = "https://quote-api.jup.ag"
PYTH_HIST_URL = "https://hermes.pyth.network/api/historical_price/"
RPC_URL = os.getenv("RPC_URL", "https://api.mainnet-beta.solana.com")
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
