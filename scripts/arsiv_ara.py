#!/usr/bin/env python3
"""ARŞİV ARAMA — başlık VE gövde üzerinden tematik olay çıkarımı.

NEDEN VAR: yıl sonu raporu "İran-İsrail savaşında siberin kullanımı" gibi
TEMATİK sorular soracak ve bu sorular kategori/varlık alanlarıyla
karşılanamaz — tema bir kategori değil, birden çok kategoriye yayılan bir
anlatıdır (nation_state_apt + politika_hukuk + stratejik_kurum_saldirisi).

Neden BAŞLIK YETMEZ: ölçüldü (2026-09-23), İran/İsrail örüntüsü başlıklarda
177 kayıt eşleşiyor, gövdeyle birlikte 755. Aradaki 578 kayıt manşeti başka
bir şey olan ama olayı gövdede anlatan haberlerdir — "güvenlik kameralarına
sızıp füze hedeflemesi" tipi gelişmeler tam da bu kümede kalır ve başlık
taraması onları SESSİZCE düşürür.

Neden KANIT CÜMLESİ zorunlu: gövde taraması kapsamı 4 kat artırırken gürültü
de getirir (ilk ölçümde Epstein ve Notepad++ haberleri de düştü). Bu yüzden
araç bir sayı değil, her eşleşme için EŞLEŞTİĞİ CÜMLEYİ döndürür; süzme
gözle yapılır, "150 olay bulundu" denip geçilmez.

Kullanım:
  python3 scripts/arsiv_ara.py --tema iran_israil --kanit
  python3 scripts/arsiv_ara.py --kalip "kamera|CCTV" --kalip "füze|hedefleme"
  python3 scripts/arsiv_ara.py --tema kinetik --json cikti.json

`--kalip` birden çok kez verilirse VE ile bağlanır (her kalıp ayrı ayrı
eşleşmeli); tek kalıp içindeki `|` ise VEYA'dır.
"""
import argparse
import datetime
import importlib.util
import json
import pathlib
import re
import sys

ARSIV = 'data/haberler_arsiv.txt'

_KOK = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('olay_kaydi',
                                               _KOK / 'olay_kaydi.py')
olay = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(olay)

_AY = olay._AY
_GUN_RE = olay._GUN_RE
_BAS_RE = olay._BAS_RE
_SON_RE = olay._SON_RE
_KAYNAK_RE = re.compile(r'^\([^,]*,\s*(?:AÇIK|ÖZET)\s*-\s*(?:.*,\s*)?'
                        r'([^\s,]+),\s*(\d{2}\.\d{2}\.\d{4})\)$')

# TEMA = VE ile bağlı kalıp grupları. Her grup bir KOŞULDUR; kayıt ancak
# tüm gruplar eşleşirse alınır. Tek grup vermek "geniş tarama"dır.
TEMALAR = {
    # Coğrafi/aktör ekseni — tek grup, bilerek geniş.
    'iran_israil': [
        r'İran|İsrail|Tahran|Tel Aviv|Mossad|IRGC|Devrim Muhafız|'
        r'Hamas|Hizbullah|Gazze|Handala|Predatory Sparrow|Cyber Av3ngers|'
        r'MuddyWater|Charming Kitten|APT3[45]|Nobitex|Bank Sepah',
    ],
    # Siberin SAVAŞTA kullanımı — kinetik/askeri bağ ARANIR (VE).
    'kinetik': [
        r'savaş|çatışma|askeri|ordu|cephe|işgal|saldırı hazırlığ|'
        r'füze|İHA|insansız hava|drone|hava saldırı|bombard|sabotaj',
        r'siber|hack|sızma|sızdır|ele geçir|zararlı yazılım|kötü amaçlı|'
        r'kamera|CCTV|gözetim|istihbarat|hedefleme|GPS|elektronik harp|'
        r'SCADA|PLC|kritik altyapı',
    ],
    'rusya_ukrayna': [
        r'Rusya|Ukrayna|Kremlin|GRU|Sandworm|Fancy Bear|APT28|APT29|'
        r'Turla|Gamaredon|Kiev|Moskova',
    ],
    'yasal_duzenleme': [
        r'yasa|yönetmelik|düzenleme|mevzuat|direktif|yaptırım|ceza|mahkeme|'
        r'regülas|uyum zorunlu|NIS2|GDPR|KVKK|CISA direktif|yasakla',
    ],
}


def arsivi_tara(yol=ARSIV):
    """Başlık, GÖVDE, kaynak ve üstveriyi birlikte toplar.

    `»` ile başlayan satır paragraf DEĞİLDİR (CLAUDE.md); gövdeye girmez.
    """
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
            cur = {'gun': gun, 'baslik': m.group(2).strip(), 'para': [],
                   'kat': None, 'onem': None, 'eksen': None,
                   'kaynak': None, 'kaynak_tarih': None}
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
        s = satir.strip()
        if not s or s.startswith('»') or set(s) <= {'─', '='}:
            continue
        m = _KAYNAK_RE.match(s)
        if m:
            cur['kaynak'], cur['kaynak_tarih'] = m.group(1), m.group(2)
            continue
        cur['para'].append(s)
    return kayitlar


def _metin(k):
    return k['baslik'] + ' ' + ' '.join(k['para'])


_CUMLE_RE = re.compile(r'[^.!?]*[.!?]|[^.!?]+$')


def kanit(metin, kalip):
    """Eşleşmeyi İÇEREN cümleyi döndürür — süzme gözle yapılabilsin diye."""
    m = kalip.search(metin)
    if not m:
        return None
    for c in _CUMLE_RE.finditer(metin):
        if c.start() <= m.start() < c.end():
            return c.group().strip()
    return metin[max(0, m.start() - 60):m.start() + 120].strip()


def ara(kayitlar, kaliplar):
    """VE ile bağlı kalıp grupları; her grubun kanıt cümlesi taşınır."""
    derlenmis = [re.compile(p, re.I) for p in kaliplar]
    bulunan = []
    for k in kayitlar:
        metin = _metin(k)
        kanitlar = [kanit(metin, r) for r in derlenmis]
        if any(c is None for c in kanitlar):
            continue
        k = dict(k)
        k['kanit'] = kanitlar
        k['baslikta'] = any(r.search(k['baslik']) for r in derlenmis)
        bulunan.append(k)
    return bulunan


def olaylastir(bulunan):
    """Kayıtları olaya indirger — aynı olayın ardışık günleri tek satır."""
    for k in bulunan:
        k['bel'] = olay.belirtecler(k['baslik'])
    kumeler, _ = olay.kumele(bulunan)
    sonuc = []
    for indeksler in kumeler.values():
        kume = sorted((bulunan[i] for i in indeksler), key=lambda x: x['gun'])
        en = max(kume, key=lambda x: (x['onem'] or 0))
        sonuc.append({
            'baslik': en['baslik'], 'kategori': en['kat'], 'onem': en['onem'],
            'eksen': en['eksen'], 'ilk_gun': kume[0]['gun'],
            'son_gun': kume[-1]['gun'],
            'gun_sayisi': len({x['gun'] for x in kume}),
            'kayit_sayisi': len(kume),
            'baslikta': any(x['baslikta'] for x in kume),
            'kaynak': en['kaynak'], 'kanit': en['kanit'],
        })
    e = lambda o: o.get('eksen') or [0, 0, 0, 0]
    sonuc.sort(key=lambda o: (-(o['onem'] or 0), -o['gun_sayisi'],
                              -e(o)[1], -e(o)[0], o['ilk_gun']))
    return sonuc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tema', choices=sorted(TEMALAR))
    ap.add_argument('--kalip', action='append', default=[],
                    help='VE ile bağlanır; tek kalıp içinde | VEYA demektir')
    ap.add_argument('--kanit', action='store_true',
                    help='eşleşme cümlelerini yazdır (gürültü denetimi)')
    ap.add_argument('--asgari-onem', type=int, default=0)
    ap.add_argument('--top', type=int, default=30)
    ap.add_argument('--json')
    a = ap.parse_args()

    kaliplar = list(a.kalip)
    if a.tema:
        kaliplar = TEMALAR[a.tema] + kaliplar
    if not kaliplar:
        ap.error('--tema ya da --kalip verin')

    kayitlar = arsivi_tara()
    bulunan = ara(kayitlar, kaliplar)
    olaylar = [o for o in olaylastir(bulunan)
               if (o['onem'] or 0) >= a.asgari_onem]

    bas = sum(1 for k in bulunan if k['baslikta'])
    print(f'kayıt {len(kayitlar)} → eşleşen {len(bulunan)} '
          f'(başlıkta {bas}, YALNIZCA gövdede {len(bulunan) - bas}) '
          f'→ olay {len(olaylar)}')
    aylik = {}
    for o in olaylar:
        aylik[o['ilk_gun'][:7]] = aylik.get(o['ilk_gun'][:7], 0) + 1
    print('aylık:', sorted(aylik.items()))
    kat = {}
    for o in olaylar:
        kat[o['kategori']] = kat.get(o['kategori'], 0) + 1
    print('kategori:', sorted(kat.items(), key=lambda x: -x[1]))
    print()
    for o in olaylar[:a.top]:
        im = ' ' if o['baslikta'] else '·'   # · = yalnızca gövdede geçiyor
        print(f"{im}{o['onem'] or 0:>4}  {o['ilk_gun']}  "
              f"{o['kategori']}  {o['baslik']}")
        if a.kanit:
            for c in o['kanit']:
                print(f"        ↳ {c[:200]}")
    if len(olaylar) > a.top:
        print(f'... (+{len(olaylar) - a.top} olay; --top ile artırın)')
    print('\n· işareti: tema YALNIZCA gövdede geçiyor — başlık taraması '
          'bu olayı kaçırırdı.')

    if a.json:
        with open(a.json, 'w', encoding='utf-8') as f:
            json.dump({'kalip': kaliplar, 'olay': olaylar}, f,
                      ensure_ascii=False, indent=1)
        print(f'✅ {a.json}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
