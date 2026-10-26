"""Tazminat kalemi: temporary_disability (CompensationItem uygular)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from trafikrag.calculation.parameters import (
    get_param_warnings,
    get_parameter_version,
    resolve_monthly_net_income,
    round_currency,
    to_decimal,
)
from trafikrag.domain.analysis import CaseInput


class TemporaryDisabilityItem:
    """Geçici iş göremezlik tazminatını hesaplar: (aylık net gelir / 30) * gün sayısı."""

    name: str = "temporary_disability"

    def compute(self, case: CaseInput, params: dict[str, Any]) -> dict[str, Any]:
        version = get_parameter_version(params)
        if case.temporary_incapacity_months is None:
            return {
                "amount": Decimal("0.00"),
                "formula": "(aylik_net_gelir / 30) * gun_sayisi",
                "inputs": {
                    "monthly_net_income": Decimal("0.00"),
                    "temporary_incapacity_months": Decimal(0),
                    "days": Decimal(0),
                    "parameter_version": version,
                },
                "parameter_version": version,
                "warnings": [],
            }

        months = to_decimal(case.temporary_incapacity_months)
        if months <= Decimal(0):
            return {
                "amount": Decimal("0.00"),
                "formula": "(aylik_net_gelir / 30) * gun_sayisi",
                "inputs": {
                    "monthly_net_income": Decimal("0.00"),
                    "temporary_incapacity_months": months,
                    "days": Decimal(0),
                    "parameter_version": version,
                },
                "parameter_version": version,
                "warnings": [],
            }

        active_income, passive_income, income_warnings, used_keys = resolve_monthly_net_income(
            case, params
        )
        aktif_ust_yas = int(params["genel_sartlar_2021"]["aktif_donem"][1])
        is_passive = (
            case.employment_status == "emekli"
            or (case.age is not None and case.age >= aktif_ust_yas)
        )
        monthly_net = passive_income if is_passive else active_income

        days = months * Decimal(30)
        daily_net = monthly_net / Decimal(30)
        amount = round_currency(daily_net * days)

        warnings = list(income_warnings) + get_param_warnings(params, used_keys)

        return {
            "amount": amount,
            "formula": "(aylik_net_gelir / 30) * gun_sayisi",
            "inputs": {
                "monthly_net_income": monthly_net,
                "temporary_incapacity_months": months,
                "days": days,
                "parameter_version": version,
            },
            "parameter_version": version,
            "warnings": warnings,
        }
