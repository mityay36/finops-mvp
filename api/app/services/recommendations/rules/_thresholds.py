"""Centralized rule thresholds, env-overridable for experiments.

In production, defaults below apply (14-day window, 10-day minimum).
For diss experiments where synthetic workloads have only 2-3 days of
data, set:

    export FINOPS_RULE_WINDOW_DAYS=3
    export FINOPS_RULE_MIN_VALID_DAYS=2

This is the only knob; the rest of the rule logic (p95, safety margin,
severity thresholds) is unchanged. Experimental override is logged at
engine startup via factory.
"""

from __future__ import annotations

import os


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        v = int(raw)
        if v <= 0:
            return default
        return v
    except ValueError:
        return default


WINDOW_DAYS: int = _int_env("FINOPS_RULE_WINDOW_DAYS", 14)
MIN_VALID_DAYS: int = _int_env("FINOPS_RULE_MIN_VALID_DAYS", 10)