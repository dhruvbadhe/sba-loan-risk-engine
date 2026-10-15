import numpy as np
import pytest

from src.risk_tiers import assign_risk_tier, assign_risk_tiers


BOUNDARY_CASES = [
    (0.0, 1),
    (np.nextafter(0.10, 0.0), 1),
    (0.10, 2),
    (np.nextafter(0.10, 1.0), 2),
    (np.nextafter(0.25, 0.0), 2),
    (0.25, 3),
    (np.nextafter(0.25, 1.0), 3),
    (np.nextafter(0.40, 0.0), 3),
    (0.40, 4),
    (np.nextafter(0.40, 1.0), 4),
    (1.0, 4),
]


@pytest.mark.parametrize(
    "pd_score,expected_tier",
    BOUNDARY_CASES,
    ids=[
        "zero",
        "below-10-percent",
        "at-10-percent",
        "above-10-percent",
        "below-25-percent",
        "at-25-percent",
        "above-25-percent",
        "below-40-percent",
        "at-40-percent",
        "above-40-percent",
        "one",
    ],
)
def test_scalar_risk_tiers_at_each_boundary(pd_score, expected_tier):
    assert assign_risk_tier(pd_score) == expected_tier


def test_vectorized_risk_tiers_at_each_boundary():
    scores = np.array([score for score, _ in BOUNDARY_CASES])
    expected_tiers = np.array([tier for _, tier in BOUNDARY_CASES])

    np.testing.assert_array_equal(assign_risk_tiers(scores), expected_tiers)
