import hashlib
import json
import os
import random
import re
import time
from typing import Dict, List, Optional, Set
from bs4 import BeautifulSoup
from playwright.sync_api import Page, sync_playwright

# ==============================================================================
# YAPILANDIRMA VE SABİTLER
# ==============================================================================
HEDEF_KARAR_SAYISI = 300
ARAMA_KELIMESI = "trafik kazası maddi manevi tazminat kusur"
SAYFA_BASI_KAYIT = 10

DATA_DIR = "data"
TXT_DIR = os.path.join(DATA_DIR, "txt_dosyalar")
JSON_PATH = os.path.join(DATA_DIR, "uyap_emsal_kararlar.json")

os.makedirs(TXT_DIR, exist_ok=True)


# ==============================================================================
# YARDIMCI FONKSİYONLAR VE DOĞRULAMA (HASH & DEDUPLICATION)
# ==============================================================================
def metin_hash_al(metin: str) -> str:
  norm_metin = re.sub(r"\s+", "", metin.lower())
  return hashlib.md5(norm_metin.encode("utf-8")).hexdigest()


def birlesik_anahtar_olustur(daire: str, esas: str, karar: str) -> str:
  ham = f"{daire}_{esas}_{karar}".lower()
  return re.sub(r"\s+", "", ham)


def html_temizle(ham_html: str) -> str:
  if not ham_html:
    return ""
  soup = BeautifulSoup(ham_html, "html.parser")
  for tag in soup(["script", "style", "meta", "head"]):
    tag.decompose()
  metin = soup.get_text(separator="\n")
  satirlar = [
      re.sub(r"\s+", " ", satir).strip() for satir in metin.splitlines()
  ]
  temiz_satirlar = [s for s in satirlar if s]
  return "\n".join(temiz_satirlar)


def mevcut_kayitlari_yukle() -> List[Dict]:
  if not os.path.exists(JSON_PATH):
    return []
  try:
    with open(JSON_PATH, "r", encoding="utf-8") as f:
      veriler = json.load(f)

    temiz_liste = []
    gorulen_hashler = set()
    gorulen_anahtarlar = set()

    for k in veriler:
      icerik = k.get("icerik", "")
      if len(icerik) < 100:
        continue
      h = metin_hash_al(icerik)
      anahtar = birlesik_anahtar_olustur(
          k.get("daire", ""), k.get("esas_no", ""), k.get("karar_no", "")
      )

      if h not in gorulen_hashler and anahtar not in gorulen_anahtarlar:
        gorulen_hashler.add(h)
        gorulen_anahtarlar.add(anahtar)
        k["icerik_hash"] = h
        temiz_liste.append(k)

    # TXT dosyalarını temiz listeyle senkronize et
    for idx, karar in enumerate(temiz_liste, start=1):
      karari_diske_yaz(karar, idx, temiz_liste, sadece_txt=True)

    with open(JSON_PATH, "w", encoding="utf-8") as json_f:
      json.dump(temiz_liste, json_f, ensure_ascii=False, indent=4)

    print(
        f"[*] Mevcut JSON kontrol edildi: {len(temiz_liste)} adet %100"
        " benzersiz karar hazır."
    )
    return temiz_liste
  except Exception as e:
    print(f"[!] Mevcut JSON okunamadı, sıfırdan başlanıyor: {e}")
    return []


def karari_diske_yaz(
    karar_paketi: Dict,
    sira_no: int,
    tum_kararlar: List[Dict],
    sadece_txt: bool = False,
):
  txt_dosya_yolu = os.path.join(TXT_DIR, f"karar_{sira_no}.txt")
  baslik = (
      f"SIRA NO: {sira_no}\n"
      f"DOKÜMAN ID: {karar_paketi.get('id', 'Bilinmiyor')}\n"
      f"DAİRE / MAHKEME: {karar_paketi.get('daire', 'Belirtilmemiş')}\n"
      f"ESAS NO: {karar_paketi.get('esas_no', 'Belirtilmemiş')}\n"
      f"KARAR NO: {karar_paketi.get('karar_no', 'Belirtilmemiş')}\n"
      f"KARAR TARİHİ: {karar_paketi.get('tarih', 'Belirtilmemiş')}\n"
      f"İÇERİK HASH (MD5): {karar_paketi.get('icerik_hash', '')}\n"
      + ("=" * 75)
      + "\n\n"
  )
  with open(txt_dosya_yolu, "w", encoding="utf-8") as txt_f:
    txt_f.write(baslik + karar_paketi.get("icerik", ""))

  if not sadece_txt:
    with open(JSON_PATH, "w", encoding="utf-8") as json_f:
      json.dump(tum_kararlar, json_f, ensure_ascii=False, indent=4)


def ekrana_durum_yaz(page: Page, mesaj: str, renk: str = "#10b981"):
  """Tarayıcı ekranının üstüne canlı bilgi paneli basar (Sekmenin boş görünmesini engeller)."""
  js = """
    ({ mesaj, renk }) => {
        let kutu = document.getElementById('rag-durum-paneli');
        if (!kutu) {
            kutu = document.createElement('div');
            kutu.id = 'rag-durum-paneli';
            kutu.style.cssText = 'position:fixed;top:15px;right:15px;z-index:999999;background:#1e293b;color:#fff;padding:14px 20px;border-radius:8px;font-family:monospace;font-size:14px;box-shadow:0 10px 25px rgba(0,0,0,0.4);border-left:6px solid ' + renk + ';max-width:480px;';
            document.body.appendChild(kutu);
        }
        kutu.style.borderLeftColor = renk;
        kutu.innerHTML = '<b>🚀 UYAP RAG Scraper Aktif</b><br><span style="color:#cbd5e1;margin-top:5px;display:block;">' + mesaj + '</span>';
    }
    """
  try:
    page.evaluate(js, {"mesaj": mesaj, "renk": renk})
  except Exception:
    pass


def oturumu_tazele(page: Page):
  """UYAP rate-limit veya session kilidi koyduğunda çerezleri ve oturumu yeniler."""
  print(
      "    [🔄] UYAP hız sınırına takıldı, oturum (JSESSIONID) tazeleniyor..."
  )
  ekrana_durum_yaz(
      page, "UYAP Hız Sınırı: Oturum yenileniyor, lütfen bekleyin...", "#f59e0b"
  )
  try:
    page.context.clear_cookies()
    page.goto(
        "https://emsal.uyap.gov.tr",
        wait_until="domcontentloaded",
        timeout=45000,
    )
    time.sleep(3.5)
  except Exception as e:
    print(f"    [!] Oturum yenileme uyarısı: {e}")
    time.sleep(5.0)


# ==============================================================================
# DOĞRUDAN UYAP REST API MOTORU (RATE-LIMIT VE RETRY ZIRHLI)
# ==============================================================================
def api_sayfa_listesi_cek(
    page: Page, kelime: str, sayfa_no: int
) -> Optional[List[Dict]]:
  """UYAP'ın '/aramalist' endpoint'inden ilgili sayfanın 10 kararlık listesini çeker."""
  js_kodu = """
    async ({ kelime, sayfaNo, kayitSayisi }) => {
        const payload = {
            data: {
                aranan: kelime,
                arananKelime: kelime,
                pageSize: kayitSayisi,
                pageNumber: sayfaNo
            }
        };
        try {
            const res = await fetch('/aramalist', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json; charset=UTF-8',
                    'Accept': 'application/json, text/plain, */*',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(payload)
            });
            if (!res.ok) return { hata: 'HTTP_' + res.status };
            const json = await res.json();
            if (json && json.data) {
                if (Array.isArray(json.data)) return { kayitlar: json.data };
                if (Array.isArray(json.data.data)) return { kayitlar: json.data.data };
            }
            return { hata: 'BOS_VERI', ham: json };
        } catch (err) {
            return { hata: err.toString() };
        }
    }
    """
  for deneme in range(1, 5):
    try:
      sonuc = page.evaluate(
          js_kodu,
          {
              "kelime": kelime,
              "sayfaNo": sayfa_no,
              "kayitSayisi": SAYFA_BASI_KAYIT,
          },
      )
      if (
          sonuc
          and isinstance(sonuc, dict)
          and "kayitlar" in sonuc
          and len(sonuc["kayitlar"]) > 0
      ):
        return sonuc["kayitlar"]

      # Eğer boş döndüyse veya hız sınırına takıldıysa bekle ve oturumu yenile
      bekleme = 3.0 * deneme
      print(
          f"    [!] Sayfa {sayfa_no} listesi alınamadı (Deneme {deneme}/4)."
          f" {bekleme:.1f} sn soğutuluyor..."
      )
      time.sleep(bekleme)
      if deneme >= 2:
        oturumu_tazele(page)
    except Exception:
      time.sleep(3.0)
  return None


def api_tekil_dokuman_cek(page: Page, karar_id: str, esas_no: str) -> Optional[str]:
  """Sadece '/getDokuman?id=' ucuna istek atar. Hız sınırına takılırsa oturumu tazeleyip tekrar alır."""
  js_kodu = """
    async (id) => {
        try {
            const res = await fetch(`/getDokuman?id=${id}`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json, text/plain, */*',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            if (!res.ok) return { hata: 'HTTP_' + res.status };
            const veri = await res.json();
            if (veri && typeof veri.data === 'string' && veri.data.length > 50) {
                return { html: veri.data };
            }
            return { hata: 'ICERIK_BOS', durum: veri ? veri.metadata : null };
        } catch (e) {
            return { hata: e.toString() };
        }
    }
    """
  for deneme in range(1, 5):
    try:
      yanit = page.evaluate(js_kodu, str(karar_id))
      if yanit and isinstance(yanit, dict) and "html" in yanit:
        return yanit["html"]

      # UYAP rate-limit uyguladıysa kademeli bekle
      bekleme_suresi = 2.5 * deneme + random.uniform(0.5, 1.5)
      ekrana_durum_yaz(
          page,
          f"ID:{karar_id} ({esas_no}) için UYAP rate-limit bekleniyor"
          f" ({bekleme_suresi:.1f} sn)...",
          "#f59e0b",
      )
      time.sleep(bekleme_suresi)

      # 2. denemede de vermediyse çerezleri sıfırlayıp temiz oturum aç
      if deneme == 2 or deneme == 3:
        oturumu_tazele(page)

    except Exception:
      time.sleep(2.5)

  return None


# ==============================================================================
# ANA ÇALIŞTIRICI (MAIN PIPELINE)
# ==============================================================================
def main():
  print("=" * 75)
  print(" UYAP EMSAL KARAR İNDİRİCİ V3 (ANTI-BAN & OTURUM TAZELEME ZIRHLI)")
  print("=" * 75)

  toplanan_kararlar = mevcut_kayitlari_yukle()

  gorulen_anahtarlar: Set[str] = {
      birlesik_anahtar_olustur(
          k.get("daire", ""), k.get("esas_no", ""), k.get("karar_no", "")
      )
      for k in toplanan_kararlar
  }
  gorulen_hashler: Set[str] = {
      k.get("icerik_hash", metin_hash_al(k.get("icerik", "")))
      for k in toplanan_kararlar
  }
  gorulen_idler: Set[str] = {
      str(k.get("id", "")) for k in toplanan_kararlar if k.get("id")
  }

  if len(toplanan_kararlar) >= HEDEF_KARAR_SAYISI:
    print(f"[+] Zaten {len(toplanan_kararlar)} adet benzersiz karar mevcut!")
    return

  with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
    )
    context = browser.new_context(
        viewport=None,
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
    )
    page = context.new_page()

    try:
      print("[*] https://emsal.uyap.gov.tr adresine bağlanılıyor...")
      page.goto(
          "https://emsal.uyap.gov.tr",
          wait_until="domcontentloaded",
          timeout=60000,
      )
      time.sleep(3.0)

      ekrana_durum_yaz(
          page,
          f"Arka plan API motoru başlatıldı. Mevcut: {len(toplanan_kararlar)}"
          f" / {HEDEF_KARAR_SAYISI}",
      )

      # 1. sayfadan başla ama zaten indirilmiş olanları hızlıca atla (Arada kaçanları toplamak için!)
      sayfa_no = 1
      ardisik_basarisiz_sayfa = 0

      while (
          len(toplanan_kararlar) < HEDEF_KARAR_SAYISI
          and ardisik_basarisiz_sayfa < 4
      ):
        ekrana_durum_yaz(
            page,
            f"Sayfa {sayfa_no} taranıyor... İndirilen:"
            f" {len(toplanan_kararlar)}/{HEDEF_KARAR_SAYISI}",
        )
        kayit_listesi = api_sayfa_listesi_cek(page, ARAMA_KELIMESI, sayfa_no)

        if not kayit_listesi:
          ardisik_basarisiz_sayfa += 1
          print(
              f"[-] Sayfa {sayfa_no} alınamadı"
              f" ({ardisik_basarisiz_sayfa}/4)..."
          )
          oturumu_tazele(page)
          continue

        ardisik_basarisiz_sayfa = 0
        print(
            f"\n--- API Sayfa {sayfa_no} ({len(kayit_listesi)} kayıt inceleniyor)"
            " ---"
        )

        sayfada_yeni_islem_yapildi = False

        for kayit in kayit_listesi:
          if len(toplanan_kararlar) >= HEDEF_KARAR_SAYISI:
            break

          karar_id = str(kayit.get("id", ""))
          daire = kayit.get("birimAdi", kayit.get("daire", ""))
          esas_no = kayit.get("esasNo", "")
          karar_no = kayit.get("kararNo", "")
          tarih = kayit.get("kararTarihi", "")
          durum = kayit.get("kararDurumu", "")

          ortak_anahtar = birlesik_anahtar_olustur(daire, esas_no, karar_no)

          # Zaten indirilmişse hiç sunucuyu yorma, anında geç
          if (
              not karar_id
              or karar_id in gorulen_idler
              or ortak_anahtar in gorulen_anahtarlar
          ):
            continue

          sayfada_yeni_islem_yapildi = True
          ekrana_durum_yaz(
              page,
              f"İndiriliyor ({len(toplanan_kararlar)+1}/{HEDEF_KARAR_SAYISI}):"
              f"<br>{daire}<br>E.{esas_no} - K.{karar_no}",
          )

          ham_html = api_tekil_dokuman_cek(page, karar_id, esas_no)
          if not ham_html:
            print(
                f"    [-] ID:{karar_id} (E.{esas_no}) 4 denemede de alınamadı,"
                " geçiliyor."
            )
            continue

          temiz_metin = html_temizle(ham_html)
          if len(temiz_metin) < 100:
            continue

          yeni_hash = metin_hash_al(temiz_metin)
          if yeni_hash in gorulen_hashler:
            print(
                f"    [!] E.{esas_no} mükerrer metin içeriyor, atlandı."
            )
            gorulen_idler.add(karar_id)
            continue

          yeni_sira = len(toplanan_kararlar) + 1
          paket = {
              "id": karar_id,
              "daire": daire,
              "esas_no": esas_no,
              "karar_no": karar_no,
              "tarih": tarih,
              "durum": durum,
              "icerik_hash": yeni_hash,
              "icerik": temiz_metin,
          }

          toplanan_kararlar.append(paket)
          gorulen_anahtarlar.add(ortak_anahtar)
          gorulen_hashler.add(yeni_hash)
          gorulen_idler.add(karar_id)
          karari_diske_yaz(paket, yeni_sira, toplanan_kararlar)

          print(
              f"    [+] ({yeni_sira}/{HEDEF_KARAR_SAYISI}) İndirildi: {daire} |"
              f" E.{esas_no} K.{karar_no}"
          )

          # UYAP WAF (Güvenlik Duvarı) Koruması: Her doküman arası 1.5 - 2.3 saniye insani bekleme!
          time.sleep(random.uniform(1.5, 2.3))

        sayfa_no += 1
        # Eğer sayfadaki tüm kararlar zaten önceden indirilmişse beklemeden diğer sayfaya geç
        if sayfada_yeni_islem_yapildi:
          time.sleep(random.uniform(1.5, 2.5))

    except KeyboardInterrupt:
      print("\n[!] Kullanıcı tarafından durduruldu. İndirilenler güvende.")
    except Exception as e:
      print(f"\n[-] Beklenmeyen Hata: {e}")
    finally:
      browser.close()

  print("\n" + "=" * 75)
  print(
      f"[*] İŞLEM BİTTİ! Toplam {len(toplanan_kararlar)} adet %100 BENZERSİZ"
      " karar kaydedildi."
  )
  print(f"    -> Doğrulanan Tekil MD5 Hash Sayısı: {len(gorulen_hashler)}")
  print("=" * 75)


if __name__ == "__main__":
  main()