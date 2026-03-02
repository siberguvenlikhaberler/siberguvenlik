# Rapor İçerik Kaynakları ve Filtreleme Kriterleri

## Haber Kaynakları (RSS)

| Kaynak | Feed |
|---|---|
| The Hacker News | feeds.feedburner.com/TheHackersNews |
| BleepingComputer | bleepingcomputer.com/feed |
| Krebs on Security | krebsonsecurity.com/feed |
| Threatpost | threatpost.com/feed |
| Security Affairs | securityaffairs.com/feed |
| Graham Cluley | grahamcluley.com/feed |
| SANS ISC | isc.sans.edu/rssfeed.xml |
| Recorded Future | recordedfuture.com/feed |
| Cyberscoop | cyberscoop.com/feed |
| The Register | theregister.com/security/cyber_crime/headlines.atom |
| TechCrunch Security | techcrunch.com/category/security/feed |
| CSO Online | csoonline.com/feed |
| Infoblox Blog | blogs.infoblox.com/feed |

---

## Sosyal Medya Sinyalleri

### Reddit
- **Subredditler:** r/netsec, r/cybersecurity, r/hacking
- **Filtreleme:** min 100 upvote, son 24 saat
- **Sıralama:** upvote skoru (yüksekten düşüğe)
- **Erişim:** OAuth2 client credentials — `REDDIT_CLIENT_ID` ve `REDDIT_CLIENT_SECRET` GitHub secret olarak tanımlanmalı

### Hacker News
- **Arama terimleri:** security, cybersecurity, vulnerability, malware, breach
- **Endpoint:** Algolia `search` (relevance + popularity ağırlıklı)
- **Filtreleme:** min 15 puan, son 24 saat
- **Sıralama:** `puan + (yorum sayısı × 3)` karma skoru

### GitHub Security Advisories
- **Kaynak:** GitHub incelenmiş (reviewed) advisory veritabanı
- **Filtreleme:** Severity critical, high veya medium
- **Sıralama:** Severity önceliği (critical > high > medium), eşit severity'de CVSS skoruna göre

Her üç kaynaktan toplanan içerik karma skora göre sıralanır; en yüksek 5 tanesi rapora eklenir.

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

## Önem Sıralaması (Top 5 seçimi)

Günlük raporun "Önemli Gelişmeler" kutusuna giren 5 haber aşağıdaki öncelik sırasına göre belirlenir:

1. **Kritik altyapı saldırısı** — enerji, sağlık, finans, hükümet, SCADA/ICS sistemleri
2. **Zero-day + APT grubu aktivitesi** — devlet destekli tehdit aktörleri, daha önce bilinmeyen açıklar
3. **Jeopolitik kritik durumlar** — ülkeler arası siber savaş, seçim sistemleri, kritik altyapı hedefleme
4. **Ulusal güvenlik / Türkiye** — Türkiye'yi, NATO'yu veya Türk kurumlarını doğrudan etkileyen gelişmeler
5. **5 milyon+ kullanıcı veri ihlali** — büyük şirketler, kişisel/finansal veri sızıntıları
6. **Yasal düzenlemeler** — siber güvenliğe yönelik yeni yasa ve yönetmelikler

Top 5 karşılanamadığında bir alt seviyedeki haberlerden tamamlanır; toplam sayı her zaman tam 5'tir.

---

## Tekrar Kontrolü

Son 3 günün raporlarında yer almış olaylar yeniden rapora alınmaz. Aynı CVE numarası, aynı şirket/kurum + aynı saldırı türü veya aynı tehdit aktörü + aynı hedef kombinasyonu tekrar sayılır.
