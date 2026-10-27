"""index.py adımı için birim testler."""
import json
from pathlib import Path
from trafikrag.domain.decision import Decision, Section
from trafikrag.ingestion.steps.index import write_decisions_jsonl


def test_write_decisions_jsonl_creates_valid_file(tmp_path: Path) -> None:
    decisions = [
        Decision(
            id="karar_03",
            court="Yargıtay 4. Hukuk Dairesi",
            esas_no="2023/11230",
            karar_no="2023/13550",
            date="2023-12-14",
            source_url="https://ornek.com/1",
            sections=[Section(kind="olay", text="Olay metni"), Section(kind="hukum", text="Hüküm metni")],
        )
    ]
    out_file = tmp_path / "decisions.jsonl"
    result_path = write_decisions_jsonl(decisions, out_file)

    assert result_path.exists()
    lines = out_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    data = json.loads(lines[0])
    assert data["id"] == "karar_03"
    assert data["esas_no"] == "2023/11230"
    assert len(data["sections"]) == 2