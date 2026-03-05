"""Config - Tüm ayarlar"""
import os
from datetime import datetime

# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY', '')

# Dosya yolları
ARCHIVE_FILE = "data/haberler_arsiv.txt"

# Haber kaynakları
NEWS_SOURCES = {
    'The Hacker News': 'https://feeds.feedburner.com/TheHackersNews',
    'BleepingComputer': 'https://www.bleepingcomputer.com/feed/',
    'Krebs on Security': 'https://krebsonsecurity.com/feed/',
    'Threatpost': 'https://threatpost.com/feed/',
    'Security Affairs': 'https://securityaffairs.com/feed',
    'Graham Cluley': 'https://grahamcluley.com/feed/',
    'SANS ISC': 'https://isc.sans.edu/rssfeed.xml',
    'Recorded Future': 'https://www.recordedfuture.com/feed',
    'Cyberscoop': 'https://cyberscoop.com/feed/',
    'The Register': 'https://www.theregister.com/security/cyber_crime/headlines.atom',
    'TechCrunch Security': 'https://techcrunch.com/category/security/feed/',
    'CSO Online': 'https://www.csoonline.com/feed/',
    'Infoblox Blog': 'https://blogs.infoblox.com/feed/',
}

# ===== SOSYAL MEDYA SİNYALLERİ AYARLARI =====
# Ana havuz: HN + Mastodon + GitHub (max 2) → top 5
# Ayrı havuz: Reddit via Tavily → top 3
# Toplam: max 8 sinyal
SOCIAL_SIGNAL_CONFIG = {
    'hours_back': 24,
    'mastodon': {
        'instance':  'infosec.exchange',
        'fallback_instances': ['mastodon.social', 'fosstodon.org'],
        'hashtags':  ['cybersecurity', 'infosec', 'vulnerability'],
        'limit':     30,       # Her hashtag için çekilecek post sayısı (artırıldı)
        'min_score': 1,        # Minimum engagement — genişletildi (önceki: 2)
        'top_n':     5,        # Ana havuza eklenecek max Mastodon postu (önceki: 3)
        'hours_back': 48,      # Mastodon için zaman penceresi (son 48 saat)
    },
    'hackernews': {
        'min_points':    5,    # Daha geniş filtre — genişletildi (önceki: 10)
        'limit':         30,   # Daha fazla çek, combined score ile sırala (önceki: 25)
        'comment_weight': 3,   # combined_score = points + comments * 3
    },
    'github_advisories': {
        'min_severity': ['critical', 'high', 'medium'],
        'limit':  10,          # Çekilecek max advisory sayısı
        'top_n':   1,          # Ana havuza eklenecek max GitHub advisory (önceki: 2)
    },
    'reddit': {
        # PullPush API kullanılıyor (Pushshift halefi) — ücretsiz, API key gerektirmez
        # Azure IP bloğu yok, tam yorum derinliği mevcut
        'subreddits':     ['cybersecurity', 'netsec'],
        'query':          'cybersecurity vulnerability exploit malware breach',
        'size':           30,      # Her subreddit için çekilecek max post sayısı (artırıldı)
        'min_upvotes':    2,       # Minimum upvote — genişletildi (önceki: 3)
        'hours_back':     48,      # Son kaç saatin postları alınsın
        'top_n':          5,       # Ayrı havuzdan eklenecek max Reddit postu (önceki: 3)
        'fetch_comments': True,    # Post yorumları da çekilsin mi
        'max_comments':   5,       # Post başına max yorum sayısı
    },
}

# Scraping ayarları
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
CONTENT_SELECTORS = {
    'The Hacker News': [{'class': 'articlebody'}],
    'BleepingComputer': [{'class': 'articleBody'}],
    'Krebs on Security': [{'class': 'entry-content'}],
    'Security Affairs': [{'class': 'entry-content'}],
    'Graham Cluley': [{'class': 'entry-content'}],
    'The Register': [{'class': 'article_text_wrapper'}],
    'TechCrunch Security': [{'class': 'article-content'}],
    'CSO Online': [{'class': 'body-copy'}],
    'Infoblox Blog': [{'class': 'entry-content'}],
}

# ===== YENİ: ÖNEM SCORING SİSTEMİ (v2.0) =====
# Bu ağırlıklar haberleri kategorize etmek için kullanılır
IMPORTANCE_WEIGHTS = {
    'infrastructure_attack': {
        'weight': 100,
        'description': 'Enerji, sağlık, finans, hükümet altyapısına saldırı',
        'keywords': ['critical infrastructure', 'power grid', 'hospital', 'healthcare', 'financial', 'government', 'scada', 'industrial control']
    },
    'large_breach': {
        'weight': 80,
        'description': '5 milyon+ kullanıcı verisi ihlali',
        'keywords': ['5 million', '10 million', 'million users', 'data breach', 'personal information', 'credit card', 'ssn']
    },
    'zero_day_apt': {
        'weight': 95,
        'description': 'Zero-day + APT grubu aktivitesi',
        'keywords': ['zero-day', 'apt28', 'apt29', 'lazarus', 'nation-state', 'previously unknown', 'threat actor', 'advanced persistent']
    },
    'national_security': {
        'weight': 110,
        'description': 'Ulusal güvenlik / Türkiye',
        'keywords': ['national security', 'government agencies', 'türkiye', 'nato', 'avrupa birliği', 'gendarmerie', 'moi']
    },
    'geopolitical_critical': {
        'weight': 120,
        'description': 'Jeopolitik kritik durumlar (siber savaş, ülke çatışması)',
        'keywords': ['cyber warfare', 'nation-state conflict', 'diplomatic crisis', 'ukraine', 'russia', 'china', 'iran', 'north korea', 'election', 'voting']
    },
    'legal_regulation': {
        'weight': 50,
        'description': 'Yasal düzenlemeler ve yönetmelikler',
        'keywords': ['regulation', 'legislation', 'law', 'compliance', 'gdpr', 'kvkk', 'dpa', 'directive', 'act', 'bill']
    }
}

# Pattern tanımları (REGEX) - Otomatik kategorizasyon için
DETECTION_PATTERNS = {
    'cve': r'CVE-\d{4}-\d{4,5}',
    'apt_groups': r'\b(APT\d+|Lazarus|Wizard Spider|LockBit|Conti|REvil|DarkSide|Emotet|Aqua|Scattered)\b',
    'large_number': r'(\d+)\s*(?:million|M|B)',
    'sectors': r'\b(healthcare|health|hospital|energy|power|finance|bank|government|military|defense)\b',
    'countries': r'\b(Ukraine|Russia|China|Iran|Korea|Israel|US|USA|UK|United States)\b',
}

# Gemini prompt (RESMİ TÜRKÇE) - YENİ GELİŞTİRİLMİŞ VERSİYON
def get_claude_prompt(news_content, recent_events=''):
    now = datetime.now()
    return f"""Sen profesyonel siber güvenlik analistisin.

GÖREV: 130 haberi analiz et → En önemli 10'unu seç (10 yoksa olduğu kadar) → Kalanları önem sırasına koy → HTML raporu oluştur.

🚨 BAŞLIK KURALI — TÜM HABER BAŞLIKLARI İÇİN ZORUNLU:
⛔ YASAK: "...Etkilenmesi", "...Açıklanması", "...Bulunması" → mastar/isim-fiil KULLANMA
✅ ZORUNLU: "...Etkilemiştir", "...Açıklanmıştır", "...Tespit Edilmiştir" → eylem cümlesi

🚨 KRİTİK AŞAMA 1 - HABERLERİ FİLTRELE:
Aşağıdaki türleri ÇIKAR (raporda gösterme):
❌ "Podcast yayınlandı", "Webinar duyurusu", "Ürün lansmanı", "Beta sürüm" 
❌ "İndirilebilir rapor", "Etkinlik katılımı", "Konferans programı"
❌ Basit patch/güncelleme haberleri (kritik olmayan)
❌ İnceleme yazıları, röportajlar, genel tavsiye makaleleri
✅ SADECE aktif tehdit, açık, saldırı, veri ihlali, kritik güncelleme haberlerini AL

🚨 KRİTİK AŞAMA 2 - EN ÖNEMLİ 10 HABERİ SEÇ (yoksa olduğu kadar, max 10):
Aşağıdaki kriterlere göre önem sırasına göre en önemli 10 haberi seç:

🔴 **[GEÇİCİ ÖNCELİK — AKTİF ÇATIŞMA DÖNEMİ]** İran-İsrail çatışması kapsamındaki SİBER haberler diğer tüm kategorilere göre ÜST ÖNCELIK alır ve ÖNEMLİ GELİŞMELER kutusunda EN ÜSTE yerleştirilir:
   - İran veya İsrail kaynaklı siber saldırı / siber operasyon haberleri
   - İki ülke arasındaki siber casusluk, sabotaj, hack & leak haberleri
   - Çatışmayla bağlantılı kritik altyapı saldırıları (enerji, iletişim, finans)
   - İlgili tehdit aktörleri: Charming Kitten, APT33, APT34, OilRig, Tortoiseshell, Unit 8200
   - Anahtar kelimeler: "Iran cyber", "Israel cyber", "IDF cyber", "IRGC", "Gaza", "Hamas cyber", "Hezbollah cyber"
   - Bu kategoride haber varsa, diğer kategorilerden haber çıkarılsa bile bu haber listede kalır.

1️⃣ **KRİTİK ALTYAPI SALDIRISI**
   - Enerji, sağlık, finans, hükümet sektörü
   - "Critical infrastructure", "power grid", "hospital systems"
   - APT grupları + devlet destekli saldırılar

2️⃣ **5 MİLYON+ KULLANICI VERİ İHLALİ**
   - "5 million", "10 million", "data breach"
   - Büyük şirketler (Microsoft, Google, Amazon, Apple)
   - "Personal information", "credit card", "SSN"

3️⃣ **ZERO-DAY + APT GRUBU AKTİVİTESİ**
   - APT28, APT29, Lazarus, etc.
   - Nation-state actors
   - "Previously unknown vulnerability"

4️⃣ **ULUSAL GÜVENLİK / TÜRKİYE**
   - "National security", "government agencies"
   - Türkiye ile ilgili siber güvenlik haberleri
   - NATO, AB, Türk kurumları

5️⃣ **JEOPOLİTİK KRİTİK DURUMLAR**
   - Ülkeler arası siber savaş, siber diplomasi krizi
   - "Cyber warfare", "nation-state conflict", "diplomatic crisis"
   - Kritik ülke sistemlerine saldırı (Rusya-Ukrayna, ABD-Çin, İran, Kuzey Kore)
   - Seçim sistemleri, kritik altyapı hedefleme
   - Uluslararası hukuk/anlaşma ihlalleri

6️⃣ **YASAL DÜZENLEMELER**
   - Siber güvenlikle ilgili yeni çıkan yasalar, yasal düzenlemeler

7️⃣ **KRİTİK CVE / YÜKSEK CVSS SKORU**
   - CVSS >= 9.0 olan kritik güvenlik açıkları
   - Aktif olarak istismar edilen zafiyetler
   - Yaygın yazılım/donanımı (Windows, Linux, Cisco, Fortinet vb.) etkileyen açıklar

8️⃣ **BÜYÜK RANSOMWARE / FİDYE SALDIRISI**
   - Kritik hizmetleri durduran fidye saldırıları
   - Büyük kuruluşları etkileyen ransomware grupları (LockBit, BlackCat, Cl0p vb.)

9️⃣ **TEDARİK ZİNCİRİ / SUPPLY CHAIN SALDIRISI**
   - Yazılım tedarik zinciri saldırıları
   - Açık kaynak paketlerine enjeksiyon, geliştiricileri hedef alma

🔟 **DİĞER ÖNEMLİ GELİŞMELER** (yukarıdakilerde yer almayan en etkili haber)
   - Geniş çaplı phishing / sosyal mühendislik kampanyaları
   - Yeni zararlı yazılım ailesi / botnet keşfi
   - Önemli güvenlik araştırması veya ifşaatı

🚨 AŞAMA 3 - YAPILANDIRILMIŞ RAPOR OLUŞTUR:

RAPOR YAPISI (SIRAYLA):

1️⃣ **BAŞLIK**: "{now.strftime('%d.%m.%Y')} Siber Güvenlik Haber Özetleri"

2️⃣ **YÖNETİCİ ÖZETİ BAŞLIĞI**

3️⃣ **"ÖNEMLİ GELİŞMELER" KUTUSU**:
   - En kritik 10 haberin TAM CÜMLELİK özeti (10 yoksa olduğu kadar, minimum 1)
   - Her biri sayfa içi link: <a href="#haber-N">N. CVE-2024-1234 açığı Microsoft sunucularında kritik güvenlik riski oluşturmaktadır.</a>
   - ZORUNLU: Tam cümle (özne + yüklem + nesne) + nokta ile bitiş

⚠️ Ham veride [S1]-[S5] ile başlayan satırlar SOSYAL SİNYAL referansıdır.
   Bunları ASLA haber olarak sayma, numaralandırma veya paragraf yazma. Tamamen yoksay.

4️⃣ **GERİ KALAN HABERLERİN 2 SÜTUNLU TABLOSU** (önemli 10 haber kutusuna girmeyenler):
   - Önemli 10 haber seçildiyse: 11. haber → id="haber-11", 12. haber → id="haber-12" vs.
   - Her biri TAM CÜMLELİK özet + sayfa içi link
   - ZORUNLU: Tam cümle yapısı (özne + yüklem + nesne) + nokta ile bitiş

5️⃣ **HABER PARAGRAFLARI (SIRALAMA ÖNEMLİ!)**:
   - ÖNCE: En önemli 10 haberin paragraf özetleri (id="haber-1" dan haber-10'a)
   - SONRA: Geri kalan TÜM haberlerin paragraf özetleri (id="haber-11"den son habere kadar)
   - ⚠️ YARIDA BIRAKMAK YASAK — tabloda kaç haber varsa HEPSININ paragraf özeti olacak
   - Her news-item için news-content paragrafı ZORUNLUDUR, atlanamaz
   - ⚠️ HER PARAGRAF MİNİMUM 100 KELİME OLMALIDIR (daha kısa yazarsan HATA sayılır!)

KRİTİK KURALLALAR:
✅ ÖNEMLİ GELİŞMELER KUTUSUNA MÜMKÜNSE 10 HABER SEÇ (haber yoksa olduğu kadar, max 10)
✅ Tablodaki haber sayısı = paragraf sayısı (bire bir eşit olmalı)
✅ Önemli gelişmelerdeki haberler tekrar etmesin tabloda
✅ ID numaraları: 1'den son habere kadar sürekli
✅ Sayfa içi linkler doğru çalışsın
✅ ASLA eksik paragraf bırakma — her news-item'ın news-content'i dolu olacak

KRİTİK DİL KURALI - RESMİ TÜRKÇE:
- yapılmıştır, edilmiştir, belirtilmektedir, ifade edilmektedir, tespit edilmiştir
- ASLA: yaptı, etti, söyledi, bulundu (günlük dil yasak)
- CVE, FBI, NSA, APT gibi kısaltmaların tamamı büyük harf

ANTİ-HALÜSİNASYON:
- SADECE verilen metni kullan
- TAHMİN YAPMA, VARSAYIMDA BULUNMA, KISALTMA YAPMA  
- VERİLEN TÜM UYGUN HABERLERİ YAZ! (Filtrelenenler hariç)
- ASLA YARIDA KESME! SON HABERE KADAR DEVAM ET!

⚠️ KAYNAK SATIRI KURALI - KRİTİK:
Her haberin altında şu format var: (XXXXXXX, AÇIK - https://link, domain.com, GG.AA.YYYY)
  → href içine: tam https://... linkini yaz (ASLA domain.com değil)
  → görünen metin: domain.com
  → tarih: o satırdaki GG.AA.YYYY değerini AYNEN kopyala
⛔ ASLA bugünün tarihini yazma — her haberin tarihi farklıdır, ham veriden oku

ZORUNLU HTML ŞABLONU - AYNEN KULLAN:
```html
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Siber Güvenlik Raporu - {now.strftime('%d.%m.%Y')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html {{ scroll-behavior: smooth; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #2c3e50;
            background: #f5f7fa;
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.07);
        }}
        
        /* ŞIK BAŞLIK */
        .report-header {{
            background: linear-gradient(135deg, #1a237e 0%, #3949ab 100%);
            padding: 50px 30px;
            text-align: center;
            color: white;
        }}
        .report-header h1 {{
            font-size: 26px;
            font-weight: 600;
            margin: 0;
            letter-spacing: 0.3px;
        }}
        
        /* ÖNEMLİ GELİŞMELER KUTUSU - AÇIK PASTEL MAVİ */
        .important-news {{
            background: linear-gradient(135deg, #e3f2fd 0%, #f1f8ff 100%);
            color: #2c3e50;
            padding: 25px 30px;
            margin: 0;
            border: 1px solid #bbdefb;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .important-news h2 {{
            color: #1565c0;
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 20px;
        }}
        .important-summary {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }}
        @media (max-width: 640px) {{
            .important-summary {{
                grid-template-columns: 1fr;
            }}
        }}
        .important-item {{
            background: rgba(255,255,255,0.7);
            padding: 12px 16px;
            border-radius: 6px;
            border-left: 4px solid #42a5f5;
        }}
        .important-item a {{
            color: #2c3e50;
            text-decoration: none;
            font-weight: 500;
            font-size: 15px;
        }}
        .important-item a:hover {{
            text-decoration: underline;
            color: #1565c0;
        }}
        
        /* YÖNETİCİ ÖZETİ */
        .executive-summary {{
            background: #f8f9fa;
            padding: 25px 30px;
            margin: 0;
            border-bottom: 1px solid #e1e8ed;
        }}
        .executive-summary h2 {{
            color: #1a237e;
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 2px solid #1a237e;
        }}
        .executive-table {{
            width: 100%;
            border-spacing: 8px;
        }}
        .executive-table td {{
            background: white;
            padding: 12px 16px;
            border-radius: 6px;
            border-left: 3px solid #1a237e;
            vertical-align: top;
            width: 50%;
        }}
        .executive-table a {{
            color: #1a237e;
            text-decoration: none;
            font-weight: 500;
            font-size: 14px;
            line-height: 1.4;
        }}
        .executive-table a:hover {{
            text-decoration: underline;
        }}
        
        /* HABERLER BÖLÜMÜ */
        .news-section {{
            padding: 30px;
        }}
        .news-item {{
            background: #f8f9fa;
            margin-bottom: 25px;
            border-radius: 8px;
            padding: 20px;
            border-left: 4px solid #1a237e;
        }}
        .news-title {{
            color: #1a237e;
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 12px;
            line-height: 1.3;
        }}
        .news-content {{
            color: #2c3e50;
            font-size: 15px;
            line-height: 1.6;
            margin-bottom: 10px;
        }}
        .source {{
            color: #666;
            font-size: 13px;
            margin: 0;
        }}
        .source a {{
            color: #1a237e;
            text-decoration: none;
        }}
        .source a:hover {{
            text-decoration: underline;
        }}
        
        /* BAŞA DÖN BUTONU */
        /* ── SOSYAL MEDYA SİNYALLERİ KUTUSU ── */
        .social-signals {{
            background: #f8faff;
            border: 1px solid #c7d7fd;
            border-radius: 8px;
            padding: 24px 28px;
            margin-bottom: 20px;
        }}
        .social-signals h2 {{
            color: #1e3a8a;
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 16px;
            padding-bottom: 10px;
            border-bottom: 2px solid #dbeafe;
        }}
        .social-signals .signal-list {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }}
        .social-signals .signal-item {{
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-left: 4px solid #3b82f6;
            border-radius: 6px;
            padding: 12px 16px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}
        .social-signals .signal-item.reddit-item   {{ border-left-color: #ff4500; }}
        .social-signals .signal-item.hn-item       {{ border-left-color: #ff6600; }}
        .social-signals .signal-item.github-item   {{ border-left-color: #238636; }}
        .social-signals .signal-item.mastodon-item {{ border-left-color: #6364ff; }}
        .social-signals .signal-meta {{
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }}
        .social-signals .signal-platform-label {{
            font-size: 10px;
            font-weight: 700;
            color: #ffffff;
            background: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-radius: 3px;
            padding: 2px 7px;
        }}
        .social-signals .reddit-item .signal-platform-label   {{ background: #ff4500; }}
        .social-signals .hn-item .signal-platform-label       {{ background: #ff6600; }}
        .social-signals .github-item .signal-platform-label   {{ background: #238636; }}
        .social-signals .mastodon-item .signal-platform-label {{ background: #6364ff; }}
        .social-signals .signal-engagement {{
            font-size: 11px;
            color: #475569;
            background: #f1f5f9;
            border-radius: 3px;
            padding: 2px 8px;
        }}
        .social-signals .signal-item a {{
            color: #1e293b;
            text-decoration: none;
            font-size: 13px;
            font-weight: 500;
            line-height: 1.45;
            display: block;
        }}
        .social-signals .signal-item a:hover {{
            color: #1e3a8a;
            text-decoration: underline;
        }}
        @media (max-width: 640px) {{
            .social-signals {{
                padding: 16px;
            }}
            .social-signals .signal-list {{
                grid-template-columns: 1fr;
            }}
            .social-signals .signal-meta {{
                gap: 6px;
            }}
        }}

        .back-to-top {{
            position: fixed;
            top: 50%;
            left: calc(50% - 450px - 48px);
            transform: translateY(-50%);
            width: 36px;
            height: 36px;
            background: #1a237e;
            color: white;
            border: none;
            border-radius: 50%;
            font-size: 18px;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(0,0,0,0.25);
            display: flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            opacity: 0.85;
            transition: opacity 0.2s;
            z-index: 999;
        }}
        .back-to-top:hover {{
            opacity: 1;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="report-header">
            <h1>{now.strftime('%d.%m.%Y')} Siber Güvenlik Haber Özetleri</h1>
        </div>
        
        <!-- YÖNETİCİ ÖZETİ -->
        <div class="executive-summary">
            <h2>Yönetici Özeti</h2>
            
            <!-- ÖNEMLİ GELİŞMELER KUTUSU - EN FAZLA 10 HABER, 2 SÜTUN GRID -->
            <div class="important-news">
                <h2>Önemli Gelişmeler</h2>
                <div class="important-summary">
                    [EN ÖNEMLİ 10 HABER BURADA (mümkünse 10) - HER BİRİ TAM CÜMLE:]
                    <div class="important-item">
                        <a href="#haber-1">1. Microsoft Exchange sunucularında CVE-2024-1234 açığı kritik güvenlik riski oluşturmaktadır.</a>
                    </div>
                    <div class="important-item">
                        <a href="#haber-2">2. LockBit 4.0 fidye yazılımı dünya genelinde sağlık kurumlarını hedef almaktadır.</a>
                    </div>
                    <div class="important-item">
                        <a href="#haber-3">3. ...</a>
                    </div>
                    [... haber-10'a kadar devam et ...]
                </div>
            </div>

            <!-- GERİ KALAN HABERLERİN 2 SÜTUNLU TABLOSU (önemli 10'dan sonrakiler) -->
            <table class="executive-table">
                [GERİ KALAN HABERLERİN 2 SÜTUNLU TABLOSU - TAM CÜMLE ÖRNEKLER:]
                <tr>
                    <td><a href="#haber-11">11. Google Chrome'da sıfır gün açığı aktif olarak istismar edilmektedir.</a></td>
                    <td><a href="#haber-12">12. Cisco ağ cihazları için kritik güvenlik güncellemesi yayınlanmıştır.</a></td>
                </tr>
            </table>
        </div>
        
        <!-- HABERLER -->
        <div class="news-section">
            [ÖNEMLİ 10 HABERİN PARAGRAF ÖZETLERİ - ÖNCE BUNLAR (haber-1'den haber-10'a)]
            <div class="news-item" id="haber-1">
                <div class="news-title"><b>Birinci Önemli Haberin Başlığı</b></div>
                <p class="news-content">MİNİMUM 100 kelime paragraf özet (zorunlu), resmi Türkçe. 5N1K: kim, ne, nerede, ne zaman, nasıl, neden sorularını kapsa. Yeterli bağlam ve teknik detay ekle.</p>
                <p class="source"><b>(KAYNAK, AÇIK - <a href="[KAYNAK_LINK değeri]" target="_blank">[KAYNAK_DOMAIN değeri]</a>, [HABER_TARİHİ değeri])</b></p>
            </div>
            [... haber-2'den haber-10'a kadar devam et ...]

            [SONRA GERİ KALAN HABERLERİN PARAGRAF ÖZETLERİ (haber-11'den son habere)]
            <div class="news-item" id="haber-11">
                <div class="news-title"><b>On Birinci Haberin Başlığı</b></div>
                <p class="news-content">MİNİMUM 100 kelime paragraf özet (zorunlu), resmi Türkçe. 5N1K: kim, ne, nerede, ne zaman, nasıl, neden sorularını kapsa. Yeterli bağlam ve teknik detay ekle.</p>
                <p class="source"><b>(KAYNAK, AÇIK - <a href="[KAYNAK_LINK değeri]" target="_blank">[KAYNAK_DOMAIN değeri]</a>, [HABER_TARİHİ değeri])</b></p>
            </div>
        </div>
    </div>
    <a href="#" class="back-to-top" title="Başa Dön" onclick="window.scrollTo({{top:0,behavior:'smooth'}});history.replaceState(null,'',window.location.pathname);return false;">↑</a>
</body>
</html>
```

BAŞLIK KURALLARI:
✓ Eylem cümlesi: "CVE-2024-1234 Microsoft Exchange Sunucularını Etkilemiştir"
✓ Fiil zorunlu: -mıştır, -edilmiştir, -tespit edilmiştir, -açıklanmıştır
✗ YASAK: -ması, -edilmesi, -bulunması gibi isim-fiil (mastar) yapıları
✓ SOMUT detaylar: Şirket/CVE/ülke adları dahil
✓ 7-9 kelime, her kelimenin ilk harfi büyük

ÖZET PARAGRAF KURALLARI:
✓ MİNİMUM 100 kelime — ZORUNLU (100'den az kelime kesinlikle kabul edilmez!)
✓ İdeal uzunluk: 110-150 kelime aralığında yaz
✓ 5N1K tüm sorular cevaplansın
✓ Resmi Türkçe (-mıştır, -edilmiştir)
✓ Normal cümle yapısı (başlık değil)

KRİTİK:
- EN ÖNEMLİ 10 HABER → Hem "Önemli Gelişmeler" kutusunda HEM de haber paragraflarının en üstünde
- Kalan haberler → Önem sırasına göre sıralanmış
- Her habere id="haber-N" ve sayfa içi linkler
- Filtrelenenler (podcast/webinar/vb) raporda YOK

═══════════════════════════════════════════════════════════

SON 3 GÜNDE RAPORLANAN OLAYLAR (TEKRAR ALMA):
{recent_events if recent_events else "(Henüz arşiv yok)"}

⛔ Yukarıdaki olaylarla AYNI OLAYI anlatan haberler, farklı kaynak/başlıkla gelse bile ÇIKAR.
Aynı olay: aynı CVE numarası, aynı şirket/kurum adı + aynı saldırı türü, aynı tehdit aktörü + aynı hedef.

═══════════════════════════════════════════════════════════

HAM HABERLER:
{news_content}

═══════════════════════════════════════════════════════════

ŞİMDİ SIRAYLA YAP:
1. Filtreleme → Uygun haberleri seç (130'den ~43)
2. ÖNEMLİ GELİŞMELER için EN FAZLA 10 HABERİ SEÇ (mümkünse 10, yoksa olduğu kadar)
   - Yukarıdaki 10 kritere göre önceliklendir
   - Eğer 10 tane kritik haber bulamazsan, en az kritik haber kategorisinden tamamla
3. Kalanları önem sırasına koy (tablo için)
4. HTML şablonunu doldur

ZORUNLU:
- Yukarıdaki şablonu AYNEN kullan
- TÜM uygun haberleri dahil et
- ÖNEMLİ GELİŞMELER KUTUSUNA MÜMKÜNSE 10 HABER SEÇ (eksik bırakma!)"""
