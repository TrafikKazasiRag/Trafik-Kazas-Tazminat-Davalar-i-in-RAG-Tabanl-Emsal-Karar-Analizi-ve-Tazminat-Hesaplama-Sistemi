"""Config'deki adım listesini sırayla çalıştırır ve kalite kontrol özet raporu üretir.

Kullanım:
    python -m trafikrag.ingestion.runner --config configs/default.yaml
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from trafikrag.domain.decision import Decision
from trafikrag.ingestion.steps.clean import run_clean_dir
from trafikrag.ingestion.steps.dedupe import dedupe_files
from trafikrag.ingestion.steps.index import write_decisions_jsonl
from trafikrag.ingestion.steps.split import has_complete_sections, split_decisions_dir
from trafikrag.ingestion.steps.topic_filter import detect_outcome, run_topic_filter
from trafikrag.retrieval.topics import classify_topic

# anonymize adımı listeden tamamen çıkarıldı
DEFAULT_STEPS = ["clean", "dedupe", "topic_filter", "split", "index"]


@dataclass
class PipelineReport:
    """Bölüm 6: Veri hattı kalite kontrol ve özet raporu."""

    total_raw: int = 0
    eliminated_by_step: dict[str, int] = field(default_factory=dict)
    final_count: int = 0
    complete_sections_count: int = 0
    complete_sections_ratio: float = 0.0
    incomplete_decision_ids: list[str] = field(default_factory=list)
    missing_metadata_ids: list[str] = field(default_factory=list)
    outcome_distribution: dict[str, int] = field(default_factory=dict)
    year_distribution: dict[str, int] = field(default_factory=dict)
    topic_distribution: dict[str, int] = field(default_factory=dict)


def load_config(config_path: Path) -> dict[str, Any]:
    """YAML yapılandırma dosyasını okur."""
    if not config_path.exists():
        return {}
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _count_txt(directory: Path) -> int:
    if not directory.exists():
        return 0
    return len(list(directory.glob("*.txt")))


def _build_report(
    total_raw: int,
    eliminated_by_step: dict[str, int],
    decisions: list[Decision],
    text_dir: Path,
) -> PipelineReport:
    """Üretilen Decision nesneleri üzerinden Bölüm 6 kalite kontrol istatistiklerini hesaplar."""
    final_count = len(decisions)
    complete_count = 0
    incomplete_ids: list[str] = []
    missing_meta_ids: list[str] = []
    outcomes: Counter[str] = Counter()
    years: Counter[str] = Counter()
    topics: Counter[str] = Counter()

    for dec in decisions:
        if has_complete_sections(dec):
            complete_count += 1
        else:
            incomplete_ids.append(dec.id)

        if not (dec.court and dec.esas_no and dec.karar_no and dec.date):
            missing_meta_ids.append(dec.id)

        if dec.date and len(dec.date) >= 4 and dec.date[:4].isdigit():
            years[dec.date[:4]] += 1
        else:
            years["belirsiz"] += 1

        # Konu sınıflandırması hesabı (Issue #32)
        topic = classify_topic(dec)
        topics[topic] += 1

        txt_file = text_dir / f"{dec.id}.txt"
        full_text = (
            txt_file.read_text(encoding="utf-8")
            if txt_file.exists()
            else "\n".join(s.text for s in dec.sections)
        )
        outcomes[detect_outcome(full_text)] += 1

    ratio = round(complete_count / final_count, 4) if final_count > 0 else 0.0

    return PipelineReport(
        total_raw=total_raw,
        eliminated_by_step=eliminated_by_step,
        final_count=final_count,
        complete_sections_count=complete_count,
        complete_sections_ratio=ratio,
        incomplete_decision_ids=incomplete_ids,
        missing_metadata_ids=missing_meta_ids,
        outcome_distribution=dict(outcomes),
        year_distribution=dict(sorted(years.items())),
        topic_distribution=dict(topics),
    )


def format_report_summary(report: PipelineReport) -> str:
    """Toplu kontrol raporunu konsolda okunabilir bir özet metne çevirir."""
    lines = [
        "=== VERİ HATTI KALİTE KONTROL RAPORU ===",
        f"Toplam ham karar sayısı     : {report.total_raw}",
        f"Adımlarda elenen sayılar    : {report.eliminated_by_step}",
        f"Nihai kabul edilen karar    : {report.final_count}",
        f"Bölümleri tam olan oranı    : {report.complete_sections_count}/{report.final_count} ({report.complete_sections_ratio:.1%})",
        f"Sonuç dağılımı              : {report.outcome_distribution}",
        f"Konu dağılımı (topics)      : {report.topic_distribution}",
        f"Karar yılı dağılımı         : {report.year_distribution}",
    ]
    if report.incomplete_decision_ids:
        lines.append(f"Eksik bölümlü kararlar      : {report.incomplete_decision_ids}")
    if report.missing_metadata_ids:
        lines.append(f"Eksik künyeli kararlar      : {report.missing_metadata_ids}")
    return "\n".join(lines)


def run_pipeline(config: dict[str, Any]) -> PipelineReport:
    """Yapılandırmadaki ingestion.steps adımlarını sırayla ve idempotent biçimde çalıştırır."""
    ing_cfg = config.get("ingestion", {}) if isinstance(config, dict) else {}
    steps: list[str] = ing_cfg.get("steps", DEFAULT_STEPS)
    raw_dir = Path(ing_cfg.get("raw_dir", "data/raw"))
    interim_dir = Path(ing_cfg.get("interim_dir", "data/interim"))

    interim_dir.mkdir(parents=True, exist_ok=True)
    work_dir = interim_dir / "work"
    work_dir.mkdir(parents=True, exist_ok=True)

    total_raw = _count_txt(raw_dir)
    current_dir = raw_dir
    current_count = total_raw
    eliminated_by_step: dict[str, int] = {}
    decisions: list[Decision] = []

    for step in steps:
        if step == "fetch":
            from trafikrag.ingestion.steps.fetch import run_fetch_step

            run_fetch_step(raw_dir=raw_dir, config=ing_cfg)
            total_raw = _count_txt(raw_dir)
            current_count = total_raw

        elif step == "clean":
            out_dir = work_dir / "01_cleaned"
            run_clean_dir(current_dir, out_dir)
            new_count = _count_txt(out_dir)
            eliminated_by_step["clean"] = max(0, current_count - new_count)
            current_dir = out_dir
            current_count = new_count

        elif step == "dedupe":
            out_dir = work_dir / "02_deduped"
            dedupe_files(current_dir, out_dir)
            new_count = _count_txt(out_dir)
            eliminated_by_step["dedupe"] = max(0, current_count - new_count)
            current_dir = out_dir
            current_count = new_count

        elif step == "topic_filter":
            out_dir = work_dir / "03_filtered"
            rejected_dir = work_dir / "03_rejected_olumlu"
            log_path = interim_dir / "selection_log.csv"
            run_topic_filter(current_dir, out_dir, rejected_dir=rejected_dir, log_path=log_path)
            new_count = _count_txt(out_dir)
            eliminated_by_step["topic_filter"] = max(0, current_count - new_count)
            current_dir = out_dir
            current_count = new_count

        elif step == "split":
            decisions = split_decisions_dir(current_dir, raw_dir=raw_dir)

        elif step == "index":
            if not decisions and current_dir.exists():
                decisions = split_decisions_dir(current_dir, raw_dir=raw_dir)
            output_jsonl = interim_dir / "decisions.jsonl"
            write_decisions_jsonl(decisions, output_jsonl)

        else:
            raise ValueError(f"Bilinmeyen veri hattı adımı: {step}")

    report = _build_report(total_raw, eliminated_by_step, decisions, current_dir)
    report_path = interim_dir / "ingestion_report.json"
    report_path.write_text(
        json.dumps(asdict(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TrafikRAG veri hazırlama hattını çalıştırır.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/default.yaml"),
        help="YAML yapılandırma dosyası yolu (varsayılan: configs/default.yaml)",
    )
    args = parser.parse_args(argv)

    config = load_config(args.config)
    report = run_pipeline(config)
    print(format_report_summary(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())