"""Explainable-AI evidence assembly: turns raw z-scores, model feature
importances, and anomaly flags into a human-readable evidence list."""

READABLE = {
    "temperature": "Temperature", "vibration": "Vibration", "pressure": "Pressure",
    "current": "Motor Current", "rpm": "RPM",
}

UNITS = {"temperature": "°C", "vibration": "mm/s", "pressure": "kPa", "current": "A", "rpm": "RPM"}


def build_evidence(latest_row, baseline: dict, z: dict, anomaly_score: float,
                    recent_anomaly_count: int, window_size: int) -> list:
    evidence = []
    for s, label in READABLE.items():
        b = baseline[s]
        val = latest_row[s]
        dev_pct = ((val - b["mean"]) / b["mean"] * 100) if b["mean"] else 0
        evidence.append({
            "metric": label,
            "current_value": round(float(val), 2),
            "unit": UNITS[s],
            "normal_range": [round(b["mean"] - 2 * b["std"], 2), round(b["mean"] + 2 * b["std"], 2)],
            "deviation_std": round(float(z[s]), 2),
            "deviation_pct": round(float(dev_pct), 1),
            "flag": "elevated" if z[s] > 1.5 else ("suppressed" if z[s] < -1.5 else "normal"),
        })
    evidence.sort(key=lambda e: -abs(e["deviation_std"]))

    summary = {
        "anomaly_score": round(float(anomaly_score), 1),
        "recent_anomalous_readings": int(recent_anomaly_count),
        "recent_window_size": int(window_size),
        "narrative": _narrative(recent_anomaly_count, window_size, anomaly_score),
    }
    return evidence, summary


def _narrative(count, window, anomaly_score):
    if anomaly_score < 20:
        return f"Telemetry is stable: {count} of the last {window} readings flagged as unusual."
    if anomaly_score < 50:
        return f"Early warning signals detected: {count} of the last {window} readings deviate from the equipment's healthy baseline."
    if anomaly_score < 80:
        return f"A clear abnormal pattern is emerging: {count} of the last {window} readings are anomalous, forming a consistent deviation trend."
    return f"Strong, sustained anomaly pattern: {count} of the last {window} readings are anomalous -- consistent with an active developing fault."


def top_model_drivers(importance_list: list, top_n: int = 4) -> list:
    out = []
    for item in importance_list[:top_n]:
        feat = item["feature"]
        sensor = feat.split("_")[0]
        kind = "trend" if feat.endswith("_slope") else ("variability" if feat.endswith("_std") or "roll_std" in feat else "level")
        if feat == "anomaly_score":
            readable = "Overall anomaly score"
        else:
            readable = f"{READABLE.get(sensor, sensor)} {kind}"
        out.append({"feature": readable, "contribution_pct": round(item["importance"] * 100, 1)})
    return out
