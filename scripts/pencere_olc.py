#!/usr/bin/env python3
"""PENCERE ÖLÇÜMÜ — yayın tarihi ile rapor tarihi arasındaki GECİKME (yalnızca OKUR).

Soru: hafta sonu/pazartesi raporları zayıfken, 96 saatlik tazelik penceresini
genişletmek havuzu büyütür mü?

Doğrudan ölçüm (feed'i çekip 96-168 saat bandındaki maddeleri saymak) bu
ortamdan YAPILAMAZ: egress tüm dış siteleri 403 ile kesiyor (bkz.
scripts/feed_test.py). Dolaylı ama kesin bir vekil var: arşivdeki HER kaydın
kaynak satırında yayın tarihi, blok başlığında da rapor tarihi yazılı.
Gecikme dağılımı penceranın BAĞLAYICI olup olmadığını gösterir —
- Gecikmeler 0-1 günde yığılıyorsa pencere boş duruyor, genişletmek bir şey
  getirmez (havuzu daraltan şey arz ve link dedup'ıdır).
- Pazar/pazartesi gecikmeleri pencere sınırını (3-4 gün) yalıyorsa pencere
  gerçekten kesiyor demektir ve genişletme ölçülebilir kazanç getirir.

Kullanım: python3 scripts/pencere_olc.py [--gun N]
"""
import argparse
import re
from collections import Counter, defaultdict
from datetime import date, datetime

ARSIV = 'data/haberler_arsiv.txt'
GUN_RE = re.compile(r'^📅 (\d{2}) ([A-ZÇĞİÖŞÜ]+) (\d{4}) - ')
KAYNAK_RE = re.compile(r'^\(.*?,\s*(?:AÇIK|ÖZET)\s*-\s*(.+?),\s*(\d{2})\.(\d{2})\.(\d{4})\)')
AYLAR = {a: i for i, a in enumerate(
    ['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 'JULY', 'AUGUST',
     'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER'], 1)}


def kayitlari_oku(yol=ARSIV):
    """(rapor_gunu, kaynak, yayin_gunu) üçlüleri."""
    gun = None
    out = []
    with open(yol, encoding='utf-8') as f:
        for satir in f:
            m = GUN_RE.match(satir)
            if m and m.group(2) in AYLAR:
                gun = date(int(m.group(3)), AYLAR[m.group(2)], int(m.group(1)))
                continue
            m = KAYNAK_RE.match(satir.strip())
            if m and gun:
                try:
                    yayin = date(int(m.group(4)), int(m.group(3)), int(m.group(2)))
                except ValueError:
                    continue
                out.append((gun, m.group(1).strip(), yayin))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gun', type=int, default=60,
                    help='son kaç günü ölç (varsayılan 60)')
    a = ap.parse_args()

    kayitlar = kayitlari_oku()
    if not kayitlar:
        print('arşivde kayıt bulunamadı'); return
    son = max(g for g, _, _ in kayitlar)
    kayitlar = [k for k in kayitlar if (son - k[0]).days < a.gun]

    print(f"kayıt: {len(kayitlar)}  ·  {min(k[0] for k in kayitlar)} → {son}")

    # 1) Genel gecikme dağılımı
    gec = Counter()
    for rapor, _, yayin in kayitlar:
        gec[(rapor - yayin).days] += 1
    toplam = sum(gec.values())
    print("\nGECİKME (rapor günü − yayın günü), tüm günler")
    kum = 0
    for d in sorted(gec):
        kum += gec[d]
        isaret = '  ← 96s sınırı' if d == 4 else ''
        print(f"  {d:>3} gün  {gec[d]:>5}  %{100*gec[d]/toplam:>5.1f}   "
              f"kümülatif %{100*kum/toplam:>5.1f}{isaret}")

    # 2) Haftanın gününe göre: pazar/pazartesi gerçekten sınırı yalıyor mu?
    ADLAR = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz']
    hafta = defaultdict(list)
    for rapor, _, yayin in kayitlar:
        hafta[rapor.weekday()].append((rapor - yayin).days)
    print("\nRAPOR GÜNÜNE GÖRE gecikme (medyan / ortalama / ≥2 gün oranı / en büyük)")
    for wd in range(7):
        v = sorted(hafta.get(wd, []))
        if not v:
            continue
        med = v[len(v) // 2]
        ort = sum(v) / len(v)
        iki = 100 * sum(1 for x in v if x >= 2) / len(v)
        print(f"  {ADLAR[wd]}  n={len(v):>4}  medyan {med}  ort {ort:4.2f}  "
              f"≥2gün %{iki:4.1f}  maks {v[-1]}")

    # 3) Pencere sınırına yakın kayıtlar: 96s'i (4 gün) dolduran var mı?
    sinirda = [(r, k, y) for r, k, y in kayitlar if (r - y).days >= 4]
    print(f"\n4 GÜN VE ÜSTÜ gecikmeli kayıt: {len(sinirda)} "
          f"(%{100*len(sinirda)/len(kayitlar):.2f})")
    kaynak = Counter(k for _, k, _ in sinirda)
    for k, n in kaynak.most_common(10):
        print(f"    {k:<28} {n}")
    print("\nNOT: 4+ gün yalnızca TELAFİ penceresindeki kaynaklarda (168s) "
          "mümkündür; düz 96s kaynakta görülmesi beklenmez.")


if __name__ == '__main__':
    main()
