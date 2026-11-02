"""Current training feature interface; historical serving uses ml.runtimes.

The v2 implementation is retained byte-for-byte in features/v2.py. Changing
semantics requires a new module/version, not editing a historical runtime.
"""
from .features.v2 import (
    SENSORS, UNITS, FEATURES, FEATURE_VERSION, FeaturePolicy, digest, label, snapshot,
)
