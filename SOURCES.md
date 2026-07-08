# Rapor İçerik Kaynakları ve Filtreleme Kriterleri

## Haber Kaynakları (RSS)

| Kaynak | Feed |
|---|---|
| The Hacker News | feeds.feedburner.com/TheHackersNews |
| BleepingComputer | bleepingcomputer.com/feed |
| Krebs on Security | krebsonsecurity.com/feed |
| Security Affairs | securityaffairs.com/feed |
| Graham Cluley | grahamcluley.com/feed |
| SANS ISC | isc.sans.edu/rssfeed.xml |
| Recorded Future | recordedfuture.com/feed |
| Cyberscoop | cyberscoop.com/feed |
| The Register | theregister.com/security/cyber_crime/headlines.atom |
| TechCrunch Security | techcrunch.com/category/security/feed |
| CSO Online | csoonline.com/feed |
| Infoblox Blog | blogs.infoblox.com/feed |
| Dark Reading | darkreading.com/rss.xml — ⚠️ şu an her gün HTTP 404 veriyor (bkz. data/rss_errors.txt); alternatif URL doğrulanamadığı için değiştirilmedi |
| SecurityWeek | feeds.feedburner.com/securityweek |
| Help Net Security | helpnetsecurity.com/feed |
| The Record | therecord.media/feed |
| Talos Intelligence | blog.talosintelligence.com/rss |
| Unit 42 | unit42.paloaltonetworks.com/feed |
| CISA | cisa.gov/cybersecurity-advisories/all.xml |
| NCSC UK | ncsc.gov.uk/api/1/services/v1/all-rss-feed.xml |
| CERT-EU | cert.europa.eu/publications/security-advisories-rss |

### Stratejik / Jeopolitik / İstihbari Odaklı Kaynaklar

APT atıfı, ulus-devlet operasyonları, ticari casus yazılım ve gözetim/jeopolitik
soruşturmalara ağırlık veren kaynaklar — raporun stratejik çekirdeği.

| Kaynak | Feed | Odak |
|---|---|---|
| Microsoft Security | microsoft.com/en-us/security/blog/feed | APT atıfı, tedarik zinciri, nation-state |
| Bellingcat | bellingcat.com/feed | OSINT, jeopolitik soruşturma |
| Citizen Lab | citizenlab.ca/feed | Ticari casus yazılım (Pegasus vb.), gözetim |
| Mandiant (Google Cloud) | feeds.feedburner.com/threatintelligence/pvexyqv7v0v | APT attribution, nation-state |
| CrowdStrike | crowdstrike.com/blog/feed | Adversary tracking, APT grupları |
| Securelist (Kaspersky) | securelist.com/feed | APT araştırmaları (Rusya/Çin odaklı) |
| The DFIR Report | thedfirreport.com/feed | Gerçek saldırı TTP'leri, operasyonel istihbarat |
| ANSSI (CERT-FR) | cert.ssi.gouv.fr/feed | Fransız CERT, APT raporları |
| BSI | bsi.bund.de/.../RSSNewsfeed_Presse_Veranstaltungen.xml | Alman Federal Bilgi Güvenliği Dairesi |
| NIST | nist.gov/news-events/news/rss.xml | ABD Ulusal Standartlar ve Teknoloji Enstitüsü |
| SentinelOne Labs | sentinelone.com/labs/feed | APT araştırmaları, malware analizi |
| Proofpoint Threat Insight | proofpoint.com/us/rss.xml | Phishing kampanyaları, e-posta tabanlı APT |
| Schneier on Security | schneier.com/blog/atom.xml | Güvenlik politikası, kriptografi, stratejik analiz |

### Bölgesel / Orta Doğu Jeopolitik Kaynaklar

İran/İsrail/Orta Doğu siber-jeopolitik olaylarını (örn. İran iç bankacılık kesintisi —
Bank Melli/Saderat/Tejarat) yakalamak için eklendi; Batı merkezli feed'ler bu tür
bölgesel olayları çoğu zaman hiç ya da gecikmeli taşıyor.

| Kaynak | Feed | Odak |
|---|---|---|
| The Cyber Express | thecyberexpress.com/feed | Bölgesel saldırı/ihlal/kesinti haberleri |
| Industrial Cyber | industrialcyber.co/feed — ⚠️ şu an her gün XML parse hatası veriyor (bkz. data/rss_errors.txt) | Kritik altyapı / OT / finans |
| IranWire | iranwire.com/en/feed | İran iç siber olayları, bankacılık kesintileri, internet blackout |

---

## Sosyal Medya Sinyalleri

### Reddit
- **Subredditler:** r/cybersecurity (~25 post/gün), r/netsec (~1-2 post/gün, yüksek kalite)
- **Filtreleme:** min 20 upvote, son 24 saat
- **Sıralama:** upvote skoru (yüksekten düşüğe); subredditler arası top 5 seçilir
- **Erişim:** Kimlik doğrulama gerekmez; Reddit public JSON API (`/r/{sub}/top.json?t=day`) açık User-Agent ile çalışır

### Hacker News
- **Arama terimleri:** security, cybersecurity, vulnerability, malware, breach
- **Endpoint:** Algolia `search` (relevance + popularity ağırlıklı)
- **Filtreleme:** min 15 puan, son 24 saat
- **Sıralama:** `puan + (yorum sayısı × 3)` karma skoru

### GitHub Security Advisories
- **Kaynak:** GitHub incelenmiş (reviewed) advisory veritabanı
- **Filtreleme:** Severity critical, high veya medium
- **Sıralama:** Severity önceliği (critical > high > medium), eşit severity'de CVSS skoruna göre

### X.com
- **Kaynak:** Tavily arama motoru (`include_domains: x.com, twitter.com`)
- **Kapsam:** Son ~7 gün (2-3 gün tutarlı kapsama); `TAVILY_API_KEY` gerekli
- **Sıralama:** Tavily relevance skoru (0.0–1.0); min eşik 0.5
- **Kısıtlama:** X.com crawler'ları engeller; engagement verisi (beğeni/retweet) mevcut değil — sadece ilgililik skoru gösterilir. Günlük 1 kredi tüketir (ücretsiz plan: 1000 kredi/ay).

Reddit + HN + GitHub karma puana göre top 5 olarak seçilir.
X.com sonuçları ayrı havuzda tutulur ve top 5'in altına eklenir (karma sıralamayı etkilemez).
Toplam sosyal sinyal sayısı: 5 (ana) + en fazla 3 (X.com) = en fazla 8.

---

## Haber Filtreleme

**Dışlananlar:**
- Podcast, webinar, konferans duyurusu
- Ürün lansmanı, beta sürüm haberleri
- İndirilebilir rapor, etkinlik katılımı
- İnceleme yazıları, röportajlar, genel tavsiye makaleleri
- Kritik olmayan rutin patch/güncelleme haberleri

**Alınanlar:**
- Aktif tehdit, açık, saldırı, veri ihlali haberleri
- Kritik güncelleme ve yama bildirimleri

---

## Önem Sıralaması (KRİTİK 3 + skorlama)

Seçim iki aşamalıdır (bkz. `src/config.py: get_scoring_prompt`):

**1) LLM puanlaması** — her habere şunlar atanır:
- **Kategori** (tek etiket): casus_yazilim, nation_state_apt,
  stratejik_kurum_saldirisi, kolluk_operasyonu, tedarik_zinciri, veri_ihlali,
  politika_hukuk, zafiyet_aktif_apt, zafiyet_rutin, urun_icerik, siber_disi
- **Siber kapısı** (0/1): özünde somut siber boyut yoksa haber gündem dışı kalır
- **Rubrik puanı** (`SCORING_WEIGHTS`): stratejik/istihbari değer **40** +
  etki/ölçek **25** + aciliyet/güncellik **20** + kaynak güveni **15** = 100

**2) Deterministik sıralama (kod)** — LLM sıralama YAPMAZ; kod toplam puana
göre sıralar, eşitlikte `KATEGORI_ONCELIK` (casus_yazilim > nation_state_apt >
stratejik_kurum_saldirisi > ...) bozar. Raporun üstündeki **KRİTİK 3** kartı bu
sıralamanın başından seçilir; `zafiyet_rutin`, `urun_icerik` ve `siber_disi`
kategorileri KRİTİK 3'e giremez (`KRITIK3_HARIC_KATEGORILER`). Son 7 günde
KRİTİK 3'te yer almış olaylar (`data/kritik3_gecmis.json`) tekrar seçilmez.
`zafiyet_rutin`/`zafiyet_aktif_apt` kategorili haberler HTML'de "Güvenlik
Açıkları" bölümüne yönlendirilir.

---

## Tekrar Kontrolü

Son 3 günün raporlarında yer almış olaylar yeniden rapora alınmaz. Aynı CVE numarası, aynı şirket/kurum + aynı saldırı türü veya aynı tehdit aktörü + aynı hedef kombinasyonu tekrar sayılır.
