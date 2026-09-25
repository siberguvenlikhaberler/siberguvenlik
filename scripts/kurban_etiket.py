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

# Arşiv yazımı KOPYALANMAZ — tek kapı: atomik yazım + kayıt sayısı
# kapısı (bkz. scripts/arsiv_yaz.py).
_yaz_spec = importlib.util.spec_from_file_location(
    'arsiv_yaz', pathlib.Path(__file__).resolve().parent / 'arsiv_yaz.py')
_arsiv_yaz = importlib.util.module_from_spec(_yaz_spec)
_yaz_spec.loader.exec_module(_arsiv_yaz)

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


# İNGİLİZCE AD → TÜRKÇE. ÖLÇÜLDÜ (2026-09-24): hattın ilk gününde LLM
# adları İngilizce döndürdü ("Ukraine", "UAE", "European Union") oysa
# geriye dönük 1.036 etiketin tamamı Türkçedir. Eşlemesiz bırakmak aynı
# kurumu iki ayrı kurban olarak saydırırdı.
ESANLAM = {
    'ukraine': 'Ukrayna', 'russia': 'Rusya', 'china': 'Çin', 'iran': 'İran',
    'israel': 'İsrail', 'united states': 'ABD', 'usa': 'ABD', 'us': 'ABD',
    'uae': 'BAE', 'united arab emirates': 'BAE',
    'saudi arabia': 'Suudi Arabistan', 'european union': 'Avrupa Birliği',
    'eu': 'Avrupa Birliği', 'united kingdom': 'Birleşik Krallık',
    'uk': 'Birleşik Krallık', 'germany': 'Almanya', 'france': 'Fransa',
    'netherlands': 'Hollanda', 'japan': 'Japonya', 'india': 'Hindistan',
    'south korea': 'Güney Kore', 'north korea': 'Kuzey Kore',
    'türkiye': 'Türkiye', 'turkey': 'Türkiye', 'poland': 'Polonya',
    'spain': 'İspanya', 'italy': 'İtalya', 'canada': 'Kanada',
    'australia': 'Avustralya', 'brazil': 'Brezilya', 'taiwan': 'Tayvan',
}

# JENERİK BAŞ AD — kurum adı DEĞİL, bir kitle tanımı. Kural gereği `-`
# yazılmalıydı; hattın ilk gününde "Developers", "Windows users",
# "Online retailers", "US Federal Agencies", "Government contractor" gibi
# 7 kayıtta kurban alanına girmişti. Son sözcüğe bakılır: mevcut 1.036
# etiketin HİÇBİRİ bu sözcüklerle bitmiyor (ölçüldü), yani kural geçmişi
# bozmaz. "ABD Sosyal Güvenlik İdaresi" gibi adlar korunur.
JENERIK_SON = {
    'users', 'user', 'developers', 'developer', 'customers', 'customer',
    'retailers', 'retailer', 'agencies', 'agency', 'institutions',
    'institution', 'contractor', 'contractors', 'employees', 'employee',
    'citizens', 'organizations', 'organisations', 'companies', 'firms',
    'banks', 'hospitals', 'schools', 'victims', 'clients', 'residents',
    'subscribers',
    # 'systems'/'servers'/'accounts' BİLEREK YOK: gerçek şirket adlarında
    # geçiyor ("Unlimited Technology Systems") ve kuralı geçmişe uygulamak
    # o kaydı düşürüyordu.
    'kullanıcıları', 'kullanıcılar', 'müşterileri', 'müşteriler',
    'geliştiricileri', 'geliştiriciler', 'kurumları', 'şirketleri',
    'vatandaşları', 'çalışanları', 'kuruluşları', 'işletmeleri',
}


def _tek_ad(ad):
    """Tek bir kurban adını normalize eder; jenerik tanım → None."""
    ad = ad.strip().strip('.').strip()
    if not ad:
        return None
    if ad.lower() in ESANLAM:
        return ESANLAM[ad.lower()]
    # Jenerik baş ad sonda DEĞİL de ortada olabilir ("Android users in
    # Europe and Canada" → kurban Android kullanıcılarıdır, adlandırılmış
    # bir kurum yoktur). Bu yüzden HER sözcüğe bakılır; mevcut 1.036
    # etiketin hiçbirinde bu sözcükler geçmiyor (ölçüldü).
    if {w.lower().strip(',.') for w in ad.split()} & JENERIK_SON:
        return None
    return ad


def temizle(ad):
    """Boş/`-`/`yok`/jenerik → None. İngilizce ülke adı Türkçeleşir."""
    ad = (ad or '').strip().strip('.').strip()
    if not ad or ad.lower() in ('-', 'yok', 'none', 'bilinmiyor', 'n/a'):
        return None
    parca, gorulen = [], set()
    for p in ad.split(','):
        t = _tek_ad(p)
        if t and t not in gorulen:
            gorulen.add(t)
            parca.append(t)
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
    _arsiv_yaz.guvenli_yaz(ARSIV, satirlar)
    print(f'✅ {ARSIV} güncellendi')
    return 0


def topla():
    """Arşive ÜRETİM HATTI tarafından yazılmış `» kurban` satırlarını depoya
    geri okur. Depoda ZATEN olan anahtara dokunulmaz — arşiv, deponun
    üzerine yazamaz; tek seferlik geçişin kararları korunur.
    """
    d = depo_yukle()
    once, eklenen = len(d), 0
    for k in hedefler(arsivi_tara()):
        if k['anahtar'] in d:
            continue
        ad = None
        for m in k['meta']:
            g = re.match(r'^»\s*kurban \| ad=([^|]+)', m)
            if g:
                ad = temizle(g.group(1))
        d[k['anahtar']] = {'ad': ad}
        eklenen += 1
    depo_yaz(d)
    print(f'{eklenen} kayıt depoya alındı | depo {once} → {len(d)}')
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
    if komut == 'topla':
        return topla()
    if komut == 'uygula':
        return uygula('--kuru' in sys.argv)
    print(__doc__)
    return 1


if __name__ == '__main__':
    sys.exit(main())
