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

### Varlık alanı — `» varlik` (`scripts/varlik_cikar.py`)
Sektör, ülke ROLÜ ve aktör kırılımı. Satır biçimi (boş alan yazılmaz):
`» varlik | sektor=finans,kamu | hedef=ABD | aktor_ulke=Rusya | aktor=APT28`
- **Yargı değil ÇIKARIM** olduğu için LLM'e değil KURALLARA bağlıdır: aynı
  arşiv her koşuda aynı sonucu verir, kayma üretmez, `--ornek` ile
  denetlenebilir. **Üretim hattı da artık bu satırı yazıyor** (2026-09-23,
  `_varlik_satiri`): kurallar kopyalanmaz, hat `scripts/varlik_cikar.py`
  modülünü çağırır — tek sözlük. Geriye dönük koşu (`--yaz`) yine gerekli
  ve fikir-değişmezdir (ikinci koşuda ekleme 0); hat yalnızca yeni
  kayıtların betik unutulduğunda sektörsüz kalmasını önler.
- **Sektör ÇOK ETİKETLİDİR.** Tek etiket seçmek seçimi sözlük sırasına
  bırakıyordu: ilk prototipte finans 961 / enerji 45 çıkmıştı — dağılım
  değil, sıralama yanlılığı. Kapsam %58; eşleşmeyenlerin çoğu (681
  `zafiyet_rutin`, 150 `urun_icerik`) gerçekten sektörsüzdür (bir Chrome
  yamasının kurban sektörü yoktur), boşluk doğru davranıştır.
- **Ülke iki rolde ayrılır.** "Çin bağlantılı grup ABD'yi hedefledi"de iki
  ülke de geçer; tek alanda toplamak "ABD en çok saldıran ülke" üretirdi.
  Rol Türkçe ipucu kalıplarıyla belirlenir (`bağlantılı/menşeli/destekli`
  → fail; `-deki/-e yönelik/hükümeti` → hedef); ipucu yoksa HEDEF sayılır,
  çünkü arşiv ağırlıklı olarak kurban perspektifinden yazılmıştır.
  **FAİL ROLÜ HEDEFİ EZER** (2026-09-25): bir ülke aynı kayıtta iki rolde
  görünmez. Ölçülmüştü: 5.109 kaydın 108'inde ülke her iki listedeydi ve
  hedef ipucu neredeyse hep yanlıştı ("Tayvan'ın Çin Menşeli Saldırılara
  Maruz Kalması"nda Çin yalnızca faildir). İpucusuz varsayılan (hedef)
  ZAYIF kestirimdir, açık fail ipucu ona üstün gelir. Kural OLAY düzeyinde
  de uygulanır
  (`olay_tablosu`), yoksa aynı olayın iki kaydı ülkeyi farklı rolde görüp
  birleşimde çift rol üretiyordu — 22 olayda sürmüştü.
  **İPUCU PENCERESİ ÖĞE SINIRINDA KESİLİR** (2026-09-25): 40 karakterlik
  ham kuyruk komşu öğeye taşıyordu; "Japonya hükümeti, Çin menşeli
  saldırılara maruz kaldı" cümlesinde Japonya "menşeli" ipucunu yakalayıp
  FAİL sayılıyordu. Virgül/nokta ve `ve/ile/ancak/fakat` sınırdır.
  **EN YAKIN İPUCU KAZANIR** (2026-09-25): önce fail ipuçlarına bakmak
  yanlıştı; "Birleşik Krallık'taki yetkililerin Rus menşeli saldırıya maruz
  kalması" kuyruğunda bitişik `'taki` (hedef) varken ilerideki `menşeli`
  (fail) kazanıyor ve KURBAN ülke fail sayılıyordu. Konum, ipucu türünden
  güvenilir bir sinyaldir.
  **SERT ÜNSÜZ EKİ** (2026-09-25): "Birleşik Krallık'taki" gibi geçişlerde
  bulunma eki sertleşir; yalnızca `'daki/'deki` aranınca 32 geçiş hedef
  ipucunu kaçırıyordu. `'taki/'teki/'ta/'te` eklendi.
  **ÜLKE ALANI DEVLETİ GÖSTERİR** (kullanıcı kararı, 2026-09-25):
  yurtdışındaki muhalif, diaspora ya da sürgün gruplar o devleti TEMSİL
  ETMEZ. "İran Devlet Destekli Hackerların İranlıları Hedeflemesi"nde İran
  yalnızca FAİLDİR — hedef alınan muhalifler İran devleti değildir. Bu
  yüzden fail/hedef ayrımında istisna YOKTUR; bir ülkenin iki rolde
  görünmesi her zaman hatadır.
  **SÖZLÜK TARAMASI** (2026-09-25): 24 ülkelik sözlükte 30 ülke EKSİKTİ
  (arşivde 15+ geçiş). Tayvan 78 geçişle en büyük boşluktu — Çin-Tayvan
  ekseni ülke kırılımında tamamen görünmüyordu; Belarus 51, Meksika 61,
  Kamboçya 39, BAE 54, Suudi Arabistan 22 da yoktu. Sözlük 53 ülkeye
  çıkarıldı. Mevcut ülkelerde eksik sıfat biçimleri de eklendi (Amerikan
  58 + Amerikalı 60, Ukraynalı 40, İsrailli 30, Hollandalı 29, Kanadalı
  21). `Koreli` TEK BAŞINA EKLENMEZ: "Kuzey Koreli" geçişlerini (150)
  yutar. Hedef ülke kapsamı %43 → %46.
  Ölçüldü (tüm düzeltmeler sonrası, kayıt düzeyi): fail Çin 180, Rusya 140,
  İran 112, Kuzey Kore 69; hedefte ABD 1.119, Rusya 324, Çin 265.
  **SEKTÖR ANAHTARI SÖZCÜK BAŞINDA ARANIR** (2026-09-25): düz alt dizi
  araması altı sektöre sahte kayıt yazıyordu — "senatosu"nda `nato` (57),
  "havalimanı"nda `liman` (32), "kullanıyordu"nda `ordu` (28),
  "çabasının"da `basın` (20), "çokuluslu"da `okul` (7), "web sunucusu
  altyapısı"nda `su altyapı`. Ülke alanındaki `hesap`/`sap` hatasının aynısı.
  Savunma 442 → 388, medya 141 → 122 kayda indi; bileşik oldukları için
  düşen `başsavcılık`/`başbakanlık` açık anahtar olarak eklendi.
  **AKTÖR SÖZLÜĞÜ 53 → 85** (2026-09-25): "grubu/çetesi/tehdit aktörü/
  olarak bilinen" bağlamı taranıp doğrulandı; MuddyWater 32, Kimsuky,
  Lotus Blossom, Famous Chollima, CyberAv3ngers, FishMonger, Fox Tempest,
  Karakurt, Trigona, REvil, INC, The Com, World Leaks ve diğerleri
  eksikti. `Larva-\d+` kod kalıbı eklendi; `WorldLeaks→World Leaks`,
  `Sodinokibi→REvil`, `Vice Society→Rapid Brigantine`, `Earth Lusca→
  FishMonger`, `Space Pirates/Erudite Mogwai→Webworm` eşanlamları bağlandı.
  Aynı bağlamda çıkan ama AKTÖR OLMAYAN adlar bilerek dışarıda: Rokarolla/
  RESURGE/GRIDTIDE/FIRESTARTER (zararlı yazılım), DarkSword/Coruna/BlueMoon
  (istismar kiti), EvilTokens (PhaaS), Nexcorium (Mirai varyantı),
  Nightmare Eclipse (ARAŞTIRMACI), Gold Eagle (ABD federal merkezi),
  Mythos (yapay zekâ modeli), Play (Google Play).
- Kapsam: sektör %58, hedef ülke %46, fail ülke %10, adlandırılmış aktör %19.
  **Bu oranlar raporda açıkça yazılmalıdır**; eşleşmeyen kayıt "o sektör/ülke
  yok" demek DEĞİLDİR.

### Teknik alan — `» teknik` (`scripts/teknik_cikar.py`)
CVE, etkilenen ürün ve aktif istismar. Satır biçimi (boş alan yazılmaz):
`» teknik | cve=CVE-2026-1731,CVE-2026-2441 | urun=Cisco | istismar=aktif`
- Kapsam (2026-09-25): CVE %18 (968 kayıt, **899 tekil açık**), ürün %27
  (1.415), aktif istismar %11. Oranlar raporda açıkça yazılmalıdır.
- **SON SINIR DA ARANIR** (2026-09-25): yalnızca baş sınır aranınca `sap`
  "saptanmıştır" içinde 161, `opera` "operasyon" içinde 698 kez
  eşleşiyordu — `hesap`/`sap` hatasının sondan tekrarı. Devam eden harf
  KÜÇÜKSE eşleşme düşer; büyük harf, rakam ve alt çizgi devamı serbesttir
  (AppleScript, CitrixBleed, AzureHound gerçek ürün sinyalidir). Sınır
  BÜYÜK/küçük harfe duyarlı yazılmalıdır: `re.I` altında `[a-z]` büyük
  harfi de yakalar ve CitrixBleed'i düşürür (`(?-i:...)`).
- **SÖZLÜK 34 → 80 SATICI** (2026-09-25): teknik bağlamlı kayıtlarda 6+
  kez geçtiği ölçülen satıcılar eksikti — AWS 72, Cloudflare 48,
  Kaspersky 44, ESET, CrowdStrike, Akamai, Okta, Sophos, SolarWinds,
  Telegram, Mozilla/Firefox, Check Point, WhatsApp, Signal, Nginx,
  PostgreSQL, Redis, Siemens, Dell, TP-Link ve yapay zekâ kümesi
  (Anthropic/Claude 70 kayıt, OpenAI 37, LiteLLM, Hugging Face, Ollama).
  `intel` TEK BAŞINA ALINMAZ: geçişlerin çoğu tehdit istihbaratı firması
  "Intel 471"dir, çip satıcısı değil.
- **Ürün yalnızca teknik ipucuyla AYNI CÜMLEDE geçerse yazılır.** Satıcı
  çoğu kez RAPORLAYAN taraftır: "RedVDS'nin çökertilmesi — Microsoft ...
  açıklamıştır" kaydı `urun=Microsoft` alıyordu. Ülke rolündeki fail/hedef
  ayrımının teknik karşılığıdır.
- İki ölçülmüş tuzak koda gömülü: düz alt dizi araması `sap`ı "hesap"
  içinde buluyordu (SAP 240 → 37); `açı[ğk]` ipucu "açıklamıştır" ve "dava
  açmıştır" ile eşleşip kolluk haberlerine teknik bağlam uyduruyordu.
- `istismar=aktif` yalnızca AÇIK ipucuyla ("aktif olarak istismar", "vahşi
  doğada", KEV). "İstismar edilebilir" (potansiyel) BİLEREK sayılmaz.
- Varlık gibi: hem geriye dönük (`--yaz`) hem üretim hattında
  (`_teknik_satiri`, sözlük kopyalanmaz — modül çağrılır).

### Ölçek alanı — `» olcek` (`scripts/olcek_cikar.py`)
Nicel etki. `onem` bir YARGIDIR, bu alan ÖLÇÜMDÜR; ikisi karıştırılmaz.
`» olcek | etkilenen=478188 | zarar=1180000USD | ceza=42000000EUR | kumulatif=zarar`
- Kapsam %6 (400 kayıt) — düşük ve öyle kalacak; raporda yazılmalıdır.
- **SÜRÜM NUMARASI SAYI DEĞİLDİR** (2026-09-25): "iOS 16 Kullanıcılarını
  Etkilemiştir" kaydı `etkilenen=16` yazıyordu; ürün adının hemen
  ardındaki rakam sürümdür (6 geçiş, hepsi saçma küçük değer).
- **KÜMÜLATİF İPUCU GENİŞLETİLDİ** (2026-09-25): 5 milyar üzeri 18 zarar
  değerinin 13'ü işaretsizdi ("Amerikalıların geçen yıl 21 milyar dolar
  kaybetmesi", "Alman şirketlerine yıllık 240 milyar dolar"). İşaretli
  kayıt 51 → 68. Çıplak `<yıl> yılında` ipucu ALINMAZ: "2018 yılında
  uğradığı saldırıda 2,5 milyon müşteri" TEKİL olaydır, tarih kümülatif
  kanıtı değildir — ilk denemede 17 kaydı yanlış işaretlemişti.
  Alan olmayan kayıt "etkisi yoktu" demek DEĞİLDİR.
- **Tür ipucu ŞARTTIR.** Aynı kalıp üç ayrı anlam taşıyor: "34 kişinin
  tutuklandığı" kurban değil, "283 milyon dolarlık bütçe" zarar değildir.
  `tutuklama` ve `butce` bilerek AYRI tutulur ve ölçek satırına YAZILMAZ.
- Her sayı, birimine uyan ipuçlarından kendisine EN YAKIN olanına bağlanır;
  cümleye tek tür atamak "42 milyon Euro ceza ... 10 milyon kişi etkilendi"
  cümlesinde ikinci sayıyı düşürüyordu.
- Tür başına METİNDE İLK geçen değer alınır. En büyüğü almak gövdedeki
  ilgisiz sayıyı seçiyordu (23andMe: manşet 47 milyon uzlaşma, gövdede
  48 milyar şirket değeri).
- **Ayırıcı yorumu çarpana bağlıdır:** "4.62 milyon" ondalık, "478.188"
  binliktir. Tek kural 4,62 milyonu 462 milyona şişiriyordu. Cümle ayırıcı
  da rakam arasındaki noktada BÖLMEZ.
- `kumulatif=` işaretli değer tekil olay değil, yıllık rapor/sektör
  toplamıdır (51 kayıt). "Yılın en pahalı saldırısı" sorgusu bunları
  DIŞARIDA bırakmalıdır.

### Kurban alanı — `» kurban` (`scripts/kurban_etiket.py`) — TEK LLM ALANI
`» kurban | ad=Odido | kaynak=llm`
- **Kurallı çıkarım DENENDİ ve ÇALIŞMADI.** Arşiv başlıkları Başlık
  Düzenindedir; her kelime büyük harfle başladığı için büyük harf özel ad
  sinyali taşımaz. Ölçüldü: başlıktan %2 kapsam ve "Veri", "Lüks Markalara
  Veri" gibi yanlış parçalar; gövdeden %1 kapsam ve raporlayan tarafın
  (Resecurity, Mandiant) kurban sanılması. Alan bu yüzden YARGIYA bağlandı
  ve satır kaynağını AÇIKÇA yazar (`kaynak=llm`) — `varlik`/`teknik`/`olcek`
  deterministiktir, bu alan değildir.
- **Hedef küme kategoriyle daraltıldı**: 2.859 kayıt (veri_ihlali,
  nation_state_apt, tedarik_zinciri, kolluk_operasyonu, casus_yazilim,
  stratejik_kurum_saldirisi, zafiyet_aktif_apt, phishing). Bir Chrome
  yamasının ya da yasa tasarısının kurbanı yoktur.
- Sonuç: 2.859 kaydın tamamı etiketlendi, **1.036'sında adlandırılmış
  kurban** (518 tekil kurum), 1.823'ü kurbansız işaretlendi. En sık:
  Fortinet 19, Cisco 16, Odido 15, LiteLLM/Microsoft/JetBrains/iRhythm 13.
- KURAL: kurban = SALDIRIYA UĞRAYAN taraf. Raporlayan firma, yamalayan
  satıcı ve failin kendisi kurban DEĞİLDİR. Tedarik zincirinde hem
  sağlayıcı hem etkilenen müşteri yazılabilir.
- Üretim hattı aynı alanı skorlama çağrısında istiyor (`kurban`, ek maliyet
  yok); `-` yanıtı alan yazdırmaz. Hat `temizle()`yi modülden çağırır —
  kural KOPYALANMAZ, yoksa aynı kurum iki ayrı kurban sayılır.
- **NORMALİZASYON (2026-09-24, hattın ilk gününde ölçüldü):** LLM adları
  İngilizce döndürdü ("Ukraine", "UAE", "European Union") oysa geriye dönük
  1.036 etiketin tamamı Türkçedir → `ESANLAM` eşlemesi Türkçeleştirir.
  Ayrıca 7 kayıtta kurum yerine KİTLE TANIMI yazılmıştı ("Developers",
  "Windows users", "Online retailers", "US Federal Agencies") → `JENERIK_SON`
  bunları düşürür. Kural HER sözcüğe bakar ("Android users in Europe and
  Canada"); `systems`/`servers` BİLEREK listede yok, gerçek şirket
  adlarında geçiyor ("Unlimited Technology Systems").
- `topla` komutu hattın arşive yazdığı etiketleri depoya geri okur; depoda
  olan anahtara DOKUNMAZ (arşiv, deponun üzerine yazamaz).
- **DENETLENDİ (2026-09-25): alanda sistematik hata YOK.** 2.887 anahtarın
  1.050'sinde ad var (534 tekil); `temizle()` yeniden koşturulduğunda
  değişen kayıt 0, kitle tanımı kaçağı 0. Satıcı adı taşıyan etiketler
  (Fortinet 19, Cisco 16, Microsoft 13) örneklendi — hepsi gerçekten
  saldırıya uğrayan taraftı, raporlayan/yamalayan satıcı değil.

### Olay kaydı — `data/olaylar.json` (`scripts/olay_kaydi.py`)
Arşiv **haber kaydı** tutar, rapor **olay** sayar. Aynı olay ardışık günlerde
yeniden raporlanır; 10 günde aynı güne ait birden çok blok vardır. Ölçüldü:
5.043 kayıt → **4.399 olay** (644 tekilleştirme), 247 olay birden çok günde.
- Kaç ayrı GÜNDE raporlandığı (`gun_sayisi`) LLM yargısı içermeyen tek önem
  sinyalidir; sıralamada `onem`den sonraki eşitlik bozucudur.
- SIRALAMA ANAHTARI: `onem` → `gun_sayisi` → kritiklik ekseni → etki ekseni →
  tarih. Yalnızca `onem` ile sıralamak YETMEZ: 84+ bandında ~300 olay berabere
  kalır ve eşitlik tarihe düşerse liste tek bir aya yığılır.
- **KALICI KİMLİK — `data/olay_kimlik.json`.** `olaylar.json` her koşuda
  yeniden TÜRETİLİR; rapor bir olaya sırasıyla ya da başlığıyla atıf
  yaparsa eşik değiştiğinde ya da yeni kayıt geldiğinde atıf sessizce
  başka olaya kayar. Her olay artık `id` taşır (`O-<gün>-<başlık özeti>`)
  ve yeni küme, üyelerinin önceki koşudaki kimliğini DEVRALIR; birden çok
  kimlik varsa çoğunluğu getiren kazanır, kaybeden `takma` olarak saklanır
  ki eski atıflar çözülebilsin. ÖLÇÜLDÜ: eşik 0,5 → 0,4 yapılınca 261 olay
  birleşti, kimliklerin TAMAMI devralındı, yeniden üretilen kimlik 0.
  Raporda olaya atıf `id` ile yapılmalıdır, sıra ya da başlıkla değil.
- Kümeleme bir sezgiseldir (başlıktan özel ad + CVE belirteçleri, Türkçe ekler
  için 6 karaktere gövdeleme, 10 günlük pencere, Jaccard 0,5). Anlamsal
  eşleştirme DEĞİLDİR; şüpheli birleşmeler `--ornek N` ile denetlenir.

### BİRLEŞİK OLAY TABLOSU — `data/olay_tablosu.json` / `.csv` (ANALİZİN YÜZEYİ)
**Çapraz sorgu buradan yapılır.** Alanlar yapılandırılmıştı ama
BİRLEŞTİRİLMEMİŞTİ: hepsi arşiv metninde `»` satırıydı, `olaylar.json` ise
yalnızca başlık/kategori/önem/gün taşıyordu. "Çin bağlantılı aktörün finans
sektöründe kaç kişiyi etkileyen olayı" sorusu her seferinde arşivi yeniden
ayrıştırmayı gerektiriyordu.
- Olay başına TEK satır: `id`, başlık, kategori, `anlati` (urun_icerik/
  siber_disi ise `false`), `onem` + eksen, ilk/son gün, gün ve kayıt sayısı,
  `sektor[]`, `hedef_ulke[]`, `aktor_ulke[]`, `aktor[]`, `kurban[]`,
  `cve[]`, `urun[]`, `istismar`, `olcek{}`, `kaynaklar[]`, `kayitlar[]`.
- **Kimlik `olaylar.json` ile AYNIDIR** (`olay_kimlik.json` üzerinden
  devralınır); iki dosya aynı olaya aynı `id` ile atıf yapar.
- Olay düzeyi kapsam (4.461 olay, 2026-09-25, sözlük taramaları sonrası):
  sektör %59, hedef ülke %47, ürün %28, kurban %21, CVE %19, aktör %18,
  fail ülke %11, ölçek %7. Olay düzeyinde
  fail Çin 155, Rusya 124, İran 102, Kuzey Kore 62; hedefte ABD 973.
  İran olay düzeyinde hedefte 122, failde 102.
- Çok değerli alanlar olay boyunca BİRLEŞTİRİLİR, sıra korunur (ilk görülen
  önce) — sözlük sırası yanlılığı olmasın. Ölçekte tür başına en büyük
  TEKİL değer alınır; kümülatif değer `*_kumulatif` olarak ayrı yazılır,
  "yılın en pahalı saldırısı" sorgusuna girmez.
- `.csv` düz tablodur (çok değerli alanlar `;` ile) — elektronik tabloda
  açılabilir.
- **Üretim hattı her arşiv yazımından sonra türetilmiş veriyi DOĞRU SIRADA
  tazeler** (`_turetilmis_veriyi_tazele`): kurban `topla` → önem `topla` →
  kapsam künyesi → olay kaydı (`olaylar.json` + `olay_kimlik.json`) → tablo.
  Künye ve etiket depoları da buradadır; ölçüldü (25 Eylül) künye 23 Eylül'de
  kalmış 5.043 kayıt gösteriyordu (arşivde 5.109) ve önem deposu 5.043'teydi
  (arşivde 5.106) — bayat payda aylık normalizasyonu sessizce bozar. SIRA ŞART: olay
  kaydı kalıcı kimlikleri üretir, tablo onları DEVRALIR. Ölçüldü
  (24 Eylül): yalnızca tablo tazelenince tablo 4.429 olaya çıkarken
  `olaylar.json` 4.399'da kalmış, yeni 30 olay kalıcı kimlik alamamıştı.
  Başarısızlık raporu DÜŞÜRMEZ; hepsi türetilmiş veridir.

### Tematik sorgu — `scripts/arsiv_ara.py` (BAŞLIK YETMEZ)
Kategori/varlık alanları bir TEMAYI karşılamaz: "İran-İsrail savaşında
siberin kullanımı" birden çok kategoriye yayılır. Araç başlık VE GÖVDE
tarar; `»` satırları paragraf sayılmaz.
- **Ölçüldü (2026-09-23):** İran/İsrail örüntüsü başlıkta 184, gövdeyle
  birlikte 755 kayıt. Aradaki 571 kaydın manşeti başka bir şeydir ama olay
  gövdede anlatılır — başlık taraması onları SESSİZCE düşürür.
- Kalıplar VE ile bağlanır (`--kalip` birden çok kez); tek kalıp içindeki
  `|` VEYA'dır. `--tema` hazır kalıp kümeleri: `iran_israil`, `kinetik`,
  `rusya_ukrayna`, `yasal_duzenleme`.
- Çıktı bir SAYI değil, her eşleşme için KANIT CÜMLESİDİR (`--kanit`).
  Gövde taraması gürültü de getirir (ilk ölçümde Epstein ve Notepad++
  haberleri düşmüştü); süzme gözle yapılır, "N olay bulundu" denip
  geçilmez. `·` işareti tema yalnızca gövdede geçiyor demektir.
- Sonuç `olay_kaydi.kumele` ile olaya indirgenir ve `onem` ile sıralanır;
  aylık dağılım `arsiv_kapsam.json` gün sayısına normalize EDİLMELİDİR.

### ANALİZ ÖNCESİ TEK KOMUT — `scripts/yilsonu_hazirla.py --yaz`
Dört adımı doğru SIRADA koşturur. Sıra önemlidir: varlık ve önem alanları
ARŞİVE yazılır, kapsam künyesi ile olay kaydı arşivden TÜRETİLİR; türetilenler
önce koşarsa eski arşivi ölçer ve rapor sessizce eski sayılarla kurulur.
1. `retro_etiket durum` — önem etiketi eksiği var mı (yazmaz)
2. `retro_etiket denetim` — kafes dışı etiket = ölçek kayması (çıkış 1)
3. `varlik_cikar --yaz` — `» varlik` satırlarını arşive yazar
4. `teknik_cikar --yaz` — `» teknik` satırlarını arşive yazar
5. `olcek_cikar --yaz` — `» olcek` satırlarını arşive yazar
6. `arsiv_kapsam --yaz` → `data/arsiv_kapsam.json`
7. `olay_kaydi --yaz` → `data/olaylar.json` + `data/olay_kimlik.json`
8. `olay_tablosu --yaz` → `data/olay_tablosu.json` + `.csv` (ÇAPRAZ SORGU)
`--yaz` verilmezse hiçbir dosyaya dokunulmaz. Hepsi fikir-değişmezdir; ne
zaman koşulduğu önemli değil, analizden hemen önce bir kez yeter.

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
  kayıtta `» sonradan | onem` vardır. Denetlendi (2026-09-25): 5.109
  kaydın tamamı etiketli, kafes dışı 0, medyan tüm aylarda 50-59. Sistemin `puan` alanı yalnızca
  23 Ağustos sonrasındadır ve AYRI ölçektir — sıralamaya sokulmaz.
- Sayım **olay** bazında isteniyorsa `data/olay_tablosu.json` kullanılır
  (tüm alanlar bağlı); ham kayıt sayımı aynı olayın tekrarlarını olay sanar.
  `olaylar.json` aynı kimlikleri taşır ama yalnızca çekirdek alanları içerir.
- Kaynak/tarih satırı ayrışmayan 9 kayıt ayrı ele alınmalı, sessizce
  toplama katılmamalıdır. Erişim etiketi 5.014 kayıtta `AÇIK`, 20 kayıtta
  `ÖZET`.
- Sayılar arşivden ÖLÇÜLEREK verilir; bellekten ya da tahminle değil.
