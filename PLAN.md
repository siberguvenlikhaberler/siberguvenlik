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
3. **Puanlama/seçim (LLM)** — Skorlayıcı ajanı her habere kategori + siber-kapı
   + rubrik puanı (`SCORING_WEIGHTS`: stratejik 40 / etki 25 / aciliyet 20 /
   kaynak güveni 15) verir; ardından **Critique (Denetçi) ajanı** en yüksek
   adayları bağımsız olarak denetleyip açık hataları düzeltir. SIRALAMA KOD
   tarafından deterministik yapılır (`KATEGORI_ONCELIK` eşitlik bozucu).
   KRİTİK 3 seçimi Seçici + Doğrulayıcı ajan çiftiyle, `KRITIK3_HARIC_KATEGORILER`
   filtresi ve 7 günlük tekrar geçmişi (`data/kritik3_gecmis.json`) ile yapılır.
4. **İçerik üretimi (LLM)** — derin analiz + özet + yönetici özeti + başlık
   kurtarma ajanları (aşağıdaki tabloya bkz.); sağlayıcı tek bir dispatcher
   (`_gemini_call_json` → Gemini; yedek `src/llm_client.py: generate_json` →
   OpenRouter). Kalite kontrol ajanı üretilen içeriği denetler; ardından
   **Auditor ajanı** rapor TAMAMEN oluştuktan sonra TÜM haberleri son bir kez
   tarayıp semantik ("aynı olay, farklı sözcükler") mükerrerleri temizler.
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

## LLM ajanları (roller)

Sistem otonom bir agent framework'ü (tool-calling döngüsü, planlayıcı, hafıza)
DEĞİLDİR; **sabit sıralı, çok-rollü bir LLM pipeline'ıdır**. Her rol tek atışlık
(stateless) bir prompt fonksiyonudur (`src/config.py`) ve tek bir dispatcher
üzerinden çağrılır. "Agentic" desen olarak *üret → bağımsız denetle* çifti üç
yerde kuruludur (Skorlayıcı→Critique, Kritik-3 Seçici→Doğrulayıcı, Kalite
kontrol→Auditor — sonuncusu rapor TAMAMEN oluştuktan sonra final mükerrer
denetimi yapar).

Üretimde fiilen çağrılan **10 aktif ajan rolü**:

| # | Ajan | Prompt (`src/config.py`) | Çağrı (`main.py`) |
|---|------|--------------------------|-------------------|
| 1 | Skorlayıcı | `get_scoring_prompt` | 2903 |
| 2 | Denetçi (Critique) | `get_critique_prompt` | 2950 |
| 3 | Kritik-3 seçimi | `get_top3_selection_prompt` | 2582 |
| 4 | Kritik-3 doğrulama | `get_top3_verification_prompt` | 2525 |
| 5 | Derin analiz | `get_deep_analysis_prompt` | 3219 |
| 6 | Kalite kontrol | `get_quality_review_prompt` | 3303 |
| 7 | Yönetici özeti | `get_executive_summary_prompt` | 3480 |
| 8 | Başlık kurtarma | `get_title_rescue_prompt` | 3610 |
| 9 | Özet (batch) | `get_summary_batch_prompt` | 3658 |
| 10 | Auditor (final mükerrer denetimi, Pass 5.5) | `get_dedup_review_prompt` | 2677 |

Ek olarak **1 fallback ajan** (`get_legacy_json_prompt`, `main.py:3750`) yalnızca
ana yol çökerse devreye girer.

## Bilinen açık konular

- `get_ranking_prompt` (`src/config.py:174`) import ediliyor ama hiçbir yerde
  çağrılmıyor — ölü kod; kaldırılabilir.

- `data/haberler_arsiv.txt` (~7 MB) repo içinde büyümeye devam ediyor —
  temizlik/taşıma kararı bekliyor.
- Dark Reading ve Industrial Cyber feed'leri `data/rss_errors.txt`te her gün
  hata üretiyor (404 / parse hatası); alternatif URL bu ortamdan doğrulanamadı
  (403), düzeltme doğrulama yapılabilen bir ortamdan yapılmalı.
- `requirements.txt` sürümleri `>=` ile serbest; kilitleme ayrıca test ister.
