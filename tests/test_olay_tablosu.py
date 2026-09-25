"""BİRLEŞİK OLAY TABLOSU — alanların olay başına TEK satırda buluşması.

NEDEN VAR: alanlar yapılandırıldı ama BİRLEŞTİRİLMEMİŞTİ; hepsi arşiv
metninde `»` satırlarıydı ve `olaylar.json` yalnızca başlık/kategori/önem/
gün taşıyordu. "Çin bağlantılı aktörün finans sektöründe kaç kişiyi
etkileyen olayı" gibi çapraz sorgu her seferinde arşivi yeniden
ayrıştırmayı gerektiriyordu.

Testler üç şeyi sabitler: kimliğin `olay_kaydi` ile AYNI olması (iki dosya
aynı olaya aynı `id` ile atıf yapmalı), çok değerli alanların olay
boyunca BİRLEŞMESİ, ve kümülatif ölçek değerinin tekil değerle
KARIŞMAMASI.
"""
import importlib.util
import pathlib

_KOK = pathlib.Path(__file__).resolve().parent.parent / 'scripts'


def _yukle(ad):
    spec = importlib.util.spec_from_file_location(ad, _KOK / f'{ad}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


tab = _yukle('olay_tablosu')


def test_alan_ayristirma():
    a = tab._alanlar('sektor=finans,kamu | hedef=ABD | aktor=APT28')
    assert a == {'sektor': ['finans', 'kamu'], 'hedef': ['ABD'],
                 'aktor': ['APT28']}


def test_arsivde_tum_alanlar_toplanir():
    k = tab.arsivi_tara()
    assert len(k) > 4000
    assert sum(1 for x in k if x['sektor']) > 2500
    assert sum(1 for x in k if x['cve']) > 800
    assert sum(1 for x in k if x['kurban']) > 900
    assert sum(1 for x in k if x['olcek']) > 250
    assert sum(1 for x in k if x['kaynak']) > 4900


def test_kimlik_olay_kaydiyla_ayni():
    """İki dosya aynı olaya aynı id ile atıf yapmalı."""
    import json
    o = json.load(open('data/olaylar.json', encoding='utf-8'))['olaylar']
    t = json.load(open('data/olay_tablosu.json', encoding='utf-8'))['olaylar']
    assert len(o) == len(t)
    assert {x['id'] for x in o} == {x['id'] for x in t}


def test_cok_degerli_alanlar_olay_boyunca_birlesir():
    u = [{'anahtar': 'a', 'gun': '2026-02-13', 'blok': '2026-02-13',
          'baslik': 'Odido Telekom İhlalinde Hollanda Verilerinin Sızdırılması',
          'kat': 'veri_ihlali', 'onem': 42,
          'eksen': None, 'sektor': ['telekom'], 'hedef': ['Hollanda'],
          'aktor_ulke': [], 'aktor': ['ShinyHunters'], 'cve': [],
          'urun': [], 'istismar': None, 'kurban': ['Odido'],
          'olcek': {'etkilenen': {'deger': '6200000', 'kumulatif': False}},
          'kaynak': 'x.com', 'kaynak_tarih': None, 'erisim': 'AÇIK',
          'url': None},
         {'anahtar': 'b', 'gun': '2026-02-15', 'blok': '2026-02-15',
          'baslik': 'Odido Telekom İhlalinin Hollanda Müşterilerine '
                    'Duyurulması', 'kat': 'veri_ihlali', 'onem': 42, 'eksen': None, 'sektor': ['kamu'], 'hedef': [],
          'aktor_ulke': [], 'aktor': [], 'cve': ['CVE-2026-1731'],
          'urun': [], 'istismar': 'aktif', 'kurban': ['Odido'],
          'olcek': {}, 'kaynak': 'y.com', 'kaynak_tarih': None,
          'erisim': 'AÇIK', 'url': None}]
    for x in u:
        x['bel'] = tab.olay.belirtecler(x['baslik'])
    satirlar, _, _ = tab.tablo_kur(u)
    assert len(satirlar) == 1
    o = satirlar[0]
    assert o['sektor'] == ['telekom', 'kamu']
    assert o['kurban'] == ['Odido'], 'tekrar eden kurban çoğaltıldı'
    assert o['cve'] == ['CVE-2026-1731'] and o['istismar'] == 'aktif'
    assert o['olcek']['etkilenen'] == '6200000'
    assert o['gun_sayisi'] == 2 and o['kaynaklar'] == ['x.com', 'y.com']


def test_kumulatif_olcek_tekille_karismaz():
    """Yıllık rapor toplamı "en pahalı saldırı" sorgusuna girmemeli."""
    u = [{'olcek': {'zarar': {'deger': '442000000000', 'kumulatif': True}}},
         {'olcek': {'zarar': {'deger': '1180000USD', 'kumulatif': False}}}]
    assert tab._olcek_birlestir(u) == {'zarar': '1180000USD'}
    yalniz_kum = [{'olcek': {'zarar': {'deger': '442000000000',
                                       'kumulatif': True}}}]
    assert tab._olcek_birlestir(yalniz_kum) == {
        'zarar_kumulatif': '442000000000'}


def test_anlati_disi_isaretlenir():
    import json
    t = json.load(open('data/olay_tablosu.json', encoding='utf-8'))['olaylar']
    disi = [o for o in t if not o['anlati']]
    assert disi and all(o['kategori'] in tab.ANLATI_DISI for o in disi)
    assert all(o['anlati'] for o in t if o['kategori'] == 'veri_ihlali')


def test_csv_coklu_alanlari_noktali_virgulle_yazar():
    s = tab._csv_satir({'id': 'O-x', 'ilk_gun': '2026-01-01',
                        'son_gun': '2026-01-01', 'gun_sayisi': 1,
                        'kayit_sayisi': 1, 'kategori': 'veri_ihlali',
                        'anlati': True, 'onem': 42, 'eksen': [8, 17, 8, 8],
                        'baslik': 'X', 'kurban': ['A', 'B'],
                        'sektor': ['finans'], 'hedef_ulke': [],
                        'aktor_ulke': [], 'aktor': [], 'cve': [],
                        'urun': [], 'istismar': None,
                        'olcek': {'etkilenen': '100'}, 'kaynaklar': ['z.com']})
    assert s['kurban'] == 'A;B' and s['eksen'] == '8/17/8/8'
    assert s['anlati'] == 'evet' and s['etkilenen'] == '100'
    assert s['hedef_ulke'] == '' and s['istismar'] == ''


def test_uretim_hatti_turetilmis_veriyi_dogru_sirada_tazeler():
    """SIRA ŞART: olay kaydı kalıcı kimlikleri üretir, tablo onları
    DEVRALIR. Yalnızca tablo tazelenirse yeni olaylar her koşuda yeni
    kimlik alır — ölçüldü, 24 Eylül koşusunda tablo 4.429 olaya çıkarken
    olaylar.json 4.399'da kalmıştı."""
    import main
    src = open('main.py', encoding='utf-8').read()
    assert 'self._turetilmis_veriyi_tazele()' in src
    for ad in ('_kurban_topla', '_olay_kaydi_tazele', '_olay_tablosu_tazele'):
        assert hasattr(main.HaberSistemi, ad), ad
    govde = src.split('def _turetilmis_veriyi_tazele')[1].split('def ')[0]
    assert (govde.index('_olay_kaydi_tazele')
            < govde.index('_olay_tablosu_tazele')), 'sıra bozuk'


def test_olaylar_ve_tablo_ayni_kayit_sayisini_gorur():
    import json
    o = json.load(open('data/olaylar.json', encoding='utf-8'))
    t = json.load(open('data/olay_tablosu.json', encoding='utf-8'))
    assert o['kayit'] == t['kayit'] and o['olay'] == t['olay']


def test_hat_paydayi_ve_etiket_deposunu_da_tazeler():
    """ÖLÇÜLDÜ (25 Eylül): `arsiv_kapsam.json` 23 Eylül'de kalmış, 5.043
    kayıt gösteriyordu; arşivde 5.109 vardı. Bayat payda aylık
    normalizasyonu sessizce yanlış yapar. Önem deposu da toplanmazsa her
    yeni gün "etiketsiz" görünür (arşivde 5.106, depoda 5.043'tü)."""
    import main
    src = open('main.py', encoding='utf-8').read()
    govde = src.split('def _turetilmis_veriyi_tazele')[1].split('\n    @')[0]
    for ad in ('_kurban_topla', '_retro_topla', '_arsiv_kapsam_tazele',
               '_olay_kaydi_tazele', '_olay_tablosu_tazele'):
        assert ad in govde, ad
        assert hasattr(main.HaberSistemi, ad), ad
    assert (govde.index('_arsiv_kapsam_tazele')
            < govde.index('_olay_kaydi_tazele')), 'payda olaydan sonra'


def test_kapsam_kunyesi_arsivle_ayni_kayiti_gorur():
    import json
    k = json.load(open('data/arsiv_kapsam.json', encoding='utf-8'))
    t = json.load(open('data/olay_tablosu.json', encoding='utf-8'))
    assert k['kayit'] == t['kayit'], (k['kayit'], t['kayit'])


def test_olay_duzeyinde_de_fail_rolu_hedefi_ezer():
    """Aynı olayın iki kaydı ülkeyi farklı rolde görebilir (biri "Rus
    menşeli", öteki "Rusya'daki"); birleşim ikisini de yazınca ülke yine
    çift rolde çıkıyordu — ölçüldü, kayıt düzeyi düzeltildikten SONRA
    bile 22 olayda sürüyordu."""
    import json
    t = json.load(open('data/olay_tablosu.json', encoding='utf-8'))['olaylar']
    cift = [o['id'] for o in t if set(o['aktor_ulke']) & set(o['hedef_ulke'])]
    assert not cift, f'{len(cift)} olayda çift rol: {cift[:5]}'
