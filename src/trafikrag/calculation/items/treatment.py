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
    """Belgeli tedavi giderlerini hesaplar; SGK karşılaması olay bazlı girdi olarak düşülür."""

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
        raw_sgk = getattr(case, "sgk_treatment_covered", None)
        if raw_sgk is None:
            raw_sgk = params.get("sgk_treatment_covered", 0)
        sgk_covered = round_currency(to_decimal(raw_sgk))
        net_treatment = max(Decimal("0.00"), round_currency(documented - sgk_covered))

        if documented > Decimal(0) and getattr(case, "sgk_treatment_covered", None) is None:
            warnings.append(
                "Tedavi giderlerinde SGK tarafından karşılanan kısım (sgk_treatment_covered) belirtilmedi; varsa düşülmelidir (hukuki doğrulama gerekir)"
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
