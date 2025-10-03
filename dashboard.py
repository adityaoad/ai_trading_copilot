# dashboard.py — add Accuracy tab (reads eval_log.csv)
import json
from pathlib import Path
import pandas as pd
import streamlit as st

PROJECT_DIR = Path.home() / "Documents" / "ai_trading_copilot"
WATCHLIST = PROJECT_DIR / "daily_watchlist.json"
TRADES = PROJECT_DIR / "trades_log.csv"
POSITIONS = PROJECT_DIR / "positions.json"
EVAL = PROJECT_DIR / "eval_log.csv"

st.set_page_config(page_title="AI Trading Copilot", layout="wide")

def load_json(path: Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}

def load_csv(path: Path):
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

st.title("AI Trading Copilot")

tab1, tab2, tab3, tab4 = st.tabs(["Watchlist", "Open Positions", "Trades", "Accuracy"])

with tab1:
    st.subheader("Today's Watchlist")
    wl = load_json(WATCHLIST)
    ideas = wl.get("ideas", [])
    if ideas:
        df = pd.DataFrame(ideas)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No watchlist loaded yet.")

with tab2:
    st.subheader("Open Positions")
    pos = load_json(POSITIONS)
    positions = pos.get("positions", [])
    if positions:
        dfp = pd.DataFrame(positions)
        st.dataframe(dfp, use_container_width=True)
    else:
        st.info("No open positions.")

with tab3:
    st.subheader("Recent Trades")
    dft = load_csv(TRADES)
    if not dft.empty:
        st.dataframe(dft.tail(200), use_container_width=True)
        # Simple P&L summary
        closed = dft[dft["event"].str.startswith("CLOSE")] if "event" in dft.columns else pd.DataFrame()
        if not closed.empty and "pnl_dollars" in closed.columns:
            pnl = closed["pnl_dollars"].sum()
            st.metric("Net Realized P&L ($)", f"{pnl:,.2f}")
    else:
        st.info("No trades logged yet.")

with tab4:
    st.subheader("Accuracy (Daily Evaluator)")
    dfe = load_csv(EVAL)
    if dfe.empty:
        st.info("No eval_log.csv yet. It will populate after the evaluator runs.")
    else:
        # Normalize expected columns
        # expecting: date, symbol, result, triggered, rr (+ optional OHLC columns)
        needed = {"date","symbol","result","triggered","rr"}
        missing = needed - set(dfe.columns)
        if missing:
            st.warning(f"eval_log.csv missing columns: {missing}")
        # show latest rows
        st.markdown("**Latest Evaluations**")
        st.dataframe(dfe.tail(200), use_container_width=True)

        # Daily summary: win/loss/no_trigger counts and win rate
        def win_flag(x): return 1 if x == "win" else 0
        def loss_flag(x): return 1 if x == "loss" else 0
        if "result" in dfe.columns and "date" in dfe.columns:
            dfe["wins"] = dfe["result"].apply(win_flag)
            dfe["losses"] = dfe["result"].apply(loss_flag)
            daily = dfe.groupby("date", as_index=False).agg(
                total=("result","count"),
                wins=("wins","sum"),
                losses=("losses","sum")
            )
            # avoid div by zero
            daily["win_rate_%"] = (daily["wins"] / daily[["wins","losses"]].sum(axis=1).clip(lower=1)) * 100.0
            daily = daily.sort_values("date")
            st.markdown("**Daily Summary**")
            st.dataframe(daily, use_container_width=True)
            # Chart: daily win rate
            st.markdown("**Daily Win Rate (%)**")
            chart_df = daily.set_index("date")[["win_rate_%"]]
            st.line_chart(chart_df)
        else:
            st.info("Evaluator results available, but missing 'date'/'result' columns to compute accuracy.")
