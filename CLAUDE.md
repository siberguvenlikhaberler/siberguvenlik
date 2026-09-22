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

### Kaynak dosyalar ve derinlikleri (2026-09-22 ölçümü)
- `data/haberler_arsiv.txt` — **OMURGA. BUDANMAZ.** 13 Şubat'tan beri 211 gün,
  4.809 haber, 7,7 MB. 17 Şubat'tan itibaren yapılı biçim: `[N] başlık`,
  paragraf, `(XXXXXXX, AÇIK - kaynak, gg.aa.yyyy)`. Kaynak+tarih 4.359 kayıtta
  (%91) ayrışıyor; 43 farklı kaynak. İlk 4 gün (13-16 Şubat) eski
  "GEMİNİ ÖZET RAPORU" biçiminde — yapılı ayrıştırma orada ÇALIŞMAZ.
- `data/skorlama_log.jsonl` — kategori, puan, yerleşim, eleme nedeni. 18 Temmuz'dan beri.
- `data/kalite_denetim.jsonl` — koşu denetimi, manşet karar izi, `metin_onarim`.
- `data/rapor_gecmis.json`, `data/kritik3_gecmis.json` — **yalnızca 30-31 gün.**
- `docs/raporlar/*.html` — **30 günde siliniyor** (`_cleanup_old_reports`).

### Arşiv üstverisi (2026-09-22'den İTİBAREN biriker, geçmişe dönük YOK)
Her arşiv kaydının altına `save_summary_to_archive` şu satırı yazar:
`» manset=evet|hayir | kategori=<kat> | puan=<n>`
Biçim bilerek küçük harf + alt çizgilidir: `_load_recent_events`'in CamelCase/
ALL-CAPS entity tarayıcısına gürültü üretmez ve `[N]` başlık kalıbına uymaz.
`»` ile başlayan satır PARAGRAF DEĞİLDİR — arşivi okuyan her kod onu atlamalıdır
(bkz. `scripts/gecmis_geri_doldur.py`).

### Analiz yapılırken UYULACAK kurallar
- Kapsam "2026 yılının tamamı" DEĞİL, **"13 Şubat 2026 sonrası"**dır; 1 Ocak –
  12 Şubat arası veri YOKTUR. Rapor bunu açıkça yazmalı.
- Kategori/puan/manşet bilgisi arşivde ancak **2026-09-22 sonrası** vardır.
  Daha eski günler için bu kırılımlar YAPILAMAZ — uydurma, "veri yok" de.
- Ayrışmayan ~450 kayıt (kaynak/tarih satırı okunamayan) ayrı ele alınmalı,
  sessizce toplama katılmamalıdır.
- Sayılar arşivden ÖLÇÜLEREK verilir; bellekten ya da tahminle değil.
