def suggest_option(spot: float, q_lo: float, q_md: float, q_hi: float, sigma: float, bars_to_horizon: int = 20):
    """
    Turn price quantiles into TP/SL and a simple option pick.
    spot: current price
    q_lo/q_md/q_hi: forecast return quantiles (e.g., -0.01, 0.00, 0.01)
    sigma: recent realized vol (daily)
    bars_to_horizon: your forecast horizon in bars (assume ~1 bar = 1 day if daily data)
    """
    tp_price = spot * (1 + q_hi)
    sl_price = spot * (1 + q_lo)
    # simple rules of thumb
    target_days = max(14, int(bars_to_horizon * 2.5))
    call_delta = 0.30 if q_md > 0 else None
    put_delta  = 0.30 if q_md < 0 else None

    return {
        "entry_bias": "LONG" if q_md > 0 else ("SHORT" if q_md < 0 else "FLAT"),
        "entry_spot": round(float(spot), 2),
        "tp_spot": round(float(tp_price), 2),
        "sl_spot": round(float(sl_price), 2),
        "horizon_days_min": int(target_days),
        "call_delta_if_long": call_delta,
        "put_delta_if_short": put_delta
    }
