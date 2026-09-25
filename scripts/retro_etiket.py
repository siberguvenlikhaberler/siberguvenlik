#!/usr/bin/env python3
"""Geriye dönük etiket (`» sonradan`) deposu + arşive yazıcı.

NEDEN VAR: arşivde `» manset/kategori/puan` satırı YALNIZCA 23 Ağustos 2026
sonrası kayıtlarda var. Daha eski kayıtlar için yıl sonu analizinde kategori
ve önem kırılımı yapılabilsin diye, RETRO_RUBRIK.md'ye göre üretilen etiketler
AYRI bir satıra yazılır:

    » sonradan | kategori=<kat> | onem=<0-100> | rubrik=v1

Sistem alanlarının üzerine ASLA yazılmaz; `» sonradan` ayrı alandır.

Depo: data/retro_etiket.json → {"<YYYY-MM-DD>|<sıra>": {"kat":..,"onem":..}}
Anahtar gün + blok içi sıra numarasıdır (başlık değil: başlık günler arasında
tekrarlayabilir, sıra tekrarlamaz).

Kullanım:
  python3 scripts/retro_etiket.py durum
  python3 scripts/retro_etiket.py parti [adet] [--karakter N]   # etiketlenecek sıradaki kayıtlar
  python3 scripts/retro_etiket.py uygula [--kuru]               # depoyu arşive yaz
  python3 scripts/retro_etiket.py topla                         # arşivdeki etiketleri depoya geri oku
  python3 scripts/retro_etiket.py denetim                       # ölçek kayması denetimi (CI kapısı)
  python3 scripts/retro_etiket.py parti 300 --kafesdisi         # eksenleri hesaplanmamış etiketler
  ... | python3 scripts/retro_etiket.py yaz   # stdin: anahtar<TAB>kat<TAB>onem
"""
import datetime
import json
import os
import importlib.util
import pathlib
import re
import sys

ARSIV = 'data/haberler_arsiv.txt'

# Arşiv yazımı KOPYALANMAZ — tek kapı: atomik yazım + kayıt sayısı
# kapısı (bkz. scripts/arsiv_yaz.py).
_yaz_spec = importlib.util.spec_from_file_location(
    'arsiv_yaz', pathlib.Path(__file__).resolve().parent / 'arsiv_yaz.py')
_arsiv_yaz = importlib.util.module_from_spec(_yaz_spec)
_yaz_spec.loader.exec_module(_arsiv_yaz)

DEPO = 'data/retro_etiket.json'
# Eski sabit aralık; artık hedef ölçütü tarih DEĞİL (bkz. hedefler()).
_AY = {'JANUARY': 1, 'FEBRUARY': 2, 'MARCH': 3, 'APRIL': 4, 'MAY': 5,
       'JUNE': 6, 'JULY': 7, 'AUGUST': 8, 'SEPTEMBER': 9, 'OCTOBER': 10,
       'NOVEMBER': 11, 'DECEMBER': 12}
_GUN_RE = re.compile(r'📅 (\d+) ([A-ZÇĞİÖŞÜ]+) (\d{4})')
_BAS_RE = re.compile(r'\[\s*(\d+)\]\s+(.+)')
_SONRADAN_RE = re.compile(r'^»\s*sonradan\b')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import SCORING_CATEGORIES  # noqa: E402

TAVAN_KATEGORI = {'urun_icerik', 'siber_disi'}
TAVAN = 39

# Rubriğin dört ekseni yalnızca bu çapa değerlerini alır (RETRO_RUBRIK.md).
CAPA = (0, 8, 17, 25)
# Dört çapanın toplayabileceği DEĞERLER. `onem` bu kafesin dışındaysa eksenler
# hiç hesaplanmamış, sayı doğrudan atanmış demektir — ölçüldü (2026-09-23):
# 5.043 kaydın 1.116'sı kafes dışındaydı ve bu kayıtlar üst kuyruğu
# sistematik olarak bastırıyordu (p90: kafes içi dönemde 76, dışında 68).
KAFES = sorted({a + b + c + d
                for a in CAPA for b in CAPA for c in CAPA for d in CAPA})


def arsivi_tara(yol=ARSIV):
    """[{anahtar, gun, sira, baslik, para, satir_no, meta, sistem_ustveri}]

    ANAHTAR = `<YYYY-MM-DD>|<blok içi sıra>`. Arşivde AYNI GÜNE ait birden çok
    blok olabilir (aynı gün yeniden üretilmiş koşular; ölçüldü: 10 gün, 784
    kayıt). İkinci ve sonraki bloklar `<gün>#2`, `<gün>#3` ile ayrılır —
    yoksa aynı anahtar birden çok kayda denk gelir ve tek etiket hepsine
    yazılırdı.
    """
    kayitlar, gun, cur = [], None, None
    blok_sayaci = {}
    with open(yol, encoding='utf-8') as f:
        for no, satir in enumerate(f):
            m = _GUN_RE.match(satir)
            if m:
                tarih = datetime.date(int(m.group(3)), _AY[m.group(2)],
                                      int(m.group(1))).isoformat()
                n = blok_sayaci[tarih] = blok_sayaci.get(tarih, 0) + 1
                gun = tarih if n == 1 else f'{tarih}#{n}'
                cur = None
                continue
            m = _BAS_RE.match(satir)
            if m:
                cur = {'anahtar': f'{gun}|{int(m.group(1))}', 'gun': gun,
                       'sira': int(m.group(1)), 'baslik': m.group(2).strip(),
                       'para': [], 'satir_no': no, 'meta': [],
                       'sistem_ustveri': False}
                kayitlar.append(cur)
                continue
            if cur is None:
                continue
            if satir.startswith('»'):
                cur['meta'].append(satir.rstrip('\n'))
                if not _SONRADAN_RE.match(satir):
                    cur['sistem_ustveri'] = True
                continue
            if satir.strip() and not satir.startswith(('─', '=')):
                cur['para'].append(satir.strip())
    return kayitlar


def hedefler(kayitlar):
    """ARŞİVDEKİ HER KAYIT hedeftir — sistem üstverisi olanlar DAHİL.

    Ölçüt iki kez daraldı, ikisi de sayımı bozuyordu:

    1. Önce sabit tarih aralığıydı (13 Şubat – 22 Ağustos); 31 Ağustos ve
       14 Eylül'ün üçer kaydı hiçbir listeye girmiyordu.
    2. Sonra "sistem üstverisi yok" oldu. Bu, 23 Ağustos sonrasındaki 543
       kaydı retro ölçeğin DIŞINDA bırakıyordu ve iki ölçek karşılaştırılamaz
       olduğu için yıl çapında tek bir sıralama kurulamıyordu. ÖLÇÜLDÜ
       (2026-09-23): 80+ bandındaki 485 kaydın 216'sı sistem `puan`ından
       geliyordu, oysa sistem etiketli kayıt arşivin yalnızca %10,8'i —
       "yılın en ağır olayları" listesi baştan sona son dört haftaya
       düşüyordu.

    Artık HER kayıt `» sonradan` alır; `onem` yıl boyunca tek ölçektir.
    Sistemin `» manset/kategori/puan` satırı OLDUĞU GİBİ KALIR — ayrı satır,
    ayrı alan, farklı ölçek. İkisinin aynı kayıtta bulunması bilinçlidir:
    kategori uyumu ölçülebilir hale gelir.
    """
    return list(kayitlar)


def depo_yukle():
    try:
        with open(DEPO, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def depo_yaz(d):
    with open(DEPO, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=0, sort_keys=True)


def onem_hesapla(kat, eksen):
    """Dört eksenin toplamı, tavan kuralı uygulanmış hâli."""
    t = sum(eksen)
    return min(t, TAVAN) if kat in TAVAN_KATEGORI else t


def dogrula(kat, onem, eksen=None):
    """Etiketi rubriğe göre denetler.

    `eksen` verilmişse (v2) her eksen çapa değeri olmalı ve `onem` toplamla
    birebir tutmalıdır. Verilmemişse (v1, eski kayıtlar) en azından toplamın
    KAFES üzerinde olması aranır: kafes dışı bir sayı, eksenlerin hiç
    hesaplanmadığının kanıtıdır.
    """
    if kat not in SCORING_CATEGORIES:
        return f'geçersiz kategori: {kat}'
    if not isinstance(onem, int) or not 0 <= onem <= 100:
        return f'geçersiz onem: {onem}'
    if eksen is not None:
        if len(eksen) != 4 or any(x not in CAPA for x in eksen):
            return f'eksenler {CAPA} dışında: {eksen}'
        bek = onem_hesapla(kat, eksen)
        if onem != bek:
            return f'onem {onem}, eksen toplamı {bek} (tavan sonrası)'
        return ''
    if kat in TAVAN_KATEGORI:
        if onem > TAVAN:
            return f'{kat} için onem tavanı {TAVAN} (bkz. RETRO_RUBRIK.md)'
        return ''
    if onem not in KAFES:
        return f'onem={onem} rubrik kafesinde yok (eksenler hesaplanmamış)'
    return ''



def durum():
    h = hedefler(arsivi_tara())
    d = depo_yukle()
    var = sum(1 for k in h if k['anahtar'] in d)
    yazili = sum(1 for k in h if any(_SONRADAN_RE.match(m) for m in k['meta']))
    g = sorted({k['gun'].split('#')[0] for k in h})
    print(f'hedef kayıt : {len(h)}  (tüm arşiv; '
          f'{g[0] if g else "-"} – {g[-1] if g else "-"})')
    print(f'depoda      : {var}  (%{100*var//max(len(h),1)})')
    print(f'arşive yazılı: {yazili}')
    eksik = [k for k in h if k['anahtar'] not in d]
    if eksik:
        print(f'sıradaki    : {eksik[0]["anahtar"]}  →  {eksik[-1]["anahtar"]}')
    return 0


def parti(adet=150, karakter=170, kafesdisi=False):
    """Etiketlenecek sıradaki kayıtları TSV olarak döker.

    `--kafesdisi`: depoda OLAN ama `onem`i rubrik kafesinde olmayan kayıtları
    döker. Bunlar eksenleri hiç hesaplanmamış etiketlerdir; v2'ye geçerken
    yeniden puanlanmaları gerekir.
    """
    h = hedefler(arsivi_tara())
    d = depo_yukle()
    if kafesdisi:
        eksik = [k for k in h
                 if k['anahtar'] in d
                 and 'eksen' not in d[k['anahtar']]
                 and dogrula(d[k['anahtar']]['kat'],
                             d[k['anahtar']]['onem'])][:adet]
    else:
        eksik = [k for k in h if k['anahtar'] not in d][:adet]
    for k in eksik:
        para = ' '.join(k['para'])[:karakter]
        print(f'{k["anahtar"]}\t{k["baslik"]}\t{para}')
    print(f'--- {len(eksik)} kayıt ---', file=sys.stderr)
    return 0


def yaz():
    """stdin'den `anahtar<TAB>kategori<TAB>onem` satırlarını depoya işler.

    Anahtar arşivde yoksa ya da rubrik doğrulaması geçmezse HİÇBİRİ yazılmaz —
    kısmi parti, sessiz boşluk demektir.
    """
    gecerli = {k['anahtar'] for k in hedefler(arsivi_tara())}
    yeni, hata = {}, []
    for no, satir in enumerate(sys.stdin, 1):
        satir = satir.strip()
        if not satir or satir.startswith('#'):
            continue
        p = [x.strip() for x in satir.split('\t')]
        if len(p) not in (3, 6):
            hata.append(f'{no}: 3 (v1) ya da 6 (v2) alan bekleniyor '
                        f'→ {satir[:60]}')
            continue
        anahtar, kat = p[0], p[1]
        if anahtar not in gecerli:
            hata.append(f'{no}: arşivde yok → {anahtar}')
            continue
        if not all(x.isdigit() for x in p[2:]):
            hata.append(f'{no}: sayı olmayan alan → {p[2:]}')
            continue
        if len(p) == 6:
            eksen = [int(x) for x in p[2:]]
            onem = onem_hesapla(kat, eksen)
            msg = dogrula(kat, onem, eksen)
            kayit = {'kat': kat, 'onem': onem, 'eksen': eksen}
        else:
            eksen, onem = None, int(p[2])
            msg = dogrula(kat, onem)
            kayit = {'kat': kat, 'onem': onem}
        if msg:
            hata.append(f'{no}: {msg}')
            continue
        yeni[anahtar] = kayit
    if hata:
        for h in hata[:20]:
            print('HATA ' + h)
        print(f'{len(hata)} hatalı satır — depoya HİÇBİR ŞEY yazılmadı.')
        return 1
    d = depo_yukle()
    once = len(d)
    d.update(yeni)
    depo_yaz(d)
    print(f'{len(yeni)} etiket işlendi | depo {once} → {len(d)}')
    return 0


def uygula(kuru=False):
    kayitlar = arsivi_tara()
    d = depo_yukle()
    hatali = [(a, dogrula(v.get('kat'), v.get('onem'), v.get('eksen')))
              for a, v in d.items()
              if dogrula(v.get('kat'), v.get('onem'), v.get('eksen'))]
    if hatali:
        for a, msg in hatali[:20]:
            print(f'HATA {a}: {msg}')
        print(f'{len(hatali)} geçersiz kayıt — hiçbir şey yazılmadı.')
        return 1

    with open(ARSIV, encoding='utf-8') as f:
        satirlar = f.readlines()

    ekle, guncelle = 0, 0
    # sondan başa: satır numaraları kaymasın
    for k in sorted(kayitlar, key=lambda x: -x['satir_no']):
        v = d.get(k['anahtar'])
        if not v:
            continue
        if v.get('eksen'):
            yeni = (f'» sonradan | kategori={v["kat"]} | onem={v["onem"]} '
                    f'| eksen={"/".join(str(x) for x in v["eksen"])} '
                    f'| rubrik=v2\n')
        else:
            yeni = (f'» sonradan | kategori={v["kat"]} | onem={v["onem"]} '
                    f'| rubrik=v1\n')
        # kaydın üstveri bloğu: kaynak satırından sonraki » satırları
        # Kayıt gövdesi: başlık → 57'lik ─ cetveli → paragraf → kaynak satırı →
        # (varsa) » üstveri satırları → boş satır → 80'lik ─ ayracı.
        # 57'lik cetvel AYRAÇ DEĞİLDİR; yalnızca 60+ uzunluktaki ─/= satırı,
        # bir sonraki başlık ya da gün başlığı kaydı bitirir.
        i = k['satir_no'] + 1
        son_icerik = i
        mevcut_sonradan = None
        while i < len(satirlar):
            s = satirlar[i]
            cip = s.rstrip('\n')
            if (_BAS_RE.match(s) or _GUN_RE.match(s)
                    or (set(cip) <= {'─', '='} and len(cip) >= 60)):
                break
            if s.startswith('»') and _SONRADAN_RE.match(s):
                mevcut_sonradan = i
            if s.strip():
                son_icerik = i + 1
            i += 1
        if mevcut_sonradan is not None:
            if satirlar[mevcut_sonradan] != yeni:
                satirlar[mevcut_sonradan] = yeni
                guncelle += 1
        else:
            satirlar.insert(son_icerik, yeni)
            ekle += 1

    print(f'eklenecek: {ekle} | güncellenecek: {guncelle}')
    if kuru:
        print('(kuru koşu — yazmak için --kuru olmadan çalıştır)')
        return 0
    _arsiv_yaz.guvenli_yaz(ARSIV, satirlar)
    print(f'✅ {ARSIV} güncellendi')
    return 0


_SONRADAN_AYRIS = re.compile(
    r'^»\s*sonradan\s*\|\s*kategori=(\S+)\s*\|\s*onem=(\d+)'
    r'(?:\s*\|\s*eksen=(\d+)/(\d+)/(\d+)/(\d+))?')


def topla():
    """Arşivdeki `» sonradan` satırlarını depoya GERİ okur.

    Bazı etiketler arşive depo üzerinden değil, doğrudan yazıldı: 1 Ocak –
    8 Şubat kayıtları arşive eklenirken, 13-16 Şubat ise yapılandırılırken.
    Depo ile arşiv bu yüzden ayrışmıştı (ölçüldü 2026-09-23: arşivde 4.494,
    depoda 4.289). Depo, etiketin TEK kaynağı olmalı ki sonraki bir `uygula`
    sessizce eksik yazmasın.

    Depoda ZATEN olan anahtara dokunulmaz — arşiv, deponun üzerine yazamaz.
    """
    d = depo_yukle()
    once, eklenen, catisma = len(d), 0, []
    for k in hedefler(arsivi_tara()):
        m = next((_SONRADAN_AYRIS.match(x) for x in k['meta']
                  if _SONRADAN_AYRIS.match(x)), None)
        if not m:
            continue
        kat, onem = m.group(1), int(m.group(2))
        eksen = ([int(x) for x in m.groups()[2:]] if m.group(3) else None)
        mevcut = d.get(k['anahtar'])
        if mevcut:
            if (mevcut['kat'], mevcut['onem']) != (kat, onem):
                catisma.append(k['anahtar'])
            continue
        msg = dogrula(kat, onem, eksen)
        if msg:
            print(f'HATA {k["anahtar"]}: {msg}')
            return 1
        d[k['anahtar']] = ({'kat': kat, 'onem': onem, 'eksen': eksen}
                           if eksen else {'kat': kat, 'onem': onem})
        eklenen += 1
    if catisma:
        print(f'⚠️  {len(catisma)} anahtarda depo ile arşiv ayrışıyor '
              f'(depo korundu): {catisma[:5]}')
    depo_yaz(d)
    print(f'{eklenen} etiket arşivden toplandı | depo {once} → {len(d)}')
    return 0


def denetim():
    """ÖLÇEK KAYMASI DENETİMİ — yıl boyunca tek ölçek mi, ölçer.

    NEDEN VAR: `onem` LLM yargısıdır ve yargı oturumlar arasında kayar.
    ÖLÇÜLDÜ (2026-09-23): medyan tüm aylarda 50-58 arasında sabitken üst
    kuyruk kaymıştı — p90 Şubat-Haziran'da 76, Temmuz-Eylül'de 68; tavan
    100'e karşı 80. Kayma dönemsel görünüyordu ama gerçek nedeni, 1.116
    kaydın eksenleri hesaplanmadan doğrudan sayı atanmış olmasıydı.

    Bu yüzden denetim ÖNCE kafes uyumuna bakar: kafes dışı kayıt, kaymanın
    nedenidir, belirtisi değil. Kafes tuttuğunda aylık p90/tavan dağılımı
    zaten kendiliğinden hizalanır.

    Çıkış kodu 1: kafes dışı kayıt var (CI kapısı olarak kullanılabilir).
    """
    import statistics
    kayitlar = hedefler(arsivi_tara())
    d = depo_yukle()
    ay = {}
    kafes_disi = []
    eksenli = 0
    for k in kayitlar:
        v = d.get(k['anahtar'])
        if not v:
            continue
        a = k['gun'].split('#')[0][:7]
        ay.setdefault(a, []).append(v['onem'])
        if v.get('eksen'):
            eksenli += 1
        elif dogrula(v['kat'], v['onem']):
            kafes_disi.append((k['anahtar'], v['onem']))
    print(f'etiketli kayıt : {sum(len(x) for x in ay.values())} '
          f'| eksenli (v2): {eksenli}')
    print(f'kafes dışı     : {len(kafes_disi)}')
    print('ay       n   medyan  p90  tavan')
    for a in sorted(ay):
        v = sorted(ay[a])
        print(f'{a}  {len(v):4d}  {statistics.median(v):6.0f}  '
              f'{v[int(len(v) * 0.9)]:3d}  {v[-1]:4d}')
    if kafes_disi:
        print(f'\n⚠️  {len(kafes_disi)} etikette eksenler hesaplanmamış; '
              f'ilk 5: {kafes_disi[:5]}')
        return 1
    return 0


if __name__ == '__main__':
    komut = sys.argv[1] if len(sys.argv) > 1 else 'durum'
    if komut == 'topla':
        sys.exit(topla())
    if komut == 'denetim':
        sys.exit(denetim())
    if komut == 'durum':
        sys.exit(durum())
    if komut == 'parti':
        say = next((int(a) for a in sys.argv[2:] if a.isdigit()), 150)
        kar = 170
        if '--karakter' in sys.argv:
            kar = int(sys.argv[sys.argv.index('--karakter') + 1])
        sys.exit(parti(say, kar, '--kafesdisi' in sys.argv))
    if komut == 'yaz':
        sys.exit(yaz())
    if komut == 'uygula':
        sys.exit(uygula('--kuru' in sys.argv))
    print(__doc__)
    sys.exit(2)
