import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge

def _q_model(alpha: float):
    return GradientBoostingRegressor(
        loss="quantile",
        alpha=alpha,
        n_estimators=400,
        max_depth=3,
        subsample=0.8,
        random_state=42,
    )

def _mu_model():
    return Ridge(alpha=1.0)

def fit_models(X_train, y_train, quantiles=(0.15, 0.5, 0.85)):
    q_models = {q: _q_model(q).fit(X_train, y_train) for q in quantiles}
    mu = _mu_model().fit(X_train, y_train)
    return q_models, mu

def predict_dist(q_models, mu, X):
    preds = {q: m.predict(X) for q, m in q_models.items()}
    preds["mu"] = mu.predict(X)
    return preds
