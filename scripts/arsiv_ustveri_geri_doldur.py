#!/usr/bin/env python3
"""ARŞİV ÜSTVERİSİ GERİ DOLDURMA — kategori/puan/manşet, mevcut kayıtlara.

NEDEN: `save_summary_to_archive` üstveri satırını 2026-09-22'den İTİBAREN
yazıyor (bkz. CLAUDE.md, yıl sonu veri sözleşmesi). Daha eski arşiv kayıtları
yalnızca başlık + paragraf + kaynak taşıyor, dolayısıyla kategori kırılımı
yapılamıyordu.

KAPSAM — ölçüldü, ve sanıldığından DAR:
  skorlama_log.jsonl  18 Temmuz'dan beri kategori/puan taşır AMA başlığı
                      İNGİLİZCE'dir (kaynak makale başlığı).
  arşiv               başlıkları TÜRKÇE'dir.
  rapor_gecmis.json   tr_title ↔ title köprüsünü kurar ama YALNIZCA 31 gün.
Yani kesin (uydurmasız) geri doldurma yalnızca rapor_gecmis penceresinde
mümkündür. Ölçüm: o pencerede köprü %100 kuruluyor (525/525) ve arşiv
kayıtlarının %98'i eşleşiyor (514/520).

18 Temmuz – 22 Ağustos arası için köprü YOKTUR; o günler DOKUNULMAZ.

Kullanım:  python3 scripts/arsiv_ustveri_geri_doldur.py [--uygula]
Varsayılan KURU ÇALIŞMA. --uygula önce .yedek kopyası alır.
"""
import json
import os
import re
import shutil
import sys

ARSIV = 'data/haberler_arsiv.txt'
LOG = 'data/skorlama_log.jsonl'
GECMIS = 'data/rapor_gecmis.json'

_AY = {'JANUARY': 1, 'FEBRUARY': 2, 'MARCH': 3, 'APRIL': 4, 'MAY': 5,
       'JUNE': 6, 'JULY': 7, 'AUGUST': 8, 'SEPTEMBER': 9, 'OCTOBER': 10,
       'NOVEMBER': 11, 'DECEMBER': 12}


def _norm(s):
    return ' '.join((s or '').lower().split())


def eslesme_tablosu():
    """(gün, normalize_tr_başlık) → {kat, puan, manset}."""
    log_by = {}
    with open(LOG, encoding='utf-8') as f:
        for satir in f:
            satir = satir.strip()
            if not satir:
                continue
            try:
                r = json.loads(satir, strict=False)
            except ValueError:
                continue
            log_by.setdefault(_norm(r.get('baslik')), r)

    tablo = {}
    with open(GECMIS, encoding='utf-8') as f:
        for gun in json.load(f):
            for it in (gun.get('views') or []):
                r = log_by.get(_norm(it.get('title')))
                if not r:
                    continue
                tablo[(gun['date'], _norm(it.get('tr_title')))] = {
                    'kat': r.get('kat', ''),
                    'puan': r.get('toplam', 0),
                    'manset': r.get('yerlesim') == 'kritik3',
                }
    return tablo


def isle(uygula=False):
    tablo = eslesme_tablosu()
    if not tablo:
        print('⚠️  Eşleme tablosu boş — geri doldurma yapılmadı.')
        return 1

    with open(ARSIV, encoding='utf-8') as f:
        metin = f.read()

    parcalar = re.split(r'(📅 )', metin)
    cikti = []
    yazildi = eslesmedi = zaten = 0

    i = 0
    while i < len(parcalar):
        p = parcalar[i]
        if p != '📅 ':
            cikti.append(p)
            i += 1
            continue
        blok = parcalar[i + 1] if i + 1 < len(parcalar) else ''
        m = re.match(r'(\d+) ([A-ZÜÇŞĞİÖ]+) (\d{4})', blok)
        gun = (f"{m.group(3)}-{_AY.get(m.group(2), 0):02d}-{int(m.group(1)):02d}"
               if m else None)

        yeni, baslik = [], None
        for satir in blok.split('\n'):
            if satir.lstrip().startswith('»'):
                # Zaten üstverili kayıt — dokunma, mükerrer satır yazma.
                if satir.lstrip().startswith('» manset='):
                    zaten += 1
                    baslik = None
                yeni.append(satir)
                continue
            mb = re.match(r'\[\s*\d+\]\s+(.+)', satir)
            if mb:
                baslik = mb.group(1).strip()
                yeni.append(satir)
                continue
            # Kaynak satırından SONRA üstveriyi ekle.
            if baslik and satir.startswith('(XXXXXXX'):
                yeni.append(satir)
                rec = tablo.get((gun, _norm(baslik))) if gun else None
                if rec:
                    yeni.append(
                        f"» manset={'evet' if rec['manset'] else 'hayir'}"
                        f" | kategori={rec['kat'] or 'bilinmiyor'}"
                        f" | puan={rec['puan']}")
                    yazildi += 1
                else:
                    eslesmedi += 1
                baslik = None
                continue
            yeni.append(satir)

        cikti.append(p)
        cikti.append('\n'.join(yeni))
        i += 2

    sonuc = ''.join(cikti)
    print(f"üstveri yazıldı : {yazildi}")
    print(f"eşleşmeyen kayıt: {eslesmedi} (köprü dışı gün ya da başlık farkı)")
    print(f"zaten üstverili : {zaten}")

    if not uygula:
        print('\nKURU ÇALIŞMA — dosya değiştirilmedi. Uygulamak için --uygula')
        return 0
    # Yedek git'e GİRMEMELİ (9,5 MB). Uygulama sonrası elle silinir ya da
    # .gitignore'a alınır; burada yalnızca güvenlik ağı olarak bırakılır.
    shutil.copy2(ARSIV, ARSIV + '.yedek')
    with open(ARSIV, 'w', encoding='utf-8') as f:
        f.write(sonuc)
    print(f'\n✅ {ARSIV} güncellendi (yedek: {ARSIV}.yedek)')
    return 0


if __name__ == '__main__':
    sys.exit(isle('--uygula' in sys.argv))
