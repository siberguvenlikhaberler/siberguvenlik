# Proje Durumu ve Mimari Özeti

> ⚠️ Bu dosyanın eski sürümü (20 Şubat 2026 tarihli "İyileştirme Planı v2.0"),
> terk edilmiş bir mimariyi (IMPORTANCE_WEIGHTS/DETECTION_PATTERNS anahtar
> kelime skorlaması, ayrı branch talimatı) anlatıyordu ve gerçek sistemle
> uyuşmuyordu. O içerik kaldırıldı; güncel işleyiş aşağıdadır.

## Sistem nasıl çalışır (güncel)

1. **Toplama** — `main.py`: RSS/Atom kaynakları (`src/config.py: RSS_SOURCES`)
   + sosyal sinyaller (Reddit, HN, GitHub Advisories, Mastodon, X.com/Tavily)
   çekilir; ham içerik `data/haberler_ham.txt`e yazılır (`SESSION_DATE` başlığıyla).
2. **Tekilleştirme** — `src/dedup.py` + `main.py:_filter_duplicates`:
   URL normalizasyonu → içerik hash'i → başlık benzerliği (0.72) →
   anahtar kelime Jaccard (0.45) → ortak kod adı (codename) olmak üzere
   5 seviye; son 7 günün linkleri `data/haberler_linkler.txt`te tutulur.
3. **Puanlama/seçim (LLM)** — `src/config.py: get_scoring_prompt`:
   her habere kategori + siber-kapı + rubrik puanı (`SCORING_WEIGHTS`:
   stratejik 40 / etki 25 / aciliyet 20 / kaynak güveni 15) verilir;
   SIRALAMA KOD tarafından deterministik yapılır (`KATEGORI_ONCELIK`
   eşitlik bozucu). KRİTİK 3 seçimi `KRITIK3_HARIC_KATEGORILER` filtresi ve
   7 günlük tekrar geçmişi (`data/kritik3_gecmis.json`) ile yapılır.
4. **İçerik üretimi (LLM)** — derin analiz + yönetici özeti promptları
   (`get_deep_analysis_prompt`, `get_executive_summary_prompt`);
   sağlayıcı `src/llm_client.py` (OpenRouter aktif, Gemini yedek).
5. **Rapor** — `main.py:_build_html` → `docs/index.html` +
   `docs/raporlar/YYYY-MM-DD.html` (GitHub Pages). Gün damgaları
   Europe/Istanbul gününe göredir (`_now_tr()`).
6. **İdempotency** — o günün BAŞARILI raporu varsa otomatik koşular hemen
   çıkar; başarısızlık `<!-- RAPOR_DURUM: FALLBACK -->` yapısal işaretiyle
   tespit edilir (`main.py: _rapor_basarili`).
7. **Manuel araç** — `api/manual_add.py` (Vercel) + `docs/manual-add.js`:
   şifre korumalı Ekle/Değiştir/Sil; SSRF (hop-bazlı IP doğrulama) ve
   XSS (HTML escape) korumaları içerir; değişiklikler GitHub API ile
   `main`'e atomik commit edilir.
8. **Zamanlama** — `.github/workflows/daily.yml`: gün içine yayılmış 8
   schedule + cron-job.org `repository_dispatch`; günde en fazla 1 başarılı
   rapor.

## Bilinen açık konular

- `data/haberler_arsiv.txt` (~7 MB) repo içinde büyümeye devam ediyor —
  temizlik/taşıma kararı bekliyor.
- Dark Reading ve Industrial Cyber feed'leri `data/rss_errors.txt`te her gün
  hata üretiyor (404 / parse hatası); alternatif URL bu ortamdan doğrulanamadı
  (403), düzeltme doğrulama yapılabilen bir ortamdan yapılmalı.
- `requirements.txt` sürümleri `>=` ile serbest; kilitleme ayrıca test ister.
