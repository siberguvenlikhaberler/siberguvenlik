#!/usr/bin/env python3
"""BİRLEŞİK OLAY TABLOSU — tüm alanları TEK satırda birleştirir.

NEDEN VAR: alanlar yapılandırıldı ama BİRLEŞTİRİLMEDİ. Kategori ve önem
5.043 kayıtta, varlık 3.711'inde, teknik 1.616'sında, kurban 1.036'sında,
ölçek 346'sında — hepsi arşiv metninde `»` satırları olarak duruyor.
`olaylar.json` ise yalnızca başlık/kategori/önem/gün taşıyordu. Bu yüzden
"Çin bağlantılı aktörün finans sektöründe, kaç kişiyi etkileyen olayı"
gibi ÇAPRAZ sorgu her seferinde arşivi yeniden ayrıştırmayı gerektiriyordu.

Bu betik olay başına TEK kayıt üretir: kimlik, başlık, kategori, önem ve
eksenleri, tarih aralığı, sektör/ülke/aktör, CVE/ürün/istismar, kurban,
nicel ölçek, kaynaklar. Sayı DEĞİL, varlık odaklıdır.

ÜRETİLEN DOSYALAR:
  data/olay_tablosu.json  — tam kayıt (çok değerli alanlar liste)
  data/olay_tablosu.csv   — düz tablo (çok değerli alanlar `;` ile)

KİMLİK `olay_kaydi.py` ile AYNIDIR (`data/olay_kimlik.json` üzerinden
devralınır), böylece iki dosya aynı olaya aynı `id` ile atıf yapar.

Kullanım: python3 scripts/olay_tablosu.py [--yaz] [--ornek N]
"""
import collections
import csv
import datetime
import importlib.util
import json
import pathlib
import re
import sys

ARSIV = 'data/haberler_arsiv.txt'
CIKTI_JSON = 'data/olay_tablosu.json'
CIKTI_CSV = 'data/olay_tablosu.csv'

_KOK = pathlib.Path(__file__).resolve().parent


def _yukle(ad):
    spec = importlib.util.spec_from_file_location(ad, _KOK / f'{ad}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


olay = _yukle('olay_kaydi')

_GUN_RE = olay._GUN_RE
_BAS_RE = olay._BAS_RE
_AY = olay._AY
_SON_RE = olay._SON_RE
_KAYNAK_RE = re.compile(r'^\([^,]*,\s*(AÇIK|ÖZET)\s*-\s*(?:.*,\s*)?'
                        r'([^\s,]+),\s*(\d{2}\.\d{2}\.\d{4})\)$')
_VARLIK_RE = re.compile(r'^» varlik \| (.+)$')
_TEKNIK_RE = re.compile(r'^» teknik \| (.+)$')
_OLCEK_RE = re.compile(r'^» olcek \| (.+)$')
_KURBAN_RE = re.compile(r'^» kurban \| ad=([^|]+)')
_URL_RE = re.compile(r'^» url=(\S+)')

# Anlatı sayımlarına GİRMEYEN kategoriler (CLAUDE.md analiz kuralı).
ANLATI_DISI = ('urun_icerik', 'siber_disi')


def _alanlar(metin):
    """`a=1 | b=2,3` → {'a': ['1'], 'b': ['2', '3']}"""
    d = {}
    for parca in metin.split('|'):
        if '=' not in parca:
            continue
        ad, _, deger = parca.partition('=')
        deger = deger.strip()
        if deger:
            d[ad.strip()] = [x.strip() for x in deger.split(',') if x.strip()]
    return d


def arsivi_tara(yol=ARSIV):
    """Kayıt başına TÜM alanlar. `»` satırı paragraf DEĞİLDİR."""
    kayitlar, gun, cur = [], None, None
    blok = {}
    for satir in open(yol, encoding='utf-8'):
        m = _GUN_RE.match(satir)
        if m:
            tarih = datetime.date(int(m.group(3)), _AY[m.group(2)],
                                  int(m.group(1))).isoformat()
            n = blok[tarih] = blok.get(tarih, 0) + 1
            gun = tarih if n == 1 else f'{tarih}#{n}'
            cur = None
            continue
        m = _BAS_RE.match(satir)
        if m:
            cur = {'anahtar': f'{gun}|{int(m.group(1))}',
                   'gun': gun.split('#')[0], 'blok': gun,
                   'baslik': m.group(2).strip(),
                   'kat': None, 'onem': None, 'eksen': None,
                   'sektor': [], 'hedef': [], 'aktor_ulke': [], 'aktor': [],
                   'cve': [], 'urun': [], 'istismar': None, 'kurban': [],
                   'olcek': {}, 'kaynak': None, 'kaynak_tarih': None,
                   'erisim': None, 'url': None}
            cur['bel'] = olay.belirtecler(cur['baslik'])
            kayitlar.append(cur)
            continue
        if cur is None:
            continue
        m = _SON_RE.match(satir)
        if m:
            cur['kat'], cur['onem'] = m.group(1), int(m.group(2))
            cur['eksen'] = ([int(x) for x in m.groups()[2:]]
                            if m.group(3) else None)
            continue
        m = _VARLIK_RE.match(satir.rstrip('\n'))
        if m:
            a = _alanlar(m.group(1))
            for k in ('sektor', 'hedef', 'aktor_ulke', 'aktor'):
                cur[k] = a.get(k, [])
            continue
        m = _TEKNIK_RE.match(satir.rstrip('\n'))
        if m:
            a = _alanlar(m.group(1))
            cur['cve'] = a.get('cve', [])
            cur['urun'] = a.get('urun', [])
            cur['istismar'] = (a.get('istismar') or [None])[0]
            continue
        m = _OLCEK_RE.match(satir.rstrip('\n'))
        if m:
            a = _alanlar(m.group(1))
            kum = set(a.get('kumulatif', []))
            for tur in ('etkilenen', 'zarar', 'fidye', 'ceza'):
                if tur in a:
                    cur['olcek'][tur] = {'deger': a[tur][0],
                                         'kumulatif': tur in kum}
            continue
        m = _KURBAN_RE.match(satir.rstrip('\n'))
        if m:
            cur['kurban'] = [x.strip() for x in m.group(1).split(',')
                             if x.strip()]
            continue
        m = _URL_RE.match(satir.rstrip('\n'))
        if m:
            cur['url'] = m.group(1)
            continue
        m = _KAYNAK_RE.match(satir.strip())
        if m:
            cur['erisim'], cur['kaynak'], cur['kaynak_tarih'] = m.groups()
    return kayitlar


def _sayi(ham):
    try:
        return int(re.sub(r'[^\d]', '', ham) or 0)
    except ValueError:
        return 0


def _olcek_birlestir(uyeler):
    """Tür başına EN BÜYÜK tekil (kümülatif OLMAYAN) değer.

    Kümülatif değerler ayrı tutulur: "yılın en pahalı saldırısı" sorgusu
    yıllık rapor toplamlarını dışarıda bırakabilsin diye.
    """
    sonuc = {}
    for tur in ('etkilenen', 'zarar', 'fidye', 'ceza'):
        adaylar = [(k['olcek'][tur]['deger'], k['olcek'][tur]['kumulatif'])
                   for k in uyeler if tur in k['olcek']]
        tekil = [d for d, kum in adaylar if not kum]
        if tekil:
            sonuc[tur] = max(tekil, key=_sayi)
        elif adaylar:
            sonuc[tur + '_kumulatif'] = max((d for d, _ in adaylar), key=_sayi)
    return sonuc


def _tekil(uyeler, alan):
    """Sıra KORUNUR (ilk görülen önce) — sözlük sırası yanlılığı olmasın."""
    gorulen, sonuc = set(), []
    for k in uyeler:
        for v in k[alan]:
            if v not in gorulen:
                gorulen.add(v)
                sonuc.append(v)
    return sonuc


def tablo_kur(kayitlar):
    kume, _ = olay.kumele(kayitlar)
    onceki, _ = olay.kimlik_yukle()
    kimlik, esleme, takma = olay.kimlik_ata(kume, kayitlar, onceki)
    satirlar = []
    for kok, indeksler in kume.items():
        u = sorted((kayitlar[i] for i in indeksler), key=lambda x: x['gun'])
        gunler = sorted({x['gun'] for x in u})
        onemler = [x['onem'] for x in u if x['onem'] is not None]
        katlar = collections.Counter(x['kat'] for x in u if x['kat'])
        tems = max(u, key=lambda x: ((x['onem'] or 0), x['gun'] == gunler[0]))
        kat = katlar.most_common(1)[0][0] if katlar else None
        satirlar.append({
            'id': kimlik[kok],
            'baslik': tems['baslik'],
            'kategori': kat,
            'anlati': kat not in ANLATI_DISI,
            'onem': max(onemler) if onemler else None,
            'eksen': next((x['eksen'] for x in u if x.get('eksen')), None),
            'ilk_gun': gunler[0], 'son_gun': gunler[-1],
            'gun_sayisi': len(gunler), 'kayit_sayisi': len(u),
            'sektor': _tekil(u, 'sektor'),
            # FAİL ROLÜ HEDEFİ EZER — kayıt düzeyinde olduğu gibi OLAY
            # düzeyinde de. Aynı olayın iki kaydı ülkeyi farklı rolde
            # görebilir (biri "Rus menşeli", öteki "Rusya'daki"); birleşim
            # ikisini de yazınca ülke yine çift rolde çıkıyordu — ölçüldü,
            # kayıt düzeyi düzeltildikten SONRA bile 22 olayda sürüyordu.
            'hedef_ulke': [x for x in _tekil(u, 'hedef')
                           if x not in set(_tekil(u, 'aktor_ulke'))],
            'aktor_ulke': _tekil(u, 'aktor_ulke'),
            'aktor': _tekil(u, 'aktor'),
            'kurban': _tekil(u, 'kurban'),
            'cve': sorted({c for x in u for c in x['cve']}),
            'urun': _tekil(u, 'urun'),
            'istismar': 'aktif' if any(x['istismar'] for x in u) else None,
            'olcek': _olcek_birlestir(u),
            'kaynaklar': sorted({x['kaynak'] for x in u if x['kaynak']}),
            'kayitlar': [x['anahtar'] for x in u],
        })
    e = lambda o: o.get('eksen') or [0, 0, 0, 0]
    satirlar.sort(key=lambda o: (-(o['onem'] or 0), -o['gun_sayisi'],
                                 -e(o)[1], -e(o)[0], o['ilk_gun']))
    return satirlar, esleme, takma


CSV_ALAN = ('id', 'ilk_gun', 'son_gun', 'gun_sayisi', 'kayit_sayisi',
            'kategori', 'anlati', 'onem', 'eksen', 'baslik', 'kurban',
            'sektor', 'hedef_ulke', 'aktor_ulke', 'aktor', 'cve', 'urun',
            'istismar', 'etkilenen', 'zarar', 'fidye', 'ceza', 'kaynaklar')


def _csv_satir(o):
    d = {a: o.get(a) for a in CSV_ALAN}
    for tur in ('etkilenen', 'zarar', 'fidye', 'ceza'):
        d[tur] = o['olcek'].get(tur, '')
    d['eksen'] = '/'.join(str(x) for x in (o['eksen'] or []))
    for a, v in list(d.items()):
        if isinstance(v, list):
            d[a] = ';'.join(v)
        elif v is None:
            d[a] = ''
        elif isinstance(v, bool):
            d[a] = 'evet' if v else 'hayir'
    return d


def main():
    kayitlar = arsivi_tara()
    satirlar, esleme, takma = tablo_kur(kayitlar)
    n = len(satirlar)
    print(f'kayıt {len(kayitlar)} → olay {n}')
    dolu = {a: sum(1 for o in satirlar if o[a])
            for a in ('sektor', 'hedef_ulke', 'aktor_ulke', 'aktor',
                      'kurban', 'cve', 'urun', 'olcek')}
    print('alan kapsamı:', {a: f'%{100*v//n} ({v})' for a, v in dolu.items()})
    print('anlatı dışı (urun_icerik/siber_disi):',
          sum(1 for o in satirlar if not o['anlati']))
    print('en çok geçen aktör:', collections.Counter(
        a for o in satirlar for a in o['aktor']).most_common(5))
    print('en çok geçen kurban:', collections.Counter(
        k for o in satirlar for k in o['kurban']).most_common(5))

    ornek = next((int(a) for a in sys.argv[1:] if a.isdigit()), 0)
    if '--ornek' in sys.argv and ornek:
        print('\n-- en ağır olaylar --')
        for o in satirlar[:ornek]:
            print(f"{o['onem']:3d} {o['id']} {o['baslik'][:58]}")
            print(f"      kurban={o['kurban']} sektor={o['sektor']} "
                  f"aktor={o['aktor']} olcek={o['olcek']}")

    if '--yaz' not in sys.argv:
        print('\n(yazmak için --yaz)')
        return 0
    with open(CIKTI_JSON, 'w', encoding='utf-8') as f:
        json.dump({'olcum_tarihi': datetime.date.today().isoformat(),
                   'kayit': len(kayitlar), 'olay': n,
                   'olaylar': satirlar}, f, ensure_ascii=False, indent=1)
    print(f'✅ {CIKTI_JSON}')
    with open(CIKTI_CSV, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=CSV_ALAN)
        w.writeheader()
        for o in satirlar:
            w.writerow(_csv_satir(o))
    print(f'✅ {CIKTI_CSV}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
