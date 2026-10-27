"""
1. Adım (Fetch): Ham karar metinlerini data/raw (veya belirtilen dizin) altından 
güvenli bir şekilde toplar ve ingestion pipeline için hazırlar.
"""

from pathlib import Path
from typing import List, Generator

def fetch_raw_decisions(data_dir: str | Path = "data/raw") -> List[Path]:
    """
    Ham karar dizinindeki dosyalardan yalnızca tam olarak 'karar_*.txt' formatına 
    uyanları (büyük/küçük harf ve uzantı duyarlı olarak) sıralı bir şekilde listeler.
    """
    path = Path(data_dir)
    if not path.exists():
        return []
    
    valid_files = []
    for file_path in path.glob("*.txt"):
        if file_path.name.startswith("karar_") and file_path.name.endswith(".txt") and file_path.name != "karar_.txt":
            valid_files.append(file_path)
            
    return sorted(valid_files)

def iter_raw_decisions(data_dir: str | Path = "data/raw") -> Generator[tuple[Path, str], None, None]:
    """
    Ham karar dosyalarını tek tek okuyarak dosya yolu ve içerik string'ini 
    generator olarak döner. Farklı encoding (utf-8 / cp1254) denemeleri ve 
    okuma hatalarında akışı kesmeden güvenli devam etme özelliği içerir.
    """
    for file_path in fetch_raw_decisions(data_dir):
        content = None
        # Farklı karakter kodlamaları için güvenli okuma sırası
        for encoding in ("utf-8", "cp1254", "latin-1"):
            try:
                content = file_path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"Hata [fetch]: {file_path} okunamadı -> {e}")
                break
        
        if content is not None:
            yield file_path, content