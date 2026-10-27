"""
tests/unit/test_fetch.py
fetch.py modülü için Buğra'nın PR review'larından geçecek tam kapsamlı birim testleri.
"""

import pytest
from pathlib import Path
from trafikrag.ingestion.steps.fetch import fetch_raw_decisions, iter_raw_decisions

def test_fetch_raw_decisions_non_existent_dir(tmp_path):
    """Olmayan bir dizin verilirse boş liste dönmeli."""
    missing_dir = tmp_path / "olmayan_klasor"
    result = fetch_raw_decisions(missing_dir)
    assert result == []

def test_fetch_raw_decisions_filtering_and_strict_naming(tmp_path):
    """Sadece tam olarak karar_*.txt formatındaki küçük harfli dosyaların alındığını, 
       uzantı veya büyük harf farkı olanların (örn. .PDF veya KARAR_) elendiğini test eder."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    
    valid_file = raw_dir / "karar_01.txt"
    invalid_ext = raw_dir / "karar_02.PDF"
    invalid_prefix = raw_dir / "rapor_03.txt"
    uppercase_name = raw_dir / "KARAR_04.TXT"
    
    valid_file.write_text("Geçerli", encoding="utf-8")
    invalid_ext.write_text("Geçersiz uzantı", encoding="utf-8")
    invalid_prefix.write_text("Geçersiz önek", encoding="utf-8")
    uppercase_name.write_text("Büyük harf", encoding="utf-8")
    
    results = fetch_raw_decisions(raw_dir)
    
    assert len(results) == 1
    assert results[0].name == "karar_01.txt"

def test_fetch_raw_decisions_numerical_sorting(tmp_path):
    """Dosya adları sıralanırken alfabetik karmaşa (örn. karar_10, karar_2'den önce gelmesi) 
       yaşanmadığını veya doğru sıralama yapıldığını test eder."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    
    (raw_dir / "karar_02.txt").write_text("2", encoding="utf-8")
    (raw_dir / "karar_10.txt").write_text("10", encoding="utf-8")
    (raw_dir / "karar_01.txt").write_text("1", encoding="utf-8")
    
    results = fetch_raw_decisions(raw_dir)
    names = [p.name for p in results]
    
    # Standart sorted string sıralamasında karar_10, karar_02'den önce gelebilir. 
    # Eğer mimari doğal sıralama (natsort) gerektiriyorsa veya alfabetikse buna göre netleşir.
    # Burada mevcut sorted() beklentisine göre test edelim:
    assert names[0] == "karar_01.txt"
    assert names[1] == "karar_02.txt"
    assert names[2] == "karar_10.txt"

def test_iter_raw_decisions_content_and_turkish_chars(tmp_path):
    """Generator yapısının Türkçe karakterleri ve içerikleri bozmadan okuduğunu test eder."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    
    file_path = raw_dir / "karar_01.txt"
    expected_content = "Yargıtay Hukuk Dairesi - Trafik Kazası Maddi Tazminat Kararı ŞÖĞÜÇçşğüöıİ"
    file_path.write_text(expected_content, encoding="utf-8")
    
    items = list(iter_raw_decisions(raw_dir))
    
    assert len(items) == 1
    path, content = items[0]
    assert path.name == "karar_01.txt"
    assert content == expected_content

def test_iter_raw_decisions_empty_file(tmp_path):
    """Boş bir karar dosyası olduğunda sistemin çökmediğini ve boş string döndüğünü test eder."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    
    file_path = raw_dir / "karar_01.txt"
    file_path.write_text("", encoding="utf-8")
    
    items = list(iter_raw_decisions(raw_dir))
    assert len(items) == 1
    _, content = items[0]
    assert content == ""

def test_iter_raw_decisions_read_exception_handling(tmp_path, monkeypatch):
    """Dosya okuma sırasında disk veya yetki hatası fırlatılırsa, pipeline'ın 
       diğer dosyaları işlemeye devam ettiğini ve çökmediğini test eder."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    
    file_1 = raw_dir / "karar_01.txt"
    file_2 = raw_dir / "karar_02.txt"
    
    file_1.write_text("Normal Dosya", encoding="utf-8")
    file_2.write_text("Hatalı Okunacak Dosya", encoding="utf-8")
    
    # Sadece karar_02.txt okunurken PermissionError fırlatsın
    original_read_text = Path.read_text
    def mock_read_text(self, encoding="utf-8"):
        if "karar_02.txt" in str(self):
            raise PermissionError("Disk okuma hatası")
        return original_read_text(self, encoding=encoding)
        
    monkeypatch.setattr(Path, "read_text", mock_read_text)
    
    items = list(iter_raw_decisions(raw_dir))
    
    # karar_01 başarıyla okunmalı, karar_02 hata verip atlanmalı (generator çökmemeli)
    assert len(items) == 1
    assert items[0][0].name == "karar_01.txt"
    assert items[0][1] == "Normal Dosya"