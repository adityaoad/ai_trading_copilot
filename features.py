import pandas as pd

def make_features(df):
    out = df.copy()
    r = out["close"].pct_change()

    out["r1"] = r
    out["r5"] = out["close"].pct_change(5)
    out["r10"] = out["close"].pct_change(10)
    out["ma5"] = out["close"].rolling(5).mean() / out["close"] - 1
    out["ma10"] = out["close"].rolling(10).mean() / out["close"] - 1
    out["vol5"] = r.rolling(5).std()
    out["vol10"] = r.rolling(10).std()
    out["hi_lo"] = (out["high"] - out["low"]) / out["close"]

    out = out.dropna()
    X = out[["r1","r5","r10","ma5","ma10","vol5","vol10","hi_lo"]]
    y = out["fwd_ret"] if "fwd_ret" in out.columns else None
    return out, X, y
