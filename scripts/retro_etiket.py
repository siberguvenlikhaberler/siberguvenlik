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
  ... | python3 scripts/retro_etiket.py yaz   # stdin: anahtar<TAB>kat<TAB>onem
"""
import datetime
import json
import os
import re
import sys

ARSIV = 'data/haberler_arsiv.txt'
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
    """Sistemin KENDİ üstverisi olmayan HER kayıt hedeftir.

    Önceden hedef sabit bir tarih aralığıydı (13 Şubat – 22 Ağustos). Bu,
    aralığın dışında kalan ama sistem üstverisi de olmayan kayıtları sessizce
    dışarıda bırakıyordu: ölçüldü (2026-09-23), 31 Ağustos ve 14 Eylül'ün
    üçer kaydı hem `» manset` hem `» sonradan` satırından yoksundu ve hiçbir
    sayımda görünmüyordu. Ölçüt artık tarih değil, üstveri YOKLUĞUDUR —
    kapsam kendiliğinden güncel kalır.
    """
    return [k for k in kayitlar if not k['sistem_ustveri']]


def depo_yukle():
    try:
        with open(DEPO, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def depo_yaz(d):
    with open(DEPO, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=0, sort_keys=True)


def dogrula(kat, onem):
    if kat not in SCORING_CATEGORIES:
        return f'geçersiz kategori: {kat}'
    if not isinstance(onem, int) or not 0 <= onem <= 100:
        return f'geçersiz onem: {onem}'
    if kat in TAVAN_KATEGORI and onem > TAVAN:
        return f'{kat} için onem tavanı {TAVAN} (bkz. RETRO_RUBRIK.md)'
    return ''


def durum():
    h = hedefler(arsivi_tara())
    d = depo_yukle()
    var = sum(1 for k in h if k['anahtar'] in d)
    yazili = sum(1 for k in h if any(_SONRADAN_RE.match(m) for m in k['meta']))
    g = sorted({k['gun'].split('#')[0] for k in h})
    print(f'hedef kayıt : {len(h)}  (sistem üstverisiz; '
          f'{g[0] if g else "-"} – {g[-1] if g else "-"})')
    print(f'depoda      : {var}  (%{100*var//max(len(h),1)})')
    print(f'arşive yazılı: {yazili}')
    eksik = [k for k in h if k['anahtar'] not in d]
    if eksik:
        print(f'sıradaki    : {eksik[0]["anahtar"]}  →  {eksik[-1]["anahtar"]}')
    return 0


def parti(adet=150, karakter=170):
    h = hedefler(arsivi_tara())
    d = depo_yukle()
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
        p = satir.split('\t')
        if len(p) != 3:
            hata.append(f'{no}: 3 alan bekleniyor → {satir[:60]}')
            continue
        anahtar, kat, onem = p[0].strip(), p[1].strip(), p[2].strip()
        if anahtar not in gecerli:
            hata.append(f'{no}: arşivde yok → {anahtar}')
            continue
        if not onem.isdigit():
            hata.append(f'{no}: onem sayı değil → {onem}')
            continue
        msg = dogrula(kat, int(onem))
        if msg:
            hata.append(f'{no}: {msg}')
            continue
        yeni[anahtar] = {'kat': kat, 'onem': int(onem)}
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
    hatali = [(a, dogrula(v.get('kat'), v.get('onem')))
              for a, v in d.items() if dogrula(v.get('kat'), v.get('onem'))]
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
    with open(ARSIV, 'w', encoding='utf-8') as f:
        f.writelines(satirlar)
    print(f'✅ {ARSIV} güncellendi')
    return 0


_SONRADAN_AYRIS = re.compile(
    r'^»\s*sonradan\s*\|\s*kategori=(\S+)\s*\|\s*onem=(\d+)')


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
        mevcut = d.get(k['anahtar'])
        if mevcut:
            if (mevcut['kat'], mevcut['onem']) != (kat, onem):
                catisma.append(k['anahtar'])
            continue
        msg = dogrula(kat, onem)
        if msg:
            print(f'HATA {k["anahtar"]}: {msg}')
            return 1
        d[k['anahtar']] = {'kat': kat, 'onem': onem}
        eklenen += 1
    if catisma:
        print(f'⚠️  {len(catisma)} anahtarda depo ile arşiv ayrışıyor '
              f'(depo korundu): {catisma[:5]}')
    depo_yaz(d)
    print(f'{eklenen} etiket arşivden toplandı | depo {once} → {len(d)}')
    return 0


if __name__ == '__main__':
    komut = sys.argv[1] if len(sys.argv) > 1 else 'durum'
    if komut == 'topla':
        sys.exit(topla())
    if komut == 'durum':
        sys.exit(durum())
    if komut == 'parti':
        say = next((int(a) for a in sys.argv[2:] if a.isdigit()), 150)
        kar = 170
        if '--karakter' in sys.argv:
            kar = int(sys.argv[sys.argv.index('--karakter') + 1])
        sys.exit(parti(say, kar))
    if komut == 'yaz':
        sys.exit(yaz())
    if komut == 'uygula':
        sys.exit(uygula('--kuru' in sys.argv))
    print(__doc__)
    sys.exit(2)
