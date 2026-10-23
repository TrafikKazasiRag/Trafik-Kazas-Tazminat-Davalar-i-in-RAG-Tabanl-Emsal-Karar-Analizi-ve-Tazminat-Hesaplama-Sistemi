import json

from trafikrag.extraction.extractor import extract_facts

KARAR = "Davacının kusuru %30, davalının kusuru %70 olarak belirlenmiştir. Bakıcı gideri 12.000,50 TL hesaplanmıştır."

class FakeLLM:
    def __init__(self, payload):
        self.payload = payload
    def complete(self, prompt, *, system=None, json_schema=None):
        return json.dumps(self.payload) if isinstance(self.payload, dict) else self.payload
def _payload(**kw):
    base = {
        "plaintiff_fault": 0.3, "defendant_fault": 0.7, "disability_rate": None,
        "injury_type": None, "awarded_items": {}, "outcome": None,
        "evidence": {
            "plaintiff_fault": "Davacının kusuru %30",
            "defendant_fault": "davalının kusuru %70",
        },
    }
    base.update(kw)
    return base
def test_valid_outuput_is_kept():
    facts, warnings = extract_facts("k1", KARAR, FakeLLM(_payload()))
    assert facts.plaintiff_fault == 0.3 and facts.defendant_fault == 0.7
    assert warnings == []
def test_invented_quote_drops_field():
    p = _payload()
    p["evidence"]["plaintiff_fault"] = "Davacı tamamen kusurludur"
    facts, warnings =extract_facts("k1", KARAR, FakeLLM(p))
    assert facts.plaintiff_fault is None
    assert any("bulunamadı" in w for w in warnings)
def test_fault_sum_must_be_one():
    p = _payload(plaintiff_fault=0.5)
    p["evidence"]["plaintiff_fault"] = "Davacının kusuru %30"
    facts, _ = extract_facts("k1", KARAR, FakeLLM(p))
    assert facts.plaintiff_fault is None and facts.defendant_fault is None
def test_amount_must_appear_in_quote():
    good = _payload(awarded_items={"bakici_gideri":12000.5})
    good["evidence"]["awarded_items.bakici_gideri"] = "Bakıcı gideri 12.000,50 TL hesaplanmıştır."
    facts, _ = extract_facts("k1", KARAR, FakeLLM(good))
    assert facts.awarded_items == {"bakici_gideri": 12000.5}

    bad = _payload(awarded_items={"bakici_gideri": 99999.0})
    bad["evidence"]["awarded_items.bakici_gideri"] = "Bakıcı gideri 12.000,50 TL hesaplanmıştır."
    facts, warnings = extract_facts("k1", KARAR, FakeLLM(bad))
    assert facts.awarded_items == {}
    assert any("tutar" in w for w in warnings)
def test_bad_json_returns_empty_facts():
    facts, warnings = extract_facts("k1", KARAR, FakeLLM("bu json değil"))
    assert facts.plaintiff_fault is None and warnings