"""Sonuç dağılımı, Wilson güven aralığı ve beklenen değer (risk/outcome_stats.py)."""
from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

from trafikrag.calculation.parameters import round_currency, to_decimal
from trafikrag.domain.facts import ExtractedFacts
from trafikrag.extraction.validators import ALLOWED_OUTCOMES

OUTCOME_CATEGORIES = tuple(sorted(ALLOWED_OUTCOMES))
DEFAULT_MIN_SAMPLES = 10
Z_95 = 1.959963984540054


def wilson_confidence_interval(
    successes: int, total: int, z: float = Z_95
) -> tuple[Decimal, Decimal]:
    """Wilson güven aralığı alt ve üst sınırlarını (Decimal, 4 ondalık) hesaplar."""
    if total <= 0:
        return Decimal("0.0000"), Decimal("0.0000")

    p_hat = successes / total
    z2 = z * z
    denom = 1.0 + z2 / total
    center = p_hat + z2 / (2.0 * total)
    margin = z * math.sqrt((p_hat * (1.0 - p_hat) / total) + (z2 / (4.0 * total * total)))

    lower = max(0.0, (center - margin) / denom)
    upper = min(1.0, (center + margin) / denom)
    return (
        to_decimal(f"{lower:.4f}"),
        to_decimal(f"{upper:.4f}"),
    )


def compute_outcome_stats(
    facts_list: list[ExtractedFacts],
    min_samples: int = DEFAULT_MIN_SAMPLES,
) -> dict[str, Any]:
    """Emsal kararlardan çıkarılan sonuçların dağılımını ve Wilson güven aralıklarını hesaplar."""
    valid_outcomes = [
        f.outcome for f in facts_list if f.outcome in ALLOWED_OUTCOMES
    ]
    n = len(valid_outcomes)
    selection_bias_warning = (
        "Veri setindeki kararlar çoğunlukla istinaf (BAM) ve üst derece incelemesine taşınmış "
        "uyuşmazlıkları içerdiğinden seçim yanılımı (istinaf reddi, kaldırma ve bozma kararlarının "
        "aşırı temsili) üretir; tüm ilk derece davalarının genel dağılımını temsil etmez."
    )

    if n < min_samples:
        return {
            "status": "yetersiz_emsal",
            "sample_size": n,
            "min_samples_required": min_samples,
            "message": f"Yetersiz emsal ({n} < {min_samples}); istatistiksel olasılık gösterilmez.",
            "probabilities": None,
            "warnings": [
                f"Emsal sayısı eşik değerin ({min_samples}) altında olduğundan olasılık dağılımı hesaplanmadı",
                selection_bias_warning,
            ],
        }

    counts = {cat: 0 for cat in OUTCOME_CATEGORIES}
    for outcome in valid_outcomes:
        if outcome is not None:
            counts[outcome] += 1

    probabilities: dict[str, dict[str, Any]] = {}
    for cat in OUTCOME_CATEGORIES:
        k = counts[cat]
        p_hat = to_decimal(f"{k / n:.4f}")
        ci_low, ci_high = wilson_confidence_interval(k, n)
        probabilities[cat] = {
            "count": k,
            "proportion": p_hat,
            "wilson_95_ci": (ci_low, ci_high),
        }

    return {
        "status": "ok",
        "sample_size": n,
        "min_samples_required": min_samples,
        "probabilities": probabilities,
        "warnings": [selection_bias_warning],
    }


def compute_expected_value(
    net_compensation: Decimal | int | str,
    total_costs: Decimal | int | str,
    counter_attorney_fee: Decimal | int | str,
    p_accept: Decimal | int | str,
    p_reject: Decimal | int | str,
) -> Decimal:
    """Basit beklenen değer: BD = P_kabul * T_net - M_toplam - P_ret * V_karsi."""
    t_net = to_decimal(net_compensation)
    m_top = to_decimal(total_costs)
    v_karsi = to_decimal(counter_attorney_fee)
    p_kab = to_decimal(p_accept)
    p_ret = to_decimal(p_reject)

    bd = (p_kab * t_net) - m_top - (p_ret * v_karsi)
    return round_currency(bd)
