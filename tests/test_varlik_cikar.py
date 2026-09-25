"""VARLIK ÇIKARIMI — sektör / ülke rolü / aktör alanları.

NEDEN VAR: yıl sonu raporu sektör, ülke ve aktör kırılımı isteyecek; bu üç
eksen arşivde yalnızca serbest metinde vardı ve ham kelime sayımı yanıltıcı
(ölçüldü: "su " 1.114 kez geçiyor ama çoğu su altyapısı değil).

Bu bir YARGI değil ÇIKARIM olduğu için kurallara bağlandı — testler kuralların
iki bilinen tuzağa düşmediğini sabitler:
  1. Sektör TEK etiket seçilirse seçim sözlük sırasına düşer (ilk prototipte
     finans 961, enerji 45 çıkmıştı — dağılım değil, sıralama yanlılığı).
  2. Ülke tek alanda toplanırsa fail ile kurban karışır ve "ABD en çok
     saldıran ülke" gibi sonuçlar üretilir.
"""
import importlib.util
import pathlib

_yol = (pathlib.Path(__file__).resolve().parent.parent
        / 'scripts' / 'varlik_cikar.py')
_spec = importlib.util.spec_from_file_location('varlik_cikar', _yol)
varlik = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(varlik)


def test_sektor_cok_etiketlidir():
    s = varlik.sektorler('Eyalet hükümeti tarafından işletilen sağlık '
                         'sistemine fidye yazılımı saldırısı')
    assert 'kamu' in s and 'saglik' in s


def test_kisa_ve_cok_anlamli_dizi_sektor_uretmez():
    """"su" tek başına eşleşmemeli; yalnızca ayırt edici tamlama saymalı."""
    assert 'su' not in varlik.sektorler('Suudi Arabistan ve Rusya arasındaki '
                                        'görüşmede sunucu güvenliği ele alındı')
    assert 'su' in varlik.sektorler('Colorado su tesislerine yönelik saldırı')


def test_ulke_rolu_ayrisir():
    fail, hedef = varlik.ulkeler(
        'Çin bağlantılı bir grup ABD\'deki kritik altyapıyı hedef aldı')
    assert 'Çin' in fail and 'Çin' not in hedef
    assert 'ABD' in hedef and 'ABD' not in fail


def test_ipucu_yoksa_ulke_hedef_sayilir():
    """Arşiv ağırlıklı olarak kurban perspektifinden yazılmıştır."""
    fail, hedef = varlik.ulkeler('Hollanda merkezli Odido verileri sızdırdı')
    assert 'Hollanda' in hedef and not fail


def test_aktor_kod_adlari_yakalanir():
    a = varlik.aktorler('APT28 ve UNC2814 grupları ile Storm-1175 aktörü')
    assert {'APT28', 'UNC2814', 'Storm-1175'} <= set(a)


def test_aktor_esanlamlari_tek_ada_iner():
    assert varlik.aktorler('Cl0p fidye yazılımı çetesi') == ['Clop']


def test_satir_bicimi_bos_alan_yazmaz():
    s = varlik.satir_kur({'sektor': ['finans'], 'hedef': ['ABD'],
                          'aktor_ulke': [], 'aktor': []})
    assert s == '» varlik | sektor=finans | hedef=ABD\n'
    assert varlik.satir_kur({'sektor': [], 'hedef': [], 'aktor_ulke': [],
                             'aktor': []}) is None


def test_gercek_arsivde_fail_ulkeler_beklenen_dortlu():
    """Rol ayrımı bozulursa en çok saldıran ülkeler listesi anlamsızlaşır."""
    kayitlar = varlik.arsivi_tara()
    assert len(kayitlar) > 4000
    import collections
    c = collections.Counter(u for k in kayitlar
                            for u in varlik.cikar(k)['aktor_ulke'])
    ilk4 = {u for u, _ in c.most_common(4)}
    assert ilk4 == {'Çin', 'Rusya', 'İran', 'Kuzey Kore'}, c.most_common(6)
    # ABD arşivde en çok geçen ülke ama fail listesinde başı çekmemeli.
    assert c['ABD'] < c['Çin']


def test_uretim_hatti_varlik_satirini_yazar():
    """Hat yazmazsa alan yalnızca elle koşulan betikle dolar; unutulursa
    yılın son kayıtları sektörsüz kalır ve kırılım dönemsel olarak eksilir."""
    import main
    S = main.HaberSistemi
    satir = S._varlik_satiri(
        'Çin Bağlantılı Grubun ABD\'deki Hastane Sistemlerini Hedeflemesi', '')
    assert satir.startswith('» varlik | ')
    assert 'sektor=saglik' in satir
    assert 'aktor_ulke=Çin' in satir and 'hedef=ABD' in satir
    assert satir.endswith('\n')


def test_uretim_hatti_esleme_yoksa_satir_yazmaz():
    import main
    assert main.HaberSistemi._varlik_satiri('Sıradan bir başlık', '') is None


def test_hat_kurallari_kopyalamaz():
    """Kurallar kopyalansaydı iki sözlük zamanla ayrışırdı."""
    import main
    assert main.HaberSistemi._varlik_modulu().__file__.endswith(
        'scripts/varlik_cikar.py')
    src = open('main.py', encoding='utf-8').read()
    assert '_varlik_satiri(title, content)' in src


def test_fail_rolu_hedefi_ezer():
    """Bir ülke aynı kayıtta iki rolde görünemez.

    ÖLÇÜLDÜ (2026-09-25): 5.109 kaydın 108'inde ülke her iki listeye de
    giriyordu; örneklerde hedef ipucu neredeyse hep yanlıştı ("Tayvan'ın
    Çin Menşeli Saldırılara Maruz Kalması"nda Çin yalnızca faildir).
    """
    fail, hedef = varlik.ulkeler(
        'Japonya hükümeti, Çin menşeli yoğun siber saldırılara maruz '
        "kaldığını ve Çin'in bu saldırıları sürdürdüğünü açıklamıştır")
    assert 'Çin' in fail and 'Çin' not in hedef
    assert 'Japonya' in hedef and 'Japonya' not in fail


def test_gercek_arsivde_hicbir_ulke_cift_rolde_degil():
    kayitlar = varlik.arsivi_tara()
    cift = []
    for k in kayitlar:
        metin = k['baslik'] + ' ' + ' '.join(k['para'])
        f, h = varlik.ulkeler(metin)
        if set(f) & set(h):
            cift.append((k['gun'], sorted(set(f) & set(h))))
    assert not cift, f'{len(cift)} kayıtta çift rol: {cift[:5]}'


def test_ipucu_penceresi_komsu_ogeye_tasmaz():
    """40 karakterlik ham kuyruk komşu öğeye taşıyordu: "Japonya
    hükümeti, Çin menşeli saldırılara maruz kaldı" cümlesinde Japonya'nın
    kuyruğu "menşeli" ipucunu yakalayıp Japonya'yı FAİL sayıyordu."""
    fail, hedef = varlik.ulkeler(
        'Japonya hükümeti, Çin menşeli yoğun siber saldırılara maruz '
        'kaldığını açıklamıştır')
    assert fail == ['Çin'] and hedef == ['Japonya']
    assert varlik._kuyruk('Japonya hükümeti, Çin menşeli', 7) == ' hükümeti'
