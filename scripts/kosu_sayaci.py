#!/usr/bin/env python3
"""GÜNLÜK TAM KOŞU SINIRI (kullanıcı kararı, 2026-11-07).

6 Kasım'da üç slot raporu bitirip süre sınırına takıldı; kaydedilmeyen her
koşu bütün LLM hattını sıfırdan ödedi (dört tam koşu, normal günün ~4 katı).
Günde 6 tetik slotu var (cron-job.org 3 + GitHub schedule 3), en kötü durumda
maliyet 6 katına çıkabilirdi. Kural: bir günde en fazla TAM_KOSU_SINIRI tam
(ücretli) koşu. Bugünün başarılı raporu varsa main.py zaten erken çıkar —
o koşu SAYILMAZ.

Sayaç ANA İŞTEN ÖNCE push edilir: zaman aşımında iş akışının commit adımı hiç
koşmaz, sona yazılan sayaç kaybolurdu. Manuel `workflow_dispatch` bu sınıra
tabi değildir (bilinçli eylem; Kontrol 1 ile aynı politika).

Çıkış: 0 = devam (sayaç artırıldıysa `--artirildi` dosyası yazılır),
       1 = sınır doldu (iş akışı başarısız olur ve issue açılır).
"""
import json
import os
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

TAM_KOSU_SINIRI = int(os.getenv('TAM_KOSU_SINIRI') or 2)
SAYAC = KOK / 'data' / 'tam_kosu_sayaci.json'


def karar(bugun, rapor_basarili, sayac, sinir=TAM_KOSU_SINIRI):
    """(devam_mi, yeni_sayac_ya_da_None, mesaj) — saf fonksiyon."""
    if rapor_basarili:
        return True, None, 'bugünün başarılı raporu var — koşu sayılmaz'
    adet = sayac.get('adet', 0) if sayac.get('tarih') == bugun else 0
    if adet >= sinir:
        return False, None, (f'bugün {adet} tam koşu yapıldı (sınır {sinir}) '
                             f'— LLM maliyeti için yeni koşu YAPILMIYOR')
    return True, {'tarih': bugun, 'adet': adet + 1}, \
        f'tam koşu {adet + 1}/{sinir}'


def main():
    from main import _now_tr, _rapor_basarili
    bugun = _now_tr().strftime('%Y-%m-%d')
    rapor = KOK / 'docs' / 'raporlar' / f'{bugun}.html'
    basarili = False
    if rapor.exists():
        try:
            basarili = _rapor_basarili(rapor.read_text(encoding='utf-8'))
        except Exception:
            basarili = False
    try:
        sayac = json.loads(SAYAC.read_text(encoding='utf-8'))
    except Exception:
        sayac = {}
    devam, yeni, mesaj = karar(bugun, basarili, sayac)
    print(f"🧮 Günlük tam koşu sınırı: {mesaj}")
    if not devam:
        print(f"::error title=Günlük tam koşu sınırı doldu::{mesaj}")
        return 1
    if yeni is not None:
        SAYAC.write_text(json.dumps(yeni, ensure_ascii=False) + '\n',
                         encoding='utf-8')
        (KOK / '.sayac_artirildi').write_text('1')
    return 0


if __name__ == '__main__':
    sys.exit(main())
