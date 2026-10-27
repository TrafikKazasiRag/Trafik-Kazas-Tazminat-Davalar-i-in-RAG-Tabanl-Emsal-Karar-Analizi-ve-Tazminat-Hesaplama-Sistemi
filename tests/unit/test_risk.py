"""Risk modülü birim testleri (outcome_stats.py)."""
from __future__ import annotations

from decimal import Decimal

from trafikrag.domain.facts import ExtractedFacts
from trafikrag.extraction.validators import ALLOWED_OUTCOMES
from trafikrag.risk.outcome_stats import (
    OUTCOME_CATEGORIES,
    compute_expected_value,
    compute_outcome_stats,
    wilson_confidence_interval,
)


def test_outcome_categories_matches_allowed_outcomes():
    assert set(OUTCOME_CATEGORIES) == ALLOWED_OUTCOMES
    assert "istinaf_reddi" in OUTCOME_CATEGORIES
    assert "kaldirma" in OUTCOME_CATEGORIES


def test_insufficient_precedents_returns_yetersiz_emsal():
    facts = [ExtractedFacts(decision_id=f"d{i}", outcome="kabul") for i in range(5)]
    stats = compute_outcome_stats(facts, min_samples=10)
    assert stats["status"] == "yetersiz_emsal"
    assert stats["probabilities"] is None
    assert any("istinaf (BAM)" in w for w in stats["warnings"])


def test_sufficient_precedents_with_istinaf_outcomes_computes_wilson_ci():
    facts = (
        [ExtractedFacts(decision_id=f"ir{i}", outcome="istinaf_reddi") for i in range(5)]
        + [ExtractedFacts(decision_id=f"kl{i}", outcome="kaldirma") for i in range(3)]
        + [ExtractedFacts(decision_id=f"k{i}", outcome="kabul") for i in range(1)]
        + [ExtractedFacts(decision_id=f"r{i}", outcome="ret") for i in range(1)]
    )
    stats = compute_outcome_stats(facts, min_samples=10)
    assert stats["status"] == "ok"
    assert stats["sample_size"] == 10
    ir_info = stats["probabilities"]["istinaf_reddi"]
    assert ir_info["count"] == 5
    assert ir_info["proportion"] == Decimal("0.5000")
    low, high = ir_info["wilson_95_ci"]
    assert low == Decimal("0.2366")
    assert high == Decimal("0.7634")
    assert stats["probabilities"]["kaldirma"]["count"] == 3


def test_wilson_interval_bounds():
    low, high = wilson_confidence_interval(0, 10)
    assert low == Decimal("0.0000")
    assert Decimal("0.20") < high < Decimal("0.30")


def test_expected_value_hand_calculated():
    """BD = 0.70 * 100.000 - 10.000 - 0.20 * 30.000 = 70.000 - 10.000 - 6.000 = 54.000,00 TL."""
    bd = compute_expected_value(
        net_compensation=Decimal("100000.00"),
        total_costs=Decimal("10000.00"),
        counter_attorney_fee=Decimal("30000.00"),
        p_accept=Decimal("0.70"),
        p_reject=Decimal("0.20"),
    )
    assert isinstance(bd, Decimal)
    assert bd == Decimal("54000.00")
