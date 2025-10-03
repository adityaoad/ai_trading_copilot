#!/usr/bin/env python3
# evaluator.py — end-of-day scoring of today's watchlist
# Checks: (1) did entry cross today? (2) if yes, did target or stop get hit first?
# Logs a row per symbol to eval_log.csv

import json, sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import yfinance as yf

PROJECT_DIR = Path.home() / "Documents" / "ai_trading_copilot"
WATCHLIST = PROJECT_DIR / "daily_watchlist.json"
EVAL_LOG = PROJECT_DIR / "eval_log.csv"

def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def load_watchlist():
    if not WATCHLIST.exists():
        sys.exit("No daily_watchlist.json found.")
    payload = json.loads(WATCHLIST.read_text())
    ideas = payload.get("ideas", [])
    if not ideas:
        sys.exit("No ideas to evaluate.")
    return ideas

def day_hilo(sym: str, period="5d"):
    df = yf.download(tickers=sym, period=period, interval="1d",
                     auto_adjust=True, progress=False)
    if df is None or df.empty:
        return None
    row = df.iloc[-1]
    # Ensure pure Python floats (avoid pandas/numpy scalar warnings)
    lo = float(row["Low"].item() if hasattr(row["Low"], "item") else row["Low"])
    hi = float(row["High"].item() if hasattr(row["High"], "item") else row["High"])
    opn = float(row["Open"].item() if hasattr(row["Open"], "item") else row["Open"])
    cls = float(row["Close"].item() if hasattr(row["Close"], "item") else row["Close"])
    return lo, hi, opn, cls


def score_row(sym, entry, stop, target):
    # EOD logic:
    # If High >= entry → entry was triggered.
    # If entry triggered: if High >= target before Low <= stop -> WIN, else if Low <= stop -> LOSS
    # With only daily bars, we assume worst-case ambiguity is rare; intraday could refine later.
    hilo = day_hilo(sym)
    if not hilo:
        return {"symbol": sym, "status":"no_data"}
    lo, hi, opn, cls = hilo

    triggered = hi >= entry
    result = "no_trigger"
    reached_target = False
    reached_stop = False

    if triggered:
        # If both target and stop are within range, order unknown on daily bars.
        # Use distance from open as tie-breaker proxy (approximation).
        reached_target = hi >= target
        reached_stop = lo <= stop
        if reached_target and not reached_stop:
            result = "win"
        elif reached_stop and not reached_target:
            result = "loss"
        elif reached_target and reached_stop:
            # tie-breaker: whichever is closer to open; heuristic only.
            dist_t = abs(target - opn)
            dist_s = abs(opn - stop)
            result = "win" if dist_t < dist_s else "loss"
        else:
            result = "open"  # entry hit but neither exit touched (rare with wide targets)

    rr = abs(target - entry) / max(abs(entry - stop), 1e-9)
    return {
        "symbol": sym,
        "triggered": int(triggered),
        "result": result,
        "open": round(opn,4),
        "high": round(hi,4),
        "low": round(lo,4),
        "close": round(cls,4),
        "entry": round(entry,4),
        "stop": round(stop,4),
        "target": round(target,4),
        "rr": round(rr,2)
    }

def main():
    ideas = load_watchlist()
    rows = []
    for i in ideas:
        try:
            sym = i["symbol"]
            entry = float(i["entry"]); stop = float(i["stop"]); target = float(i["target"])
            rows.append(score_row(sym, entry, stop, target))
        except Exception as e:
            rows.append({"symbol": i.get("symbol","?"), "status": f"error: {e}"})

    df = pd.DataFrame(rows)
    df.insert(0, "date", datetime.now().date().isoformat())
    df.insert(1, "ts_utc", utcnow())
    header = not EVAL_LOG.exists()
    df.to_csv(EVAL_LOG, mode="a", header=header, index=False)
    print(df[["date","symbol","result","triggered","rr"]].to_string(index=False))

if __name__ == "__main__":
    main()

