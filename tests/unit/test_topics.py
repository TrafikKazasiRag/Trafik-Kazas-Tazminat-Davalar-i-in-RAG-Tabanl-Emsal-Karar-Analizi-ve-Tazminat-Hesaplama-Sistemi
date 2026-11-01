from trafikrag.domain.decision import Decision, Section
from trafikrag.retrieval.topics import classify_topic


def _decision(*sections: tuple[str, str]) -> Decision:
    return Decision(
        id="k1", court="", esas_no="", karar_no="", date="", source_url="",
        sections=[Section(kind=kind, text=text) for kind, text in sections],
    )


def test_death_case():
    d = _decision(("hukum", "Destekten yoksun kalma tazminatının davalıdan tahsiline karar verilmiştir."))
    assert classify_topic(d) == "olum"



def test_injury_case():
    d = _decision(("gerekce", "Sürekli iş göremezlik tazminatı ve geçici iş göremezlik tazminatı hesaplanmıştır."))
    assert classify_topic(d) == "yaralanma"


def test_damage_case():
    d = _decision(("hukum", "Araç değer kaybı bedelinin davalıdan tahsiline karar verilmiştir."))
    assert classify_topic(d) == "hasar"


def test_petition_summary_is_ignored():
    d = _decision(
        ("olay", "Davacı vekili destekten yoksun kalma tazminatı talep etmiştir."),
        ("hukum", "İstinaf başvurusunun reddine karar verilmiştir."),
    )
    assert classify_topic(d) == "diger"


def test_uppercase_turkish_text():
    d = _decision(("gerekce", "SÜREKLİ İŞ GÖREMEZLİK ve GEÇİCİ İŞ GÖREMEZLİK hesaplanmıştır."))
    assert classify_topic(d) == "yaralanma"


def test_no_gerekce_or_hukum_falls_back_to_all_text():
    d = _decision(("olay", "Destekten yoksun kalma tazminatı. Destekten yoksun kalma zararı hesaplanmıştır."))
    assert classify_topic(d) == "olum"

def test_hukum_decides_over_gerekce_mention():
    d = _decision(
        ("gerekce", "Davacılar destekten yoksun kalma talebinde bulunmamıştır."),
        ("hukum", "Sürekli iş göremezlik tazminatı hükmedilmiştir."),
    )
    assert classify_topic(d) == "yaralanma"


def test_passing_death_mention_in_injury_gerekce_is_ignored():
    d = _decision(("gerekce", "Destekten yoksun kalma. " + "Sürekli iş göremezlik maluliyet. " * 5))
    assert classify_topic(d) == "yaralanma"