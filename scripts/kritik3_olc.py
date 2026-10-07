#!/usr/bin/env python3
"""KRİTİK 3 GİRİŞ ÖLÇÜMÜ — hangi kapı tekrar manşet sokuyor? (yalnızca OKUR)

bkz. KRITIK3_PLAN.md. Üç ölçüm verir:

  --matris  KRİTİK 3'e id SOKABİLEN katmanların tek uygunluk yüklemini
            (`_manset_uygun_mu`) ya da ortak yedek bulucuyu çağırıp
            çağırmadığı — KAYNAK TARAMASI. Adım adım kablolamanın
            önce/sonra göstergesi budur.
  --tekrar  Son 31 günün YAYIMLANMIŞ manşetleri arasında, defterin "bu olay
            zaten manşet oldu" dediklerini listeler ve o gün gövdede
            defter-temiz aday olup olmadığını söyler (kabul ölçütü 1 ve 2).
  --kapi    Manşet karar izindeki her `giren` id için defter tekrar durumu —
            hangi katmanın kaç tekrar soktuğu.

Yüklemin kendisi aday/manşet bağlamı ister (records, view_fn); bu betik
rapor_gecmis görünümleriyle çalıştığı için yalnızca DEFTER kapısını
(G3) yeniden hesaplar — ölçülen arızaların tamamı o kapıdandır.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
from src import olay_iliski as oi                     # noqa: E402

VERI = KOK / 'data'

# KRİTİK 3'e id SOKABİLEN katmanlar (KRITIK3_PLAN.md, 1. bölüm).
GIRIS_KATMANLARI = (
    '_derive_top3_by_score', '_manset_llm_sec', '_dedup_kritik3_ici',
    '_dedup_kritik3_cross_day_llm', '_audit_kritik3_selection',
    '_yayin_yonetmeni', '_son_mukerrer_kapisi', '_manset_puan_tersinelik',
    '_kritik3_cesitlilik', '_kritik3_dominans_takasi',
)


def _fonksiyonlar():
    src = (KOK / 'main.py').read_text('utf-8')
    fns, cur, buf = {}, None, []
    for line in src.splitlines():
        m = re.match(r'    def (\w+)\(', line)
        if m:
            if cur:
                fns[cur] = '\n'.join(buf)
            cur, buf = m.group(1), [line]
        elif cur:
            buf.append(line)
    if cur:
        fns[cur] = '\n'.join(buf)
    return fns


def matris():
    fns = _fonksiyonlar()
    print('katman                            yüklem  yedek_bul  kendi süzgeci')
    eksik = []
    for f in GIRIS_KATMANLARI:
        g = fns.get(f, '')
        y = '_manset_uygun_mu' in g
        yb = '_kritik3_yedek_bul' in g
        kendi = bool(re.search(r'KRITIK3_HARIC_KATEGORILER|not \(records', g))
        print(f'  {f:<32}{"✓" if y else "·":^8}{"✓" if yb else "·":^11}'
              f'{"✓" if kendi else "·":^14}')
        if not (y or yb):
            eksik.append(f)
    print(f'\nyüklemden ya da yedek bulucudan GEÇMEYEN katman: {len(eksik)}'
          + (f' → {eksik}' if eksik else ''))


def _gunler():
    rapor = {d['date']: d.get('views', [])
             for d in json.loads((VERI / 'rapor_gecmis.json').read_text('utf-8'))}
    k3 = {d['date']: d.get('views', [])
          for d in json.loads((VERI / 'kritik3_gecmis.json').read_text('utf-8'))}
    return rapor, k3


def _defter_akisi():
    """Her gün için: (gun, o güne kadarki defter, o günün manşet görünümleri)."""
    rapor, k3 = _gunler()
    sozluk = oi.OlaySozlugu([v for g in rapor for v in rapor[g]])
    defter = oi.OlayDefteri(sozluk=sozluk)
    for g in sorted(rapor):
        bas = {w.get('tr_title') for w in k3.get(g, [])}
        yield g, defter, k3.get(g, []), rapor[g]
        defter.gunleri_isle(
            [(g, rapor[g], [v for v in rapor[g] if v.get('tr_title') in bas])])


def tekrar():
    toplam = bulasik = 0
    for g, defter, mansetler, gunun in _defter_akisi():
        bas = {w.get('tr_title') for w in mansetler}
        for v in mansetler:
            toplam += 1
            n = defter.manset_gunu_sayisi(v)
            if n < 1:
                continue
            bulasik += 1
            temiz = [x for x in gunun
                     if x.get('tr_title') not in bas
                     and defter.manset_gunu_sayisi(x) < 1]
            print(f"  {g}  tekrar={n}  {(v.get('tr_title') or '')[:52]}")
            print(f"        gövdede defter-temiz aday: {len(temiz)}"
                  + (f" (ör. {(temiz[0].get('tr_title') or '')[:44]})"
                     if temiz else '  ⚠️ YOK — manşet yerinde kalmalı'))
    print(f"\nyayımlanmış manşet: {toplam}  ·  defter tekrarı: {bulasik} "
          f"(%{100*bulasik/max(toplam,1):.1f})")


def kapi():
    den = {}
    for line in (VERI / 'kalite_denetim.jsonl').read_text('utf-8').splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        den[r['tarih']] = r
    say = Counter()
    for g, defter, mansetler, _ in _defter_akisi():
        kayit = den.get(g) or {}
        ms = (kayit.get('manset_sirasi') or {}).get('manset') or []
        for v in mansetler:
            if defter.manset_gunu_sayisi(v) < 1:
                continue
            t = (v.get('tr_title') or '')
            mid = next((m['id'] for m in ms
                        if (m.get('baslik') or '')[:30] == t[:30]), None)
            katman = 'ilk seçim'
            for e in (kayit.get('manset_karar_izi') or []):
                if mid is not None and e.get('giren') == mid:
                    katman = e['katman']
            say[katman] += 1
            print(f'  {g}  id={mid}  {katman:<34} {t[:46]}')
    print('\nkapı dağılımı:', dict(say.most_common()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--matris', action='store_true')
    ap.add_argument('--tekrar', action='store_true')
    ap.add_argument('--kapi', action='store_true')
    a = ap.parse_args()
    if not (a.matris or a.tekrar or a.kapi):
        a.matris = a.tekrar = a.kapi = True
    if a.matris:
        matris()
    if a.tekrar:
        print()
        tekrar()
    if a.kapi:
        print()
        kapi()


if __name__ == '__main__':
    main()
