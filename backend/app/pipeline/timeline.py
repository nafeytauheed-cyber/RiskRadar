"""Builds a chronological failure/event timeline per equipment: clusters of
anomalous readings (as discrete "events") interleaved with maintenance log
entries."""
import pandas as pd

from .preprocessing import SENSORS


def _cluster_anomalies(g: pd.DataFrame, baseline: dict) -> list:
    events = []
    in_cluster = False
    cluster_rows = []

    def flush():
        if not cluster_rows:
            return
        sub = pd.DataFrame(cluster_rows)
        # dominant sensor = greatest average absolute z-score in this cluster
        z_avgs = {}
        for s in SENSORS:
            b = baseline[s]
            z_avgs[s] = ((sub[s] - b["mean"]) / (b["std"] or 1.0)).abs().mean()
        dominant = max(z_avgs, key=z_avgs.get)
        events.append({
            "type": "anomaly_cluster",
            "date": str(sub["timestamp"].iloc[0].date()),
            "end_date": str(sub["timestamp"].iloc[-1].date()),
            "dominant_signal": dominant,
            "avg_anomaly_score": round(float(sub["anomaly_score"].mean()), 1),
            "reading_count": len(sub),
            "label": f"Anomalous {dominant} pattern detected ({len(sub)} readings)",
        })

    for _, row in g.iterrows():
        if row["is_anomaly"]:
            cluster_rows.append(row)
            in_cluster = True
        else:
            if in_cluster:
                flush()
                cluster_rows = []
            in_cluster = False
    flush()
    return events


def build_timeline(features_g: pd.DataFrame, maint_g: pd.DataFrame, baseline: dict) -> list:
    g = features_g.sort_values("cycle")
    events = _cluster_anomalies(g, baseline)

    for _, row in maint_g.sort_values("date").iterrows():
        events.append({
            "type": "maintenance",
            "date": str(row["date"].date()),
            "end_date": str(row["date"].date()),
            "label": f"{row['type']}: {row['notes']}",
        })

    events.sort(key=lambda e: e["date"])
    return events
