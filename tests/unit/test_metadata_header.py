from trafikrag.ingestion.steps.parse_decision import extract_metadata

HEADER = (
    "SIRA NO: 1\n"
    "DERECE: BAM (İstinaf)\n"
    "DAİRE / MAHKEME: İstanbul Bölge Adliye Mahkemesi 9. Hukuk Dairesi\n"
    "ESAS NO: 2018/4092\n"
    "KARAR NO: 2020/4175\n"
    "KARAR TARİHİ: 24.12.2020 (Yıl: 2020)\n"
    + "=" * 80
    + "\n"
)

BODY = (
    "Yargıtay 9. Hukuk Dairesi'nin 2017/696 E., 2017/238 K. sayılı ilamında belirtildiği üzere,\n"
    "karar 17.05.2014 tarihinde verilmiştir.\n"
)


def test_metadata_comes_from_header_not_cited_decisions():
    meta = extract_metadata(HEADER + BODY)
    assert meta["court"] == "İstanbul Bölge Adliye Mahkemesi 9. Hukuk Dairesi"
    assert meta["esas_no"] == "2018/4092"
    assert meta["karar_no"] == "2020/4175"
    assert meta["date"] == "2020-12-24"

def test_metadata_falls_back_to_body_without_header():
    meta = extract_metadata("Yargıtay 4. Hukuk Dairesi\n2023/11230 E. , 2023/13550 K.\n")
    assert meta["esas_no"] == "2023/11230"
    assert meta["karar_no"] == "2023/13550"