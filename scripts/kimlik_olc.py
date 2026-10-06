#!/usr/bin/env python3
"""KİMLİK KANITI ÖLÇÜMÜ — olay defteri birleşmeleri hangi kanıta dayanıyor?
(yalnızca OKUR)

6 Ekim arızası: günün en büyük haberi (Danimarka nüfus kayıt sisteminden
8,8 milyon kişinin CPR verisi, 95 puan) manşete giremedi, çünkü defter onu
4 Ekim'in manşeti olan Danimarka Teknik Üniversitesi ihlaliyle (apayrı olay)
`ortak=ad:danimark,ad:denmark topic=0.17` ile aynı olay saydı. Ortak olan tek
şey ÜLKE ADIYDI — üstelik aynı ülkenin Türkçe ve İngilizce yazımı İKİ ayrı
kimlik sayıldığı için `MIN_ORTAK_AD=2` kapısı TEK varlıkla açıldı.

Bu betik her birleşmeyi kanıt sınıfına ayırır:
  · yapısal      — CVE / kod adı / paket (regexle tanımlı, güvenilir)
  · tek_varlik   — ortak adların TAMAMI tek bir ÇOK SÖZCÜKLÜ varlık
                   ("Check Point", "Hugging Face", "Coast Guard",
                   "Known Exploited", "Temsilciler Meclisi") ya da aynı adın
                   iki dildeki yazımı → kapı tek varlıkla açılmış
  · cografi      — ortak adların tamamı ülke/yer adı
  · salt_konu    — ortak kimlik yok, yalnızca konu örtüşmesi
  · adlandirilmis— geriye kalan (gerçek ortak özel ad)

`--uretim` üretim ŞEKLİNDE ölçer: defter yalnızca GEÇMİŞ günlerden kurulur,
sonra o günün manşetleri sorgulanır (`_manset_disi_ids`'in gördüğü durum).
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import olay_iliski as oi                     # noqa: E402

VERI = Path(__file__).resolve().parent.parent / 'data'


def _gunler():
    rapor = {d['date']: d.get('views', [])
             for d in json.loads((VERI / 'rapor_gecmis.json').read_text('utf-8'))}
    k3 = {d['date']: d.get('views', [])
          for d in json.loads((VERI / 'kritik3_gecmis.json').read_text('utf-8'))}
    return rapor, k3


def _bitisik(a, b, metin):
    """İki kök metinde YAN YANA mı geçiyor? (tek çok sözcüklü ad sınaması)"""
    return bool(re.search(rf'\b{re.escape(a)}\w*\s+{re.escape(b)}\w*', metin)
                or re.search(rf'\b{re.escape(b)}\w*\s+{re.escape(a)}\w*', metin))


def _tek_varlik_mi(adlar, ma, mb):
    if len(adlar) < 2:
        return True
    kalan = set(adlar)
    kume = [adlar[0]]
    kalan.discard(adlar[0])
    degisti = True
    while degisti:
        degisti = False
        for a in list(kalan):
            if any(_bitisik(a, k, ma) and _bitisik(a, k, mb) for k in kume):
                kume.append(a); kalan.discard(a); degisti = True
    return not kalan


def olc(uretim=False):
    rapor, k3 = _gunler()
    sozluk = oi.OlaySozlugu([v for g in rapor for v in rapor[g]])
    kayitlar = []
    defter = oi.OlayDefteri(sozluk=sozluk)
    orj = oi.OlayDefteri.ekle

    def ekle(self, gun, view, manset=False):
        k, il, nd = self.esle(view, explain=True)
        if k is not None and il in (oi.AYNI_GELISME, oi.YENI_GELISME):
            capa = k[oi.OlayDefteri.CAPA_ALANI]
            kayitlar.append({
                'gun': gun, 'neden': nd, 'iliski': il,
                'adlar': re.findall(r'ad:([^\s,]+)', nd),
                'yapisal': re.findall(r'(?:cve|kod|pkg):([^\s,]+)', nd),
                'a': (view.get('tr_title') or '')[:44],
                'b': (capa.get('tr_title') or '')[:44],
                'ma': oi._metin(view).lower(), 'mb': oi._metin(capa).lower(),
            })
        return orj(self, gun, view, manset)

    oi.OlayDefteri.ekle = ekle
    try:
        for g in sorted(rapor):
            bas = {w.get('tr_title') for w in k3.get(g, [])}
            defter.gunleri_isle(
                [(g, rapor[g], [v for v in rapor[g] if v.get('tr_title') in bas])])
    finally:
        oi.OlayDefteri.ekle = orj

    sinif = Counter()
    ornek = {}
    for k in kayitlar:
        if k['yapisal']:
            s = 'yapisal'
        elif not k['adlar']:
            s = 'salt_konu'
        elif all(a in getattr(oi, '_COGRAFI_AD', frozenset()) for a in k['adlar']):
            s = 'cografi'
        elif _tek_varlik_mi(k['adlar'], k['ma'], k['mb']):
            s = 'tek_varlik'
        else:
            s = 'adlandirilmis'
        sinif[s] += 1
        ornek.setdefault(s, []).append(k)

    print(f"birleşme (AYNI/YENI_GELISME): {len(kayitlar)}")
    for s in ('yapisal', 'adlandirilmis', 'tek_varlik', 'cografi', 'salt_konu'):
        n = sinif[s]
        print(f"  {s:<15} {n:>4}  %{100*n/max(len(kayitlar),1):>5.1f}")
    for s in ('tek_varlik', 'cografi'):
        if ornek.get(s):
            print(f"\n— {s.upper()} örnekleri (kapı TEK kanıtla açılmış) —")
            for k in ornek[s][:12]:
                print(f"   {k['gun']} {k['a']} ↔ {k['b']}\n        {k['neden'][:86]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--uretim', action='store_true')
    olc(ap.parse_args().uretim)


if __name__ == '__main__':
    main()
