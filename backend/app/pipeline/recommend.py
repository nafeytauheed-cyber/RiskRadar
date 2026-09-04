"""Recommended preventive action generation, keyed off root cause + severity."""
from ..data_gen import ACTION_LIBRARY

GENERIC_ACTIONS = {
    "immediate": ["Review latest inspection log", "Notify shift supervisor of monitoring status"],
    "short_term": ["Continue scheduled preventive maintenance plan"],
    "monitoring": ["Maintain standard telemetry monitoring cadence"],
}


def recommend_actions(root_cause: str, severity: str) -> dict:
    lib = ACTION_LIBRARY.get(root_cause, GENERIC_ACTIONS)
    urgency_map = {
        "Critical": "Act within 24 hours",
        "High": "Act within this week",
        "Medium": "Plan within next maintenance cycle",
        "Low": "Monitor only",
    }
    actions = {
        "urgency": urgency_map.get(severity, "Monitor only"),
        "immediate": lib["immediate"] if severity in ("Critical", "High") else [],
        "short_term": lib["short_term"],
        "monitoring": lib["monitoring"],
    }
    return actions
