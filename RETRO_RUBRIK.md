# Geriye Dönük Etiketleme Rubriği — v1

## Neden var

Arşivdeki `» manset=... | kategori=... | puan=...` satırı yalnızca
**2026-08-23 sonrası** kayıtlarda vardır (sistem kendi üretim anında yazar;
23 Ağustos–22 Eylül aralığı `scripts/arsiv_ustveri_geri_doldur.py` ile geri
dolduruldu). Daha eski kayıtlarda kategori de puan da yoktur.

Yıl sonu çalışmasında "bu yılın en önemli 10 gelişmesi", "kategori dağılımı",
"aktör düzeyine göre kırılım" gibi sorular **tüm yılı** kapsayacaksa, eski
kayıtların da etiketlenmesi gerekir. Bu etiketleme kaçınılmaz olarak LLM
yargısıdır. Rubriğin amacı o yargıyı **tek ve yazılı bir ölçüte** bağlamak:
aynı kayıt tekrar etiketlendiğinde aynı sonucu vermeli, farklı günlerin
kayıtları birbiriyle karşılaştırılabilir olmalı.

## Kapsam

- Uygulanır: `data/haberler_arsiv.txt` içinde `» manset/kategori/puan` satırı
  **olmayan** kayıtlar (13 Şubat – 22 Ağustos 2026 arası üretim kayıtları +
  1 Ocak – 8 Şubat 2026 arası sonradan eklenen kayıtlar).
- Uygulanmaz: sistemin kendi yazdığı üstveri satırı bulunan kayıtlar. Bunlara
  **dokunulmaz**, üzerine yazılmaz.

## Yazım formatı

Sistem alanlarından **ayrı** bir satıra yazılır, kaynak satırının hemen altına:

```
» sonradan | kategori=<kategori> | onem=<0-100> | rubrik=v1
```

Kurallar:

- `» manset=` / `» kategori=` / `» puan=` satırı ASLA üretilmez, değiştirilmez,
  silinmez. `» sonradan` ayrı bir satırdır, ayrı bir alandır.
- `onem` ile sistemin `puan` alanı **aynı ölçek değildir**. `puan` günün
  havuzuna göre kalibre edilmiş bir seçim skoru; `onem` gün bağımsız, mutlak
  bir önem ölçütüdür. Yıl sonu analizinde ikisi **toplanmaz, ortalaması
  alınmaz, aynı sıralamaya sokulmaz** — hangi alanın kullanıldığı raporda
  açıkça belirtilir.
- `rubrik=v1` sürüm damgasıdır. Rubrik değişirse `v2` ile yeniden etiketlenir;
  eski satır silinmez, sürüm ayrımı analizde kullanılır.
- Manşet işareti geriye dönük **üretilmez**. O günün gerçek manşet seçimi
  bilinmiyorsa uydurulmaz.

## Kategori

Sistemin kendi kategori listesi **aynen** kullanılır (`SCORING_CATEGORIES`,
`src/config.py`) — böylece eski ve yeni kayıtlar tek dağılımda sayılabilir:

`casus_yazilim`, `nation_state_apt`, `stratejik_kurum_saldirisi`,
`kolluk_operasyonu`, `tedarik_zinciri`, `veri_ihlali`, `politika_hukuk`,
`zafiyet_aktif_apt`, `zafiyet_rutin`, `phishing_sosyal_muhendislik`,
`yapay_zeka_guvenligi`, `urun_icerik`, `siber_disi`.

Çakışma kuralı (bir haber birden çok kategoriye uyuyorsa): `KATEGORI_ONCELIK`
tablosunda **önceliği yüksek** olan seçilir. Tek istisna: haberin ASIL konusu
neyse o kazanır — devlet destekli bir grubun yol açtığı veri sızıntısı
`nation_state_apt`, ama bir şirketin sızıntısının failinin sonradan devlet
bağlantılı çıkması haberi `veri_ihlali` kalır.

## Önem puanı — 4 eksen × 0-25

Her eksen bağımsız puanlanır, toplanır. Ara değer verilmez; yalnızca
aşağıdaki çapa değerleri kullanılır (0 / 8 / 17 / 25).

### 1. Etki genişliği (0-25)
Kaç kişi/kurum/ülke doğrudan etkilendi?

- **25** — ülke çapı aşan: çok uluslu, milyonlarca kişi, birden çok ülkenin
  kritik altyapısı, ekosistem geneli (ör. 8 milyar kimlik kaydı, 2 milyon
  cihazlık botnet, 37 ülkede 70 kuruluş).
- **17** — bir ülke çapında ya da bir sektörün tamamı (ulusal telekom,
  ülkenin en büyük enerji şirketi, ulusal strateji belgesi).
- **8** — tek kurum/şirket, sınırlı kullanıcı kitlesi.
- **0** — birkaç kişi, tekil olay, ölçü verilmemiş.

### 2. Kritiklik (0-25)
Etkilenen varlığın niteliği — ne kadar yerine konulamaz?

- **25** — can/kamu güvenliği, kritik altyapı işleyişi (enerji şebekesi, su,
  savunma sistemi, denizaltı kablosu), devlet iletişiminin dinlenmesi.
- **17** — devlet kurumu, ordu, finans altyapısı, sağlık kuruluşu, kimlik/
  biyometrik veri.
- **8** — ticari veri, müşteri kişisel verisi, tek ürünün güvenliği.
- **0** — itibar/ticari zarar ötesinde somut varlık kaybı yok.

### 3. Aktör düzeyi (0-25)
Olayın arkasındaki ya da olayı yapan taraf kim?

- **25** — devlet ya da devlet destekli APT, devletin resmi kararı/operasyonu
  (yaptırım, siber silah kullanımı, yasa yürürlüğe girmesi).
- **17** — ticari casus yazılım üreticisi, organize siber suç örgütü,
  uluslararası kolluk koalisyonu.
- **8** — tekil suçlu, küçük grup, iç tehdit, kazara/teknik arıza.
- **0** — aktör belirsiz ya da haberin konusu değil.

### 4. Kalıcılık / sonuç (0-25)
Olay kapandı mı, yoksa kalıcı bir değişiklik mi bıraktı?

- **25** — kalıcı yapısal değişiklik: yürürlüğe giren yasa, ülkeler arası
  anlaşma, bir teknolojinin/tedarikçinin yasaklanması, süregiden erişim
  (pre-positioning).
- **17** — sürmekte olan kampanya, kapanmamış zafiyet, iade/dava süreci
  devam ediyor.
- **8** — olay kontrol altına alındı ama etkisi (çalınan veri, para) kalıcı.
- **0** — kapanmış dosya, geri alınmış karar, tekil ürün yaması.

### Toplam ve bantlar

`onem = e1 + e2 + e3 + e4` (0-100).

**Tavan kuralı:** `urun_icerik` ve `siber_disi` kategorilerinde `onem` en çok
**39**'dur. Gerekçe: erişim ekseni (etki genişliği) tek başına bir ürün
duyurusunu milyarlarca kullanıcı üzerinden yukarı taşıyabiliyor; bu iki
kategori sistemin kendi tablosunda da 0 önceliklidir ve yıl anlatısına
girmemelidir. Tavan, eksen puanlarını değiştirmez, yalnızca toplamı kırpar.

- **80-100** — yılın belirleyici gelişmesi; "en önemli 10" adayı.
- **60-79** — yılın anlatısında yer alması gereken gelişme.
- **40-59** — kategorisi içinde kayda değer, genel anlatıda dipnot.
- **0-39** — sayımda yer alır, anlatıda yer almaz.

## Kesişme ve tekrar kuralları

- Aynı olayın farklı günlerde çıkan parçaları ayrı ayrı etiketlenir; yıl sonu
  analizinde **olay** bazında sayım isteniyorsa tekilleştirme ayrıca yapılır.
  (Ölçüldü: 4.766 başlığın yalnızca 38'i günler arasında tekrarlıyor — çapraz
  gün mükerrer kapısı nedeniyle tekrar, önem göstergesi olarak kullanılamaz.)
- Bir haberde ölçü verilmemişse eksen **yukarı yuvarlanmaz**; veri yoksa daha
  düşük çapa seçilir. Rubrik tahmini değil, metinde yazanı puanlar.
- Kaynak metin dışında bilgi kullanılmaz. Arşiv ne diyorsa o puanlanır.

## Bilinen sınırlar (yıl sonu raporunda açıkça yazılacak)

- Kapsam **1 Ocak 2026 sonrası**dır, ama 1 Ocak – 8 Şubat aralığı günde
  yalnızca **3 haber** içerir (o dönemin kaynağı böyleydi); 13 Şubat sonrası
  günde 40+ haberdir. **Ham sayımlar bu iki dönem arasında kıyaslanamaz**;
  kıyas yalnızca oran/dağılım üzerinden yapılır.
- **27 Ocak 2026** kaydı hiç yoktur (kaynakta da yoktu).
- **9 Şubat – 12 Şubat 2026** arası kayıt yoktur.
- `onem` LLM yargısıdır; ölçüm değildir. Rubrik bu yargıyı tekrarlanabilir
  kılar, nesnel yapmaz.
