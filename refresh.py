import sys
import pandas as pd
import yfinance as yf
from labeling import add_labels
from features import make_features
from backtest import walk_forward

ticker = sys.argv[1] if len(sys.argv) > 1 else "SPY"

# 1) Download
df = yf.download(ticker, period="2y", interval="1d", auto_adjust=False, progress=False)
if df.empty:
    raise SystemExit(f"No data for {ticker}")

# 2) If MultiIndex (some yfinance versions), collapse to single-level
if isinstance(df.columns, pd.MultiIndex):
    # If one symbol level is present, drop it
    for lvl in range(df.columns.nlevels - 1, -1, -1):
        if len(df.columns.get_level_values(lvl).unique()) == 1:
            df = df.droplevel(lvl, axis=1)
            break
    # If still MultiIndex, flatten
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ["_".join([str(x) for x in tup if x is not None]).strip() for tup in df.columns]

# 3) Normalize names to lowercase-with-underscores
df = df.rename(columns=lambda c: str(c).strip().lower().replace(" ", "_"))

# 4) Robustly pick required columns (handles weird names)
def pick_column(candidates, exclude_substr=None):
    cols = list(df.columns)
    # prefer exact match
    for cand in candidates:
        if cand in cols:
            return cand
    # fallback: substring match
    for cand in candidates:
        for col in cols:
            name = str(col)
            if cand in name and not (exclude_substr and exclude_substr in name):
                return col
    return None

open_col  = pick_column(["open"])
high_col  = pick_column(["high"])
low_col   = pick_column(["low"])
# prefer 'close' over 'adj_close'
close_col = pick_column(["close"], exclude_substr="adj")
if not close_col:
    close_col = pick_column(["close"])  # accept adj_close if needed
vol_col   = pick_column(["volume","vol"])

missing = [x for x in [open_col, high_col, low_col, close_col, vol_col] if x is None]
if missing:
    raise SystemExit(f"Could not identify columns. Got: {df.columns.tolist()}")

# 5) Build our schema
out = (
    df[[open_col, high_col, low_col, close_col, vol_col]]
    .copy()
    .rename(columns={
        open_col: "open",
        high_col: "high",
        low_col: "low",
        close_col: "close",
        vol_col: "volume",
    })
    .reset_index()
)

# Normalize datetime column
if "date" in out.columns:
    out = out.rename(columns={"date": "datetime"})
elif "index" in out.columns:
    out = out.rename(columns={"index": "datetime"})
elif "datetime" not in out.columns:
    out.rename(columns={out.columns[0]: "datetime"}, inplace=True)

# 6) Force numeric and clean
for c in ["open","high","low","close","volume"]:
    out[c] = pd.to_numeric(out[c], errors="coerce")

out = out.dropna(subset=["open","high","low","close","volume"]).set_index("datetime").sort_index()

# 7) Labels → Features → Backtest
df_l = add_labels(out, horizon=3, tp_sigma=0.8, sl_sigma=0.6, vol_lookback=5)
df_f, X, y = make_features(df_l)
bt = walk_forward(df_f, X, y, quantiles=(0.15, 0.5, 0.85), cost_bps=1.5, train_frac=0.7)

# 8) Save artifacts for app
out.reset_index().to_csv("data/prices.csv", index=False)
bt.to_csv("backtest_results.csv")
print(f"Refreshed {ticker}: {len(bt)} test rows, final_equity={bt.equity.iloc[-1]:.3f}, trades={(bt.signal!=0).sum()}")
