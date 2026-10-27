"""Tazminat kalemlerini sırayla çalıştırır, kusur indirimi, poliçe limiti ve masrafları birleştirir (LLM'siz)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from trafikrag.calculation.costs import calculate_costs
from trafikrag.calculation.fault import apply_fault_discount
from trafikrag.calculation.items.caregiver import CaregiverItem
from trafikrag.calculation.items.permanent_disability import PermanentDisabilityItem
from trafikrag.calculation.items.temporary_disability import TemporaryDisabilityItem
from trafikrag.calculation.items.treatment import TreatmentItem
from trafikrag.calculation.parameters import (
    get_param_warnings,
    get_parameter_version,
    load_parameters,
    round_currency,
    to_decimal,
)
from trafikrag.domain.analysis import AnalysisResult, CaseInput, validate_case
from trafikrag.ports.compensation import CompensationItem


def select_disability_regulation(accident_date: date | None) -> str:
    """Kaza tarihine göre uygulanacak maluliyet tespit mevzuatını döner (Yargıtay 4. HD 2024/3323 E.)."""
    if accident_date is None:
        return "Erişkinler İçin Engellilik Değerlendirmesi Hakkında Yönetmelik (varsayılan güncel mevzuat)"
    if accident_date < date(2008, 10, 11):
        return "Sosyal Sigorta Sağlık İşlemleri Tüzüğü"
    if accident_date < date(2013, 9, 1):
        return "Çalışma Gücü ve Meslekte Kazanma Gücü Kaybı Oranı Tespit İşlemleri Yönetmeliği"
    if accident_date < date(2015, 6, 1):
        return "Maluliyet Tespiti İşlemleri Yönetmeliği"
    if accident_date < date(2019, 2, 20):
        return "Özürlülük Ölçütü, Sınıflandırması ve Özürlülere Verilecek Sağlık Kurul Raporları Hakkında Yönetmelik"
    return "Erişkinler İçin Engellilik Değerlendirmesi Hakkında Yönetmelik"


def select_rule_version(case: CaseInput) -> str:
    """Vaka tarihlerine ve seçilen yönteme göre kural seti etiketini döner."""
    if case.method == "genel_sartlar":
        return "genel_sartlar_2021"
    if case.method == "yargitay":
        return "yargitay_4hd_trh2010_progresif_rant"
    if case.policy_date is not None and case.policy_date < date(2021, 12, 4):
        return "karsilastirmali (varsayilan: yargitay_4hd_trh2010_progresif_rant)"
    return "karsilastirmali (varsayilan: genel_sartlar_2021)"


def check_statute_of_limitations(
    accident_date: date | None,
    calculation_date: date | None,
    params: dict[str, Any],
) -> list[str]:
    """Genel Şartlar C.8 zamanaşımı kontrolü (2 yıl / 10 yıl)."""
    if accident_date is None:
        return []
    ref_date = calculation_date if calculation_date is not None else date.today()
    zamanasimi_cfg = params["genel_sartlar_2021"]["zamanasimi"]
    kisa_yil = int(zamanasimi_cfg["kisa_yil"])
    uzun_yil = int(zamanasimi_cfg["uzun_yil"])

    elapsed_days = (ref_date - accident_date).days
    warnings: list[str] = []
    if elapsed_days > uzun_yil * 365:
        warnings.append(
            f"Zamanaşımı uyarısı (Genel Şartlar C.8): Kaza tarihinden itibaren {uzun_yil} yıllık kesin zamanaşımı süresi aşılmış olabilir (ceza zamanaşımı istisnası kontrol edilmelidir)"
        )
    elif elapsed_days > kisa_yil * 365:
        warnings.append(
            f"Zamanaşımı uyarısı (Genel Şartlar C.8): Kaza tarihinden itibaren {kisa_yil} yıldan fazla süre geçmiştir (öğrenme tarihi ve uzamış ceza zamanaşımı kontrol edilmelidir)"
        )
    return warnings


def _deduplicate_warnings(warnings: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for w in warnings:
        if w not in seen:
            seen.add(w)
            ordered.append(w)
    return ordered


def default_items() -> list[CompensationItem]:
    """MVP kapsamındaki 4 temel maddi tazminat kalemini sırasıyla döner."""
    return [
        TreatmentItem(),
        TemporaryDisabilityItem(),
        PermanentDisabilityItem(),
        CaregiverItem(),
    ]


# Geriye dönük uyumluluk için takma ad
DefaultItems = default_items


class CalculationEngine:
    """Saf, deterministik tazminat ve dava masrafı hesaplama motoru."""

    def __init__(
        self,
        items: list[CompensationItem] | None = None,
        params: dict[str, Any] | None = None,
    ) -> None:
        self.items: list[CompensationItem] = items if items is not None else default_items()
        self.params: dict[str, Any] = params if params is not None else load_parameters()

    def calculate(
        self,
        case: CaseInput,
        params: dict[str, Any] | None = None,
    ) -> AnalysisResult:
        active_params = params if params is not None else self.params
        version = get_parameter_version(active_params)

        errors, validation_warnings = validate_case(case)
        if errors:
            return AnalysisResult(
                summary="Girdi doğrulama hatası nedeniyle tahmini hesap yapılamadı.",
                compensation={
                    "label": "tahmini hesap",
                    "errors": errors,
                    "parameter_version": version,
                },
                costs={},
                risk={},
                warnings=list(validation_warnings),
            )

        all_warnings: list[str] = list(validation_warnings)
        all_warnings.extend(
            check_statute_of_limitations(case.accident_date, case.calculation_date, active_params)
        )

        regulation = select_disability_regulation(case.accident_date)
        if case.disability_rate is not None and to_decimal(case.disability_rate) > Decimal(0):
            all_warnings.append(
                f"Maluliyet oranı ({case.disability_rate}) kaza tarihine göre '{regulation}' hükümlerine uygun sağlık kurulu raporuyla belirlenmiş olmalıdır"
            )

        item_results: dict[str, dict[str, Any]] = {}
        gross_total = Decimal("0.00")

        for item in self.items:
            res = item.compute(case, active_params)
            amount = round_currency(res["amount"])
            gross_total = round_currency(gross_total + amount)
            item_results[item.name] = res
            all_warnings.extend(res.get("warnings", []))

        fault_res = apply_fault_discount(gross_total, case.plaintiff_fault)
        all_warnings.extend(fault_res["warnings"])
        net_total = fault_res["net_amount"]

        # Sigorta poliçe teminat limiti kontrolü
        used_limit_keys: list[str] = []
        if case.policy_limit is not None:
            policy_limit = round_currency(to_decimal(case.policy_limit))
        else:
            policy_limit = round_currency(
                to_decimal(active_params["sigorta_limitleri_2026"]["bedeni_zarar_magdur_basi"])
            )
            used_limit_keys.append("sigorta_limitleri_2026.bedeni_zarar_magdur_basi")
            all_warnings.append(
                "Poliçe teminat limiti (policy_limit) girilmediğinden kaza tarihine uygun limit kullanılmadı; 2026 yılı varsayılan teminat limiti esas alındı"
            )

        insurer_payable = min(net_total, policy_limit)
        excess_over_limit = max(Decimal("0.00"), round_currency(net_total - policy_limit))
        if excess_over_limit > Decimal(0):
            all_warnings.append(
                f"Hesaplanan net tazminat ({net_total} TL) sigorta teminat limitini ({policy_limit} TL) aşmaktadır; aşan {excess_over_limit} TL kısım işleten/sürücü sorumluluğundadır"
            )
        all_warnings.extend(get_param_warnings(active_params, used_limit_keys))

        # Eğer method=None ise iki yöntemin yan yana toplam karşılaştırmasını oluştur
        method_comparison: dict[str, Any] = {}
        perm_res = item_results.get("permanent_disability", {})
        perm_methods = perm_res.get("inputs", {}).get("methods", {})
        if len(perm_methods) > 1:
            other_items_gross = round_currency(
                gross_total - round_currency(perm_res.get("amount", Decimal("0.00")))
            )
            for m_name, m_detail in perm_methods.items():
                m_gross = round_currency(other_items_gross + m_detail["amount"])
                m_fault = apply_fault_discount(m_gross, case.plaintiff_fault)
                method_comparison[m_name] = {
                    "permanent_disability_amount": m_detail["amount"],
                    "gross_total": m_gross,
                    "net_total": m_fault["net_amount"],
                    "insurer_payable": min(m_fault["net_amount"], policy_limit),
                }

        costs_res = calculate_costs(net_total, active_params)
        all_warnings.extend(costs_res.get("warnings", []))

        compensation_payload: dict[str, Any] = {
            "label": "tahmini hesap",
            "rule_version": select_rule_version(case),
            "disability_regulation": regulation,
            "parameter_version": version,
            "items": item_results,
            "gross_total": gross_total,
            "fault_discount": fault_res,
            "net_total": net_total,
            "policy_limit": policy_limit,
            "insurer_payable": insurer_payable,
            "excess_over_limit": excess_over_limit,
        }
        if method_comparison:
            compensation_payload["method_comparison"] = method_comparison

        return AnalysisResult(
            summary=f"Tahmini net maddi tazminat: {net_total} TL (parametre sürümü: {version}). Bu bir tahmini hesaptır, hukuki tavsiye değildir.",
            compensation=compensation_payload,
            costs=costs_res,
            risk={},
            warnings=_deduplicate_warnings(all_warnings),
        )
