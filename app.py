import streamlit as st
import pandas as pd

from trade_closer import auto_close_trades
from logger import now_ts as pt_now
from paper_trader import open_trade
from options import suggest_option
from sizing import size_equity_trade, size_option_trade


# --- config ---
account_equity = 10000
risk_per_trade_pct = 0.01
max_leverage = 2.0
option_premium = 2.5

st.set_page_config("AI Trading Copilot", layout="wide")
st.title("AI Trading Copilot — Latest Signal")

# ------------------------------------------------
# Ticker selection
# ------------------------------------------------
tickers = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "TSLA"]
ticker = st.selectbox("Choose ticker", tickers)
custom = st.text_input("Custom symbol")
if custom.strip():
    ticker = custom.strip().upper()

# ------------------------------------------------
# Try to load signal and show
# ------------------------------------------------
try:
    bt = pd.read_csv("backtest_results.csv", parse_dates=["datetime"]).set_index("datetime")
    px = pd.read_csv("data/prices.csv", parse_dates=["datetime"]).set_index("datetime").sort_index()

    last = bt.iloc[-1]
    spot = float(px["close"].iloc[-1])
    sigma = px["close"].pct_change().rolling(20).std().iloc[-1]
    sigma = float(sigma) if pd.notna(sigma) else 0.02

    rec = suggest_option(
        spot=spot,
        q_lo=last["q_lo"], q_md=last["q_md"], q_hi=last["q_hi"],
        sigma=sigma, bars_to_horizon=20
    )

    st.metric("Bias", rec["entry_bias"])
    c1, c2, c3 = st.columns(3)
    c1.metric("Spot", f"{rec['entry_spot']:.2f}")
    c2.metric("Take Profit (spot)", f"{rec['tp_spot']:.2f}")
    c3.metric("Stop (spot)", f"{rec['sl_spot']:.2f}")

    st.subheader("Option Hint")
    if rec["entry_bias"] == "LONG":
        st.write(f"Buy CALL ~Δ {rec['call_delta_if_long']}, min expiry ~{rec['horizon_days_min']} days")
    elif rec["entry_bias"] == "SHORT":
        st.write(f"Buy PUT ~Δ {rec['put_delta_if_short']}, min expiry ~{rec['horizon_days_min']} days")
    else:
        st.write("No trade (FLAT)")

    # Position sizing
    eq = size_equity_trade(
        spot=spot,
        tp_spot=rec["tp_spot"],
        sl_spot=rec["sl_spot"],
        account_equity=account_equity,
        risk_per_trade_pct=risk_per_trade_pct,
        max_leverage=max_leverage,
    )
    opt = size_option_trade(
        account_equity=account_equity,
        max_premium_pct=risk_per_trade_pct,
        option_premium=option_premium,
    )

    st.subheader("Position size")
    cA, cB, cC, cD = st.columns(4)
    cA.metric("Shares", f"{eq['shares']}")
    cB.metric("Risk/share", f"{eq['risk_per_share']:.2f}")
    cC.metric("Max loss", f"{eq['max_loss']:.2f}")
    cD.metric("R:R", f"{eq['rr_ratio']:.2f}")

    st.subheader("Option size")
    dA, dB = st.columns(2)
    dA.metric("Contracts", f"{opt['contracts']}")
    dB.metric("Max spend", f"{opt['max_spend']:.2f}")

    # Paper trade button
    if st.button("Open Paper Trade"):
        try:
            open_trade({
                "ts": pt_now(),
                "ticker": ticker,
                "side": "LONG" if rec["entry_bias"] == "LONG" else ("SHORT" if rec["entry_bias"] == "SHORT" else "FLAT"),
                "entry_spot": round(spot, 4),
                "tp_spot": round(rec["tp_spot"], 4),
                "sl_spot": round(rec["sl_spot"], 4),
                "shares": int(eq["shares"]),
                "contracts": int(opt["contracts"]),
                "risk_per_share": round(eq["risk_per_share"], 4),
                "max_loss": round(eq["max_loss"], 2),
                "status": "OPEN"
            })
            st.success("Paper trade opened → trades_log.csv")
        except Exception as e:
            st.error(str(e))

except Exception:
    st.info("Pick a ticker and click 'Fetch & Rebuild'.")

# ------------------------------------------------
# Logs section
# ------------------------------------------------
st.divider()
st.subheader("Signals Log")
try:
    logdf = pd.read_csv("signals_log.csv", engine="python", on_bad_lines="skip")
    st.dataframe(logdf.tail(50), use_container_width=True)
except Exception as e:
    st.caption(f"No signals logged yet. ({e})")

st.subheader("Paper Trades")
try:
    tdf = pd.read_csv("trades_log.csv", engine="python", on_bad_lines="skip")
    st.dataframe(tdf.tail(50), use_container_width=True)
except Exception as e:
    st.caption(f"No paper trades yet. ({e})")


# ------------------------------------------------
# Auto-close section
# ------------------------------------------------
st.divider()
if st.button("Auto-Close OPEN Trades"):
    try:
        res = auto_close_trades(
            prices_path="data/prices.csv",
            trades_path="trades_log.csv",
            max_hold_days=20
        )
        st.success(f"Closed {res['closed']} trade(s). OPEN remaining: {res['open_remaining']}")
    except Exception as e:
        st.error(str(e))

# Refresh and show updated trades + summary
try:
    tdf = pd.read_csv("trades_log.csv", engine="python", on_bad_lines="skip")
    st.subheader("Paper Trades (updated)")
    st.dataframe(tdf.tail(50), use_container_width=True)

    if "realized_pnl" in tdf.columns:
        realized = tdf.dropna(subset=["realized_pnl"])
        total_pnl = realized["realized_pnl"].sum() if not realized.empty else 0.0
        wins = (realized["realized_pnl"] > 0).sum() if not realized.empty else 0
        losses = (realized["realized_pnl"] <= 0).sum() if not realized.empty else 0
        st.caption(f"Realized PnL: {total_pnl:.2f} • Wins: {wins} • Losses: {losses}")
except Exception:
    pass

