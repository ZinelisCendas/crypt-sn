from __future__ import annotations

import logging
import logging.config

from pythonjsonlogger import jsonlogger

from config import PRIV_KEY
from gmgn_wallet_bot import main


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

if __name__ == "__main__":
    main()
