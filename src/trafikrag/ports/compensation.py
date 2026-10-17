from typing import Protocol

from trafikrag.domain.analysis import CaseInput


class CompensationItem(Protocol):
    """Her tazminat kalemi bu arayüzü uygular (tedavi, iş göremezlik, bakıcı...)."""

    name: str

    def compute(self, case: CaseInput, params: dict) -> dict:
        """Dönüş: {"amount": Decimal, "formula": str, "inputs": dict}"""
        ...
