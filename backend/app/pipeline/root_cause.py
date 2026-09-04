"""Root-cause reasoning engine.

This is the core of RiskRadar's "failure-chain reasoning" USP: instead of a
single black-box score, it explicitly walks

    weak signals -> emerging pattern -> likely root cause

by combining (a) per-sensor deviation-from-baseline + trend direction with
(b) agreement from the historical-similarity search. Each rule below encodes
a known causal signature (see data_gen.py fault patterns); confidence blends
how strongly the live signals match the rule with how well the nearest
historical incidents agree.
"""

LABELS = {
    "bearing_wear": "Bearing Wear",
    "lubrication_breakdown": "Lubrication Breakdown",
    "seal_leak": "Seal Leak",
    "blockage": "Blockage / Clogging",
    "electrical_overload": "Electrical Overload",
    "misalignment": "Shaft Misalignment",
}

DESCRIPTIONS = {
    "bearing_wear": "Rising vibration coupled with rising temperature indicates increasing friction consistent with bearing surface degradation.",
    "lubrication_breakdown": "Steadily climbing temperature with only mild vibration increase suggests the lubricant film is breaking down, raising friction.",
    "seal_leak": "Falling pressure combined with rising vibration points to a loss of sealed fluid/gas integrity.",
    "blockage": "Rising pressure alongside rising current suggests the system is working harder against a growing obstruction.",
    "electrical_overload": "Rising current with unstable RPM points to an electrical supply or drive-load problem rather than a mechanical one.",
    "misalignment": "Increasingly spiky vibration with RPM jitter is characteristic of a rotating assembly going out of alignment.",
}


def _signal(name, zscore, slope, note):
    return {"signal": name, "zscore": round(float(zscore), 2), "slope": round(float(slope), 4), "note": note}


def evaluate_patterns(feat_row, z: dict) -> list:
    """feat_row: latest engineered-feature row (has *_slope, *_roll_std columns).
    z: dict of per-sensor current z-scores vs healthy baseline.
    Returns a list of {root_cause, confidence, signals} candidate hypotheses."""
    candidates = []

    def slope(s):
        # long-window (noise-resistant) trend, used for gating/confidence -- NOT
        # the short 10-point ML feature slope, which is too noisy for this.
        return feat_row.get(f"{s}_trend_slope", 0.0)

    def rstd(s):
        return feat_row.get(f"{s}_roll_std", 0.0)

    def trend_mult(s, expect_positive: bool):
        """Soft confidence modifier: confirms if the long-window trend agrees
        with the expected direction, mild penalty (not elimination) if not --
        the z-score deviation is the primary evidence, trend is corroboration."""
        sl = slope(s)
        agrees = (sl > 0) if expect_positive else (sl < 0)
        return 1.15 if agrees else 0.85

    # bearing_wear: rising vibration + rising temperature together
    vib_z, temp_z = z["vibration"], z["temperature"]
    if vib_z > 1.0 and temp_z > 0.5:
        conf = min(1.0, (0.35 + 0.15 * vib_z + 0.1 * temp_z) * trend_mult("vibration", True) * trend_mult("temperature", True))
        candidates.append({
            "root_cause": "bearing_wear", "confidence": conf,
            "signals": [
                _signal("vibration", vib_z, slope("vibration"), "rising above healthy baseline"),
                _signal("temperature", temp_z, slope("temperature"), "rising alongside vibration"),
            ],
        })

    # lubrication_breakdown: temperature climbing, vibration only mildly elevated
    if temp_z > 1.2 and 0 <= vib_z < 2.0:
        conf = min(1.0, (0.3 + 0.18 * temp_z) * trend_mult("temperature", True))
        candidates.append({
            "root_cause": "lubrication_breakdown", "confidence": conf,
            "signals": [
                _signal("temperature", temp_z, slope("temperature"), "steadily climbing"),
                _signal("vibration", vib_z, slope("vibration"), "only mildly elevated"),
            ],
        })

    # seal_leak: falling pressure + rising vibration
    pres_z = z["pressure"]
    if pres_z < -1.0 and vib_z > 0.5:
        conf = min(1.0, (0.35 + 0.15 * abs(pres_z) + 0.1 * vib_z) * trend_mult("pressure", False) * trend_mult("vibration", True))
        candidates.append({
            "root_cause": "seal_leak", "confidence": conf,
            "signals": [
                _signal("pressure", pres_z, slope("pressure"), "falling below healthy baseline"),
                _signal("vibration", vib_z, slope("vibration"), "rising as seal integrity degrades"),
            ],
        })

    # blockage: rising pressure + rising current
    if pres_z > 1.0 and z["current"] > 0.8:
        conf = min(1.0, (0.35 + 0.15 * pres_z + 0.12 * z["current"]) * trend_mult("pressure", True) * trend_mult("current", True))
        candidates.append({
            "root_cause": "blockage", "confidence": conf,
            "signals": [
                _signal("pressure", pres_z, slope("pressure"), "rising, system working against resistance"),
                _signal("current", z["current"], slope("current"), "rising to compensate"),
            ],
        })

    # electrical_overload: rising current + unstable rpm
    cur_z = z["current"]
    if cur_z > 1.2 and rstd("rpm") > BASELINE_RPM_STD * 1.8:
        conf = min(1.0, (0.35 + 0.18 * cur_z) * trend_mult("current", True))
        candidates.append({
            "root_cause": "electrical_overload", "confidence": conf,
            "signals": [
                _signal("current", cur_z, slope("current"), "rising sharply"),
                _signal("rpm", z["rpm"], slope("rpm"), "unstable / jittering"),
            ],
        })

    # misalignment: erratic vibration + jittery rpm, without a clear directional pressure/current cause
    if rstd("vibration") > BASELINE_VIB_STD * 1.8 and rstd("rpm") > BASELINE_RPM_STD * 1.5:
        conf = min(1.0, 0.3 + 0.1 * (rstd("vibration") / max(BASELINE_VIB_STD, 1e-6)))
        candidates.append({
            "root_cause": "misalignment", "confidence": conf,
            "signals": [
                _signal("vibration", vib_z, slope("vibration"), "increasingly spiky/erratic"),
                _signal("rpm", z["rpm"], slope("rpm"), "jittering"),
            ],
        })

    return sorted(candidates, key=lambda c: -c["confidence"])


# Populated by pipeline_runner at startup from baseline stats (rolling-std of a healthy unit)
BASELINE_VIB_STD = 0.3
BASELINE_RPM_STD = 15.0


def set_baseline_std(vib_std: float, rpm_std: float):
    global BASELINE_VIB_STD, BASELINE_RPM_STD
    BASELINE_VIB_STD = max(vib_std, 1e-6)
    BASELINE_RPM_STD = max(rpm_std, 1e-6)


def build_root_cause_report(feat_row, z: dict, similar_incidents: list) -> dict:
    candidates = evaluate_patterns(feat_row, z)

    # Boost confidence where the similarity search independently agrees.
    sim_causes = {s["root_cause"] for s in similar_incidents}
    for c in candidates:
        if c["root_cause"] in sim_causes:
            c["confidence"] = min(1.0, c["confidence"] + 0.2)
            c["corroborated_by_history"] = True
        else:
            c["corroborated_by_history"] = False

    candidates = sorted(candidates, key=lambda c: -c["confidence"])

    if not candidates:
        # No live rule fired -- fall back to the historical-similarity search as a
        # weaker, explicitly-flagged hypothesis rather than declaring "unknown"
        # outright. Mirrors how an investigator reasons from precedent when the
        # live signal pattern alone isn't yet a clean textbook signature.
        if similar_incidents and similar_incidents[0]["similarity_pct"] >= 60:
            top_sim = similar_incidents[0]
            cause = top_sim["root_cause"]
            confidence = round(min(0.65, top_sim["similarity_pct"] / 100 * 0.75), 2)
            return {
                "top_cause": cause,
                "top_cause_label": LABELS[cause],
                "confidence": confidence,
                "description": (
                    f"No live sensor pattern matched a known signature strongly enough on its own, but current "
                    f"telemetry is {top_sim['similarity_pct']}% similar to a past {cause.replace('_', ' ')} incident. "
                    + DESCRIPTIONS[cause]
                ),
                "signals": [_signal("similarity", top_sim["similarity_pct"] / 100, 0.0,
                                     f"matches historical incident {top_sim['incident_id']}")],
                "corroborated_by_history": True,
                "history_only": True,
                "candidates": [{"root_cause": cause, "label": LABELS[cause], "confidence": confidence}],
            }
        return {
            "top_cause": None,
            "top_cause_label": "No clear root cause identified",
            "confidence": 0.0,
            "description": "Telemetry is within or near normal healthy ranges; no dominant fault signature detected.",
            "candidates": [],
        }

    top = candidates[0]
    return {
        "top_cause": top["root_cause"],
        "top_cause_label": LABELS[top["root_cause"]],
        "confidence": round(top["confidence"], 2),
        "description": DESCRIPTIONS[top["root_cause"]],
        "signals": top["signals"],
        "corroborated_by_history": top["corroborated_by_history"],
        "history_only": False,
        "candidates": [
            {"root_cause": c["root_cause"], "label": LABELS[c["root_cause"]], "confidence": round(c["confidence"], 2)}
            for c in candidates
        ],
    }
