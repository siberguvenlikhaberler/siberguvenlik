"""ÖLÇEK ÇIKARIMI — nicel etki alanı ve ölçülmüş ayrıştırma tuzakları.

NEDEN VAR: "yılın en büyük ihlalleri" şu an yalnızca `onem` ile
cevaplanıyor; `onem` YARGI, etkilenen kişi sayısı ÖLÇÜMDÜR.

Testler dört ÖLÇÜLMÜŞ hatayı sabitler:
  1. Aynı kalıp üç ayrı anlam taşıyor: "34 kişinin tutuklandığı" kurban
     değildir, "283 milyon dolarlık bütçe" zarar değildir.
  2. Cümle ayırıcı `[.!?]` "478.188 kişi" ifadesini ikiye bölüp alana 188
     yazdırıyordu (Türkçe binlik ayırıcı noktadır).
  3. Ayırıcı yorumu çarpana bağlıdır: "4.62 milyon" ondalıktır, "478.188"
     binliktir. Tek kural 4,62 milyonu 462 milyona şişiriyordu.
  4. Tür başına EN BÜYÜK değeri almak, gövdedeki ilgisiz büyük sayıyı
     seçiyordu (23andMe: manşet 47 milyon uzlaşma, gövdede 48 milyar
     şirket değeri).
"""
import importlib.util
import pathlib

_yol = (pathlib.Path(__file__).resolve().parent.parent
        / 'scripts' / 'olcek_cikar.py')
_spec = importlib.util.spec_from_file_location('olcek_cikar', _yol)
olc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(olc)


def _k(baslik, *para):
    return {'baslik': baslik, 'para': list(para)}


def test_tutuklama_etkilenen_sayilmaz():
    v = olc.cikar(_k('Suç Örgütü Operasyonu',
                     '34 kişinin İspanya\'da tutuklandığı bildirilmiştir.'))
    assert 'etkilenen' not in v
    assert olc.satir_kur(v) is None, 'tutuklama ölçek satırına girdi'


def test_butce_zarar_sayilmaz():
    v = olc.cikar(_k('Siber Savunma Programı',
                     'Program 283 milyon dolarlık bütçeyle desteklenmiştir.'))
    assert 'zarar' not in v and olc.satir_kur(v) is None


def test_binlik_nokta_bolunmez():
    v = olc.cikar(_k('Sağlık Kuruluşu İhlali',
                     '478.188 kişiyi etkileyen bir veri ihlali olmuştur.'))
    assert v['etkilenen'][0] == 478188


def test_carpanla_nokta_ondalik_olur():
    v = olc.cikar(_k('Bisiklet Kiralama İhlali',
                     'Sızıntıdan 4.62 milyon kişi etkilenmiştir.'))
    assert v['etkilenen'][0] == 4_620_000, v


def test_virgul_ondalik():
    v = olc.cikar(_k('Kripto Hırsızlığı',
                     'Cüzdanlardan 1,18 milyon dolar çalınmıştır.'))
    assert v['zarar'] == (1_180_000, 'USD', False)


def test_ilk_deger_kazanir():
    v = olc.cikar(_k('47 Milyon Dolarlık Uzlaşma Fonu Onaylanmıştır',
                     'Şirketin değeri 48 milyar dolar olan uzlaşma.'))
    assert v['ceza'][0] == 47_000_000


def test_para_birimi_kisi_turune_yazilmaz():
    v = olc.cikar(_k('İhlal', '42 milyon Euro ceza kesilmiş, '
                              'ihlalden 10 milyon kişi etkilenmiştir.'))
    assert v['ceza'] == (42_000_000, 'EUR', False)
    assert v['etkilenen'][0] == 10_000_000


def test_kumulatif_isaretlenir():
    """Yıllık rapor toplamı tekil olay değildir; silinmez, işaretlenir."""
    v = olc.cikar(_k('Yıllık Rapor',
                     'Siber suçlar küresel olarak 442 milyar dolar '
                     'zarara yol açmıştır.'))
    assert v['zarar'][2] is True
    assert 'kumulatif=zarar' in olc.satir_kur(v)


def test_gercek_arsivde_kapsam():
    kayitlar = olc.arsivi_tara()
    cikti = [olc.cikar(k) for k in kayitlar]
    yazilan = sum(1 for v in cikti if olc.satir_kur(v))
    assert len(kayitlar) > 4000
    assert 200 < yazilan < 600, yazilan
    enb = max(v['etkilenen'][0] for v in cikti if 'etkilenen' in v)
    assert enb < 1_000_000_000, f'inandırıcı olmayan değer: {enb}'


def test_uretim_hatti_olcek_satirini_yazar():
    import main
    s = main.HaberSistemi._olcek_satiri(
        'Sağlık Kuruluşunun Veri İhlali',
        '478.188 kişiyi etkileyen bir ihlal yaşanmıştır.')
    assert s == '» olcek | etkilenen=478188\n'
    assert main.HaberSistemi._olcek_satiri('Başlık', 'Hiçbir şey.') is None
