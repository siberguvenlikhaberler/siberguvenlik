"""OLAY KAYDI — kayıt → olay tekilleştirmesi ve sıralama anahtarı.

NEDEN VAR: arşiv "haber kaydı" tutar, yıl sonu raporu "olay" sayar. Aynı olay
ardışık günlerde yeniden raporlanır ve 10 günde aynı güne ait birden çok blok
vardır (784 kayıt). Tekilleştirilmeden yapılan sayım bu tekrarları olay sanar.

Sıralama anahtarı da ölçüldü: rubrik 25 değerlik bir kafes ürettiği için 84+
bandında ~300 olay berabere kalıyor; eşitlik tarihe düşerse liste, yüksek
puanlı olayı çok olan aya kayıyor.
"""
import importlib.util
import pathlib

_yol = (pathlib.Path(__file__).resolve().parent.parent
        / 'scripts' / 'olay_kaydi.py')
_spec = importlib.util.spec_from_file_location('olay_kaydi', _yol)
olay = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(olay)


def test_belirtecler_durak_sozcukleri_atar():
    b = olay.belirtecler('Yeni Siber Tehdit Aktörünün Odido Sistemlerini '
                         'Hedeflemesi')
    assert 'Odido' in b
    for d in ('Yeni', 'Siber', 'Tehdit', 'Hedeflemesi'):
        assert d not in b


def test_belirtecler_cve_yakalar():
    b = olay.belirtecler('CVE-2026-1731 Açığının İstismar Edilmesi')
    assert 'CVE-2026-1731' in b


def test_ayni_olayin_farkli_gunleri_birlesir():
    k = [
        {'gun': '2026-02-13', 'baslik': 'Odido Telekom İhlalinde Hollanda '
         'Müşterilerinin Verilerinin Sızdırılması', 'kat': 'veri_ihlali',
         'onem': 42, 'eksen': None},
        {'gun': '2026-02-15', 'baslik': 'Odido Telekom İhlalinin Hollanda '
         'Müşterilerine Duyurulması', 'kat': 'veri_ihlali', 'onem': 42,
         'eksen': None},
    ]
    for x in k:
        x['bel'] = olay.belirtecler(x['baslik'])
    kume, _ = olay.kumele(k)
    assert len(kume) == 1, 'aynı olayın iki günü ayrı kaldı'


def test_farkli_olaylar_birlesmez():
    k = [
        {'gun': '2026-02-13', 'baslik': 'Odido Müşteri Verilerinin '
         'Sızdırılması', 'kat': 'veri_ihlali', 'onem': 42, 'eksen': None},
        {'gun': '2026-02-14', 'baslik': 'Lazarus Grubunun Graphalgo '
         'Kampanyası', 'kat': 'nation_state_apt', 'onem': 67, 'eksen': None},
    ]
    for x in k:
        x['bel'] = olay.belirtecler(x['baslik'])
    kume, _ = olay.kumele(k)
    assert len(kume) == 2, 'ilgisiz iki olay birleşti'


def test_pencere_disi_birlesmez():
    """Aynı adlar aylar sonra yeniden geçebilir; pencere bunu ayırır."""
    k = [
        {'gun': '2026-02-13', 'baslik': 'Odido Müşteri Verilerinin '
         'Sızdırılması', 'kat': 'veri_ihlali', 'onem': 42, 'eksen': None},
        {'gun': '2026-07-21', 'baslik': 'Odido Müşteri Verilerinin '
         'Sızdırılması', 'kat': 'veri_ihlali', 'onem': 42, 'eksen': None},
    ]
    for x in k:
        x['bel'] = olay.belirtecler(x['baslik'])
    kume, _ = olay.kumele(k)
    assert len(kume) == 2


def test_gercek_arsivde_tekillestirme_calisiyor():
    k = olay.arsivi_tara()
    kume, _ = olay.kumele(k)
    assert len(k) > 4000
    # Tekilleştirme olmalı ama kayıtların büyük kısmı tekil olay olmalı:
    # aşırı birleştirme kümeleme eşiğinin bozulduğunu gösterir.
    assert len(kume) < len(k), 'hiç tekilleştirme olmadı'
    assert len(kume) > len(k) * 0.8, 'aşırı birleştirme — eşik bozulmuş'


def test_kayit_kimligi_sira_numarasindan_bagimsiz():
    """Aynı gün yeniden üretilirse `[N]` kayar, başlık kalır."""
    a = olay.kayit_kimligi({'gun': '2026-02-13', 'baslik': 'Odido İhlali',
                            'sira': 3})
    b = olay.kayit_kimligi({'gun': '2026-02-13', 'baslik': 'Odido İhlali',
                            'sira': 17})
    assert a == b and a.startswith('2026-02-13-')


def test_kimlik_onceki_kosudan_devralinir():
    k = [{'gun': '2026-02-13', 'baslik': 'Odido İhlali'},
         {'gun': '2026-02-15', 'baslik': 'Odido İhlali Devamı'}]
    onceki = {olay.kayit_kimligi(k[0]): 'O-ESKI'}
    kimlik, esleme, takma = olay.kimlik_ata({0: [0, 1]}, k, onceki)
    assert kimlik[0] == 'O-ESKI', 'kimlik yeniden üretildi'
    assert esleme[olay.kayit_kimligi(k[1])] == 'O-ESKI'


def test_birlesmede_kaybeden_kimlik_takma_olarak_saklanir():
    """Eski atıflar çözülebilsin diye kaybeden kimlik kaydedilir."""
    k = [{'gun': '2026-02-13', 'baslik': 'A olayı'},
         {'gun': '2026-02-14', 'baslik': 'B olayı'},
         {'gun': '2026-02-15', 'baslik': 'C olayı'}]
    onceki = {olay.kayit_kimligi(k[0]): 'O-BIR',
              olay.kayit_kimligi(k[1]): 'O-BIR',
              olay.kayit_kimligi(k[2]): 'O-IKI'}
    kimlik, _, takma = olay.kimlik_ata({0: [0, 1, 2]}, k, onceki)
    assert kimlik[0] == 'O-BIR', 'çoğunluk kimliği kazanmalı'
    assert takma == {'O-IKI': 'O-BIR'}


def test_esik_degisince_kimlikler_kaymaz():
    """ÖLÇÜLDÜ: eşik 0,5 → 0,4 yapılınca 261 olay birleşti ama kimliklerin
    TAMAMI devralındı; yeniden üretilen kimlik sayısı 0."""
    import json
    k = olay.arsivi_tara()
    onceki, _ = olay.kimlik_yukle()
    if not onceki:
        import pytest
        pytest.skip('data/olay_kimlik.json henüz üretilmemiş')
    eski_esik = olay.ESIK
    try:
        olay.ESIK = 0.4
        kume, _ = olay.kumele(k)
        kimlik, _, takma = olay.kimlik_ata(kume, k, onceki)
    finally:
        olay.ESIK = eski_esik
    yeni = set(kimlik.values()) - set(onceki.values())
    assert not yeni, f'{len(yeni)} kimlik yeniden üretildi'
    assert takma, 'birleşen olayların takma adı kaydedilmemiş'
