"""services/analyze.py uçtan uca entegrasyon ve birim testleri (FakeLLM ve FakeEmbedder ile)."""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from trafikrag.adapters.embedders.fake import FakeEmbedder
from trafikrag.adapters.llms.fake import FakeLLM
from trafikrag.adapters.rerankers.none import NoReranker
from trafikrag.adapters.vector_stores.memory import MemoryVectorStore
from trafikrag.calculation import calculate
from trafikrag.domain.analysis import CaseInput, validate_case
from trafikrag.domain.decision import Chunk
from trafikrag.domain.facts import ExtractedFacts
from trafikrag.services.analyze import analyze


def _sample_injury_case(**overrides) -> CaseInput:
    defaults = {
        "narrative": "Yaya geçidinde aracın çarpması sonucu davacı yaralanmış ve %10 malul kalmıştır.",
        "case_type": "yaralanma",
        "accident_type": "yaya_carpmasi",
        "age": 30,
        "gender": "E",
        "employment_status": "calisiyor",
        "monthly_income": 30000.0,
        "income_basis": "net",
        "disability_rate": 0.10,
        "temporary_incapacity_months": 2.0,
        "treatment_costs": 10000.0,
        "plaintiff_fault": 0.30,
        "fault_source": "rapor",
        "accident_date": date(2025, 1, 1),
        "calculation_date": date(2026, 1, 1),
        "policy_date": date(2024, 6, 1),
        "policy_limit": 3600000.0,
    }
    defaults.update(overrides)
    return CaseInput(**defaults)


def _build_corpus(
    embedder: FakeEmbedder,
    injury_count: int,
    other_topic_count: int = 0,
) -> tuple[MemoryVectorStore, dict[str, ExtractedFacts]]:
    store = MemoryVectorStore()
    chunks: list[Chunk] = []
    facts_map: dict[str, ExtractedFacts] = {}

    for i in range(1, injury_count + 1):
        did = f"k_yar_{i}"
        cid = f"c_yar_{i}"
        chunks.append(
            Chunk(
                id=cid,
                decision_id=did,
                section_kind="gerekce",
                text=(
                    f"Karar {i}: Kusur raporunda davalının %70, davacının %30 kusurlu olduğu "
                    "ve sürekli iş göremezlik tazminatının TRH-2010 tablosuna göre hesaplandığı belirtilmiştir."
                ),
                metadata={"topics": ["yaralanma"], "court": "Yargıtay 4. HD", "date": "2024-05-10"},
            )
        )
        facts_map[did] = ExtractedFacts(
            decision_id=did,
            outcome="kabul" if i % 3 != 0 else "kismen_kabul",
            plaintiff_fault=0.30,
            defendant_fault=0.70,
            disability_rate=0.10,
        )

    for j in range(1, other_topic_count + 1):
        did = f"k_olum_{j}"
        cid = f"c_olum_{j}"
        chunks.append(
            Chunk(
                id=cid,
                decision_id=did,
                section_kind="hukum",
                text=f"Ölümlü karar {j}: Destekten yoksun kalma tazminatının kabulüne karar verilmiştir.",
                metadata={"topics": ["olum"], "court": "Yargıtay 4. HD", "date": "2024-05-10"},
            )
        )
        facts_map[did] = ExtractedFacts(
            decision_id=did,
            outcome="kabul",
            plaintiff_fault=0.20,
            defendant_fault=0.80,
        )

    if chunks:
        vectors = embedder.embed([c.text for c in chunks])
        store.add(chunks, vectors)

    return store, facts_map


def test_calculate_entry_point_takes_case_input_and_returns_decimal():
    """Hesaplama giriş noktası CaseInput alır ve tüm parasal sonuçları Decimal döner."""
    case = _sample_injury_case()
    res = calculate(case)
    assert isinstance(res.compensation["gross_total"], Decimal)
    assert isinstance(res.compensation["net_total"], Decimal)
    assert res.compensation["net_total"] > Decimal("0.00")
    assert isinstance(res.costs["total_upfront_costs"], Decimal)
    assert isinstance(res.costs["total_judgment_costs"], Decimal)


def test_analyze_normal_flow_with_fake_llm_and_fake_embedder():
    """1. Yol (Normal): Geçerli yaralanma vakası, yeterli emsal (>= 10), FakeEmbedder + FakeLLM."""
    embedder = FakeEmbedder(dim=16)
    store, facts_map = _build_corpus(embedder, injury_count=12, other_topic_count=5)

    llm = FakeLLM(
        json.dumps(
            {
                "statements": [
                    {
                        "text": "Emsal kararda davalı %70, davacı %30 kusurlu bulunmuştur.",
                        "chunk_id": "c_yar_1",
                        "quote": "davalının %70, davacının %30 kusurlu olduğu",
                    }
                ]
            }
        )
    )

    case = _sample_injury_case()
    result = analyze(
        case,
        embedder=embedder,
        vector_store=store,
        reranker=NoReranker(),
        llm=llm,
        facts=facts_map,
        top_k=20,
        top_n=12,
    )

    # Hesaplama Decimal olarak döndü
    assert isinstance(result.compensation["net_total"], Decimal)
    assert result.compensation["net_total"] > Decimal("0.00")
    assert isinstance(result.costs["vekalet_ucreti"], Decimal)

    # Risk modülü yalnızca 12 yaralanma kararını saydı (5 ölümlü kararı karıştırmadı)
    assert result.risk["status"] == "ok"
    assert result.risk["sample_size"] == 12
    assert isinstance(result.risk["expected_value"], Decimal)

    # LLM değerlendirmesi + check_statements + topic_guard geçti ve atıf eklendi
    assert len(result.citations) == 1
    assert result.citations[0].decision_id == "k_yar_1"
    assert result.citations[0].chunk_id == "c_yar_1"
    assert "Emsal kararda davalı %70, davacı %30 kusurlu bulunmuştur. [1]" in result.summary


def test_analyze_out_of_scope_for_olum_skips_calculation_and_search():
    """2. Yol (Kapsam Dışı): case_type='olum' ise hesap veya arama yapmadan 'kapsam dışı' döner."""

    class ExplodingComponent:
        def __getattr__(self, name: str):
            def _boom(*args, **kwargs):
                raise AssertionError(f"Kapsam dışı vakada {name} çağrılmamalıydı!")

            return _boom

    case = CaseInput(
        narrative="Ölümlü trafik kazası nedeniyle destekten yoksun kalma talebi.",
        case_type="olum",
        age=42,
        gender="E",
        monthly_income=40000.0,
    )

    result = analyze(
        case,
        embedder=ExplodingComponent(),  # type: ignore[arg-type]
        vector_store=ExplodingComponent(),  # type: ignore[arg-type]
        lexical_index=ExplodingComponent(),  # type: ignore[arg-type]
        llm=ExplodingComponent(),  # type: ignore[arg-type]
        engine=ExplodingComponent(),  # type: ignore[arg-type]
    )

    assert "kapsam dışı" in result.summary.lower()
    assert result.compensation.get("status") == "kapsam_disi"
    assert result.risk.get("status") == "kapsam_disi"
    assert result.citations == []
    assert any("kapsam dışıdır" in w for w in result.warnings)


def test_analyze_insufficient_precedents_does_not_backfill_from_other_clusters():
    """3. Yol (Yetersiz Emsal): Hedef kümede ('yaralanma') yalnızca 3 karar varken başka kümede ('olum')
    15 karar olsa bile başka kümeden doldurma yapmaz; hesaplama sonucu ve uyarıyla döner.
    """
    embedder = FakeEmbedder(dim=16)
    store, facts_map = _build_corpus(embedder, injury_count=3, other_topic_count=15)

    llm = FakeLLM(
        json.dumps(
            {
                "statements": [
                    {
                        "text": "Davacı %30 kusurlu bulunmuştur.",
                        "chunk_id": "c_yar_1",
                        "quote": "davacının %30 kusurlu olduğu",
                    }
                ]
            }
        )
    )

    case = _sample_injury_case()
    result = analyze(
        case,
        embedder=embedder,
        vector_store=store,
        llm=llm,
        facts=facts_map,
        top_k=30,
        top_n=15,
    )

    # Risk modülü yetersiz_emsal verdi ve ölümlü kümeden (15 karar) doldurma yapmadı
    assert result.risk["status"] == "yetersiz_emsal"
    assert result.risk["sample_size"] == 3
    assert any("eşik değerin" in w.lower() or "yetersiz emsal" in w.lower() for w in result.warnings)

    # Hesaplama emsalden bağımsız olarak tam ve Decimal döndü
    standalone_calc = calculate(case)
    assert result.compensation["net_total"] == standalone_calc.compensation["net_total"]
    assert result.costs["total_judgment_costs"] == standalone_calc.costs["total_judgment_costs"]


def test_calculation_is_completely_independent_of_precedents():
    """Hesaplama emsalden bağımsız çalışır: hiç emsal/store/LLM verilmediğinde bile aynı Decimal sonucu üretir."""
    case = _sample_injury_case()
    res_no_rag = analyze(case)
    res_direct = calculate(case)

    assert isinstance(res_no_rag.compensation["net_total"], Decimal)
    assert res_no_rag.compensation == res_direct.compensation
    assert res_no_rag.costs == res_direct.costs
    assert res_no_rag.risk["status"] == "yetersiz_emsal"


def test_validate_case_new_form_fields():
    """CaseInput yeni form alanları (case_type, accident_type, fault_source) doğrulaması."""
    err_case = CaseInput(
        case_type="gecersiz_tur",
        accident_type="ucak_kazasi",
        fault_source="tahmin",
    )
    errors, _ = validate_case(err_case)
    assert any("case_type" in e for e in errors)
    assert any("accident_type" in e for e in errors)
    assert any("fault_source" in e for e in errors)

    olum_case = CaseInput(case_type="olum")
    errors_olum, warnings_olum = validate_case(olum_case)
    assert errors_olum == []
    assert any("kapsam dışıdır" in w for w in warnings_olum)
