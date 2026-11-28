import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const ACCIDENT_TYPE_LABELS = {
  carpisma: 'Araçların Çarpışması',
  yaya_carpmasi: 'Yayaya Çarpma',
  tek_tarafli: 'Tek Taraflı Kaza',
  park_halindeki_arac: 'Park Halindeki Araca Çarpma',
  diger: 'Diğer',
};

const VICTIM_ROLE_LABELS = {
  surucu: 'Sürücü',
  yolcu: 'Yolcu (Araç İçi)',
  yaya: 'Yaya',
};

const GENDER_LABELS = {
  E: 'Erkek',
  K: 'Kadın',
};

const INCOME_BASIS_LABELS = {
  net: 'Net Gelir',
  brut: 'Brüt Gelir',
};

function formatCurrencyTR(value) {
  if (value === null || value === undefined || value === '' || Number.isNaN(Number(value))) {
    return '—';
  }
  return `${Number(value).toLocaleString('tr-TR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} TL`;
}

function formatDateTR(isoDate) {
  if (!isoDate || typeof isoDate !== 'string') return 'Belirtilmedi';
  const parts = isoDate.split('-');
  if (parts.length !== 3) return isoDate;
  return `${parts[2]}.${parts[1]}.${parts[0]}`;
}

export default function App() {
  const [currentView, setCurrentView] = useState('landing'); // 'landing' | 'calculator'

  useEffect(() => {
    document.title = 'Trafik Kazası Tazminat Hesaplama';
  }, []);

  const [formData, setFormData] = useState({
    accident_type: '',
    victim_role: '',
    seatbelt_or_helmet: '',
    non_pecuniary_claim: '',
    age: '',
    gender: '',
    disability_rate: '',
    monthly_income: '',
    income_basis: '',
    plaintiff_fault: '',
    temporary_incapacity_months: '',
    accident_date: '',
  });

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;

    if (name === 'victim_role' && value === 'yaya') {
      setFormData((prev) => ({
        ...prev,
        victim_role: value,
        seatbelt_or_helmet: '',
      }));
      return;
    }

    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    let seatbeltVal = null;
    if (formData.victim_role !== 'yaya' && formData.seatbelt_or_helmet !== '') {
      seatbeltVal = formData.seatbelt_or_helmet === 'true';
    }

    const payload = {
      accident_type: formData.accident_type || null,
      victim_role: formData.victim_role || null,
      seatbelt_or_helmet: seatbeltVal,
      age: formData.age === '' ? null : Number(formData.age),
      gender: formData.gender || null,
      monthly_income: formData.monthly_income === '' ? null : Number(formData.monthly_income),
      income_basis: formData.income_basis || null,
      non_pecuniary_claim:
        formData.non_pecuniary_claim === '' ? null : Number(formData.non_pecuniary_claim),
      disability_rate:
        formData.disability_rate === '' ? null : Number(formData.disability_rate) / 100,
      plaintiff_fault:
        formData.plaintiff_fault === '' ? null : Number(formData.plaintiff_fault) / 100,
      temporary_incapacity_months:
        formData.temporary_incapacity_months === ''
          ? null
          : Number(formData.temporary_incapacity_months),
      accident_date: formData.accident_date || null,
    };

    try {
      const response = await axios.post(`${API_BASE_URL}/api/analyze`, payload);
      setResult(response.data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(
        Array.isArray(detail)
          ? detail.map((d) => d.msg).join(', ')
          : detail || 'Hesaplama servisine bağlanırken bir hata oluştu.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const comp = result?.calculation_results?.compensation;
  const costs = result?.calculation_results?.costs;
  const warnings = result?.calculation_results?.warnings || [];
  const caseSummary = result?.case_summary || {};
  const todayFormatted = new Date().toLocaleDateString('tr-TR');

  return (
    <div className="min-h-screen bg-[#FFFFFF] text-[#1B2430] flex flex-col">
      {/* Üst Başlık Çubuğu */}
      <header className="border-b border-[#D9DEE5] bg-[#FFFFFF] no-print">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div>
            <button
              type="button"
              onClick={() => setCurrentView('landing')}
              className="text-left focus:outline-none cursor-pointer"
            >
              <span className="font-serif-heading text-lg text-[#1B2430] tracking-tight block">
                Trafik Kazası Bedensel Zarar Hesaplama
              </span>
              <span className="text-xs text-[#566070]">
                TRH-2010 Yaşam Tablosu ve Yargıtay Aktüerya Esasları
              </span>
            </button>
          </div>
          {currentView === 'calculator' && (
            <button
              type="button"
              onClick={() => setCurrentView('landing')}
              className="text-xs font-medium text-[#1F3A5F] hover:underline px-3 py-1.5 border border-[#D9DEE5] rounded-[4px] bg-[#F6F7F9] cursor-pointer"
            >
              Giriş Sayfasına Dön
            </button>
          )}
        </div>
      </header>

      {/* Yazdırma / PDF Başlığı */}
      <div className="hidden print:block border-b border-[#D9DEE5] pb-4 mb-6">
        <div className="flex items-baseline justify-between">
          <div>
            <h1 className="font-serif-heading text-xl text-[#1B2430]">
              Hesaplama özeti (PDF)
            </h1>
            <p className="text-xs text-[#566070] mt-1">
              Trafik Kazası Bedensel Zarar Ön Hesaplama Dökümü
            </p>
          </div>
          <div className="text-right text-xs text-[#566070] tabular-nums">
            <div>Düzenleme Tarihi: {todayFormatted}</div>
            <div>Dayanak: TRH-2010 / 6098 s. TBK / 2918 s. KTK</div>
          </div>
        </div>
      </div>

      {/* EKRAN 1: AÇILIŞ SAYFASI */}
      {currentView === 'landing' && (
        <main className="flex-1 max-w-3xl mx-auto w-full px-4 sm:px-6 py-12 sm:py-16 space-y-12 no-print">
          <section className="space-y-4 border-b border-[#D9DEE5] pb-10">
            <h1 className="font-serif-heading text-2xl sm:text-3xl text-[#1B2430] leading-snug">
              Trafik Kazası Bedensel Tazminat Ön Hesaplama Aracı
            </h1>
            <p className="text-sm sm:text-base text-[#566070] leading-relaxed">
              Yaralanmalı trafik kazalarında maluliyet, geçici iş göremezlik ve yargılama gideri
              kalemlerini aktüeryal esaslara göre hesaplayan ön değerlendirme aracıdır.
            </p>
            <div className="pt-2">
              <button
                type="button"
                onClick={() => setCurrentView('calculator')}
                className="inline-flex items-center justify-center px-5 py-2.5 text-sm font-medium text-[#FFFFFF] bg-[#1F3A5F] hover:bg-[#172C49] rounded-[4px] transition-colors cursor-pointer"
              >
                Hesaplama Formuna Geç
              </button>
            </div>
          </section>

          {/* 3 Adımlı Nasıl Çalışır */}
          <section className="space-y-4">
            <h2 className="font-serif-heading text-lg text-[#1B2430]">Nasıl çalışır?</h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="bg-[#F6F7F9] border border-[#D9DEE5] rounded-[4px] p-4 space-y-1.5">
                <div className="text-xs font-semibold text-[#1F3A5F] tabular-nums">Adım 1</div>
                <div className="text-sm font-semibold text-[#1B2430]">Olay ve Kişi Bilgileri</div>
                <p className="text-xs text-[#566070] leading-relaxed">
                  Kaza tarihi, mağdurun yaşı, cinsiyeti, gelir durumu ve kusur oranı forma girilir.
                </p>
              </div>
              <div className="bg-[#F6F7F9] border border-[#D9DEE5] rounded-[4px] p-4 space-y-1.5">
                <div className="text-xs font-semibold text-[#1F3A5F] tabular-nums">Adım 2</div>
                <div className="text-sm font-semibold text-[#1B2430]">Aktüeryal Hesaplama</div>
                <p className="text-xs text-[#566070] leading-relaxed">
                  TRH-2010 bakiye ömür tablosu ve yerleşik Yargıtay formülleriyle zarar kalemleri
                  hesaplanır.
                </p>
              </div>
              <div className="bg-[#F6F7F9] border border-[#D9DEE5] rounded-[4px] p-4 space-y-1.5">
                <div className="text-xs font-semibold text-[#1F3A5F] tabular-nums">Adım 3</div>
                <div className="text-sm font-semibold text-[#1B2430]">Kalem Dökümü ve Özet</div>
                <p className="text-xs text-[#566070] leading-relaxed">
                  Tazminat kalemleri, harç tutarları ve yasal dayanaklar tablo halinde görüntülenir.
                </p>
              </div>
            </div>
          </section>

          {/* Kapsam ve Sınırlar */}
          <section className="bg-[#F6F7F9] border border-[#D9DEE5] rounded-[4px] p-5 space-y-2.5">
            <h2 className="font-serif-heading text-base text-[#1B2430]">Kapsam ve sınırlar</h2>
            <ul className="list-disc pl-5 space-y-1.5 text-xs sm:text-sm text-[#566070] leading-relaxed">
              <li>
                Bu araç yalnızca <strong className="text-[#1B2430] font-medium">yaralanmalı (bedensel zarar)</strong> trafik kazaları için ön hesaplama yapar; <strong className="text-[#1B2430] font-medium">ölümlü kazalar ve destekten yoksun kalma tazminatı</strong> kapsam dışındadır.
              </li>
              <li>
                Sistem <strong className="text-[#1B2430] font-medium">dava açma tavsiyesi veya kazanma olasılığı üretmez</strong>; sonuçlar resmi bilirkişi raporu yerine geçmez.
              </li>
              <li>
                Boş bırakılan alanlar için sistem tarafından gizli varsayılan değer atanmaz; eksik
                veriler hesaplama özetinde uyarı olarak listelenir.
              </li>
            </ul>
          </section>
        </main>
      )}

      {/* EKRAN 2 & 3: FORM VE SONUÇ RAPORU */}
      {currentView === 'calculator' && (
        <main className="flex-1 max-w-5xl mx-auto w-full px-4 sm:px-6 py-8 space-y-10 print-container">
          {/* FORM BÖLÜMÜ (4 Başlıklı Yapı) */}
          <section className="space-y-6 no-print">
            <div className="border-b border-[#D9DEE5] pb-3">
              <h1 className="font-serif-heading text-xl text-[#1B2430]">
                Hesaplama Parametreleri
              </h1>
              <p className="text-xs text-[#566070] mt-1">
                Bilinen verileri ilgili alanlara giriniz. Boş bırakılan alanlar varsayılan değerle
                doldurulmaz.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Bölüm 1: Kaza */}
              <fieldset className="bg-[#F6F7F9] border border-[#D9DEE5] rounded-[4px] p-5 space-y-4">
                <legend className="px-2 font-serif-heading text-base text-[#1B2430]">
                  1. Kaza Bilgileri
                </legend>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                  <div>
                    <label
                      htmlFor="accident_date"
                      className="block text-sm font-medium text-[#1B2430]"
                    >
                      Kaza tarihi
                    </label>
                    <p className="text-xs text-[#566070] mt-0.5 mb-1.5">
                      Olayın meydana geldiği tarih (asgari ücret ve dönem hesabı için kullanılır).
                    </p>
                    <input
                      id="accident_date"
                      type="date"
                      name="accident_date"
                      value={formData.accident_date}
                      onChange={handleChange}
                      className="w-full bg-[#FFFFFF] border border-[#D9DEE5] rounded-[4px] px-3 py-2 text-sm text-[#1B2430] focus:outline-none focus:border-[#1F3A5F] tabular-nums"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="accident_type"
                      className="block text-sm font-medium text-[#1B2430]"
                    >
                      Kaza oluş türü
                    </label>
                    <p className="text-xs text-[#566070] mt-0.5 mb-1.5">
                      Kaza tespit tutanağındaki temel çarpışma veya olay sınıfı.
                    </p>
                    <select
                      id="accident_type"
                      name="accident_type"
                      value={formData.accident_type}
                      onChange={handleChange}
                      className="w-full bg-[#FFFFFF] border border-[#D9DEE5] rounded-[4px] px-3 py-2 text-sm text-[#1B2430] focus:outline-none focus:border-[#1F3A5F]"
                    >
                      <option value="">Seçiniz</option>
                      <option value="carpisma">Araçların Çarpışması</option>
                      <option value="yaya_carpmasi">Yayaya Çarpma</option>
                      <option value="tek_tarafli">Tek Taraflı Kaza</option>
                      <option value="park_halindeki_arac">Park Halindeki Araca Çarpma</option>
                      <option value="diger">Diğer</option>
                    </select>
                  </div>
                </div>
              </fieldset>

              {/* Bölüm 2: Kişi ve Gelir */}
              <fieldset className="bg-[#F6F7F9] border border-[#D9DEE5] rounded-[4px] p-5 space-y-4">
                <legend className="px-2 font-serif-heading text-base text-[#1B2430]">
                  2. Kişi ve Gelir Bilgileri
                </legend>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                  <div>
                    <label htmlFor="age" className="block text-sm font-medium text-[#1B2430]">
                      Kaza tarihindeki yaş
                    </label>
                    <p className="text-xs text-[#566070] mt-0.5 mb-1.5">
                      TRH-2010 bakiye ömür ve aktif/pasif devre süresi için tam yıl.
                    </p>
                    <input
                      id="age"
                      type="number"
                      name="age"
                      min="0"
                      max="120"
                      value={formData.age}
                      onChange={handleChange}
                      className="w-full bg-[#FFFFFF] border border-[#D9DEE5] rounded-[4px] px-3 py-2 text-sm text-[#1B2430] focus:outline-none focus:border-[#1F3A5F] tabular-nums"
                    />
                  </div>

                  <div>
                    <label htmlFor="gender" className="block text-sm font-medium text-[#1B2430]">
                      Cinsiyet
                    </label>
                    <p className="text-xs text-[#566070] mt-0.5 mb-1.5">
                      TRH-2010 kadın ve erkek yaşam süresi katsayıları farklıdır.
                    </p>
                    <select
                      id="gender"
                      name="gender"
                      value={formData.gender}
                      onChange={handleChange}
                      className="w-full bg-[#FFFFFF] border border-[#D9DEE5] rounded-[4px] px-3 py-2 text-sm text-[#1B2430] focus:outline-none focus:border-[#1F3A5F]"
                    >
                      <option value="">Seçiniz</option>
                      <option value="E">Erkek</option>
                      <option value="K">Kadın</option>
                    </select>
                  </div>

                  <div>
                    <label
                      htmlFor="monthly_income"
                      className="block text-sm font-medium text-[#1B2430]"
                    >
                      Aylık gelir (TL)
                    </label>
                    <p className="text-xs text-[#566070] mt-0.5 mb-1.5">
                      Belgelenebilir aylık kazanç tutarı. Belirtilmezse uyarı verilir.
                    </p>
                    <input
                      id="monthly_income"
                      type="number"
                      name="monthly_income"
                      min="0"
                      step="0.01"
                      value={formData.monthly_income}
                      onChange={handleChange}
                      className="w-full bg-[#FFFFFF] border border-[#D9DEE5] rounded-[4px] px-3 py-2 text-sm text-[#1B2430] focus:outline-none focus:border-[#1F3A5F] tabular-nums"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="income_basis"
                      className="block text-sm font-medium text-[#1B2430]"
                    >
                      Gelir esası
                    </label>
                    <p className="text-xs text-[#566070] mt-0.5 mb-1.5">
                      Girilen aylık tutarın net veya brüt olma durumu.
                    </p>
                    <select
                      id="income_basis"
                      name="income_basis"
                      value={formData.income_basis}
                      onChange={handleChange}
                      className="w-full bg-[#FFFFFF] border border-[#D9DEE5] rounded-[4px] px-3 py-2 text-sm text-[#1B2430] focus:outline-none focus:border-[#1F3A5F]"
                    >
                      <option value="">Seçiniz</option>
                      <option value="net">Net Gelir</option>
                      <option value="brut">Brüt Gelir</option>
                    </select>
                  </div>
                </div>
              </fieldset>

              {/* Bölüm 3: Yaralanma ve Masraflar */}
              <fieldset className="bg-[#F6F7F9] border border-[#D9DEE5] rounded-[4px] p-5 space-y-4">
                <legend className="px-2 font-serif-heading text-base text-[#1B2430]">
                  3. Yaralanma ve Masraf Bilgileri
                </legend>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
                  <div>
                    <label
                      htmlFor="disability_rate"
                      className="block text-sm font-medium text-[#1B2430]"
                    >
                      Sürekli maluliyet oranı (%)
                    </label>
                    <p className="text-xs text-[#566070] mt-0.5 mb-1.5">
                      Sağlık kurulu raporundaki iş gücü kaybı yüzdesi (0–100).
                    </p>
                    <input
                      id="disability_rate"
                      type="number"
                      name="disability_rate"
                      min="0"
                      max="100"
                      step="0.1"
                      value={formData.disability_rate}
                      onChange={handleChange}
                      className="w-full bg-[#FFFFFF] border border-[#D9DEE5] rounded-[4px] px-3 py-2 text-sm text-[#1B2430] focus:outline-none focus:border-[#1F3A5F] tabular-nums"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="temporary_incapacity_months"
                      className="block text-sm font-medium text-[#1B2430]"
                    >
                      Geçici iş göremezlik (ay)
                    </label>
                    <p className="text-xs text-[#566070] mt-0.5 mb-1.5">
                      İyileşme süresince çalışılamayan toplam ay sayısı.
                    </p>
                    <input
                      id="temporary_incapacity_months"
                      type="number"
                      name="temporary_incapacity_months"
                      min="0"
                      max="120"
                      step="0.5"
                      value={formData.temporary_incapacity_months}
                      onChange={handleChange}
                      className="w-full bg-[#FFFFFF] border border-[#D9DEE5] rounded-[4px] px-3 py-2 text-sm text-[#1B2430] focus:outline-none focus:border-[#1F3A5F] tabular-nums"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="non_pecuniary_claim"
                      className="block text-sm font-medium text-[#1B2430]"
                    >
                      Manevi tazminat talebi (TL)
                    </label>
                    <p className="text-xs text-[#566070] mt-0.5 mb-1.5">
                      Varsa talep edilen manevi tazminat tutarı (opsiyonel).
                    </p>
                    <input
                      id="non_pecuniary_claim"
                      type="number"
                      name="non_pecuniary_claim"
                      min="0"
                      step="0.01"
                      value={formData.non_pecuniary_claim}
                      onChange={handleChange}
                      className="w-full bg-[#FFFFFF] border border-[#D9DEE5] rounded-[4px] px-3 py-2 text-sm text-[#1B2430] focus:outline-none focus:border-[#1F3A5F] tabular-nums"
                    />
                  </div>
                </div>
              </fieldset>

              {/* Bölüm 4: Kusur ve Poliçe */}
              <fieldset className="bg-[#F6F7F9] border border-[#D9DEE5] rounded-[4px] p-5 space-y-4">
                <legend className="px-2 font-serif-heading text-base text-[#1B2430]">
                  4. Kusur ve Konum Bilgileri
                </legend>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
                  <div>
                    <label
                      htmlFor="victim_role"
                      className="block text-sm font-medium text-[#1B2430]"
                    >
                      Kazadaki sıfat / konum
                    </label>
                    <p className="text-xs text-[#566070] mt-0.5 mb-1.5">
                      Zarar görenin olay anındaki konumu (sürücü, yolcu, yaya).
                    </p>
                    <select
                      id="victim_role"
                      name="victim_role"
                      value={formData.victim_role}
                      onChange={handleChange}
                      className="w-full bg-[#FFFFFF] border border-[#D9DEE5] rounded-[4px] px-3 py-2 text-sm text-[#1B2430] focus:outline-none focus:border-[#1F3A5F]"
                    >
                      <option value="">Seçiniz</option>
                      <option value="surucu">Sürücü</option>
                      <option value="yolcu">Yolcu (Araç İçi)</option>
                      <option value="yaya">Yaya</option>
                    </select>
                  </div>

                  <div>
                    <label
                      htmlFor="plaintiff_fault"
                      className="block text-sm font-medium text-[#1B2430]"
                    >
                      Davacı kusur oranı (%)
                    </label>
                    <p className="text-xs text-[#566070] mt-0.5 mb-1.5">
                      Zarar görenin kazadaki kendi kusur yüzdesi (0–100).
                    </p>
                    <input
                      id="plaintiff_fault"
                      type="number"
                      name="plaintiff_fault"
                      min="0"
                      max="100"
                      step="1"
                      value={formData.plaintiff_fault}
                      onChange={handleChange}
                      className="w-full bg-[#FFFFFF] border border-[#D9DEE5] rounded-[4px] px-3 py-2 text-sm text-[#1B2430] focus:outline-none focus:border-[#1F3A5F] tabular-nums"
                    />
                  </div>

                  {formData.victim_role !== 'yaya' && (
                    <div>
                      <label
                        htmlFor="seatbelt_or_helmet"
                        className="block text-sm font-medium text-[#1B2430]"
                      >
                        Emniyet kemeri / kask
                      </label>
                      <p className="text-xs text-[#566070] mt-0.5 mb-1.5">
                        Kaza sırasında koruyucu ekipman kullanımı bilgisi.
                      </p>
                      <select
                        id="seatbelt_or_helmet"
                        name="seatbelt_or_helmet"
                        value={formData.seatbelt_or_helmet}
                        onChange={handleChange}
                        className="w-full bg-[#FFFFFF] border border-[#D9DEE5] rounded-[4px] px-3 py-2 text-sm text-[#1B2430] focus:outline-none focus:border-[#1F3A5F]"
                      >
                        <option value="">Belirtilmedi</option>
                        <option value="true">Takılıydı</option>
                        <option value="false">Takılı Değildi</option>
                      </select>
                    </div>
                  )}
                </div>
              </fieldset>

              <div className="flex items-center justify-end pt-1">
                <button
                  type="submit"
                  disabled={loading}
                  className="px-6 py-2.5 text-sm font-medium text-[#FFFFFF] bg-[#1F3A5F] hover:bg-[#172C49] disabled:opacity-50 rounded-[4px] transition-colors cursor-pointer"
                >
                  {loading ? 'Hesaplanıyor...' : 'Tazminat Hesapla'}
                </button>
              </div>
            </form>
          </section>

          {/* HATA MESAJI */}
          {error && (
            <div className="bg-[#FFF6E5] border border-[#D9DEE5] rounded-[4px] p-4 text-sm text-[#4A3500] no-print">
              <strong className="font-semibold">İşlem Hatası:</strong> {error}
            </div>
          )}

          {/* SONUÇ RAPORU BÖLÜMÜ (Rapor Düzeni) */}
          {result && comp && (
            <section className="space-y-8 pt-4 border-t border-[#D9DEE5]">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 no-print">
                <div>
                  <h2 className="font-serif-heading text-xl text-[#1B2430]">
                    Hesaplama Sonuç Raporu
                  </h2>
                  <p className="text-xs text-[#566070] mt-0.5">
                    Aşağıdaki döküm girilen parametrelere göre oluşturulan ön hesaplama özetidir.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handlePrint}
                  className="px-4 py-2 text-xs font-medium text-[#1F3A5F] bg-[#F6F7F9] hover:bg-[#EBEEF3] border border-[#D9DEE5] rounded-[4px] transition-colors cursor-pointer self-start sm:self-auto"
                >
                  Hesaplama özeti (PDF)
                </button>
              </div>

              {/* 1. Eksik / Varsayılan Bilgi Uyarıları (Yalnızca Sarı Ton) */}
              {warnings.length > 0 && (
                <div className="bg-[#FFF6E5] border border-[#E6C88A] rounded-[4px] p-4 space-y-2 text-[#4A3500] print-block">
                  <h3 className="font-serif-heading text-sm text-[#4A3500]">
                    1. Eksik veya Varsayılan Bilgi Uyarıları
                  </h3>
                  <ul className="list-disc pl-5 space-y-1 text-xs leading-relaxed">
                    {warnings.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* 2. Girdi Özeti */}
              <div className="space-y-2.5 print-block">
                <h3 className="font-serif-heading text-base text-[#1B2430]">
                  {warnings.length > 0 ? '2. Girdi Özeti' : '1. Girdi Özeti'}
                </h3>
                <div className="bg-[#F6F7F9] border border-[#D9DEE5] rounded-[4px] p-4">
                  <dl className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-3 text-xs">
                    <div>
                      <dt className="text-[#566070]">Kaza Tarihi</dt>
                      <dd className="font-medium text-[#1B2430] mt-0.5 tabular-nums">
                        {formatDateTR(caseSummary.accident_date)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[#566070]">Kaza Türü</dt>
                      <dd className="font-medium text-[#1B2430] mt-0.5">
                        {ACCIDENT_TYPE_LABELS[caseSummary.accident_type] || 'Belirtilmedi'}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[#566070]">Kazadaki Konum</dt>
                      <dd className="font-medium text-[#1B2430] mt-0.5">
                        {VICTIM_ROLE_LABELS[caseSummary.victim_role] || 'Belirtilmedi'}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[#566070]">Yaş / Cinsiyet</dt>
                      <dd className="font-medium text-[#1B2430] mt-0.5 tabular-nums">
                        {caseSummary.age !== null && caseSummary.age !== undefined
                          ? `${caseSummary.age} yaş`
                          : 'Belirtilmedi'}{' '}
                        /{' '}
                        {GENDER_LABELS[caseSummary.gender] || 'Belirtilmedi'}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[#566070]">Aylık Gelir</dt>
                      <dd className="font-medium text-[#1B2430] mt-0.5 tabular-nums">
                        {caseSummary.monthly_income !== null
                          ? `${formatCurrencyTR(caseSummary.monthly_income)} (${
                              INCOME_BASIS_LABELS[caseSummary.income_basis] || 'Belirtilmedi'
                            })`
                          : 'Belirtilmedi'}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[#566070]">Maluliyet Oranı</dt>
                      <dd className="font-medium text-[#1B2430] mt-0.5 tabular-nums">
                        {caseSummary.disability_rate !== null
                          ? `%${(Number(caseSummary.disability_rate) * 100).toLocaleString('tr-TR')}`
                          : 'Belirtilmedi'}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[#566070]">Geçici İş Göremezlik</dt>
                      <dd className="font-medium text-[#1B2430] mt-0.5 tabular-nums">
                        {caseSummary.temporary_incapacity_months !== null
                          ? `${Number(caseSummary.temporary_incapacity_months).toLocaleString('tr-TR')} ay`
                          : 'Belirtilmedi'}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[#566070]">Davacı Kusur Oranı</dt>
                      <dd className="font-medium text-[#1B2430] mt-0.5 tabular-nums">
                        {caseSummary.plaintiff_fault !== null
                          ? `%${(Number(caseSummary.plaintiff_fault) * 100).toLocaleString('tr-TR')}`
                          : 'Belirtilmedi'}
                      </dd>
                    </div>
                  </dl>
                </div>
              </div>

              {/* 3. Kalem Kalem Tutar Tablosu */}
              <div className="space-y-2.5 print-block">
                <h3 className="font-serif-heading text-base text-[#1B2430]">
                  {warnings.length > 0 ? '3. Kalem Kalem Tazminat Tablosu' : '2. Kalem Kalem Tazminat Tablosu'}
                </h3>
                <div className="overflow-x-auto border border-[#D9DEE5] rounded-[4px]">
                  <table className="w-full text-left border-collapse text-xs sm:text-sm">
                    <thead>
                      <tr className="bg-[#F6F7F9] border-b border-[#D9DEE5] text-[#1B2430]">
                        <th className="py-2.5 px-4 font-semibold">Zarar Kalemi</th>
                        <th className="py-2.5 px-4 font-semibold">Hukuki / Aktüeryal Dayanak</th>
                        <th className="py-2.5 px-4 font-semibold text-right">Hesaplanan Tutar</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#D9DEE5]">
                      <tr>
                        <td className="py-3 px-4 font-medium text-[#1B2430]">
                          Sürekli İş Göremezlik (Kalıcı Maluliyet)
                        </td>
                        <td className="py-3 px-4 text-xs text-[#566070]">
                          TBK m. 54/3, TRH-2010 Yaşam Tablosu, Progresif Rant (%10 artış / %10 iskonto)
                        </td>
                        <td className="py-3 px-4 text-right font-medium text-[#1B2430] tabular-nums">
                          {formatCurrencyTR(comp.items?.permanent_disability?.amount || 0)}
                        </td>
                      </tr>
                      <tr>
                        <td className="py-3 px-4 font-medium text-[#1B2430]">
                          Geçici İş Göremezlik Tazminatı
                        </td>
                        <td className="py-3 px-4 text-xs text-[#566070]">
                          TBK m. 54/2, Tedavi ve İyileşme Süresi Gelir Kaybı Esası
                        </td>
                        <td className="py-3 px-4 text-right font-medium text-[#1B2430] tabular-nums">
                          {formatCurrencyTR(comp.items?.temporary_disability?.amount || 0)}
                        </td>
                      </tr>
                      {caseSummary.non_pecuniary_claim !== null &&
                        Number(caseSummary.non_pecuniary_claim) > 0 && (
                          <tr>
                            <td className="py-3 px-4 font-medium text-[#1B2430]">
                              Manevi Tazminat Talebi (Kullanıcı Beyanı)
                            </td>
                            <td className="py-3 px-4 text-xs text-[#566070]">
                              TBK m. 56 (Hâkimin takdir yetkisine tabidir; aktüeryal hesaba dahil değildir)
                            </td>
                            <td className="py-3 px-4 text-right font-medium text-[#566070] tabular-nums">
                              {formatCurrencyTR(caseSummary.non_pecuniary_claim)}
                            </td>
                          </tr>
                        )}
                      <tr className="bg-[#F6F7F9] font-semibold text-[#1B2430]">
                        <td className="py-3 px-4" colSpan={2}>
                          Toplam Hesaplanan Net Maddi Tazminat
                        </td>
                        <td className="py-3 px-4 text-right text-[#1F3A5F] tabular-nums">
                          {formatCurrencyTR(comp.net_total || 0)}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* 4. Dava Masrafları */}
              {costs && (
                <div className="space-y-2.5 print-block">
                  <h3 className="font-serif-heading text-base text-[#1B2430]">
                    {warnings.length > 0 ? '4. Yargılama Giderleri ve Harçlar' : '3. Yargılama Giderleri ve Harçlar'}
                  </h3>
                  <div className="overflow-x-auto border border-[#D9DEE5] rounded-[4px]">
                    <table className="w-full text-left border-collapse text-xs sm:text-sm">
                      <thead>
                        <tr className="bg-[#F6F7F9] border-b border-[#D9DEE5] text-[#1B2430]">
                          <th className="py-2.5 px-4 font-semibold">Gider Kalemi</th>
                          <th className="py-2.5 px-4 font-semibold">Dayanak</th>
                          <th className="py-2.5 px-4 font-semibold text-right">Tutar</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#D9DEE5]">
                        <tr>
                          <td className="py-2.5 px-4 text-[#1B2430]">Başvurma Harcı</td>
                          <td className="py-2.5 px-4 text-xs text-[#566070]">
                            492 sayılı Harçlar Kanunu Tarifesi
                          </td>
                          <td className="py-2.5 px-4 text-right tabular-nums">
                            {formatCurrencyTR(costs.basvurma_harci)}
                          </td>
                        </tr>
                        <tr>
                          <td className="py-2.5 px-4 text-[#1B2430]">Peşin Karar ve İlam Harcı</td>
                          <td className="py-2.5 px-4 text-xs text-[#566070]">
                            Nispi Harç Oranı (Binde 68,31'in 1/4'ü)
                          </td>
                          <td className="py-2.5 px-4 text-right tabular-nums">
                            {formatCurrencyTR(costs.pesin_harc)}
                          </td>
                        </tr>
                        <tr className="bg-[#F6F7F9] font-semibold">
                          <td className="py-2.5 px-4 text-[#1B2430]" colSpan={2}>
                            Toplam Başlangıç Harç Tutarı
                          </td>
                          <td className="py-2.5 px-4 text-right text-[#1B2430] tabular-nums">
                            {formatCurrencyTR(costs.total_upfront_costs)}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* 5. Emsal Kararlar */}
              <div className="space-y-2.5 print-block">
                <h3 className="font-serif-heading text-base text-[#1B2430]">
                  {warnings.length > 0 ? '5. Emsal Yargıtay Kararları' : '4. Emsal Yargıtay Kararları'}
                </h3>
                {result?.precedent_citations && result.precedent_citations.length > 0 ? (
                  <div className="space-y-3">
                    {result.precedent_citations.map((item, idx) => (
                      <div
                        key={idx}
                        className="bg-[#F6F7F9] border border-[#D9DEE5] rounded-[4px] p-4 space-y-1.5"
                      >
                        <div className="text-xs font-semibold text-[#1B2430]">
                          {item.court} — {item.case_no} ({formatDateTR(item.date)})
                        </div>
                        <p className="text-xs text-[#566070] leading-relaxed">{item.summary}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="bg-[#F6F7F9] border border-[#D9DEE5] rounded-[4px] p-4 text-xs text-[#566070]">
                    Emsal karar analizi henüz bağlı değildir. Dava risk ve kazanma olasılığı
                    hesaplaması emsal veri tabanı entegrasyonu sonrasında eklenecektir.
                  </div>
                )}
              </div>

              {/* 6. Hesabın Dayanakları ve Yasal Uyarı */}
              <div className="space-y-2.5 print-block">
                <h3 className="font-serif-heading text-base text-[#1B2430]">
                  {warnings.length > 0 ? '6. Hesabın Dayanakları ve Hukuki Çerçeve' : '5. Hesabın Dayanakları ve Hukuki Çerçeve'}
                </h3>
                <div className="bg-[#F6F7F9] border border-[#D9DEE5] rounded-[4px] p-4 text-xs text-[#566070] leading-relaxed space-y-2">
                  <p>
                    <strong className="text-[#1B2430] font-medium">Mevzuat ve Tablo Esası:</strong>{' '}
                    Hesaplamada 6098 sayılı Türk Borçlar Kanunu'nun 54. maddesi, 2918 sayılı
                    Karayolları Trafik Kanunu hükümleri, TRH-2010 Ulusal Mortalite Tablosu ve
                    Yargıtay Hukuk Genel Kurulu'nun yerleşik progresif rant (%10 artırım / %10
                    iskonto) yöntemi esas alınmıştır.
                  </p>
                  <p>
                    <strong className="text-[#1B2430] font-medium">Bilgilendirme Niteliği:</strong>{' '}
                    Bu döküm yalnızca girilen beyan verilerine dayalı teknik bir ön hesaplama
                    özetidir; kesin hüküm veya resmî adli bilirkişi raporu niteliği taşımaz. Nihai
                    tazminat tutarı yargılama sürecinde alınacak kusur ve sağlık kurulu raporlarıyla
                    belirlenir.
                  </p>
                </div>
              </div>
            </section>
          )}
        </main>
      )}
    </div>
  );
}