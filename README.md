# Trafik Kazası RAG

Trafik kazası tazminat davaları için RAG tabanlı emsal karar analizi ve tazminat hesaplama sistemi (ders projesi).

> Bu uygulama hukuki danışmanlık değildir. Sadece tahmin yürütüp bilgi vermek amacıyla oluşturulmuştur.

## Mimari ilkeleri
- Bağımlılık yönü: `api -> services -> ports <- adapters`; `domain` hiçbir şeye bağımlı değil.
- Değişebilecek her bileşen (`embedder`, `vector_store`, `reranker`, `llm`, `chunker`) `ports/` altında bir arayüz, `adapters/` altında bir uygulamadır.
- Bileşenler `configs/*.yaml` ile seçilir (`src/trafikrag/bootstrap.py`). Yeni adaptör = yeni dosya + `build(cfg)` + config'de `type`.
- Rakamlar LLM'den değil `calculation/` modülünden gelir.

## Hızlı başlangıç
```bash
cp .env.example .env
make install
make db
make run        # http://localhost:8000/api/health
make test
```

## Klasörler
`configs/` deney ve varsayılan ayarlar · `prompts/` sürümlü prompt'lar · `data/` (Git'e girmez) · `src/trafikrag/` kod · `frontend/` saf HTML/CSS/JS + Bootstrap · `docs/` mimari raporu · `tests/`
