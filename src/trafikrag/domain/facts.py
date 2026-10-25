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
    # --- hesap motorunu geriye dönük test etmek için kararda geçen girdiler ---
    accident_date: str | None = None       # ISO "YYYY-MM-DD"
    age_at_accident: int | None = None
    gender: str | None = None              # "E" | "K"
    monthly_income: float | None = None    # kararda kabul edilen aylık gelir (TL)
    temporary_incapacity_months: float | None = None
    caregiver_months: float | None = None
    life_table: str | None = None          # "TRH-2010" | "PMF-1931" | "TRFH-2020" | "diger"
    evidence: dict[str, str] = field(default_factory=dict)         # alan -> dayanak cümle