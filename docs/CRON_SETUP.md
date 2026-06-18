# Harici Zamanlayıcı Kurulumu (cron-job.org)

## Neden?
GitHub Actions'ın kendi `schedule` (cron) tetikleyicisi **güvenilmez**: tetiklemeleri
"best-effort" kuyruğa alır, yoğun saatlerde saatlerce geciktirir ve özellikle
**sabah 06–10 UTC slotlarını pratikte hiç ateşlemez**. Gerçek run geçmişinde hiçbir
gün ~11:00 UTC'den önce çalışmadığı görüldü → sabah raporu hiç üretilmiyordu.

Çözüm: Zamanlamayı **harici** bir servise (cron-job.org, ücretsiz) taşıyıp GitHub'ı
`repository_dispatch` API'siyle dakikası dakikasına tetiklemek. GitHub'ın kendi
`schedule` bloğu **yedek olarak korunur** (idempotency sayesinde zararsız: harici
tetikleme başarılı raporu ürettiyse geç gelen GitHub cron'u atlar).

`main.py` `repository_dispatch` event'ini `schedule` ile aynı sayar → aynı gün
başarılı rapor üretildiyse sonraki slotlar otomatik atlanır (çift rapor olmaz).

---

## Tetiklenecek 8 slot (GitHub'daki ile birebir aynı saat & sıra — hepsi UTC)

| # | Saat (UTC) |
|---|-----------|
| 1 | 06:23 |
| 2 | 08:23 |
| 3 | 10:23 |
| 4 | 12:23 |
| 5 | 14:23 |
| 6 | 16:23 |
| 7 | 18:23 |
| 8 | 20:53 (son güvenlik ağı) |

---

## Adım 1 — GitHub token oluştur (sadece bir kez, sen yapacaksın)

1. https://github.com/settings/personal-access-tokens/new (Fine-grained token)
2. **Resource owner:** `siberguvenlikhaberler`
3. **Repository access:** Only select repositories → `siberguvenlik`
4. **Repository permissions:** `Contents` → **Read and write**
   (`repository_dispatch` API'si Contents:write ister. Metadata:Read otomatik gelir.)
5. **Expiration:** mümkün olan en uzun (ör. 1 yıl) — süresi dolunca yenilemen gerekir.
6. Token'ı **kopyala** (`github_pat_...`). Bir daha gösterilmez.

> Test (token çalışıyor mu?) — terminalde `<PAT>` yerine token'ı koy:
> ```bash
> curl -i -X POST \
>   -H "Accept: application/vnd.github+json" \
>   -H "Authorization: Bearer <PAT>" \
>   -H "X-GitHub-Api-Version: 2022-11-28" \
>   https://api.github.com/repos/siberguvenlikhaberler/siberguvenlik/dispatches \
>   -d '{"event_type":"scheduled-report"}'
> ```
> Beklenen yanıt: **HTTP 204 No Content**. Actions sekmesinde "Günlük Rapor"
> run'ı `repository_dispatch` event'iyle başlamalı.

---

## Adım 2 — cron-job.org'da 2 iş oluştur

Hesap aç: https://console.cron-job.org  → **CREATE CRONJOB**

Her iki iş için **ortak ayarlar (REQUEST sekmesi):**

- **URL:** `https://api.github.com/repos/siberguvenlikhaberler/siberguvenlik/dispatches`
- **Request method:** `POST`
- **Headers:**
  - `Accept: application/vnd.github+json`
  - `Authorization: Bearer <PAT>`   ← Adım 1'deki token
  - `X-GitHub-Api-Version: 2022-11-28`
  - `User-Agent: cron-job.org`   ← GitHub API User-Agent ister, boş bırakma
- **Request body:** `{"event_type":"scheduled-report"}`
- **TIMEZONE:** **UTC** (çok önemli — saatler UTC'ye göre)

### İş A — "Siber Rapor (gündüz, 7 slot)"
SCHEDULE sekmesi (Expert / custom):
- **Minutes:** `23`
- **Hours:** `6, 8, 10, 12, 14, 16, 18`
- **Days of month:** her gün (`*`)
- **Months:** her ay (`*`)
- **Days of week:** her gün (`*`)

→ Cron karşılığı: `23 6,8,10,12,14,16,18 * * *`

### İş B — "Siber Rapor (gece güvenlik ağı)"
SCHEDULE sekmesi:
- **Minutes:** `53`
- **Hours:** `20`
- Geri kalan: her gün/her ay

→ Cron karşılığı: `53 20 * * *`

Bu iki iş, GitHub'daki 8 slotun tamamını birebir karşılar.

---

## Davranış (kurulduktan sonra)
- cron-job.org her slotta `repository_dispatch` atar → GitHub workflow **anında** başlar
  (GitHub schedule kuyruğunu beklemez).
- Günün ilk **başarılı** raporu `data/cron_basarili.txt` işaretini yazar; aynı günün
  kalan slotları (hem harici hem GitHub'ın yedek schedule'ı) işareti görüp **atlar**.
- Rapor fallback üretirse işaret yazılmaz → sıradaki slot yeniden dener.
- Token süresi dolarsa cron-job.org "Execution history"de 401 görünür → Adım 1'i tekrarla.
