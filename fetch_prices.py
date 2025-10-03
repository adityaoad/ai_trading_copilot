import sys
import pandas as pd
import yfinance as yf
from datetime import datetime

# Usage: python fetch_prices.py TICKER   (example: python fetch_prices.py SPY)
ticker = sys.argv[1] if len(sys.argv) > 1 else "SPY"

df = yf.download(ticker, period="2y", interval="1d", auto_adjust=False, progress=False)
if df.empty:
    raise SystemExit(f"No data returned for {ticker}. Check the symbol or network.")

df = df.rename(columns={
    "Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"
}).reset_index().rename(columns={"Date":"datetime"})

df = df[["datetime","open","high","low","close","volume"]]
df.to_csv("data/prices.csv", index=False)

print(f"Wrote data/prices.csv for {ticker} with {len(df)} rows (through {df['datetime'].iloc[-1].date()}).")
