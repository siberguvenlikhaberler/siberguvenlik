"""TEKNİK ÇIKARIM — CVE / etkilenen ürün / aktif istismar.

NEDEN VAR: "yılın en çok istismar edilen açıkları" ve satıcı kırılımı şu an
yalnızca serbest metinden elle regex'le çıkıyor; iki analiz iki sonuç
veriyor. ÖLÇÜLDÜ: 956 kayıtta CVE, 874 tekil açık, 352 kayıtta birden çok.

Testler üç ÖLÇÜLMÜŞ tuzağı sabitler:
  1. Düz alt dizi araması: `sap` anahtarı "hesap" içinde eşleşiyor, SAP
     240 kayıtta çıkıyordu (gerçek: 37).
  2. Satıcı RAPORLAYAN taraf olabilir: "RedVDS'nin çökertilmesi —
     Microsoft ... açıklamıştır" kaydı `urun=Microsoft` alıyordu.
  3. `açı[ğk]` ipucu "açıklamıştır"/"dava açmıştır" ile eşleşip kolluk
     haberlerine teknik bağlam uyduruyordu.
"""
import importlib.util
import pathlib

_yol = (pathlib.Path(__file__).resolve().parent.parent
        / 'scripts' / 'teknik_cikar.py')
_spec = importlib.util.spec_from_file_location('teknik_cikar', _yol)
tek = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tek)


def _k(baslik, *para):
    return {'baslik': baslik, 'para': list(para)}


def test_cve_cok_etiketli_ve_tekil():
    v = tek.cikar(_k('CVE-2026-1731 Açığı',
                     'CVE-2026-2441 ve yine CVE-2026-1731 zincirlenmiştir.'))
    assert v['cve'] == ['CVE-2026-1731', 'CVE-2026-2441']


def test_sap_hesap_icinde_eslesmez():
    v = tek.cikar(_k('Banka Hesaplarına Yönelik Zafiyet',
                     'Saldırganlar hesap bilgilerini ele geçirmiştir.'))
    assert 'SAP' not in v['urun']
    assert 'SAP' in tek.cikar(_k('SAP NetWeaver Zafiyeti',
                                 'SAP sistemlerinde açığı yamaladı.'))['urun']


def test_raporlayan_satici_urun_sayilmaz():
    """Teknik ipucu ürünle AYNI CÜMLEDE olmalı."""
    v = tek.cikar(_k('RedVDS Platformunun Çökertilmesi',
                     'Microsoft, platformun çökertildiğini açıklamıştır.',
                     'Operasyonda bir zafiyet kullanılmamıştır.'))
    assert 'Microsoft' not in v['urun']


def test_aciklamak_teknik_ipucu_degildir():
    assert not tek._TEKNIK_IPUCU.search('Kurum konuyu açıklamıştır')
    assert not tek._TEKNIK_IPUCU.search('Savcılık dava açmıştır')
    assert tek._TEKNIK_IPUCU.search('Güvenlik açığı yamalanmıştır')


def test_aktif_istismar_potansiyelden_ayrilir():
    assert tek.cikar(_k('X', 'Açık aktif olarak istismar edilmektedir.')
                     )['istismar'] == 'aktif'
    assert tek.cikar(_k('X', 'Zafiyet istismar edilebilir niteliktedir.')
                     )['istismar'] is None


def test_teknik_baglam_yoksa_urun_yazilmaz():
    v = tek.cikar(_k('Apple Yeni Telefonunu Tanıttı',
                     'Apple ürün lansmanı yaptı.'))
    assert v['urun'] == [] and tek.satir_kur(v) is None


def test_baslik_govdeye_bitismez():
    """Başlık noktasızsa ilk paragrafla tek cümle sayılıyordu."""
    m = tek._metin(_k('Bir Platformun Çökertilmesi', 'Microsoft açığı buldu.'))
    assert 'Çökertilmesi. Microsoft' in m


def test_gercek_arsivde_kapsam_ve_dagilim():
    kayitlar = tek.arsivi_tara()
    cikti = [tek.cikar(k) for k in kayitlar]
    assert len(kayitlar) > 4000
    cve = sum(1 for v in cikti if v['cve'])
    assert 800 < cve < 1200, cve
    tekil = {c for v in cikti for c in v['cve']}
    assert len(tekil) > 700
    import collections
    u = collections.Counter(x for v in cikti for x in v['urun'])
    assert u['SAP'] < u['Microsoft'] / 3, u.most_common(5)


def test_uretim_hatti_teknik_satirini_yazar():
    import main
    s = main.HaberSistemi._teknik_satiri(
        'CVE-2026-1731 Açığı Cisco ASA Cihazlarında Aktif Olarak İstismar '
        'Edilmektedir', 'Zafiyet yamalanmıştır.')
    assert s.startswith('» teknik | cve=CVE-2026-1731')
    assert 'urun=Cisco' in s and 'istismar=aktif' in s
    assert main.HaberSistemi._teknik_satiri('Sıradan başlık', 'Hiçbir şey') is None


def test_hat_sozlugu_kopyalamaz():
    import main
    assert main.HaberSistemi._teknik_modulu().__file__.endswith(
        'scripts/teknik_cikar.py')
