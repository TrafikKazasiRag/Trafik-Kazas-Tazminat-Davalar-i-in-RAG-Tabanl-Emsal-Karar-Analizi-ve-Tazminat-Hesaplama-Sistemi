"""Kusur indirimi (T_net = T_toplam * (1 - p))."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from trafikrag.calculation.parameters import round_currency, to_decimal


def apply_fault_discount(
    total_amount: Decimal | int | str,
    plaintiff_fault: float | Decimal | None,
) -> dict[str, Any]:
    """Toplam tazminat tutarına davacı kusur oranına göre indirim uygular."""
    gross = round_currency(to_decimal(total_amount))
    warnings: list[str] = []

    if plaintiff_fault is None:
        warnings.append("kusur oranı girilmedi")
        return {
            "gross_amount": gross,
            "net_amount": gross,
            "discount_amount": Decimal("0.00"),
            "plaintiff_fault": None,
            "defendant_share": Decimal(1),
            "formula": "T_net = T_toplam (kusur oranı girilmedi)",
            "warnings": warnings,
        }

    p = to_decimal(plaintiff_fault)
    defendant_share = Decimal(1) - p
    net = round_currency(gross * defendant_share)
    discount = round_currency(gross - net)

    return {
        "gross_amount": gross,
        "net_amount": net,
        "discount_amount": discount,
        "plaintiff_fault": p,
        "defendant_share": defendant_share,
        "formula": "T_net = T_toplam * (1 - p)",
        "warnings": warnings,
    }
