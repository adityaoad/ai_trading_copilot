# multi_scan.py
# Multi-symbol daily scanner (equities only) with auto-movers via yahooquery.
# Filters sub-$1 "cents" penny stocks and mid/large caps by volume/relative volume.
# Reuses a simple indicator set to produce entry/stop/target/units.
#
# Run:
#   python multi_scan.py --auto --equity 500 --risk 10
# Or pass explicit tickers:
#   python multi_scan.py --symbols AAPL NVDA QQQ

import argparse
import math
from typing import List, Dict, Any, Tuple
import pandas as pd
import yfinance as yf

# ---------- indicators ----------

def rsi14(close: pd.Series) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).rolling(14).mean()
    dn = (-d.clip(upper=0)).rolling(14).mean()
    rs = up / dn
    return 100 - 100 / (1 + rs)

def atr14(h: pd.Series, l: pd.Series, c: pd.Series) -> pd.Series:
    hl = h - l
    hc = (h - c.shift()).abs()
    lc = (l - c.shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(14).mean()

def compute_plan(symbol: str, period: str="1y", interval: str="1d",
                 account: float=500.0, risk_dollars: float=10.0) -> Dict[str, Any]:
    df = yf.download(symbol, period=period, interval=interval, auto_adjust=True, progress=False, group_by="column")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if df.empty:
        return {"symbol": symbol, "error": "no data"}
    df = df.rename(columns=str.lower).reset_index()
    for c in ["open","high","low","close","volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["rsi14"] = rsi14(df["close"])
    df["atr14"] = atr14(df["high"], df["low"], df["close"])
    df = df.dropna()
    if df.empty:
        return {"symbol": symbol, "error": "insufficient data"}
    r = df.iloc[-1]
    entry = float(r["close"]); atr = float(r["atr14"])
    stop = float(entry - 1.5*atr); target = float(entry + 3.0*atr)
    per_unit = abs(entry - stop)
    units = int(risk_dollars // per_unit) if per_unit > 0 else 0
    return {
        "symbol": symbol, "entry": round(entry,2), "stop": round(stop,2), "target": round(target,2),
        "rsi": round(float(r["rsi14"]),2), "atr": round(atr,2), "units": units
    }

# ---------- movers (yahooquery) ----------

def fetch_movers(max_equities:int=60) -> List[str]:
    try:
        from yahooquery import Screener
        s = Screener()
        tickers = set()
        for key in ("day_gainers","day_losers"):
            data = s.get_screeners(key, count=max_equities)
            items = data.get("quotes") or data.get(key, {}).get("quotes") or []
            for it in items:
                sym = it.get("symbol")
                if sym:
                    tickers.add(sym)
        return list(tickers)
    except Exception as e:
        print(f"[movers] yahooquery error: {e}")
        return []

def filter_buckets(symbols: List[str], penny_ceiling: float=1.0,
                   min_vol_penny:int=100_000, min_vol_big:int=2_000_000,
                   relvol_floor: float=1.5) -> Tuple[List[str], List[str]]:
    try:
        from yahooquery import Ticker
        t = Ticker(symbols)
        q = t.quotes
        if isinstance(q, dict):
            q = list(q.values())
        penny, big = [], []
        for itm in q:
            sym = itm.get("symbol")
            price = itm.get("regularMarketPrice")
            vol = itm.get("regularMarketVolume") or itm.get("averageDailyVolume10Day") or itm.get("averageDailyVolume3Month")
            avg10 = itm.get("averageDailyVolume10Day") or itm.get("averageDailyVolume3Month") or 0
            exch = itm.get("fullExchangeName") or ""
            if not sym or price is None or vol is None:
                continue
            if "OTC" in exch or "Pink" in exch:
                continue
            relvol = float(vol)/float(avg10) if avg10 else 0.0
            if price <= penny_ceiling and price >= 0.05 and vol >= min_vol_penny and relvol >= relvol_floor:
                penny.append(sym)
            elif price > penny_ceiling and vol >= min_vol_big:
                big.append(sym)
        # cap list sizes
        return penny[:60], big[:60]
    except Exception as e:
        print(f"[movers] filter error: {e}")
        return [], []

# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description="Multi-symbol daily scanner with auto-movers")
    ap.add_argument("--auto", action="store_true", help="Auto-pull movers via yahooquery")
    ap.add_argument("--symbols", nargs="*", default=None, help="Explicit list of tickers")
    ap.add_argument("--equity", type=float, default=500.0, help="Account equity (for sizing)")
    ap.add_argument("--risk", type=float, default=10.0, help="Risk dollars per trade")
    ap.add_argument("--penny-ceil", type=float, default=1.0, help="Max price for 'cents' bucket")
    ap.add_argument("--min-vol-penny", type=int, default=100_000, help="Min volume for penny bucket")
    ap.add_argument("--min-vol-big", type=int, default=2_000_000, help="Min volume for big bucket")
    ap.add_argument("--relvol", type=float, default=1.5, help="Min relative volume for penny bucket")
    args = ap.parse_args()

    tickers = []
    if args.symbols:
        tickers = args.symbols
    elif args.auto:
        syms = fetch_movers()
        penny, big = filter_buckets(syms, args.penny_ceil, args.min_vol_penny, args.min_vol_big, args.relvol)
        tickers = penny + big
        print(f"[auto] penny={len(penny)} big={len(big)} total={len(tickers)}")
        if not tickers:
            tickers = ["QQQ","SPY"]

    if not tickers:
        print("No symbols provided. Use --auto or --symbols AAPL NVDA ...")
        return

    rows = []
    for sym in tickers:
        plan = compute_plan(sym, account=args.equity, risk_dollars=args.risk)
        rows.append(plan)

    df = pd.DataFrame(rows)
    print(df.to_string(index=False))

if __name__ == "__main__":
    main()
