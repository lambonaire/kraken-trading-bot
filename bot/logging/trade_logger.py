# bot/logging/trade_logger.py

import csv
from pathlib import Path
from datetime import datetime

LOG_FILE = Path("logs/trades.csv")

def log_event(symbol, event, level, entry_price, position_size, extra=""):

    LOG_FILE.parent.mkdir(exist_ok=True)

    file_exists = LOG_FILE.exists()

    with open(LOG_FILE, "a", newline="") as f:

        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "timestamp",
                "symbol",
                "event",
                "level",
                "entry_price",
                "position_size",
                "extra"
            ])

        writer.writerow([
            datetime.utcnow().isoformat(),
            symbol,
            event,
            level,
            entry_price,
            position_size,
            extra
        ])
