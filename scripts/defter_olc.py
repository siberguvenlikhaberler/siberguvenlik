#!/usr/bin/env python3
"""OLAY DEFTERİ ÖLÇÜMÜ — "bu olay daha önce raporlandı/manşet oldu" kaydı ne
kadar güvenilir? (yalnızca OKUR)

İki soru:
  1. "Olay daha önce GÖVDEDE raporlandıysa manşet olamaz" kuralı konsa, son 31
     günün GERÇEK manşetlerinin kaçı buna takılırdı? (--kural)
  2. Defter kaç olay kuruyor ve en büyük kümeler GERÇEKTEN tek olay mı?
     (--kume, gözle denetlenir — kümeleme bir sezgiseldir)

Defter kalıcı dosya DEĞİLDİR: rapor_gecmis + kritik3_gecmis'ten her koşuda
yeniden türetilir (bkz. CLAUDE.md). Bu betik aynı türetmeyi yapar, böylece
üretimdeki kayıtla aynı kayda bakar.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import olay_iliski as oi                     # noqa: E402

VERI = Path(__file__).resolve().parent.parent / 'data'


def _sozluk(rapor):
    """ÜRETİMDEKİ sözlük: defterin jeneriklik filtresi derlemden öğrenilir.

    Bu olmadan ölçüm yanıltır — sözlüksüz koşuda 'analytic/careers/threats'
    gibi İngilizce menü sözcükleri özel ad sayılıp sahte kümeler kurar.
    main.py sözlüğü son 30 günün görünümleri + bugünün adaylarıyla kurar.
    """
    return oi.OlaySozlugu([v for g in rapor for v in rapor[g]])


def _gunler():
    rapor = {d['date']: d.get('views', [])
             for d in json.loads((VERI / 'rapor_gecmis.json').read_text('utf-8'))}
    k3 = {d['date']: d.get('views', [])
          for d in json.loads((VERI / 'kritik3_gecmis.json').read_text('utf-8'))}
    return rapor, k3


def _manset_views(views, manset_views):
    """Manşet görünümlerini rapor görünümleri içinde başlıkla eşler."""
    basliklar = {w.get('tr_title') for w in (manset_views or [])}
    return [v for v in views if v.get('tr_title') in basliklar]


def kural_olc():
    rapor, k3 = _gunler()
    defter = oi.OlayDefteri(sozluk=_sozluk(rapor))
    takilan, temiz = [], 0
    for g in sorted(set(rapor) | set(k3)):
        for v in k3.get(g, []):                        # GÜN İŞLENMEDEN sorgula
            kayit, _ = defter.esle(v)
            onceki = [x for x in (kayit or {}).get('gunler', []) if x < g]
            if onceki:
                takilan.append((g, (v.get('tr_title') or '')[:62], onceki,
                                [x for x in kayit['manset_gunleri'] if x < g]))
            else:
                temiz += 1
        views = rapor.get(g, []) or []
        defter.gunleri_isle([(g, views, _manset_views(views, k3.get(g)))])

    n = temiz + len(takilan)
    print(f"gerçek manşet: {n}  ·  'daha önce raporlandı' kuralına takılan: "
          f"{len(takilan)} (%{100*len(takilan)/max(n,1):.0f})")
    for g, t, o, m in takilan:
        print(f"  {g}  {t}\n       önceki rapor: {len(o)} gün  önceki manşet: {m}")


def yasak_olc():
    """ÜRETİMDEKİ kural: `manset_gunu_sayisi >= MANSET_TEKRAR_SINIRI` (1).

    Gerçek manşetlerin kaçı, YAYIMLANDIĞI GÜN defterde "bu olay zaten manşet
    oldu" görünüyordu? Yüksek sayı = defter kirli, çünkü bu haberler gerçekte
    o gün ilk kez manşet oldu.
    """
    rapor, k3 = _gunler()
    defter = oi.OlayDefteri(sozluk=_sozluk(rapor))
    yasak, toplam = [], 0
    for g in sorted(set(rapor) | set(k3)):
        for v in k3.get(g, []):
            toplam += 1
            n = defter.manset_gunu_sayisi(v)
            if n >= 1:
                yasak.append((g, (v.get('tr_title') or '')[:58], n))
        views = rapor.get(g, []) or []
        defter.gunleri_isle([(g, views, _manset_views(views, k3.get(g)))])
    print(f"gerçek manşet: {toplam}  ·  defter 'zaten manşet oldu' diyor: "
          f"{len(yasak)}")
    for g, t, n in yasak:
        print(f"  {g}  {t}  (sayı={n})")


def kume_olc(ornek):
    rapor, k3 = _gunler()
    defter = oi.OlayDefteri(sozluk=_sozluk(rapor))
    for g in sorted(rapor):
        views = rapor.get(g, []) or []
        defter.gunleri_isle([(g, views, _manset_views(views, k3.get(g)))])
    print(f"olay sayısı: {len(defter.kayitlar)}")
    print("gün sayısı dağılımı:",
          Counter(len(k['gunler']) for k in defter.kayitlar).most_common(10))
    print("\nEN GENİŞ KÜMELER — temsilcileri okuyun; farklı olaylar aynı kümede "
          "görünüyorsa kayıt KİRLİDİR ve manşet tekrar sayısı yanlıştır:")
    for k in sorted(defter.kayitlar, key=lambda k: -len(k['gunler']))[:ornek]:
        print(f"\n  olay {k['olay_id']}  gün={len(k['gunler'])}  "
              f"manşet={len(k['manset_gunleri'])}")
        for v in k['views']:
            print('     ·', (v.get('tr_title') or '')[:72])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kural', action='store_true')
    ap.add_argument('--kume', action='store_true')
    ap.add_argument('--yasak', action='store_true')
    ap.add_argument('--ornek', type=int, default=3)
    a = ap.parse_args()
    if not (a.kural or a.kume or a.yasak):
        a.kural = a.kume = a.yasak = True
    if a.kural:
        kural_olc()
    if a.yasak:
        print()
        yasak_olc()
    if a.kume:
        print()
        kume_olc(a.ornek)


if __name__ == '__main__':
    main()
