"""Karardan çıkarılan yapılandırılmış alanlar."""
from dataclasses import dataclass, field


@dataclass
class ExtractedFacts:
    decision_id: str
    plaintiff_fault: float | None = None   # davacı kusur oranı (0-1)
    defendant_fault: float | None = None
    disability_rate: float | None = None   # maluliyet oranı (0-1)
    injury_type: str | None = None
    awarded_items: dict[str, float] = field(default_factory=dict)  # kalem -> tutar
    outcome: str | None = None             # kabul | kismen_kabul | ret | bozma
    evidence: dict[str, str] = field(default_factory=dict)         # alan -> dayanak cümle
