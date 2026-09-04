"""Data loading, cleaning, and feature engineering shared by training (on the
historical run-to-failure fleet) and inference (on the current fleet)."""
import os
import numpy as np
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

SENSORS = ["temperature", "vibration", "pressure", "current", "rpm"]
ROLL_WINDOW = 10


def load_raw():
    hist = pd.read_csv(os.path.join(DATA_DIR, "sensor_readings_history.csv"), parse_dates=["timestamp"])
    incidents = pd.read_csv(os.path.join(DATA_DIR, "failure_history.csv"))
    current = pd.read_csv(os.path.join(DATA_DIR, "sensor_readings.csv"), parse_dates=["timestamp"])
    master = pd.read_csv(os.path.join(DATA_DIR, "equipment_master.csv"), parse_dates=["install_date"])
    maint = pd.read_csv(os.path.join(DATA_DIR, "maintenance_logs.csv"), parse_dates=["date"])
    return hist, incidents, current, master, maint


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Basic cleaning: sort, de-dup, interpolate gaps, clip impossible values."""
    df = df.sort_values(["equipment_id", "cycle"]).drop_duplicates(["equipment_id", "cycle"])
    df = df.groupby("equipment_id", group_keys=False).apply(
        lambda g: g.assign(**{s: g[s].interpolate().bfill().ffill() for s in SENSORS})
    )
    for s in SENSORS:
        df[s] = df[s].clip(lower=0)
    return df.reset_index(drop=True)


def _slope(y: np.ndarray) -> float:
    if len(y) < 2:
        return 0.0
    x = np.arange(len(y))
    return float(np.polyfit(x, y, 1)[0])


TREND_WINDOW = 30  # longer, smoother window used for root-cause trend gating


def engineer_features(df: pd.DataFrame, window: int = ROLL_WINDOW) -> pd.DataFrame:
    """Adds rolling mean/std/slope per sensor, computed causally (no lookahead).

    Two slope signals are produced per sensor: a short (`_slope`, window=10)
    one used as a raw ML model feature, and a longer (`_trend_slope`,
    window=30) one used by the root-cause rule engine, which needs a
    noise-resistant trend direction rather than a point-in-time estimate.
    """
    df = df.copy()
    out_frames = []
    for eq_id, g in df.groupby("equipment_id"):
        g = g.sort_values("cycle").reset_index(drop=True)
        for s in SENSORS:
            g[f"{s}_roll_mean"] = g[s].rolling(window, min_periods=3).mean()
            g[f"{s}_roll_std"] = g[s].rolling(window, min_periods=3).std().fillna(0)
            g[f"{s}_slope"] = g[s].rolling(window, min_periods=3).apply(_slope, raw=True)
            g[f"{s}_trend_slope"] = g[s].rolling(TREND_WINDOW, min_periods=5).apply(_slope, raw=True)
        fill_cols = [c for c in g.columns if c.endswith(("_roll_mean", "_roll_std", "_slope", "_trend_slope"))]
        g[fill_cols] = g[fill_cols].bfill().fillna(0)
        out_frames.append(g)
    return pd.concat(out_frames, ignore_index=True)


def feature_columns():
    cols = []
    for s in SENSORS:
        cols += [f"{s}_roll_mean", f"{s}_roll_std", f"{s}_slope"]
    return cols


def baseline_stats(df: pd.DataFrame, healthy_frac_cutoff: float = 0.3) -> dict:
    """Healthy-state mean/std per sensor, estimated from the early (presumed
    healthy) portion of every unit's lifecycle -- used for z-score evidence."""
    stats = {}
    early_rows = []
    for eq_id, g in df.groupby("equipment_id"):
        g = g.sort_values("cycle")
        cutoff = max(5, int(len(g) * healthy_frac_cutoff))
        early_rows.append(g.iloc[:cutoff])
    early = pd.concat(early_rows, ignore_index=True)
    for s in SENSORS:
        stats[s] = {"mean": float(early[s].mean()), "std": float(early[s].std() or 1.0)}
    return stats
