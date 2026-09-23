#!/usr/bin/env python3
"""ÖLÇEK ÇIKARIMI — nicel etki (etkilenen / fidye / zarar / ceza) alanı.

NEDEN VAR: "yılın en büyük ihlalleri" sorusu şu an yalnızca `onem` ile
cevaplanabiliyor; `onem` bir YARGIDIR, kaç kişinin etkilendiği ise
ÖLÇÜMDÜR. Arşivde bu sayı var (ölçüldü 2026-09-23: 674 "dolar", 124
"kişi", 70 "kullanıcı", 57 "müşteri", 27 "kayıt" geçişi) ama yapılı alan
olmadığı için sıralamaya sokulamıyor.

EN BÜYÜK TUZAK — AYNI KALIP, ÜÇ AYRI ANLAM. Ölçülen örnekler:
  • "478.188 kişiyi etkileyen veri ihlali"        → etkilenen
  • "34 kişinin İspanya'da tutuklandığı"          → TUTUKLAMA, kurban değil
  • "283 milyon dolarlık bütçeyle desteklenmesi"  → BÜTÇE, zarar değil
  • "6,9 milyon doları aşan zarara yol açan"      → zarar
Sayıyı türe bakmadan toplamak "yılın en büyük ihlali" listesine tutuklama
operasyonlarını ve devlet bütçelerini sokardı. Bu yüzden TÜR İPUCU ŞARTTIR:
sayı, tür ipucuyla AYNI CÜMLEDE geçmiyorsa alan YAZILMAZ.

Yazılan satır (boş alan yazılmaz, tür başına EN BÜYÜK değer):
    » olcek | etkilenen=478188 | zarar=6900000USD | ceza=42000000EUR

Kullanım: python3 scripts/olcek_cikar.py [--yaz] [--ornek N] [--kuru]
"""
import collections
import importlib.util
import pathlib
import re
import sys

ARSIV = 'data/haberler_arsiv.txt'
_OLCEK_RE = re.compile(r'^»\s*olcek\b')

_spec = importlib.util.spec_from_file_location(
    'varlik_cikar', pathlib.Path(__file__).resolve().parent / 'varlik_cikar.py')
_varlik = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_varlik)
arsivi_tara = _varlik.arsivi_tara

# Cümle sınırı: RAKAM ARASINDAKİ nokta bölmez. Düz `[.!?]` ile bölmek
# "478.188 kişiyi etkileyen" ifadesini ikiye ayırıyor ve alana 188
# yazdırıyordu — Türkçe binlik ayırıcı noktadır.
_BOL_RE = re.compile(r'(?<!\d)[.!?]+(?!\d)')


def cumleler(metin):
    parca, son = [], 0
    for m in _BOL_RE.finditer(metin):
        parca.append(metin[son:m.end()])
        son = m.end()
    if metin[son:].strip():
        parca.append(metin[son:])
    return parca

CARPAN = {'bin': 1_000, 'milyon': 1_000_000, 'milyar': 1_000_000_000}
PARA = {'dolar': 'USD', 'usd': 'USD', 'euro': 'EUR', 'avro': 'EUR',
        'sterlin': 'GBP', 'pound': 'GBP', 'tl': 'TRY', 'lira': 'TRY'}
KISI = ('kişi', 'kullanıcı', 'müşteri', 'kayıt', 'hesap', 'çalışan',
        'hasta', 'öğrenci', 'vatandaş', 'abone')

_SAYI_RE = re.compile(
    r'(\d[\d\.\, ]*\d|\d)\s*(milyon|milyar|bin)?\s*'
    r'(dolar|usd|euro|avro|sterlin|pound|tl\b|lira|' + '|'.join(KISI) + r')',
    re.I)

# TÜR İPUCU — sayıyla aynı cümlede aranır. Sıra ÖNEMLİ: ilk eşleşen kazanır,
# bu yüzden daraltıcı türler (tutuklama, bütçe) önce gelir.
TUR = (
    ('tutuklama', re.compile(
        r'tutukla|gözaltı|yakalan|suçlan|iddianame|hakkında dava|'
        r'sanık|şüpheli|operasyonda ele geçir', re.I)),
    ('butce', re.compile(
        r'bütçe|ödenek|yatırım|fon ayır|hibe|destek program|'
        r'finansman sağla|kaynak ayır|pazar büyüklü|gelir elde', re.I)),
    ('ceza', re.compile(
        r'para cezası|idari ceza|ceza kesil|tazminat|uzlaşma|'
        r'ödemeye mahkum|yaptırım bedeli|fon(?:u|un)? onayla', re.I)),
    ('fidye', re.compile(
        r'fidye', re.I)),
    ('zarar', re.compile(
        r'zarar|kayıp|dolandırıcılıkla|çalın|çalmak|çaldı|ele geçiril'
        r'|maliyeti|mali kayıp', re.I)),
    ('etkilenen', re.compile(
        r'etkile|mağdur|veri(?:si|leri)? (?:sızdı|çalın|ifşa)|'
        r'ihlalde|ihlalinde|sızdırıl|ifşa ol|açığa çık|'
        r'bilgileri ele geçiril|kaydı(?:nın)? çalın', re.I)),
)

# KÜMÜLATİF İPUCU — sayı tek bir olayın değil, bir raporun/sektörün toplamı.
# Ölçüldü: en büyük üç `zarar` değeri (442 milyar, 240 milyar, 31 milyar)
# tekil olay değil, yıllık rapor toplamlarıdır. Silmek yerine İŞARETLENİR;
# "yılın en pahalı saldırısı" sorgusu bunları dışarıda bırakabilsin diye.
_KUMULATIF_RE = re.compile(
    r'küresel|dünya genelinde|toplam(?:da|ı|ında)?\b|yıllık rapor|'
    r'sektör genelinde|rapora göre|ortalama|yıl boyunca|'
    r'\d{4} yılında (?:kurbanlara|şirketlere|toplam)', re.I)

# Kişi birimleri YALNIZCA şu türlere, para birimleri yalnızca şu türlere
# yazılabilir. Karışırsa "42 milyon Euro etkilendi" gibi alan üretilirdi.
KISI_TURU = {'etkilenen', 'tutuklama'}
PARA_TURU = {'zarar', 'fidye', 'ceza', 'butce'}
# Rapora giren türler; tutuklama ve bütçe ölçek DEĞİL, bağlamdır.
ETKI_TURU = ('etkilenen', 'zarar', 'fidye', 'ceza')


def _sayi(ham, carpan):
    """Ayırıcı, ÇARPAN VARLIĞINA göre yorumlanır.

    Arşiv iki biçimi de kullanıyor (ölçüldü): çarpan varsa nokta ONDALIK
    ayırıcıdır ("4.62 milyon kişi", "17.7 milyar dolar"), çarpan yoksa
    BİNLİK ayırıcıdır ("478.188 kişi"). Tek kural uygulamak birini yüz kat
    şişiriyordu: 4.62 milyon → 462.000.000.
    """
    t = ham.replace(' ', '')
    if carpan:
        t = t.replace(',', '.')
        if t.count('.') > 1:            # "1.234.567 milyon" → binlik
            t = t.replace('.', '')
    else:
        t = t.replace('.', '')
        t = t.replace(',', '.')
    try:
        d = float(t)
    except ValueError:
        return None
    d *= CARPAN.get((carpan or '').lower(), 1)
    return int(round(d))


def cikar(kayit):
    """Tür başına METİNDE İLK geçen değer; tür ipucu yoksa sayı ATILIR.

    EN BÜYÜĞÜ almak yanlıştı: aynı kayıtta ilgisiz büyük sayılar bulunuyor.
    23andMe uzlaşma haberinde manşet 47 milyon dolarlık fondu ama gövdede
    geçen 48 milyar dolarlık şirket değeri alana yazılıyordu. Başlık metnin
    başında olduğu için ilk-gelen kuralı manşet sayısını seçer.
    """
    metin = kayit['baslik'] + '. ' + ' '.join(kayit['para'])
    bulunan = {}
    for cumle in cumleler(metin):
        # Cümlede BİRDEN ÇOK tür ipucu olabilir ("42 milyon Euro ceza
        # kesilmiş, 10 milyon kişi etkilenmiştir"). Cümleye tek tür atamak
        # ikinci sayıyı düşürüyordu; her sayı, BİRİMİNE UYAN ipuçlarından
        # kendisine EN YAKIN olanına bağlanır.
        ipuclari = [(ad, m.start()) for ad, r in TUR
                    for m in [r.search(cumle)] if m]
        if not ipuclari:
            continue
        kumulatif = bool(_KUMULATIF_RE.search(cumle))
        for m in _SAYI_RE.finditer(cumle):
            birim = m.group(3).lower().strip()
            para = PARA.get(birim)
            uygun = PARA_TURU if para else KISI_TURU
            aday = [(abs(yer - m.start()), ad)
                    for ad, yer in ipuclari if ad in uygun]
            if not aday:
                continue
            tur = min(aday)[1]
            deger = _sayi(m.group(1), m.group(2))
            if deger is None or deger <= 0:
                continue
            if tur not in bulunan:
                bulunan[tur] = (deger, para, kumulatif)
    return bulunan


def satir_kur(v):
    parca = []
    kum = []
    for tur in ETKI_TURU:
        if tur in v:
            deger, para, kumulatif = v[tur]
            parca.append(f'{tur}={deger}{para or ""}')
            if kumulatif:
                kum.append(tur)
    if not parca:
        return None
    if kum:
        parca.append('kumulatif=' + ','.join(kum))
    return '» olcek | ' + ' | '.join(parca) + '\n'


def main():
    kayitlar = arsivi_tara()
    cikti = [cikar(k) for k in kayitlar]
    n = len(kayitlar)
    yazilan = sum(1 for v in cikti if satir_kur(v))
    print(f'kayıt {n} | ölçek alanı yazılan %{100*yazilan//n} ({yazilan})')
    say = collections.Counter(t for v in cikti for t in v)
    kum = sum(1 for v in cikti if any(x[2] for x in v.values()))
    print('tür:', say.most_common(), f'| kümülatif işaretli kayıt: {kum}')
    print('(aşağıdaki en büyükler kümülatif OLMAYAN kayıtlardan)')
    for tur in ETKI_TURU:
        d = sorted((v[tur][0], k['gun'], k['baslik'])
                   for k, v in zip(kayitlar, cikti)
                   if tur in v and not v[tur][2])[-3:]
        print(f'  en büyük {tur}:',
              [(f'{x[0]:,}', x[1], x[2][:42]) for x in reversed(d)])

    ornek = next((int(a) for a in sys.argv[1:] if a.isdigit()), 0)
    if '--ornek' in sys.argv and ornek:
        print('\n-- örnek --')
        for k, v in [(k, v) for k, v in zip(kayitlar, cikti)
                     if satir_kur(v)][:ornek]:
            print(f'{k["gun"]} {k["baslik"][:58]}\n   {satir_kur(v)}', end='')

    if '--yaz' not in sys.argv:
        print('\n(yazmak için --yaz)')
        return 0

    satirlar = open(ARSIV, encoding='utf-8').readlines()
    ekle = guncelle = 0
    for k, v in sorted(zip(kayitlar, cikti), key=lambda p: -p[0]['satir_no']):
        yeni = satir_kur(v)
        if yeni is None:
            continue
        mevcut = next((no for no, m in zip(k['meta_no'], k['meta'])
                       if _OLCEK_RE.match(m)), None)
        if mevcut is not None:
            if satirlar[mevcut] != yeni:
                satirlar[mevcut] = yeni
                guncelle += 1
        elif k['meta_no']:
            satirlar.insert(max(k['meta_no']) + 1, yeni)
            ekle += 1
    print(f'\neklenecek: {ekle} | güncellenecek: {guncelle}')
    if '--kuru' in sys.argv:
        print('(kuru koşu)')
        return 0
    open(ARSIV, 'w', encoding='utf-8').writelines(satirlar)
    print(f'✅ {ARSIV} güncellendi')
    return 0


if __name__ == '__main__':
    sys.exit(main())
