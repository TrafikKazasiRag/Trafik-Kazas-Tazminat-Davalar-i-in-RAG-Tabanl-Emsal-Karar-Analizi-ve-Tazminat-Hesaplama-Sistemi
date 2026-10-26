"""Versiyonlu parametre okuyucu (yaşam tablosu, asgari ücret, AAÜT) ve Decimal yardımcıları."""
from __future__ import annotations

import csv
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

import yaml

from trafikrag.domain.analysis import CaseInput

KURUS = Decimal("0.01")
FACTOR_PRECISION = Decimal("0.000001")

DEFAULT_PARAMS_PATH = (
    Path(__file__).resolve().parents[3] / "configs" / "parameters" / "trafik_2026.yaml"
)
DEFAULT_TABLES_DIR = DEFAULT_PARAMS_PATH.parent


def to_decimal(value: Decimal | float | str) -> Decimal:
    """Sayısal değeri float hassasiyet kaybı olmadan Decimal'e dönüştürür."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise TypeError("Boolean değer Decimal'e dönüştürülemez")
    return Decimal(str(value))


def round_currency(amount: Decimal | int | str) -> Decimal:
    """Tek noktada kuruş yuvarlaması (ROUND_HALF_UP)."""
    dec = to_decimal(amount)
    return dec.quantize(KURUS, rounding=ROUND_HALF_UP)


def _convert_numbers_to_decimal(obj: Any) -> Any:
    """YAML içindeki tüm float/int sayısal değerleri özyinelemeli olarak Decimal yapar."""
    if isinstance(obj, dict):
        return {k: _convert_numbers_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_numbers_to_decimal(v) for v in obj]
    if isinstance(obj, bool) or obj is None:
        return obj
    if isinstance(obj, (int, float)):
        return Decimal(str(obj))
    return obj


def load_parameters(path: str | Path | None = None) -> dict[str, Any]:
    """YAML parametre dosyasını okur ve tüm sayıları Decimal olarak döndürür."""
    target = Path(path) if path is not None else DEFAULT_PARAMS_PATH
    with open(target, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    params = _convert_numbers_to_decimal(raw)
    params["_base_dir"] = str(target.parent)
    return params


def get_parameter_version(params: dict[str, Any]) -> str:
    """Parametre sözlüğündeki sürüm numarasını döndürür."""
    return str(params.get("version", "bilinmiyor"))


def is_param_verified(params: dict[str, Any], key_path: str) -> bool:
    """Verilen parametre anahtarının doğrulanmış (verified: true) olup olmadığını döner."""
    verification = params.get("verification", {})
    meta = verification.get(key_path)
    if isinstance(meta, dict):
        return bool(meta.get("verified", False))
    return False


def get_param_warnings(params: dict[str, Any], used_keys: list[str] | set[str]) -> list[str]:
    """Kullanılan parametrelerden verified=false olanlar için standart uyarı listesi üretir."""
    warnings: list[str] = []
    verification = params.get("verification", {})
    for key in sorted(set(used_keys)):
        meta = verification.get(key)
        if isinstance(meta, dict) and not meta.get("verified", False):
            source = meta.get("source", "kaynak belirtilmedi")
            warnings.append(f"parametre {key} teyit edilmemiştir ({source})")
        elif meta is None:
            warnings.append(f"parametre {key} teyit edilmemiştir")
    return warnings


def resolve_monthly_net_income(
    case: CaseInput, params: dict[str, Any]
) -> tuple[Decimal, Decimal, list[str], list[str]]:
    """Aktif ve pasif dönem aylık net geliri (Decimal), uyarıları ve kullanılan parametre anahtarlarını döner."""
    warnings: list[str] = []
    used_keys: list[str] = []

    asgari_cfg = params["asgari_ucret"]
    net_asgari = to_decimal(asgari_cfg["net"])
    brut_asgari = to_decimal(asgari_cfg["brut"])
    pasif_asgari = to_decimal(asgari_cfg.get("pasif_net", net_asgari))

    if (
        case.monthly_income is None
        or case.income_basis in ("asgari", "bilinmiyor")
        or case.employment_status in ("calismiyor", "emekli")
        and case.monthly_income is None
    ):
        used_keys.append("asgari_ucret.net")
        active_income = net_asgari
    else:
        raw_income = to_decimal(case.monthly_income)
        if case.income_basis == "brut":
            used_keys.extend(["asgari_ucret.net", "asgari_ucret.brut"])
            net_ratio = net_asgari / brut_asgari
            active_income = round_currency(raw_income * net_ratio)
            warnings.append(
                "Brüt gelir, asgari ücret net/brüt oranı kullanılarak tahmini net gelire dönüştürüldü"
            )
        else:
            active_income = round_currency(raw_income)

        if active_income < net_asgari:
            used_keys.append("asgari_ucret.net")
            warnings.append(
                "Girilen aylık net gelir asgari ücretin altında olduğundan net asgari ücrete tamamlandı"
            )
            active_income = net_asgari

    used_keys.append("asgari_ucret.pasif_net" if "pasif_net" in asgari_cfg else "asgari_ucret.net")
    return active_income, pasif_asgari, warnings, used_keys


def load_life_table(
    table_name: str, gender: str = "E", tables_dir: str | Path | None = None
) -> dict[int, dict[str, Decimal]]:
    """TRH-2010 veya TRFH-2020 CSV yaşam tablosunu okur ve yaş -> {qx, ex} sözlüğü döner."""
    base_dir = Path(tables_dir) if tables_dir is not None else DEFAULT_TABLES_DIR
    normalized = table_name.upper().strip()
    if normalized == "TRFH-2020":
        csv_path = base_dir / "trfh_2020.csv"
    else:
        csv_path = base_dir / "trh_2010.csv"

    if not csv_path.exists():
        raise FileNotFoundError(f"Yaşam tablosu dosyası bulunamadı: {csv_path}")

    table: dict[int, dict[str, Decimal]] = {}
    is_female = gender == "K"

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(line for line in f if not line.strip().startswith("#"))
        for row in reader:
            age = int(row["age"])
            if "qx" in row:
                qx = to_decimal(row["qx"])
                ex = to_decimal(row.get("ex", "0"))
            elif normalized == "TRFH-2020":
                qx = to_decimal(row["qx_female"])
                ex = to_decimal(row.get("ex_female", "0"))
            else:
                qx = to_decimal(row["qx_female"] if is_female else row["qx_male"])
                ex = to_decimal(row["ex_female"] if is_female else row["ex_male"])
            table[age] = {"qx": qx, "ex": ex}

    return table


def compute_survival_probabilities(
    table: dict[int, dict[str, Decimal]], start_age: int
) -> list[Decimal]:
    """x yaşındaki kişinin k=0..omega-x yıl daha yaşama olasılıklarını (k_p_x) döner."""
    max_age = max(table.keys())
    if start_age > max_age:
        return [Decimal(1)]

    probs: list[Decimal] = [Decimal(1)]
    cumulative = Decimal(1)
    for age in range(start_age, max_age):
        qx = table[age]["qx"]
        px = Decimal(1) - qx
        cumulative = cumulative * px
        probs.append(cumulative)
    return probs


def compute_annuity_due(
    table: dict[int, dict[str, Decimal]],
    start_age: int,
    discount_rate: Decimal,
) -> Decimal:
    """Dönem başı ödemeli tam hayat anüitesi (ä_x = sum_{k=0}^{omega-x} v^k * k_p_x) hesaplar."""
    probs = compute_survival_probabilities(table, start_age)
    one_plus_i = Decimal(1) + to_decimal(discount_rate)
    v = Decimal(1) / one_plus_i

    total = Decimal(0)
    v_power = Decimal(1)
    for k_p_x in probs:
        total += v_power * k_p_x
        v_power *= v

    return total.quantize(FACTOR_PRECISION, rounding=ROUND_HALF_UP)


def compute_split_annuity_due(
    table: dict[int, dict[str, Decimal]],
    start_age: int,
    active_end_age: int,
    discount_rate: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    """Aktif dönem anüitesi, ertelenmiş pasif dönem anüitesi ve toplam ä_x katsayısını döner."""
    probs = compute_survival_probabilities(table, start_age)
    one_plus_i = Decimal(1) + to_decimal(discount_rate)
    v = Decimal(1) / one_plus_i

    active_years = max(0, int(active_end_age) - start_age)
    active_annuity = Decimal(0)
    passive_annuity = Decimal(0)

    v_power = Decimal(1)
    for k, k_p_x in enumerate(probs):
        term = v_power * k_p_x
        if k < active_years:
            active_annuity += term
        else:
            passive_annuity += term
        v_power *= v

    total_annuity = active_annuity + passive_annuity
    return (
        active_annuity.quantize(FACTOR_PRECISION, rounding=ROUND_HALF_UP),
        passive_annuity.quantize(FACTOR_PRECISION, rounding=ROUND_HALF_UP),
        total_annuity.quantize(FACTOR_PRECISION, rounding=ROUND_HALF_UP),
    )


def get_remaining_life_expectancy(
    table: dict[int, dict[str, Decimal]], age: int
) -> Decimal:
    """Tablodan x yaşı için bakiye ömür (e_x) yıl değerini döner."""
    max_age = max(table.keys())
    clamped_age = min(max(0, age), max_age)
    ex = table[clamped_age].get("ex", Decimal(0))
    if ex > Decimal(0):
        return ex
    probs = compute_survival_probabilities(table, clamped_age)
    computed = Decimal("0.5") + sum(probs[1:], Decimal(0))
    return computed.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
