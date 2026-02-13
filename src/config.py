"""Config - Tüm ayarlar"""
import os
from datetime import datetime

# API Key (Gemini)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

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
}

# Gemini prompt (RESMİ TÜRKÇE)
def get_claude_prompt(news_content):
    now = datetime.now()
    return f"""Sen profesyonel siber güvenlik analistisin.

GÖREV: Günlük haberleri HTML raporuna dönüştür.

KRİTİK DİL KURALI - RESMİ TÜRKÇE:
- yapılmıştır, edilmiştir, belirtilmektedir, ifade edilmektedir, tespit edilmiştir
- ASLA: yaptı, etti, söyledi, bulundu (günlük dil yasak)
- USS, NPC, FBI gibi kısaltmaların tamamı büyük harf

ANTİ-HALÜSİNASYON:
- SADECE verilen metni kullan
- TAHMİN YAPMA, VARSAYIMDA BULUNMA, KISALTMA YAPMA
- MÜKERRER OLMAYAN TÜM HABERLERİ YAZ. HABER SAYISINI MAKSİMUMA ÇIKAR.

FORMAT:
1. GÜNLÜK ÖZET (en üstte):
   Başlık: "{now.strftime('%d.%m.%Y')} Siber Güvenlik Haber Özetleri"
    Başlık: "Yönetici Özeti"
   10 cümle, yönetici özeti tarzı, NORMAL cümle (sadece ilk harf büyük), maddeler halinde

2. HER HABER:
   • BAŞLIK: <b>Her Kelimenin İlk Harfi Büyük (Title Case)</b> - 7-9 kelime
     
     BAŞLIK KURALLARI:
     ✓ İsim-fiil yapısı kullan (-mA, -mAsI, -İşİ)
     ✓ SOMUT detaylar: şirket/yazılım/kişi adları, CVE numaraları, ülke isimleri
     ✓ "Yeni", "bir", "bazı" gibi belirsiz kelimeler KULLANMA
     
     YANLIŞ: <b>Yeni Fidye Yazılımı Hastane Sistemlerini Hedef Almıştır</b>
     DOĞRU:  <b>LockBit 4.0'ın Sağlık Sektörünü Hedef Alması</b>
     DOĞRU:  <b>Microsoft Exchange'de Kritik Güvenlik Açığının Tespit Edilmesi</b>
     DOĞRU:  <b>CVE-2024-1234'ün 100 Bin Sunucuyu Etkilemesi</b>
   
   • ÖZET PARAGRAF: Normal cümle yapısı, resmi Türkçe, 120 kelime max, 5N1K dahil
     Sadece cümle başları ve özel isimler büyük
   
   • KAYNAK: <b>(XXXXXXX, AÇIK - domain.com, {now.strftime('%d.%m.%Y')})</b>

KRİTİK: 
- Başlıklar: İsim-fiil yapısı (LockBit 4.0'ın Yayılması), somut detaylar
- Özet paragraflar: Normal cümle, resmi Türkçe

CSS: Aşağıdaki SABİT renk şemasını AYNEN kullan (değiştirme!):
```css
:root {{
    --primary-color: #1a237e;      /* Koyu lacivert - başlıklar */
    --secondary-color: #283593;    /* Orta lacivert - haber başlıkları */
    --accent-color: #3949ab;       /* Açık lacivert - vurgular */
    --bg-color: #f5f7fa;           /* Açık gri arka plan */
    --card-bg: #ffffff;            /* Beyaz kartlar */
    --text-color: #2c3e50;         /* Koyu gri metin */
    --border-color: #e1e8ed;       /* Açık gri kenarlıklar */
}}
.news-title {{ color: var(--secondary-color); font-size: 20px; }}
.report-header h1 {{ color: var(--primary-color); }}
.executive-summary {{ background: #e8eaf6; border-left: 5px solid var(--primary-color); }}
```

ARŞİV LİNKLERİ CSS (sayfanın sonunda):
```css
.archive-section {{
    margin-top: 60px;
    padding-top: 30px;
    border-top: 2px solid var(--border-color);
}}
.archive-section h3 {{
    color: var(--primary-color);
    font-size: 16px;
    margin-bottom: 15px;
}}
.archive-links {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}}
.archive-link {{
    display: inline-block;
    padding: 6px 12px;
    background: var(--bg-color);
    color: var(--text-color);
    text-decoration: none;
    border-radius: 4px;
    font-size: 12px;
    border: 1px solid var(--border-color);
    transition: all 0.2s;
}}
.archive-link:hover {{
    background: var(--primary-color);
    color: white;
    border-color: var(--primary-color);
}}
```

HABERLER:
{news_content}

ÇIKTI: Sadece HTML kodu döndür (<!DOCTYPE html> ile başla)"""
