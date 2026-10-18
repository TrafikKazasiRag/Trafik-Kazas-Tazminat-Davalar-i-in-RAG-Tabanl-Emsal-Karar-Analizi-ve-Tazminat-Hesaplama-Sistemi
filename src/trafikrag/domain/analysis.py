"""Analiz isteği ve sonucu."""
from dataclasses import dataclass, field


@dataclass
class CaseInput:
    narrative: str = ""
    age: int | None = None
    monthly_income: float | None = None
    disability_rate: float | None = None
    plaintiff_fault: float | None = None
    injury_type: str | None = None
    treatment_costs: float | None = None


@dataclass
class Citation:
    decision_id: str
    chunk_id: str
    quote: str


@dataclass
class AnalysisResult:
    summary: str
    citations: list[Citation] = field(default_factory=list)
    compensation: dict = field(default_factory=dict)
    costs: dict = field(default_factory=dict)
    risk: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
