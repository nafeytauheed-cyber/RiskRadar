"""
RiskRadar synthetic dataset generator.

Generates two populations:
  1. HISTORICAL fleet (completed run-to-failure lifecycles) -> used to train the
     anomaly + failure-risk models and to build the failure-similarity library.
  2. CURRENT fleet (ongoing, mid-lifecycle equipment being monitored today) ->
     what the dashboard actually investigates. Some are healthy, some are
     silently developing one of the fault patterns below, none have "failed" yet.

No ground-truth labels for the CURRENT fleet are exposed to the app at
inference time -- the pipeline has to (re)discover risk from raw telemetry,
exactly like it would with real data.

Fault patterns simulated (each is a distinct causal signature the root-cause
engine is built to recognize):
  - bearing_wear         : vibration + temperature rise together, accelerating
  - lubrication_breakdown: temperature rises steadily, vibration rises mildly
  - seal_leak            : pressure drops, vibration rises
  - blockage             : pressure rises, current rises
  - electrical_overload  : current spikes, rpm becomes unstable
  - misalignment         : vibration develops periodic spiking, rpm jitters
"""
import os
import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)

OUT_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(OUT_DIR, exist_ok=True)

EQUIPMENT_TYPES = ["Pump", "Compressor", "Motor", "Turbine", "Conveyor"]
LOCATIONS = ["Plant A - Line 1", "Plant A - Line 2", "Plant B - Line 1", "Plant B - Line 3", "Plant C - Utility"]

FAULT_PATTERNS = [
    "bearing_wear",
    "lubrication_breakdown",
    "seal_leak",
    "blockage",
    "electrical_overload",
    "misalignment",
]

BASELINE = {
    # sensor: (mean, std) for a healthy unit
    "temperature": (65.0, 2.0),   # deg C
    "vibration": (2.2, 0.3),      # mm/s
    "pressure": (100.0, 3.0),     # kPa
    "current": (40.0, 1.5),       # Amps
    "rpm": (1500.0, 15.0),        # RPM
}

SENSORS = list(BASELINE.keys())


def _healthy_series(n):
    return {s: RNG.normal(BASELINE[s][0], BASELINE[s][1], n) for s in SENSORS}


def _apply_fault_trajectory(series, fault, n, onset_frac, severity=1.0):
    """Overlay a degradation trend onto an otherwise-healthy series.

    onset_frac: fraction of the series (0-1) at which degradation begins.
    severity: 0-1, how far along the fault has progressed by the end of the
              series (1.0 = reaches failure-level by the last sample).
    """
    onset = int(n * onset_frac)
    ramp_len = n - onset
    if ramp_len <= 0:
        return series
    t = np.linspace(0, 1, ramp_len) ** 1.6  # accelerating (concave) ramp
    t = t * severity

    if fault == "bearing_wear":
        series["vibration"][onset:] += t * 4.5 + RNG.normal(0, 0.15, ramp_len)
        series["temperature"][onset:] += t * 22 + RNG.normal(0, 0.8, ramp_len)
    elif fault == "lubrication_breakdown":
        series["temperature"][onset:] += t * 28 + RNG.normal(0, 1.0, ramp_len)
        series["vibration"][onset:] += t * 1.8 + RNG.normal(0, 0.15, ramp_len)
    elif fault == "seal_leak":
        series["pressure"][onset:] -= t * 35 + RNG.normal(0, 1.2, ramp_len)
        series["vibration"][onset:] += t * 2.2 + RNG.normal(0, 0.15, ramp_len)
    elif fault == "blockage":
        series["pressure"][onset:] += t * 40 + RNG.normal(0, 1.2, ramp_len)
        series["current"][onset:] += t * 14 + RNG.normal(0, 0.6, ramp_len)
    elif fault == "electrical_overload":
        series["current"][onset:] += t * 22 + RNG.normal(0, 0.8, ramp_len)
        series["rpm"][onset:] += RNG.normal(0, 8 + t.max() * 60, ramp_len)
    elif fault == "misalignment":
        spikes = (RNG.random(ramp_len) < (0.05 + 0.25 * t)) * RNG.normal(6, 1.5, ramp_len) * t
        series["vibration"][onset:] += spikes
        series["rpm"][onset:] += RNG.normal(0, 5 + t.max() * 25, ramp_len)
    return series


def _make_lifecycle(n_cycles, fault, onset_frac, severity):
    series = _healthy_series(n_cycles)
    series = _apply_fault_trajectory(series, fault, n_cycles, onset_frac, severity)
    for s in SENSORS:
        series[s] = np.clip(series[s], 0, None)
    return series


def generate_historical_fleet(n_units=24, start_ts="2024-01-01"):
    """Completed run-to-failure lifecycles with known root cause -- training data
    and the failure-similarity library."""
    rows = []
    incidents = []
    for i in range(n_units):
        eq_id = f"HIST-{i+1:03d}"
        eq_type = EQUIPMENT_TYPES[i % len(EQUIPMENT_TYPES)]
        fault = FAULT_PATTERNS[i % len(FAULT_PATTERNS)]
        n_cycles = int(RNG.integers(180, 320))
        onset_frac = float(RNG.uniform(0.45, 0.7))
        series = _make_lifecycle(n_cycles, fault, onset_frac, severity=1.0)

        ts = pd.date_range(start_ts, periods=n_cycles, freq="6h")
        for c in range(n_cycles):
            row = {"equipment_id": eq_id, "equipment_type": eq_type, "cycle": c + 1,
                   "timestamp": ts[c]}
            for s in SENSORS:
                row[s] = round(float(series[s][c]), 3)
            rows.append(row)

        # signature = mean of last 10% of cycles (the failure fingerprint)
        tail = max(5, int(n_cycles * 0.1))
        signature = {f"{s}_mean": float(np.mean(series[s][-tail:])) for s in SENSORS}
        signature.update({f"{s}_std": float(np.std(series[s][-tail:])) for s in SENSORS})

        incidents.append({
            "incident_id": f"INC-{i+1:03d}",
            "equipment_id": eq_id,
            "equipment_type": eq_type,
            "root_cause": fault,
            "failure_cycle": n_cycles,
            "onset_cycle": int(n_cycles * onset_frac),
            "failure_date": str(ts[-1].date()),
            "action_taken": ACTION_LIBRARY[fault]["immediate"][0],
            **signature,
        })

    df = pd.DataFrame(rows)
    inc_df = pd.DataFrame(incidents)
    df.to_csv(os.path.join(OUT_DIR, "sensor_readings_history.csv"), index=False)
    inc_df.to_csv(os.path.join(OUT_DIR, "failure_history.csv"), index=False)
    return df, inc_df


def generate_current_fleet(n_units=14, start_ts="2025-05-01"):
    """Ongoing fleet -- what the app actually investigates. Mix of healthy units
    and units silently mid-way through a fault trajectory (never reaching the
    labeled 'failure point' -- that's for the model to predict)."""
    rows = []
    master = []
    maint_rows = []

    for i in range(n_units):
        eq_id = f"EQ-{i+1:03d}"
        eq_type = EQUIPMENT_TYPES[i % len(EQUIPMENT_TYPES)]
        name = f"{eq_type} {chr(65 + i // len(EQUIPMENT_TYPES))}{i % len(EQUIPMENT_TYPES) + 1}"
        location = LOCATIONS[i % len(LOCATIONS)]
        criticality = ["High", "Medium", "Low"][i % 3]
        install_date = pd.Timestamp("2019-01-01") + pd.Timedelta(days=int(RNG.integers(0, 1800)))

        n_cycles = int(RNG.integers(150, 260))
        is_degrading = i % 3 != 0  # ~2/3 of fleet shows some degree of an emerging issue
        if is_degrading:
            fault = FAULT_PATTERNS[i % len(FAULT_PATTERNS)]
            onset_frac = float(RNG.uniform(0.5, 0.85))
            severity = float(RNG.uniform(0.25, 0.95))  # how far along -- NOT failed
        else:
            fault, onset_frac, severity = None, 1.0, 0.0

        if fault:
            series = _make_lifecycle(n_cycles, fault, onset_frac, severity)
        else:
            series = _healthy_series(n_cycles)
            for s in SENSORS:
                series[s] = np.clip(series[s], 0, None)

        ts = pd.date_range(start_ts, periods=n_cycles, freq="6h")
        for c in range(n_cycles):
            row = {"equipment_id": eq_id, "cycle": c + 1, "timestamp": ts[c]}
            for s in SENSORS:
                row[s] = round(float(series[s][c]), 3)
            rows.append(row)

        master.append({
            "equipment_id": eq_id, "name": name, "type": eq_type, "location": location,
            "install_date": str(install_date.date()), "criticality": criticality,
        })

        # maintenance history: a few random past events + possibly one near onset
        n_maint = int(RNG.integers(2, 5))
        for _ in range(n_maint):
            day_offset = int(RNG.integers(0, n_cycles // 4)) * 6 // 24
            mdate = ts[0] + pd.Timedelta(days=day_offset)
            mtype = RNG.choice(["Inspection", "Lubrication", "Filter Replacement", "Calibration"])
            maint_rows.append({"equipment_id": eq_id, "date": str(mdate.date()),
                                "type": mtype, "notes": f"Routine {mtype.lower()} performed."})

    pd.DataFrame(rows).to_csv(os.path.join(OUT_DIR, "sensor_readings.csv"), index=False)
    pd.DataFrame(master).to_csv(os.path.join(OUT_DIR, "equipment_master.csv"), index=False)
    pd.DataFrame(maint_rows).to_csv(os.path.join(OUT_DIR, "maintenance_logs.csv"), index=False)


ACTION_LIBRARY = {
    "bearing_wear": {
        "immediate": ["Schedule bearing inspection within 48 hours", "Reduce load / RPM if operationally possible"],
        "short_term": ["Plan bearing replacement during next maintenance window", "Increase vibration monitoring frequency"],
        "monitoring": ["Trend vibration + temperature weekly"],
    },
    "lubrication_breakdown": {
        "immediate": ["Perform lubrication check and top-up immediately", "Verify lubricant grade and contamination"],
        "short_term": ["Full lubricant replacement", "Inspect seals for lubricant loss"],
        "monitoring": ["Trend temperature daily until stabilized"],
    },
    "seal_leak": {
        "immediate": ["Inspect seals and gaskets for visible leakage", "Contain/clean any leaked fluid for safety"],
        "short_term": ["Replace worn seals", "Check downstream pressure-dependent safety systems"],
        "monitoring": ["Trend pressure + vibration together"],
    },
    "blockage": {
        "immediate": ["Inspect and clear intake/outlet lines for obstruction", "Check filters for clogging"],
        "short_term": ["Clean or replace filtration elements", "Review process material for contaminants"],
        "monitoring": ["Trend pressure + current together"],
    },
    "electrical_overload": {
        "immediate": ["De-rate load or inspect motor drive/electrical supply now", "Check for phase imbalance / overcurrent trips"],
        "short_term": ["Inspect windings and drive electronics", "Verify protective relay settings"],
        "monitoring": ["Trend current + RPM stability"],
    },
    "misalignment": {
        "immediate": ["Perform shaft alignment check", "Inspect couplings for wear/looseness"],
        "short_term": ["Re-align and re-balance rotating assembly", "Torque-check mounting bolts"],
        "monitoring": ["Trend vibration spike frequency"],
    },
}


def main():
    generate_historical_fleet()
    generate_current_fleet()
    print("Synthetic datasets written to", OUT_DIR)


if __name__ == "__main__":
    main()
