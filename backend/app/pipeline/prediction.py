"""Supervised failure-risk prediction.

Trained on the historical run-to-failure fleet, where the true outcome
(remaining useful life at every cycle) is known. Label = 1 if the unit is
within FAILURE_HORIZON cycles of its recorded failure, else 0. The model then
scores the CURRENT fleet's latest telemetry window for probability of
failure-soon, using the exact same engineered features (no ground truth
leaks into the current fleet -- it never had a labeled failure cycle).
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier

from .preprocessing import feature_columns

FAILURE_HORIZON = 30  # cycles


def build_training_set(hist_features: pd.DataFrame, incidents: pd.DataFrame) -> pd.DataFrame:
    fail_cycle = incidents.set_index("equipment_id")["failure_cycle"].to_dict()
    df = hist_features.copy()
    df["failure_cycle"] = df["equipment_id"].map(fail_cycle)
    df["rul"] = df["failure_cycle"] - df["cycle"]
    df["label"] = (df["rul"] <= FAILURE_HORIZON).astype(int)
    return df


MODEL_FEATURES = None  # set at fit time to include anomaly_score


def fit_model(train_df: pd.DataFrame):
    global MODEL_FEATURES
    MODEL_FEATURES = feature_columns() + ["anomaly_score"]
    X = train_df[MODEL_FEATURES].values
    y = train_df["label"].values
    model = GradientBoostingClassifier(n_estimators=150, max_depth=3, learning_rate=0.08, random_state=42)
    model.fit(X, y)
    return model


def predict_risk(model, features_row: pd.Series) -> float:
    X = features_row[MODEL_FEATURES].values.reshape(1, -1)
    return float(model.predict_proba(X)[0, 1])


def feature_importance(model) -> list:
    importances = model.feature_importances_
    pairs = sorted(zip(MODEL_FEATURES, importances), key=lambda p: -p[1])
    return [{"feature": f, "importance": float(i)} for f, i in pairs]
