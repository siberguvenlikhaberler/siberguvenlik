# KRİTİK 3 SEÇİM SİSTEMİ — DENETİM VE KALICI ÇÖZÜM PLANI
Hazırlandı: 2026-10-07 · Durum: PLAN (kod değişikliği yapılmadı)

## 1. Bugünkü mimari: KRİTİK 3'e YEDİ KAPI

Manşet listesini değiştirebilen katmanlar, boru hattı sırasıyla:

| # | katman | işlevi |
|---|--------|--------|
| 1 | `_derive_top3_by_score` | deterministik ilk havuz + `_manset_yasak` kurulumu |
| 2 | `_manset_llm_sec` | LLM ilk seçimi (3 manşet) |
| 3 | `_dedup_kritik3_ici` | aynı gün iki manşet aynı olaysa takas |
| 4 | `_dedup_kritik3_cross_day_llm` | çapraz-gün tekrarı → takas |
| 5 | `_audit_kritik3_selection` | "bu haber manşetlik mi?" → takas |
| 6 | `_yayin_yonetmeni` | bütün rapora bakan editoryal takas |
| 7 | `_son_mukerrer_kapisi` | son mükerrer temizliği → takas |
| 8 | `_manset_puan_tersinelik` | gövdede daha yüksek puan varsa takas |
| 9 | `_kritik3_cesitlilik` | aynı hattın iki manşeti → takas |
| 10 | `_kritik3_dominans_takasi` | iki eksende üstün aday → takas |

Ortak yedek seçici `_kritik3_yedek_bul` vardır ama **zorunlu değildir**: 10
numara kendi havuzunu kurar, 6 numara kendi listesini yönetir.

## 2. UYGUNLUK KAPILARI ve hangi katmanda uygulandığı (koddan ölçüldü)

G1 kategori (`KRITIK3_HARIC_KATEGORILER` + zafiyet) · G2 `_manset_yasak` ·
G3 defter tekrarı (`manset_gunu_sayisi >= MANSET_TEKRAR_SINIRI`,
`_manset_disi_ids` içinde) · G4 çapraz-gün (`mukerrer_karari != FARKLI`) ·
G5 aynı gün aynı olay · G6 puan bandı · G8 çeşitlilik (aynı hat)

```
katman                               G1    G2    G3    G4    G5    G6    G8
_derive_top3_by_score                 ✓     ✓     ✓     ✓     ✓     ·     ·
_manset_llm_sec                       ·     ·     ·     ✓     ·     ✓     ·
_dedup_kritik3_ici                    ·     ·     ·     ✓     ✓     ·     ·
_dedup_kritik3_cross_day_llm          ·     ✓     ·     ✓     ·     ·     ·
_audit_kritik3_selection              ·     ✓     ·     ✓     ·     ·     ·
_yayin_yonetmeni                      ✓     ·     ✓*    ·     ✓     ✓     ·
_son_mukerrer_kapisi                  ·     ·     ✓     ✓     ✓     ✓     ·
_manset_puan_tersinelik               ·     ·     ✓     ✓     ·     ✓     ·
_kritik3_cesitlilik                   ·     ·     ✓     ✓     ·     ✓     ✓
_kritik3_dominans_takasi              ✓     ✓     ·     ·     ✓     ✓     ·
_kritik3_yedek_bul (ortak seçici)     ✓     ✓     ·     ✓     ✓     ✓     ·
```
`*` = havuz üzerinden, aday başına değil (bkz. 4. bölüm).

**G3 ORTAK SEÇİCİDE YOK; ÇAĞIRANIN GÖREVİ.** `_kritik3_yedek_bul` çağrılarında
`haric=` ne geçiyor:
- `_dedup_kritik3_ici` → `set(top3_ids)` — **manset_disi YOK**
- `_audit_kritik3_selection` → `set(hatali)` — **manset_disi YOK**
- `_dedup_kritik3_cross_day_llm` → `flagged` — **manset_disi YOK**
- `_kritik3_cesitlilik` / `_manset_puan_tersinelik` / `_son_mukerrer_kapisi` →
  `set(manset_disi) | …` ✓

Yani yedi kapıdan **dördü** defter tekrar kapısını uygulamıyor, biri (10) hiç
uygulamıyor, biri (6) aday başına değil havuz üzerinden uyguluyor.

## 3. ÖLÇÜM: kapılar ne sıklıkla kaçırıyor?

Son 31 gün, 93 yayımlanmış manşet (`scripts/defter_olc.py --yasak`):
**8 manşet (%8,6) defterin "bu olay zaten manşet oldu" dediği haberdi** —
yani ortalama dört günde bir tekrar manşet yayımlanıyor.

Hangi kapıdan girdikleri (yayımlanan rapor izlerinden):

| kapı | vaka | eksik kapı |
|------|------|-----------|
| `kritik3_dominans` | 3 (09-19, 10-01, **10-07 Linux**) | G3 + G4 hiç yok |
| `manset_capraz_gun_llm` | 2 (09-28, 09-29) | yedek_bul'a manset_disi geçmiyor |
| `manset_llm_secim` (ilk seçim) | 2 (09-22, 10-05) | LLM seçimi G3'e sınanmıyor |
| `yayin_yonetmeni_takas` | 1 (09-12) | G3 havuz üzerinden, aday havuzda değildi |

**Alternatif var mıydı?** 8 günün 7'sinde gövdede defter-temiz (tekrar=0)
aday vardı (11-22 aday); yalnızca 5 Ekim'de (3 haberlik kıtlık günü) yoktu —
orada mevcut "temiz aday yoksa manşet yerinde kalır" kuralı DOĞRU davranış.
Yani sıkı kapı 8 vakanın 7'sini düzeltir ve KRİTİK 3'ü hiçbir gün 2'ye
düşürmez.

## 4. KÖK SEBEP: tek bir UYGUNLUK YÜKLEMİ yok

Dört ayrı arıza (2026-08-21 Siemens PLC, 08-25 yaşlı dolandırıcılığı,
10-04 OpenAI/Avustralya, 10-07 Linux) tek bir yapısal nedenin örnekleridir:

1. **Uygunluk, KATMAN BAŞINA elle kodlanıyor.** Her katman "bu aday manşete
   girebilir mi?" sorusunu kendi süzgeciyle yanıtlıyor; yedi süzgeçten her
   biri FARKLI bir kapıyı atlıyor. Kopyalanan idiom, eksik kapıyı da
   kopyalıyor.
2. **Kapı AY AY DEĞİL HAVUZ üzerinde çalışıyor.** `_manset_disi_ids(havuz, …)`
   bir listeyi süzer; havuzu kuran yer bir id'yi listeye koymazsa kapı o id'yi
   hiç görmez (09-12 vakası). Yüklem ADAY BAŞINA olmalı.
3. **Çıkış tarafı merkezîleştirildi, giriş tarafı değil.** 5 Ekim'de kurulan
   manşet aracısı (`_manset_yasagi_koy` / `_manset_takas` /
   `_manset_takasi_uygula`) KARARIN ve LİSTENİN tek yazarı oldu; ama "kim
   girebilir" sorusu hâlâ yedi yerde ayrı yanıtlanıyor.
4. **Üç tanım ayrışabiliyor.** 10-07 çiftinde `same_event` True,
   `iliski_belirle` AYNI_GELISME, `mukerrer_karari` ise FARKLI dedi (konu
   0,333 vs 0,35 eşiği — 0,017 fark). Her katman farklı tanımı çağırdığı için
   sonuç katmana göre değişiyor.

## 5. KALICI ÇÖZÜM — TEK UYGUNLUK YÜKLEMİ (giriş aracısı)

### P0 · `_manset_uygun_mu(aid, mevcut_manset, …) -> (uygun, gerekçe)`
ADAY BAŞINA çalışan tek yüklem; kapıları SABİT SIRADA uygular ve gerekçe
döndürür (iz için). Kapılar: G1 kategori/zafiyet → G2 `_manset_yasak` →
G3 defter tekrarı → G4 çapraz-gün → G5 aynı gün aynı olay → G8 çeşitlilik →
G6 puan bandı (opsiyonel, `bant=` ile). `yonetmen=` gibi çağırana göre
değişen davranış KALDIRILIR: tek tablo, tek sıra.

### P1 · `_kritik3_yedek_bul` yüklemin İNCE SARMALAYICISI olur
Havuzu puan sırasında tarar, `_manset_uygun_mu` doğru diyen ilk adayı döndürür.
**G3 artık yüklemin İÇİNDE** — çağıran `manset_disi` geçmeyi unutamaz.
`haric=` yalnızca çağırana özgü dışlamalar için kalır (ör. o turda düşenler).

### P2 · Kendi havuzunu kuran iki katman yükleme bağlanır
- `_kritik3_dominans_takasi`: elle kurulan havuz süzgeci (kategori + ham
  `mukerrer` + yasak + aynı gün aynı olay) KALDIRILIR, yerine yüklem.
  Dominans ölçütü (iki eksende üstünlük) katmanda kalır — o SIRALAMA kuralı,
  uygunluk kuralı değil.
- `_yayin_yonetmeni`: `_yy_disi` havuz süzgeci yerine aday başına yüklem.

### P3 · İlk seçim de sınanır
`_manset_llm_sec` dönüşü ve `_derive_top3_by_score` ilk üçlüsü, kabul
edilmeden önce yüklemden geçirilir; uygun olmayan seçim aynı yedek bulucuyla
değiştirilir. Bu, ölçülen 8 vakanın 2'sini kapatır. Değiştirme yine
**TAKAS, ELEME DEĞİL**: temiz aday yoksa manşet yerinde kalır.

### P4 · Yapı testleri (giriş tarafının bekçisi)
- `test_kapilar_tek_yuklemden_gecer`: KRİTİK 3'e id SOKABİLEN her fonksiyon
  ya `_manset_uygun_mu` ya `_kritik3_yedek_bul` çağırmalı; kaynak taraması
  aksini bulursa test kırılır (5 Ekim'deki
  `test_katmanlar_takasi_elle_yapmaz`ın giriş ikizi).
- `test_uygunluk_kapilari_sabit`: yüklemin uyguladığı kapı listesi ve SIRASI
  sabitlenir; yeni kapı eklenince test güncellenmek zorunda kalır.
- Vaka testleri: 10-07 Linux (3 Ekim manşetinin tekrarı), 10-04
  OpenAI/Avustralya, 08-21 Siemens PLC.

### P5 · Ölçüm aracı ve KABUL ÖLÇÜTÜ
Yeni `scripts/kritik3_olc.py` (yalnızca OKUR): son 31 günü yeniden oynatır ve
her yayımlanmış manşet için yüklemi çalıştırır.
Kabul ölçütleri (öncesi → hedef):
1. Defter-tekrarlı yayımlanmış manşet **8 → 0** (5 Ekim hariç; o gün temiz
   aday yok, kural gereği yerinde kalır → **8 → 1**).
2. KRİTİK 3 hiçbir günde 3'ün altına DÜŞMEZ (31/31 gün).
3. `dedup_golden` 15/21 · 18/23 · 20/23 — DEĞİŞMEZ.
4. `zincir_olc` süzgeçli 0 düşürme, çeşitlilik 1 vaka — DEĞİŞMEZ.
5. `defter_olc --kume` en büyük küme ≤ 5 gün — DEĞİŞMEZ.
6. Tüm test takımı geçer; LLM çağrı sayısı AYNI (yüklem deterministiktir,
   maliyet nötr).

### P6 · Üç tanımın ayrışmasını kapatmak (ayrı, ölçüm gerektiren adım)
`mukerrer_karari` ile `iliski_belirle` 10-07 çiftinde zıt karar verdi.
Hedef: manşet yolunda TEK tanım. Önerilen yön — manşet uygunluğunda
`iliski_belirle` (defter tanımı) ESAS alınır, gövde politikası
`mukerrer_karari`'de kalır; çünkü manşette yanlış-pozitifin maliyeti bir
manşet yuvası, yanlış-negatifin maliyeti TEKRAR MANŞETTİR (2026-08-21'de
ölçülmüş asimetri). Bu adım P0-P5'ten SONRA ve kendi ölçümüyle yapılır.

## 6. DEĞİŞMEYECEKLER
- **KRİTİK 3 ASLA 2'YE DÜŞMEZ.** Yüklem ELEME yetkisi almaz; yalnızca
  TAKAS'ın adayını belirler. Temiz aday yoksa manşet yerinde kalır.
- Zafiyet haberi manşete giremez; politika haberi girebilir (eşik 80).
- Puan bandı, kategori önceliği ve çeşitlilik ölçütleri olduğu gibi kalır.
- LLM promptları ve çağrı sayısı değişmez; yüklem saf Python'dur.
- Pazar/pazartesi kıtlığı yapısaldır; yüklem o günlerde bandı zorlamaz.

## 7. SIRA VE RİSK
P0 → P1 → P4 (test) → P2 → P3 → P5 (ölçüm) → (ayrı) P6.
En riskli adım P3: ilk seçimin sınanması, kıtlık günlerinde havuzu
boşaltabilir — P5'in 2. kabul ölçütü tam bunu denetler. P2'deki dominans
değişikliği en yüksek getirili (8 vakanın 3'ü).


---

## 8. UYGULAMA GÜNLÜĞÜ (önce/sonra ölçümleriyle)

### P0 ✅ (2026-10-07, commit 3d57565) — tek uygunluk yüklemi
`_manset_uygun_mu` (aday başına, kapılar sabit sırada, gerekçeli) +
`_manset_hatti` (çeşitlilik ölçütü tek tanım). KABLOLAMA YAPILMADI.
Ölçüm: giriş matrisi 10 katmandan 4'ü ne yüklemden ne ortak yedek bulucudan
geçiyor; `dedup_golden` 15/21 · 18/23 · 20/23, `zincir_olc` süzgeçli 6
düşürme + çeşitlilik 1 vaka (öncesi/sonrası birebir — 6 değeri 31 günlük
pencerenin 7 Ekim'i içermesiyle 0'dan yükseldi, KOD DEĞİL VERİ kayması;
P0 öncesi kodla aynı veride de 6). 745 test.

### P1 ✅ (2026-10-07) — yedek bulucu yüklemin sarmalayıcısı
`_kritik3_yedek_bul` artık havuzu puan sırasında tarayıp `_manset_uygun_mu`
doğru diyen ilk adayı döndürüyor; kopya kural kalmadı. **G3 (defter tekrarı)
artık yüklemin İÇİNDE** — `manset_disi` geçmeyi unutan üç çağrı
(`_dedup_kritik3_ici`, `_audit_kritik3_selection`,
`_dedup_kritik3_cross_day_llm`) kapıyı otomatik uyguluyor. Yapı testleri
kapıları yüklemde arar hale getirildi.
Ölçüm: tüm kapılar birebir aynı (dedup_golden, zincir_olc, defter_olc);
745 test.

### ÖLÇÜM BÜTÜNLÜĞÜ DÜZELTMESİ — TABAN ÇİZGİSİ 8 DEĞİL 5
`scripts/kritik3_olc.py --yuklem` ilk koşuda tekrar manşetlerin 8'inden
yalnızca 5'ini reddetti. Sebep ölçüm aracındaydı: **aynı haberi İKİ AYRI
TEMSİLLE soruyordum.** `kritik3_gecmis` görünümleri daha uzun saklanıyor
(paragraf 600 / full_text 1500 karakter), `rapor_gecmis` kırpık (500 / 400).
Uzun görünümle sorulduğunda defter Florida Motorlu Araçlar ihlalini
"Çin Bağlantılı Grubun Sogou Yazılımına Arka Kapı Yerleştirmesi" manşetiyle
aynı olay sayıyor — fazladan 1.100 karakterlik sayfa şablonu metni yüzünden;
kırpık görünümle eşleşme yok.

DÜZELTİLDİ: `--tekrar` artık yalnızca RAPOR GEÇMİŞİ görünümüyle sorar.
**Taban çizgisi: 93 yayımlanmış manşetin 4'ü (%4,3) defter tekrarı** (09-19,
10-01, 10-05, 10-07) + 1'i aynı-hat ihlali (09-29) = toplam **5 uygunsuz
manşet**; 5'in 4'ünde temiz yedek var, yalnızca 10-05 kıtlık gününde yok
(kural gereği yerinde kalır). Kabul ölçütü buna göre güncellendi: **5 → 1**.

### YENİ BULGU (P6'ya eklendi) — DEFTER ASİMETRİK BESLENİYOR
Defter, manşetleri 1.500 karakterlik `full_text` ile, gövde haberlerini 400
karakterle görüyor; yani AYNI haber "manşet görünümü" ile sorulduğunda daha
çok sahte eşleşme üretiyor. Bu, uzun metnin sayfa şablonu gürültüsünü içeri
taşımasının defterdeki karşılığıdır (bkz. CLAUDE.md "sayfa şablonundaki kod
adı"). P6 kapsamına alınır: defter TEK ve KIRPIK temsille beslenmeli, ya da
`_load_recent_events` iki dosyayı aynı uzunlukta saklamalı.

### P2 — DOMİNANS VE YAYIN YÖNETMENİ YÜKLEME BAĞLANDI (2026-10-07)

İki katman kapılarını kendi eliyle sıralıyordu. `_kritik3_dominans_takasi`
kategori + ham `mukerrer` + `_manset_yasak` + aynı-gün-aynı-olay okuyordu,
DEFTER TEKRARI ve ÇAPRAZ-GÜN hiç yoktu (`_manset_disi_ids` buradan hiç
çağrılmıyordu). `_yayin_yonetmeni` kategori + puan bandı + aynı-olay
okuyordu, ÇAPRAZ-GÜN ve ÇEŞİTLİLİK yoktu.

Her ikisi artık `_manset_uygun_mu`yu ADAY BAŞINA çağırıyor. Dominans ölçütü
(öncelik + puan) katmanda kalır — o bir SIRALAMA kuralıdır; yönetmenin çift
düşüş reddi ve iki yönlü liste mekaniği de katmanda kalır. Puan bandı
tavanı yönetmende katmanda hesaplanır (raporun tamamını görür).

HAM `mukerrer` BAYRAĞI DOMİNANSTA BIRAKILDI: 2026-08-26 Interpol ölçümü —
bayrak kümeye konur, kümenin hayatta kalan temsilcisi de taşır; yedek
bulucu bu yüzden bayrağı bırakmıştı, dominans okumaya devam ediyordu, yani
aynı aday iki kapıda farklı yanıt alıyordu. Gerçek mükerrer `yasak` (G2) ve
`capraz_gun` (G4) kapılarıyla, daha dar tanımlarla elenir.

ÖLÇÜLDÜ (önce → sonra):
- matris: yüklemden geçmeyen katman 4 → **2** (`_derive_top3_by_score`,
  `_manset_llm_sec` — P3'ün konusu)
- yüklem tekrarı (replay): uygunsuz 8 kaydın 5'ini yüklem REDDEDİYOR;
  dominans kapısından giren ÜÇÜNÜN (19 Eylül Telegram, 1 Ekim Bitget,
  7 Ekim Linux arka kapıları) hepsi artık RED
- kapılar birebir aynı: `dedup_golden` 15/21 · 18/23 · 20/23,
  `zincir_olc` süzgeçli 6 düşürme + çeşitlilik 1 vaka (P2 `src/`e
  dokunmadı), 747 test geçiyor
- LLM çağrısı sayısı DEĞİŞMEDİ — yüklem deterministiktir

Regresyon: `tests/test_kritik3_dominans.py` (`test_yasakli_aday_kullanilmaz`,
`test_ham_mukerrer_bayragi_tek_basina_elemez`,
`test_capraz_gun_manseti_tekrar_manset_olmaz` — 7 Ekim vakası).

ÖLÇÜM ARACI DÜZELTMESİ: `--matris` ham metin tarıyordu ve katmanın YORUMUNU
kendi süzgeci sanıyordu (yönetmendeki "takas kapısı
KRITIK3_HARIC_KATEGORILER'e bakar" notu). Yorum satırları artık sayılmıyor.
