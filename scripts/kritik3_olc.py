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
    """Yayımlanmış manşetlerden kaçı defter tekrarı?

    ⚠️ TEK TEMSİL ŞART: sorgu RAPOR GEÇMİŞİ görünümüyle yapılır, manşet
    geçmişi görünümüyle DEĞİL. ÖLÇÜLDÜ (2026-10-07): `kritik3_gecmis`
    görünümleri daha UZUN saklanıyor (paragraf 600 / full_text 1500 karakter)
    `rapor_gecmis` ise kırpık (500 / 400). Uzun görünümle sorulduğunda defter
    Florida Motorlu Araçlar ihlalini "Çin Bağlantılı Grubun Sogou Yazılımına
    Arka Kapı Yerleştirmesi" manşetiyle AYNI OLAY sayıyor (fazladan 1.100
    karakterlik sayfa şablonu metni yüzünden); kırpık görünümle eşleşme YOK.
    Aynı haberi iki temsille sormak 8 ve 5 gibi İKİ AYRI sayı veriyordu.
    """
    toplam = bulasik = 0
    for g, defter, mansetler, gunun in _defter_akisi():
        bas = {w.get('tr_title') for w in mansetler}
        rapor_gorunum = {(v.get('tr_title') or ''): v for v in gunun}
        for v0 in mansetler:
            v = rapor_gorunum.get(v0.get('tr_title') or '', v0)
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


def yuklem():
    """Tekrar manşetleri YÜKLEME sorar: reddedilir mi, yerine aday var mı?

    Kabul ölçütü 1-2 (KRITIK3_PLAN.md P5): yüklem tekrar manşetlerin
    TAMAMINI reddetmeli ve kıtlık günü dışında her birinin yerine temiz aday
    bulunmalı. `records` skorlama logundan, görünümler rapor geçmişinden
    kurulur; `_manset_uygun_mu` ÜRETİM kodundan çağrılır.
    """
    import main                                        # noqa: E402

    sko = {}
    for line in (VERI / 'skorlama_log.jsonl').read_text('utf-8').splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        sko.setdefault(r['tarih'], {})[r['baslik']] = r

    sistem = main.HaberSistemi.__new__(main.HaberSistemi)
    red = tutulan = yedeksiz = 0
    for g, defter, mansetler, gunun in _defter_akisi():
        tekrarli = [v for v in mansetler if defter.manset_gunu_sayisi(v) >= 1]
        if not tekrarli:
            continue
        # Görünüm ve kayıt tabloları: BAŞLIKLA eşleştir — kritik3_gecmis ve
        # rapor_gecmis AYRI dosyalardır, nesne kimliği tutmaz.
        idx = {(v.get('tr_title') or ''): i for i, v in enumerate(gunun)}
        view_fn = lambda k: gunun[k]                   # noqa: E731
        records = {}
        for i, v in enumerate(gunun):
            r = (sko.get(g) or {}).get(v.get('tr_title')) or {}
            records[i] = {'kat': r.get('kat') or 'nation_state_apt',
                          'toplam': r.get('toplam', 0)}
        sistem._olay_defteri = defter
        sistem._olay_sozlugu = None
        sistem._manset_yasak = set()
        manset_idx = [idx[v.get('tr_title') or ''] for v in mansetler
                      if (v.get('tr_title') or '') in idx]
        for v in tekrarli:
            k = idx.get(v.get('tr_title') or '')
            if k is None:
                continue
            digerleri = [m for m in manset_idx if m != k]
            uygun, neden = sistem._manset_uygun_mu(
                k, digerleri, records, view_fn, ())
            havuz = [i for i in range(len(gunun)) if i not in manset_idx]
            yedek = sistem._kritik3_yedek_bul(
                havuz, digerleri, records, view_fn, (), bant=False)
            if uygun:
                tutulan += 1
            else:
                red += 1
            if yedek is None:
                yedeksiz += 1
            print(f"  {g}  {'RED' if not uygun else 'KABUL'}  "
                  f"{(v.get('tr_title') or '')[:46]}\n        gerekçe: "
                  f"{neden or '-'}\n        yedek: "
                  + (f"{(gunun[yedek].get('tr_title') or '')[:46]}"
                     if yedek is not None else '⚠️ YOK (manşet yerinde kalır)'))
    print(f"\ntekrar manşet: {red + tutulan}  ·  yüklem REDDETTİ: {red}  ·  "
          f"yüklemden geçen: {tutulan}  ·  yedeksiz gün: {yedeksiz}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--matris', action='store_true')
    ap.add_argument('--tekrar', action='store_true')
    ap.add_argument('--kapi', action='store_true')
    ap.add_argument('--yuklem', action='store_true')
    a = ap.parse_args()
    if not (a.matris or a.tekrar or a.kapi or a.yuklem):
        a.matris = a.tekrar = a.kapi = a.yuklem = True
    if a.matris:
        matris()
    if a.tekrar:
        print()
        tekrar()
    if a.kapi:
        print()
        kapi()
    if a.yuklem:
        print()
        yuklem()


if __name__ == '__main__':
    main()
