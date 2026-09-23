#!/usr/bin/env python3
"""KURBAN ETİKETİ — hedef alınan kurumun ADI (tek seferlik LLM geçişi).

NEDEN KURALLA YAPILMADI — ÖLÇÜLDÜ (2026-09-23): arşiv başlıkları Başlık
Düzeninde yazılmıştır, yani HER kelime büyük harfle başlar ve büyük harf
özel ad sinyali TAŞIMAZ. Kurallı çıkarım denendi; başlıktan %2 kapsamla
"Veri", "Lüks Markalara Veri", "Hesap Kayıt Sistemine Yönelik" gibi yanlış
parçalar çıktı. Gövde normal yazımda olduğu için isabet artıyor ama kapsam
%1'e düşüyor ve raporlayan taraf (Resecurity, Mandiant) kurban sanılıyor.
Bu yüzden alan YARGIYA bağlandı: `» varlik`/`» teknik`/`» olcek`'in aksine
LLM etiketidir ve kaynağı satırda açıkça yazar.

ÖLÇEK: 4.399 olayın 1.748'i kurbanı adlandırılabilir kategoridedir
(veri_ihlali, stratejik_kurum_saldirisi, tedarik_zinciri, kolluk_operasyonu,
casus_yazilim, nation_state_apt). Kalanı zafiyet/ürün/politika haberidir ve
kurbanı yoktur; hedef kümesi bu yüzden kategoriye göre DARALTILIR.

KURAL: kurban = SALDIRIYA UĞRAYAN taraf. Raporlayan firma (CISA, Mandiant),
açığı yamalayan satıcı ve failin kendisi kurban DEĞİLDİR. Tedarik zinciri
olaylarında hem sağlayıcı hem etkilenen müşteri yazılabilir (virgülle).
Adlandırılmış kurban yoksa `-` yazılır — tahmin YÜRÜTÜLMEZ.

Yazılan satır:  » kurban | ad=Odido | kaynak=llm

Kullanım:
  python3 scripts/kurban_etiket.py durum
  python3 scripts/kurban_etiket.py parti 60          # etiketlenecek parti
  ... | python3 scripts/kurban_etiket.py yaz         # stdin: anahtar<TAB>ad
  python3 scripts/kurban_etiket.py uygula [--kuru]   # arşive yaz
"""
import importlib.util
import json
import os
import pathlib
import re
import sys

ARSIV = 'data/haberler_arsiv.txt'
DEPO = 'data/kurban_etiket.json'
_KURBAN_RE = re.compile(r'^»\s*kurban\b')

_spec = importlib.util.spec_from_file_location(
    'retro_etiket', pathlib.Path(__file__).resolve().parent / 'retro_etiket.py')
_retro = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_retro)
arsivi_tara = _retro.arsivi_tara

# Kurbanı ADLANDIRILABİLİR kategoriler. Bir Chrome yamasının ya da bir
# yasa tasarısının kurbanı yoktur; onları hedefe almak etiketleyiciyi
# binlerce kez "-" yazmaya zorlar ve gerçek kurbanlar arasında kaybolur.
HEDEF_KATEGORI = {
    'veri_ihlali', 'stratejik_kurum_saldirisi', 'tedarik_zinciri',
    'kolluk_operasyonu', 'casus_yazilim', 'nation_state_apt',
    'zafiyet_aktif_apt', 'phishing_sosyal_muhendislik',
}
_KAT_RE = re.compile(r'^» sonradan \| kategori=(\S+)')


def kategori(kayit):
    for m in kayit['meta']:
        g = _KAT_RE.match(m)
        if g:
            return g.group(1)
    return None


def hedefler(kayitlar):
    return [k for k in kayitlar if kategori(k) in HEDEF_KATEGORI]


def depo_yukle():
    try:
        with open(DEPO, encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


def depo_yaz(d):
    os.makedirs('data', exist_ok=True)
    with open(DEPO, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=1, sort_keys=True)


def temizle(ad):
    """Boş/`-`/`yok` → None. Fazla boşluk ve sondaki nokta atılır."""
    ad = (ad or '').strip().strip('.').strip()
    if not ad or ad.lower() in ('-', 'yok', 'none', 'bilinmiyor'):
        return None
    parca = [p.strip() for p in ad.split(',') if p.strip()]
    return ','.join(parca) or None


def durum():
    h = hedefler(arsivi_tara())
    d = depo_yukle()
    var = sum(1 for k in h if k['anahtar'] in d)
    adli = sum(1 for k in h if d.get(k['anahtar'], {}).get('ad'))
    print(f'hedef kayıt {len(h)} | etiketli {var} | eksik {len(h) - var}')
    print(f'adlandırılmış kurban {adli} '
          f'| kurbansız işaretlenen {var - adli}')
    eksik = [k for k in h if k['anahtar'] not in d]
    if eksik:
        print(f'sıradaki: {eksik[0]["anahtar"]} → {eksik[-1]["anahtar"]}')
    return 0


def parti(adet=60, karakter=300):
    h = hedefler(arsivi_tara())
    d = depo_yukle()
    eksik = [k for k in h if k['anahtar'] not in d][:adet]
    for k in eksik:
        para = ' '.join(k['para'])[:karakter].replace('\t', ' ')
        print(f'{k["anahtar"]}\t{k["baslik"]}\t{para}')
    return 0


def yaz():
    """stdin: `anahtar<TAB>ad`. `-` = adlandırılmış kurban yok."""
    gecerli = {k['anahtar'] for k in hedefler(arsivi_tara())}
    d = depo_yukle()
    once, yeni, hata = len(d), {}, []
    for no, satir in enumerate(sys.stdin, 1):
        if not satir.strip():
            continue
        p = satir.rstrip('\n').split('\t')
        if len(p) < 2:
            hata.append(f'{no}: alan eksik → {satir.strip()[:60]}')
            continue
        anahtar = p[0].strip()
        if anahtar not in gecerli:
            hata.append(f'{no}: hedef kümede yok → {anahtar}')
            continue
        yeni[anahtar] = {'ad': temizle(p[1])}
    if hata:
        for h in hata[:20]:
            print('HATA', h)
        print(f'{len(hata)} satır reddedildi — hiçbir şey yazılmadı.')
        return 1
    d.update(yeni)
    depo_yaz(d)
    print(f'{len(yeni)} etiket işlendi | depo {once} → {len(d)}')
    return 0


def satir_kur(v):
    return f'» kurban | ad={v["ad"]} | kaynak=llm\n' if v.get('ad') else None


def uygula(kuru=False):
    kayitlar = arsivi_tara()
    d = depo_yukle()
    with open(ARSIV, encoding='utf-8') as f:
        satirlar = f.readlines()
    ekle = guncelle = 0
    for k in sorted(kayitlar, key=lambda x: -x['satir_no']):
        v = d.get(k['anahtar'])
        if not v:
            continue
        yeni = satir_kur(v)
        if yeni is None:
            continue
        # Üstveri bloğu: kaynak satırından sonraki » satırları.
        i, son_meta = k['satir_no'] + 1, None
        mevcut = None
        while i < len(satirlar):
            s = satirlar[i]
            cip = s.rstrip('\n')
            if (_retro._BAS_RE.match(s) or _retro._GUN_RE.match(s)
                    or (set(cip) <= {'─', '='} and len(cip) >= 60)):
                break
            if s.startswith('»'):
                son_meta = i
                if _KURBAN_RE.match(s):
                    mevcut = i
            i += 1
        if mevcut is not None:
            if satirlar[mevcut] != yeni:
                satirlar[mevcut] = yeni
                guncelle += 1
        elif son_meta is not None:
            satirlar.insert(son_meta + 1, yeni)
            ekle += 1
    print(f'eklenecek: {ekle} | güncellenecek: {guncelle}')
    if kuru:
        print('(kuru koşu)')
        return 0
    with open(ARSIV, 'w', encoding='utf-8') as f:
        f.writelines(satirlar)
    print(f'✅ {ARSIV} güncellendi')
    return 0


def main():
    komut = sys.argv[1] if len(sys.argv) > 1 else 'durum'
    n = next((int(a) for a in sys.argv[2:] if a.isdigit()), None)
    if komut == 'durum':
        return durum()
    if komut == 'parti':
        return parti(n or 60)
    if komut == 'yaz':
        return yaz()
    if komut == 'uygula':
        return uygula('--kuru' in sys.argv)
    print(__doc__)
    return 1


if __name__ == '__main__':
    sys.exit(main())
