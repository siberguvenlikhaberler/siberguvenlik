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
#   Model    : google/gemini-3.5-flash  (GA — 19 May 2026; Flash sınıfı, 1M bağlam)
#   Not      : google/gemini-3-flash-preview hâlâ "preview" olduğundan üretimde
#              kararlı GA modeli (3.5 Flash) varsayılan alındı; preview yedekte tutulur.
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
Her gruptan yalnızca en kapsamlı/güncel haberi bırak; diğerlerini "filtered" listesine ekle.
⚠️ Dikkat: farklı CVE numaraları veya farklı mağdurlar → farklı haber (filtreleme).

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
4. Jeopolitik/diplomatik siber gelişme + devlet destekli APT/casusluk operasyonu
   (ülkeler arası atıf, siber savaş; Rusya, Çin, İran, Kuzey Kore vb.)
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


def get_top3_selection_prompt(articles_brief):
    """
    Pass 4: Tüm non-CVE haberler arasından istihbari/stratejik açıdan EN KRİTİK 3'ü seç.
    articles_brief: "=== HABER ID: N ===\\nBaşlık: ...\\nÖzet: ...\n" formatında string.
    """
    return f"""Sen bir siber tehdit istihbarat analistisin. Görevin: aşağıdaki haberler arasından yalnızca STRATEJİK, JEOPOLİTİK veya İSTİHBARİ değeri olan EN KRİTİK 3 haberi seçmek.

NOT: Haber içerikleri İngilizce olabilir; dil fark etmez, anlam ve stratejik öneme göre değerlendir.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEMEL İLKE — STRATEJİK DEĞER TESTİ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Her haberi değerlendirirken şu soruyu sor:
"Bu olay; hükümetleri, uluslararası ilişkileri, ulusal güvenliği veya
 devletlerin siber kapasitesini doğrudan ya da dolaylı olarak etkiliyor mu?"
→ EVET: Kategori 1 veya 2 adayı.
→ HAYIR: Önce Kategori 3'e bak, orada da yer yoksa seçme.

⚠️ SAAT SIFIR KURALI: Stratejik haber olmayan günler de olur.
Bu durumda top 3'ü boş bırakmak yerine Kategori 3'ten en iyi 3'ü seç.
"Seçilmez" listesi her zaman geçerlidir — başka seçenek olmasa bile o listeden seçme.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KATEGORİ 0 — NATO TÜRKİYE ZİRVESİ (MUTLAK ÖNCELİK — HER ŞEYİN ÜSTÜNDE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ DAR KAPSAM: Bu kategori SADECE doğrudan NATO TÜRKİYE ZİRVESİ (Temmuz 2026) ile
ilgili haberleri içerir. Haberin NATO Türkiye Zirvesi'nden açıkça söz etmesi veya
açıkça zirveyi hedef/konu alması ŞARTTIR.
Yalnızca zirveye bağlıysa KOŞULSUZ top 3'e alınır (1. sıraya yerleştirilir):
   • Zirveyi hedef alan APT faaliyeti, siber casusluk, saldırı, keşif, hazırlık
   • Zirve güvenliğine dair uyarı, tehdit değerlendirmesi, güvenlik önlemi
   • Türk kurumlarının veya katılımcı ülkelerin doğrudan zirveye yönelik gelişmeleri
   • Zirveyi konu alan dezenformasyon / hack & leak / etki operasyonu
   • Zirve bağlamında ilgili aktörler: Rusya (APT28/APT29/Sandworm), Çin (APT10/APT40), İran, Kuzey Kore
   • Anahtar kelimeler: "NATO summit", "NATO Turkey/Türkiye summit", "NATO Antalya",
     "NATO 2026 zirvesi", "summit security"

⛔ BU KATEGORİYE GİRMEZ (genel NATO haberi ≠ zirve haberi):
   • Zirveden bahsetmeyen genel NATO siber politikası, NATO savunma/üyelik haberleri
   • NATO üyesi bir ülkeye yönelik, zirveyle bağı OLMAYAN herhangi bir saldırı
   • "NATO" kelimesi geçen ama Türkiye Zirvesi'yle ilgisi olmayan her haber
   → Bunlar Kategori 0 DEĞİLDİR; uygunsa Kategori 1/2'de normal değerlendirilir.
→ Zirveyle doğrudan ilgili haber varsa: önce onu/onları seç, kalanı Kategori 1'den tamamla.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KATEGORİ 1 — EN YÜKSEK ÖNCELİK (NATO zirvesi haberi yoksa)
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
   • Uluslararası anlaşma, diplomatik kriz, yaptırım, sınır dışı etme kararı
   • NATO, AB, BM, OSCE gibi uluslararası örgütlerin siber güvenlik kararı veya politikası

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

KURAL: Bir haber "büyük rakam" içerse de (milyonlarca kullanıcı, milyarlarca dolar zarar)
stratejik/jeopolitik/istihbari boyutu yoksa top 3'e GİREMEZ.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KARAR AKIŞI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
0. Kategori 0 (NATO Türkiye Zirvesi) adaylarını say.
   → Varsa: önce bunları 1. sıradan başlayarak seç, kalan yerleri adım 1'den tamamla.
   → Yoksa: adım 1'e geç.

1. Kategori 1'den (A→B→C→D) adayları say.
   → 3 veya daha fazla aday: ilk 3'ü seç, bitti.
   → 1-2 aday: bunları al, kalan yerleri adım 2'den tamamla.
   → 0 aday: adım 2'ye geç.

2. Kategori 2'den adayları say.
   → Kategori 1+2 toplamı 3 veya daha fazla: ilk 3'ü doldur, bitti.
   → Kategori 1+2 toplamı 1-2: bunları al, kalan yerleri adım 3'ten tamamla.
   → Kategori 1+2 toplamı 0: adım 3'e geç.

3. Kategori 3'ten en iyi adayları seçerek 3'ü tamamla.

4. Her adımda: "Seçilmez" listesindeki haber KESİNLİKLE alınmaz, başka seçenek olmasa bile.

SADECE JSON FORMATINDA YANIT VER — başka hiçbir şey yazma:
{{"top3": [42, 7, 15]}}

HABERLER:
{articles_brief}"""


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

   - 5N1K'yı stratejik çerçevede kapsa (kim, kime, ne amaçla, hangi bağlamda)
   - MUTLAK YASAK: Paragrafı "Bu olay...", "Bu saldırı...", "Bu gelişme...", "Bu operasyon...", "Bu yaklaşım..." ile başlayan herhangi bir cümleyle BITIRME
   - MUTLAK YASAK SON KELIMELER: "göstermektedir", "ortaya koymaktadır", "vurgulamaktadır", "taşımaktadır", "kanıtlamaktadır", "darbe vurmuştur", "önem arz etmektedir"
   - Son cümle somut bir bulgu veya operasyonel/stratejik tespit olacak

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
   - MUTLAK YASAK: Paragrafı "Bu olay...", "Bu saldırı...", "Bu gelişme...", "Bu operasyon...", "Bu yaklaşım..." ile başlayan herhangi bir cümleyle BİTİRME
   - MUTLAK YASAK SON KELİMELER: "göstermektedir", "ortaya koymaktadır", "vurgulamaktadır", "taşımaktadır", "kanıtlamaktadır", "darbe vurmuştur", "önem arz etmektedir"
   - Son cümle somut bir bulgu veya operasyonel/stratejik tespit olacak

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
    'SANS ISC': 'https://isc.sans.edu/rssfeed.xml',
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
    'CISA': 'https://www.cisa.gov/cybersecurity-advisories/all.xml',
    'NCSC UK': 'https://www.ncsc.gov.uk/api/1/services/v1/all-rss-feed.xml',
    'CERT-EU': 'https://cert.europa.eu/publications/security-advisories-rss',
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
}

# ===== YENİ: ÖNEM SCORING SİSTEMİ (v2.0) =====
# Bu ağırlıklar haberleri kategorize etmek için kullanılır
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

