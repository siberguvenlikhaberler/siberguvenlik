#!/usr/bin/env python3
"""13-16 Şubat 2026 arşiv bloklarını YAPILI biçime çevirir.

NEDEN VAR: bu dört gün arşive eski "GEMİNİ ÖZET RAPORU" biçiminde yazılmıştı —
paragraf + kaynak satırı vardı ama `[N] başlık` satırı YOKTU. Arşivi okuyan
her araç kaydı `[N]` ile saydığı için bu dört gün yapılı ayrıştırmada SIFIR
haber görünüyordu; retro etiket de alamamışlardı. Yıl sonu analizinde dört
günün görünmez kalması, 13 Şubat'ta başlayan yoğun dönemin ilk haftasını
eksik bırakırdı.

BAŞLIKLAR TÜRETİLMİŞTİR: o günlerin özgün manşetleri arşivde yok; başlıklar
kaydın KENDİ paragrafından çıkarılmıştır, dışarıdan bilgi eklenmemiştir.
Gün başlığı ("GEMİNİ ÖZET RAPORU") bilerek DEĞİŞTİRİLMEZ — kaydın hangi
dönemden geldiği okunabilir kalsın diye.

GÜNLÜK ÖZET paragrafı kayıt DEĞİLDİR: ardından kaynak satırı gelmez, bu
yüzden `[N]` almaz ve sayımlara girmez.

Kullanım: python3 scripts/arsiv_subat_yapilastir.py <baslik.tsv> [--kuru]
TSV sütunları: <gun>|<sira>  <baslik>  <kategori>  <onem>
"""
import re
import sys

ARSIV = 'data/haberler_arsiv.txt'
GUN_RE = re.compile(r'📅 (\d{1,2}) FEBRUARY 2026')
KAYNAK_RE = re.compile(r'^\(.*AÇIK\s*-.*\d{2}\.\d{2}\.\d{4}\)$')
BAS_RE = re.compile(r'^\[\s*\d+\]')
CETVEL = '─' * 57


def _tsv_oku(yol):
    kayit = {}
    for ham in open(yol, encoding='utf-8'):
        ham = ham.rstrip('\n')
        if not ham.strip():
            continue
        p = ham.split('\t')
        if len(p) != 4:
            sys.exit(f'bozuk satır: {ham[:60]}')
        kayit[p[0]] = (p[1].strip(), p[2].strip(), int(p[3]))
    return kayit


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    basliklar = _tsv_oku(sys.argv[1])
    kuru = '--kuru' in sys.argv

    satirlar = open(ARSIV, encoding='utf-8').read().split('\n')
    bas = [i for i, s in enumerate(satirlar)
           if GUN_RE.match(s) and 13 <= int(GUN_RE.match(s).group(1)) <= 16]
    if not bas:
        print('13-16 Şubat bloğu bulunamadı — iş yok.')
        return
    son = next(i for i, s in enumerate(satirlar)
               if i > bas[-1] and s.startswith('📅 17 FEBRUARY'))

    # Zaten yapılı mı? (fikir-değişmezlik)
    if any(BAS_RE.match(s) for s in satirlar[bas[0]:son]):
        print('bloklar zaten yapılı — değişiklik yok.')
        return

    yeni = list(satirlar[:bas[0]])
    for b in bas:
        e = min([x for x in bas + [son] if x > b])
        gun = str(int(GUN_RE.match(satirlar[b]).group(1)))
        n = 0
        tampon = []          # son görülen paragraf (henüz kaydı doğrulanmadı)
        for s in satirlar[b:e]:
            if KAYNAK_RE.match(s) and tampon:
                n += 1
                anahtar = f'{gun}|{n}'
                if anahtar not in basliklar:
                    sys.exit(f'başlık eksik: {anahtar}')
                baslik, kat, onem = basliklar[anahtar]
                yeni.append(f'[{n:2d}] {baslik}')
                yeni.append(CETVEL)
                yeni.extend(tampon)
                yeni.append(s)
                yeni.append(f'» sonradan | kategori={kat} | onem={onem} '
                            f'| rubrik=v1')
                tampon = []
                continue
            if s.strip() and not set(s.strip()) <= {'─', '='} \
                    and not s.startswith('GÜNLÜK ÖZET:') \
                    and not GUN_RE.match(s):
                tampon = [s]
                continue
            # paragraf olmayan satır: bekleyen tamponu olduğu gibi bırak
            if tampon:
                yeni.extend(tampon)
                tampon = []
            yeni.append(s)
        if tampon:
            yeni.extend(tampon)
        print(f'  {gun} Şubat: {n} kayıt yapılandırıldı')
    yeni.extend(satirlar[son:])

    if kuru:
        print(f'kuru koşu — satır {len(satirlar)} → {len(yeni)}')
        return
    open(ARSIV, 'w', encoding='utf-8').write('\n'.join(yeni))
    print(f'✅ {ARSIV} güncellendi ({len(satirlar)} → {len(yeni)} satır)')


if __name__ == '__main__':
    main()
