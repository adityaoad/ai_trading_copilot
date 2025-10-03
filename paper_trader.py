import os, csv, time

TRADES_PATH = "trades_log.csv"
FIELDS = [
    "ts","ticker","side","entry_spot","tp_spot","sl_spot",
    "shares","contracts","risk_per_share","max_loss",
    "status"  # OPEN/CLOSED
]

def now_ts():
    return time.strftime("%Y-%m-%d %H:%M:%S")

def open_trade(row: dict, path: str = TRADES_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    is_new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new:
            w.writeheader()
        out = {k: row.get(k, "") for k in FIELDS}
        w.writerow(out)
