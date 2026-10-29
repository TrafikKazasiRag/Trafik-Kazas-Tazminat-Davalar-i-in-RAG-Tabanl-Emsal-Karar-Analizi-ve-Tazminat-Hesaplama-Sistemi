from trafikrag.adapters.lexical import bm25
from trafikrag.domain.decision import Chunk


def _index() -> bm25.Bm25Index:
    index = bm25.build({})
    index.add(
        [
            Chunk(
                "c1", "d1", "gerekce",
                "Davacının maluliyet oranı hesaplanırken TRH 2010 tablosu esas alınmıştır.",
                {"esas_no": "2019/1234", "karar_no": "2021/555"},
            ),
            Chunk(
                "c2", "d2", "hukum",
                "KTK 85. madde gereği işleten ve sürücü kusur oranında sorumludur.",
                {"esas_no": "2020/77", "karar_no": "2022/88"},
            ),
            Chunk(
                "c3", "d3", "olay",
                "Kaza tutanağına göre araç kavşakta duran bisiklete çarpmıştır.",
                {"esas_no": "2018/900", "karar_no": "2020/321"},
            ),
        ]
    )
    return index


def test_search_by_article_number():
    results = _index().search("madde 85", top_k=3)
    assert results[0].chunk.id == "c2"


def test_search_by_esas_and_karar_no():
    index = _index()
    assert index.search("2019/1234", top_k=3)[0].chunk.id == "c1"
    assert index.search("2020/321", top_k=3)[0].chunk.id == "c3"


def test_turkish_case_folding():
    # "I" -> "ı", "İ" -> "i": büyük harfli sorgu küçük harfli metni bulmalı
    results = _index().search("MALULİYET ORANI", top_k=3)
    assert results[0].chunk.id == "c1"


def test_filters_and_top_k():
    index = _index()
    assert index.search("kaza araç sürücü", top_k=1)
    only_hukum = index.search("araç sürücü", top_k=5, filters={"section_kind": "hukum"})
    assert [r.chunk.id for r in only_hukum] == ["c2"]
    assert index.search("xyz", top_k=3) == []
