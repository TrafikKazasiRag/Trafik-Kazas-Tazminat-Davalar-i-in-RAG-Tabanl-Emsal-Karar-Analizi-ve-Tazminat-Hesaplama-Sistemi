"""Konu sınıflandırıcısını gerçek kararlar üzerinde dener.

Kullanım: python scripts/check_topics.py [örnek_sayısı]
"""
import random
import sys
from collections import Counter
from pathlib import Path

from trafikrag.ingestion.steps.parse_decision import load_decision
from trafikrag.retrieval.topics import classify_topic


def main() -> None:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    paths = sorted(Path("data/txt_dosyalar").glob("karar_*.txt"))
    decisions = [load_decision(path) for path in paths]
    topics = [classify_topic(decision) for decision in decisions]
    print(Counter(topics))

    random.seed(1)
    for index in random.sample(range(len(decisions)), count):
        decision = decisions[index]
        hukum = next((s.text for s in decision.sections if s.kind == "hukum"), "")
        print(f"\n{decision.id} -> {topics[index]}")
        print("  hüküm:", " ".join(hukum.split())[:300])


if __name__ == "__main__":
    main()