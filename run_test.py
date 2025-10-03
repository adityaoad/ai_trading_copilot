import pandas as pd
from labeling import add_labels
from features import make_features
from backtest import walk_forward

# 1) LOAD DATA (force numeric to avoid the string/NoneType error you saw)
df = (
    pd.read_csv("data/prices.csv", parse_dates=["datetime"])
      .set_index("datetime")
      .sort_index()
)
for c in ["open","high","low","close","volume"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
df = df.dropna(subset=["open","high","low","close","volume"])

# 2) LABELS (short windows so we keep enough rows)
df_l = add_labels(df, horizon=3, tp_sigma=0.8, sl_sigma=0.6, vol_lookback=5)

# 3) FEATURES
df_f, X, y = make_features(df_l)

# 4) BACKTEST
bt = walk_forward(df_f, X, y, quantiles=(0.15, 0.5, 0.85), cost_bps=1.5, train_frac=0.7)

# 5) RESULTS
print("Tail:")
print(bt.tail(10))
print("\nSummary:")
print(
    pd.DataFrame({
        "trades": [(bt.signal != 0).sum()],
        "avg_pnl": [bt.pnl.mean()],
        "sharpe_like": [(bt.pnl.mean() / (bt.pnl.std() + 1e-9)) * (252**0.5)],
        "final_equity": [bt.equity.iloc[-1]]
    })
)

bt.to_csv("backtest_results.csv")
print("\nSaved: backtest_results.csv")
