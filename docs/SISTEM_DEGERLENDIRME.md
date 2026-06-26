# Sistem Devir Notu & Değerlendirme Promptu

> Bu dosya, 25–26 Haziran 2026 oturumlarında yapılan işlerin özetini ve
> **yeni bir oturumda tüm sistemin baştan sona değerlendirilmesi** için
> kullanılacak araştırma promptunu içerir.
> Yeni oturuma: *"docs/SISTEM_DEGERLENDIRME.md dosyasını oku ve BÖLÜM 3'teki
> değerlendirme promptunu uygula"* diyebilirsin.

---

## BÖLÜM 1 — Bu oturumlarda yapılan işler (özet)

### A) Manuel Haber Ekle sistemi (Vercel serverless)
- Anasayfaya şifre korumalı "Manuel Haber Ekle" pop-up'ı eklendi.
- Kullanıcı: şifre + haber URL'si girer, 3 kritik haberden birini seçip değiştirir.
- Sunucu (`api/manual_add.py`, Vercel Python serverless) URL'yi çeker, **raporun
  geri kalanıyla BİREBİR aynı** prompt/format ile (`get_deep_analysis_prompt` +
  `src/llm_client`) Türkçe başlık+paragraf üretir, hem `docs/index.html` hem o
  günün arşivinde YALNIZCA seçili kritik kartı değiştirip GitHub API ile commit eder.
- Uç nokta: `https://siberguvenlik-5hqc.vercel.app/api/manual_add`
- Gerekli Vercel env: `OPENROUTER_API_KEY`, `MANUAL_ADD_PASSWORD`, `GH_TOKEN`.
- Çözülen sorunlar: Vercel `framework:null` ile serverless routing, CORS, cache-bust.

### B) Arayüz / yerleşim düzeltmeleri
- "Manuel Haber Ekle" butonu sağ üstte tema (dark/light) butonunun altına alındı
  (`.header-actions` dikey istif).
- **Buton stili bug'ı:** stil `manual-add.js` içinde modal açılınca enjekte ediliyordu;
  bu yüzden tıklamadan önce stilsiz, sonra mavi görünüyordu. `.manual-add-btn` CSS'i
  ana stylesheet'e (`index.html` + `main.py`) taşındı → artık tutarlı.

### C) Mobil optimizasyon (yalnızca ≤640px)
- Tam genişlik: `body` padding 0, container border-radius/shadow kaldırıldı.
- İç içe padding'ler kısıldı (top3 kartlarda her kenarda ~80px → ~26px).
- Başlık/buton boyutları küçültüldü, header butonları tek satıra alındı.
- Sürükle-bırak (drag) chip'i mobilde gizlendi.
- `justify` metinler mobilde sola hizalandı.
- Kurallar hem `index.html` hem `main.py` üretecine eklendi → masaüstü etkilenmez.

### D) Kritik haber (top3) içerik düzeltmeleri
- **Doha/ABD-İran "Çatışmayı Önleme Merkezi"** kartı kaldırıldı: siber boyutu yoktu,
  üstelik yanlışlıkla "NATO ZİRVESİ" rozetiyle çıkmıştı.
- Önce FortiBleed ile değiştirildi; ardından FortiBleed'in 17–24 Haziran raporlarında
  defalarca geçtiği (mükerrer) görülünce **Cellebrite haberiyle** değiştirildi
  (Rusya FSB'nin muhalif aktivistlere karşı ticari adli bilişim aracı kullanması —
  Kategori 1A, mükerrer değil).

### E) Prompt sağlamlaştırma — `src/config.py`
- `get_top3_selection_prompt`'a **"siber boyut zorunluluğu"** kuralı: siber bileşeni
  olmayan (saf diplomatik/askeri/siyasi) haberler top3'e ALINMAZ; "Seçilmez" listesine
  örnekler eklendi (Doha dekonfliction hattı vb.).
- İlk sıralama promptunda (`get_ranking_prompt`) "jeopolitik" → "jeopolitik SİBER" daraltıldı.

### F) **Günler arası mükerrer engeli — KÖK NEDEN DÜZELTMESİ** (en önemli)
- **Bug (deterministik, LLM kusuru değil):** Arşiv (`data/haberler_arsiv.txt`) her gün
  YAZILIYOR ama hiç GERİ OKUNMUYORDU. `recent_events` parametresi hep boş geçiliyor,
  prompta "(Arşiv yok)" yazılıyordu → LLM dünkü haberleri HİÇ görmüyordu, bu yüzden
  mükerrerleri yakalayamıyordu.
- **Düzeltme:** Yeni `_load_recent_events()` — arşivin yalnızca **son ~600KB**'sini
  (`f.seek`) okuyup son 3 günün başlıklarını çıkarır (dosya boyutundan bağımsız, O(1)).
  Pass 1 (sıralama) ve Pass 4 (top3) çağrılarına bağlandı. `get_top3_selection_prompt`'a
  açık "mükerrer engeli" bölümü + karar akışına "geçmişle eşleşeni en baştan ele" adımı.
- Arşiv rapor üretiminden SONRA yazıldığı için seçim anında yalnızca geçmiş günler görünür.
- **Not:** Bu düzeltme bir sonraki otomatik cron raporundan itibaren etki eder.

### İlgili commit'ler
```
46627b8 fix: günler arası mükerrer engelini fiilen çalışır hale getir
3a75844 fix: mükerrer FortiBleed kartını Cellebrite haberiyle değiştir
d64830f fix: Manuel Haber Ekle buton stilini ana CSS'e taşı
fc4c01e feat(mobil): raporu mobil ekrana göre optimize et
ded9c54 fix: Doha/ABD-İran kartını değiştir, promptu güçlendir
f4827de feat(ui): Manuel Haber Ekle butonunu tema butonunun altına taşı
```

---

## BÖLÜM 2 — Sistem mimarisi (yeni oturum için bağlam)

**Akış (günlük otomatik):** RSS toplama → makale ayrıştırma → **Pass 1** önem sıralaması
(JSON) → **Pass 2** top-10 derin analiz → **Pass 3** kalan haberler batch özet →
**Pass 4** en kritik 3 seçimi → Yönetici Özeti → HTML üretimi → `docs/index.html` +
`docs/raporlar/YYYY-MM-DD.html` → arşive ekleme → commit.

**Anahtar dosyalar:**
- `main.py` (~3800 satır): tüm boru hattı, HTML üretimi, arşiv, GitHub Pages çıktısı.
- `src/config.py` (~926 satır): tüm LLM promptları (`get_ranking_prompt`,
  `get_top3_selection_prompt`, `get_deep_analysis_prompt`, `get_summary_batch_prompt`,
  `get_executive_summary_prompt`, `get_quality_review_prompt` …).
- `src/llm_client.py`: OpenRouter (OpenAI SDK) çağrıları, model fallback.
- `src/http_utils.py`: retry'li HTTP.
- `api/manual_add.py`: Vercel serverless manuel ekleme uç noktası.
- `.github/workflows/daily.yml`: 8 cron slotu (06:23–20:53 UTC) + `repository_dispatch`
  (cron-job.org), idempotent (`data/cron_basarili.txt`).
- `data/haberler_arsiv.txt`: birikimli arşiv (~7 MB, append-only).

**Model:** OpenRouter `google/gemini-3-flash-preview` (varsayılan).

**KESİN KURALLAR (CLAUDE.md):**
- URL/dış kaynak eklemeden önce WebFetch ile DOĞRULA, uydurma.
- Tüm değişiklikler DOĞRUDAN `main` branch'e; ayrı branch açma.

---

## BÖLÜM 3 — DEĞERLENDİRME PROMPTU (yeni oturumda uygula)

> Aşağıdaki promptu yeni oturumda kullan. Amaç: kod/prompt/çıktı üçlüsünü uçtan uca
> denetleyip somut, önceliklendirilmiş bir iyileştirme raporu çıkarmak. **Bu bir
> ANALİZ görevidir — onay almadan kod değiştirme, sadece bulguları raporla.**

```
Sen bu siber güvenlik haber-özeti sisteminin baş denetçisisin. Görevin: tüm
sistemi (kod + promptlar + üretilen çıktılar + arşiv) uçtan uca değerlendirip
SOMUT, KANITA DAYALI, ÖNCELİKLENDİRİLMİŞ bir iyileştirme raporu üretmek.
Şimdilik KOD DEĞİŞTİRME — yalnızca incele ve raporla; düzeltmeleri onaydan sonra yaparız.

Bağlam için önce şunları oku: docs/SISTEM_DEGERLENDIRME.md (bu dosya),
main.py, src/config.py, src/llm_client.py, api/manual_add.py, .github/workflows/daily.yml.

Sonra şu eksenlerde değerlendir ve her bulguyu dosya:satır referansıyla belgele:

1) MÜKERRER & İÇERİK KALİTESİ
   - Son 7 günün raporlarını (docs/raporlar/*.html) ve top3 kartlarını incele.
   - Günler arası tekrar eden haber/kampanya var mı? (yeni _load_recent_events
     dedup'u gerçekten yeterli mi; kod adı taşımayan mükerrerler kaçıyor mu?)
   - Aynı gün içinde near-duplicate kartlar oluşuyor mu?
   - Top3 seçimleri prompttaki kategori kurallarıyla tutarlı mı? Siber boyutu
     zayıf veya yanlış rozetli (NATO ZİRVESİ) kartlar var mı?

2) PROMPT MİMARİSİ (src/config.py)
   - 8 prompt fonksiyonu arasında çelişki/çakışan kural var mı?
   - Kategori tanımları net mi, LLM'i yanlış yönlendiren muğlak ifadeler hangileri?
   - Türkçe başlık (mastar) ve min-kelime kuralları tutarlı uygulanıyor mu?
   - recent_events'in diller arası (TR arşiv vs EN gelen haber) eşleşme zayıflığı
     nerede risk yaratıyor; başlık yerine kod-adı/entity indeksi gerekir mi?

3) BORU HATTI SAĞLAMLIĞI (main.py)
   - Pass 1–4 hata/fallback yolları; bir pass boş dönerse rapor kalitesi ne olur?
   - Arşiv büyümesi (şu an ~7MB, sınırsız) için bölme/indeksleme gerekir mi?
   - cron idempotency ve repository_dispatch akışında yarış/çift-rapor riski var mı?
   - _parse_articles_from_txt, fetch, retry sınırları; sessiz veri kaybı noktaları.

4) MANUEL EKLEME (api/manual_add.py)
   - Güvenlik: şifre doğrulama, GH_TOKEN kapsamı, URL/SSRF, girdi doğrulama yeterli mi?
   - _CARD_RE regex'i HTML yapısı değişirse kırılır mı? Daha sağlam yöntem?
   - index ↔ arşiv tutarlılığı; kısmi başarı (index commit oldu, arşiv olmadı) durumu.

5) ÇIKTI / ARAYÜZ
   - Mobil/masaüstü görünüm, erişilebilirlik (kontrast, başlık hiyerarşisi).
   - Performans (sayfa boyutu, gömülü CSS tekrarı main.py ↔ index.html senkron mu?).

ÇIKTI FORMATI:
- Önce 5–8 maddelik "Yönetici Özeti" (en kritik bulgular).
- Sonra önceliklendirilmiş tablo: [Önem: Yüksek/Orta/Düşük] | Bulgu | Kanıt (dosya:satır)
  | Önerilen düzeltme | Tahmini efor.
- "Hızlı kazanımlar" (≤1 saatlik düzeltmeler) ayrı listelenmeli.
- Varsayım/uydurma YASAK: her iddia kod veya üretilen çıktıdan kanıtla desteklenecek;
  emin olunmayan yerler "doğrulanmalı" diye işaretlenecek.
```

---

*Hazırlanma tarihi: 26.06.2026 — devreden oturum.*
