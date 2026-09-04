"""Historical failure similarity search.

Every past incident has a "signature" (mean/std of each sensor over its final
cycles, i.e. the fingerprint of the failure). Each current equipment unit's
latest window is reduced to the same kind of signature, then matched against
the incident library with a cosine-similarity nearest-neighbor search. This
grounds the root-cause hypothesis in "this looks like what happened before",
not just an abstract rule.
"""
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from .preprocessing import SENSORS

SIG_COLS = [f"{s}_mean" for s in SENSORS] + [f"{s}_std" for s in SENSORS]


def fit_similarity_index(incidents: pd.DataFrame):
    X = incidents[SIG_COLS].values
    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)
    nn = NearestNeighbors(n_neighbors=min(3, len(incidents)), metric="cosine").fit(Xs)
    return scaler, nn


def current_signature(current_df: pd.DataFrame, equipment_id: str, tail_frac: float = 0.1) -> dict:
    g = current_df[current_df.equipment_id == equipment_id].sort_values("cycle")
    tail = max(5, int(len(g) * tail_frac))
    g = g.tail(tail)
    sig = {}
    for s in SENSORS:
        sig[f"{s}_mean"] = float(g[s].mean())
        sig[f"{s}_std"] = float(g[s].std() or 0.0)
    return sig


def find_similar_incidents(scaler, nn, incidents: pd.DataFrame, sig: dict, top_k: int = 2) -> list:
    x = np.array([[sig[c] for c in SIG_COLS]])
    xs = scaler.transform(x)
    dist, idx = nn.kneighbors(xs, n_neighbors=min(top_k, len(incidents)))
    results = []
    for d, i in zip(dist[0], idx[0]):
        row = incidents.iloc[i]
        similarity_pct = round(max(0.0, 1 - d) * 100, 1)
        results.append({
            "incident_id": row["incident_id"],
            "equipment_type": row["equipment_type"],
            "root_cause": row["root_cause"],
            "similarity_pct": similarity_pct,
            "action_taken": row["action_taken"],
            "failure_date": row["failure_date"],
        })
    return results
