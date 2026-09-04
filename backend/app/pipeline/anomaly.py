"""Unsupervised anomaly detection.

Two complementary signals are produced:
  - IsolationForest multivariate anomaly score, trained on the healthy portion
    of the historical fleet -- catches combinations of sensors that look
    jointly unusual even if no single sensor is far out of range.
  - Per-sensor z-score against the healthy baseline -- used for
    human-readable evidence ("vibration is 3.1 std above normal").
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from .preprocessing import SENSORS, feature_columns


def fit_isolation_forest(hist_features: pd.DataFrame, healthy_frac_cutoff: float = 0.3) -> IsolationForest:
    rows = []
    for eq_id, g in hist_features.groupby("equipment_id"):
        g = g.sort_values("cycle")
        cutoff = max(5, int(len(g) * healthy_frac_cutoff))
        rows.append(g.iloc[:cutoff])
    healthy = pd.concat(rows, ignore_index=True)
    X = healthy[feature_columns()].values
    model = IsolationForest(n_estimators=200, contamination=0.05, random_state=42)
    model.fit(X)
    return model


def score_anomalies(model: IsolationForest, features: pd.DataFrame) -> pd.DataFrame:
    df = features.copy()
    X = df[feature_columns()].values
    # decision_function: higher = more normal. Flip & rescale to an intuitive 0-100 score.
    raw = model.decision_function(X)
    df["anomaly_raw"] = raw
    df["is_anomaly"] = model.predict(X) == -1
    lo, hi = np.percentile(raw, [1, 99])
    span = max(hi - lo, 1e-6)
    df["anomaly_score"] = np.clip((hi - raw) / span, 0, 1) * 100
    return df


def zscores(row: pd.Series, baseline: dict) -> dict:
    out = {}
    for s in SENSORS:
        b = baseline[s]
        out[s] = (row[s] - b["mean"]) / (b["std"] or 1.0)
    return out
