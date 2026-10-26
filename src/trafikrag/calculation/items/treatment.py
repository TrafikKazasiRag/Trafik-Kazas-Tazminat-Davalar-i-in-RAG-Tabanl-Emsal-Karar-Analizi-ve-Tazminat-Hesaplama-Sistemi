"""Tazminat kalemi: treatment (CompensationItem uygular)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from trafikrag.calculation.parameters import (
    get_parameter_version,
    round_currency,
    to_decimal,
)
from trafikrag.domain.analysis import CaseInput


class TreatmentItem:
    """Belgeli tedavi giderlerini hesaplar; SGK karşılaması uyarısını üretir."""

    name: str = "treatment"

    def compute(self, case: CaseInput, params: dict[str, Any]) -> dict[str, Any]:
        version = get_parameter_version(params)
        warnings: list[str] = []

        if case.treatment_costs is None:
            return {
                "amount": Decimal("0.00"),
                "formula": "belgeli_tedavi_gideri - sgk_karsilanan",
                "inputs": {
                    "treatment_costs": Decimal("0.00"),
                    "sgk_covered": Decimal("0.00"),
                    "parameter_version": version,
                },
                "parameter_version": version,
                "warnings": warnings,
            }

        documented = round_currency(to_decimal(case.treatment_costs))
        sgk_covered = round_currency(to_decimal(params.get("sgk_treatment_covered", 0)))
        net_treatment = max(Decimal("0.00"), round_currency(documented - sgk_covered))

        if documented > Decimal("0.00"):
            warnings.append(
                "Tedavi giderlerinde SGK tarafından karşılanan kısım varsa düşülmelidir (hukuki doğrulama gerekir)"
            )

        return {
            "amount": net_treatment,
            "formula": "belgeli_tedavi_gideri - sgk_karsilanan",
            "inputs": {
                "treatment_costs": documented,
                "sgk_covered": sgk_covered,
                "parameter_version": version,
            },
            "parameter_version": version,
            "warnings": warnings,
        }
