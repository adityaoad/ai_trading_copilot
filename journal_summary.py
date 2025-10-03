cat > journal_summary.py << 'PY'
#!/usr/bin/env python3
# journal_summary.py
# Summarize trades_log.csv -> overall & per-symbol stats.

import argparse
import sys
import pandas as pd
from pathlib import Path

def load_trades(path: Path) -> pd.DataFrame:
    if not path.exists():
        sys.exit(f"File not found: {path}")
    df = pd.read_csv(path)
    if df.empty:
        sys.exit("trades_log.csv is empty.")
    # Ensure expected columns
    needed = {"timestamp_utc","event","symbol","side","last","entry","stop",
              "target","units","rr","pnl_dollars","pnl_pct","hold_minutes"}
    missing = [c for c in needed if c not in df.columns]
    if missing:
        sys.exit(f"Missing columns in log: {missing}")
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], errors="coerce", utc=True)
    return df.sort_values("timestamp_utc").reset_index(drop=True)

def overall_stats(df: pd.DataFrame) -> pd.DataFrame:
    closed = df[df["event"].str.startswith("CLOSE")].copy()
    if closed.empty:
        return pd.DataFrame([{"trades":0,"win_rate_%":0.0,"net_pnl_$":0.0,
                              "avg_pnl_$":0.0,"avg_hold_min":0.0}])
    wins = closed["pnl_dollars"] > 0
    out = {
        "trades": int(len(closed)),
        "win_rate_%": round(100.0 * wins.mean(), 2),
        "net_pnl_$": round(closed["pnl_dollars"].sum(), 2),
        "avg_pnl_$": round(closed["pnl_dollars"].mean(), 2),
        "avg_hold_min": round(closed["hold_minutes"].mean(), 1),
        "best_$": round(closed["pnl_dollars"].max(), 2),
        "worst_$": round(closed["pnl_dollars"].min(), 2),
    }
    return pd.DataFrame([out])

def per_symbol_stats(df: pd.DataFrame) -> pd.DataFrame:
    closed = df[df["event"].str.startswith("CLOSE")].copy()
    if closed.empty:
        return pd.DataFrame(columns=["symbol","trades","win_rate_%","net_pnl_$",
                                     "avg_pnl_$","avg_hold_min"])
    g = closed.groupby("symbol", as_index=False).agg(
        trades=("pnl_dollars","count"),
        win_rate_%=("pnl_dollars", lambda s: round(100.0*(s>0).mean(),2)),
        net_pnl_$=("pnl_dollars", lambda s: round(s.sum(),2)),
        avg_pnl_$=("pnl_dollars", lambda s: round(s.mean(),2)),
        avg_hold_min=("hold_minutes", lambda s: round(s.mean(),1)),
    )
    return g.sort_values("net_pnl_$", ascending=False).reset_index(drop=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="trades_log.csv", help="Path to trades log CSV")
    args = ap.parse_args()
    path = Path(args.csv)
    df = load_trades(path)
    print("\n=== OVERALL ===")
    print(overall_stats(df).to_string(index=False))
    print("\n=== PER SYMBOL ===")
    per = per_symbol_stats(df)
    print("(no closed trades yet)" if per.empty else per.to_string(index=False))
    overall_stats(df).to_csv("summary_overall.csv", index=False)
    per.to_csv("summary_by_symbol.csv", index=False)

if __name__ == "__main__":
    main()
PY
