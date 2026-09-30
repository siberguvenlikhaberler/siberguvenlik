#!/usr/bin/env python3
"""KÜÇÜK MODEL DENEYİ — yalnızca ÖLÇER, hiçbir dosyaya yazmaz, üretimi
DEĞİŞTİRMEZ.

SORU: skorlamanın (kategori + puan) bir kısmını LLM yerine, kendi
etiketlerimizle eğitilmiş küçük bir modele yaptırabilir miyiz? Ölçüt TEK:
**KALİTE BOZULMAYACAK.** Maliyet ikincildir; uyum yeterli değilse hiçbir
değişiklik yapılmaz (kullanıcı kararı, 2026-09-30: "kalite bozulacaksa
bugünkü maliyetimiz normal").

EĞİTİM VERİSİ: `data/skorlama_log.jsonl` — 5.000 satır, 64 gün, her satırda
LLM'in verdiği kategori, dört alt puan ve toplam. ÖZNİTELİK olarak yalnızca
İngilizce BAŞLIK + KAYNAK vardır; log gövde metnini saklamıyor. Bu bilinçli
bir sınırdır ve ölçümün ilk sorusu zaten budur: başlık tek başına yetiyor mu?

ÜÇ ÖLÇÜ (hepsi ZAMANA SAYGILI bölmeyle — geçmişle eğit, sonraki günü tahmin
et; rastgele bölme sızıntı yaratır çünkü aynı olay ardışık günlerde döner):
  1. Kategori isabeti ve KRİTİK 3'E UYGUNLUK isabeti (zafiyet/ürün/siber-dışı
     kapısı doğru mu) — kapı yanlışsa zafiyet haberi manşete sızar.
  2. Puan hatası (MAE) ve sıralama korelasyonu.
  3. ASIL ÖLÇÜT — MANŞET ÖRTÜŞMESİ: o günün havuzunda küçük modelin
     puanlarıyla seçilen ilk 3 ile gerçekte yayımlanan KRİTİK 3 kaç haberde
     örtüşüyor. %100'ün altı, kalite kaybı demektir.

Kullanım: python3 scripts/kucuk_model_olc.py [--gun N]
Gereksinim: scikit-learn (yalnızca bu deney için; üretim bağımlılığı DEĞİL).
"""
import collections
import json
import sys

LOG = 'data/skorlama_log.jsonl'
# Kritik 3'e giremeyen kategoriler — src/config.py ile AYNI olmalı.
KRITIK3_HARIC = {'zafiyet_rutin', 'zafiyet_aktif_apt', 'urun_icerik',
                 'siber_disi'}


def _yukle():
    satirlar = []
    for ham in open(LOG, encoding='utf-8'):
        try:
            r = json.loads(ham)
        except ValueError:
            continue
        if r.get('baslik') and r.get('kat') and r.get('toplam') is not None:
            satirlar.append(r)
    satirlar.sort(key=lambda r: (r['tarih'], r.get('id') or 0))
    return satirlar


def _metin(r):
    return f"{r['baslik']} || kaynak: {r.get('kaynak') or '?'}"


def olc(egitim_gun=None):
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression, Ridge
        from sklearn.pipeline import make_pipeline
    except ImportError:
        print('scikit-learn kurulu değil: pip install scikit-learn')
        return 1
    import numpy as np

    rows = _yukle()
    gunler = sorted({r['tarih'] for r in rows})
    print(f'{len(rows)} satır | {len(gunler)} gün '
          f'({gunler[0]} → {gunler[-1]})')

    # ZAMANA SAYGILI DEĞERLENDİRME: son N günün her biri için, o günden
    # ÖNCEKİ tüm günlerle eğit, o günü tahmin et.
    test_gunleri = gunler[-(egitim_gun or 21):]
    kat_dogru = kat_top = 0
    kapi_dogru = kapi_top = 0
    mae_top = 0.0
    ortusme = []
    for gun in test_gunleri:
        egitim = [r for r in rows if r['tarih'] < gun]
        test = [r for r in rows if r['tarih'] == gun]
        if len(egitim) < 500 or len(test) < 5:
            continue
        X = [_metin(r) for r in egitim]
        kat_model = make_pipeline(
            TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=60000,
                            sublinear_tf=True),
            LogisticRegression(max_iter=2000, C=4.0))
        kat_model.fit(X, [r['kat'] for r in egitim])
        puan_model = make_pipeline(
            TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=60000,
                            sublinear_tf=True),
            Ridge(alpha=1.0))
        puan_model.fit(X, [r['toplam'] for r in egitim])

        Xt = [_metin(r) for r in test]
        kat_tah = kat_model.predict(Xt)
        puan_tah = puan_model.predict(Xt)

        for r, k in zip(test, kat_tah):
            kat_top += 1
            kat_dogru += (k == r['kat'])
            kapi_top += 1
            kapi_dogru += ((k in KRITIK3_HARIC) == (r['kat'] in KRITIK3_HARIC))
        mae_top += float(np.mean(np.abs(
            np.array([r['toplam'] for r in test]) - puan_tah)))

        # MANŞET ÖRTÜŞMESİ: gerçek KRİTİK 3 ile küçük modelin ilk 3'ü.
        gercek = {r['id'] for r in test if r.get('yerlesim') == 'kritik3'}
        if len(gercek) == 3:
            uygun = [(p, r['id']) for r, k, p in zip(test, kat_tah, puan_tah)
                     if k not in KRITIK3_HARIC]
            uygun.sort(reverse=True)
            tahmin = {i for _, i in uygun[:3]}
            ortusme.append(len(gercek & tahmin))

    n = len(test_gunleri)
    print(f'\n── ZAMANA SAYGILI DEĞERLENDİRME ({n} test günü) ──')
    print(f'kategori isabeti      : %{100*kat_dogru/max(kat_top,1):.1f} '
          f'({kat_dogru}/{kat_top})')
    print(f'KRİTİK 3 kapısı doğru : %{100*kapi_dogru/max(kapi_top,1):.1f} '
          f'— yanlış kapı = zafiyet haberi manşete sızar')
    print(f'puan MAE              : {mae_top/max(n,1):.1f} puan')
    if ortusme:
        tam = sum(1 for x in ortusme if x == 3)
        print(f'MANŞET ÖRTÜŞMESİ      : ortalama {sum(ortusme)/len(ortusme):.2f}/3 '
              f'| 3/3 tutan gün: {tam}/{len(ortusme)}')
        print('   dağılım:', dict(collections.Counter(ortusme)))
    print('\nKARAR ÖLÇÜTÜ: manşet örtüşmesi 3/3 olmadıkça üretimde hiçbir şey '
          'değişmez — kalite kaybı maliyet kazancından önemlidir.')
    return 0


if __name__ == '__main__':
    gun = next((int(a) for a in sys.argv[1:] if a.isdigit()), None)
    sys.exit(olc(gun))
