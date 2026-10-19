"""1. Adım (clean): Ham karar metinlerindeki site gürültüsünü temizler ve metni normalleştirir.

Kurallar:
- Site reklamları, menüler, telif uyarıları, editoryal özetler ve site yorumları silinir.
- Unicode NFC normalleştirmesi yapılır, zero-width karakterler (\u200b) silinir,
  bölünemez boşluklar (\u00a0) normal boşluğa çevrilir.
- Başlıklar (I. DAVA, II. CEVAP, IV. GEREKÇE, C. Gerekçe, V. KARAR, VI. KARAR, SONUÇ :) 
  ve künye bilgileri KESİNLİKLE aynı satırda ve yazımla korunur, satırlar birleştirilmez.
- Adım idempotent'tir.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

# Görünmez sıfır genişlikli karakterler silinir (\u200b), \u00a0 ise normal boşluğa çevrilir.
_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff\u00ad]")

# Satır içi birden fazla boşluk veya sekme (tab)
_MULTI_SPACE_RE = re.compile(r"[ \t]+")

# 3 veya daha fazla ardışık satır sonunu en fazla 2 satır sonuna indirmek için
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")

# Sayfa numarası gürültüsü (tek başına duran küçük sayılar veya "Sayfa 1 / 3" kalıpları)
_PAGE_NUMBER_LINE_RE = re.compile(
    r"^(?:sayfa\s*\d+(?:\s*/\s*\d+)?|-\s*\d+\s*-|\d+\s*/\s*\d+|\d+)$",
    re.IGNORECASE,
)

# Breadcrumb / navigasyon satırları
_BREADCRUMB_LINE_RE = re.compile(r"^(?:ana\s*sayfa|anasayfa|home)\s*[>/»|].*$", re.IGNORECASE)

# Madde 19: Gürültü kalıpları tek bir modüler listede toplanmıştır (NOISE_PATTERNS)
NOISE_PATTERNS: list[re.Pattern[str]] = [
    # Tıklama ve reklam çağrıları
    re.compile(r"\btıklayınız\b", re.IGNORECASE),
    re.compile(r"\btiklayiniz\b", re.IGNORECASE),
    re.compile(r"^reklam\s*:?$", re.IGNORECASE),
    re.compile(r"^ilgili\s+kararlar\s*:?$", re.IGNORECASE),
    re.compile(r"^benzer\s+kararlar\s*:?$", re.IGNORECASE),
    re.compile(r"^etiketler\s*:", re.IGNORECASE),
    re.compile(r"^paylaş\s*:", re.IGNORECASE),
    re.compile(r"^yazdır$", re.IGNORECASE),
    re.compile(r"^https?://\S+$", re.IGNORECASE),
    
    # Minval Hukuk ve benzeri site gürültüleri
    re.compile(r"\bminval\s+hukuk\b", re.IGNORECASE),
    re.compile(r"kararın\s+özeti\s*;", re.IGNORECASE),
    re.compile(r"\bankara\s+avukat\b", re.IGNORECASE),
    re.compile(r"\bistanbul\s+avukat\b", re.IGNORECASE),
    re.compile(r"\bizmir\s+avukat\b", re.IGNORECASE),

    # Kanunyolu ve editoryal bloklar
    re.compile(r"karar\s+özeti\s+ve\s+hukuki\s+bağlam", re.IGNORECASE),
    re.compile(r"\bkanun\s*yolu\.com\b", re.IGNORECASE),
    re.compile(r"\byargitaykararlari\.com\b", re.IGNORECASE),

    # Karamercan Hukuk ve telif/not blokları
    re.compile(r"\bkaramercan\s+hukuk\b", re.IGNORECASE),
    re.compile(r"kaynak\s+gösterilmeden\s+kopyalana?maz", re.IGNORECASE),
    re.compile(r"kaynak\s+gösterilmeden\s+kullanılamaz", re.IGNORECASE),
    re.compile(r"tüm\s+hakları\s+saklıdır", re.IGNORECASE),
    re.compile(r"bu\s+karar\s+.*tarafından\s+derlenmiştir", re.IGNORECASE),
    re.compile(r"^b\s*İ\s*l\s*g\s*İ\s*:", re.IGNORECASE),
    re.compile(r"^bilgi\s*:", re.IGNORECASE),
]

# Korunması zorunlu bölüm başlıkları (Madde 2: I. DAVA, II. CEVAP, IV. GEREKÇE, C. Gerekçe, V. KARAR, VI. KARAR, SONUÇ :)
_PROTECTED_HEADING_RE = re.compile(
    r"^(?:[IVX]+\.\s+.{2,60}|[A-ZÇĞİÖŞÜ]\.\s+.{2,60}|SONUÇ\s*:.*)$"
)


def _is_noise_line(line: str) -> bool:
    """Satırın gürültü olup olmadığını kontrol eder."""
    if not line:
        return False
    if _PROTECTED_HEADING_RE.match(line):
        return False
    if _PAGE_NUMBER_LINE_RE.match(line):
        return True
    if _BREADCRUMB_LINE_RE.match(line):
        return True
    for pattern in NOISE_PATTERNS:
        if pattern.search(line):
            return True
    return False


def clean_text(text: str) -> str:
    """Ham karar metnini temizler, başlıkları ve satır yapısını korur, idempotency sağlar."""
    if not text:
        return ""

    # 1. Unicode NFC normalleştirmesi ve görünmez/bölünemez karakter dönüşümleri (Madde 8)
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\u00a0", " ")  # Non-breaking space -> normal boşluk
    normalized = _ZERO_WIDTH_RE.sub("", normalized)  # Zero-width silinir

    # 2. Satır satır işleme (Madde 3 & 4: satırlar birleştirilmez, kendi satırında kalır)
    cleaned_lines: list[str] = []
    for raw_line in normalized.split("\n"):
        line = _MULTI_SPACE_RE.sub(" ", raw_line).strip()

        if _is_noise_line(line):
            continue

        cleaned_lines.append(line)

    result = "\n".join(cleaned_lines)
    result = _MULTI_NEWLINE_RE.sub("\n\n", result).strip()

    return result + "\n" if result else ""


def clean_file(input_path: Path, output_path: Path) -> Path:
    """Tek bir dosyayı temizleyip hedef yola yazar (Madde 14 & 15: Ham dosya değişmez)."""
    raw_text = input_path.read_text(encoding="utf-8")
    cleaned = clean_text(raw_text)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(cleaned, encoding="utf-8", newline="\n")
    return output_path


def run_clean_dir(input_dir: Path, output_dir: Path) -> list[Path]:
    """data/raw/ klasöründen okuyup data/interim/ klasörüne yazar (Madde 15)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for src in sorted(input_dir.glob("karar_*.txt")):
        dst = output_dir / src.name
        written.append(clean_file(src, dst))
    return written