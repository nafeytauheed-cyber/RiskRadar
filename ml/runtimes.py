"""Explicit code allowlist for historical feature replay. No dynamic imports."""
from dataclasses import dataclass
import hashlib
from pathlib import Path
from .features import v1, v2


@dataclass(frozen=True)
class Runtime:
    version: str
    module: object
    promotable: bool

    @property
    def window(self):
        return self.module.FeaturePolicy().window

    @property
    def fingerprint(self):
        return hashlib.sha256(Path(self.module.__file__).read_bytes()).hexdigest()

    def snapshot(self, events, target, arrival_cutoff, freshness_cutoff=None):
        if self.version == 'causal-v1':
            # v1 had no independent freshness clock. Retain its historical output.
            return self.module.snapshot(events, target, arrival_cutoff)
        return self.module.snapshot(
            events, target, arrival_cutoff, freshness_cutoff=freshness_cutoff,
        )


RUNTIMES = {
    'causal-v1': Runtime('causal-v1', v1, False),
    'causal-v2': Runtime('causal-v2', v2, True),
}


def resolve(version):
    try:
        return RUNTIMES[version]
    except (KeyError, TypeError):
        raise ValueError('unsupported feature runtime') from None


def descriptors(artifacts):
    return {
        version: {'sha256': resolve(version).fingerprint,
                  'window_cycles': resolve(version).window}
        for version in sorted({a['feature_version'] for a in artifacts.values()})
    }
