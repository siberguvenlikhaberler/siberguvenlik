#!/usr/bin/env python3
"""ZİNCİR + MANŞET ÇEŞİTLİLİĞİ A/B ÖLÇÜMÜ — yalnızca OKUR, hiçbir şey yazmaz.

NEDEN VAR: iki katman değiştirilmeden ÖNCE, önerilen kuralın gerçek veride ne
yapacağı gün gün görülebilmeli. Katmanları ölçmeden değiştirmek bu projenin
bugüne kadarki arıza deseniydi (bkz. scripts/sokum_hazirlik.py).

ÖLÇÜLEN İKİ SORUN (2026-09-29 raporunda görüldü):
  1. SÜREGELEN HİKÂYE ZİNCİRİ ÇÖP KÖKLERLE KURULUYOR. `story_entities` tam
     metnin ilk 1500 karakterinden Başlık-Düzeni İngilizce sözcükleri özel ad
     sanıyor; zincirler `governme`, `protecti`, `united`, `court`, `personal`,
     `nearly`, `attacker`, `yazılımı` gibi köklerle bağlanıyor ve zincir
     kurulumu GEÇİŞLİ olduğu için bağımsız hikâyeler tek bloğa toplanıyor.
  2. AYNI HATTIN İKİ HABERİ AYNI GÜN MANŞET OLABİLİYOR (29 Eylül: FBI ihlali
     + Hollanda'daki ShinyHunters yakalaması).

ÖNERİLEN KURAL (bu betikte PROTOTİP olarak durur; onaylanırsa src/dedup.py'ye
taşınır ve betik oradan import eder — kural KOPYALANMAZ):
  • Zincir kimliği = yapısal kimlikler (CVE / kod adı / paket / aktör kodu)
    + derlemde NADİR (DF ≤ %0,5) VE Türkçe başlık-paragrafta da geçen özel
    adlar. İngilizce boilerplate böylece düşer.
  • Zincir kurulumu TEMSİLCİ tabanlı (olay_kaydi.kumele ile aynı felsefe),
    geçişli birleştirme YOK.
  • Manşet çeşitliliği: iki manşet aynı MARKA aktörü / aynı kurbanı / aynı
    CVE'yi paylaşıyorsa düşük puanlı olan temiz bir adayla DEĞİŞTİRİLİR
    (elenmez; KRİTİK 3 asla 2'ye düşmez).

Kullanım: python3 scripts/zincir_olc.py [--gun N] [--ayrinti]
"""
import collections
import json
import sys

sys.path.insert(0, '.')
from src import dedup  # noqa: E402

K3 = 'data/kritik3_gecmis.json'
RAPOR = 'data/rapor_gecmis.json'
LOG = 'data/skorlama_log.jsonl'
DF_TAVAN = 0.005          # bu orandan sık geçen kök AYIRT EDİCİ değildir
ZINCIR_MIN_GUN = dedup.STORY_CHAIN_MIN_DAYS
ZINCIR_ESIK = dedup.STORY_CHAIN_LINK_SHARED


def _yukle():
    k3 = json.load(open(K3, encoding='utf-8'))
    rapor = json.load(open(RAPOR, encoding='utf-8'))
    puan, kat = {}, {}
    for satir in open(LOG, encoding='utf-8'):
        try:
            r = json.loads(satir)
        except ValueError:
            continue
        anahtar = (r.get('tarih'), (r.get('baslik') or '').strip())
        puan[anahtar] = r.get('toplam') or 0
        kat[anahtar] = r.get('kat')
    return k3, rapor, puan, kat


def _df(views):
    df = collections.Counter()
    for v in views:
        for t in dedup.story_entities(v):
            df[t] += 1
    return df, max(len(views), 1)


def yeni_kimlik(view, df, n):
    """PROTOTİP — zincir kimliği: yapısal + derlemde nadir + Türkçe tarafta."""
    blob = ' '.join(dedup._bundle(view))
    kimlik = {('cve:' + a) if a.startswith('cve') else ('kod:' + a)
              for a in dedup.extract_actors(blob)}
    kimlik |= {'kod:' + c for c in dedup.extract_codenames(blob)}
    kimlik |= {'pkg:' + p for p in dedup.extract_package_names(blob)}
    tr = ((view.get('tr_title') or '') + ' ' +
          (view.get('paragraph') or '')).lower()
    kimlik |= {'ad:' + t for t in dedup.story_entities(view)
               if df.get(t, 0) / n <= DF_TAVAN and t[:6] in tr}
    return kimlik


def yeni_zincirler(gunler, kimlik_fn, min_gun=ZINCIR_MIN_GUN,
                   esik=ZINCIR_ESIK):
    """PROTOTİP — TEMSİLCİ tabanlı zincir: geçişli birleştirme YOK."""
    zin = []
    for gun, views in gunler:
        for v in views:
            e = kimlik_fn(v)
            if not e:
                continue
            hedef = next((z for z in zin if len(e & z['temsilci']) >= esik),
                         None)
            if hedef is None:
                zin.append({'temsilci': set(e), 'entities': set(e),
                            'days': {gun}, 'title': v.get('tr_title', '')})
            else:
                hedef['days'].add(gun)
                hedef['entities'] |= e
    return [{'days': sorted(z['days']), 'entities': z['entities'],
             'title': z['title']} for z in zin if len(z['days']) >= min_gun]


def _marka_aktorler(view):
    blob = ' '.join(dedup._bundle(view))
    return {a for a in dedup.extract_actors(blob) if dedup._aktor_markasi(a)}


def _guclu_kimlik(view):
    """Manşet çeşitliliği ölçütü: MARKA aktör + CVE. KOD ADI BİLEREK YOK —
    ölçüldü (2026-09-23): `kod:spycloud` iki manşeti aynı hat saymıştı, oysa
    SpyCloud olayın tarafı değil RAPORLAYAN firmaydı."""
    blob = ' '.join(dedup._bundle(view))
    return ({'aktor:' + a for a in _marka_aktorler(view)} |
            {'cve:' + a for a in dedup.extract_actors(blob)
             if a.startswith('cve')})


def olc(gun_sayisi=None, ayrinti=False):
    k3, rapor, puan, kat = _yukle()
    if gun_sayisi:
        k3, rapor = k3[-gun_sayisi:], rapor[-gun_sayisi:]
    derlem = [v for r in rapor for v in r['views']]
    df, n = _df(derlem)
    print(f'derlem {n} haber | manşet günü {len(k3)} | rapor günü {len(rapor)}')

    # ── 1) ZİNCİR: ESKİ vs YENİ ─────────────────────────────────────────
    gunler = [(r['date'], r['views']) for r in k3]
    eski = dedup.build_story_chains(gunler)
    yeni = yeni_zincirler(gunler, lambda v: yeni_kimlik(v, df, n))
    print(f'\n── ZİNCİR ── eski {len(eski)} zincir '
          f'({sum(len(z["days"]) for z in eski)} gün) | '
          f'yeni {len(yeni)} zincir ({sum(len(z["days"]) for z in yeni)} gün)')
    for ad, kume in (('ESKİ', eski), ('YENİ', yeni)):
        for z in sorted(kume, key=lambda z: -len(z['days'])):
            print(f'   {ad} {len(z["days"])} gün {z["days"][0]}→{z["days"][-1]}'
                  f' | {sorted(z["entities"])[:6]}')
            print(f'        {z["title"][:66]}')

    # ── 2) GÜN GÜN: hangi haber hangi kuralla manşet havuzundan düşerdi ──
    print('\n── GÜNLÜK FARK (zincire takılan rapor haberleri) ──')
    top_e = top_y = 0
    for r in rapor:
        gecmis = [(x['date'], x['views']) for x in k3 if x['date'] < r['date']]
        if not gecmis:
            continue
        ze = dedup.build_story_chains(gecmis)
        zy = yeni_zincirler(gecmis, lambda v: yeni_kimlik(v, df, n))
        de, dy = [], []
        for v in r['views']:
            if dedup.matching_story_chain(v, ze):
                de.append(v)
            k = yeni_kimlik(v, df, n)
            if any(len(k & z['entities']) >= 1 for z in zy):
                dy.append(v)
        top_e += len(de)
        top_y += len(dy)
        if de or dy:
            print(f'   {r["date"]}: eski {len(de)}/{len(r["views"])} düşerdi, '
                  f'yeni {len(dy)}/{len(r["views"])}')
            if ayrinti:
                for v in de:
                    z = dedup.matching_story_chain(v, ze)
                    print(f'        eski→ {v["tr_title"][:52]} '
                          f'ortak={z["shared"][:4]}')
    print(f'   TOPLAM: eski {top_e} düşürme, yeni {top_y} düşürme')

    # ── 3) MANŞET ÇEŞİTLİLİĞİ ───────────────────────────────────────────
    print('\n── MANŞET ÇEŞİTLİLİĞİ (aynı gün aynı hat) ──')
    vaka = 0
    for r in k3:
        vs = r['views']
        for i in range(len(vs)):
            for j in range(i + 1, len(vs)):
                ortak = _guclu_kimlik(vs[i]) & _guclu_kimlik(vs[j])
                if not ortak:
                    continue
                vaka += 1
                gun_rapor = next((x for x in rapor if x['date'] == r['date']),
                                 None)
                manset_baslik = {(v.get('title') or '').strip() for v in vs}
                pi = puan.get((r['date'], (vs[i].get('title') or '').strip()), 0)
                pj = puan.get((r['date'], (vs[j].get('title') or '').strip()), 0)
                dusuk = vs[i] if pi <= pj else vs[j]
                aday = None
                if gun_rapor:
                    govde = [v for v in gun_rapor['views']
                             if (v.get('title') or '').strip()
                             not in manset_baslik]
                    govde.sort(key=lambda v: -puan.get(
                        (r['date'], (v.get('title') or '').strip()), 0))
                    aday = next(
                        (v for v in govde
                         if kat.get((r['date'], (v.get('title') or '').strip()))
                         not in ('zafiyet_rutin', 'zafiyet_aktif_apt',
                                 'urun_icerik', 'siber_disi')), None)
                print(f'   {r["date"]} ortak={sorted(ortak)[:3]}')
                print(f'        {vs[i]["tr_title"][:58]}')
                print(f'        {vs[j]["tr_title"][:58]}')
                print(f'        → çıkacak: {dusuk["tr_title"][:46]} '
                      f'| yerine: '
                      f'{(aday or {}).get("tr_title", "TEMİZ ADAY YOK")[:46]}')
    print(f'   TOPLAM: {vaka} vaka / {len(k3)} gün')
    return 0


if __name__ == '__main__':
    gun = next((int(a) for a in sys.argv[1:] if a.isdigit()), None)
    sys.exit(olc(gun, '--ayrinti' in sys.argv))
