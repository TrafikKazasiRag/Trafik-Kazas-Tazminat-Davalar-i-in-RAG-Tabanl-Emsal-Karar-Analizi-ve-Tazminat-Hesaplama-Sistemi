"""Analiz isteği ve sonucu."""
from dataclasses import dataclass, field
from datetime import date

GENDERS = ("E", "K")
INCOME_BASES = ("net", "brut", "asgari", "bilinmiyor")
EMPLOYMENT_STATUSES = ("calisiyor", "emekli", "calismiyor")
METHODS = ("genel_sartlar", "yargitay")
CAREGIVER_RATIOS = (0.5, 1.0)


@dataclass
class CaseInput:
    narrative: str = ""
    # --- kişi ---
    age: int | None = None                   # KAZA TARİHİNDEKİ yaş
    gender: str | None = None                # "E" | "K" (yaşam tabloları cinsiyete göre)
    employment_status: str | None = None     # "calisiyor" | "emekli" | "calismiyor"
    # --- gelir ---
    monthly_income: float | None = None
    income_basis: str | None = None          # "net" | "brut" | "asgari" | "bilinmiyor"
    # --- yaralanma ve masraflar ---
    injury_type: str | None = None
    disability_rate: float | None = None     # kalıcı maluliyet oranı, 0-1
    temporary_incapacity_months: float | None = None
    caregiver_months: float | None = None
    caregiver_ratio: float | None = None     # 0.5 | 1.0
    treatment_costs: float | None = None
    # --- kusur ---
    plaintiff_fault: float | None = None     # davacı kusur oranı, 0-1
    # --- tarih ve poliçe ---
    accident_date: date | None = None
    calculation_date: date | None = None     # hesap tarihi; boşsa bugün
    policy_date: date | None = None
    policy_limit: float | None = None
    # --- yöntem ---
    method: str | None = None 


@dataclass
class Citation:
    decision_id: str
    chunk_id: str
    quote: str


@dataclass
class AnalysisResult:
    summary: str
    citations: list[Citation] = field(default_factory=list)
    compensation: dict = field(default_factory=dict)
    costs: dict = field(default_factory=dict)
    risk: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

def validate_case(case: CaseInput) -> tuple[list[str], list[str]]:
    """(hatalar, uyarılar) döner. Hata varsa hesap yapılmaz, uyarı varsa varsayımla devam edilir."""
    errors: list[str] = []
    warnings: list[str] = []

    for name in ("disability_rate", "plaintiff_fault"):
        value = getattr(case, name)
        if value is not None and not 0 <= value <= 1:
            errors.append(f"{name} 0 ile 1 arasında olmalı")
    if case.age is not None and not 0 <= case.age <= 120:
        errors.append("age 0-120 arasında olmalı")
    for name in ("monthly_income", "treatment_costs", "temporary_incapacity_months",
                 "caregiver_months", "policy_limit"):
        value = getattr(case, name)
        if value is not None and value < 0:
            errors.append(f"{name} negatif olamaz")
    choices = {
        "gender": GENDERS,
        "income_basis": INCOME_BASES,
        "employment_status": EMPLOYMENT_STATUSES,
        "method": METHODS,
        "caregiver_ratio": CAREGIVER_RATIOS,
    }
    for name, allowed in choices.items():
        value = getattr(case, name)
        if value is not None and value not in allowed:
            errors.append(f"{name} şunlardan biri olmalı: {allowed}")
    if case.accident_date and case.calculation_date and case.accident_date > case.calculation_date:
        errors.append("accident_date, calculation_date'ten sonra olamaz")

    if case.accident_date is None:
        warnings.append("Kaza tarihi girilmedi: güncel kurallar kullanılacak")
    if case.gender is None:
        warnings.append("Cinsiyet girilmedi: yaşam tablosu için varsayım gerekir")
    if case.monthly_income is None or case.income_basis == "bilinmiyor":
        warnings.append("Gelir bilinmiyor: asgari ücret kullanılacak")
    elif case.income_basis is None:
        warnings.append("Gelir türü (net/brüt) belirtilmedi")
    if case.disability_rate is None:
        warnings.append("Maluliyet oranı yok: sürekli iş göremezlik hesaplanmayacak")
    return errors, warnings
