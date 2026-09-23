#!/usr/bin/env python3
"""Arşivin KAPSAM KÜNYESİNİ ölçer: data/arsiv_kapsam.json.

NEDEN VAR: yıl sonu analizinde "Mart'ta X vaka, Temmuz'da Y vaka" demek,
arşivin her gün aynı derinlikte olduğunu varsaymaktır. DEĞİLDİR: 1 Ocak –
8 Şubat günde 3 haber, 13 Şubat sonrası günde 40'a kadar; arada tamamen
eksik günler var; bazı günler tek haneli. Ham aylık toplam bu yüzden
"olay sayısı"nı değil "o ay kaç haber çekilebildiğini" ölçer.

Bu betik sayımı DEĞİŞTİRMEZ; sayımın paydasını yazar. Rapor, oranları
buradaki `gun_sayisi`/`kayit` değerlerine bölerek kurmalı ve `eksik_gun`
listesini açıkça belirtmelidir.

Kullanım: python3 scripts/arsiv_kapsam.py [--yaz]
"""
import collections
import datetime
import json
import re
import sys

ARSIV = 'data/haberler_arsiv.txt'
CIKTI = 'data/arsiv_kapsam.json'
_AY = {'JANUARY': 1, 'FEBRUARY': 2, 'MARCH': 3, 'APRIL': 4, 'MAY': 5,
       'JUNE': 6, 'JULY': 7, 'AUGUST': 8, 'SEPTEMBER': 9, 'OCTOBER': 10,
       'NOVEMBER': 11, 'DECEMBER': 12}
_GUN_RE = re.compile(r'📅 (\d+) ([A-ZÇĞİÖŞÜ]+) (\d{4})')
_BAS_RE = re.compile(r'\[\s*(\d+)\]')
# Kaynak satırı ÜÇ eksende değişkenlik gösterir; sabit bir kalıp bunları
# sessizce "ayrışmadı" sayıp sayımdan düşürüyordu (ölçüldü 2026-09-23: 70
# kayıt, gerçek bozuk sayısı 4):
#   • Alan sayısı: bazı kayıtlarda araya tam URL girer
#     (`AÇIK - https://..., alan, gg.aa.yyyy`) → SON iki alan okunur.
#   • Erişim etiketi: `AÇIK` dışında `ÖZET` de kullanılmış (20 kayıt,
#     çoğu 11 Mayıs) → ikisi de kabul edilir, hangisi olduğu döndürülür.
#   • İlk alan: `XXXXXXX`, `KAYNAK` ya da kaynağın adı olabilir; okunmaz.
_KAYNAK_RE = re.compile(r'^\([^,]*,\s*(AÇIK|ÖZET)\s*-\s*(?:.*,\s*)?'
                        r'([^\s,]+),\s*(\d{2}\.\d{2}\.\d{4})\)$')

# Günde 3 haberle sınırlı, dış kaynaktan sonradan eklenen dönem. Ham sayımı
# 13 Şubat sonrasıyla KIYASLANAMAZ; ayrı paydası vardır.
SEYREK_BASLANGIC, SEYREK_BITIS = '2026-01-01', '2026-02-08'


def olc(yol=ARSIV):
    gun = None
    blok = collections.Counter()
    per = collections.Counter()
    kaynak = collections.Counter()
    ustveri = collections.Counter()
    ayrismayan = collections.Counter()
    erisim = collections.Counter()
    cur = None
    for satir in open(yol, encoding='utf-8'):
        m = _GUN_RE.match(satir)
        if m:
            gun = datetime.date(int(m.group(3)), _AY[m.group(2)],
                                int(m.group(1))).isoformat()
            blok[gun] += 1
            per[gun] += 0
            cur = None
            continue
        if _BAS_RE.match(satir) and gun:
            per[gun] += 1
            cur = {'gun': gun, 'kaynak': False}
            ayrismayan[gun] += 1        # kaynak satırı görülünce geri alınır
            continue
        if cur is None:
            continue
        m = _KAYNAK_RE.match(satir.strip())
        if m:
            cur['kaynak'] = True
            ayrismayan[cur['gun']] -= 1
            kaynak[m.group(2)] += 1
            erisim[m.group(1)] += 1
            continue
        if satir.startswith('» manset'):
            ustveri['sistem'] += 1
        elif satir.startswith('» sonradan'):
            ustveri['sonradan'] += 1

    gunler = sorted(per)
    d0 = datetime.date.fromisoformat(gunler[0])
    d1 = datetime.date.fromisoformat(gunler[-1])
    tum = [(d0 + datetime.timedelta(days=i)).isoformat()
           for i in range((d1 - d0).days + 1)]
    eksik = [g for g in tum if g not in per]
    bos = [g for g in gunler if per[g] == 0]

    toplam = sum(per.values())
    seyrek = {g: per[g] for g in gunler
              if SEYREK_BASLANGIC <= g <= SEYREK_BITIS}
    yogun = {g: per[g] for g in gunler if g > SEYREK_BITIS}

    aylik = collections.Counter()
    aylik_gun = collections.Counter()
    for g in gunler:
        aylik[g[:7]] += per[g]
        aylik_gun[g[:7]] += 1

    return {
        'olcum_tarihi': datetime.date.today().isoformat(),
        'ilk_gun': gunler[0], 'son_gun': gunler[-1],
        'gun_sayisi': len(gunler), 'kayit': toplam,
        'eksik_gun': eksik,
        'bos_gun': bos,
        'cok_bloklu_gun': {g: blok[g] for g in gunler if blok[g] > 1},
        'kaynak_ayrismayan': {g: n for g, n in sorted(ayrismayan.items())
                              if n > 0},
        'ustveri': dict(ustveri),
        'erisim': dict(erisim),
        'donem': {
            'seyrek': {'aralik': [SEYREK_BASLANGIC, SEYREK_BITIS],
                       'gun': len(seyrek), 'kayit': sum(seyrek.values()),
                       'gun_basina': round(
                           sum(seyrek.values()) / max(len(seyrek), 1), 2)},
            'yogun': {'aralik': [gunler[0] if not yogun else
                                 min(yogun), max(yogun) if yogun else None],
                      'gun': len(yogun), 'kayit': sum(yogun.values()),
                      'gun_basina': round(
                          sum(yogun.values()) / max(len(yogun), 1), 2)},
        },
        'aylik': {a: {'kayit': aylik[a], 'gun': aylik_gun[a],
                      'gun_basina': round(aylik[a] / aylik_gun[a], 2)}
                  for a in sorted(aylik)},
        'gunluk': {g: per[g] for g in gunler},
        'kaynak_dagilimi': dict(kaynak.most_common()),
    }


def main():
    k = olc()
    print(f"gün {k['gun_sayisi']} | kayıt {k['kayit']} | "
          f"eksik gün {len(k['eksik_gun'])} | boş gün {len(k['bos_gun'])}")
    print(f"seyrek dönem {k['donem']['seyrek']['gun_basina']} haber/gün, "
          f"yoğun dönem {k['donem']['yogun']['gun_basina']} haber/gün")
    print(f"üstveri: {k['ustveri']} | kaynak ayrışmayan: "
          f"{sum(k['kaynak_ayrismayan'].values())}")
    if '--yaz' in sys.argv:
        with open(CIKTI, 'w', encoding='utf-8') as f:
            json.dump(k, f, ensure_ascii=False, indent=1, sort_keys=False)
        print(f'✅ {CIKTI}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
