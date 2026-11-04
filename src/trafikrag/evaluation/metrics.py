"""hit rate, MRR, nDCG.

Girdiler: `ranked` sıralı kimlik listesi (en iyi ilk), `relevant` ilgili kimlik kümesi.
"""
import math
from collections.abc import Collection, Sequence


def hit_rate(ranked: Sequence[str], relevant: Collection[str], k: int) -> float:
    return 1.0 if any(item in relevant for item in ranked[:k]) else 0.0


def reciprocal_rank(ranked: Sequence[str], relevant: Collection[str], k: int | None = None) -> float:
    for rank, item in enumerate(ranked[:k], start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


def ndcg(ranked: Sequence[str], relevant: Collection[str], k: int) -> float:
    """İkili ilgililik ile nDCG@k; tekrar eden kimlikler yalnızca ilk görüldüğünde sayılır."""
    seen: set[str] = set()
    dcg = 0.0
    for rank, item in enumerate(ranked[:k], start=1):
        if item in relevant and item not in seen:
            dcg += 1.0 / math.log2(rank + 1)
        seen.add(item)
    ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, min(len(set(relevant)), k) + 1))
    return dcg / ideal if ideal else 0.0


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0
