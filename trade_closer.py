import pandas as pd
from datetime import datetime, timedelta

def _to_date(s):
    # handle "YYYY-MM-DD HH:MM:SS" or date-only
    try:
        return pd.to_datetime(s).normalize()
    except Exception:
        return pd.NaT

def _first_hit(row, px: pd.DataFrame, max_hold_days: int):
    """
    Find the first day after entry where TP or SL is touched using daily OHLC.
    Returns (close_date, close_spot, reason) or (None, None, None).
    """
    side = str(row.get("side", "")).upper()
    entry = _to_date(row.get("ts"))
    if pd.isna(entry) or side not in ("LONG", "SHORT"):
        return None, None, None

    tp = float(row.get("tp_spot", None))
    sl = float(row.get("sl_spot", None))
    entry_spot = float(row.get("entry_spot", None))

    # price rows strictly AFTER entry date, up to hold window
    start = entry + pd.Timedelta(days=1)
    end = entry + pd.Timedelta(days=max_hold_days)
    df = px.loc[(px.index >= start) & (px.index <= end)]
    if df.empty:
        return None, None, None

    if side == "LONG":
        # TP: high >= tp ; SL: low <= sl
        tp_hits = df[df["high"] >= tp]
        sl_hits = df[df["low"]  <= sl]
    else:  # SHORT
        # TP for short = price goes DOWN to tp (low <= tp)
        # SL for short = price goes UP to sl (high >= sl)
        tp_hits = df[df["low"]  <= tp]
        sl_hits = df[df["high"] >= sl]

    # choose earliest hit by date
    first_tp_date = tp_hits.index.min() if not tp_hits.empty else None
    first_sl_date = sl_hits.index.min() if not sl_hits.empty else None

    # decide which happened first
    if first_tp_date is not None and (first_sl_date is None or first_tp_date <= first_sl_date):
        d = first_tp_date
        # fill price at touch; use tp as proxy
        return d, float(tp), "TP"
    if first_sl_date is not None:
        d = first_sl_date
        return d, float(sl), "SL"

    # no hit within window
    # time exit on last available bar in window
    lastd = df.index.max()
    close_spot = float(df.loc[lastd, "close"])
    return lastd, close_spot, "TIME"

def auto_close_trades(prices_path="data/prices.csv",
                      trades_path="trades_log.csv",
                      max_hold_days: int = 20):
    """
    Marks OPEN trades CLOSED when TP/SL (or time) is hit.
    Adds columns: close_ts, close_spot, reason, realized_pnl.
    Returns a summary dict.
    """
    # load prices (daily OHLC)
    px = pd.read_csv(prices_path, parse_dates=["datetime"]).set_index("datetime").sort_index()
    # ensure numeric
    for c in ["open","high","low","close","volume"]:
        px[c] = pd.to_numeric(px[c], errors="coerce")
    px = px.dropna(subset=["open","high","low","close"])

    # load trades
    tdf = pd.read_csv(trades_path) if pd.io.common.file_exists(trades_path) else pd.DataFrame()
    if tdf.empty:
        return {"closed": 0, "open_remaining": 0}

    # ensure needed cols exist
    for col in ["status","side","entry_spot","tp_spot","sl_spot","shares","contracts","ts"]:
        if col not in tdf.columns:
            tdf[col] = None

    closed_count = 0
    for i, row in tdf.iterrows():
        if str(row.get("status","")).upper() != "OPEN":
            continue

        close_date, close_spot, reason = _first_hit(row, px, max_hold_days)
        if close_date is None:
            continue

        # realized PnL (equity leg only)
        side = str(row.get("side","")).upper()
        shares = int(row.get("shares") or 0)
        entry_spot = float(row.get("entry_spot") or 0.0)

        if side == "LONG":
            pnl = (close_spot - entry_spot) * shares
        elif side == "SHORT":
            pnl = (entry_spot - close_spot) * shares
        else:
            pnl = 0.0

        tdf.loc[i, "status"] = "CLOSED"
        tdf.loc[i, "close_ts"] = close_date.strftime("%Y-%m-%d")
        tdf.loc[i, "close_spot"] = round(close_spot, 4)
        tdf.loc[i, "reason"] = reason
        tdf.loc[i, "realized_pnl"] = round(pnl, 2)
        closed_count += 1

    tdf.to_csv(trades_path, index=False)
    open_remaining = (tdf["status"].str.upper() == "OPEN").sum()
    return {"closed": closed_count, "open_remaining": int(open_remaining)}
