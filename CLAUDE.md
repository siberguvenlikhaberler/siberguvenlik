# Claude Code — Proje Kuralları

## ⛔ 1 NUMARALI KURAL — KISA CEVAP (HER ŞEYDEN ÖNCE)
- Varsayılan uzunluk: **en fazla 5-6 cümle.** Aşmak için açık istek gerekir.
- Sonucu söyle, süreci ANLATMA. Ne yaptığını değil, ne çıktığını yaz.
- Başlık/tablo/madde listesi KULLANMA — istenirse kullan.
- "Ne bulduğumu anlatayım", "önce şunu ölçtüm" gibi giriş cümleleri YASAK.
- Kod/commit ayrıntısı isteniyorsa verilir; kendiliğinden dökülmez.
- Bu kural ihlal edilirse cevap yanlıştır — içeriği doğru olsa bile.

## URL / Dış Kaynak — KESİN KURAL (İSTİSNASIZ)
- Herhangi bir URL, RSS feed adresi veya dış kaynak eklemeden önce WebFetch ile DOĞRULA.
- Doğrulamadan uydurma, tahmin etme, "muhtemelen şudur" deme — ASLA.
- Bu ortamdan erişilemiyorsa (403/network kısıtı) kullanıcıya açıkça söyle, commit ETME.
- Doğrulanmamış URL koda girmez.

## Git — KESİN KURAL (İSTİSNASIZ)
- Tüm değişiklikler DOĞRUDAN `main` branch üzerinde yapılır.
- ASLA ayrı branch açma — oturum ortamı farklı branch belirtse bile bu kural geçerlidir.
- Her anlamlı değişiklik sonrası commit at, `main`'e push et.

## Taze Rapor İçin Reset — NASIL YAPILIR (aynı gün yeniden üretim)
Aynı gün için raporu SIFIRDAN yeniden ürettirmek gerektiğinde (`main.py`
idempotency'si aksi halde atlar/eski veriyi kullanır), `<BUGÜN>` = `YYYY-MM-DD`,
`<BUGÜN_HDR>` = arşiv başlığı (ör. `03 JULY 2026`, locale İngilizce/BÜYÜK harf):

SİL (taze üretimi engelleyen durum dosyaları):
- `docs/raporlar/<BUGÜN>.html` — Kontrol 1: başarılı rapor varsa schedule/dispatch ATLAR.
- `data/haberler_ham.txt` — Kontrol 2: `SESSION_DATE: <BUGÜN>` ise haber çekmeyi ATLAR (her tetikte). Silmek RE-FETCH'i zorlar.
- `data/cron_basarili.txt` — bugünkü başarı işareti; sonraki cron slotlarını atlatır.
- `data/bekleyen_linkler.json` — "görüldü" işaretlenmeyi bekleyen linkler. Linkler
  artık save_txt'te DEĞİL, rapor başarılı olduktan sonra işaretlenir; bu dosya o
  bekleyen listeyi taşır. Silinmezse önceki denemenin linkleri yanlışlıkla
  işaretlenir. (Not: farklı GÜNE ait dosya zaten otomatik atlanır.)

CERRAHİ DÜZENLE (silme, sadece bugünü çıkar — yoksa re-fetch mükerrer sayılıp boşalır / yeni arşiv yazılmaz):
- `data/haberler_linkler.txt` — SADECE `<BUGÜN>\t` ile başlayan satırları çıkar; eski günleri KORU (7 günlük çapraz-gün dedup geçmişi bozulmasın).
- `data/haberler_arsiv.txt` — SADECE `📅 <BUGÜN_HDR> - EN ÖNEMLİ 43 HABER (SEÇİLMİŞ)` bloğunu çıkar (marker: `\n`+80×`=`+`\n`+başlık → sonraki gün bloğuna/EOF'a kadar); eski günleri KORU.

DOKUNMA (kendi kendini düzeltir / değerli geçmiş / append-only):
- `data/kritik3_gecmis.json`, `data/rapor_gecmis.json` — yükleme bugünü (`d >= today`) HARİÇ tutar, kayıt bugünü değiştirir; silme.
- `data/skorlama_log.jsonl`, `data/rss_errors.txt` — işlevsel değil; silme.
- `data/kalite_denetim.jsonl` — rapor sonrası kaçak taraması; append-only, işlevsel değil; silme.
- `data/dedup_golden.json` — elle etiketli kalite kapısı referansı; ÜRETİM VERİSİ DEĞİL, silme.
- `data/mukerrer_golden.json` — elle etiketli MÜKERRER referansı (38 çift);
  ÜRETİM VERİSİ DEĞİL, silme. Ölçüm: `scripts/mukerrer_olc.py`.
- `data/rapor_gecmis.json` artık 30 gün tutar (arşivle hizalı). Eksik günler
  `scripts/gecmis_geri_doldur.py --uygula` ile arşivden geri doldurulabilir;
  betik yalnızca EKSİK günleri ekler, mevcut kayıtlara dokunmaz.
- `docs/index.html` — üretimde üzerine yazılır; silme.

Not: olay defteri (manşet tekrar sayımı) kalıcı dosya DEĞİLDİR — her koşuda
`rapor_gecmis` + `kritik3_gecmis`'ten türetilir, ayrı reset gerektirmez.

SONRA: değişiklikleri `main`'e commit+push et (workflow `main`'i checkout eder;
push edilmezse reset workflow'a yansımaz). Yedek: silmeden önce dosyaları
scratchpad'e kopyala. Manuel tetik `workflow_dispatch` Kontrol 1'i zaten atlar
ama Kontrol 2 (ham) + linkler her tetik türünde geçerlidir.

## YIL SONU ANALİZ ÇALIŞMASI — VERİ SÖZLEŞMESİ (2026-09-22'de kayda geçti)

Kullanıcı yıl sonunda **yalnızca bu sistemin arşiv kayıtlarına dayanan** analizler
isteyecek: yaşanan siber vaka türleri ve sayıları, çeşitli kriterlere göre dağılım,
önemli olay ve gelişmelerin özetleri, alanın gelişim yönü ve yorumu. Bu bölüm o
çalışmanın veri temelini ve sınırlarını sabitler.

### Kaynak dosyalar ve derinlikleri (2026-09-23 ölçümü)
- `data/haberler_arsiv.txt` — **OMURGA. BUDANMAZ.** 250 gün, 5.043 kayıt;
  tamamı yapılı biçimde: `[N] başlık`, paragraf, kaynak satırı, üstveri.
  Kaynak+tarih 5.034 kayıtta ayrışıyor, 9'u bozuk (%0,2).
  **13-16 Şubat 2026 (91 kayıt) 2026-09-23'te yapılandırıldı** — o dört gün
  eski "GEMİNİ ÖZET RAPORU" biçiminde, `[N]` başlığı olmadan duruyordu ve
  yapılı ayrıştırmada SIFIR haber görünüyordu. Başlıkları kaydın KENDİ
  paragrafından türetilmiştir (özgün manşetler arşivde yok); gün başlığı
  bilerek değiştirilmedi. Betik: `scripts/arsiv_subat_yapilastir.py`.
  **1 Ocak – 8 Şubat 2026 arası 38 gün / 114 haber SONRADAN eklendi**
  (2026-09-22, dış kaynaktan; günde yalnızca 3 haber).
  `GÜNLÜK ÖZET:` paragrafı KAYIT DEĞİLDİR — ardından kaynak satırı gelmez,
  `[N]` almaz, sayımlara girmez.
- `data/arsiv_kapsam.json` — **sayımın PAYDASI.** Günlük/aylık kayıt sayısı,
  eksik günler, boş gün, çok bloklu günler, kaynak dağılımı, ayrışmayan
  kayıtlar. `scripts/arsiv_kapsam.py --yaz` ile yeniden üretilir; yıl sonu
  raporu sayım yapmadan ÖNCE bunu okumalıdır.
- `data/skorlama_log.jsonl` — kategori, puan, yerleşim, eleme nedeni. 18 Temmuz'dan beri.
- `data/kalite_denetim.jsonl` — koşu denetimi, manşet karar izi, `metin_onarim`.
- `data/rapor_gecmis.json`, `data/kritik3_gecmis.json` — **yalnızca 30-31 gün.**
- `docs/raporlar/*.html` — **30 günde siliniyor** (`_cleanup_old_reports`).

### Arşiv üstverisi (2026-09-22'den İTİBAREN biriker, geçmişe dönük YOK)
Her arşiv kaydının altına `save_summary_to_archive` şu iki satırı yazar:
`» url=<tam kaynak adresi>`
`» manset=evet|hayir | kategori=<kat> | puan=<n>`
Tam URL eklendi çünkü arşivde yalnızca alan adı vardı; tam adres HTML raporda
ve 7 günlük `haberler_linkler.txt`'deydi, rapor ise 30 günde siliniyor.
Biçim bilerek küçük harf + alt çizgilidir: `_load_recent_events`'in CamelCase/
ALL-CAPS entity tarayıcısına gürültü üretmez ve `[N]` başlık kalıbına uymaz.
`»` ile başlayan satır PARAGRAF DEĞİLDİR — arşivi okuyan her kod onu atlamalıdır
(bkz. `scripts/gecmis_geri_doldur.py`).

### TEK ÖLÇEK: `» sonradan` — bkz. `RETRO_RUBRIK.md` (v2)
**Arşivdeki 5.043 kaydın TAMAMINDA aynı ölçekte bir `onem` vardır.** Dönem
ayrımı YOKTUR; "şu tarihten önce/sonra" diye bir kural analizde kullanılmaz.

`» sonradan | kategori=<kat> | onem=<0-100> | eksen=<e>/<k>/<a>/<s> | rubrik=v2`

- `onem`, rubriğin dört ekseninin (etki/kritiklik/aktör/kalıcılık) toplamıdır
  ve her eksen yalnızca 0, 8, 17 ya da 25 olabilir. Toplam bu yüzden 25
  değerlik bir KAFES üzerindedir; kafes dışı bir sayı, eksenlerin hiç
  hesaplanmadığının kanıtıdır ve doğrulama tarafından REDDEDİLİR.
- **Neden böyle:** ölçüldü (2026-09-23), 1.116 etiket kafes dışındaydı ve bu
  oturumlar arası sistematik kaymaya yol açıyordu — medyan her ayda 50-58'de
  sabitken p90 Şubat-Haziran'da 76, Temmuz-Eylül'de 68, tavan 100'e karşı
  80'di. "Yılın en ağır 20 olayı" sorgusu bu yüzden dönemsel olarak çarpıktı.
  Hepsi eksenleriyle yeniden puanlandı; şimdi p90 68-76, tavan 92-100.
- Sistemin kendi `» manset/kategori/puan` satırı OLDUĞU GİBİ KALIR. `puan`
  gün havuzuna göre kalibredir, `onem` mutlaktır: **toplanmaz, ortalaması
  alınmaz, aynı sıralamaya sokulmaz.** Sıralama her zaman `onem` iledir.
  İkisinin aynı kayıtta bulunması kategori uyumunu ölçülebilir kılar
  (543 çiftte %71 uyum).
- Araç: `scripts/retro_etiket.py` (`durum` / `parti [--kafesdisi]` / `yaz` /
  `uygula` / `topla` / `denetim`). `yaz` 6 alanlı TSV alır:
  `anahtar<TAB>kategori<TAB>e<TAB>k<TAB>a<TAB>s`. `denetim` kafes dışı etiket
  sayar ve varsa 1 döner — kayma alarmı olarak kullanılır.
- Depo `data/retro_etiket.json` etiketin TEK kaynağıdır; arşive doğrudan
  yazılmış etiketler `topla` ile geri okunur. `uygula` fikir-değişmezdir;
  aynı gün birden çok blok taşıyorsa anahtarlar `<tarih>#2` ile ayrışır.

#### Üretim hattı da artık bu alanı yazıyor (2026-09-23)
Skorlama ajanı aynı çağrıda dört önem eksenini de döndürüyor (`oe/ok/oa/os`);
`_normalize_record` bunları çapalara oturtuyor, `save_summary_to_archive`
`» sonradan | ... | rubrik=v2` satırını yazıyor. **Ek LLM maliyeti yok.**
- Neden şart: yıl sonuna 99 gün vardı ve bu tempoyla ~2.300 yeni kayıt
  gelecekti — havuzun üçte biri. Hat yazmasaydı "iki ayrı ölçek" sorunu
  yılın son çeyreğini kapsayarak geri gelirdi.
- `oe/ok/oa/os` ile `s/e/a/k` AYRI rubriklerdir: ikincisi o günün havuzundan
  SEÇİM yapar (`puan`), birincisi gün bağımsız MUTLAK ağırlıktır (`onem`).
- LLM eksenlerden birini vermezse satır HİÇ yazılmaz (uydurma değer yerine
  boşluk); eksik kayıtları `scripts/retro_etiket.py durum` raporlar ve
  `parti`/`yaz` ile geriye doldurulur.

### Olay kaydı — `data/olaylar.json` (`scripts/olay_kaydi.py`)
Arşiv **haber kaydı** tutar, rapor **olay** sayar. Aynı olay ardışık günlerde
yeniden raporlanır; 10 günde aynı güne ait birden çok blok vardır. Ölçüldü:
5.043 kayıt → **4.399 olay** (644 tekilleştirme), 247 olay birden çok günde.
- Kaç ayrı GÜNDE raporlandığı (`gun_sayisi`) LLM yargısı içermeyen tek önem
  sinyalidir; sıralamada `onem`den sonraki eşitlik bozucudur.
- SIRALAMA ANAHTARI: `onem` → `gun_sayisi` → kritiklik ekseni → etki ekseni →
  tarih. Yalnızca `onem` ile sıralamak YETMEZ: 84+ bandında ~300 olay berabere
  kalır ve eşitlik tarihe düşerse liste tek bir aya yığılır.
- Kümeleme bir sezgiseldir (başlıktan özel ad + CVE belirteçleri, Türkçe ekler
  için 6 karaktere gövdeleme, 10 günlük pencere, Jaccard 0,5). Anlamsal
  eşleştirme DEĞİLDİR; şüpheli birleşmeler `--ornek N` ile denetlenir.

### Analiz yapılırken UYULACAK kurallar
- Kapsam **1 Ocak 2026 sonrası**dır, ama derinlik gün gün DEĞİŞİR:
  1 Ocak – 8 Şubat günde 3 kayıt, 13 Şubat sonrası ortalama 23. Aylık
  ortalamalar da düz değil: Haziran 31,6 kayıt/gün iken Temmuz 12,9.
  **Ham aylık toplam "olay sayısı" DEĞİL, "o ay kaç haber çekilebildiği"dir**
  — her sayım `arsiv_kapsam.json`daki gün sayısına normalize edilmelidir.
- **16 gün arşivde hiç YOK**, 1 gün (21 Haziran) boş: 27 Ocak, 9-12 Şubat,
  8 Mart, 13/16/17/20/23 Nisan, 5 ve 20 Mayıs, 5/11/16/21 Haziran. Rapor bu
  listeyi açıkça yazmalı; eksik gün "olay olmadı" demek DEĞİLDİR.
- **10 günde aynı güne ait birden çok blok** vardır (aynı gün yeniden
  üretilmiş koşular, 784 kayıt). Bu günlerde aynı olay birden çok kez
  sayılabilir; `cok_bloklu_gun` listesi kontrol edilmeden trend kurulmamalı.
- Önem/kategori kırılımı **tüm yıl için tek ölçekte** yapılabilir: her
  kayıtta `» sonradan | onem` vardır. Sistemin `puan` alanı yalnızca
  23 Ağustos sonrasındadır ve AYRI ölçektir — sıralamaya sokulmaz.
- Sayım **olay** bazında isteniyorsa `data/olaylar.json` kullanılır; ham
  kayıt sayımı aynı olayın tekrarlarını olay sanar.
- Kaynak/tarih satırı ayrışmayan 9 kayıt ayrı ele alınmalı, sessizce
  toplama katılmamalıdır. Erişim etiketi 5.014 kayıtta `AÇIK`, 20 kayıtta
  `ÖZET`.
- Sayılar arşivden ÖLÇÜLEREK verilir; bellekten ya da tahminle değil.
