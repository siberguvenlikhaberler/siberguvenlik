# Harici Zamanlayıcı Kurulumu (cron-job.org)

## Neden?
GitHub Actions'ın kendi `schedule` (cron) tetikleyicisi **güvenilmez**: tetiklemeleri
"best-effort" kuyruğa alır, yoğun saatlerde saatlerce geciktirir ve özellikle
**sabah 06–10 UTC slotlarını pratikte hiç ateşlemez**. Gerçek run geçmişinde hiçbir
gün ~11:00 UTC'den önce çalışmadığı görüldü → sabah raporu hiç üretilmiyordu.

Çözüm: Zamanlamayı **harici** bir servise (cron-job.org, ücretsiz) taşıyıp GitHub'ı
`repository_dispatch` API'siyle dakikası dakikasına tetiklemek. Böylece **asıl
zamanlayıcı cron-job.org**'dur; aşağıdaki slotları o gönderir.

GitHub'ın kendi `schedule` bloğu artık **tek bir yedek çalıştırmaya** indirildi
(`7 9 * * *` = 09:07 UTC = TR 12:07, cron-job.org'un ilk denemesinden hemen sonra).
Amacı yalnızca cron-job.org tamamen düşerse (servis kesintisi, token expire) günü
kurtarmaktır. Eskiden GitHub'da 8 slot (06:23–20:53 UTC) vardı; kaldırıldı çünkü
(a) tekrarları zaten cron-job.org yapıyor, (b) geç/gece slotlar GitHub kuyruğunda
gecikince TR gece yarısını aşıp bir sonraki günün raporunu geceleyin erkenden
üretiyordu. Tek yedek slot (TR 12:07) birkaç saat gecikse bile TR günü içinde kalır.

Bu yedek, cron-job.org'un TR 12:00 slotuyla aynı ana denk gelse bile sorun
yaratmaz: `daily.yml`'deki `concurrency` grubu aynı anda tek çalıştırmaya izin
verir, ikinci tetikleme kuyruğa girer ve raporun zaten üretildiğini görüp anında
çıkar (main.py Kontrol 1).

`main.py` `repository_dispatch` event'ini `schedule` ile aynı sayar → aynı gün
başarılı rapor üretildiyse sonraki slotlar otomatik atlanır (çift rapor olmaz).

---

## cron-job.org'un göndereceği slotlar (asıl zamanlama — GÜNCEL)

| # | TR saati | UTC |
|---|----------|-----|
| 1 | 12:00 | 09:00 |
| 2 | 13:00 | 10:00 |
| 3 | 14:00 | 11:00 |

(Önceki sürümde 06:23–20:53 UTC arasına yayılmış 8 slot vardı; program TR öğlen
ile 14:00 arasına toplanan 3 slota indirildi.)

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

## Adım 2 — cron-job.org'da iş oluştur

Hesap aç: https://console.cron-job.org  → **CREATE CRONJOB**

**Ortak ayarlar (REQUEST sekmesi):**

- **URL:** `https://api.github.com/repos/siberguvenlikhaberler/siberguvenlik/dispatches`
- **Request method:** `POST`
- **Headers:**
  - `Accept: application/vnd.github+json`
  - `Authorization: Bearer <PAT>`   ← Adım 1'deki token
  - `X-GitHub-Api-Version: 2022-11-28`
  - `User-Agent: cron-job.org`   ← GitHub API User-Agent ister, boş bırakma
- **Request body:** `{"event_type":"scheduled-report"}`
- **TIMEZONE:** **Europe/Istanbul** (TR saatine göre kurulacaksa) — veya UTC seçip
  saatleri yukarıdaki tabloya göre UTC girin. Hangisini kullandığınızı tutarlı tutun.

### "Siber Rapor (öğlen, 3 slot)"
SCHEDULE sekmesi (Expert / custom):
- **Minutes:** `0`
- **Hours:** `12, 13, 14` (TIMEZONE Europe/Istanbul ise) veya `9, 10, 11` (TIMEZONE UTC ise)
- **Days of month:** her gün (`*`)
- **Months:** her ay (`*`)
- **Days of week:** her gün (`*`)

→ Cron karşılığı (Istanbul): `0 12,13,14 * * *`

---

## Davranış (kurulduktan sonra)
- cron-job.org her slotta `repository_dispatch` atar → GitHub workflow **anında** başlar
  (GitHub schedule kuyruğunu beklemez).
- Günün ilk **başarılı** raporu `docs/raporlar/<bugün>.html` dosyasını üretir; aynı
  günün kalan slotları (hem harici hem GitHub'ın TR 12:07 yedeği) bu dosyayı görüp
  **atlar** — üzerine asla yazılmaz (main.py Kontrol 1).
- Rapor fallback üretirse işaret yazılmaz → sıradaki slot yeniden dener.
- Token süresi dolarsa cron-job.org "Execution history"de 401 görünür → Adım 1'i tekrarla.
