import numpy as np
import pytest

from src.expected_loss import compute_expected_loss, compute_lgd


@pytest.mark.parametrize(
    "guarantee,expected_lgd",
    [(0.0, 1.0), (75000.0, 0.25), (100000.0, 0.0),
     (150000.0, 0.0), (-25000.0, 1.0)],
    ids=["no-guarantee", "partial-guarantee", "full-guarantee",
         "clip-below-zero", "clip-above-one"],
)
def test_lgd_is_unguaranteed_share_clipped_to_unit_interval(guarantee, expected_lgd):
    result = compute_lgd([100000.0], [guarantee])

    np.testing.assert_allclose(result, [expected_lgd])


@pytest.mark.parametrize("guarantee", [0.0, 100.0])
def test_zero_gross_approval_has_zero_lgd_and_expected_loss(guarantee):
    # np.where evaluates the division before selecting the zero-approval fallback.
    with np.errstate(divide="ignore", invalid="ignore"):
        result = compute_expected_loss([0.4], [0.0], [guarantee])

    np.testing.assert_array_equal(result["LGD"], [0.0])
    np.testing.assert_array_equal(result["EAD"], [0.0])
    np.testing.assert_array_equal(result["EL"], [0.0])
    assert result["portfolio_EL"] == 0.0
    assert np.isfinite(result["EL"]).all()


def test_expected_loss_is_pd_times_lgd_times_ead_for_each_loan():
    result = compute_expected_loss(
        pd_scores=[0.0, 0.2, 1.0],
        gr_appv=[100000.0, 250000.0, 100000.0],
        sba_appv=[75000.0, 187500.0, 75000.0],
    )

    np.testing.assert_allclose(result["PD"], [0.0, 0.2, 1.0])
    np.testing.assert_allclose(result["LGD"], [0.25, 0.25, 0.25])
    np.testing.assert_allclose(result["EAD"], [100000.0, 250000.0, 100000.0])
    np.testing.assert_allclose(result["EL"], [0.0, 12500.0, 25000.0])
    assert result["portfolio_EL"] == pytest.approx(37500.0)
    np.testing.assert_allclose(
        result["bank_exposure_if_default"], [25000.0, 62500.0, 25000.0]
    )
    np.testing.assert_allclose(result["sba_guarantee_covers"], [75000.0, 187500.0, 75000.0])
