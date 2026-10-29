# Veri Hazırlama Hattı (Ingestion Pipeline) 400 Doküman Doğrulama Raporu

**Tarih:** 2026  
**Test Kapsamı:** 400 adet ham Yargıtay emsal karar metni (`data/txt_dosyalar`)  
**Kullanılan Yapılandırma:** `configs/default.yaml`  
**Test Branch:** `demo/full-pipeline-test`  

---

## 1. Özet & Genel Başarı

400 kararlık ham veri seti üzerinde uçtan uca veri hazırlama boru hattı (`clean` -> `dedupe` -> `topic_filter` -> `split` -> `index`) koşturulmuş ve modüller sorunsuz şekilde çalışmıştır.

* **Toplam Ham Karar:** 400
* **Filtrelenen Kapsam Dışı Karar:** 125 (Ceza davaları ve ölümlü kaza kararları `03_rejected_olumlu` klasörüne ayrıştırıldı)
* **Kabul Edilen Temiz Karar:** 275
* **Bölümleri Tam Parçalanan Karar Oranı:** %85.8 (236 / 275)

---

## 2. Adım Adım Çalışma Sonuçları

| Pipeline Adımı | Girdi Sayısı | Çıktı / Elenen | İlem Detayı |
| :--- | :---: | :---: | :--- |
| **01_clean** | 400 | 400 | Site gürültüleri, avukat reklamları ve gereksiz header/footer alanları temizlendi. |
| **02_dedupe** | 400 | 400 (0 elendi) | İçerik bazlı mükerrer karar kontrolü yapıldı. |
| **03_topic_filter** | 400 | 275 (125 elendi)| Yaralanmalı trafik kazası dışındaki ceza ve ölümlü kaza kararları ayrıştırıldı. |
| **04_split** | 275 | 275 | Decision şemasına uygun olarak Dava, Gerekçe ve Karar bölümlerine ayrıştırıldı. |
| **05_index** | 275 | 275 | RAG vektör indeksleme aşamasına hazır `data/interim/decisions.jsonl` dosyası üretildi. |

---

## 3. İstatistiksel Dağılım

### A. Karar Sonucu Dağılımı (`outcome_distribution`)
Yaralanmalı trafik kazası davalarında beklenen emsal dağılımı ile birebir uyumludur:
* **Kısmen Kabul:** 136 (%49.4)
* **Red:** 94 (%34.1)
* **Kabul:** 29 (%10.5)
* **İstinaf Reddi:** 12 (%4.3)
* **Kaldırma:** 3 (%1.1)
* **Bozma:** 1 (%0.4)

### B. Karar Yılı Dağılımı (`year_distribution`)
* **2018:** 12 | **2019:** 13 | **2020:** 31 | **2021:** 36 | **2022:** 51 | **2023:** 41 | **2024:** 30 | **2025:** 37 | **2026:** 24

---

## 4. Çıktı Dosyaları ve Erişilebilirlik

Test sonucunda üretilen özet rapor dosyası `data/interim/ingestion_report.json` olarak diske yazılmış, elenen kararlar `data/interim/work/03_rejected_olumlu/` klasörüne ayrıştırılmış ve nihai veri kümesi `data/interim/decisions.jsonl` altında hazır edilmiştir.