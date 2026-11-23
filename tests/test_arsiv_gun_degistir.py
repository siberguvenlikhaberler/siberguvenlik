"""AYNI GÜN YENİDEN ÜRETİMDE ARŞİV YAYIMLANAN RAPORU TAŞIR.

ÖLÇÜLDÜ (2026-11-23): taban altı ilk koşu arşive yazıldı, yayımlanan ikinci
koşu "blok zaten var" denip atlandı; yayımlanan 6 haberin yalnızca 1'i
arşivdeydi. Konumla anahtarlanan etiketler de silinmeli — yoksa eski
etiket aynı sıradaki başka habere yapışır.
"""
import json
import os

import main

AYRAC = '\n' + '=' * 80 + '\n'


def _blok(baslik, kayitlar):
    s = f'{AYRAC}{baslik}{AYRAC}\n'
    for i, k in enumerate(kayitlar, 1):
        s += f'[{i:2d}] {k}\nparagraf\n\n' + '─' * 80 + '\n\n'
    return s


def _kur(tmp_path, monkeypatch, icerik, depolar):
    monkeypatch.chdir(tmp_path)
    os.makedirs('data')
    open(main.ARCHIVE_FILE, 'w', encoding='utf-8').write(icerik)
    for ad, d in depolar.items():
        json.dump(d, open(f'data/{ad}.json', 'w', encoding='utf-8'))


H22 = '📅 22 NOVEMBER 2026 - EN ÖNEMLİ HABERLER (SEÇİLMİŞ)'
H23 = '📅 23 NOVEMBER 2026 - EN ÖNEMLİ HABERLER (SEÇİLMİŞ)'


def test_blok_yoksa_degistirmez(tmp_path, monkeypatch):
    _kur(tmp_path, monkeypatch, _blok(H22, ['a']), {})
    assert not main.HaberSistemi._arsiv_gun_blogunu_degistir(
        H23, _blok(H23, ['x']), '2026-11-23')


def test_son_blok_degisir_eski_gunler_korunur(tmp_path, monkeypatch):
    eski = _blok(H22, ['a', 'b'])
    _kur(tmp_path, monkeypatch, eski + _blok(H23, ['ilk1', 'ilk2', 'ilk3']),
         {'retro_etiket': {'2026-11-22|1': {'onem': 50},
                           '2026-11-23|2': {'onem': 76}},
          'kurban_etiket': {'2026-11-23|2': {'ad': 'Cleverbridge'}}})
    assert main.HaberSistemi._arsiv_gun_blogunu_degistir(
        H23, _blok(H23, ['yeni1', 'yeni2']), '2026-11-23')
    a = open(main.ARCHIVE_FILE, encoding='utf-8').read()
    assert a.startswith(eski)
    assert a.count(H23) == 1 and 'yeni2' in a and 'ilk1' not in a
    r = json.load(open('data/retro_etiket.json'))
    assert r == {'2026-11-22|1': {'onem': 50}}
    assert json.load(open('data/kurban_etiket.json')) == {}


def test_ortadaki_blok_degisince_sonraki_gun_korunur(tmp_path, monkeypatch):
    sonraki = _blok('📅 24 NOVEMBER 2026 - EN ÖNEMLİ HABERLER (SEÇİLMİŞ)',
                    ['c'])
    _kur(tmp_path, monkeypatch, _blok(H23, ['ilk']) + sonraki, {})
    main.HaberSistemi._arsiv_gun_blogunu_degistir(
        H23, _blok(H23, ['yeni']), '2026-11-23')
    a = open(main.ARCHIVE_FILE, encoding='utf-8').read()
    assert a.endswith(sonraki) and 'yeni' in a and 'ilk' not in a


def test_cok_bloklu_gunde_son_blok_anahtari(tmp_path, monkeypatch):
    _kur(tmp_path, monkeypatch, _blok(H23, ['b1']) + _blok(H23, ['b2']),
         {'retro_etiket': {'2026-11-23|1': {'onem': 1},
                           '2026-11-23#2|1': {'onem': 2}}})
    main.HaberSistemi._arsiv_gun_blogunu_degistir(
        H23, _blok(H23, ['yeni']), '2026-11-23')
    a = open(main.ARCHIVE_FILE, encoding='utf-8').read()
    assert 'b1' in a and 'b2' not in a and 'yeni' in a
    assert json.load(open('data/retro_etiket.json')) == {
        '2026-11-23|1': {'onem': 1}}


def test_budama_kapisi_beklenen_farki_asamaz(tmp_path):
    import importlib.util
    sp = importlib.util.spec_from_file_location(
        'arsiv_yaz', os.path.join(os.path.dirname(main.__file__), 'scripts',
                                  'arsiv_yaz.py'))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    yol = tmp_path / 'a.txt'
    yol.write_text(_blok(H22, ['a', 'b', 'c']), encoding='utf-8')
    yeni = _blok(H22, ['a']).splitlines(True)
    try:
        m.guvenli_yaz(str(yol), yeni, izinli_dusus=1)
        assert False, 'düşüş 2 iken izin 1 — reddedilmeliydi'
    except RuntimeError:
        pass
    assert m.guvenli_yaz(str(yol), yeni, izinli_dusus=2) == 1
