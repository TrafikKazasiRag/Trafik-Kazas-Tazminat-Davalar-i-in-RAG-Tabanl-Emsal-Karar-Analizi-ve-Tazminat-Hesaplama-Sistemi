"""Atıf denetimi: parça var mı, konu uyuyor mu, alıntı parçada geçiyor mu, rakamlar alıntıda geçiyor mu."""
import re

from trafikrag.domain.decision import Chunk
from trafikrag.retrieval.topics import TOPICS

NUMBER = re.compile(r"\d[\d.,]*\d|\d")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _numbers(text: str) -> set[str]:
    return {m.group().rstrip(".,") for m in NUMBER.finditer(text)}


def check_statements(
    statements: list[dict],
    chunks: dict[str, Chunk],
    case_type: str | None = None,
) -> tuple[list[dict], list[str]]:
    """Denetimden geçen ifadeleri ve uyarıları döner. Geçmeyen ifade atılır.

    case_type verilirse, atıf yapılan parçanın `topics` listesi bu dava türünü içermelidir.
    """
    if case_type is not None and case_type not in TOPICS:
        raise ValueError(f"bilinmeyen case_type: {case_type!r}; geçerli değerler: {TOPICS}")
    valid: list[dict] = []
    warnings: list[str] = []
    for index, statement in enumerate(statements, start=1):
        chunk = chunks.get(statement.get("chunk_id", ""))
        quote = statement.get("quote", "")
        text = statement.get("text", "")
        if chunk is None:
            warnings.append(f"ifade {index}: atıf yapılan parça verilen parçalar arasında yok")
        elif case_type and not (chunk.metadata.get("topics") or []):
            warnings.append(f"ifade {index}: parçada konu etiketi yok (yeniden indeksleme gerekebilir)")
        elif case_type and case_type not in chunk.metadata["topics"]:
            warnings.append(f"ifade {index}: konu uyumsuz, parça farklı dava türüne ait")
        elif not quote or _norm(quote) not in _norm(chunk.text):
            warnings.append(f"ifade {index}: alıntı parçada bulunamadı")
        elif not _numbers(text) <= _numbers(quote):
            warnings.append(f"ifade {index}: rakam alıntıda geçmiyor")
        else:
            valid.append(statement)
    return valid, warnings