"""Orchestrates the full RiskRadar pipeline:

    Data -> Clean/Preprocess -> Anomaly Detection -> Failure Prediction
         -> Historical Similarity -> Root Cause -> Risk Score -> Explanation
         -> Recommended Action -> Timeline -> Report

Runs once at API startup (dataset is small, trains in well under a second)
and caches results in memory for the API layer to serve.
"""
import numpy as np
import pandas as pd

from . import preprocessing as prep
from . import anomaly as anom
from . import prediction as pred
from . import similarity as sim
from . import root_cause as rca
from . import risk_score as risk
from . import explain as expl
from . import recommend as rec
from . import timeline as tl

RECENT_WINDOW = 15


class RiskRadarPipeline:
    def __init__(self):
        self.equipment_results = {}
        self.overview = {}
        self.master = None
        self.generated_at = None

    def run(self):
        hist, incidents, current, master, maint = prep.load_raw()
        hist = prep.clean(hist)
        current = prep.clean(current)
        self.master = master

        hist_features = prep.engineer_features(hist)
        current_features = prep.engineer_features(current)

        baseline = prep.baseline_stats(current)
        vib_std_baseline = float(current_features["vibration_roll_std"].quantile(0.3))
        rpm_std_baseline = float(current_features["rpm_roll_std"].quantile(0.3))
        rca.set_baseline_std(vib_std_baseline, rpm_std_baseline)

        iso_model = anom.fit_isolation_forest(hist_features)
        hist_features = anom.score_anomalies(iso_model, hist_features)
        current_features = anom.score_anomalies(iso_model, current_features)

        train_df = pred.build_training_set(hist_features, incidents)
        risk_model = pred.fit_model(train_df)
        importances = pred.feature_importance(risk_model)

        scaler, nn_index = sim.fit_similarity_index(incidents)

        results = []
        for eq_id, g in current_features.groupby("equipment_id"):
            g = g.sort_values("cycle").reset_index(drop=True)
            latest = g.iloc[-1]
            meta = master[master.equipment_id == eq_id].iloc[0]

            failure_prob = pred.predict_risk(risk_model, latest)

            z = anom.zscores(latest, baseline)

            recent = g.tail(RECENT_WINDOW)
            recent_anomaly_count = int(recent["is_anomaly"].sum())

            sig = sim.current_signature(current, eq_id)
            similar = sim.find_similar_incidents(scaler, nn_index, incidents, sig, top_k=2)

            rc = rca.build_root_cause_report(latest, z, similar)

            score = risk.compute_risk_score(
                failure_probability=failure_prob,
                anomaly_score=float(latest["anomaly_score"]),
                root_cause_confidence=rc["confidence"],
                criticality=meta["criticality"],
            )

            evidence, evidence_summary = expl.build_evidence(
                latest, baseline, z, latest["anomaly_score"], recent_anomaly_count, len(recent)
            )
            model_drivers = expl.top_model_drivers(importances)

            actions = rec.recommend_actions(rc["top_cause"], score["severity"]) if rc["top_cause"] else \
                rec.recommend_actions(None, score["severity"])

            maint_g = maint[maint.equipment_id == eq_id]
            events = tl.build_timeline(g, maint_g, baseline)

            failure_chain = _build_failure_chain(rc, score, actions)

            result = {
                "equipment_id": eq_id,
                "name": meta["name"],
                "type": meta["type"],
                "location": meta["location"],
                "criticality": meta["criticality"],
                "install_date": str(meta["install_date"].date()),
                "last_updated": str(latest["timestamp"]),
                "cycle": int(latest["cycle"]),
                "failure_probability": round(failure_prob, 3),
                "risk_score": score["risk_score"],
                "severity": score["severity"],
                "risk_components": score["components"],
                "root_cause": rc,
                "similar_incidents": similar,
                "evidence": evidence,
                "evidence_summary": evidence_summary,
                "model_drivers": model_drivers,
                "recommended_actions": actions,
                "timeline": events,
                "failure_chain": failure_chain,
                "sensor_trend": g[["cycle", "timestamp"] + prep.SENSORS + ["anomaly_score"]].tail(60).assign(
                    timestamp=lambda d: d["timestamp"].astype(str)
                ).to_dict(orient="records"),
            }
            results.append(result)
            self.equipment_results[eq_id] = result

        self.overview = _build_overview(results)
        self.generated_at = pd.Timestamp.utcnow().isoformat()
        return self


def _build_failure_chain(rc, score, actions):
    steps = []
    if rc["top_cause"]:
        signal_labels = ", ".join(s["signal"] for s in rc.get("signals", []))
        steps.append({"stage": "Weak Signals", "detail": signal_labels or "Multiple minor sensor deviations"})
        steps.append({"stage": "Emerging Pattern", "detail": f"Deviation pattern matches '{rc['top_cause_label']}' signature"})
        steps.append({"stage": "Likely Root Cause", "detail": rc["top_cause_label"]})
    else:
        steps.append({"stage": "Weak Signals", "detail": "No significant deviations detected"})
        steps.append({"stage": "Emerging Pattern", "detail": "Telemetry within healthy envelope"})
        steps.append({"stage": "Likely Root Cause", "detail": "None identified"})
    steps.append({"stage": "Predicted Failure Risk", "detail": f"{score['components']['failure_probability_pct']}% probability of failure within 30 operating cycles"})
    steps.append({"stage": "Safety Risk", "detail": f"{score['severity']} ({score['risk_score']}/100)"})
    steps.append({"stage": "Recommended Intervention", "detail": actions["urgency"]})
    return steps


def _build_overview(results):
    if not results:
        return {}
    scores = [r["risk_score"] for r in results]
    severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for r in results:
        severity_counts[r["severity"]] += 1

    equipment_list = sorted(
        [{
            "equipment_id": r["equipment_id"], "name": r["name"], "type": r["type"],
            "location": r["location"], "criticality": r["criticality"],
            "risk_score": r["risk_score"], "severity": r["severity"],
            "top_root_cause": r["root_cause"]["top_cause_label"],
            "failure_probability": r["failure_probability"],
        } for r in results],
        key=lambda e: -e["risk_score"]
    )

    return {
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "total_equipment": len(results),
        "overall_risk_score": round(float(np.mean(scores)), 1),
        "overall_severity": risk.severity_band(float(np.mean(scores))),
        "severity_counts": severity_counts,
        "high_risk_count": severity_counts["Critical"] + severity_counts["High"],
        "equipment": equipment_list,
    }
