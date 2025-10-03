import math
import pandas as pd
import yfinance as yf

SYMBOL = "AAPL"
ACCOUNT = 500.0
RISK_DOLLARS = 10.0

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

def main():
    df = yf.download(
        SYMBOL,
        period="1y",
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="column",        # <- force single-level columns
    )
    if isinstance(df.columns, pd.MultiIndex):  # <- flatten if still multiindex
        df.columns = df.columns.get_level_values(0)

    if df.empty:
        raise SystemExit(f"No data for {SYMBOL}")

    df = df.rename(columns=str.lower).reset_index()
    # ensure numeric
    for c in ["open","high","low","close","volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["rsi14"] = rsi14(df["close"])
    df["atr14"] = atr14(df["high"], df["low"], df["close"])
    df = df.dropna().reset_index(drop=True)

    r = df.iloc[-1]
    entry  = float(r["close"])
    atr    = float(r["atr14"])
    stop   = float(entry - 1.5 * atr)
    target = float(entry + 3.0 * atr)

    per_unit = abs(entry - stop)
    units = int(RISK_DOLLARS // per_unit) if per_unit > 0 else 0

    print({
        "symbol": SYMBOL,
        "entry": round(entry,2),
        "stop": round(stop,2),
        "target": round(target,2),
        "rsi": round(float(r["rsi14"]),2),
        "atr": round(atr,2),
        "units": units
    })

if __name__ == "__main__":
    main()
import math
import pandas as pd
import yfinance as yf

SYMBOL = "AAPL"
ACCOUNT = 500.0
RISK_DOLLARS = 10.0

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

def main():
    df = yf.download(
        SYMBOL,
        period="1y",
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="column",        # <- force single-level columns
    )
    if isinstance(df.columns, pd.MultiIndex):  # <- flatten if still multiindex
        df.columns = df.columns.get_level_values(0)

    if df.empty:
        raise SystemExit(f"No data for {SYMBOL}")

    df = df.rename(columns=str.lower).reset_index()
    # ensure numeric
    for c in ["open","high","low","close","volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["rsi14"] = rsi14(df["close"])
    df["atr14"] = atr14(df["high"], df["low"], df["close"])
    df = df.dropna().reset_index(drop=True)

    r = df.iloc[-1]
    entry  = float(r["close"])
    atr    = float(r["atr14"])
    stop   = float(entry - 1.5 * atr)
    target = float(entry + 3.0 * atr)

    per_unit = abs(entry - stop)
    units = int(RISK_DOLLARS // per_unit) if per_unit > 0 else 0

    print({
        "symbol": SYMBOL,
        "entry": round(entry,2),
        "stop": round(stop,2),
        "target": round(target,2),
        "rsi": round(float(r["rsi14"]),2),
        "atr": round(atr,2),
        "units": units
    })

if __name__ == "__main__":
    main()
