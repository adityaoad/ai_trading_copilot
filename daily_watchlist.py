
#!/usr/bin/env python3
# daily_watchlist.py
# Builds a daily watchlist from Yahoo gainers/losers (if available) plus crypto (BTC/ETH/DOGE/SOL/XRP)
# Outputs a table and saves daily_watchlist.json with trade plans.

import argparse, sys, json
from datetime import datetime, timezone
from typing import List, Dict, Any
import pandas as pd
import numpy as np
import yfinance as yf

try:
    from yahooquery import Screener
    HAVE_YQ = True
except Exception:
    HAVE_YQ = False

CRYPTO_TICKERS = ["BTC-USD","ETH-USD","DOGE-USD","SOL-USD","XRP-USD"]

def utcnow():
    return datetime.now(timezone.utc).isoformat()

def normalize_yf(sym: str, period: str, interval: str) -> pd.DataFrame:
    df = yf.download(sym, period=period, interval=interval, auto_adjust=True, progress=False, group_by="column")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if df is None or len(df) == 0:
        raise ValueError("empty frame")
    df = df.rename(columns=str.lower).reset_index()
    ts_col = "date" if "date" in df.columns else ("datetime" if "datetime" in df.columns else None)
    if ts_col is None:
        ts_col = df.columns[0]
    df = df.rename(columns={ts_col: "timestamp"})
    for c in ["open","high","low","close","volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["symbol"] = sym
    req = ["timestamp","open","high","low","close","volume","symbol"]
    missing = [c for c in req if c not in df.columns]
    if missing:
        raise ValueError(f"normalized frame missing required columns: {missing}")
    df = df[req].dropna().reset_index(drop=True)
    if df.empty:
        raise ValueError("normalized frame became empty after dropna()")
    return df

def rsi14(close: pd.Series) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0).rolling(14).mean()
    down = (-delta.clip(upper=0)).rolling(14).mean()
    rs = up / down
    return 100 - 100 / (1 + rs)

def atr14(high, low, close) -> pd.Series:
    hl = high - low
    hc = (high - close.shift()).abs()
    lc = (low - close.shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(14).mean()

def compute_plan(df: pd.DataFrame, risk: float) -> Dict[str, Any]:
    d = df.copy().sort_values("timestamp")
    d["rsi14"] = rsi14(d["close"])
    d["atr14"] = atr14(d["high"], d["low"], d["close"])
    d = d.dropna().reset_index(drop=True)
    r = d.iloc[-1]

    price = float(r["close"])
    atr = float(r["atr14"])

    # ATR floor to avoid zero-distance stops
    if price <= 1.0:
        atr = max(atr, max(0.01 * price, 0.001))
    else:
        atr = max(atr, 0.0025 * price)

    entry = price
    stop  = entry - 1.5 * atr
    target= entry + 3.0 * atr

    per_unit = max(entry - stop, 1e-6)
    units = int(risk // per_unit) if per_unit > 0 else 0

    return {
        "entry": round(entry, 5 if price < 1 else 2),
        "stop": round(stop, 5 if price < 1 else 2),
        "target": round(target, 5 if price < 1 else 2),
        "rsi": round(float(r["rsi14"]), 2),
        "atr": round(atr, 5 if price < 1 else 2),
        "units": units
    }

def fetch_auto_equities(max_each: int = 15) -> List[str]:
    if not HAVE_YQ:
        return []
    syms = set()
    try:
        s = Screener()
        for key in ("day_gainers","day_losers"):
            try:
                data = s.get_screeners(key, count=max_each)
                items = data.get("quotes") or data.get(key, {}).get("quotes") or []
                for it in items:
                    sym = it.get("symbol")
                    exch = (it.get("fullExchangeName") or "")
                    if sym and ("OTC" not in exch and "Pink" not in exch):
                        syms.add(sym)
            except Exception:
                continue
    except Exception:
        return []
    return list(syms)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto", action="store_true", help="Pull equities from Yahoo gainers/losers")
    ap.add_argument("--symbols", nargs="*", default=None, help="Explicit stock symbols (skip auto)")
    ap.add_argument("--risk", type=float, default=10.0, help="Risk dollars per trade")
    args = ap.parse_args()

    equities: List[str] = []
    if args.symbols:
        equities = args.symbols
    elif args.auto:
        equities = fetch_auto_equities()
    print(f"[auto] equities gathered: {len(equities)}")

    rows = []
    ideas = []

    for sym in equities:
        try:
            df = normalize_yf(sym, period="1y", interval="1d")
            plan = compute_plan(df, risk=args.risk)
            rows.append({"symbol": sym, "asset": "equity", **plan})
            ideas.append({"symbol": sym, "asset": "equity", **plan})
        except Exception as e:
            rows.append({"symbol": sym, "asset": "equity", "error": str(e)})

    for sym in CRYPTO_TICKERS:
        try:
            df = normalize_yf(sym, period="30d", interval="1h")
            plan = compute_plan(df, risk=args.risk)
            rows.append({"symbol": sym, "asset": "crypto", **plan})
            ideas.append({"symbol": sym, "asset": "crypto", **plan})
        except Exception as e:
            rows.append({"symbol": sym, "asset": "crypto", "error": str(e)})

    out = pd.DataFrame(rows)
    print(out.to_string(index=False))

    with open("daily_watchlist.json", "w") as f:
        json.dump({"generated_at_utc": utcnow(), "ideas": ideas}, f, indent=2)
    print("\nSaved daily_watchlist.json")

if __name__ == "__main__":
    main()
