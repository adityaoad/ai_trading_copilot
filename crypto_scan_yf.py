
# crypto_scan_yf.py
# Scan BTC/ETH/DOGE/SOL/XRP using Yahoo Finance (no exchange API).
# Prints entry/stop/target/RSI/ATR/units for 1-hour bars.
# Run: python crypto_scan_yf.py

import math
import pandas as pd
import yfinance as yf

SYMS = ["BTC-USD","ETH-USD","DOGE-USD","SOL-USD","XRP-USD"]
INTERVAL = "1h"
PERIOD = "10d"   # enough bars for 14-period indicators; adjust if needed
ACCOUNT = 500.0
RISK_DOLLARS = 10.0

def rsi14(close: pd.Series) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0).rolling(14, min_periods=14).mean()
    down = (-delta.clip(upper=0)).rolling(14, min_periods=14).mean()
    rs = up / down
    return 100 - 100 / (1 + rs)

def atr14(high, low, close) -> pd.Series:
    hl = high - low
    hc = (high - close.shift()).abs()
    lc = (low - close.shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(14, min_periods=14).mean()

def prep_df(df: pd.DataFrame) -> pd.DataFrame:
    # Normalize yfinance dataframe to have: timestamp, open, high, low, close, volume
    if df is None or df.empty:
        raise ValueError("empty df")
    # Flatten columns if multiindex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    # Reset index -> get datetime column regardless of name
    df = df.copy()
    df.reset_index(inplace=True)
    # Normalize column names
    cols_lower = {c: c.lower() for c in df.columns}
    df.rename(columns=cols_lower, inplace=True)

    # Find the timestamp column
    ts_candidate = None
    for candidate in ("datetime", "date", "index", "time"):
        if candidate in df.columns:
            ts_candidate = candidate
            break
    if ts_candidate is None:
        # Fallback to first column if it's datetime-like
        first = df.columns[0]
        if pd.api.types.is_datetime64_any_dtype(df[first]):
            ts_candidate = first
        else:
            raise KeyError("No timestamp-like column after reset_index")

    df.rename(columns={ts_candidate: "timestamp"}, inplace=True)
    # lower-case OHLCV
    for col in ["open","high","low","close","volume"]:
        if col not in df.columns:
            df[col] = pd.NA
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop rows with missing close
    df = df.dropna(subset=["close"]).copy()
    return df[["timestamp","open","high","low","close","volume"]]

def one_symbol(sym: str):
    # Try short period first; if insufficient rows for indicators, expand
    tried = []
    df = None
    for per in (PERIOD, "30d", "60d"):
        tried.append(per)
        df = yf.download(sym, period=per, interval=INTERVAL, auto_adjust=True, progress=False, group_by="column")
        if df is not None and not df.empty:
            try:
                tmp = prep_df(df)
                if len(tmp) >= 50:
                    break
            except Exception:
                continue
    if df is None or df.empty:
        raise ValueError(f"no data returned for {sym} (tried periods: {tried})")
    # Final prep
    dfp = prep_df(df)
    d = dfp.copy()
    d["rsi14"] = rsi14(d["close"])
    d["atr14"] = atr14(d["high"], d["low"], d["close"])
    d = d.dropna().reset_index(drop=True)
    if d.empty:
        raise ValueError("not enough data after indicators")
    r = d.iloc[-1]
    entry = float(r["close"])
    atr = float(r["atr14"])
    stop = entry - 1.5 * atr
    target = entry + 3.0 * atr
    per_unit = abs(entry - stop)
    units = int(RISK_DOLLARS // per_unit) if per_unit > 0 else 0

    return {
        "symbol": sym,
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "target": round(target, 2),
        "rsi": round(float(r["rsi14"]), 2),
        "atr": round(atr, 2),
        "units": units,
    }

def main():
    rows = []
    for s in SYMS:
        try:
            rows.append(one_symbol(s))
        except Exception as e:
            rows.append({"symbol": s, "entry": float("nan"), "stop": float("nan"),
                         "target": float("nan"), "rsi": float("nan"), "atr": float("nan"),
                         "units": float("nan"), "error": str(e)})
    df = pd.DataFrame(rows)
    # Order columns
    cols = ["symbol","entry","stop","target","rsi","atr","units"]
    if "error" in df.columns:
        cols += ["error"]
    print(df[cols].to_string(index=False))

if __name__ == "__main__":
    main()
