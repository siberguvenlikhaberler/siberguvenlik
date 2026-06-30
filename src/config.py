"""Config - Tüm ayarlar"""
import os
from datetime import datetime

# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY', '')

# ─────────────────────────────────────────────────────────────────────────────
# LLM SAĞLAYICI SEÇİMİ — OpenRouter geçişi için PASİF altyapı
# ─────────────────────────────────────────────────────────────────────────────
# Sistem varsayılan olarak Gemini (google-genai SDK) ile çalışmaya devam eder.
# OpenRouter'a geçiş için TEK YAPILACAK: ortam değişkeni LLM_PROVIDER=openrouter
# ve OPENROUTER_API_KEY tanımlamak. Anahtar gelene kadar bu blok uyur (pasif).
#
# OpenRouter, OpenAI uyumlu bir API sunar; bu yüzden mevcut `openai` paketiyle
# (requirements.txt'te zaten var) yalnızca base_url değiştirilerek kullanılır.
#   Endpoint : https://openrouter.ai/api/v1/chat/completions
#   Birincil : google/gemini-3-flash-preview  (OPENROUTER_MODEL varsayılanı)
#   Yedek    : google/gemini-3.5-flash  (GA — 19 May 2026; Flash sınıfı, 1M bağlam)
#   Not      : Birincil model env (OPENROUTER_MODEL / Actions vars) ile değiştirilebilir;
#              tanımsızsa preview kullanılır, başarısızlıkta GA 3.5 Flash'a düşer.
#              (Aşağıdaki OPENROUTER_MODEL / OPENROUTER_FALLBACK_MODELS ile birebir tutarlı.)
#
# Gemini 3.x Flash bir "thinking" modelidir; reasoning gücü `reasoning.effort` ile
# ayarlanır: minimal | low | medium | high | xhigh. JSON üretim görevlerinde
# (sıralama/özet) düşük effort yeterli ve hızlı/ucuzdur — varsayılan: low.
# Not: GitHub Actions tanımsız `vars.X` değerlerini boş string olarak geçirir;
# bu yüzden `or default` ile boş değerleri de varsayılana düşürürüz.
LLM_PROVIDER = (os.getenv('LLM_PROVIDER') or 'gemini').strip().lower()

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
OPENROUTER_BASE_URL = os.getenv('OPENROUTER_BASE_URL') or 'https://openrouter.ai/api/v1'
# Birincil model + başarısızlıkta denenecek yedekler (sıra önemlidir)
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL') or 'google/gemini-3-flash-preview'
# Birincil: Gemini 3 Flash preview. Başarısızlıkta TEK yedek: Gemini 3.5 Flash (GA).
OPENROUTER_FALLBACK_MODELS = [
    m.strip() for m in os.getenv(
        'OPENROUTER_FALLBACK_MODELS',
        'google/gemini-3.5-flash'
    ).split(',') if m.strip()
]
# Reasoning effort: minimal|low|medium|high|xhigh ; 'none'/'' → reasoning gönderilmez
OPENROUTER_REASONING_EFFORT = (os.getenv('OPENROUTER_REASONING_EFFORT') or 'low').strip().lower()
# Reasoning çıktısını yanıttan gizle (sadece nihai cevabı al) — token tasarrufu
OPENROUTER_REASONING_EXCLUDE = (os.getenv('OPENROUTER_REASONING_EXCLUDE') or '1') not in ('0', 'false', 'False')
OPENROUTER_TEMPERATURE = float(os.getenv('OPENROUTER_TEMPERATURE') or '0.3')
OPENROUTER_TIMEOUT = int(os.getenv('OPENROUTER_TIMEOUT') or '300')   # saniye
# OpenRouter sıralama/analitik başlıkları (opsiyonel, isteğe gömülür)
OPENROUTER_HTTP_REFERER = os.getenv('OPENROUTER_HTTP_REFERER') or 'https://github.com/siberguvenlikhaberler/siberguvenlik'
OPENROUTER_APP_TITLE = os.getenv('OPENROUTER_APP_TITLE') or 'Siber Guvenlik Haberleri'


def is_openrouter_active():
    """OpenRouter sağlayıcısı seçili VE API anahtarı mevcut mu?

    Anahtar gelene kadar False döner; bu sayede altyapı tamamen pasif kalır ve
    mevcut Gemini akışı hiç etkilenmez.
    """
    return LLM_PROVIDER == 'openrouter' and bool(OPENROUTER_API_KEY)

# Dosya yolları
ARCHIVE_FILE = "data/haberler_arsiv.txt"

# Son günlerde KRİTİK 3'e (üst manşet) giren haberlerin zengin parmak-izi deposu.
# Çapraz-gün deterministik dedup (src.dedup.same_event cross_day) bu dosyayı
# okuyarak aynı olayın üst üste iki gün KRİTİK 3 manşeti olmasını engeller.
KRITIK3_HISTORY_FILE = "data/kritik3_gecmis.json"
# Çapraz-gün KRİTİK 3 dedup penceresi (gün).
KRITIK3_HISTORY_DAYS = 7


# ─────────────────────────────────────────────────────────────────────────────
# 3-PASS MİMARİSİ İÇİN PROMPT FONKSİYONLARI
# Pass 1 → Sıralama (JSON)
# Pass 2 → Top-10 derin analiz (JSON)
# Pass 3 → Kalan haberler batch özet (JSON)
# ─────────────────────────────────────────────────────────────────────────────

def get_ranking_prompt(articles_brief, recent_events=''):
    """
    Pass 1: Tüm haberlerin başlık+kısa özeti → önem sıralaması (JSON).
    articles_brief: "=== HABER ID: N ===\\nKaynak: ...\\nBaşlık: ...\\nÖzet: ...\n" formatında string.
    """
    return f"""Sen siber güvenlik analistisin. Aşağıdaki haberleri önem derecesine göre değerlendir.

ADIM 0 — TEKİL OLAY KONTROLÜ (önce yap):
Aynı siber olayı/saldırıyı/gelişmeyi farklı kaynaklardan anlatan haberleri tespit et.
Kriter: başlık + içerik birlikte değerlendirildiğinde AYNI OLAY (aynı mağdur + aynı saldırgan/grup + aynı tarihli olay).
🔑 GÜÇLÜ SİNYAL: Aynı kampanya / operasyon / zararlı yazılım KOD ADINI paylaşan
   haberler (ör. "FortiBleed", "Operation Escaneo", "SolarWinds", "LockBit") —
   başlıkları farklı sözcüklerle yazılmış olsa bile — büyük olasılıkla AYNI
   OLAYDIR; en kapsamlısı dışındakileri "filtered" listesine al.
Her gruptan yalnızca en kapsamlı/güncel haberi bırak; diğerlerini "filtered" listesine ekle.
⚠️ Dikkat: farklı CVE numaraları veya farklı mağdurlar → farklı haber (filtreleme).
⚠️ Dikkat: aynı ürün/vendor adı (FortiGate, Windows, Fortinet) paylaşmak TEK BAŞINA
   aynı olay demek DEĞİLDİR — farklı kampanya/açık olabilir (ör. FortiBleed ≠ FortiSandbox açığı).

ADIM 1 — FILTRELE (bunları "filtered" listesine koy):
- Podcast, webinar, konferans, etkinlik duyurusu
- Ürün lansmanı, beta sürüm, pazar araştırması raporu
- Genel tavsiye makalesi, röportaj, inceleme yazısı
- Kritik olmayan rutin patch/güncelleme haberleri

ADIM 2 — SIRALA (kalan haberleri önem sırasına göre diz):
ÖNCELİK İLKESİ: Stratejik / jeopolitik / istihbari değeri olan haberler her zaman üsttedir.
"Büyük rakam" (milyonlarca kullanıcı, milyarlarca dolar) tek başına üst sıra GETİRMEZ.
1. DOĞRUDAN NATO Türkiye Zirvesi (Temmuz 2026) ile ilgili haberler → EN ÜSTTE
   ⚠️ SADECE zirveden açıkça söz eden veya zirveyi hedef/konu alan haberler buraya girer:
   zirveye yönelik saldırı, şüpheli faaliyet, uyarı, güvenlik önlemi, zirveyle bağlantılı
   diplomatik/siber gerilim. Gerçekleşen saldırı ZORUNLU DEĞİL ama zirve bağı ZORUNLUDUR.
   ⛔ Zirveden bahsetmeyen genel NATO haberleri (NATO siber politikası, NATO üyesi ülkeye
      yönelik ama zirveyle ilgisiz saldırılar) buraya GİRMEZ — alttaki kategorilerde değerlendir.
2. Ticari/devlet casus yazılımı: NSO Group, Pegasus, Candiru, Intellexa/Predator, Paragon,
   L3Harris, FinFisher vb. "mercenary spyware" — bunların kullanımı, keşfi, bu firmalara
   yönelik dava/yaptırım/sızıntı (örn. Meta vs. NSO Group)
3. Stratejik kurum/devlet saldırısı: devlet başkanlığı, bakanlık, meclis, büyükelçilik,
   istihbarat servisi, savunma müteahhidi veya uluslararası kurum (Avrupa Konseyi, AB
   kurumları, BM ajansları, NATO karargahı) hedefli saldırı/ihlal
4. Jeopolitik/diplomatik SİBER gelişme + devlet destekli APT/casusluk operasyonu
   (ülkeler arası siber saldırı/casusluk atfı; Rusya, Çin, İran, Kuzey Kore vb.)
   ⛔ Siber boyutu olmayan saf diplomatik/askeri haberler buraya GİRMEZ
5. Kritik altyapı saldırıları (enerji / sağlık / finans / hükümet)
6. Tedarik zinciri (supply chain) saldırıları — yaygın paket/araç/güncelleme mekanizması
7. Milli güvenliği etkileyen büyük veri ihlali (devlet/ordu/savunma verisi, pasaport/
   biyometrik/seçmen kütüğü, 50 milyon+ kritik veri)
8. Zero-day açıkları + aktif istismar kampanyası
9. Büyük fidye yazılımı (ransomware) + takedown operasyonları, hukuki süreçler, kovuşturmalar
10. Diğer önemli gelişmeler (sıradan/bireysel veri ihlalleri ve rutin zararlı yazılım dahil)

ADIM 3 — TOP 10: Sıraladığın ilk 10'u "top10" listesine koy.

SON 3 GÜNDE RAPORLANAN OLAYLAR — bu olayları "filtered" listesine ekle (tekrar alma):
{recent_events if recent_events else "(Arşiv yok)"}

SADECE JSON FORMATINDA YANIT VER — başka hiçbir şey yazma:
{{
  "top10": [3, 7, 15, 42, 1, 8, 23, 56, 12, 67],
  "remaining": [2, 5, 9, 11, 14],
  "filtered": [4, 6, 13, 20]
}}

HABERLER:
{articles_brief}"""


def get_top3_selection_prompt(articles_brief, recent_events=''):
    """
    Pass 4: Tüm non-CVE haberler arasından istihbari/stratejik açıdan EN KRİTİK 3'ü seç.
    articles_brief: "=== HABER ID: N ===\\nBaşlık: ...\\nÖzet: ...\n" formatında string.
    recent_events: son günlerde raporlanan haber başlıkları (mükerrer engelleme).
    """
    return f"""Sen bir siber tehdit istihbarat analistisin. Görevin: aşağıdaki haberler arasından yalnızca STRATEJİK, JEOPOLİTİK veya İSTİHBARİ değeri olan EN KRİTİK 3 haberi seçmek.

NOT: Haber içerikleri İngilizce olabilir; dil fark etmez, anlam ve stratejik öneme göre değerlendir.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEMEL İLKE — SİBER BOYUT ZORUNLULUĞU
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bu bir SİBER GÜVENLİK bültenidir. Top 3'e girecek her haberin mutlaka
bir siber boyutu olmalıdır: saldırı, zararlı yazılım, güvenlik açığı,
casusluk yazılımı, veri ihlali, siber operasyon veya bunları doğrudan
etkileyen politika/hukuk kararı.

⛔ Aşağıdakiler ne kadar stratejik görünürse görünsün top 3'e GİRMEZ:
   • Saf diplomatik/askeri anlaşmalar (siber bileşeni olmayan): ateşkes,
     dekonfliction hattı, askeri diyalog kanalı, barış müzakeresi
   • Saf askeri haberler: silah sistemleri, konvansiyonel saldırı/savunma,
     kara/deniz/hava operasyonları (siber boyutu olmadıkça)
   • Saf ekonomi/ticaret haberleri: yaptırım, enerji fiyatı, ticaret anlaşması
     (siber güvenliği doğrudan etkilemiyorsa)
   → Bu tür haberler için "başka seçenek yok" bahanesi geçersizdir.
     Siber boyutu olmayan haber her zaman Kategori 3'teki en zayıf
     siber haberden bile daha düşük önceliğe sahiptir.

Her haberi değerlendirirken şu soruyu sor:
"Bu haberin özünde bir siber saldırı, güvenlik açığı, casusluk yazılımı,
 veri ihlali veya siber operasyon var mı?"
→ EVET: Stratejik değer testine geç (Kategori 1-3).
→ HAYIR: Top 3'e ALMA, ne kadar önemli görünürse görünsün.

⚠️ SAAT SIFIR KURALI: Stratejik haber olmayan günler de olur.
Bu durumda top 3'ü boş bırakmak yerine Kategori 3'ten en iyi 3'ü seç.
"Seçilmez" listesi her zaman geçerlidir — başka seçenek olmasa bile o listeden seçme.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KATEGORİ 1 — EN YÜKSEK ÖNCELİK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Aşağıdaki türde haber varsa, diğer tüm kategorilere ÖNCE bu seçilir:

A) DEVLET DESTEKLİ CASUS ARAÇLARI & TİCARİ CASUS YAZILIMI
   Devletlere veya istihbarat servislerine satılan/kullanılan casus araçlar.
   • NSO Group / Pegasus, Candiru, Intellexa / Predator, FinFisher, L3Harris,
     Paragon, Hacking Team, Circles, QuaDream ve benzeri "mercenary spyware" firmaları
   • Bu firmalara yönelik dava, yaptırım, yasak, lisans iptali, sızıntı
   • Söz konusu araçların yeni hedef ülke/kişi/örgüte karşı kullanıldığına dair bulgu
   • Benzer ticari gözetleme araçlarının keşfi veya teknik analizi

B) JEOPOLİTİK & DİPLOMATİK SİBER GELİŞMELER
   • Ülkeler arası siber saldırı/casusluk/sabotaj atfı (attribution)
   • Siber savaş, hibrit savaş, siber operasyon (Rusya, Çin, İran, Kuzey Kore vb.)
   • Devlet veya istihbarat servisinin yürüttüğü aktif siber operasyon: botnet çökertme,
     tehdit aktörü altyapısı tasfiyesi, uluslararası koordineli ağ kapatma operasyonu
     (FBI, CISA, Five Eyes, Europol, NCSC, CSE, AIVD ve benzeri kurumlar dahil)
   • Uluslararası anlaşma, diplomatik kriz, yaptırım, sınır dışı etme kararı
   • NATO, AB, BM, OSCE gibi uluslararası örgütlerin siber güvenlik kararı veya politikası
   • Belirli bir uluslararası zirve/etkinliği (ör. NATO zirvesi) DOĞRUDAN hedef alan
     APT faaliyeti, casusluk, hazırlık veya etki operasyonu

   ⚠️ ALAKA TESTİ (yanlış-pozitif önleme): Bir haberi "zirve/etkinlik haberi"
   saymak için haberin ÖZÜNÜN o zirveyle ilgili olması ŞARTTIR. Metnin bir
   yerinde "NATO" geçmesi + başka bir yerinde "summit"/"zirve" geçmesi (ör.
   gövdeye yapışmış "Cloud Security Summit" reklamı, "Summit Partners" şirket
   adı, alakasız bir senatör/etkinlik bağlamı) o haberi zirve haberi YAPMAZ.
   Kelimelerin aynı metinde bulunması ≠ konu birliği. Şüpheye düşersen
   haberin BAŞLIĞI ve ANA KONUSU neyse ona göre kategorize et.

C) STRATEJİK KURUM/DEVLET SALDIRISI
   Saldırının HEDEF kurumu stratejik değer taşımalıdır:
   • Devlet başkanlığı, bakanlık, meclis, büyükelçilik, istihbarat servisi
   • Uluslararası kurum: Avrupa Konseyi, Avrupa Parlamentosu, BM ajansları,
     Uluslararası Adalet Divanı, IMF, NATO karargahı, AB kurumları
   • Askeri sistem, savunma müteahhidi, kritik altyapı operatörü
   → Örnekler: Avrupa Konseyi hacklenmesi, ABD Savunma Bakanlığı ihlali,
     NATO üyesi ülkenin seçim sistemine saldırı

D) HUKUK & DÜZENLEYICI GELİŞME (siber güvenlik boyutu olan)
   • Mahkeme kararı, kovuşturma, iade, tutuklama (siber casusluk / casus yazılım)
   • Büyük tech firması vs. mercenary spyware davası (Meta vs. NSO Group gibi)
   • Yeni siber güvenlik yasası, ulusal güvenlik direktifi, istihbarat paylaşım anlaşması
   • Devlet destekli hacker grubuna uluslararası yaptırım

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KATEGORİ 2 — İKİNCİL ÖNCELİK (Kategori 1 dolmadığında)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Kategori 1'den 3 haber bulunamazsa buradan tamamla:

E) TEDARİK ZİNCİRİ SALDIRISI (Supply Chain)
   Yazılım veya donanım tedarik zinciri aracılığıyla çok sayıda kurumu/ülkeyi
   etkileyen saldırılar ulusal güvenlik tehdidi sayılır:
   • Yaygın açık kaynak paketi, geliştirici aracı veya güvenlik yazılımına
     arka kapı/zararlı kod enjeksiyonu (SolarWinds, XZ Utils türü olaylar)
   • Büyük yazılım sağlayıcısının güncelleme mekanizmasının ele geçirilmesi
   • Donanım veya firmware düzeyinde tedarik zinciri manipülasyonu
   • Geliştiricileri, CI/CD sistemlerini veya kod depolarını (npm, PyPI, GitHub)
     hedef alan ve geniş ölçekte yayılan kampanyalar

F) MİLLİ GÜVENLİĞİ DOĞRUDAN ETKİLEYEN BÜYÜK VERİ İHLALİ
   Ölçek veya içerik açısından devlet/toplum düzeyinde sonuç doğuran ihlaller:
   • Devlet kurumu, ordu, istihbarat servisi veya savunma müteahhidine ait veri sızıntısı
   • Pasaport, kimlik, biyometrik, sağlık kaydı, seçmen kütüğü gibi hassas ulusal
     veri tabanlarının ele geçirilmesi
   • 50 milyon+ vatandaşı etkileyen platform veya telekom ihlali
     (finansal veri, konum, iletişim içeriği gibi kritik veri türleri)
   • İstihbarat operasyonunu, izleme/casusluk faaliyetini kolaylaştırabilecek
     büyük ölçekli kişisel veri sızıntısı (gazeteciler, aktivistler, kamu görevlileri)

G) DİĞER STRATEJİK HABERLER
   • APT grubu veya devlet destekli tehdit aktörünün yeni kampanyası/tekniği
   • Kritik altyapı (enerji şebekesi, hastane ağı, finans sistemi) saldırısı
   • Stratejik önemi olan büyük fidye yazılımı saldırısı (hükümet veya kritik hizmet)
   • Geniş çaplı devlet destekli dezenformasyon / etki operasyonu

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KATEGORİ 3 — FALLBACK (sakin günler için, son seçenek)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Kategori 1 ve 2'den toplam 3 haber çıkmıyorsa kalan yerleri buradan tamamla.
Günün haberleri arasından en yüksek pratik etkiye sahip olanları seç:
   • Yaygın kullanılan tüketici yazılımını (tarayıcı, işletim sistemi, ofis paketi,
     VPN, antivirüs) etkileyen aktif istismar altındaki kritik güvenlik açığı
   • Çok sayıda kurumu veya sektörü etkileyen büyük fidye yazılımı dalgası
   • Milyonlarca kullanıcıyı etkileyen ve şifre/finansal veri içeren büyük platform ihlali
     (Meta, Google, X, LinkedIn, büyük banka gibi küresel ölçekli platformlar)
   • Dünya genelinde haber değeri taşıyan büyük siber suç/dolandırıcılık operasyonu
   • Önemli güvenlik araştırması: yeni saldırı tekniği, kritik protokol zafiyeti keşfi

Kategori 3'ten seçim yaparken haberin okuyucuya pratik uyarı değeri taşıdığından emin ol.
"Seçilmez" listesindeki haber bu kategoride de alınmaz.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KESİNLİKLE SEÇİLMEZ — TOP 3'E GİRMEZ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Aşağıdaki haber türleri ne kadar büyük görünürse görünsün top 3'e ALINMAZ:

✗ Sıradan bireyleri veya tüketicileri hedef alan veri ihlalleri
   — Tanınmamış e-ticaret, uygulama, forum gibi platformlardaki sızdırılan kullanıcı adı/şifre/e-posta
   — Stratejik kurumla bağı olmayan ihlaller, etkilenen kişi sayısı ne olursa olsun
   — Örnek: "X alışveriş sitesi 2.6 milyon kullanıcı verisi sızdırdı" → SEÇİLMEZ

✗ Ticari amaçlı rutin zararlı yazılım haberleri (devlet bağlantısı yoksa)
   — Adware, browser hijacker, crimeware, finansal dolandırıcılık kötü yazılımı
   — Bilgi çalan (infostealer) zararlı yazılımların rutin keşfi (kampanya yoksa)

✗ Saf teknik/ürün haberleri
   — CVE/yama/güvenlik açığı tespiti (aktif devlet/APT istismarı yoksa)
   — Ürün lansmanı, beta sürüm, güvenlik aracı duyurusu

✗ İçerik haberleri
   — Genel tavsiye makalesi, röportaj, konferans duyurusu, pazar araştırması

✗ Siber boyutu olmayan saf diplomatik/askeri/siyasi haberler
   — Ateşkes, barış anlaşması, askeri diyalog kanalı, dekonfliction hattı
   — Silah anlaşması, konvansiyonel saldırı/savunma operasyonu
   — Diplomatik ziyaret, uluslararası müzakere (siber gündem yoksa)
   — Örnekler: "ABD-İran Doha dekonfliction hattı" → SEÇİLMEZ
                "NATO üyesi ülkeye silah yardımı" → SEÇİLMEZ
                "BM Güvenlik Konseyi ateşkes kararı" → SEÇİLMEZ

KURAL: Bir haber "büyük rakam" içerse de (milyonlarca kullanıcı, milyarlarca dolar zarar)
ya da çok stratejik görünse de, özünde siber boyutu yoksa top 3'e GİREMEZ.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GEÇMİŞ GÜNLERDE İŞLENEN OLAYLAR — TEKRAR KRİTİĞE ALMA (MÜKERRER ENGELİ)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Aşağıdaki olaylar SON GÜNLERDE zaten rapor edilmiştir. Bunlardan herhangi
biriyle AYNI olay/kampanya/operasyon (aynı kod adı, aynı zararlı yazılım,
ya da aynı aktör + aynı mağdur eşleşmesi) bugün:
   • farklı bir kaynaktan gelse,
   • farklı rakamlarla (ör. "73 bin" yerine "110 milyon") sunulsa,
   • biraz güncellenmiş/yeni gelişme olarak yazılsa bile
TOP 3'E ALINMAZ. Mükerrer olaylar kritiğe çıkmaz; günün GERÇEKTEN YENİ
en kritik haberini seç.
🔑 GÜÇLÜ SİNYAL: Kampanya/operasyon/zararlı yazılım KOD ADI (ör. "FortiBleed",
   "Amadey", "StealC", "STOCKSTAY") aşağıdaki listede geçiyorsa → MÜKERRER, ELE.

SON GÜNLERDE RAPORLANAN OLAYLAR:
{recent_events if recent_events else "(Geçmiş kayıt yok)"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KARAR AKIŞI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
0. "Geçmiş günlerde işlenen olaylar" listesiyle eşleşen TÜM adayları en baştan ELE.
   (Mükerrer haberler hiçbir kategoride değerlendirilmez.)

1. Kategori 1'den (A→B→C→D) adayları say.
   → 3 veya daha fazla aday: ilk 3'ü seç, bitti.
   → 1-2 aday: bunları al, kalan yerleri adım 2'den tamamla.
   → 0 aday: adım 2'ye geç.

2. Kategori 2'den adayları say.
   → Kategori 1+2 toplamı 3 veya daha fazla: ilk 3'ü doldur, bitti.
   → Kategori 1+2 toplamı 1-2: bunları al, kalan yerleri adım 3'ten tamamla.
   → Kategori 1+2 toplamı 0: adım 3'e geç.

3. Kategori 3'ten en iyi adayları seçerek 3'ü tamamla.

4. Her adımda: "Seçilmez" listesindeki ve "Geçmiş günlerde işlenen olaylar"
   listesindeki haber KESİNLİKLE alınmaz, başka seçenek olmasa bile.

SADECE JSON FORMATINDA YANIT VER — başka hiçbir şey yazma:
{{"top3": [42, 7, 15]}}

HABERLER:
{articles_brief}"""


def get_executive_summary_prompt(articles_brief, source_count=None, news_count=None):
    """
    Yönetici Özeti: O günün en önemli 9 haberini (top3 + sonraki 6) tek bir
    akıcı paragrafta özetler.
    articles_brief: "=== HABER N ===\\nBaşlık: ...\\nÖzet: ...\n" formatında string.
    source_count, news_count: artık kullanılmıyor (geriye dönük uyumluluk için imzada bırakıldı).
    """
    return f"""Sen bir siber güvenlik istihbarat bülteni editörüsün. Görevin: aşağıda verilen, o günün EN ÖNEMLİ haberlerini tek bir AKICI YÖNETİCİ ÖZETİ paragrafında toparlamak.

⚠️ DİL KURALI: Çıktı YALNIZCA TÜRKÇE olacak. İngilizce kelime, cümle veya paragraf YASAKTIR. Haberler İngilizce olsa bile özet kesinlikle Türkçe yazılacak. (Şirket adları, CVE kodları ve ürün adları orijinal kalabilir.)

GÖREV:
- Paragrafa güncel siber tehdit ortamına bağlamsal bir GİRİŞ CÜMLESİYLE başla.
  ⚠️ ZORUNLU: Giriş cümlesinde mutlaka "son 48 saat", "son iki gün", "geçen 48 saat" veya
  benzeri bir ZAMAN REFERANSI yer almalıdır. Zaman referansı olmayan giriş kabul edilmez.
  Örnek çerçeveler (kelimesi kelimesine kopyalama; aynı tonu koruyarak doğal biçimde yeniden ifade et):
  • "Son 48 saatin siber güvenlik gündeminde belirleyici olan gelişmeler değerlendirildiğinde..."
  • "Geçen 48 saat içinde siber tehdit ortamında yaşanan gelişmeler ele alındığında..."
  • "Son iki günde küresel siber güvenlik gündemini şekillendiren başlıca olaylar incelendiğinde..."
  ⛔ YASAK GİRİŞLER: "Bugünün…", "Bugün siber…", "Bu günün…", "Küresel siber tehdit ortamında öne çıkan…" (zaman referansı olmadan) ile başlayan ifadeler KULLANILMAZ.
  Giriş cümlesi bağlama uygun ve özgün olsun; her gün aynı kalıpla başlama.
- Giriş cümlesinin ardından, verilen haberleri TEK BİR paragraf içinde özetlemeye devam et (madde işareti, başlık, alt başlık YOK).
- Bir yönetici tek okuyuşta, son 48 saatte siber güvenlik dünyasında yaşanan en önemli gelişmeler hakkında doğrudan fikir sahibi olabilmeli.
- Girişten sonra en önemli/stratejik gelişmelerle devam et, ardından diğer önemli haberlere geç.
- CÜMLE YAPISI: Bir cümlede en fazla iki gelişme bağlanabilir ("ve", "ayrıca", "öte yandan" ile). Üç veya daha fazla olayı tek cümlede ZİNCİRLEME. Yan cümle sayısı bir cümlede en fazla bir tane.
- Resmî ve dikkatli bir Türkçe kullan; özensiz ifadelerden kaçın.
- UZUNLUK: 130-190 kelime. Tek paragraf.
- Yalnızca verilen haberlerdeki bilgileri kullan; uydurma ekleme yapma.
- Kaynak adı, URL, "HABER N" gibi referanslar YAZMA — sadece akıcı metin.

SADECE JSON FORMATINDA YANIT VER — başka hiçbir şey yazma:
{{"ozet": "Küresel siber tehdit ortamında öne çıkan gelişmeler incelendiğinde... şeklinde tek paragraf özet."}}

HABERLER:
{articles_brief}"""


def get_title_rescue_prompt(title, body):
    """
    İçerik filtresine takılıp/analiz başarısız olup HAM İNGİLİZCE kalan tek bir
    haberi YANSIZ ÇEVİRİ çerçevesiyle Türkçeye dönüştürür. Analitik 'derin analiz'
    yerine düz çeviri çerçevesi kullanıldığından güvenlik filtresine takılma
    olasılığı düşüktür.
    title: orijinal (İngilizce) başlık. body: makalenin ilk ~220 kelimesi.
    """
    return f"""Aşağıdaki İngilizce siber güvenlik haberini Türkçeye çevir. Bu yalnızca bir DİL ÇEVİRİSİ görevidir; içerik üzerinde değerlendirme/yorum yapma.

⚠️ DİL KURALI: Çıktı YALNIZCA TÜRKÇE olacak. (Şirket adları, CVE kodları, ürün adları orijinal kalabilir.)

İKİ ŞEY ÜRET:
1. TR_BASLIK: Türkçe isim-fiil (mastar) başlığı
   - 5-9 kelime, her kelimenin ilk harfi büyük
   - ZORUNLU FORMAT: "[Özne]'nin [Nesne]'yi [eylem-ması/mesi]"
   - Bitiş: -ması, -mesi, -ılması, -ilmesi, -ınması, -ünmesi
   - YASAK: -mıştır, -edilmiştir gibi eylem cümlesi yapıları

2. PARAGRAF: Haberin resmi Türkçe özeti
   - MİNİMUM 110 kelime, tek paragraf
   - SADECE verilen metindeki bilgileri kullan; tahmin/yorum ekleme
   - Resmi dil: yapılmıştır, belirtilmektedir, tespit edilmiştir

SADECE JSON FORMATINDA YANIT VER — başka hiçbir şey yazma:
{{"tr_title": "...", "paragraph": "..."}}

ORİJİNAL BAŞLIK: {title}

METİN:
{body}"""


def get_deep_analysis_prompt(articles_full):
    """
    Pass 2: Top-10 haberin TAM metni → Türkçe başlık + 120+ kelime paragraf (JSON).
    articles_full: "=== HABER ID: N ===\\nKaynak: ...\\nTAM METİN:\\n..." formatında string.
    """
    return f"""Sen siber güvenlik analistisin. Aşağıdaki haberleri TAM METİN ile analiz et.

⚠️ DİL KURALI: Tüm çıktılar YALNIZCA TÜRKÇE olacak. İngilizce kelime, cümle veya paragraf YASAKTIR. Haberler İngilizce olsa bile yanıt kesinlikle Türkçe yazılacak.

Her haber için iki şey üret:
1. TR_BASLIK: Türkçe isim-fiil (mastar) başlığı
   - 5-9 kelime, her kelimenin ilk harfi büyük
   - ZORUNLU FORMAT: "[Özne]'nin/[Özne]'ın [Nesne]'yi [eylem-ması/mesi]"
   - Bitiş: -ması, -mesi, -ılması, -ilmesi, -ınması, -ünmesi
   - Örnekler: "FBI'ın Outsider Enterprise Kimlik Avı Ağını Çökertmesi"
               "Meta'nın NSO Group'u WhatsApp Kullanıcılarını Hedeflemekle Suçlaması"
               "ShinyHunters'ın Avrupa Konseyi Verilerini Sızdırması"
               "Microsoft Exchange'de CVE-2024-1234 Açığının Keşfedilmesi"
   - YASAK: -mıştır, -edilmiştir, -tespit edilmiştir gibi eylem cümlesi yapıları
   - Somut detay: şirket/CVE/ülke adı dahil et

2. PARAGRAF: Resmi Türkçe özet
   - MİNİMUM 120 kelime (daha az yazarsan YANLIŞ sayılır — say ve kontrol et)
   - SADECE kaynak metinde olan bilgileri yaz — tahmin, yorum, çıkarım YASAK
   - Resmi dil: yapılmıştır, edilmiştir, belirtilmektedir, tespit edilmiştir

   ── ODAK KURALI (her haber için zorunlu) ───────────────────────────────────
   Bu paragrafın amacı bir TEHDİT İSTİHBARATI değerlendirmesidir, teknik bir
   rapor DEĞİLDİR. Okuyucu "bu neden stratejik/jeopolitik açıdan önemli?"
   sorusunun cevabını almalı.

   Yazmadan önce kaynak metinde şu soruları sor ve cevaplarını paragrafın
   OMURGASI yap:
     (A) SALDIRGAN KİM? Devlet bağlantısı, hangi ülke, istihbarat/askeri yapı,
         özel müteahhit mi APT grubu mu, bilinen diğer isimleri/geçmişi.
     (B) HEDEF KİM? Hangi ülkelerin hükümetleri/kritik kurumları (dış işleri,
         savunma, telekom, enerji), kaç ülke, hangi sektör.
     (C) AMAÇ NE? Casusluk, veri hırsızlığı, sabotaj, altyapıya önceden
         konumlanma, etki operasyonu.
     (D) JEOPOLİTİK ANLAM NE? Hangi ülkeler arası gerilim/rekabetle örtüşüyor,
         neden şimdi, kime karşı avantaj sağlıyor.

   TEKNİK DETAY POLİTİKASI:
     • Paragraf neredeyse tamamen A/B/C/D eksenine yazılır.
     • Teknik ayrıntılar (CVE numarası, exploit/malware/driver dosya adları,
       DLL side-loading zinciri, C2 protokol tipi, kayıt defteri anahtarları,
       sürüm numaraları) KURAL OLARAK YAZILMAZ.
     • İstisna: bir teknik unsur stratejik anlamı DOĞRUDAN değiştiriyorsa
       (ör. "aktif istismar altında bir sıfır-gün" veya "tedarik zinciri
       güncelleme mekanizmasının ele geçirilmesi"), o unsuru TEK CÜMLEYLE,
       sade dille, stratejik sonucuna bağlayarak ver — teknik liste yapma.
     • Hiçbir koşulda paragrafın yarısından fazlası teknik anlatı olamaz.

   NOT: Kaynak metin A/B/C/D'nin hiçbirine cevap vermiyorsa (saf teknik/ürün
   haberi), olayın kimi, neyi, ne ölçekte etkilediğini sade dille anlat; yine
   teknik prosedür ayrıntılarına boğma.
   ───────────────────────────────────────────────────────────────────────────

   ── TEKRAR ÖNLEME — AYNI AKTÖR ÇOKLU HABER (zorunlu) ───────────────────────
   Bu sette BİRDEN FAZLA haber AYNI tehdit aktörünü/grubunu konu alıyorsa
   (aynı isim veya kaynak metinde AÇIKÇA belirtilen aynı takma ad — örn.
   "The Gentlemen" = "Storm-2697") ve bunlardan biri grubun GENEL PROFİLİ
   (yükselişi, yöntemleri, kurban sayısı/kapsamı) diğeri o grubun SOMUT BİR
   SALDIRISI (belirli bir mağdur) ise:
     • Grubun genel tanıtımını (ne zaman kuruldu, kaç kurban, AI/infostealer
       kullanımı, ortaklık/komisyon modeli, sektörel hedef kalıbı vb.) YALNIZCA
       profil haberinde anlat.
     • Somut saldırı haberinde bu genel tanıtımı TEKRARLAMA; grubu adıyla anıp
       kimliğini bilinen bağlam gibi geç ve TÜM kelimeleri O SALDIRIYA özgü
       detaya ayır: hangi mağdur, hangi sektör, operasyonel/ekonomik etki,
       kritik altyapı boyutu.
     • Kelime minimumu yine geçerlidir — boşalan yeri dolgu cümleyle değil,
       mağdura/etkiye özgü somut bilgiyle doldur.
   ⚠️ Bu kuralı YALNIZCA aktör adı/takma adı kaynak metinlerde açıkça aynıysa
   uygula. Emin değilsen, aktör farklıysa veya yalnızca tek haber aktörden söz
   ediyorsa hiçbir şey değiştirme; her haberi bağımsız yaz.
   ───────────────────────────────────────────────────────────────────────────

   - 5N1K'yı stratejik çerçevede kapsa (kim, kime, ne amaçla, hangi bağlamda)

   ⛔⛔ UYDURMA DEĞERLENDİRME / YORUM CÜMLESİ — KESİN YASAK (EN ÖNEMLİ KURAL) ⛔⛔
   Paragrafın HİÇBİR yerine, ÖZELLİKLE SONUNA, kaynak metinde AÇIKÇA yazmayan
   bir "önem/anlam/sonuç değerlendirmesi" cümlesi EKLEME. Senin yorumun, çıkarımın,
   "bu ne anlama geliyor", "bu ne kadar önemli", "neyi teyit/kanıt ediyor" türünden
   YARGILARIN tamamen YASAKTIR. Paragrafta YALNIZCA kaynak metinde yazan olgular
   (kim, ne yaptı, kime, ne zaman, hangi sayı/kurum/teknik önlem) yer alır.
   • Bu, raporda en sık yapılan ve en çok şikâyet edilen hatadır — ASLA yapma.
   • Örnek YASAK kapanış (ASLA böyle bitirme): "Hükümetin bu yaklaşımı, kuantum
     teknolojilerini ... bir beka meselesi olarak gördüğünü teyit etmektedir."
     Bu cümle kaynakta yoktur; senin uydurman bir değerlendirmedir.

   - ⛔ Paragrafı, ÖZNESİ NE OLURSA OLSUN ("Bu olay/durum/gelişme/saldırı/
     operasyon/yaklaşım...", "Söz konusu...", "Hükümetin bu...", "Yaşanan bu..."
     fark etmez) aşağıdaki fiillerden BİRİYLE BİTEN bir cümleyle BİTİRME:
       göstermektedir, göstermiştir, ortaya koymaktadır, ortaya koymuştur,
       vurgulamaktadır, kanıtlamaktadır, teyit etmektedir, yansıtmaktadır,
       gözler önüne sermektedir, anlamına gelmektedir, işaret etmektedir,
       teşkil etmektedir, önem arz etmektedir, önem taşımaktadır, darbe vurmuştur,
       dikkat çekmektedir, haline geldiğini göstermektedir/kanıtlamaktadır.
   - Son cümle, kaynakta geçen SOMUT bir olgu olacak (kim ne yaptı, hangi sayı,
     hangi tarih, hangi kurum, hangi teknik önlem) — soyut "önemlidir/stratejiktir/
     kritiktir" yargısı DEĞİL.

SADECE JSON FORMATINDA YANIT VER — başka hiçbir şey yazma:
{{
  "3": {{
    "tr_title": "Microsoft Exchange'de CVE-2024-1234 Kritik Açığının Tespit Edilmesi",
    "paragraph": "Microsoft, Exchange Server ürününde..."
  }},
  "7": {{
    "tr_title": "...",
    "paragraph": "..."
  }}
}}

HABERLER:
{articles_full}"""


def get_summary_batch_prompt(articles_full):
    """
    Pass 3: Bir batch haberin TAM METNİ → Türkçe başlık + 100+ kelime paragraf (JSON).
    articles_full: "=== HABER ID: N ===\\nKaynak: ...\\nTAM METİN:\\n..." formatında string.
    """
    return f"""Sen siber güvenlik analistisin. Aşağıdaki haberleri TAM METİN ile analiz et.

⚠️ DİL KURALI: Tüm çıktılar YALNIZCA TÜRKÇE olacak. İngilizce kelime, cümle veya paragraf YASAKTIR. Haberler İngilizce olsa bile yanıt kesinlikle Türkçe yazılacak.

Her haber için:
1. TR_BASLIK: Türkçe isim-fiil (mastar) başlığı
   - 5-9 kelime, her kelimenin ilk harfi büyük
   - ZORUNLU FORMAT: "[Özne]'nin/[Özne]'ın [Nesne]'yi [eylem-ması/mesi]"
   - Bitiş: -ması, -mesi, -ılması, -ilmesi, -ınması, -ünmesi
   - Örnekler: "FBI'ın Outsider Enterprise Kimlik Avı Ağını Çökertmesi"
               "Meta'nın NSO Group'u WhatsApp Kullanıcılarını Hedeflemekle Suçlaması"
               "ShinyHunters'ın Avrupa Konseyi Verilerini Sızdırması"
               "Google Chrome'da Sıfır Gün Açığının Aktif Olarak İstismar Edilmesi"
   - YASAK: -mıştır, -edilmiştir, -tespit edilmiştir gibi eylem cümlesi yapıları
   - Somut detay: şirket/CVE/ülke adı dahil et

2. PARAGRAF: Resmi Türkçe özet
   - MİNİMUM 120 kelime (daha az yazarsan YANLIŞ sayılır — say ve kontrol et)
   - SADECE kaynak metinde olan bilgileri yaz — tahmin, yorum, çıkarım YASAK
   - Resmi dil: yapılmıştır, edilmiştir, belirtilmektedir, tespit edilmiştir

   ── ODAK KURALI (her haber için zorunlu) ───────────────────────────────────
   Bu paragrafın amacı bir TEHDİT İSTİHBARATI değerlendirmesidir, teknik bir
   rapor DEĞİLDİR. Okuyucu "bu neden stratejik/jeopolitik açıdan önemli?"
   sorusunun cevabını almalı.

   Yazmadan önce kaynak metinde şu soruları sor ve cevaplarını paragrafın
   OMURGASI yap:
     (A) SALDIRGAN KİM? Devlet bağlantısı, hangi ülke, istihbarat/askeri yapı,
         özel müteahhit mi APT grubu mu, bilinen diğer isimleri/geçmişi.
     (B) HEDEF KİM? Hangi ülkelerin hükümetleri/kritik kurumları (dış işleri,
         savunma, telekom, enerji), kaç ülke, hangi sektör.
     (C) AMAÇ NE? Casusluk, veri hırsızlığı, sabotaj, altyapıya önceden
         konumlanma, etki operasyonu.
     (D) JEOPOLİTİK ANLAM NE? Hangi ülkeler arası gerilim/rekabetle örtüşüyor,
         neden şimdi, kime karşı avantaj sağlıyor.

   TEKNİK DETAY POLİTİKASI:
     • Paragraf neredeyse tamamen A/B/C/D eksenine yazılır.
     • Teknik ayrıntılar (CVE numarası, exploit/malware/driver dosya adları,
       DLL side-loading zinciri, C2 protokol tipi, kayıt defteri anahtarları,
       sürüm numaraları) KURAL OLARAK YAZILMAZ.
     • İstisna: bir teknik unsur stratejik anlamı DOĞRUDAN değiştiriyorsa
       (ör. "aktif istismar altında bir sıfır-gün" veya "tedarik zinciri
       güncelleme mekanizmasının ele geçirilmesi"), o unsuru TEK CÜMLEYLE,
       sade dille, stratejik sonucuna bağlayarak ver — teknik liste yapma.
     • Hiçbir koşulda paragrafın yarısından fazlası teknik anlatı olamaz.

   NOT: Kaynak metin A/B/C/D'nin hiçbirine cevap vermiyorsa (saf teknik/ürün
   haberi), olayın kimi, neyi, ne ölçekte etkilediğini sade dille anlat; yine
   teknik prosedür ayrıntılarına boğma.
   ───────────────────────────────────────────────────────────────────────────

   - 5N1K'yı stratejik çerçevede kapsa (kim, kime, ne amaçla, hangi bağlamda)

   ⛔⛔ UYDURMA DEĞERLENDİRME / YORUM CÜMLESİ — KESİN YASAK (EN ÖNEMLİ KURAL) ⛔⛔
   Paragrafın HİÇBİR yerine, ÖZELLİKLE SONUNA, kaynak metinde AÇIKÇA yazmayan
   bir "önem/anlam/sonuç değerlendirmesi" cümlesi EKLEME. Senin yorumun, çıkarımın,
   "bu ne anlama geliyor / ne kadar önemli / neyi teyit-kanıt ediyor" türünden
   YARGILARIN tamamen YASAKTIR. Yalnızca kaynak metinde yazan olgular yer alır.
   - ⛔ Paragrafı, ÖZNESİ NE OLURSA OLSUN ("Bu olay/durum/gelişme/saldırı/yaklaşım",
     "Söz konusu...", "Hükümetin bu..." fark etmez) şu fiillerden biriyle BİTEN bir
     cümleyle BİTİRME: göstermektedir, göstermiştir, ortaya koymaktadır, ortaya
     koymuştur, vurgulamaktadır, kanıtlamaktadır, teyit etmektedir, yansıtmaktadır,
     gözler önüne sermektedir, anlamına gelmektedir, işaret etmektedir, teşkil
     etmektedir, önem arz etmektedir, önem taşımaktadır, darbe vurmuştur, dikkat
     çekmektedir.
   - Son cümle, kaynakta geçen SOMUT bir olgu olacak (kim ne yaptı, hangi sayı/
     tarih/kurum/teknik önlem) — soyut "önemlidir/stratejiktir" yargısı DEĞİL.

SADECE JSON FORMATINDA YANIT VER — başka hiçbir şey yazma:
{{
  "42": {{
    "tr_title": "Google Chrome'da Sıfır Gün Açığının Aktif Olarak İstismar Edilmesi",
    "paragraph": "Google, Chrome tarayıcısında..."
  }},
  "1": {{
    "tr_title": "...",
    "paragraph": "..."
  }}
}}

HABERLER:
{articles_full}"""

# Haber kaynakları
NEWS_SOURCES = {
    'The Hacker News': 'https://feeds.feedburner.com/TheHackersNews',
    'BleepingComputer': 'https://www.bleepingcomputer.com/feed/',
    'Krebs on Security': 'https://krebsonsecurity.com/feed/',
    # 'Threatpost': 'https://threatpost.com/feed/',  # Yıllardır ölü — 2022'den beri yayın yok, site erişilemez durumda
    'Security Affairs': 'https://securityaffairs.com/feed',
    'Graham Cluley': 'https://grahamcluley.com/feed/',
    # 'SANS ISC': 'https://isc.sans.edu/rssfeed.xml',  # isc.sans.edu tüm domain GitHub Actions IP'lerini engelliyor (2026-06'dan beri HTTP 200 + HTML/boş içerik → XML parse hatası)
    'Recorded Future': 'https://www.recordedfuture.com/feed',
    'Cyberscoop': 'https://cyberscoop.com/feed/',
    'The Register': 'https://www.theregister.com/security/cyber_crime/headlines.atom',
    'TechCrunch Security': 'https://techcrunch.com/category/security/feed/',
    'CSO Online': 'https://www.csoonline.com/feed/',
    'Infoblox Blog': 'https://blogs.infoblox.com/feed/',
    # Yeni eklenen kaynaklar
    'Dark Reading': 'https://www.darkreading.com/rss.xml',
    'SecurityWeek': 'https://feeds.feedburner.com/securityweek',
    'Help Net Security': 'https://www.helpnetsecurity.com/feed',
    'The Record': 'https://therecord.media/feed/',
    'Talos Intelligence': 'https://blog.talosintelligence.com/rss/',  # Ghost CMS — eski feeds/all.atom.xml 2026-06 itibarıyla 404
    'Unit 42': 'https://unit42.paloaltonetworks.com/feed/',
    # 'Sophos News': 'https://news.sophos.com/en-us/feed/',  # Sophos CDN GitHub Actions IP'lerini engelliyor (2026-06'dan beri Timeout)
    # Devlet siber güvenlik kurumları — joint advisory ve APT atıfları için yüksek stratejik değer
    # 'CISA': 'https://www.cisa.gov/cybersecurity-advisories/all.xml',  # cisa.gov tüm domain GitHub Actions IP'lerini engelliyor (2026-06-18'den beri kalıcı HTTP 403)
    'NCSC UK': 'https://www.ncsc.gov.uk/api/1/services/v1/all-rss-feed.xml',
    'CERT-EU': 'https://cert.europa.eu/publications/security-advisories-rss',
    # Stratejik / jeopolitik / istihbari odaklı kaynaklar (kullanıcı tarafından doğrulandı 2026-06)
    # Bu grup; APT atıfı, ulus-devlet operasyonları, ticari casus yazılım ve
    # gözetim/jeopolitik soruşturmalara ağırlık verir — raporun stratejik çekirdeği.
    'Microsoft Security': 'https://www.microsoft.com/en-us/security/blog/feed/',
    'Bellingcat': 'https://www.bellingcat.com/feed/',
    'Citizen Lab': 'https://citizenlab.ca/feed/',
    'Mandiant (Google Cloud)': 'https://feeds.feedburner.com/threatintelligence/pvexyqv7v0v',
    'CrowdStrike': 'https://www.crowdstrike.com/blog/feed/',
    'Securelist (Kaspersky)': 'https://securelist.com/feed/',
    'The DFIR Report': 'https://thedfirreport.com/feed/',
    'ANSSI (CERT-FR)': 'https://www.cert.ssi.gouv.fr/feed/',
    'BSI': 'https://www.bsi.bund.de/SiteGlobals/Functions/RSSFeed/RSSNewsfeed/RSSNewsfeed_Presse_Veranstaltungen.xml',
    'NIST': 'https://www.nist.gov/news-events/news/rss.xml',
    'SentinelOne Labs': 'https://www.sentinelone.com/labs/feed/',
    'Proofpoint Threat Insight': 'https://www.proofpoint.com/us/rss.xml',
    'Schneier on Security': 'https://www.schneier.com/blog/atom.xml',
    # Bölgesel / Orta Doğu jeopolitik kaynaklar (kullanıcı tarafından doğrulandı 2026-06-25)
    # Eklenme gerekçesi: İran iç bankacılık kesintisi (Bank Melli/Saderat/Tejarat) gibi
    # bölgesel siber-jeopolitik olaylar Batı merkezli feed'lerde ya hiç ya da gecikmeli
    # yer alıyordu. Bu grup İran/İsrail/Orta Doğu kapsamasındaki boşluğu kapatır.
    # NOT: Bu ortamın egress politikası tüm dış haber domainlerini engellediği için
    # (mevcut feed'ler dahil 403) doğrulama kullanıcı tarafından dışarıdan yapılmıştır.
    'The Cyber Express': 'https://www.thecyberexpress.com/feed/',
    'Industrial Cyber': 'https://industrialcyber.co/feed/',
    'Times of Israel': 'https://www.timesofisrael.com/feed/',
    'IranWire': 'https://iranwire.com/en/feed/',
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
        'min_points':    3,    # search endpoint (relevance) ile birlikte düşürüldü (önceki: 5)
        'limit':         30,   # Daha fazla çek, combined score ile sırala (önceki: 25)
        'comment_weight': 3,   # combined_score = points + comments * 3
    },
    'github_advisories': {
        'min_severity': ['critical', 'high', 'medium'],
        'limit':  10,          # Çekilecek max advisory sayısı
        'top_n':   1,          # Ana havuza eklenecek max GitHub advisory (önceki: 2)
    },
    'reddit': {
        # RSS hot feed — API key gerektirmez, güncel veri, Azure/GH Actions uyumlu
        # PullPush arşivi ~10 ay geride kaldığı için RSS'e geçildi
        'subreddits': ['cybersecurity', 'netsec'],
        'size':       25,   # RSS limit (her subreddit için)
        'hours_back': 48,   # Son 48 saatin postları
        'top_n':      5,    # Sosyal sinyal kutusuna eklenecek max Reddit postu
    },
}

# URL kara listesi — bu desenleri içeren RSS makaleleri atlanır
# (newsletter özeti, haftalık digest gibi liste sayfaları gerçek haber değil)
SKIP_URL_PATTERNS = [
    'newsletter-round-',       # Security Affairs: "Security Affairs Newsletter Round 566"
    'newsletter-edition',      # Security Affairs: "-international-edition"
    'weekly-roundup',          # Genel haftalık özet sayfaları
    'weekly-digest',           # Genel digest sayfaları
    '/newsletter/',            # /newsletter/ path içeren URL'ler
    'this-week-in-security',   # Genel "this week" özet sayfaları
]

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
    'Cyberscoop': [{'class': 'article-body'}, {'class': 'post-content'}, {'class': 'entry-content'}],
    'Recorded Future': [{'class': 'article-body'}, {'class': 'blog-content'}, {'class': 'entry-content'}],
    # Stratejik kaynaklar — WordPress tabanlılar entry-content kullanır; eşleşmezse
    # fetch_full_article generic <article>/<main> fallback'ine düşer (hata üretmez).
    'Bellingcat': [{'class': 'entry-content'}, {'class': 'post-content'}],
    'Citizen Lab': [{'class': 'entry-content'}, {'class': 'post-content'}],
    'Securelist (Kaspersky)': [{'class': 'entry-content'}, {'class': 'js-reading-content'}],
    'The DFIR Report': [{'class': 'entry-content'}, {'class': 'post-content'}],
    'CrowdStrike': [{'class': 'entry-content'}, {'class': 'article-body'}, {'class': 'post-content'}],
    'ANSSI (CERT-FR)': [{'class': 'article-content'}, {'class': 'content'}],
}

# ===== ÖNEM SCORING SİSTEMİ (v2.0) — ⚠️ KULLANILMIYOR (DEAD CODE) =====
# ⚠️ DİKKAT: Bu iki sözlük (IMPORTANCE_WEIGHTS + DETECTION_PATTERNS) mevcut
# boru hattında HİÇBİR yerde kullanılmıyor (main.py / api / src genelinde import
# yok; yalnızca tests/test_importance_scoring.py yapısal olarak doğruluyor).
# Sıralama/seçim tamamen LLM promptlarıyla (get_ranking_prompt /
# get_top3_selection_prompt) yapılır. Buradaki jenerik anahtar kelimeler
# ('nato', 'ukraine', 'russia' vb.) bugünkü "siber-boyut zorunluluğu"
# felsefesiyle ÇELİŞİR; yanlışlıkla boru hattına bağlanırsa siber boyutu
# olmayan jeopolitik haberleri yükseltebilir. Yeniden etkinleştirmeden ÖNCE
# anahtar kelimeleri siber-boyut kuralına göre gözden geçirin.
IMPORTANCE_WEIGHTS = {
    'nato_turkey_summit': {
        'weight': 130,
        'description': 'SADECE doğrudan NATO Türkiye Zirvesi (Temmuz 2026) haberleri — zirveyi konu/hedef alanlar. Genel NATO haberleri dahil DEĞİL.',
        'keywords': ['nato summit', 'nato turkey summit', 'nato türkiye zirvesi', 'nato antalya', 'nato 2026 summit', 'nato zirvesi', 'türkiye zirvesi', 'summit security']
    },
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
    'sectors': r'\b(healthcare|health|hospital|energy|power|financ(?:e|ial)|bank|government|military|defense)\b',
    'countries': r'\b(Ukraine|Russia|China|Iran|Korea|Israel|US|USA|UK|United States)\b',
}

def get_quality_review_prompt(articles_content):
    """
    Pass 5: Üretilmiş Türkçe içerikleri kalite kontrol eder.
    articles_content: "=== HABER ID: N ===\\nTR Başlık: ...\\nParagraf: ...\\nKaynak Var: evet/hayır\n" formatında string.
    Döndürülen JSON:
    {
      "remove":      [id, ...],   // kaldırılacak (dead-link/kriter dışı/kopya — düzeltilemez)
      "regenerate":  [id, ...]    // yeniden üretilecek (İngilizce çıkmış veya çok kısa ama kaynak var)
    }
    """
    return f"""Sen siber güvenlik raporu kalite kontrolcüsüsün. Aşağıdaki haberlerin üretilmiş Türkçe içeriklerini incele ve sorunları düzelt.

Her haber için dört kontrol yap. Karar verirken "Kaynak Var" alanına dikkat et:
- "Kaynak Var: evet" → orijinal makale metni mevcut, yeniden üretim mümkün
- "Kaynak Var: hayır" → kaynak metin yok, yeniden üretim mümkün değil

KONTROL 1 — KISA/BOZUK ÖZET:
Paragraf 40 kelimeden kısa, anlamsız veya "içerik bulunamadı" gibi placeholder ise:
  • Kaynak Var: evet → "regenerate" listesine ekle (yeniden üretilecek)
  • Kaynak Var: hayır → "remove" listesine ekle (dead link, çıkarılacak)

KONTROL 2 — İNGİLİZCE İÇERİK:
TR Başlık veya Paragraf büyük ölçüde İngilizce yazılmışsa (Türkçe olması gerekirdi):
  • Kaynak Var: evet → "regenerate" listesine ekle
  • Kaynak Var: hayır → "remove" listesine ekle
Not: İngilizce şirket/ürün/CVE adları normaldir — paragrafın çoğunluğu İngilizce cümle ise sorun var.

KONTROL 3 — KRİTER DIŞI:
Paragraf okunduğunda açıkça şunlardan biri olduğu anlaşılıyorsa → "remove" listesine ekle
(kaynak olsa bile içerik değişmeyeceğinden regenerate anlamsız):
- Ürün lansmanı / pazar araştırması / beta duyurusu
- Podcast, webinar, konferans veya etkinlik tanıtımı
- Genel tavsiye / eğitim / röportaj (somut olay/saldırı/ihlal yok)

KONTROL 4 — KOPYALAR (Pass 1'den kaçan):
Farklı ID'li iki haber aynı olayı anlatıyorsa (aynı mağdur + saldırgan + tarihli olay),
daha kısa/yüzeysel olanı → "remove" listesine ekle.

Sorun tespit etmediğin haberleri listeye EKLEME — yalnızca sorunluları bildir.

SADECE JSON FORMATINDA YANIT VER — başka hiçbir şey yazma:
{{
  "remove":     [17, 23],
  "regenerate": [8]
}}

HABERLER:
{articles_content}"""


def get_legacy_json_prompt(articles_brief):
    """
    Legacy tek-çağrı fallback için: sıralama + Türkçe özet birleşik JSON prompt.
    Döndürülen JSON:
    {
      "top10": [id, ...],          // en önemli max 10 haber ID
      "remaining": [id, ...],      // diğer haberler önem sırasıyla
      "filtered": [id, ...],       // çıkarılan haberler
      "summaries": [
        {"id": N, "tr_title": "...", "paragraph": "..."},
        ...
      ]
    }
    """
    return f"""Sen profesyonel bir siber tehdit istihbarat analistisin.
Sana {len(articles_brief.split('=== HABER ID:')) - 1} haber verilecek. Tek seferde şunları yapacaksın:

ADIM 1 — FİLTRELE (filtered listesi):
Aşağıdakileri ÇIKAR:
- Podcast, webinar, konferans, etkinlik duyurusu
- Ürün lansmanı, beta sürüm, pazar araştırması raporu
- Genel tavsiye makalesi, röportaj, inceleme yazısı
- Basit patch haberleri (kritik olmayan)

ADIM 2 — SIRALA:
Kalan haberleri önem sırasına göre sırala. En önemli max 10 tanesi "top10", geri kalanlar "remaining".
Öncelik sırası:
1. NATO/ulusal güvenlik, jeopolitik siber gelişme, hükümet kararı
2. Kritik altyapı saldırısı (enerji, sağlık, finans, hükümet)
3. Devlet destekli saldırı / APT / casusluk
4. Büyük veri ihlali (5M+ kullanıcı)
5. Zero-day + aktif istismar
6. Fidye yazılımı, takedown, kovuşturma
7. Tedarik zinciri saldırısı
8. Diğer

ADIM 3 — TÜRKÇE ÖZET YAZ (filtered hariç HER haber için):
Her haber için:
- "tr_title": Türkçe isim-fiil başlığı. ZORUNLU FORMAT: "[Özne]'nin [Nesne]'yi [eylem-ması/mesi]" — örnek: "FBI'ın Kimlik Avı Ağını Çökertmesi", "Meta'nın NSO Group'u Suçlaması". YASAK: "...gerçekleştirilmiştir", "...açığa çıkmıştır" gibi eylem cümlesi yapıları.
- "paragraph": MİNİMUM 120 kelime Türkçe özet (daha az yazarsan YANLIŞ).
  - SADECE kaynak metindeki bilgiler — tahmin, yorum, çıkarım YASAK
  - Ne oldu, kim etkilendi, teknik boyutları aktar
  - MUTLAK YASAK: "göstermektedir", "ortaya koymaktadır", "vurgulamaktadır", "taşımaktadır", "darbe vurmuştur", "önem arz etmektedir" ile biten cümleler
  - Son cümle somut haber detayı veya teknik bulgu olacak

ÇIKTI FORMATI — SADECE JSON, başka hiçbir şey yazma:
{{
  "top10": [42, 7, 15, ...],
  "remaining": [3, 8, 21, ...],
  "filtered": [5, 12, ...],
  "summaries": [
    {{"id": 42, "tr_title": "Başlık...", "paragraph": "Paragraf..."}},
    ...
  ]
}}

HABERLER:
{articles_brief}"""

