import os, csv, time

LOG_PATH = "signals_log.csv"

FIELDS = [
    "ts","ticker","bias","spot","tp_spot","sl_spot",
    "q_lo","q_md","q_hi","sigma",
    "shares","risk_per_share","max_loss",
    "contracts","max_spend"
]

def log_signal(row: dict, path: str = LOG_PATH):
    """Append a row to signals_log.csv (creates file with header if missing)."""
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    is_new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new:
            w.writeheader()
        out = {k: row.get(k, "") for k in FIELDS}
        w.writerow(out)
    print(f"[Logger] wrote to {path}")


def now_ts():
    return time.strftime("%Y-%m-%d %H:%M:%S")
