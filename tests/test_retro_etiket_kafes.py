"""RETRO ETİKET — rubrik kafesi ve eksen doğrulaması.

NEDEN VAR: `onem` LLM yargısıdır ve yargı oturumlar arasında kayar. ÖLÇÜLDÜ
(2026-09-23): 5.043 kaydın 1.116'sının `onem` değeri dört eksenin
toplayabileceği değerler kümesinin dışındaydı — o kayıtlarda eksenler hiç
hesaplanmamış, sayı doğrudan atanmıştı. Kayma dönemsel görünüyordu (p90
Şubat-Haziran 76, Temmuz-Eylül 68) ama nedeni buydu.

Kafes doğrulaması kaymayı YAPISAL olarak imkansız kılar: rubriğin izin
verdiği toplamlar dışında bir sayı depoya giremez.
"""
import importlib.util
import pathlib

_yol = (pathlib.Path(__file__).resolve().parent.parent
        / 'scripts' / 'retro_etiket.py')
_spec = importlib.util.spec_from_file_location('retro_etiket', _yol)
retro = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(retro)


def test_kafes_capalarin_toplamlarindan_olusur():
    assert retro.CAPA == (0, 8, 17, 25)
    assert retro.KAFES[0] == 0 and retro.KAFES[-1] == 100
    for x in (41, 50, 59, 67, 76, 84, 92):
        assert x in retro.KAFES
    # Ara değerler kafeste YOKTUR; v1'deki kaymanın imzası bunlardı.
    for x in (52, 55, 62, 65, 70, 72, 78, 80, 85):
        assert x not in retro.KAFES, x


def test_eksenli_etiket_toplamla_tutmalidir():
    assert retro.dogrula('nation_state_apt', 84, [17, 25, 25, 17]) == ''
    msg = retro.dogrula('nation_state_apt', 80, [17, 25, 25, 17])
    assert 'eksen toplamı' in msg


def test_capa_disi_eksen_reddedilir():
    msg = retro.dogrula('veri_ihlali', 50, [10, 15, 15, 10])
    assert 'dışında' in msg


def test_eksensiz_etikette_kafes_aranir():
    """v1 kayıtları eksen taşımaz; en azından toplam kafeste olmalı."""
    assert retro.dogrula('veri_ihlali', 50) == ''
    assert 'kafesinde yok' in retro.dogrula('veri_ihlali', 52)


def test_tavan_kategorisi_kafes_disinda_kalabilir():
    """urun_icerik tavanı 39'dur ve 39 kafeste yoktur; kırpma meşrudur."""
    assert 39 not in retro.KAFES
    assert retro.onem_hesapla('urun_icerik', [25, 25, 17, 8]) == 39
    assert retro.dogrula('urun_icerik', 39, [25, 25, 17, 8]) == ''
    assert retro.dogrula('urun_icerik', 39) == ''


def test_gercek_depoda_kafes_disi_kayit_yok():
    """Kayma alarmı: depoya kafes dışı bir etiket sızarsa burada patlar."""
    d = retro.depo_yukle()
    assert len(d) > 4000, 'depo beklenenden küçük'
    kotu = [(a, v) for a, v in d.items()
            if retro.dogrula(v.get('kat'), v.get('onem'), v.get('eksen'))]
    assert not kotu, f'{len(kotu)} kafes dışı etiket: {kotu[:5]}'
