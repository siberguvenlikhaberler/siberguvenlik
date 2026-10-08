"""KAYNAK GÖVDE DEPOSU — ölçümün eksik parçası (2026-10-08).

NEDEN VAR: iki ölçüm aynı duvara çarptı çünkü kaynak gövde metni hiçbir yerde
saklanmıyordu — 2026-09-30 küçük model denemesi ("önce gövdenin loglanması
gerekir") ve 2026-10-08 Hafnium vakası (yönetmenin 95 puanlı haberi düşürme
kararı çevrimdışı yeniden üretilemedi, çünkü defter sorguyu ÜRETİM görünümüyle
yapıyor, saklanan görünüm ise kırpık).
"""
import json
import os
import tempfile

import main


def _sistem():
    return main.HaberSistemi.__new__(main.HaberSistemi)


def _oku(yol):
    with open(yol, encoding='utf-8') as f:
        return [json.loads(x) for x in f if x.strip()]


def _yaz(s, gun, arts, yol):
    eski = main.SOURCE_BODY_LOG_FILE
    main.SOURCE_BODY_LOG_FILE = yol
    try:
        s._kaynak_govde_logla(gun, arts)
    finally:
        main.SOURCE_BODY_LOG_FILE = eski


ARTS = {1: {'title': 'A', 'full_text': 'x' * 5000},
        2: {'title': 'B', 'full_text': ''},          # gövdesiz → yazılmaz
        3: {'title': 'C', 'full_text': 'y' * 100}}


def test_govde_kirpilir_ve_govdesiz_haber_yazilmaz():
    """Kırpma sınırı `olay_iliski._metin`in tarama sınırıyla AYNI olmalı —
    kimlik çıkarımı gövdenin yalnızca o kadarını görür."""
    with tempfile.TemporaryDirectory() as d:
        yol = os.path.join(d, 'g.jsonl')
        _yaz(_sistem(), '2026-10-08', ARTS, yol)
        r = _oku(yol)
        assert len(r) == 2, 'gövdesiz haber depoya yazıldı'
        assert len(r[0]['govde']) == main.SOURCE_BODY_CHARS
        assert {x['id'] for x in r} == {1, 3}


def test_ayni_gun_yeniden_uretim_dosyayi_sismez():
    """Aynı gün yeniden üretilen koşular (bkz. CLAUDE.md reset prosedürü)
    o günün satırlarını ÇOĞALTMAMALI."""
    with tempfile.TemporaryDirectory() as d:
        yol = os.path.join(d, 'g.jsonl')
        s = _sistem()
        _yaz(s, '2026-10-08', ARTS, yol)
        _yaz(s, '2026-10-08', ARTS, yol)
        assert len(_oku(yol)) == 2, 'aynı gün iki kez yazıldı'


def test_pencere_disi_gun_duser():
    """Tavan GÜN cinsindendir ve `rapor_gecmis` ile hizalıdır; satır cinsinden
    tavan yanlış olurdu — kalabalık bir gün tek başına pencereyi yerdi."""
    with tempfile.TemporaryDirectory() as d:
        yol = os.path.join(d, 'g.jsonl')
        with open(yol, 'w', encoding='utf-8') as f:
            f.write(json.dumps({'tarih': '2020-01-01', 'id': 9,
                                'baslik': 'eski', 'govde': 'z'}) + '\n')
        _yaz(_sistem(), '2026-10-08', ARTS, yol)
        assert all(x['tarih'] != '2020-01-01' for x in _oku(yol))


def test_yazim_hatasi_raporu_dusurmez():
    """Bu bir ÖLÇÜM deposudur, üretim verisi değil — hata yalnızca yazdırılır
    (skorlama logunun aynı sözleşmesi)."""
    s = _sistem()
    _yaz(s, '2026-10-08', ARTS, '/olmayan-dizin/x/g.jsonl')   # patlamamalı
