# Veri Hazırlama Hattı (Ingestion Pipeline) 400 Doküman Doğrulama Raporu

**Tarih:** 2026  
**Test Kapsamı:** 400 adet ham karar metni (`data/txt_dosyalar`)  
**Veri Kaynağı:** 246 İlk Derece Mahkemesi + 154 BAM (Bölge Adliye Mahkemesi / İstinaf) kararı  
**Kullanılan Yapılandırma:** `configs/default.yaml`  

---

## 1. Özet & Genel Başarı

`topic_filter` adımı ve sonuç tespit mantığı refactor edildikten sonra 400 kararlık gerçek veri seti üzerinde uçtan uca veri hazırlama boru hattı (`clean` -> `dedupe` -> `topic_filter` -> `split` -> `index`) koşturulmuştur.

* **Toplam Ham Karar:** 400
* **Elenen Karar:** 0 (Sonucu belirsiz olanlar dâhil veri kaybını önlemek adına boru hattına dahil edildi)
* **Nihai Kabul Edilen Karar:** 400 (%100)
* **Bölümleri Tam Parçalanan Karar Oranı:** %86.8 (347 / 400)

---

## 2. Adım Adım Çalışma Sonuçları

| Pipeline Adımı | Girdi Sayısı | Çıktı / Elenen | İşlem Detayı |
| :--- | :---: | :---: | :--- |
| **01_clean** | 400 | 400 (0 elendi) | Veri seti halihazırda temiz; 1/400 dosyada karakter/boşluk düzeltmesi yapıldı. |
| **02_dedupe** | 400 | 400 (0 elendi) | İçerik ve künye bazlı mükerrer karar kontrolü yapıldı. |
| **03_topic_filter** | 400 | 400 (0 elendi) | Ceza/Danıştay süzgeci ve genişletilmiş hüküm penceresiyle kararlar etiketlendi, elenme yaşanmadı. |
| **04_split** | 400 | 400 | Decision şemasına uygun olarak Dava, Gerekçe ve Karar bölümlerine ayrıştırıldı. |
| **05_index** | 400 | 400 | RAG vektör indeksleme aşamasına hazır `data/interim/decisions.jsonl` dosyası üretildi. |

---

## 3. İstatistiksel Dağılım

### A. Karar Sonucu Dağılımı (`outcome_distribution`)
Genişletilmiş 4000 karakterlik hüküm penceresi ve esnek regex kalıpları sonrası 400 karardaki dağılım:
* **Kısmen Kabul:** 139 (%34.8)
* **İstinaf Reddi:** 83 (%20.8)
* **Sonucu Belirsiz / Standart Dışı:** 81 (%20.3) — *(Elenmeyip `sonuc_belirsiz` etiketiyle saklandı)*
* **Kabul:** 62 (%15.5)
* **Ret:** 32 (%8.0)
* **Kaldırma:** 2 (%0.5)
* **Bozma:** 1 (%0.3)

### B. Karar Yılı Dağılımı (`year_distribution`)
* **2018:** 16 | **2019:** 25 | **2020:** 38 | **2021:** 51 | **2022:** 72 | **2023:** 60 | **2024:** 46 | **2025:** 53 | **2026:** 39

---

## 4. Çıktı Dosyaları ve Erişilebilirlik

Test sonucunda üretilen özet rapor dosyası `data/interim/ingestion_report.json` olarak diske yazılmış, detaylı gerekçe/etiket dökümü `data/interim/selection_log.csv` dosyasına aktarılmış ve nihai veri kümesi `data/interim/decisions.jsonl` altında hazır edilmiştir.