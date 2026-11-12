"""Deterministic anomaly detectors, independent of any LLM."""

from dataclasses import dataclass


@dataclass(frozen=True)
class QualitySignal:
    """A reproducible, machine-readable quality observation."""

    kind: str
    severity: str
    observed: float
    threshold: float
    detail: str


def detect_volume_drop(
    current: int, baseline: float, minimum_ratio: float = 0.6
) -> QualitySignal | None:
    """Flag volume loss against a positive historical baseline."""
    if baseline <= 0:
        return None
    ratio = current / baseline
    if ratio < minimum_ratio:
        return QualitySignal(
            "volume_drop", "high", ratio, minimum_ratio, "Volume below baseline ratio"
        )
    return None


def detect_null_spike(
    nulls: int, total: int, max_rate: float = 0.05
) -> QualitySignal | None:
    """Flag excessive null values; zero-row batches are checked separately."""
    if total <= 0:
        return None
    rate = nulls / total
    if rate > max_rate:
        return QualitySignal(
            "null_spike", "high", rate, max_rate, "Null rate above limit"
        )
    return None


def detect_schema_change(actual: set[str], expected: set[str]) -> dict[str, list[str]]:
    """Return missing and unexpected columns in stable order."""
    return {
        "missing": sorted(expected - actual),
        "unexpected": sorted(actual - expected),
    }
