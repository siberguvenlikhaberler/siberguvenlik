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
  --gorunum ASİMETRİK BESLEME ölçümü: defter aynı manşete TÜRKÇE görünümle mi
            yoksa KAYNAK (İngilizce) görünümle mi sorulduğunda tekrar diyor.
            İlk seçim (`_derive_top3_by_score`) deftere `_kaynak_view` ile
            soruyordu; defterin kendi geçmişi ise yalnızca Türkçe.

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
        # YORUM SATIRLARI SAYILMAZ: katman kapıyı artık yükleme devretmiş
        # olsa da gerekçesini yorumda ANLATIYOR olabilir (yönetmendeki "takas
        # kapısı KRITIK3_HARIC_KATEGORILER'e bakar" notu gibi). Ham metin
        # taraması bunu kendi süzgeci sanıyordu.
        kod = '\n'.join(l for l in g.split('\n')
                         if not l.lstrip().startswith('#'))
        kendi = bool(re.search(r'KRITIK3_HARIC_KATEGORILER|not \(records', kod))
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
        yield g, defter, k3.get(g, []), rapor[g], sozluk
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
    for g, defter, mansetler, gunun, _sz in _defter_akisi():
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


def gorunum():
    """DEFTERE HANGİ GÖRÜNÜMLE SORULDUĞU SONUCU DEĞİŞTİRİR.

    `_derive_top3_by_score` defter kapısını `_kaynak_view` ile soruyor:
    tr_title/paragraph BOŞ, title İngilizce. Defterin geçmişi
    (`rapor_gecmis`) ise YALNIZCA Türkçe (tr_title + paragraph). Ortak özel
    adlar iki dilde de geçtiği için `ad:` kimlikleri tutuyor ama KONU
    ÖRTÜŞMESİ tutmuyor — defter kimlik + konu desteği istediği için eşleşme
    düşüyor. Yani kapı, boru hattının geri kalanından DAHA GEVŞEK çalışıyor.

    Ölçüm kaynak başlığı `skorlama_log.jsonl`dan alır (`yerlesim=kritik3`);
    kaynak gövde metni hiçbir yerde saklanmadığı için bu ALT SINIRDIR —
    üretimdeki `_kaynak_view` 2500 karakter İngilizce gövde de taşır, o da
    Türkçe geçmişle konu örtüşmesi üretmez.
    """
    kaynak = {}
    for satir in (VERI / 'skorlama_log.jsonl').read_text('utf-8').splitlines():
        try:
            r = json.loads(satir)
        except ValueError:
            continue
        if r.get('yerlesim') == 'kritik3' and r.get('baslik'):
            kaynak.setdefault(r['tarih'], []).append(r['baslik'])

    tr_tekrar = kv_tekrar = toplam = 0
    for g, defter, mansetler, gunun, _sz in _defter_akisi():
        rapor_gorunum = {(v.get('tr_title') or ''): v for v in gunun}
        basliklar = list(kaynak.get(g, []))
        if not basliklar:
            continue
        for i, v0 in enumerate(mansetler):
            if i >= len(basliklar):
                break
            v = rapor_gorunum.get(v0.get('tr_title') or '', v0)
            toplam += 1
            n_tr = defter.manset_gunu_sayisi(v)
            # KAYNAK GÖRÜNÜMÜ: üretimdeki `_kaynak_view` ile aynı şekil.
            n_kv = defter.manset_gunu_sayisi(
                {'tr_title': '', 'paragraph': '',
                 'title': basliklar[i], 'full_text': ''})
            tr_tekrar += n_tr >= 1
            kv_tekrar += n_kv >= 1
            if (n_tr >= 1) != (n_kv >= 1):
                print(f"  {g}  türkçe={n_tr} kaynak={n_kv}  "
                      f"{(v.get('tr_title') or '')[:48]}")
    print(f"\nkarşılaştırılan manşet: {toplam}  ·  defter tekrarı: "
          f"türkçe görünüm {tr_tekrar}  ·  kaynak görünüm {kv_tekrar}")


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


def _gun_tablosu(g, mansetler, gunun, sko):
    """O günün (view_fn, records, manset_idx) üçlüsü — TEK TEMSİL.

    ⚠️ Görünümler YALNIZCA `rapor_gecmis`ten alınır. `kritik3_gecmis` aynı
    haberi daha uzun saklıyor (paragraf 600 / full_text 1500 karakter) ve
    sayfa şablonu metni sahte eşleşme üretiyor; iki temsili karıştırmak
    2026-10-07'de 8 ve 5 gibi İKİ AYRI tekrar sayısı vermişti.
    """
    idx = {(v.get('tr_title') or ''): i for i, v in enumerate(gunun)}
    records = {}
    for i, v in enumerate(gunun):
        r = (sko.get(g) or {}).get(v.get('tr_title')) or {}
        records[i] = {'kat': r.get('kat') or 'nation_state_apt',
                      'toplam': r.get('toplam', 0)}
    manset_idx = [idx[v.get('tr_title') or ''] for v in mansetler
                  if (v.get('tr_title') or '') in idx]
    return (lambda k: gunun[k]), records, manset_idx


def _skorlama():
    sko = {}
    for line in (VERI / 'skorlama_log.jsonl').read_text('utf-8').splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        sko.setdefault(r['tarih'], {})[r['baslik']] = r
    return sko


def kabul():
    """KABUL ÖLÇÜTÜ 1-2 (KRITIK3_PLAN.md P5) — 31 GÜNÜN TAMAMI.

    `--yuklem` yalnızca TEKRAR manşetlere bakar; kabul ölçütü 2 ("KRİTİK 3
    hiçbir günde 3'ün altına düşmez") her günü ister, çünkü yüklem artık her
    seçimde koşuyor ve tekrarı olmayan bir günde de çeşitlilik ya da
    aynı-olay kapısı kapanabilir.

    YÖNTEM: her gün için yayımlanmış manşetler yüklemden geçirilir; reddedilen
    her manşet için `_kritik3_yedek_bul` ile gövdeden temiz yedek aranır ve
    bulunamazsa manşet YERİNDE BIRAKILIR (projenin değişmez kuralı). Günün
    sonunda manşet sayısı sayılır.

    SINIR: bu bir yeniden oynatmadır, LLM çağrısı yapılmaz. Yapı testi
    (`test_kapilar_tek_yuklemden_gecer`) manşete id sokabilen her katmanın bu
    yüklemden geçtiğini sabitlediği için, yüklemin REDDETTİĞİ bir haber artık
    hiçbir kapıdan giremez — ölçümün üretime bağı budur.
    """
    import main                                        # noqa: E402

    sko = _skorlama()
    sistem = main.HaberSistemi.__new__(main.HaberSistemi)
    gun = red = yedekli = yerinde = eksik = 0
    for g, defter, mansetler, gunun, sozluk in _defter_akisi():
        if not mansetler:
            continue
        gun += 1
        view_fn, records, manset_idx = _gun_tablosu(g, mansetler, gunun, sko)
        sistem._olay_defteri = defter
        sistem._olay_sozlugu = sozluk
        sistem._manset_yasak = set()
        kalan = list(manset_idx)
        havuz = [i for i in range(len(gunun)) if i not in manset_idx]
        for k in list(manset_idx):
            digerleri = [m for m in kalan if m != k]
            uygun, neden = sistem._manset_uygun_mu(
                k, digerleri, records, view_fn, ())
            if uygun:
                continue
            red += 1
            yedek = sistem._kritik3_yedek_bul(
                havuz, digerleri, records, view_fn, (), bant=False)
            if yedek is None:
                yerinde += 1
                print(f"  {g}  YERİNDE  {(gunun[k].get('tr_title') or '')[:44]}"
                      f"\n        {neden} · temiz yedek YOK")
                continue
            yedekli += 1
            kalan[kalan.index(k)] = yedek
            havuz.remove(yedek)
            print(f"  {g}  TAKAS    {(gunun[k].get('tr_title') or '')[:44]}"
                  f"\n        {neden}\n        yerine: "
                  f"{(gunun[yedek].get('tr_title') or '')[:44]}")
        if len(kalan) != len(manset_idx) or len(set(kalan)) != len(kalan):
            eksik += 1
            print(f"  ⚠️ {g}  manşet sayısı {len(manset_idx)} → {len(kalan)} "
                  f"(tekil {len(set(kalan))})")
    print(f"\ngün: {gun}  ·  yüklem REDDETTİ: {red}  ·  temiz yedekle takas: "
          f"{yedekli}  ·  yedek yok, yerinde: {yerinde}  ·  "
          f"manşet sayısı bozulan gün: {eksik}")

def yuklem():
    """Tekrar manşetleri YÜKLEME sorar: reddedilir mi, yerine aday var mı?

    Kabul ölçütü 1-2 (KRITIK3_PLAN.md P5): yüklem tekrar manşetlerin
    TAMAMINI reddetmeli ve kıtlık günü dışında her birinin yerine temiz aday
    bulunmalı. `records` skorlama logundan, görünümler rapor geçmişinden
    kurulur; `_manset_uygun_mu` ÜRETİM kodundan çağrılır.
    """
    import main                                        # noqa: E402

    sko = _skorlama()
    sistem = main.HaberSistemi.__new__(main.HaberSistemi)
    red = tutulan = yedeksiz = 0
    for g, defter, mansetler, gunun, _sz in _defter_akisi():
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
    ap.add_argument('--gorunum', action='store_true')
    ap.add_argument('--kabul', action='store_true')
    a = ap.parse_args()
    if not (a.matris or a.tekrar or a.kapi or a.yuklem or a.gorunum
            or a.kabul):
        a.matris = a.tekrar = a.kapi = a.yuklem = a.gorunum = True
    if a.matris:
        matris()
    if a.tekrar:
        print()
        tekrar()
    if a.kapi:
        print()
        kapi()
    if a.gorunum:
        print()
        gorunum()
    if a.kabul:
        print()
        kabul()
    if a.yuklem:
        print()
        yuklem()


if __name__ == '__main__':
    main()
