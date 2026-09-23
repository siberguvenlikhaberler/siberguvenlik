"""ARŞİV ARAMA — tematik sorgu başlıkla DEĞİL gövdeyle kurulur.

NEDEN VAR: "savaşta siberin kullanımı" gibi sorular kategori alanıyla
karşılanamaz ve başlık taraması yetmez. ÖLÇÜLDÜ (2026-09-23): İran/İsrail
örüntüsü başlıkta 184 kayıt, gövdeyle 755 kayıt eşleşiyor — aradaki 571
kaydın manşeti başka bir şeydir ama olay gövdede anlatılır.

Gövde taraması kapsamı artırırken gürültü de getirir; bu yüzden araç sayı
değil KANIT CÜMLESİ döndürür ve süzme gözle yapılır.
"""
import importlib.util
import pathlib

_yol = (pathlib.Path(__file__).resolve().parent.parent
        / 'scripts' / 'arsiv_ara.py')
_spec = importlib.util.spec_from_file_location('arsiv_ara', _yol)
ara = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ara)


def _k(baslik, *para, gun='2026-03-05', kat='nation_state_apt', onem=76):
    return {'gun': gun, 'baslik': baslik, 'para': list(para), 'kat': kat,
            'onem': onem, 'eksen': [17, 25, 17, 17], 'kaynak': 'x.com',
            'kaynak_tarih': '05.03.2026'}


def test_govdede_gecen_kayit_yakalanir():
    k = [_k('Rusya Bağlantılı Aktörlerin Yeni Arka Kapısı',
            'Arka kapı web kamerası aracılığıyla görüntü yakalayabilmektedir.')]
    b = ara.ara(k, [r'kamera'])
    assert len(b) == 1 and not b[0]['baslikta'], 'gövde eşleşmesi kaçtı'


def test_kaliplar_ve_ile_baglanir():
    k = [_k('İran Destekli Operasyon', 'Fidye yazılımı kullanılmıştır.')]
    assert ara.ara(k, [r'İran']) and ara.ara(k, [r'fidye'])
    assert not ara.ara(k, [r'İran', r'kamera']), 'VE koşulu VEYA gibi davrandı'


def test_kanit_eslesen_cumleyi_dondurur():
    """Sayı değil kanıt: gürültü ancak cümle görülerek elenir."""
    b = ara.ara([_k('Başlık', 'İlk cümle konu dışıdır.',
                    'İranlı aktörler gözetim kameralarını hedeflemiştir.')],
                [r'kamera'])
    assert 'gözetim kameralarını' in b[0]['kanit'][0]
    assert 'konu dışı' not in b[0]['kanit'][0]


def test_ustveri_satiri_govdeye_girmez():
    """`»` satırı PARAGRAF DEĞİLDİR; aksi halde üstveri arama sonucu üretir."""
    kayitlar = ara.arsivi_tara()
    assert len(kayitlar) > 4000
    assert not any(p.startswith('»') for k in kayitlar for p in k['para'])
    assert any(k['para'] for k in kayitlar), 'gövde hiç toplanmamış'


def test_gercek_arsivde_govde_taramasi_kapsami_artirir():
    kayitlar = ara.arsivi_tara()
    kalip = [ara.TEMALAR['iran_israil'][0]]
    b = ara.ara(kayitlar, kalip)
    bas = sum(1 for x in b if x['baslikta'])
    assert len(b) > bas * 2, (f'gövde taraması kapsamı artırmıyor: '
                              f'{len(b)} / başlıkta {bas}')


def test_bilinen_kinetik_olay_bulunur():
    """Kullanıcının adını koyduğu vaka: kamera sızıntısı + füze bağlamı."""
    kayitlar = ara.arsivi_tara()
    b = ara.ara(kayitlar, [r'kamera|CCTV', r'füze|İran|İsrail'])
    assert any('Gözetim Kamerasını' in x['baslik'] and 'Füze' in x['baslik']
               for x in b), 'bilinen vaka aramadan düştü'


def test_olaylastirma_siralamayi_onemle_kurar():
    kayitlar = ara.arsivi_tara()
    o = ara.olaylastir(ara.ara(kayitlar, [ara.TEMALAR['iran_israil'][0]]))
    onem = [x['onem'] or 0 for x in o]
    assert onem == sorted(onem, reverse=True), 'sıralama önemle kurulmamış'
    assert len(o) < len(kayitlar)
