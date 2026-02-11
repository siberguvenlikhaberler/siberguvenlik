# 📁 SİBER GÜVENLİK HABERLERİ TOPLAYICI - PROJE YAPISI

**Son Güncelleme:** 11 Şubat 2026  
**Durum:** ✅ TEMİZ VE OPTİMİZE EDİLMİŞ

---

## 📊 MEVCUT DOSYALAR

```
/SiberGuvenlikHaberleri/
│
├── 📄 cyber_news_genisletilmis.py  (21 KB)  ⭐ ANA PROGRAM
│   └─ 13 haber kaynağı
│   └─ ExtendedCyberNewsAggregator sınıfı
│   └─ RSS ve Atom feed desteği
│   └─ HTML, JSON, TXT export
│
├── 📄 advanced_news_api.py         (13 KB)  🔑 API VERSİYONU
│   └─ NewsAPI entegrasyonu
│   └─ Anahtar kelime bazlı arama
│   └─ AdvancedCyberNewsAggregator sınıfı
│
├── 📄 auto_scheduler.py            (3 KB)   ⏰ ZAMANLAYICI
│   └─ Günde 2 kez otomatik çalıştırma (09:00, 18:00)
│   └─ cyber_news_genisletilmis.py'yi kullanır
│   └─ schedule modülü gerektirir
│
├── 📄 requirements.txt             (1 KB)   📦 BAĞIMLILIKLAR
│   └─ requests>=2.31.0
│   └─ beautifulsoup4>=4.12.0
│   └─ schedule>=1.2.0
│   └─ lxml>=4.9.0
│
├── 📄 docker-compose.yml           (1 KB)   🐳 DOCKER
│   └─ Container yapılandırması
│
├── 📄 Dockerfile                   (1 KB)   🐳 DOCKER
│   └─ Image yapılandırması
│
├── 📄 README.md                    (7 KB)   📖 DOKÜMANTASYON
│   └─ Kullanım kılavuzu
│   └─ Kurulum talimatları
│
└── 📄 HATA_KONTROL_RAPORU.md       (4 KB)   🔍 TEST RAPORU
    └─ Detaylı analiz ve test sonuçları
```

---

## 🎯 KULLANIM KILAVUZU

### 1️⃣ Ana Program (Önerilen)
```bash
python cyber_news_genisletilmis.py
```
**Ne yapar:**
- 13 kaynaktan haber toplar
- TXT, JSON, HTML rapor oluşturur
- Her kaynaktan 3 haber alır

**Çıktılar:**
- `cyber_news_extended_YYYYMMDD_HHMMSS.txt`
- `cyber_news_extended_YYYYMMDD_HHMMSS.json`
- `cyber_news_extended_YYYYMMDD_HHMMSS.html`

---

### 2️⃣ API Versiyonu
```bash
export NEWSAPI_KEY="your_api_key"
python advanced_news_api.py
```
**Ne yapar:**
- NewsAPI üzerinden arama
- Anahtar kelime bazlı filtreleme
- Son 2 günün haberlerini çeker

**Not:** https://newsapi.org'dan ücretsiz API key gerekir

---

### 3️⃣ Otomatik Zamanlama
```bash
python auto_scheduler.py
```
**Ne yapar:**
- Her gün 09:00 ve 18:00'de otomatik çalışır
- `cyber_news_genisletilmis.py`'yi kullanır
- Arka planda sürekli çalışır

**Gereksinim:** `schedule` modülü yüklü olmalı

---

## 📰 HABER KAYNAKLARI (13 Adet)

### Temel Kaynaklar
1. **The Hacker News** - Güncel siber güvenlik haberleri
2. **BleepingComputer** - Teknik analiz ve detaylar
3. **SecurityWeek** - Kurumsal güvenlik

### Uzman Kaynakları
4. **Krebs on Security** - Derinlemesine araştırmalar
5. **Dark Reading** - Profesyonel içerik
6. **Threatpost** - Tehdit istihbaratı
7. **Graham Cluley** - Uzman yorumları

### Kurumsal Kaynaklar
8. **Security Affairs** - Uluslararası haberler
9. **Naked Security** (Sophos) - Güvenlik blogu
10. **SANS ISC** - İnternet fırtına merkezi
11. **US-CERT** (CISA) - Resmi uyarılar
12. **Recorded Future** - Tehdit istihbaratı
13. **Cyberscoop** - Politika ve teknoloji

---

## 🔧 TEKNİK DETAYLAR

### Sınıf Yapısı
```python
ExtendedCyberNewsAggregator
├── fetch_rss_feed()        # RSS/Atom feed okuma
├── clean_html()            # HTML temizleme
├── aggregate_news()        # Haber toplama (ana metod)
├── generate_summary()      # TXT rapor
├── generate_html_report()  # HTML rapor
├── save_to_file()          # TXT kaydetme
├── save_to_json()          # JSON kaydetme
└── save_html_report()      # HTML kaydetme
```

### Özellikler
- ✅ Rate limiting (1 saniye bekleme)
- ✅ Error handling
- ✅ UTF-8 encoding
- ✅ Responsive HTML tasarım
- ✅ Atom ve RSS feed desteği
- ✅ Duplicate filtreleme

---

## 🐳 DOCKER KULLANIMI

```bash
# Build
docker-compose build

# Run
docker-compose up -d

# Logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## 🔄 YAPISAL DEĞİŞİKLİKLER

### ❌ Kaldırılan Dosyalar
- `cyber_news_aggregator.py` (basit versiyon, gereksiz)
- `cybernews.py` (duplikat, gereksiz)

### ✅ Güncellenen Dosyalar
- `auto_scheduler.py` → Artık `ExtendedCyberNewsAggregator` kullanıyor
- `README.md` → Dosya isimleri ve kaynak listesi güncellendi

### 🎯 Sonuç
- Daha temiz proje yapısı
- Tek ana program (`cyber_news_genisletilmis.py`)
- Karışıklık yok, duplikasyon yok

---

## 📋 BAĞIMLILIK DURUMU

| Paket | Versiyon | Durum |
|-------|----------|-------|
| requests | 2.32.5 | ✅ YÜKLÜ |
| beautifulsoup4 | 4.14.3 | ✅ YÜKLÜ |
| lxml | 6.0.2 | ✅ YÜKLÜ |
| schedule | - | ⚠️ EKSIK (opsiyonel) |

---

## 🎨 ÇIKTI ÖRNEKLERİ

### TXT Formatı
```
╔═══════════════════════════════════════════════════════════╗
║      SİBER GÜVENLİK HABERLERİ - GENİŞLETİLMİŞ ÖZET       ║
║      Tarih: 11.02.2026 13:45                             ║
╚═══════════════════════════════════════════════════════════╝

📊 Toplam 39 haber | 13 kaynak
```

### HTML Formatı
- Modern gradient tasarım
- Responsive layout
- İstatistik kartları
- Hover efektleri
- Kaynak bazlı gruplandırma

### JSON Formatı
```json
{
  "The Hacker News": [
    {
      "title": "...",
      "link": "...",
      "description": "...",
      "date": "...",
      "source": "The Hacker News"
    }
  ]
}
```

---

## 🚀 HIZLI BAŞLANGIÇ

```bash
# 1. Bağımlılıkları yükle
pip install -r requirements.txt

# 2. Haberleri topla
python cyber_news_genisletilmis.py

# 3. Çıktıları kontrol et
ls -lh cyber_news_extended_*
```

---

## 💡 İPUCU

**En iyi sonuç için:**
- Günde 2-3 kez çalıştır
- HTML raporları tarayıcıda aç
- JSON dosyalarını veri analizi için kullan
- TXT dosyalarını terminal/console'da oku

---

**Son not:** Proje artık optimize edilmiş, temiz ve kullanıma hazır! 🎉
