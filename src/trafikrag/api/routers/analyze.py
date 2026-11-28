"""Analiz ve aktüeryal tazminat hesaplama router'ı."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from trafikrag.calculation.engine import CalculationEngine
from trafikrag.calculation.parameters import to_decimal
from trafikrag.domain.analysis import CaseInput

router = APIRouter(prefix="/analyze", tags=["Analyze"])
engine = CalculationEngine()

AccidentType = Literal[
    "carpisma",
    "yaya_carpmasi",
    "tek_tarafli",
    "park_halindeki_arac",
    "diger",
]


class AnalyzeRequest(BaseModel):
    accident_type: Optional[AccidentType] = Field(default=None)
    victim_role: Optional[str] = Field(default=None)  # surucu, yolcu, yaya
    seatbelt_or_helmet: Optional[bool] = Field(default=None)
    non_pecuniary_claim: Optional[float] = Field(default=None, ge=0.0)
    age: Optional[int] = Field(default=None, ge=0, le=120)
    gender: Optional[str] = Field(default=None)
    disability_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    monthly_income: Optional[float] = Field(default=None, ge=0.0)
    income_basis: Optional[str] = Field(default=None)
    plaintiff_fault: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    temporary_incapacity_months: Optional[float] = Field(default=None, ge=0.0)
    accident_date: Optional[str] = Field(default=None)


@router.post("")
def analyze_case(request: AnalyzeRequest) -> dict[str, Any]:
    # Tarih geldiyse parse et; geçersiz formatta 422 dön, boşsa None bırak
    parsed_accident_date: Optional[date] = None
    if request.accident_date:
        try:
            parsed_accident_date = datetime.strptime(
                request.accident_date, "%Y-%m-%d"
            ).date()
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail="Geçersiz kaza tarihi formatı. YYYY-AA-GG formatı bekleniyor.",
            ) from exc

    narrative_parts = [
        part for part in (request.accident_type, request.victim_role) if part
    ]
    narrative = " - ".join(narrative_parts) if narrative_parts else ""

    # 1. Aktüeryal motor girdisi (sessiz varsayılan yok, None olarak iletilir)
    case_input = CaseInput(
        narrative=narrative,
        age=request.age,
        gender=request.gender,
        monthly_income=(
            to_decimal(request.monthly_income)
            if request.monthly_income is not None
            else None
        ),
        income_basis=request.income_basis,
        disability_rate=(
            to_decimal(request.disability_rate)
            if request.disability_rate is not None
            else None
        ),
        temporary_incapacity_months=(
            to_decimal(request.temporary_incapacity_months)
            if request.temporary_incapacity_months is not None
            else None
        ),
        plaintiff_fault=(
            to_decimal(request.plaintiff_fault)
            if request.plaintiff_fault is not None
            else None
        ),
        accident_date=parsed_accident_date,
    )

    # 2. Deterministik Tazminat ve Masraf Hesabı (yalnızca motor çıktısı)
    analysis_res = engine.calculate(case_input)

    comp = dict(analysis_res.compensation or {})
    costs = dict(analysis_res.costs or {})
    warnings = list(analysis_res.warnings or [])

    # #44 / #27 merge edilene kadar eksik alan uyarıları
    missing_fields = []
    if request.accident_date is None:
        missing_fields.append("Kaza tarihi girilmedi.")
    if request.age is None:
        missing_fields.append("Kaza anındaki yaş girilmedi.")
    if request.monthly_income is None:
        missing_fields.append("Aylık gelir bilgisi girilmedi.")
    if request.disability_rate is None:
        missing_fields.append("Maluliyet oranı girilmedi.")

    warnings.extend(missing_fields)

    calculation_results = {
        "summary": analysis_res.summary,
        "compensation": comp,
        "costs": costs,
        "risk": "henüz hesaplanmıyor",
        "warnings": warnings,
    }

    case_summary = {
        "accident_type": request.accident_type,
        "victim_role": request.victim_role,
        "seatbelt_or_helmet": request.seatbelt_or_helmet,
        "non_pecuniary_claim": request.non_pecuniary_claim,
        "age": case_input.age,
        "gender": case_input.gender,
        "monthly_income": (
            str(case_input.monthly_income)
            if case_input.monthly_income is not None
            else None
        ),
        "income_basis": case_input.income_basis,
        "disability_rate": (
            str(case_input.disability_rate)
            if case_input.disability_rate is not None
            else None
        ),
        "temporary_incapacity_months": (
            str(case_input.temporary_incapacity_months)
            if case_input.temporary_incapacity_months is not None
            else None
        ),
        "plaintiff_fault": (
            str(case_input.plaintiff_fault)
            if case_input.plaintiff_fault is not None
            else None
        ),
        "accident_date": (
            str(case_input.accident_date) if case_input.accident_date else None
        ),
    }

    return {
        "status": "success",
        "message": "Hesaplama tamamlandı.",
        "case_summary": case_summary,
        "calculation_results": calculation_results,
        "precedent_citations": [],
    }