from __future__ import annotations

import logging
import logging.config
from pythonjsonlogger import jsonlogger

import argparse
import pandas as pd
from config import PRIV_KEY
from flipside_wallet_bot import main as run_bot
from helpers import calc_report


class SecretFilter(logging.Filter):
    """Redact private key or raw transaction bytes from log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        msg = record.getMessage()
        if PRIV_KEY and PRIV_KEY in msg:
            record.msg = msg.replace(PRIV_KEY, "[REDACTED]")
            if record.args:
                record.args = tuple(
                    "[REDACTED]" if a == PRIV_KEY else a for a in record.args
                )
        if record.args:
            record.args = tuple(
                "[REDACTED]" if isinstance(a, (bytes, bytearray)) else a
                for a in record.args
            )
        if isinstance(record.msg, (bytes, bytearray)):
            record.msg = "[REDACTED]"
            record.args = ()
        return True


LOG_CONFIG = {
    "version": 1,
    "formatters": {"json": {"()": jsonlogger.JsonFormatter}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

logging.config.dictConfig(LOG_CONFIG)
logging.getLogger().addFilter(SecretFilter())


def cli() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=False)
    run_p = sub.add_parser("run")
    run_p.add_argument("--ws-log", default=None)
    run_p.add_argument("--dry-run", action="store_true")

    rep_p = sub.add_parser("report")
    rep_p.add_argument("file")

    args = parser.parse_args()
    if args.cmd == "report":
        df = pd.read_csv(
            args.file,
            header=None,
            names=["ts", "address", "token", "side", "qty", "price", "nav_after"],
        )
        cagr, sharpe, dd = calc_report(df)
        print(f"CAGR {cagr:.3f} Sharpe {sharpe:.3f} MaxDD {dd:.3f}")
    else:
        run_bot(args.ws_log, args.dry_run)


if __name__ == "__main__":
    cli()
