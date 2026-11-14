from datetime import date

from trafikrag.domain.analysis import CaseInput, validate_case
from trafikrag.domain.facts import ExtractedFacts


def test_empty_case_has_no_errors_but_warns():
    errors, warnings = validate_case(CaseInput())
    assert errors == []
    assert any("Kaza tarihi" in w for w in warnings)
    assert any("Gelir bilinmiyor" in w for w in warnings)


def test_complete_case_has_no_problems():
    case = CaseInput(
        age=35, gender="E", monthly_income=30000, income_basis="net",
        disability_rate=0.12, plaintiff_fault=0.3, accident_date=date(2023,5,1),
        calculation_date=date(2026,10,1),
    )
    assert validate_case(case) == ([], [])


def test_invalid_values_are_errors():
    errors, _ = validate_case(CaseInput(disability_rate=1.5, gender="X", method="rastgele"))
    assert len(errors) == 3


def test_accident_after_calculation_is_error():
    case = CaseInput(accident_date=date(2026, 1, 1), calculation_date=date(2025, 1, 1))
    errors, _ = validate_case(case)
    assert any("accident_date" in e for e in errors)


def test_negative_amount_is_error():
    errors, _ = validate_case(CaseInput(treatment_costs=-5))
    assert errors == ["treatment_costs negatif olamaz"]


def test_extracted_facts_new_fields_default_to_none():
    facts = ExtractedFacts(decision_id="k1")
    assert facts.accident_date is None and facts.life_table is None
    assert facts.awarded_items == {} and facts.evidence == {}