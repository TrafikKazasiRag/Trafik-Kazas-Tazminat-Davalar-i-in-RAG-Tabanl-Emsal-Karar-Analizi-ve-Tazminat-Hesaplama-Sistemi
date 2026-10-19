"""1. Adım (clean): Ham karar metinlerindeki site gürültüsünü temizler ve metni normalleştirir.

Kurallar:
- Site reklamları, menüler, telif uyarıları ve editoryal gürültü satırları silinir.
- Unicode NFC normalleştirmesi yapılır, görünmez karakterler ve fazla boşluklar temizlenir.
- Başlıklar (I. DAVA, IV. GEREKÇE, V. KARAR, SONUÇ :) ve künye bilgileri KESİNLİKLE korunur.
- Adım idempotent'tir: aynı girdi iki kez temizlendiğinde aynı çıktıyı üretir.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

# Görünmez sıfır genişlikli karakterler (zero-width space, BOM vb.)
_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff\u00ad]")

# Satır içi birden fazla boşluk veya sekme (tab)
_MULTI_SPACE_RE = re.compile(r"[ \t\u00a0]+")

# 3 veya daha fazla ardışık satır sonunu 2 satır sonuna (tek boş satır) indirmek için
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")

# Sayfa numarası gürültüsü (örn. "Sayfa 1 / 3", "- 2 -", "1/8")
_PAGE_NUMBER_LINE_RE = re.compile(
    r"^(?:sayfa\s*\d+(?:\s*/\s*\d+)?|-\s*\d+\s*-|\d+\s*/\s*\d+)$",
    re.IGNORECASE,
)

# Breadcrumb / navigasyon satırları (örn. "Anasayfa > Yargıtay Kararları > ...")
_BREADCRUMB_LINE_RE = re.compile(r"^(?:ana\s*sayfa|anasayfa|home)\s*[>/»|].*$", re.IGNORECASE)

# Derleme sitelerinden gelen bilinen reklam, tıklama çağrısı, telif ve site adı gürültüleri.
# DİKKAT: Gerçek mahkeme cümlelerini silmemek için bu kalıplar satır bazlı kontrol edilir.
_NOISE_LINE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\btıklayınız\b", re.IGNORECASE),
    re.compile(r"\btiklayiniz\b", re.IGNORECASE),
    re.compile(r"\bminval\s+hukuk\b", re.IGNORECASE),
    re.compile(r"\bkaramercan\s+hukuk\b", re.IGNORECASE),
    re.compile(r"\bkanun\s*yolu\.com\b", re.IGNORECASE),
    re.compile(r"\byargitaykararlari\.com\b", re.IGNORECASE),
    re.compile(r"\bsinir\s+hukuk\b", re.IGNORECASE),
    re.compile(r"\bankara\s+avukat\b", re.IGNORECASE),
    re.compile(r"\bistanbul\s+avukat\b", re.IGNORECASE),
    re.compile(r"\bizmir\s+avukat\b", re.IGNORECASE),
    re.compile(r"kaynak\s+gösterilmeden\s+kopyalana?maz", re.IGNORECASE),
    re.compile(r"kaynak\s+gösterilmeden\s+kullanılamaz", re.IGNORECASE),
    re.compile(r"tüm\s+hakları\s+saklıdır", re.IGNORECASE),
    re.compile(r"bu\s+karar\s+.*tarafından\s+derlenmiştir", re.IGNORECASE),
    re.compile(r"^reklam\s*:?$", re.IGNORECASE),
    re.compile(r"^ilgili\s+kararlar\s*:?$", re.IGNORECASE),
    re.compile(r"^benzer\s+kararlar\s*:?$", re.IGNORECASE),
    re.compile(r"^etiketler\s*:", re.IGNORECASE),
    re.compile(r"^paylaş\s*:", re.IGNORECASE),
    re.compile(r"^yazdır$", re.IGNORECASE),
    re.compile(r"^https?://\S+$", re.IGNORECASE),
]

# Korunması zorunlu bölüm başlıkları (hiçbir zaman gürültü sayılamaz)
_PROTECTED_HEADING_RE = re.compile(
    r"^(?:[IVX]+\.\s+.{2,60}|[A-ZÇĞİÖŞÜ]\.\s+.{2,60}|SONUÇ\s*:.*)$"
)


def _is_noise_line(line: str) -> bool:
    """Satırın derleme sitesi gürültüsü olup olmadığını kontrol eder."""
    if not line:
        return False
    if _PROTECTED_HEADING_RE.match(line):
        return False
    if _PAGE_NUMBER_LINE_RE.match(line):
        return True
    if _BREADCRUMB_LINE_RE.match(line):
        return True
    for pattern in _NOISE_LINE_PATTERNS:
        if pattern.search(line):
            return True
    return False


def clean_text(text: str) -> str:
    """Ham karar metnini temizler, Unicode NFC normalleştirmesi yapar ve başlıkları korur."""
    if not text:
        return ""

    # 1. Unicode NFC normalleştirmesi
    normalized = unicodedata.normalize("NFC", text)

    # 2. Satır sonlarını standartlaştır (\r\n ve \r -> \n) ve görünmez karakterleri sil
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _ZERO_WIDTH_RE.sub("", normalized)

    # 3. Satır satır temizlik
    cleaned_lines: list[str] = []
    for raw_line in normalized.split("\n"):
        # Satır içi çoklu boşlukları, tab'ları ve non-breaking space (\u00a0) karakterlerini tek boşluğa indir
        line = _MULTI_SPACE_RE.sub(" ", raw_line).strip()

        if _is_noise_line(line):
            continue

        cleaned_lines.append(line)

    result = "\n".join(cleaned_lines)

    # 4. Ardışık 3+ satır sonunu en fazla 2 satır sonuna (tek boş satır) indir
    result = _MULTI_NEWLINE_RE.sub("\n\n", result).strip()

    return result + "\n" if result else ""


def clean_file(input_path: Path, output_path: Path) -> Path:
    """Tek bir ham karar dosyasını temizleyip hedef yola yazar (idempotent)."""
    raw_text = input_path.read_text(encoding="utf-8")
    cleaned = clean_text(raw_text)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(cleaned, encoding="utf-8", newline="\n")
    return output_path


def run_clean_dir(raw_dir: Path, output_dir: Path) -> list[Path]:
    """Verilen klasördeki tüm karar_*.txt dosyalarını temizleyip hedef klasöre yazar."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for src in sorted(raw_dir.glob("karar_*.txt")):
        dst = output_dir / src.name
        written.append(clean_file(src, dst))
    return written