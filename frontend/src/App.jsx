import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Calculator, 
  AlertTriangle, 
  CheckCircle2, 
  Scale, 
  Coins, 
  User, 
  Calendar, 
  Percent, 
  Briefcase, 
  TrendingUp, 
  Sparkles, 
  BookOpen, 
  ExternalLink, 
  Printer, 
  ShieldCheck, 
  Car,
  ArrowRight,
  ShieldAlert,
  FileCheck,
  ChevronLeft
} from 'lucide-react';

const API_BASE_URL = 'http://127.0.0.1:8000';

export default function App() {
  const [currentView, setCurrentView] = useState('landing'); // 'landing' | 'calculator'

  useEffect(() => {
    document.title = "Trafik RAG";
  }, []);

  const [formData, setFormData] = useState({
    accident_type: 'kavsak_ihlali',
    victim_role: 'surucu',
    seatbelt_or_helmet: true,
    non_pecuniary_claim: 50000,
    age: 30,
    gender: 'E',
    disability_rate: 15,
    monthly_income: 35000,
    income_basis: 'net',
    plaintiff_fault: 0,
    temporary_incapacity_months: 3,
    accident_date: new Date().toISOString().split('T')[0],
  });

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    
    // Yaya seçilirse kemer/kask kısıtlamasını otomatik true yap
    if (name === 'victim_role' && value === 'yaya') {
      setFormData((prev) => ({
        ...prev,
        victim_role: value,
        seatbelt_or_helmet: true,
      }));
      return;
    }

    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : (type === 'number' ? (value === '' ? '' : Number(value)) : value),
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const payload = {
      ...formData,
      seatbelt_or_helmet: formData.victim_role === 'yaya' ? true : formData.seatbelt_or_helmet,
      age: Number(formData.age),
      monthly_income: Number(formData.monthly_income),
      non_pecuniary_claim: Number(formData.non_pecuniary_claim || 0),
      disability_rate: Number(formData.disability_rate) / 100,
      plaintiff_fault: Number(formData.plaintiff_fault) / 100,
      temporary_incapacity_months: Number(formData.temporary_incapacity_months),
    };

    try {
      const response = await axios.post(`${API_BASE_URL}/api/analyze/`, payload);
      setResult(response.data);
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail || 
        'Hesaplama servisine bağlanırken bir sorun oluştu. Lütfen bağlantınızı kontrol edin.'
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
  const risk = result?.calculation_results?.risk;
  const warnings = result?.calculation_results?.warnings || [];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans print:bg-white print:text-black">
      {/* Özel Print/PDF Stilleri */}
      <style>{`
        @media print {
          body {
            background-color: #ffffff !important;
            color: #000000 !important;
          }
          .no-print {
            display: none !important;
          }
          .print-full {
            width: 100% !important;
            max-width: 100% !important;
            grid-column: span 12 / span 12 !important;
          }
          .print-card {
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            color: #000000 !important;
            box-shadow: none !important;
            page-break-inside: avoid;
          }
          .print-text-dark {
            color: #0f172a !important;
          }
          .print-text-muted {
            color: #475569 !important;
          }
          .print-badge {
            background: #f1f5f9 !important;
            color: #0f172a !important;
            border: 1px solid #94a3b8 !important;
          }
        }
          @keyframes pulseGlow {
          0%, 100% { opacity: 0.4; transform: scale(1); }
          50% { opacity: 0.7; transform: scale(1.05); }
        }
        @keyframes floatSlow {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-8px); }
        }
        .animate-pulse-glow {
          animation: pulseGlow 6s ease-in-out infinite;
        }
        .animate-float {
          animation: floatSlow 5s ease-in-out infinite;
        }
        .landing-fade-in {
          animation: fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(16px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* Header - Kurumsal ve Sade */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur sticky top-0 z-50 no-print">
        {/* Yalnızca Hesaplama Ekranındayken Sol Üstte Çıkan Zarif Geri Dönüş Butonu */}
      {currentView === 'calculator' && (
        <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 no-print">
          <button
            onClick={() => setCurrentView('landing')}
            className="inline-flex items-center space-x-2 text-xs font-medium text-slate-400 hover:text-white bg-slate-900/80 hover:bg-slate-800 border border-slate-800 px-3.5 py-2 rounded-lg transition-colors cursor-pointer"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Ana Sayfa</span>
          </button>
        </div>
      )}
      </header>

      {/* Yazdırıldığında Gözüken Başlık */}
      <div className="hidden print:block p-6 border-b border-slate-300 mb-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-900 uppercase tracking-tight">
              Trafik Kazası Tazminat ve Dava Risk Sistemi
            </h1>
            <p className="text-xs text-slate-600 mt-0.5">
              Aktüeryal Tazminat & Hukuki Risk Ön Analiz Raporu
            </p>
          </div>
          <div className="text-right text-xs text-slate-500 font-mono">
            <div>Tarih: {new Date().toLocaleDateString('tr-TR')}</div>
            <div>Mevzuat: TRH-2010 / KTK 97</div>
          </div>
        </div>
      </div>

      {/* GÖRÜNÜM 1: DÜZELTİLMİŞ (FERAH MOBİL UYUMLU) GİRİŞ SAYFASI */}
      {currentView === 'landing' && (
        <div className="relative flex-1 flex flex-col justify-start sm:justify-center items-center px-6 sm:px-8 pt-16 sm:pt-20 pb-24 max-w-5xl mx-auto text-center space-y-12 sm:space-y-16 no-print landing-fade-in">
          
          {/* Arka Plan Ortam Işıkları (Glow) - Mobilde küçültüldü */}
          <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] sm:w-[500px] h-[250px] sm:h-[300px] bg-gradient-to-tr from-emerald-600/20 via-teal-500/10 to-indigo-600/25 blur-[90px] sm:blur-[120px] pointer-events-none rounded-full animate-pulse-glow -z-10" />

          {/* Hero Başlık ve Rozet (Araları açıldı) */}
          <div className="space-y-7 sm:space-y-8 max-w-3xl relative pt-4">
            
            {/* Rozet (Mobilde daha zarif) */}
            <div className="inline-flex items-center space-x-2 px-4 py-2 rounded-full text-[10px] sm:text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 backdrop-blur-md shadow-[0_0_20px_-3px_rgba(16,185,129,0.3)] hover:border-emerald-400/50 transition-all cursor-default animate-float">
              <span className="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full bg-emerald-400 animate-ping" />
              <span>Yargıtay İçtihatları ve 2026 Aktüerya Standartları</span>
            </div>

            {/* Başlık (Mobilde daha dengeli kırılım) */}
            <h2 className="text-3xl sm:text-5xl lg:text-6xl font-black tracking-tight text-white leading-[1.35] sm:leading-[1.25] px-2 sm:px-0">
              Trafik Kazası Tazminatınızı ve <br className="hidden sm:block" />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-200 to-indigo-400 drop-shadow-[0_0_35px_rgba(16,185,129,0.25)]">
                Dava Açma Riskinizi
              </span>
              <br />
              Saniyeler İçinde Görün
            </h2>

            {/* Paragraf (Kenar boşlukları eklenerek nefes aldırıldı) */}
            <p className="text-sm sm:text-base text-slate-300/90 max-w-2xl mx-auto leading-relaxed px-4 sm:px-0">
              Resmi <strong className="text-slate-100 font-semibold">TRH-2010</strong> yaşam tablolarıyla bakiye ömürdeki alacağınızı kuruşu kuruşuna hesaplayın; harçlar ve karşı vekâlet risklerini <strong className="text-emerald-400 font-semibold">Net Beklenen Değer (EV)</strong> karnesiyle anında görün.
            </p>
          </div>

          {/* Aksiyon Butonu (Mobilde tek satır ve orantılı) */}
          <div className="relative group pt-2 w-full sm:w-auto px-4 sm:px-0">
            <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500 via-teal-500 to-indigo-600 rounded-2xl blur-md sm:blur-lg opacity-40 group-hover:opacity-85 transition duration-500 group-hover:duration-200" />
            
            <button
              onClick={() => setCurrentView('calculator')}
              className="relative w-full sm:w-auto flex justify-center items-center space-x-3 px-4 sm:px-8 py-4 rounded-xl text-[13px] sm:text-base font-bold bg-slate-900 border border-emerald-500/40 text-white shadow-2xl group-hover:bg-gradient-to-r group-hover:from-emerald-500 group-hover:to-indigo-600 group-hover:border-transparent transition-all duration-300 transform group-hover:-translate-y-0.5 cursor-pointer"
            >
              <div className="w-8 h-8 rounded-lg bg-emerald-500/20 group-hover:bg-white/20 flex items-center justify-center transition-colors shrink-0">
                <Calculator className="w-4 h-4 text-emerald-400 group-hover:text-white" />
              </div>
              <span className="whitespace-nowrap">Tazminat & Risk Analizine Başla</span>
              <ArrowRight className="w-4 h-4 sm:w-5 sm:h-5 ml-0.5 transition-transform duration-300 group-hover:translate-x-1.5 shrink-0" />
            </button>
            <p className="text-[10px] sm:text-[11px] text-slate-400 mt-4 font-medium tracking-wide">
              Kayıt gerektirmez • Ücretsiz • Doğrudan hesaplama
            </p>
          </div>

          {/* 3 Cam Görünümlü Kart */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full text-left pt-4 px-2 sm:px-0">
            
            {/* Kart 1: Aktüerya */}
            <div className="group relative bg-slate-900/40 hover:bg-slate-900/80 backdrop-blur-xl border border-slate-800/80 hover:border-indigo-500/50 rounded-2xl p-6 transition-all duration-300 hover:-translate-y-1.5 hover:shadow-[0_15px_30px_-10px_rgba(99,102,241,0.2)]">
              <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-4 group-hover:scale-110 group-hover:bg-indigo-500/20 transition-all">
                <FileCheck className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-bold text-slate-100 group-hover:text-indigo-300 transition-colors">
                Deterministik Aktüerya
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed mt-1.5">
                TRH-2010 tablosu, aktif/pasif devre ve progresif rant formülleriyle sapmasız net tazminat hesabı.
              </p>
            </div>

            {/* Kart 2: Risk / Getiri */}
            <div className="group relative bg-slate-900/40 hover:bg-slate-900/80 backdrop-blur-xl border border-slate-800/80 hover:border-emerald-500/50 rounded-2xl p-6 transition-all duration-300 hover:-translate-y-1.5 hover:shadow-[0_15px_30px_-10px_rgba(16,185,129,0.2)]">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-4 group-hover:scale-110 group-hover:bg-emerald-500/20 transition-all">
                <TrendingUp className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-bold text-slate-100 group-hover:text-emerald-300 transition-colors">
                Dava Açmaya Değer mi?
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed mt-1.5">
                2026 mahkeme harçları ve olası karşı vekâlet ücretini kazançla tartıp net tavsiye üreten risk karnesi.
              </p>
            </div>

            {/* Kart 3: Resmi PDF Rapor Çıktısı */}
            <div className="group relative bg-slate-900/40 hover:bg-slate-900/80 backdrop-blur-xl border border-slate-800/80 hover:border-amber-500/50 rounded-2xl p-6 transition-all duration-300 hover:-translate-y-1.5 hover:shadow-[0_15px_30px_-10px_rgba(245,158,11,0.2)]">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 mb-4 group-hover:scale-110 group-hover:bg-amber-500/20 transition-all">
                <Printer className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-bold text-slate-100 group-hover:text-amber-300 transition-colors">
                Resmi Bilirkişi PDF Raporu
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed mt-1.5">
                Hesaplama sonucunu avukatınızla veya sigorta şirketiyle doğrudan paylaşabileceğiniz A4 formatında indirin.
              </p>
            </div>

          </div>
        </div>
      )}

      {/* GÖRÜNÜM 2: HESAPLAMA PANELİ */}
      {currentView === 'calculator' && (
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full print:p-0 print:m-0 print:max-w-full">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            
            {/* Sol Kolon: Form */}
            <div className="lg:col-span-5 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-5 no-print">
              <div className="flex items-center space-x-2 border-b border-slate-800 pb-3">
                <Calculator className="w-5 h-5 text-indigo-400" />
                <h2 className="text-base font-semibold text-slate-200">Kaza ve Hukuki Parametreler</h2>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                
                {/* Kaza Oluş Tipi */}
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1 flex items-center gap-1.5">
                    <Car className="w-3.5 h-3.5 text-indigo-400" /> Kaza Oluş Tipi (Emsal Eşleştirme)
                  </label>
                  <select
                    name="accident_type"
                    value={formData.accident_type}
                    onChange={handleChange}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="kavsak_ihlali">Kavşakta Geçiş Önceliği İhlali</option>
                    <option value="kirmizi_isik">Kırmızı Işık İhlali</option>
                    <option value="arkadan_carpma">Trafikte Arkadan Çarpma</option>
                    <option value="yayaya_carpma">Yaya Geçidi / Yayaya Çarpma</option>
                    <option value="serit_ihlali">Hatalı Sollama / Şerit İhlali</option>
                  </select>
                </div>

                {/* Kazadaki Konum & Cinsiyet */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1 flex items-center gap-1.5">
                      <User className="w-3.5 h-3.5 text-slate-500" /> Kazadaki Konum
                    </label>
                    <select
                      name="victim_role"
                      value={formData.victim_role}
                      onChange={handleChange}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                    >
                      <option value="surucu">Sürücü</option>
                      <option value="yolcu">Yolcu (Araç İçi)</option>
                      <option value="yaya">Yaya</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Cinsiyet</label>
                    <select
                      name="gender"
                      value={formData.gender}
                      onChange={handleChange}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                    >
                      <option value="E">Erkek</option>
                      <option value="K">Kadın</option>
                    </select>
                  </div>
                </div>

                {/* Tarih & Yaş */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1 flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-slate-500" /> Kaza Tarihi
                    </label>
                    <input
                      type="date"
                      name="accident_date"
                      value={formData.accident_date}
                      onChange={handleChange}
                      required
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Kaza Anındaki Yaş</label>
                    <input
                      type="number"
                      name="age"
                      min="0"
                      max="100"
                      value={formData.age}
                      onChange={handleChange}
                      required
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                {/* Maluliyet & Kusur */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1 flex items-center gap-1.5">
                      <Percent className="w-3.5 h-3.5 text-slate-500" /> Maluliyet Oranı (%)
                    </label>
                    <input
                      type="number"
                      name="disability_rate"
                      min="0"
                      max="100"
                      step="0.1"
                      value={formData.disability_rate}
                      onChange={handleChange}
                      required
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1 flex items-center gap-1.5">
                      <Percent className="w-3.5 h-3.5 text-slate-500" /> Davacı Kusuru (%)
                    </label>
                    <input
                      type="number"
                      name="plaintiff_fault"
                      min="0"
                      max="100"
                      step="5"
                      value={formData.plaintiff_fault}
                      onChange={handleChange}
                      required
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                {/* Gelir & Türü */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1 flex items-center gap-1.5">
                      <Coins className="w-3.5 h-3.5 text-slate-500" /> Aylık Gelir (TL)
                    </label>
                    <input
                      type="number"
                      name="monthly_income"
                      min="0"
                      step="500"
                      value={formData.monthly_income}
                      onChange={handleChange}
                      required
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1 flex items-center gap-1.5">
                      <Briefcase className="w-3.5 h-3.5 text-slate-500" /> Gelir Türü
                    </label>
                    <select
                      name="income_basis"
                      value={formData.income_basis}
                      onChange={handleChange}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                    >
                      <option value="net">Net Gelir</option>
                      <option value="brut">Brüt Gelir</option>
                    </select>
                  </div>
                </div>

                {/* Geçici İş Göremezlik & Manevi Tazminat */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">
                      İş Göremezlik (Ay)
                    </label>
                    <input
                      type="number"
                      name="temporary_incapacity_months"
                      min="0"
                      max="48"
                      value={formData.temporary_incapacity_months}
                      onChange={handleChange}
                      required
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">
                      Manevi Tazminat (TL)
                    </label>
                    <input
                      type="number"
                      name="non_pecuniary_claim"
                      min="0"
                      step="5000"
                      value={formData.non_pecuniary_claim}
                      onChange={handleChange}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                {/* Müterafik Kusur Onayı - YAYA DEĞİLSE GÖRÜNÜR */}
                {formData.victim_role !== 'yaya' && (
                  <div className="bg-slate-800/40 border border-slate-800 p-3 rounded-lg flex items-center space-x-3 transition-all">
                    <input
                      type="checkbox"
                      id="seatbelt_or_helmet"
                      name="seatbelt_or_helmet"
                      checked={formData.seatbelt_or_helmet}
                      onChange={handleChange}
                      className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 bg-slate-700 border-slate-600 cursor-pointer"
                    />
                    <label htmlFor="seatbelt_or_helmet" className="text-xs text-slate-300 flex items-center gap-1.5 cursor-pointer">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                      Emniyet Kemeri / Kask Takılıydı (Müterafik Kusur Yok)
                    </label>
                  </div>
                )}

                {/* Hesaplama Butonu */}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full mt-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium py-2.5 px-4 rounded-lg transition-colors flex items-center justify-center space-x-2 shadow-lg shadow-indigo-600/20 cursor-pointer"
                >
                  {loading ? (
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>
                      <TrendingUp className="w-4 h-4" />
                      <span>Dava Risk & Tazminat Analizi Yap</span>
                    </>
                  )}
                </button>
              </form>
            </div>

            {/* Sağ Kolon: Sonuç Raporu */}
            <div className="lg:col-span-7 space-y-6 print-full">
              {error && (
                <div className="bg-rose-950/40 border border-rose-800/60 rounded-xl p-4 flex items-start space-x-3 text-rose-200 text-sm no-print">
                  <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="font-semibold text-rose-300">Hesaplama Başarısız</p>
                    <p className="text-xs text-rose-300/80 mt-1">{error}</p>
                  </div>
                </div>
              )}

              {!result && !loading && !error && (
                <div className="bg-slate-900 border border-slate-800 border-dashed rounded-xl p-12 text-center text-slate-500 no-print">
                  <Scale className="w-12 h-12 mx-auto stroke-1 text-slate-600 mb-3" />
                  <h3 className="text-sm font-medium text-slate-300">Henüz Analiz Başlatılmadı</h3>
                  <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
                    Sol paneldeki kaza parametrelerini belirleyip "Dava Risk & Tazminat Analizi Yap" butonuna tıklayın.
                  </p>
                </div>
              )}

              {result && risk && comp && (
                <>
                  {/* PDF İndir / Yazdır Butonu Çubuğu */}
                  <div className="flex items-center justify-between bg-slate-900 border border-slate-800 rounded-xl p-3 px-4 shadow-lg no-print">
                    <div className="flex items-center space-x-2 text-xs text-slate-300">
                      <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                      <span>Analiz hazırlandı. Rapor çıktısını alabilirsiniz.</span>
                    </div>
                    <button
                      onClick={handlePrint}
                      className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-all shadow-md shadow-emerald-900/30 cursor-pointer"
                    >
                      <Printer className="w-3.5 h-3.5" />
                      <span>Raporu PDF Olarak Kaydet / Yazdır</span>
                    </button>
                  </div>

                  {/* 1. DAVA AÇMAYA DEĞER Mİ? KARAR KARNESİ */}
                  <div className="bg-gradient-to-r from-emerald-950/40 via-slate-900 to-indigo-950/30 border border-emerald-500/30 rounded-xl p-6 shadow-2xl relative overflow-hidden print-card">
                    <div className="flex items-center justify-between pb-3 border-b border-slate-800 print:border-slate-300">
                      <span className="text-xs font-bold tracking-wider text-emerald-400 print:text-emerald-700 uppercase flex items-center gap-1.5">
                        <Sparkles className="w-4 h-4 no-print" /> Dava Açmaya Değer mi? (Risk / Getiri Karnesi)
                      </span>
                      <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 print-badge">
                        {risk.recommendation}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4">
                      <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-800 print-card">
                        <span className="text-slate-400 print-text-muted text-xs block">Tahmini Kazanma Şansı</span>
                        <span className="text-2xl font-black text-emerald-400 print:text-emerald-700 mt-1 block">
                          {risk.win_probability}
                        </span>
                      </div>

                      <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-800 print-card">
                        <span className="text-slate-400 print-text-muted text-xs block">Beklenen Değer (EV)</span>
                        <span className="text-2xl font-black text-white print-text-dark mt-1 block">
                          {Number(risk.expected_value).toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL
                        </span>
                      </div>

                      <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-800 print-card">
                        <span className="text-slate-400 print-text-muted text-xs block">Kaybetme Riski (Karşı Vekalet)</span>
                        <span className="text-xl font-bold text-rose-400 print:text-rose-700 mt-1 block">
                          -{Number(risk.estimated_counter_attorney_fee).toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL
                        </span>
                      </div>
                    </div>

                    <div className="mt-4 p-3 bg-emerald-950/30 border border-emerald-800/30 rounded-lg flex items-start space-x-2 text-xs text-emerald-200 print:bg-emerald-50 print:text-emerald-900 print:border-emerald-300">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 print:text-emerald-700 shrink-0 mt-0.5" />
                      <span>{risk.recommendation_note}</span>
                    </div>
                  </div>

                  {/* 2. NET TAZMİNAT TUTARI KARTI */}
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl print-card">
                    <div className="flex items-center justify-between pb-3 border-b border-slate-800 print:border-slate-300">
                      <span className="text-xs font-semibold tracking-wider text-slate-400 print-text-muted uppercase">
                        Talep Edilebilir Net Maddi Tazminat
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 print-badge">
                        {comp.rule_version}
                      </span>
                    </div>
                    <div className="mt-3">
                      <div className="text-3xl font-extrabold tracking-tight text-white print-text-dark">
                        {Number(comp.net_total).toLocaleString('tr-TR', { minimumFractionDigits: 2 })} TL
                      </div>
                      <div className="flex flex-wrap gap-x-4 text-xs text-slate-400 print-text-muted mt-2">
                        <span>Kalıcı Sakatlık: <strong className="text-slate-200 print-text-dark">{Number(comp.items?.permanent_disability?.amount || 0).toLocaleString('tr-TR')} TL</strong></span>
                        <span>Geçici İş Göremezlik: <strong className="text-slate-200 print-text-dark">{Number(comp.items?.temporary_disability?.amount || 0).toLocaleString('tr-TR')} TL</strong></span>
                        {comp.non_pecuniary_claim && (
                          <span>Manevi Talep: <strong className="text-amber-300 print:text-amber-800">{Number(comp.non_pecuniary_claim).toLocaleString('tr-TR')} TL</strong></span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* 3. MASRAFLAR VE AÇILIŞ GİDERLERİ */}
                  {costs && (
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 print-card">
                      <h3 className="text-xs font-bold text-slate-300 print-text-dark uppercase tracking-wider mb-3 flex items-center gap-1.5">
                        <Coins className="w-4 h-4 text-amber-400 no-print" /> Dava Açılış Masrafları ve Harçlar (2026)
                      </h3>
                      <div className="grid grid-cols-3 gap-3 text-xs">
                        <div className="bg-slate-800/40 p-2.5 rounded border border-slate-800 print-card">
                          <span className="text-slate-400 print-text-muted block">Başvurma Harcı</span>
                          <span className="font-semibold text-slate-200 print-text-dark mt-1 block">{costs.basvurma_harci} TL</span>
                        </div>
                        <div className="bg-slate-800/40 p-2.5 rounded border border-slate-800 print-card">
                          <span className="text-slate-400 print-text-muted block">Peşin Karar Harcı</span>
                          <span className="font-semibold text-slate-200 print-text-dark mt-1 block">{costs.pesin_harc} TL</span>
                        </div>
                        <div className="bg-slate-800/40 p-2.5 rounded border border-slate-800 print-card">
                          <span className="text-slate-400 print-text-muted block">Toplam Açılış Masrafı</span>
                          <span className="font-semibold text-amber-300 print:text-amber-800 mt-1 block">{costs.total_upfront_costs} TL</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 4. EMSAL YARGITAY KARARLARI (RAG ATIFLARI) */}
                  {result?.precedent_citations && result.precedent_citations.length > 0 && (
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4 print-card">
                      <div className="flex items-center justify-between pb-3 border-b border-slate-800 print:border-slate-300">
                        <div className="flex items-center space-x-2">
                          <BookOpen className="w-4 h-4 text-indigo-400 no-print" />
                          <h3 className="text-xs font-bold text-slate-200 print-text-dark uppercase tracking-wider">
                            Emsal Yargıtay Kararları (RAG Atıfları)
                          </h3>
                        </div>
                        <span className="text-[11px] text-slate-400 bg-slate-800 px-2.5 py-0.5 rounded-full border border-slate-700 print-badge">
                          {result.precedent_citations.length} Emsal Karar Dayanağı
                        </span>
                      </div>

                      <div className="space-y-3">
                        {result.precedent_citations.map((item, idx) => (
                          <div 
                            key={idx}
                            className="bg-slate-800/40 border border-slate-800/80 rounded-lg p-3.5 space-y-2 print-card"
                          >
                            <div className="flex items-start justify-between">
                              <div>
                                <span className="text-xs font-bold text-indigo-300 print:text-indigo-800 block">
                                  {item.court}
                                </span>
                                <span className="text-[11px] text-slate-400 print-text-muted font-mono">
                                  {item.case_no} • {item.date}
                                </span>
                              </div>
                              <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 print-badge">
                                %{Math.round(item.similarity_score * 100)} Benzerlik
                              </span>
                            </div>

                            <p className="text-xs text-slate-300 print-text-dark leading-relaxed">
                              {item.summary}
                            </p>

                            <div className="pt-1 flex items-center justify-between text-[11px] text-slate-400 print-text-muted border-t border-slate-700/40 print:border-slate-300">
                              <span>
                                <strong className="text-slate-300 print-text-dark">İçtihat Dayanağı:</strong> {item.relevance_point}
                              </span>
                              <span className="text-indigo-400 flex items-center gap-1 no-print">
                                Tam Metin <ExternalLink className="w-3 h-3" />
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 5. YASAL BİLGİLENDİRME VE FERAGATNAME */}
                  <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg space-y-3 print-card">
                    <div className="flex items-center space-x-2 text-amber-400 print:text-amber-800 border-b border-slate-800/80 pb-2.5">
                      <ShieldAlert className="w-4 h-4 shrink-0" />
                      <h4 className="text-xs font-bold uppercase tracking-wider">
                        Önemli Yasal Bilgilendirme ve Feragatname
                      </h4>
                    </div>

                    {warnings.filter(w => !w.toLowerCase().includes('parametre') && !w.toLowerCase().includes('csv') && !w.toLowerCase().includes('teyit')).length > 0 && (
                      <div className="space-y-1.5 pb-2">
                        {warnings
                          .filter(w => !w.toLowerCase().includes('parametre') && !w.toLowerCase().includes('csv') && !w.toLowerCase().includes('teyit'))
                          .map((w, idx) => (
                            <div key={idx} className="flex items-start gap-2 text-xs text-amber-200/90 print-text-dark bg-amber-950/20 border border-amber-800/30 p-2.5 rounded-lg">
                              <span className="text-amber-400">•</span>
                              <span>{w}</span>
                            </div>
                          ))}
                      </div>
                    )}

                    <div className="text-[11px] text-slate-400 print-text-muted leading-relaxed space-y-1.5">
                      <p>
                        • <strong>Bağlayıcılık İçermez:</strong> Bu ekranda sunulan tazminat tutarları, masraf tahminleri ve dava kazanma olasılığı genel aktüeryal formüller ile Yargıtay uygulamaları üzerinden üretilmiş <em>tahmini bir ön değerlendirme simülasyonudur</em>.
                      </p>
                      <p>
                        • <strong>Garanti veya Hukuki Tavsiye Değildir:</strong> Sistemdeki sonuçlar mahkeme nezdinde kesin bir hak veya parasal garanti teşkil etmez; doğrudan avukatlık veya resmi bilirkişi mütalaası niteliğinde değildir.
                      </p>
                      <p>
                        • <strong>Nihai Karar:</strong> Tazminat tutarı ve kusur dağılımı, açılacak davada mahkemece tayin edilecek bilirkişi heyeti ve Adli Tıp Kurumu'nun düzenleyeceği nihai sağlık raporuyla kesinleşecektir.
                      </p>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </main>
      )}
    </div>
  );
}