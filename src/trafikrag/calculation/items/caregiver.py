"""Tazminat kalemi: caregiver (CompensationItem uygular)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from trafikrag.calculation.parameters import (
    compute_annuity_due,
    get_param_warnings,
    get_parameter_version,
    load_life_table,
    round_currency,
    to_decimal,
)
from trafikrag.domain.analysis import CaseInput


class CaregiverItem:
    """Bakıcı gideri tazminatını hesaplar."""

    name: str = "caregiver"

    def compute(self, case: CaseInput, params: dict[str, Any]) -> dict[str, Any]:
        version = get_parameter_version(params)
        warnings: list[str] = []
        used_keys: list[str] = []

        has_months = (
            case.caregiver_months is not None
            and to_decimal(case.caregiver_months) > Decimal(0)
        )
        has_lifelong = (
            case.caregiver_months is None
            and case.caregiver_ratio is not None
            and case.age is not None
        )

        if not has_months and not has_lifelong:
            return {
                "amount": Decimal("0.00"),
                "formula": "aylik_bakici_ucreti * bagimlilik_orani * sure_ay",
                "inputs": {
                    "monthly_caregiver_wage": Decimal("0.00"),
                    "caregiver_ratio": case.caregiver_ratio,
                    "caregiver_months": Decimal(0),
                    "parameter_version": version,
                },
                "parameter_version": version,
                "warnings": warnings,
            }

        is_documented = bool(params.get("caregiver_documented", False))
        if is_documented:
            monthly_wage = to_decimal(params["asgari_ucret"]["brut"])
            used_keys.append("asgari_ucret.brut")
        else:
            monthly_wage = to_decimal(params["asgari_ucret"]["net"])
            used_keys.append("asgari_ucret.net")

        gs_cfg = params["genel_sartlar_2021"]
        used_keys.append("genel_sartlar_2021.bakici_orani")
        if case.caregiver_ratio is not None:
            ratio = to_decimal(case.caregiver_ratio)
        else:
            ratio = to_decimal(gs_cfg["bakici_orani"]["tam"])
            warnings.append("Bakıcı bağımlılık oranı girilmediğinden tam bağımlı (1.0) varsayıldı")

        min_disability_for_partial = to_decimal(
            gs_cfg.get("kismi_bakici_alt_maluliyet", Decimal("0.50"))
        )
        if (
            ratio == to_decimal(gs_cfg["bakici_orani"]["kismi"])
            and case.disability_rate is not None
            and to_decimal(case.disability_rate) < min_disability_for_partial
        ):
            warnings.append(
                "Genel Şartlar Ek-2 m.8 uyarınca kısmi bağımlı bakıcı gideri için maluliyet oranı en az %50 olmalıdır"
            )

        if has_months:
            months = to_decimal(case.caregiver_months)  # type: ignore[arg-type]
            amount = round_currency(monthly_wage * ratio * months)
            warnings.extend(get_param_warnings(params, used_keys))
            return {
                "amount": amount,
                "formula": "aylik_bakici_ucreti * bagimlilik_orani * sure_ay",
                "inputs": {
                    "monthly_caregiver_wage": monthly_wage,
                    "caregiver_ratio": ratio,
                    "caregiver_months": months,
                    "is_documented": is_documented,
                    "parameter_version": version,
                },
                "parameter_version": version,
                "warnings": warnings,
            }

        # Süre (ay) verilmemiş ancak bağımlılık oranı ve yaş verilmişse ömür boyu anüite
        gender = case.gender if case.gender in ("E", "K") else "E"
        table_map = gs_cfg["yasam_tablosu"]
        table_name = str(table_map["kadin"] if gender == "K" else table_map["erkek"])
        discount_rate = to_decimal(gs_cfg["iskonto"])
        used_keys.extend(["genel_sartlar_2021.iskonto", "genel_sartlar_2021.yasam_tablosu"])

        table = load_life_table(table_name, gender=gender, tables_dir=params.get("_base_dir"))
        annuity_factor = compute_annuity_due(table, int(case.age), discount_rate)  # type: ignore[arg-type]
        annual_wage = monthly_wage * Decimal(12)
        amount = round_currency(annual_wage * ratio * annuity_factor)
        warnings.extend(get_param_warnings(params, used_keys))

        return {
            "amount": amount,
            "formula": "12 * aylik_bakici_ucreti * bagimlilik_orani * ä_x",
            "inputs": {
                "monthly_caregiver_wage": monthly_wage,
                "caregiver_ratio": ratio,
                "annuity_factor": annuity_factor,
                "life_table": table_name,
                "is_documented": is_documented,
                "parameter_version": version,
            },
            "parameter_version": version,
            "warnings": warnings,
        }
