"""Chunker'ların ortak yardımcıları."""
from trafikrag.domain.decision import Decision

# Türkçe eklemeli bir dil: bir sözcük çoğu zaman 1'den fazla token tutar.
# 1.6 bir VARSAYIMDIR. Embedder'ı seçince gerçek tokenizer ile ölçüp güncelleyeceğiz.
TOKENS_PER_WORD = 1.6


def tokens_to_words(tokens: int) -> int:
    return max(1, int(tokens / TOKENS_PER_WORD))


def base_metadata(decision: Decision) -> dict:
    """Her chunk'a eklenen künye. Sonra filtreleme ve atıf için kullanılacak."""
    return {
        "court": decision.court,
        "esas_no": decision.esas_no,
        "karar_no": decision.karar_no,
        "date": decision.date,
    }
