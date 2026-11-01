"""Tüm akışı birleştiren tek giriş noktası:
validate_case -> hesaplama -> filtreli retrieval -> sonuç istatistiği ve risk -> LLM değerlendirme -> check_statements + topic_guard -> AnalysisResult
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from trafikrag.calculation.engine import (
    CalculationEngine,
    _deduplicate_warnings,
    calculate,
)
from trafikrag.domain.analysis import AnalysisResult, CaseInput, validate_case
from trafikrag.domain.decision import Chunk, ScoredChunk
from trafikrag.domain.facts import ExtractedFacts
from trafikrag.generation.summarizer import summarize
from trafikrag.ports.embedder import Embedder
from trafikrag.ports.lexical_index import LexicalIndex
from trafikrag.ports.llm import LLM
from trafikrag.ports.reranker import Reranker
from trafikrag.ports.vector_store import VectorStore
from trafikrag.risk.outcome_stats import compute_expected_value, compute_outcome_stats

KAPSAM_DISI_UYARI = "Ölümlü kazalar (destekten yoksun kalma) bu sürümde kapsam dışıdır"


def _build_query_text(case: CaseInput) -> str:
    """Arama ve özetleme için CaseInput'tan sorgu metni üretir."""
    if case.narrative and case.narrative.strip():
        return case.narrative.strip()
    parts: list[str] = ["trafik kazası"]
    if case.case_type:
        parts.append(case.case_type)
    else:
        parts.append("yaralanma")
    if case.accident_type:
        parts.append(case.accident_type.replace("_", " "))
    if case.injury_type:
        parts.append(case.injury_type)
    if case.disability_rate is not None:
        parts.append("sürekli iş göremezlik maluliyet")
    return " ".join(parts)


def _chunk_matches_topic(chunk: Chunk, target_topic: str | None) -> bool:
    """Parçanın topics metadata alanının hedef dava türüyle uyumlu olup olmadığını denetler."""
    if not target_topic:
        return True
    topics = chunk.metadata.get("topics")
    if isinstance(topics, (list, tuple, set)):
        return target_topic in topics
    if isinstance(topics, str):
        return topics == target_topic
    return False


def _retrieve_filtered_chunks(
    query_text: str,
    target_topic: str,
    *,
    embedder: Embedder | None,
    vector_store: VectorStore | None,
    lexical_index: LexicalIndex | None,
    reranker: Reranker | None,
    pre_retrieved_chunks: list[ScoredChunk] | None,
    top_k: int,
    top_n: int,
) -> list[ScoredChunk]:
    """Hedef dava türüne (topic) göre filtrelenmiş emsal parçalarını getirir.
    Başka kümeden (örn. ölümlü veya hasar) parça karıştırmaz.
    """
    if pre_retrieved_chunks is not None:
        filtered = [
            sc for sc in pre_retrieved_chunks if _chunk_matches_topic(sc.chunk, target_topic)
        ]
        if reranker is not None:
            return reranker.rerank(query_text, filtered, top_n=top_n)
        return filtered[:top_n]

    merged: dict[str, ScoredChunk] = {}

    if vector_store is not None and embedder is not None:
        query_vector = embedder.embed([query_text])[0]
        vec_hits = vector_store.search(query_vector, top_k=top_k)
        for sc in vec_hits:
            if _chunk_matches_topic(sc.chunk, target_topic):
                merged[sc.chunk.id] = sc

    if lexical_index is not None:
        lex_hits = lexical_index.search(query_text, top_k=top_k)
        for sc in lex_hits:
            if _chunk_matches_topic(sc.chunk, target_topic) and sc.chunk.id not in merged:
                merged[sc.chunk.id] = sc

    candidates = list(merged.values())
    candidates.sort(key=lambda s: s.score, reverse=True)

    if reranker is not None and candidates:
        return reranker.rerank(query_text, candidates, top_n=top_n)
    return candidates[:top_n]


def _select_matched_facts(
    facts: list[ExtractedFacts] | dict[str, ExtractedFacts] | None,
    scored_chunks: list[ScoredChunk],
    has_retrieval_source: bool,
) -> list[ExtractedFacts]:
    """Yalnızca filtrelenmiş emsal kümesindeki kararlara ait ExtractedFacts nesnelerini seçer."""
    if facts is None:
        return []

    if isinstance(facts, dict):
        if has_retrieval_source:
            decision_ids = list(dict.fromkeys(sc.chunk.decision_id for sc in scored_chunks))
            return [facts[did] for did in decision_ids if did in facts]
        return list(facts.values())

    if has_retrieval_source:
        decision_ids_set = {sc.chunk.decision_id for sc in scored_chunks}
        return [f for f in facts if f.decision_id in decision_ids_set]
    return list(facts)


def _enrich_risk_with_expected_value(
    risk_res: dict[str, Any],
    compensation: dict[str, Any],
    costs: dict[str, Any],
) -> dict[str, Any]:
    """Risk durumu 'ok' ise hesaplanan net tazminat ve masraflarla beklenen değeri (Decimal) ekler."""
    if risk_res.get("status") != "ok":
        return risk_res
    probs = risk_res.get("probabilities") or {}
    net_total = compensation.get("net_total", Decimal("0.00"))
    upfront_costs = costs.get("total_upfront_costs", Decimal("0.00"))
    attorney_fee = costs.get("vekalet_ucreti") or Decimal("0.00")

    p_accept = (
        probs.get("kabul", {}).get("proportion", Decimal("0.0000"))
        + probs.get("kismen_kabul", {}).get("proportion", Decimal("0.0000"))
        + probs.get("istinaf_reddi", {}).get("proportion", Decimal("0.0000"))
    )
    p_reject = probs.get("ret", {}).get("proportion", Decimal("0.0000"))
    ev = compute_expected_value(
        net_compensation=net_total,
        total_costs=upfront_costs,
        counter_attorney_fee=attorney_fee,
        p_accept=p_accept,
        p_reject=p_reject,
    )
    risk_res["expected_value"] = ev
    return risk_res


def analyze(
    case: CaseInput,
    *,
    embedder: Embedder | None = None,
    vector_store: VectorStore | None = None,
    lexical_index: LexicalIndex | None = None,
    reranker: Reranker | None = None,
    llm: LLM | None = None,
    facts: list[ExtractedFacts] | dict[str, ExtractedFacts] | None = None,
    chunks: list[ScoredChunk] | None = None,
    engine: CalculationEngine | None = None,
    top_k: int = 30,
    top_n: int = 8,
) -> AnalysisResult:
    """Formdan sonuca tek giriş noktası.

    Akış:
    1. `case.case_type == "olum"` ise hesap ve arama yapmadan "kapsam dışı" döner.
    2. `validate_case(case)` ile girdi doğrulaması yapar; hata varsa durur.
    3. Hesaplama motorunu (`calculate`) emsalden tamamen bağımsız olarak çalıştırır (`Decimal`).
    4. Hedef konu (`case_type`, varsayılan `"yaralanma"`) filtresiyle retrieval yapar.
    5. Sonuç istatistiği ve risk (`compute_outcome_stats`) hesaplar; `yetersiz_emsal` durumunda
       başka kümeden doldurma yapmaz, hesaplama sonucu ve uyarıyla döner.
    6. LLM değerlendirmesi (`summarize` -> `check_statements` + `topic_guard`) çalıştırır.
    """
    errors, validation_warnings = validate_case(case)
    if errors:
        return AnalysisResult(
            summary="Girdi doğrulama hatası nedeniyle analiz yapılamadı.",
            citations=[],
            compensation={"label": "tahmini hesap", "errors": errors},
            costs={},
            risk={},
            warnings=list(validation_warnings),
        )

    if case.case_type == "olum":
        return AnalysisResult(
            summary="Ölümlü trafik kazaları (destekten yoksun kalma tazminatı) bu sürümde kapsam dışıdır.",
            citations=[],
            compensation={"status": "kapsam_disi"},
            costs={},
            risk={"status": "kapsam_disi"},
            warnings=_deduplicate_warnings([KAPSAM_DISI_UYARI, *validation_warnings]),
        )

    # 1. Hesaplama (emsalden bağımsız, tüm tutarlar Decimal)
    calc_result = engine.calculate(case) if engine is not None else calculate(case)
    all_warnings: list[str] = list(calc_result.warnings)

    # 2. Konu filtreli retrieval
    target_topic = case.case_type or "yaralanma"
    query_text = _build_query_text(case)
    has_retrieval_source = (
        (vector_store is not None and embedder is not None)
        or lexical_index is not None
        or chunks is not None
    )
    scored_chunks = _retrieve_filtered_chunks(
        query_text,
        target_topic,
        embedder=embedder,
        vector_store=vector_store,
        lexical_index=lexical_index,
        reranker=reranker,
        pre_retrieved_chunks=chunks,
        top_k=top_k,
        top_n=top_n,
    )

    # 3. Sonuç istatistiği ve risk (yetersiz_emsal ise başka kümeden doldurulmaz)
    matched_facts = _select_matched_facts(facts, scored_chunks, has_retrieval_source)
    risk_res = compute_outcome_stats(matched_facts)
    risk_res = _enrich_risk_with_expected_value(
        risk_res, calc_result.compensation, calc_result.costs
    )
    all_warnings.extend(risk_res.get("warnings", []))

    # 4. LLM değerlendirme + check_statements + topic_guard
    citations = []
    llm_summary = ""
    if llm is not None and scored_chunks:
        llm_summary, citations, gen_warnings = summarize(
            query_text,
            scored_chunks,
            llm,
            case_type=target_topic,
        )
        all_warnings.extend(gen_warnings)

    final_summary = (
        f"{calc_result.summary}\n\n{llm_summary}" if llm_summary else calc_result.summary
    )

    return AnalysisResult(
        summary=final_summary,
        citations=citations,
        compensation=calc_result.compensation,
        costs=calc_result.costs,
        risk=risk_res,
        warnings=_deduplicate_warnings(all_warnings),
    )
