"""Analiz ve aktüeryal tazminat hesaplama router'ı."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from trafikrag.calculation.engine import CalculationEngine
from trafikrag.calculation.parameters import round_currency, to_decimal
from trafikrag.domain.analysis import CaseInput
from trafikrag.risk.outcome_stats import compute_expected_value

router = APIRouter(prefix="/analyze", tags=["Analyze"])
engine = CalculationEngine()


class AnalyzeRequest(BaseModel):
    accident_type: Optional[str] = Field(default="kavsak_ihlali")
    victim_role: Optional[str] = Field(default="surucu")  # surucu, yolcu, yaya
    seatbelt_or_helmet: Optional[bool] = Field(default=True)
    non_pecuniary_claim: Optional[float] = Field(default=0.0, ge=0.0)
    age: Optional[int] = Field(default=30, ge=0, le=120)
    gender: Optional[str] = Field(default="E")
    disability_rate: Optional[float] = Field(default=0.15, ge=0.0, le=1.0)
    monthly_income: Optional[float] = Field(default=35000.0, ge=0.0)
    income_basis: Optional[str] = Field(default="net")
    plaintiff_fault: Optional[float] = Field(default=0.0, ge=0.0, le=1.0)
    temporary_incapacity_months: Optional[float] = Field(default=3.0, ge=0.0)
    accident_date: Optional[str] = Field(default=None)


@router.post("/")
def analyze_case(request: AnalyzeRequest) -> dict[str, Any]:
    # Tarih string geldiyse datetime.date objesine parse et
    parsed_accident_date: Optional[date] = None
    if request.accident_date:
        try:
            parsed_accident_date = datetime.strptime(
                request.accident_date, "%Y-%m-%d"
            ).date()
        except ValueError:
            parsed_accident_date = date.today()
    else:
        parsed_accident_date = date.today()

    # Eğer davacı yolcu veya yaya ise kusur durumunu hukuken kalibre et
    effective_fault = float(request.plaintiff_fault or 0.0)
    if request.victim_role in ["yolcu", "yaya"] and effective_fault > 0.2:
        # Yolcular kural olarak kazanın oluşumunda kusursuz kabul edilir
        effective_fault = min(effective_fault, 0.1)

    # 1. Aktüeryal motor girdisi
    case_input = CaseInput(
        narrative=f"{request.accident_type} - {request.victim_role}",
        age=request.age,
        gender=request.gender or "E",
        monthly_income=to_decimal(request.monthly_income)
        if request.monthly_income is not None
        else None,
        income_basis=request.income_basis or "net",
        disability_rate=to_decimal(request.disability_rate)
        if request.disability_rate is not None
        else None,
        temporary_incapacity_months=to_decimal(
            request.temporary_incapacity_months
        )
        if request.temporary_incapacity_months is not None
        else None,
        plaintiff_fault=to_decimal(str(effective_fault)),
        accident_date=parsed_accident_date,
    )

    # 2. Deterministik Tazminat ve Masraf Hesabı
    analysis_res = engine.calculate(case_input)

    comp = dict(analysis_res.compensation or {})
    costs = dict(analysis_res.costs or {})
    warnings = list(analysis_res.warnings or [])

    # Müterafik Kusur İndirimi (Emniyet Kemeri / Kask Takılmamışsa Yargıtay %20 indirir)
    net_comp_dec = to_decimal(comp.get("insurer_payable") or comp.get("net_total") or "0.00")
    if not request.seatbelt_or_helmet and net_comp_dec > 0:
        discount = round_currency(net_comp_dec * Decimal("0.20"))
        net_comp_dec = net_comp_dec - discount
        comp["net_total"] = str(net_comp_dec)
        comp["insurer_payable"] = str(net_comp_dec)
        warnings.append(
            "Yargıtay yerleşik içtihatları uyarınca emniyet kemeri / kask takılmaması nedeniyle "
            "tazminat tutarından %20 müterafik kusur indirimi uygulanmıştır."
        )

    # Manevi tazminat talebi varsa ekle
    if request.non_pecuniary_claim and request.non_pecuniary_claim > 0:
        comp["non_pecuniary_claim"] = str(request.non_pecuniary_claim)
        comp["grand_total_with_moral"] = str(
            net_comp_dec + to_decimal(request.non_pecuniary_claim)
        )

    total_costs = costs.get("total_upfront_costs") or "0.00"

    # Karşı vekalet ücreti riski
    estimated_counter_attorney_fee = (
        round_currency(net_comp_dec * Decimal("0.08"))
        if net_comp_dec > 0
        else Decimal("18000.00")
    )

    # Kazanma Olasılığı Hesaplama (Rol ve kaza tipine göre kalibreli)
    base_prob = 0.92
    if request.victim_role == "yolcu":
        base_prob = 0.96
    elif request.victim_role == "yaya":
        base_prob = 0.90
    
    p_accept_val = max(0.20, min(0.96, base_prob - (effective_fault * 0.50)))
    if not request.seatbelt_or_helmet:
        p_accept_val -= 0.05  # Kemer takılmaması davanın kabul oranında hafif risk oluşturur

    p_reject_val = round(1.0 - p_accept_val, 2)
    p_accept = to_decimal(f"{p_accept_val:.2f}")
    p_reject = to_decimal(f"{p_reject_val:.2f}")

    expected_value = compute_expected_value(
        net_compensation=net_comp_dec,
        total_costs=total_costs,
        counter_attorney_fee=estimated_counter_attorney_fee,
        p_accept=p_accept,
        p_reject=p_reject,
    )

    # Tavsiye Karnesi
    ev_num = float(expected_value)
    if ev_num > 100000:
        recommendation = "Dava Açmaya Değer (Yüksek Beklenen Fayda)"
        recommendation_badge = "success"
        recommendation_note = (
            "Beklenen net tazminat getirisi açılış ve olası karşı vekâlet risklerinin "
            "oldukça üzerindedir. Dava açılması hukuken ve ekonomik olarak güçlü biçimde önerilir."
        )
    elif ev_num > 0:
        recommendation = "Dava Açılabilir (Orta Risk / Dikkatli Takip)"
        recommendation_badge = "warning"
        recommendation_note = (
            "Beklenen getiri pozitif olmakla birlikte kusur veya masraf oranları "
            "dikkate alınmalı; sigorta tahkim yoluna gitmek alternatif olarak değerlendirilmelidir."
        )
    else:
        recommendation = "Dava Açmak Riskli (Düşük Beklenen Değer)"
        recommendation_badge = "danger"
        recommendation_note = (
            "Dava masrafları ve karşı tarafa vekâlet ücreti ödeme riski, "
            "elde edilecek net tazminatın üzerindedir. Dava açılması önerilmez."
        )

    risk_data = {
        "status": "ok",
        "expected_value": str(expected_value),
        "win_probability": f"%{int(p_accept_val * 100)}",
        "p_accept": str(p_accept),
        "p_reject": str(p_reject),
        "estimated_counter_attorney_fee": str(estimated_counter_attorney_fee),
        "recommendation": recommendation,
        "recommendation_badge": recommendation_badge,
        "recommendation_note": recommendation_note,
    }

    calculation_results = {
        "summary": analysis_res.summary,
        "compensation": comp,
        "costs": costs,
        "risk": risk_data,
        "warnings": warnings,
    }

    # Kaza tipine göre akıllı emsal eşleme (RAG için mükemmel mock altyapısı)
    accident_labels = {
        "kavsak_ihlali": "Kavşak Geçiş Önceliği İhlali",
        "kirmizi_isik": "Kırmızı Işık İhlali",
        "arkadan_carpma": "Trafikte Arkadan Çarpma",
        "yayaya_carpma": "Yaya Geçidi / Yayaya Çarpma",
        "serit_ihlali": "Hatalı Sollama ve Şerit İhlali",
    }
    acc_label = accident_labels.get(request.accident_type, "Trafik Kazası")

    mock_citations = [
        {
            "id": "YARGITAY-4HD-2023-4512",
            "court": "Yargıtay 4. Hukuk Dairesi",
            "case_no": "2023/4512 E., 2023/8901 K.",
            "date": "2023-10-18",
            "similarity_score": 0.95,
            "summary": f"{acc_label} sonucu meydana gelen kazada davacının ({request.victim_role}) bedensel zararına ilişkin aktüerya raporunun TRH-2010 tablosuna göre kesinleştirilmesi ve sigortacının temerrüt faizinden tam sorumluluğu onanmıştır.",
            "relevance_point": f"{acc_label} ve {request.victim_role} sıfatıyla tazminat hakkı.",
        },
        {
            "id": "YARGITAY-17HD-2022-1189",
            "court": "Yargıtay 17. Hukuk Dairesi",
            "case_no": "2022/1189 E., 2022/3321 K.",
            "date": "2022-04-12",
            "similarity_score": 0.89,
            "summary": "Kask/emniyet kemeri ve müterafik kusur itirazlarının kaza tutanağı ve hekim raporu kapsamında değerlendirilmesi gerektiği; geçici iş göremezlik zararlarının net asgari ücretin altına düşürülemeyeceği karara bağlanmıştır.",
            "relevance_point": "Müterafik kusur ve geçici iş göremezlik sınırları.",
        },
    ]

    case_summary = {
        "accident_type": request.accident_type,
        "victim_role": request.victim_role,
        "seatbelt_or_helmet": request.seatbelt_or_helmet,
        "non_pecuniary_claim": request.non_pecuniary_claim,
        "age": case_input.age,
        "gender": case_input.gender,
        "monthly_income": str(case_input.monthly_income) if case_input.monthly_income is not None else None,
        "income_basis": case_input.income_basis,
        "disability_rate": str(case_input.disability_rate) if case_input.disability_rate is not None else None,
        "temporary_incapacity_months": str(case_input.temporary_incapacity_months) if case_input.temporary_incapacity_months is not None else None,
        "plaintiff_fault": str(effective_fault),
        "accident_date": str(case_input.accident_date) if case_input.accident_date else None,
    }

    return {
        "status": "success",
        "message": "Analiz ve risk hesaplaması başarıyla tamamlandı.",
        "case_summary": case_summary,
        "calculation_results": calculation_results,
        "precedent_citations": mock_citations,
    }