"""Bir experiment config'iyle tüm değerlendirme setini çalıştırır.

Kullanım: python -m trafikrag.evaluation.run_eval configs/experiments/a_naive.yaml data/eval/questions.jsonl

Değerlendirme seti JSONL: her satır {"query": "...", "relevant_decision_ids": ["..."], "filters": {...}}
(`filters` opsiyonel). İlgililik karar düzeyinde ölçülür: aynı karardan gelen tekrarlar bir sayılır.
"""
import json
import sys
from pathlib import Path

from trafikrag.bootstrap import build_container
from trafikrag.evaluation.metrics import hit_rate, mean, ndcg, reciprocal_rank
from trafikrag.retrieval.retriever import Retriever, build_retriever

DEFAULT_K = 8


def load_questions(path: str | Path) -> list[dict]:
    questions = []
    with open(path, encoding="utf-8") as f:
        for number, line in enumerate(f, start=1):
            if not line.strip():
                continue
            item = json.loads(line)
            if not item.get("query") or not item.get("relevant_decision_ids"):
                raise ValueError(f"{path}:{number}: 'query' ve 'relevant_decision_ids' gerekli")
            questions.append(item)
    return questions


def _unique(ids: list[str]) -> list[str]:
    return list(dict.fromkeys(ids))


def evaluate(retriever: Retriever, questions: list[dict], k: int = DEFAULT_K) -> dict:
    hits, rrs, ndcgs = [], [], []
    for item in questions:
        results = retriever.retrieve(item["query"], item.get("filters"))
        ranked = _unique([r.chunk.decision_id for r in results])
        relevant = set(item["relevant_decision_ids"])
        hits.append(hit_rate(ranked, relevant, k))
        rrs.append(reciprocal_rank(ranked, relevant, k))
        ndcgs.append(ndcg(ranked, relevant, k))
    return {
        "questions": len(questions),
        "k": k,
        f"hit_rate@{k}": mean(hits),
        f"mrr@{k}": mean(rrs),
        f"ndcg@{k}": mean(ndcgs),
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    config_path, questions_path = argv
    container = build_container(config_path)
    k = container["config"].get("retrieval", {}).get("eval_k", DEFAULT_K)
    report = evaluate(build_retriever(container), load_questions(questions_path), k)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
