"""Composite risk scoring: blends the supervised failure probability, the
unsupervised anomaly severity, root-cause confidence, and equipment
criticality into a single 0-100 score with a safety severity band."""

CRITICALITY_WEIGHT = {"High": 1.15, "Medium": 1.0, "Low": 0.9}


def severity_band(score: float) -> str:
    if score >= 80:
        return "Critical"
    if score >= 55:
        return "High"
    if score >= 30:
        return "Medium"
    return "Low"


def compute_risk_score(failure_probability: float, anomaly_score: float,
                        root_cause_confidence: float, criticality: str) -> dict:
    base = (failure_probability * 100) * 0.55 + anomaly_score * 0.30 + (root_cause_confidence * 100) * 0.15
    weighted = base * CRITICALITY_WEIGHT.get(criticality, 1.0)
    score = round(min(100.0, max(0.0, weighted)), 1)
    return {
        "risk_score": score,
        "severity": severity_band(score),
        "components": {
            "failure_probability_pct": round(failure_probability * 100, 1),
            "anomaly_score": round(anomaly_score, 1),
            "root_cause_confidence_pct": round(root_cause_confidence * 100, 1),
            "criticality_multiplier": CRITICALITY_WEIGHT.get(criticality, 1.0),
        },
    }
