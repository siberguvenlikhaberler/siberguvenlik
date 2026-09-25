#!/usr/bin/env python3
"""ARŞİVE GÜVENLİ YAZIM — tek geri döndürülemez dosyanın koruması.

NEDEN VAR: `data/haberler_arsiv.txt` yıl sonu analizinin OMURGASIDIR ve
yedeği yoktur; beş betik (`varlik/teknik/olcek/kurban/retro`) 10,6 MB'lık
dosyanın TAMAMINI yeniden yazıyor. Bu yazımlar düz `open(...,'w')` ile
yapılıyordu: GitHub Actions'ın 25 dakikalık sınırı ya da disk dolması
yazımın ORTASINDA işi öldürürse dosya yarım kalır ve o haliyle commit
edilir. `main.py` aynı dosya için tam bu gerekçeyle atomik yazım
kullanıyordu (`_atomic_write`); betikler kullanmıyordu.

İKİ KORUMA:
1. ATOMİK — geçici dosyaya yaz, fsync, `os.replace`. POSIX'te ya eski ya
   yeni içerik görünür, yarısı ASLA.
2. KAYIT SAYISI KAPISI — `[N] başlık` satırı sayısı azalıyorsa yazım
   REDDEDİLİR. Üstveri satırı eklemek/güncellemek kayıt sayısını asla
   düşürmez; düşüyorsa ayrıştırma hatası vardır ve dosya kurtarılamaz
   biçimde budanmak üzeredir.
"""
import os
import re

_BAS_RE = re.compile(r'^\[\s*\d+\]\s+\S')


def _kayit_say(satirlar):
    return sum(1 for s in satirlar if _BAS_RE.match(s))


def guvenli_yaz(yol, satirlar):
    """Kayıt sayısı düşmüyorsa arşivi ATOMİK yazar; döndürdüğü sayı yeni
    kayıt adedidir. Düşüyorsa hiçbir şey yazmaz ve RuntimeError yükseltir."""
    yeni = _kayit_say(satirlar)
    if os.path.exists(yol):
        with open(yol, encoding='utf-8') as f:
            eski = _kayit_say(f.readlines())
        if yeni < eski:
            raise RuntimeError(
                f'YAZIM REDDEDİLDİ: kayıt sayısı {eski} → {yeni} düşüyor. '
                f'{yol} budanmak üzereydi; dosyaya dokunulmadı.')
    d = os.path.dirname(yol) or '.'
    tmp = os.path.join(d, f'.{os.path.basename(yol)}.tmp')
    try:
        with open(tmp, 'w', encoding='utf-8') as f:
            f.writelines(satirlar)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, yol)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return yeni
