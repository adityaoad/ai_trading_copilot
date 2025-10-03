#!/usr/bin/env python3
# monitor_entries.py (fast batch version)
# - Polls all symbols in one yfinance.download call (1m data), so it's much faster.
# - Uses a tiny entry buffer (0.1% default) to avoid instant re-triggers.
# - Falls back to per-symbol fetch if batch data missing.

import argparse, json, time, sys
from datetime import datetime, timezone
from typing import Dict, Any, List
import pandas as pd
import yfinance as yf

def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def batch_last_prices(symbols: List[str]) -> Dict[str, float]:
    """Return last close for each symbol using a single yfinance download call."""
    out: Dict[str, float] = {}
    if not symbols:
        return out
    try:
        data = yf.download(
            tickers=" ".join(symbols),
            period="1d",
            interval="1m",
            group_by="ticker",
            progress=False,
            auto_adjust=False,
        )
        # When multiple tickers: columns become a MultiIndex (ticker, field)
        if isinstance(data.columns, pd.MultiIndex):
            for sym in symbols:
                try:
                    sub = data[sym]
                    if not sub.empty:
                        out[sym] = float(sub["Close"].dropna().iloc[-1])
                except Exception:
                    continue
        else:
            # Single ticker case: no MultiIndex
            if not data.empty and "Close" in data.columns:
                out[symbols[0]] = float(data["Close"].dropna().iloc[-1])
    except Exception:
        pass
    # Fallbacks for any missing symbols
    for sym in symbols:
        if sym not in out:
            try:
                t = yf.Ticker(sym)
                hist = t.history(period="1d", interval="1m")
                if hist is None or hist.empty:
                    hist = t.history(period="5d", interval="1d")
                if hist is not None and not hist.empty:
                    out[sym] = float(hist["Close"].dropna().iloc[-1])
            except Exception:
                continue
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=10, help="Minutes between checks (0 = run once & exit)")
    ap.add_argument("--buffer-bps", type=float, default=10.0, help="Entry buffer in basis points (0.1% = 10)")
    args = ap.parse_args()

    try:
        with open("daily_watchlist.json","r") as f:
            payload = json.load(f)
    except Exception:
        print("No daily_watchlist.json found.")
        sys.exit(0)

    ideas = payload.get("ideas", [])
    if not ideas:
        print("No ideas to monitor.")
        sys.exit(0)

    symbols = sorted({i["symbol"] for i in ideas})
    buf = args.buffer_bps / 10000.0

    print(f"Loaded {len(ideas)} ideas across {len(symbols)} symbols. Checking every {args.interval} minutes.\n")

    triggered = set()
    def poll_once():
        print(f"[{utcnow()}] polling...")
        last = batch_last_prices(symbols)
        if not last:
            print("  (no prices fetched; retry next cycle)")
            return
        for idea in ideas:
            key = f"{idea['symbol']}:{idea.get('entry')}"
            if key in triggered:
                continue
            lp = last.get(idea["symbol"])
            if lp is None:
                print(f"  {idea['symbol']}: no price this tick")
                continue
            entry = float(idea["entry"])
            stop  = float(idea["stop"])
            target= float(idea["target"])

            # Long-only triggers
            hit = lp >= entry * (1 + buf)
            if hit:
                rr_denom = max(abs(entry - stop), 1e-6)
                rr = abs(target - entry) / rr_denom
                print("======================================================")
                print(f"TRIGGER {idea['symbol']} @ {round(lp,5)} | Side: long")
                print(f" Entry: {entry} | Stop: {stop} | Target: {target} | R:R ~ {round(rr,2)}")
                print(f" Units: {idea.get('units', 0)}")
                print("======================================================")
                triggered.add(key)

    # First poll immediately
    poll_once()
    if args.interval <= 0:
        return

    while True:
        try:
            time.sleep(max(10, args.interval * 60))
        except KeyboardInterrupt:
            print("\nStopping monitor.")
            break
        poll_once()

if __name__ == "__main__":
    main()
