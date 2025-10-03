import numpy as np
import pandas as pd
from models import fit_models, predict_dist

def walk_forward(df_feat: pd.DataFrame, X: pd.DataFrame, y: pd.Series,
                 quantiles=(0.15, 0.5, 0.85), cost_bps=1.5, train_frac=0.7):
    """
    Simple one-cut walk-forward:
    - Train on first train_frac of data, test on the rest
    - Long if median forecast > costs; short if < -costs
    - PnL uses forward return y (already aligned to features)
    """
    n = len(df_feat)
    cut = max(int(n * train_frac), 50)
    X_tr, X_te = X.iloc[:cut], X.iloc[cut:]
    y_tr, y_te = y.iloc[:cut], y.iloc[cut:]

    q_models, mu = fit_models(X_tr, y_tr, quantiles)
    pred = predict_dist(q_models, mu, X_te)

    te = df_feat.iloc[cut:].copy()
    te["q_lo"] = pred[quantiles[0]]
    te["q_md"] = pred[quantiles[1]]
    te["q_hi"] = pred[quantiles[2]]

    cost = cost_bps * 1e-4
    long_sig = te["q_md"] > cost
    short_sig = te["q_md"] < -cost

    ret = te["fwd_ret"].astype(float)
    pnl = np.where(long_sig, ret, np.where(short_sig, -ret, 0.0))
    trade_flag = (long_sig | short_sig).astype(float)
    pnl_after_cost = pnl - cost * trade_flag

    te["signal"] = np.where(long_sig, 1, np.where(short_sig, -1, 0))
    te["pnl"] = pnl_after_cost
    te["equity"] = (1 + te["pnl"]).cumprod()

    cols = ["q_lo", "q_md", "q_hi", "signal", "fwd_ret", "pnl", "equity"]
    return te[cols]
