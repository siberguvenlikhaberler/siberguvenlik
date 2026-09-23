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
