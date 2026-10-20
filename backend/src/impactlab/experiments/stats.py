"""Statistical aggregation functions for Monte Carlo experiments."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class SummaryStats:
    """Summary statistics for a sample of Monte Carlo runs."""

    count: int
    mean: float
    median: float
    std: float
    stderr: float
    p5: float
    p25: float
    p75: float
    p95: float
    min: float
    max: float

    def to_dict(self) -> dict[str, float | int]:
        """Convert to dictionary."""
        return asdict(self)


def aggregate_series(values: Sequence[float]) -> SummaryStats:
    """Compute summary statistics (mean, median, p5, p95, standard error) for a series.

    Args:
        values: Sequence of numeric values.

    Returns:
        SummaryStats dataclass.
    """
    if not values:
        return SummaryStats(
            count=0,
            mean=0.0,
            median=0.0,
            std=0.0,
            stderr=0.0,
            p5=0.0,
            p25=0.0,
            p75=0.0,
            p95=0.0,
            min=0.0,
            max=0.0,
        )

    arr = np.array(values, dtype=np.float64)
    n = len(arr)
    mean = float(np.mean(arr))
    median = float(np.median(arr))
    std = float(np.std(arr, ddof=1)) if n > 1 else 0.0
    stderr = (std / np.sqrt(n)) if n > 1 else 0.0
    p5, p25, p75, p95 = [float(x) for x in np.percentile(arr, [5, 25, 75, 95])]
    min_v = float(np.min(arr))
    max_v = float(np.max(arr))

    return SummaryStats(
        count=n,
        mean=mean,
        median=median,
        std=std,
        stderr=stderr,
        p5=p5,
        p25=p25,
        p75=p75,
        p95=p95,
        min=min_v,
        max=max_v,
    )
