import pandas as pd
from options import suggest_option

# load backtest results and original prices
bt = pd.read_csv("backtest_results.csv", parse_dates=["datetime"]).set_index("datetime")
px = pd.read_csv("data/prices.csv", parse_dates=["datetime"]).set_index("datetime").sort_index()

last_bt = bt.iloc[-1]
spot = float(px["close"].iloc[-1])  # real latest close
# simple recent daily vol estimate (last 20 days)
sigma = px["close"].pct_change().rolling(20).std().iloc[-1]

result = suggest_option(
    spot=spot,
    q_lo=last_bt["q_lo"],
    q_md=last_bt["q_md"],
    q_hi=last_bt["q_hi"],
    sigma=float(sigma) if pd.notna(sigma) else 0.02,
    bars_to_horizon=20
)

print("Latest trading signal:")
print(result)
