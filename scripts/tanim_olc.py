#!/usr/bin/env python3
"""ÜÇ AYNI-OLAY TANIMININ AYRIŞMASI (P6, yalnızca OKUR).

Manşet yolunda iki ayrı tanım iş görüyor:

  (A) `ayni_olay` → `mukerrer_karari`  — çapraz-gün eleme ve manşet
      uygunluğu bunu çağırır. Temeli `dedup.same_event`tir; üstüne ÖLÇÜLMÜŞ
      eleme süzgeçleri binmiştir (gövde kod adı + konu kapısı, salt başlık
      reddi, DF sözlüğü).
  (B) `iliski_belirle`                 — OLAY DEFTERİ bunu çağırır, yani
      "bu olay son 30 günde kaç kez manşet oldu" sorusunu yanıtlayan kayıt
      bu tanımla kurulur.

`ayni_olay`ın kendi gövdesi (B)'yi 22/38 ölçümüyle TEMEL OLARAK REDDETTİĞİNİ
yazıyor; buna rağmen defter hâlâ (B) ile kuruluyor. Bu betik ayrışmanın
BÜYÜKLÜĞÜNÜ ve YÖNÜNÜ ölçer; karar ölçümden sonra verilir.

  --ayrisma   son 31 günün ortak anahtarlı çiftlerinde (A)×(B) çapraz tablosu
  --ornek N   ayrışan çiftlerden N örnek, iki tarafın gerekçesiyle
  --golden    `dedup_golden` çiftlerinde iki tanımı etiketle karşılaştırır
  --sikilastir  defterin `ad:` kimliklerine ZİNCİR AYARINDAKİ iki süzgeci
                (DF %0,5 + Türkçe ön planda geçme) uygulayınca kaç bağ
                düşüyor; gerçek devam haberleri ayakta kalıyor mu
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
from src import olay_iliski as oi                      # noqa: E402

VERI = KOK / 'data'


def _gunler():
    return {d['date']: d.get('views', [])
            for d in json.loads(
                (VERI / 'rapor_gecmis.json').read_text('utf-8'))}


def _sozluk(rapor):
    return oi.OlaySozlugu([v for g in rapor for v in rapor[g]])


def _ciftler():
    """Son 31 günün ORTAK ANAHTARLI çapraz-gün çiftleri.

    Ortak anahtar şartı boru hattının kendi ön filtresidir
    (`aday_anahtarlari`); onsuz çift sayısı yüz binlere çıkar ve ölçüm
    üretimin hiç sormadığı çiftleri de sayar.
    """
    rapor = _gunler()
    sozluk = _sozluk(rapor)
    gunler = sorted(rapor)
    anahtar = {}
    for g in gunler:
        for v in rapor[g]:
            anahtar[id(v)] = oi.aday_anahtarlari(v)
    for i, ga in enumerate(gunler):
        for gb in gunler[:i]:
            for a in rapor[ga]:
                for b in rapor[gb]:
                    if anahtar[id(a)] & anahtar[id(b)]:
                        yield ga, a, gb, b, sozluk


def _kararlar(a, b, sozluk):
    """(A) manşet yolu · (B) defter yolu — ikisi de ÇAPRAZ-GÜN kipinde."""
    ao, ao_neden = oi.ayni_olay(a, b, sozluk=sozluk, explain=True)
    il, il_neden = oi.iliski_belirle(a, b, explain=True, sozluk=sozluk)
    bagli = il in (oi.AYNI_GELISME, oi.YENI_GELISME)
    return (ao, ao_neden), (bagli, f'{il} {il_neden}')


def ayrisma():
    tablo = Counter()
    for ga, a, gb, b, sozluk in _ciftler():
        (ao, _), (bagli, _) = _kararlar(a, b, sozluk)
        tablo[(ao, bagli)] += 1
    toplam = sum(tablo.values())
    print('ortak anahtarlı çapraz-gün çifti:', toplam)
    print('  manşet yolu(A) × defter yolu(B)')
    for ao in (True, False):
        for bg in (True, False):
            n = tablo[(ao, bg)]
            print(f'    A={"aynı" if ao else "ayrı":<4} '
                  f'B={"bağlı" if bg else "bağsız":<6} {n:>6}'
                  + ('   ← AYRIŞMA' if ao != bg and n else ''))
    ayri = tablo[(True, False)] + tablo[(False, True)]
    print(f'  ayrışan çift: {ayri} (%{100*ayri/max(toplam,1):.2f})')
    print(f'  defter DAHA GEVŞEK: {tablo[(False, True)]}  ·  '
          f'manşet yolu daha gevşek: {tablo[(True, False)]}')


def ornek(n):
    yazilan = 0
    for ga, a, gb, b, sozluk in _ciftler():
        (ao, aon), (bagli, biln) = _kararlar(a, b, sozluk)
        if ao == bagli:
            continue
        yazilan += 1
        print(f"\n[{yazilan}] {gb} ↔ {ga}  "
              f"{'defter BAĞLADI, manşet yolu AYIRDI' if bagli else 'manşet yolu BİRLEŞTİRDİ, defter ayırdı'}")
        print(f"   A: {(a.get('tr_title') or '')[:72]}")
        print(f"   B: {(b.get('tr_title') or '')[:72]}")
        print(f"   manşet yolu: {aon or '-'}")
        print(f"   defter     : {biln}")
        print(f"   konu       : {oi._konu_ortusmesi(a, b):.2f}")
        if yazilan >= n:
            break
    if not yazilan:
        print('ayrışan çift yok')


def golden():
    d = json.loads((VERI / 'dedup_golden.json').read_text('utf-8'))
    ciftler = [c for c in d['ciftler'] if c.get('a') and c.get('b')]
    if not ciftler:
        print('dedup_golden çiftleri bu betiğin beklediği biçimde değil — '
              'anahtarlar:', sorted(d['ciftler'][0]) if d['ciftler'] else '-')
        return
    skor = Counter()
    for c in ciftler:
        beklenen = bool(c.get('ayni_olay', c.get('elenir')))
        (ao, _), (bagli, _) = _kararlar(c['a'], c['b'], None)
        skor['A_dogru'] += (ao == beklenen)
        skor['B_dogru'] += (bagli == beklenen)
        skor['n'] += 1
    print(f"dedup_golden {skor['n']} çift  ·  manşet yolu(A) "
          f"{skor['A_dogru']}  ·  defter yolu(B) {skor['B_dogru']}")


def sikilastir():
    """Defterin `ad:` kimliklerine ZİNCİR AYARINDAKİ süzgeçleri uygular.

    Zincir kuralı (2026-09-29) iki süzgeç kullanıyor: derlem frekansı %0,5 ve
    "kök haberin TÜRKÇE başlık/paragrafında da geçmeli". Defterin sözlüğü ise
    yalnızca %3 DF kullanıyor ve Türkçe ön plan şartı YOK. Bu ölçüm, defterin
    bağ kurduğu her ayrışan çiftte ortak `ad:` köklerinin bu iki süzgeci
    geçip geçmediğini sayar. Yapısal kimlikler (cve/kod/pkg) MUAFTIR.
    """
    rapor = _gunler()
    sozluk = _sozluk(rapor)
    derlem = [v for g in rapor for v in rapor[g]]
    df, n = oi.dedup.story_df(derlem)
    esik = max(2, int(0.005 * n))

    def _tr(view):
        return ((view.get('tr_title') or '') + ' '
                + (view.get('paragraph') or '')).lower()

    sayim = Counter()
    for ga, a, gb, b, sozluk_ in _ciftler():
        (ao, _), (bagli, bneden) = _kararlar(a, b, sozluk)
        if not bagli or ao:
            continue                      # yalnızca defterin TEK BAŞINA bağladıkları
        sayim['toplam'] += 1
        ortak = (oi.olay_kimlikleri(a, sozluk)
                 & oi.olay_kimlikleri(b, sozluk))
        adlar = {k.split(':', 1)[1] for k in ortak if k.startswith('ad:')}
        yapisal = [k for k in ortak if not k.startswith('ad:')]
        if yapisal:
            sayim['yapisal_kimlik_var'] += 1
            continue
        if not adlar:
            sayim['salt_konu'] += 1
            continue
        kalan = {k for k in adlar
                 if df.get(k, 0) <= esik
                 and k in _tr(a) and k in _tr(b)}
        if len(kalan) >= oi.MIN_ORTAK_AD:
            sayim['süzgeçten_geçer'] += 1
        else:
            sayim['süzgeç_düşürür'] += 1
            print(f"  düşer: {gb} ↔ {ga}  ortak={sorted(adlar)} → "
                  f"{sorted(kalan)}\n         "
                  f"{(a.get('tr_title') or '')[:58]}\n         "
                  f"{(b.get('tr_title') or '')[:58]}")
    print(f"\nderlem {n} haber · DF eşiği {esik}")
    for k in ('toplam', 'yapisal_kimlik_var', 'salt_konu',
              'süzgeçten_geçer', 'süzgeç_düşürür'):
        print(f"  {k:<22}{sayim[k]:>5}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ayrisma', action='store_true')
    ap.add_argument('--ornek', type=int, default=0)
    ap.add_argument('--golden', action='store_true')
    ap.add_argument('--sikilastir', action='store_true')
    a = ap.parse_args()
    if not (a.ayrisma or a.ornek or a.golden or a.sikilastir):
        a.ayrisma = True
    if a.ayrisma:
        ayrisma()
    if a.ornek:
        ornek(a.ornek)
    if a.sikilastir:
        print()
        sikilastir()
    if a.golden:
        print()
        golden()


if __name__ == '__main__':
    main()
