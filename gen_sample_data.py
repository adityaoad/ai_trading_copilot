import pandas as pd
import numpy as np

np.random.seed(42)
n = 300  # ~300 days
dates = pd.date_range("2024-01-01", periods=n, freq="B")  # business days

# random walk for close
ret = np.random.normal(loc=0.0005, scale=0.01, size=n)
close = 100 * (1 + pd.Series(ret)).cumprod().values

# build OHLCV around close
open_ = close * (1 + np.random.normal(0, 0.002, n))
high  = np.maximum(open_, close) * (1 + np.abs(np.random.normal(0, 0.004, n)))
low   = np.minimum(open_, close) * (1 - np.abs(np.random.normal(0, 0.004, n)))
vol   = np.random.randint(10000, 50000, size=n)

df = pd.DataFrame({
    "datetime": dates,
    "open": open_.round(2),
    "high": high.round(2),
    "low": low.round(2),
    "close": close.round(2),
    "volume": vol
})

df.to_csv("data/prices.csv", index=False)
print("Wrote data/prices.csv with", len(df), "rows")
