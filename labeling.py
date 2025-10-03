import numpy as np

def add_labels(df, horizon=20, tp_sigma=1.0, sl_sigma=0.7, vol_lookback=50):
    """
    Adds trade labels using a triple-barrier style method.
    - df: DataFrame with 'close','high','low'
    - horizon: number of bars to look ahead
    - tp_sigma/sl_sigma: multipliers for take-profit / stop-loss thresholds
    - vol_lookback: rolling window for volatility estimate
    """
    out = df.copy()
    r = out["close"].pct_change()
    sigma = r.rolling(vol_lookback).std().shift(1)

    fwd = out["close"].shift(-horizon)
    fwd_ret = (fwd - out["close"]) / out["close"]

    high_fwd = out["high"].shift(-1).rolling(horizon).max()
    low_fwd  = out["low"].shift(-1).rolling(horizon).min()

    tp = sigma * tp_sigma
    sl = sigma * sl_sigma

    ret_tp = (high_fwd - out["close"]) / out["close"]
    ret_sl = (out["close"] - low_fwd) / out["close"]

    hit_tp = ret_tp >= tp
    hit_sl = ret_sl >= sl

    label = np.where(hit_tp, 1, np.where(hit_sl, -1, 0))

    out["label"] = label
    out["fwd_ret"] = fwd_ret
    out["sigma"] = sigma
    return out.dropna()
