import math

def size_equity_trade(spot: float,
                      tp_spot: float,
                      sl_spot: float,
                      account_equity: float,
                      risk_per_trade_pct: float = 0.01,
                      max_leverage: float = 1.0):
    """
    Vol and price aware position sizing for stock or ETF.
    Uses dollar risk between entry and stop.
    """
    if spot <= 0 or sl_spot <= 0:
        return {"shares": 0, "dollar_risk": 0.0, "max_loss": 0.0}

    dollar_risk_per_share = abs(spot - sl_spot)
    if dollar_risk_per_share == 0:
        return {"shares": 0, "dollar_risk": 0.0, "max_loss": 0.0}

    risk_budget = account_equity * risk_per_trade_pct
    raw_shares = risk_budget / dollar_risk_per_share

    # capital constraint
    max_shares_by_capital = (account_equity * max_leverage) / spot
    shares = int(max(0, min(raw_shares, max_shares_by_capital)))

    max_loss = shares * dollar_risk_per_share
    rr = (abs(tp_spot - spot) / dollar_risk_per_share) if dollar_risk_per_share > 0 else float("nan")

    return {
        "shares": shares,
        "risk_per_share": float(dollar_risk_per_share),
        "max_loss": float(max_loss),
        "risk_budget": float(risk_budget),
        "rr_ratio": float(rr)
    }

def size_option_trade(account_equity: float,
                      max_premium_pct: float = 0.01,
                      option_premium: float = None,
                      contract_multiplier: int = 100):
    """
    Simple option sizing by premium budget.
    You pass the expected premium per contract.
    """
    if option_premium is None or option_premium <= 0:
        return {"contracts": 0, "premium_budget": 0.0, "max_spend": 0.0}

    premium_budget = account_equity * max_premium_pct
    raw_contracts = premium_budget / (option_premium * contract_multiplier)
    contracts = int(max(0, math.floor(raw_contracts)))
    max_spend = contracts * option_premium * contract_multiplier

    return {
        "contracts": contracts,
        "premium_budget": float(premium_budget),
        "max_spend": float(max_spend)
    }
