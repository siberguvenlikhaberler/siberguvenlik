#!/usr/bin/env python3
"""YIL SONU HAZIRLIĞI — analiz öncesi tek komut.

NEDEN VAR: analiz öncesi koşulması gereken dört adım var ve SIRASI önemli.
Varlık ve önem alanları ARŞİVE yazılır; kapsam künyesi ile olay kaydı ise
arşivden TÜRETİLİR. Türetilenler önce koşarsa eski arşivi ölçer ve rapor
sessizce eski sayılarla kurulur.

Hepsi fikir-değişmezdir (idempotent): iki kez koşmak tek koşmakla aynıdır,
bu yüzden ne zaman koşulduğu önemli değildir — analizden hemen önce bir kez
yeter, yeni kayıtları da kapsar.

Kullanım: python3 scripts/yilsonu_hazirla.py [--yaz]
`--yaz` verilmezse hiçbir dosyaya dokunulmaz, yalnızca durum raporlanır.
"""
import subprocess
import sys

YAZ = '--yaz' in sys.argv

# (başlık, komut, yalnızca-okuma-mı)
ADIMLAR = [
    ('1/8  Önem etiketi kapsamı (yazmaz — eksik varsa raporlar)',
     ['python3', 'scripts/retro_etiket.py', 'durum'], True),
    ('2/8  Ölçek kayması denetimi (kafes dışı etiket = kayma)',
     ['python3', 'scripts/retro_etiket.py', 'denetim'], True),
    ('3/8  Varlık alanı → arşive yazılır',
     ['python3', 'scripts/varlik_cikar.py'] + (['--yaz'] if YAZ else []),
     False),
    ('4/8  Teknik alan → arşive yazılır (CVE / ürün / aktif istismar)',
     ['python3', 'scripts/teknik_cikar.py'] + (['--yaz'] if YAZ else []),
     False),
    ('5/8  Ölçek alanı → arşive yazılır (etkilenen / fidye / zarar / ceza)',
     ['python3', 'scripts/olcek_cikar.py'] + (['--yaz'] if YAZ else []),
     False),
    ('6/8  Kapsam künyesi → data/arsiv_kapsam.json (arşivden TÜRETİLİR)',
     ['python3', 'scripts/arsiv_kapsam.py'] + (['--yaz'] if YAZ else []),
     False),
    ('7/8  Olay kaydı → data/olaylar.json (arşivden TÜRETİLİR)',
     ['python3', 'scripts/olay_kaydi.py'] + (['--yaz'] if YAZ else []),
     False),
    ('8/8  Birleşik olay tablosu → data/olay_tablosu.json + .csv',
     ['python3', 'scripts/olay_tablosu.py'] + (['--yaz'] if YAZ else []),
     False),
]


def main():
    if not YAZ:
        print('⚠️  KURU KOŞU — hiçbir dosyaya yazılmayacak. '
              'Yazmak için: --yaz\n')
    uyari = []
    for baslik, komut, sadece_okuma in ADIMLAR:
        print(f'── {baslik}')
        p = subprocess.run(komut, capture_output=True, text=True)
        print((p.stdout or '').rstrip())
        if p.stderr.strip():
            print(p.stderr.rstrip())
        # `denetim` kafes dışı etiket bulursa 1 döner; bu bir HATA değil,
        # rapor öncesi kapatılması gereken bir bulgudur.
        if p.returncode != 0:
            uyari.append(baslik)
        print()
    if uyari:
        print('⚠️  KAPATILMASI GEREKEN BULGU:')
        for u in uyari:
            print(f'   • {u}')
        print('   (bkz. RETRO_RUBRIK.md — kafes dışı etiket ölçek kaymasıdır)')
        return 1
    print('✅ Hazırlık tamam. Çapraz sorgular data/olay_tablosu.json '
          'üzerinden yapılır; rapor ÖNCE data/arsiv_kapsam.json okumalı: '
          'ham aylık toplam "olay sayısı" değil, "o ay kaç haber '
          'çekilebildiği"dir.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
