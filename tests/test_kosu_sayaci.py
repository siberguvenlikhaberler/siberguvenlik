"""Günlük tam koşu sınırı (kullanıcı kararı, 2026-11-07)."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    'kosu_sayaci', Path(__file__).parent.parent / 'scripts' / 'kosu_sayaci.py')
ks = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ks)


def test_ilk_iki_koşu_izinli_ucuncu_durur():
    s = {}
    for beklenen in (1, 2):
        devam, s, _ = ks.karar('2026-11-08', False, s, sinir=2)
        assert devam and s == {'tarih': '2026-11-08', 'adet': beklenen}
    devam, yeni, mesaj = ks.karar('2026-11-08', False, s, sinir=2)
    assert not devam and yeni is None and 'sınır 2' in mesaj


def test_yeni_gun_sayaci_sifirlar():
    devam, s, _ = ks.karar('2026-11-09', False,
                           {'tarih': '2026-11-08', 'adet': 2}, sinir=2)
    assert devam and s == {'tarih': '2026-11-09', 'adet': 1}


def test_basarili_rapor_varsa_sayilmaz():
    devam, s, _ = ks.karar('2026-11-08', True,
                           {'tarih': '2026-11-08', 'adet': 2}, sinir=2)
    assert devam and s is None


def test_is_akisi_sayaci_ana_isten_once_ve_manuelde_muaf():
    yml = (Path(__file__).parent.parent / '.github/workflows/daily.yml'
           ).read_text('utf-8')
    assert yml.index('scripts/kosu_sayaci.py') < yml.index('python -u main.py')
    blok = yml[yml.index('- name: Günlük tam koşu sınırı'):]
    assert "github.event_name != 'workflow_dispatch'" in blok.split('run:')[0]
