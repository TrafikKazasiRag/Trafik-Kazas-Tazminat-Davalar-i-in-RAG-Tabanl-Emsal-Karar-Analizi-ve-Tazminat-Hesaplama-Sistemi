"""Atıf denetimi: parça var mı, alıntı parçada geçiyor mu, rakamlar alıntıda geçiyor mu."""
import re

from trafikrag.domain.decision import Chunk

NUMBER = re.compile(r"\d[\d.,]*\d|\d")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _numbers(text: str) -> set[str]:
    return {m.group().rstrip(".,") for m in NUMBER.finditer(text)}


def check_statements(statements: list[dict], chunks: dict[str, Chunk]) -> tuple[list[dict], list[str]]:
    """Denetimden geçen ifadeleri ve uyarıları döner. Geçmeyen ifade atılır."""
    valid: list[dict] = []
    warnings: list[str] = []
    for index, statement in enumerate(statements, start=1):
        chunk = chunks.get(statement.get("chunk_id", ""))
        quote = statement.get("quote", "")
        text = statement.get("text", "")
        if chunk is None:
            warnings.append(f"ifade {index}: atıf yapılan parça verilen parçalar arasında yok")
        elif not quote or _norm(quote) not in _norm(chunk.text):
            warnings.append(f"ifade {index}: alıntı parçada bulunamadı")
        elif not _numbers(text) <= _numbers(quote):
            warnings.append(f"ifade {index}: rakam alıntıda geçmiyor")
        else:
            valid.append(statement)
    return valid, warnings