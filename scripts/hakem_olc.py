#!/usr/bin/env python3
"""MÜKERRER HAKEMİ ÖLÇÜMÜ — deterministik tanımın kaçırdıklarını kurtarıyor mu?

NEDEN VAR: `ayni_olay` YÜKSEK İSABETLİ ama ÇÖZÜNÜRLÜK SINIRI var. 7 Ekim'de
ölçüldü (bkz. CLAUDE.md "`ayni_olay` GEREKÇENİN ÖN EKİNE GÖRE YÖNLENDİRİR"):
FBI/Accenture ↔ FBI personel ihlali çifti AYNI ihlalin yeni gelişmesidir ama
`ayni_olay` onu AYIRIYOR, ve aynı sinyallere sahip bir BAŞKA çift (FBI/Accenture
↔ Rey'in Ürdün'de yakalanması) için ayırma DOĞRU. Hiçbir eşik ikisini
ayıramaz — karar LLM hakemine kalıyor. Bu betik hakemin o çiftlere NE DEDİĞİNİ
ölçer; o güne kadar hakem kararı hiç ölçülmemişti.

ÖLÇÜM ORTAMI: bu betik ÜRETİM YOLUNU çağırır (`main.HaberSistemi.
_mukerrer_llm_hakem`), yani prompt, parti boyutu, önbellek ve yanıt
ayrıştırması üretimdekiyle AYNIDIR. Kendi prompt'unu KURMAZ — kopya prompt
ölçümü üretimden ayırır.

API ANAHTARI ŞART: `OPENROUTER_API_KEY` (LLM_PROVIDER=openrouter ile) ya da
`GEMINI_API_KEY`. Anahtarsız ortamda çıkış kodu 2 ile DURUR — "ölçtüm" demez.
Geliştirme ortamında egress 403 veriyorsa (bkz. `pencere_olc.py` notu) ölçüm
BU ORTAMDAN YAPILAMAZ; anahtarlı bir koşuda çalıştırılmalıdır.

Kullanım:
  OPENROUTER_API_KEY=... LLM_PROVIDER=openrouter python scripts/hakem_olc.py
  GEMINI_API_KEY=... python scripts/hakem_olc.py --vaka "FBI ihlali"
  ... --hepsi            hakeme ULAŞAN her golden çiftini sorar
  ... --yaz <dosya>      kararları JSONL olarak yazar (varsayılan: yazmaz)
  ... --kuru              LLM'i ÇAĞIRMAZ, sahte yanıtla boru hattını sınar —
                          anahtarsız ortamda betiğin kendisini doğrulamak için.
                          Çıktı KARAR DEĞİLDİR ve öyle etiketlenir.

MALİYET: çiftler tek partide (en fazla `MUKERRER_HAKEM_BATCH`=12) gider;
varsayılan kapsamda bu 1-2 LLM çağrısıdır.
"""
import argparse
import json
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from src import olay_iliski as O                        # noqa: E402
from src.config import GEMINI_API_KEY, is_openrouter_active  # noqa: E402

GOLDEN = os.path.join(KOK, 'data', 'dedup_golden.json')
# Etiketlerden "aynı olay" sayılanlar — hakemin `ayni=True` demesi beklenir.
AYNI_ETIKET = {'AYNI_GELISME', 'YENI_GELISME'}


def _anahtar_var():
    return bool(is_openrouter_active() or GEMINI_API_KEY)


def _sozluk():
    views = []
    for p in ('data/rapor_gecmis.json', 'data/kritik3_gecmis.json'):
        tam = os.path.join(KOK, p)
        if not os.path.exists(tam):
            continue
        with open(tam, encoding='utf-8') as f:
            for r in json.load(f):
                views.extend(r.get('views') or [])
    return O.OlaySozlugu(views)


def _ciftler(vaka=None):
    with open(GOLDEN, encoding='utf-8') as f:
        return [c for c in json.load(f)['ciftler']
                if not vaka or vaka.lower() in c['ad'].lower()]


def _kapsam(ciftler, sozluk, hepsi):
    """Hakeme ULAŞAN çiftler.

    Boru hattı hakeme yalnızca `llm_adaylari`nın döndürdüklerini taşır; o da
    ortak aday anahtarı ve `ADAY_BENZERLIK_MIN` ister. Ulaşmayan bir çifti
    sormak ölçümü üretimden koparır.

    Varsayılan kapsam KARARSIZ çiftlerdir: `ayni_olay` ile etiket AYRIŞIYOR.
    `--hepsi` hakeme ulaşan her çifti sorar (kontrol grubu dahil: etiketi
    ILISKISIZ olanlarda hakem SAHTE BİRLEŞTİRME yapıyor mu).
    """
    secili = []
    for c in ciftler:
        a, b = c['a'], c['b']
        if not (O.aday_anahtarlari(a) & O.aday_anahtarlari(b)):
            c['_ulasmaz'] = 'ortak aday anahtarı yok'
            continue
        puan = O.aday_benzerligi(a, b, sozluk=sozluk)
        puan = puan[0] if isinstance(puan, tuple) else puan
        if puan < O.ADAY_BENZERLIK_MIN:
            c['_ulasmaz'] = f'benzerlik {puan:.2f} < {O.ADAY_BENZERLIK_MIN}'
            continue
        det = bool(O.ayni_olay(a, b, sozluk=sozluk, ayni_gun=c['ayni_gun']))
        beklenen = c['iliski'] in AYNI_ETIKET
        c['_det'] = det
        c['_beklenen'] = beklenen
        c['_benzerlik'] = puan
        if hepsi or det != beklenen:
            secili.append(c)
    return secili


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vaka', help='çift adında geçen metin (ör. "FBI ihlali")')
    ap.add_argument('--hepsi', action='store_true',
                    help='hakeme ulaşan TÜM golden çiftlerini sor')
    ap.add_argument('--yaz', help='kararları bu JSONL dosyasına yaz')
    ap.add_argument('--kuru', action='store_true',
                    help='LLM çağrısı YAPMADAN boru hattını sına (karar değil)')
    a = ap.parse_args()

    if not a.kuru and not _anahtar_var():
        print('⛔ API anahtarı YOK (OPENROUTER_API_KEY + LLM_PROVIDER=openrouter '
              'ya da GEMINI_API_KEY). Hakem kararı ÖLÇÜLEMEZ — betik hiçbir '
              'sonuç uydurmaz.', file=sys.stderr)
        return 2

    sozluk = _sozluk()
    tum = _ciftler(a.vaka)
    if not tum:
        print('⛔ Ölçülecek çift bulunamadı (--vaka süzgeci boş döndü).',
              file=sys.stderr)
        return 2
    secili = _kapsam(tum, sozluk, a.hepsi)
    print(f'📊 golden çift: {len(tum)}  ·  hakeme sorulacak: {len(secili)}')
    for c in tum:
        if c.get('_ulasmaz'):
            print(f'   ⏭️  hakeme ULAŞMAZ ({c["_ulasmaz"]}): {c["ad"][:52]}')
    if not secili:
        print('   kararsız çift yok — hakeme soracak bir şey yok.')
        return 0

    import main as uretim                                # noqa: E402
    sistem = uretim.HaberSistemi.__new__(uretim.HaberSistemi)
    if a.kuru:
        # SAHTE YANIT: her çifte `ayni=true` der. Amaç kararı ölçmek DEĞİL,
        # prompt kurulumunun, parti bölmenin, yanıt ayrıştırmanın ve
        # özet sayımının anahtarsız ortamda çalıştığını görmektir.
        import re as _re

        def _kuru_cagri(prompt, max_output_tokens=4096, label=''):
            # ÇİFT NUMARASI İSTEMDEN OKUNUR. İlk sürüm her parti için 1..n
            # üretiyordu; üretim numaraları GLOBAL olduğu için ikinci parti
            # yanıtsız kalıyordu (kuru koşuda 9 yanıtsız). Sahte yanıt da
            # üretimin sözleşmesine uymalı, yoksa kuru koşu olmayan bir hata
            # gösterir.
            nolar = [int(x) for x in _re.findall(r'--- ÇİFT (\d+) ---', prompt)]
            print(f'   🧪 KURU: {label} — {len(prompt)} karakterlik istem, '
                  f'{len(nolar)} çift {nolar} (LLM ÇAĞRILMADI)')
            return {'kararlar': [{'no': i, 'ayni': True, 'olay': 'KURU-SAHTE'}
                                 for i in nolar]}
        sistem._gemini_call_json = _kuru_cagri

    ciftler = []
    for i, c in enumerate(secili, 1):
        ortak = sorted(O.olay_kimlikleri(c['a'], sozluk)
                       & O.olay_kimlikleri(c['b'], sozluk))
        ipucu = (f'ortak={",".join(ortak[:3]) or "-"} '
                 f'konu={O._konu_ortusmesi(c["a"], c["b"]):.2f}')
        ciftler.append((i, c['a'], c['b'], ipucu))

    kararlar = sistem._mukerrer_llm_hakem(ciftler)
    if not kararlar:
        print('⚠️  Hakem yanıt vermedi — ölçüm YAPILAMADI (üretimde bu durum '
              '"mükerrer sayılmaz" demektir).', file=sys.stderr)
        return 1

    sayim = {'kurtardi': 0, 'kacirdi': 0, 'sahte': 0, 'dogru_ayirdi': 0,
             'yanitsiz': 0}
    satirlar = []
    for i, c in enumerate(secili, 1):
        if i not in kararlar:
            sayim['yanitsiz'] += 1
            print(f'   ⚠️  yanıtsız: {c["ad"][:52]}')
            continue
        ayni, olay = kararlar[i]
        beklenen, det = c['_beklenen'], c['_det']
        if beklenen and not det:
            sayim['kurtardi' if ayni else 'kacirdi'] += 1
        elif not beklenen:
            sayim['sahte' if ayni else 'dogru_ayirdi'] += 1
        print(f'\n  {c["ad"][:58]}')
        print(f'     etiket={c["iliski"]:<22} ayni_olay={det!s:<5} '
              f'hakem={ayni!s:<5} ({olay or "-"})')
        print(f'     benzerlik={c["_benzerlik"]:.2f}  '
              f'{"✅ hakem etiketle uyumlu" if ayni == beklenen else "❌ hakem etiketten ayrı"}')
        satirlar.append({'ad': c['ad'], 'etiket': c['iliski'],
                         'ayni_olay': det, 'hakem': ayni, 'olay': olay})

    if a.kuru:
        print('\n🧪 KURU KOŞU — aşağıdaki sayılar SAHTE yanıttan gelir, '
              'HAKEM KARARI DEĞİLDİR.')
    print(f'\nSONUÇ: deterministik kaçırdı → hakem KURTARDI {sayim["kurtardi"]}'
          f'  ·  hakem de kaçırdı {sayim["kacirdi"]}'
          f'  ·  ayrı olayı birleştirdi (SAHTE) {sayim["sahte"]}'
          f'  ·  doğru ayırdı {sayim["dogru_ayirdi"]}'
          f'  ·  yanıtsız {sayim["yanitsiz"]}')
    if a.yaz and satirlar:
        with open(a.yaz, 'w', encoding='utf-8') as f:
            for s in satirlar:
                f.write(json.dumps(s, ensure_ascii=False) + '\n')
        print(f'   📝 {len(satirlar)} karar yazıldı: {a.yaz}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
