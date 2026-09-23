#!/usr/bin/env python3
"""OLAY KAYDI — arşiv KAYITLARINI tekilleştirip OLAY'lara indirger.

NEDEN VAR: arşiv "haber kaydı" tutar, yıl sonu raporu ise "olay" sayar. İkisi
aynı değildir ve fark küçük değildir:

  • Aynı olay ardışık günlerde yeniden raporlanır (Odido ihlali 13, 14, 15 ve
    16 Şubat bloklarının hepsinde ayrı kayıt olarak var).
  • 10 günde aynı güne ait BİRDEN ÇOK blok vardır (aynı gün yeniden üretilmiş
    koşular, 784 kayıt); bu bloklarda çoğu kayıt birebir tekrarlanır.

Tekilleştirilmeden yapılan her sayım bu tekrarları olay sanar ve en çok
işlenen olayları olduğundan büyük gösterir. Tersi de doğrudur: tekrar sayısı
ATILACAK bir gürültü değil, ÖLÇÜLEN bir önem sinyalidir — bir olayın kaç ayrı
günde raporlandığı, LLM yargısı içermeyen tek önem göstergesidir.

YÖNTEM (kasıtlı olarak basit ve denetlenebilir):
  1. Başlıktan ayırt edici belirteçler çıkarılır: özel adlar (büyük harfle
     başlayan ve durak listesinde olmayan sözcükler), ALL-CAPS kod adları,
     CVE numaraları.
  2. İki kayıt, PENCERE günü içinde kalıyorsa ve belirteç kümeleri yeterince
     örtüşüyorsa (Jaccard >= ESIK, en az 2 ortak belirteç) aynı olaydır.
  3. Kümeler geçişli birleştirilir (union-find).

SINIR: bu bir kümeleme sezgiselidir, anlamsal eşleştirme değildir. Yanlış
birleştirme riski, eşiği yüksek ve pencereyi dar tutarak sınırlandırılmıştır;
şüpheli çiftler `--ornek` ile gözle denetlenebilir.

Kullanım: python3 scripts/olay_kaydi.py [--yaz] [--ornek N]
"""
import collections
import hashlib
import datetime
import json
import re
import sys

ARSIV = 'data/haberler_arsiv.txt'
CIKTI = 'data/olaylar.json'
PENCERE = 10          # gün
ESIK = 0.5            # Jaccard
ASGARI_ORTAK = 2

_AY = {'JANUARY': 1, 'FEBRUARY': 2, 'MARCH': 3, 'APRIL': 4, 'MAY': 5,
       'JUNE': 6, 'JULY': 7, 'AUGUST': 8, 'SEPTEMBER': 9, 'OCTOBER': 10,
       'NOVEMBER': 11, 'DECEMBER': 12}
_GUN_RE = re.compile(r'📅 (\d+) ([A-ZÇĞİÖŞÜ]+) (\d{4})')
_BAS_RE = re.compile(r'\[\s*(\d+)\]\s+(.+)')
_SON_RE = re.compile(r'^» sonradan \| kategori=(\S+) \| onem=(\d+)'
                     r'(?:\s*\| eksen=(\d+)/(\d+)/(\d+)/(\d+))?')
_CVE_RE = re.compile(r'CVE-\d{4}-\d{4,6}')

# Başlıklarda sürekli geçen, ayırt ediciliği olmayan büyük harfli sözcükler.
DURAK = {
    'Siber', 'Güvenlik', 'Yeni', 'Bir', 'Büyük', 'Kritik', 'Yapay', 'Zeka',
    'Zekâ', 'Tehdit', 'Aktörü', 'Aktörlerinin', 'Aktörünün', 'Grubunun',
    'Grubu', 'Saldırı', 'Saldırısı', 'Saldırıları', 'Veri', 'İhlali',
    'Zararlı', 'Yazılım', 'Yazılımı', 'Yazılımının', 'Açığının', 'Açığı',
    'Açıkların', 'Açıkları', 'Kullanıcılarını', 'Kullanıcıların', 'Sistem',
    'Sistemleri', 'Sistemlerini', 'Platformu', 'Platformunun', 'Şirketinin',
    'Fidye', 'Kimlik', 'Avı', 'Hedef', 'Milyon', 'Bin', 'Sunucularında',
    'Sunucularının', 'Uzaktan', 'Kod', 'Yürütme', 'Çalıştırma', 'Tespit',
    'Edilmesi', 'Kapatılması', 'Yamalaması', 'Gidermesi', 'İstismar',
    'Edilmesinin', 'Hedeflemesi', 'Kullanması', 'Yönelik', 'Üzerinden',
    'Nedeniyle', 'Sonrası', 'Sonucu', 'İçin', 'İle', 'Ve', 'Bu',
}
_SOZ_RE = re.compile(r'[A-ZÇĞİÖŞÜ][\wçğıöşüÇĞİÖŞÜ\.\-]{2,}')

# Türkçe EKLER belirteci parçalar: aynı olay "İhlalinde" ve "İhlalinin",
# "Müşterilerinin" ve "Müşterilerine" olarak geçer ve küme eşiği tutmaz
# (ölçüldü: Odido ihlalinin iki günü Jaccard 0,30 ile ayrı kaldı). Belirteç
# bu yüzden ilk GOVDE karakterine kırpılır — kaba ama Türkçe için yeterli
# bir gövdeleme; ayırt ediciliği koruyacak kadar uzun tutulmuştur.
GOVDE = 6


def belirtecler(baslik):
    b = set(_CVE_RE.findall(baslik))
    for s in _SOZ_RE.findall(baslik):
        s = s.strip('.,')
        if s in DURAK or len(s) < 3:
            continue
        b.add(s[:GOVDE])
    return b


def arsivi_tara(yol=ARSIV):
    kayitlar, gun, cur = [], None, None
    for satir in open(yol, encoding='utf-8'):
        m = _GUN_RE.match(satir)
        if m:
            gun = datetime.date(int(m.group(3)), _AY[m.group(2)],
                                int(m.group(1))).isoformat()
            cur = None
            continue
        m = _BAS_RE.match(satir)
        if m:
            cur = {'gun': gun, 'sira': int(m.group(1)),
                   'baslik': m.group(2).strip(), 'kat': None, 'onem': None,
                   'eksen': None}
            cur['bel'] = belirtecler(cur['baslik'])
            kayitlar.append(cur)
            continue
        if cur is None:
            continue
        m = _SON_RE.match(satir)
        if m:
            cur['kat'], cur['onem'] = m.group(1), int(m.group(2))
            cur['eksen'] = ([int(x) for x in m.groups()[2:]]
                            if m.group(3) else None)
    return kayitlar


def _bul(ebeveyn, x):
    while ebeveyn[x] != x:
        ebeveyn[x] = ebeveyn[ebeveyn[x]]
        x = ebeveyn[x]
    return x


def kumele(kayitlar):
    ebeveyn = list(range(len(kayitlar)))
    sirali = sorted(range(len(kayitlar)), key=lambda i: kayitlar[i]['gun'])
    birlesme = []
    for p, i in enumerate(sirali):
        ki = kayitlar[i]
        gi = datetime.date.fromisoformat(ki['gun'])
        if not ki['bel']:
            continue
        for j in sirali[p + 1:]:
            kj = kayitlar[j]
            if (datetime.date.fromisoformat(kj['gun']) - gi).days > PENCERE:
                break
            ortak = ki['bel'] & kj['bel']
            if len(ortak) < ASGARI_ORTAK:
                continue
            if len(ortak) / len(ki['bel'] | kj['bel']) < ESIK:
                continue
            a, b = _bul(ebeveyn, i), _bul(ebeveyn, j)
            if a != b:
                ebeveyn[a] = b
                birlesme.append((i, j, sorted(ortak)))
    kume = collections.defaultdict(list)
    for i in range(len(kayitlar)):
        kume[_bul(ebeveyn, i)].append(i)
    return kume, birlesme


KIMLIK = 'data/olay_kimlik.json'


def kayit_kimligi(k):
    """Kaydın KALICI kimliği: gün + başlık özeti.

    Sıra numarası KULLANILMAZ — aynı gün yeniden üretilirse `[N]` kayar
    ama başlık kalır. Başlık düzeltilirse kimlik değişir; bu kabul edilen
    maliyettir, alternatifi sıra numarasıyla her yeniden üretimde TÜM
    kimlikleri kaydırmaktı.
    """
    h = hashlib.sha1(k['baslik'].strip().encode('utf-8')).hexdigest()[:8]
    return f"{k['gun']}-{h}"


def kimlik_ata(kumeler, kayitlar, onceki):
    """Kümelere KALICI olay kimliği verir; eşik değişse bile kimlik kaymaz.

    NEDEN: `olaylar.json` her koşuda yeniden TÜRETİLİR. Rapor bir olaya
    sırasıyla ya da başlığıyla atıf yaparsa, kümeleme eşiği değiştiğinde
    ya da yeni kayıt geldiğinde atıf sessizce başka bir olaya kayar.

    Kural: yeni küme, üyelerinin ÖNCEKİ koşuda taşıdığı kimliği devralır;
    birden çok kimlik varsa en çok üyeyi getiren kazanır, kaybedenler
    `takma` olarak saklanır ki eski atıflar çözülebilsin. Hiç eşleşme
    yoksa en erken üyenin kayıt kimliğinden yeni kimlik üretilir.
    """
    yeni_esleme, takma, sonuc = {}, {}, {}
    for kok, uyeler in kumeler.items():
        uye_k = [kayitlar[i] for i in uyeler]
        kimlikler = [kayit_kimligi(k) for k in uye_k]
        aday = collections.Counter(
            onceki[kk] for kk in kimlikler if kk in onceki)
        if aday:
            en_cok = max(aday.values())
            olay_id = min(k for k, v in aday.items() if v == en_cok)
            for k in aday:
                if k != olay_id:
                    takma[k] = olay_id
        else:
            olay_id = 'O-' + min(kimlikler)
        sonuc[kok] = olay_id
        for kk in kimlikler:
            yeni_esleme[kk] = olay_id
    return sonuc, yeni_esleme, takma


def kimlik_yukle(yol=KIMLIK):
    try:
        with open(yol, encoding='utf-8') as f:
            d = json.load(f)
    except (FileNotFoundError, ValueError):
        return {}, {}
    return d.get('kayit_olay', {}), d.get('takma', {})


def main():
    kayitlar = arsivi_tara()
    kume, birlesme = kumele(kayitlar)
    onceki, eski_takma = kimlik_yukle()
    kimlik, yeni_esleme, takma = kimlik_ata(kume, kayitlar, onceki)
    takma = {**eski_takma, **takma}
    olaylar = []
    for kok, uyeler in kume.items():
        k = [kayitlar[i] for i in uyeler]
        gunler = sorted({x['gun'] for x in k})
        onemler = [x['onem'] for x in k if x['onem'] is not None]
        katlar = collections.Counter(x['kat'] for x in k if x['kat'])
        # Temsilci: en yüksek onem, eşitlikte en erken gün.
        tems = max(k, key=lambda x: ((x['onem'] or 0), x['gun'] == gunler[0]))
        eks = next((x['eksen'] for x in k if x.get('eksen')), None)
        olaylar.append({
            'id': kimlik[kok],
            'baslik': tems['baslik'],
            'eksen': eks,
            'ilk_gun': gunler[0], 'son_gun': gunler[-1],
            'gun_sayisi': len(gunler), 'kayit_sayisi': len(k),
            'kategori': katlar.most_common(1)[0][0] if katlar else None,
            'onem': max(onemler) if onemler else None,
            'gunler': gunler,
        })
    # SIRALAMA ANAHTARI — `onem` tek başına sıralamaya yetmez: rubrik 25
    # değerlik bir kafes ürettiği için 84+ bandında ~300 olay BERABERE kalır
    # ve sıralama tarihe düşerse liste, yüksek puanlı olayı çok olan aya
    # kayar. Eşitlik bu yüzden ÖLÇÜLMÜŞ sinyallerle bozulur:
    #   1. onem (rubrik yargısı)
    #   2. kaç ayrı GÜNDE raporlandı (ölçüm; LLM yargısı içermez)
    #   3. kritiklik ekseni, sonra etki ekseni (yargının hangi bileşenden
    #      geldiği — can/altyapı riski, erişim genişliğine yeğlenir)
    def anahtar(o):
        e = o.get('eksen') or [0, 0, 0, 0]
        return (-(o['onem'] or 0), -o['gun_sayisi'], -e[1], -e[0], o['ilk_gun'])
    olaylar.sort(key=anahtar)
    cok = [o for o in olaylar if o['gun_sayisi'] > 1]
    print(f'kayıt {len(kayitlar)} → olay {len(olaylar)} '
          f'(tekilleştirme {len(kayitlar) - len(olaylar)})')
    print(f'birden çok GÜNDE raporlanan olay: {len(cok)} '
          f'| en çok gün: {max((o["gun_sayisi"] for o in olaylar), default=0)}')
    n = next((int(a) for a in sys.argv[1:] if a.isdigit()), 0)
    if '--ornek' in sys.argv and n:
        print('\n-- en çok günde raporlanan olaylar --')
        for o in sorted(olaylar, key=lambda x: -x['gun_sayisi'])[:n]:
            print(f'{o["gun_sayisi"]}g {o["kayit_sayisi"]}k '
                  f'onem={o["onem"]} {o["ilk_gun"]} {o["baslik"][:70]}')
    if '--top' in sys.argv:
        ust = n or 20
        print(f'\n-- sıralama anahtarına göre en ağır {ust} olay --')
        for o in olaylar[:ust]:
            print(f'{o["onem"]:3d} {o["gun_sayisi"]}g {o["ilk_gun"]} '
                  f'{(o["kategori"] or "-")[:22]:22s} {o["baslik"][:62]}')
    eski_id = set(onceki.values())
    tum = set(kimlik.values())
    yeni_id = {v for v in tum if v not in eski_id}
    print(f'kalıcı kimlik: {len(tum)} olay | yeni {len(yeni_id)} '
          f'| devralınan {len(tum) - len(yeni_id)} | takma {len(takma)}')
    if '--yaz' in sys.argv:
        with open(KIMLIK, 'w', encoding='utf-8') as f:
            json.dump({'olcum_tarihi': datetime.date.today().isoformat(),
                       'kayit_olay': yeni_esleme, 'takma': takma},
                      f, ensure_ascii=False, indent=1)
        print(f'✅ {KIMLIK}')
        with open(CIKTI, 'w', encoding='utf-8') as f:
            json.dump({'olcum_tarihi': datetime.date.today().isoformat(),
                       'pencere_gun': PENCERE, 'esik': ESIK,
                       'kayit': len(kayitlar), 'olay': len(olaylar),
                       'olaylar': olaylar}, f, ensure_ascii=False, indent=1)
        print(f'✅ {CIKTI}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
