#!/usr/bin/env python3
# monitor_entries.py
# Fast batch monitor: reads daily_watchlist.json, fetches prices in bulk,
# triggers when entry is crossed (with buffer), logs CSV, optional Telegram alerts.

import os, json, time, argparse, csv
from datetime import datetime, timezone
import pandas as pd
import yfinance as yf
import requests

def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def send_telegram(msg: str):
    tok = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{tok}/sendMessage",
            data={"chat_id": chat, "text": msg}, timeout=5
        )
    except Exception:
        pass

def batch_last_prices(symbols):
    """Fetch last prices for a list of symbols."""
    out = {}
    if not symbols:
        return out
    try:
        df = yf.download(
            tickers=" ".join(symbols),
            period="1d",
            interval="1m",
            auto_adjust=True,
            progress=False
        )
        # MultiIndex columns when >1 ticker
        if isinstance(df.columns, pd.MultiIndex):
            close = df["Close"].iloc[-1].dropna()
            for sym in close.index:
                out[str(sym)] = float(close[sym])
        else:
            out[symbols[0]] = float(df["Close"].iloc[-1])
    except Exception:
        pass

    # fallback for any missing
    missing = [s for s in symbols if s not in out]
    for s in missing:
        try:
            t = yf.Ticker(s)
            h = t.history(period="1d", interval="1m")
            if h is None or h.empty:
                h = t.history(period="5d", interval="1d")
            if h is not None and not h.empty:
                out[s] = float(h["Close"].iloc[-1])
        except Exception:
            pass
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=10,
                    help="Minutes between polls (0 = run once)")
    ap.add_argument("--buffer-bps", type=float, default=10.0,
                    help="Entry buffer in basis points (0.1% = 10)")
    args = ap.parse_args()

    try:
        with open("daily_watchlist.json", "r") as f:
            payload = json.load(f)
    except Exception:
        print("No daily_watchlist.json found.")
        return

    ideas = payload.get("ideas", [])
    if not ideas:
        print("No ideas to monitor.")
        return

    symbols = sorted({i["symbol"] for i in ideas})
    buf = args.buffer_bps / 10000.0

    print(f"Loaded {len(ideas)} ideas across {len(symbols)} symbols. "
          f"Checking every {args.interval} minutes.\n")

    # Prepare CSV log
    log_path = "trades_log.csv"
    if not os.path.exists(log_path):
        with open(log_path, "w", newline="") as f:
            csv.writer(f).writerow(
                ["timestamp_utc", "symbol", "side", "last", "entry", "stop",
                 "target", "units", "rr"]
            )

    triggered = set()
    while True:
        print(f"[{utcnow()}] polling...")
        last_map = batch_last_prices(symbols)

        for idea in ideas:
            key = f"{idea['symbol']}:{idea.get('entry')}"
            if key in triggered:
                continue
            sym = idea["symbol"]
            if sym not in last_map:
                continue

            last = float(last_map[sym])
            entry = float(idea["entry"])
            stop = float(idea["stop"])
            target = float(idea["target"])

            # Long-only triggers
            if last >= entry * (1 + buf):
                rr = abs(target - entry) / max(abs(entry - stop), 1e-6)
                msg = (f"TRIGGER {sym} @ {round(last,5)} | Side: long\n"
                       f"Entry {entry} | Stop {stop} | Target {target} | "
                       f"R:R ~ {round(rr,2)} | Units {idea.get('units',0)}")
                print("="*54)
                print(msg)
                print("="*54)

                with open(log_path, "a", newline="") as f:
                    csv.writer(f).writerow(
                        [utcnow(), sym, "long", round(last,5), entry, stop,
                         target, idea.get("units",0), round(rr,2)]
                    )

                send_telegram(msg)
                triggered.add(key)

        if args.interval <= 0:
            break
        try:
            time.sleep(max(10, args.interval * 60))
        except KeyboardInterrupt:
            print("\nStopping monitor.")
            break

if __name__ == "__main__":
    main()
