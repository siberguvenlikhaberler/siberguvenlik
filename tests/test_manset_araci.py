"""MANŞET ARACISI — `_manset_yasak`ın ve kararın TEK YAZARI.

KRİTİK 3'ü yedi katman değiştirebiliyor ve her biri kararını kendi elleriyle
yazıyordu: `hasattr` kontrolü + `_manset_yasak.add` + `_manset_karar_kaydet`
üçlüsü dört ayrı yerde kopyalanmıştı. Kopyalanan idiomu yeni katman yazarı
ATLAR; aynı arıza ÜÇ KEZ ölçüldü — auditor kararı (2026-08-25, "yaşlıları
dolandıran şebeke" son kapıdan manşete geri döndü), olay defteri (2026-08-21,
Siemens PLC iki gün üst üste manşet), çapraz-gün (2026-10-04, dört günlük
OpenAI/Avustralya tekrarı yayın yönetmeniyle birinci manşet oldu).

Aracı LLM çağrısı YAPMAZ/EKLEMEZ — maliyet değişmez. İşi muhasebedir:
kalıcılık tek tablodan (`MANSET_KALICI_KATMAN`) okunur, çağıran yer karar
vermez.
"""
import inspect
import re

import main


def _sistem():
    return main.HaberSistemi.__new__(main.HaberSistemi)


def test_yasak_tek_yazardan_gecer():
    """Kaynak taraması: `_manset_yasak`a ekleme YALNIZCA aracıda olabilir.

    Bu testin işi gelecekteki bir katman yazarını durdurmaktır; davranış
    testi değil, YAPI testidir.
    """
    kaynak = inspect.getsource(main).splitlines()
    araci = inspect.getsource(main.HaberSistemi._manset_yasagi_koy)
    ihlal = []
    for i, satir in enumerate(kaynak, 1):
        if re.search(r'_manset_yasak\s*(\.add\(|\|=|\.update\()', satir):
            if satir.strip() not in araci:
                ihlal.append((i, satir.strip()))
        # Kümeyi yeniden kurmak yalnızca koşu başı sıfırlamada ve aracıda olur.
        if re.search(r'self\._manset_yasak\s*=\s*set\(\)', satir):
            onceki = '\n'.join(kaynak[max(0, i - 6):i])
            if 'KOŞU BAŞI SIFIRLAMA' not in onceki and satir.strip() not in araci:
                ihlal.append((i, satir.strip()))
    assert not ihlal, f'aracı dışında yasak yazımı: {ihlal}'


def test_kalici_katman_yasak_yazar():
    s = _sistem()
    s._manset_takas('manset_capraz_gun_llm', 5, 9, 'tekrar')
    assert 5 in s._manset_yasak
    izler = [i['katman'] for i in s._manset_izi]
    assert 'manset_capraz_gun_llm' in izler
    assert 'yasak:manset_capraz_gun_llm' in izler


def test_goreli_katman_yasak_yazmaz():
    s = _sistem()
    s._manset_takas('yayin_yonetmeni_takas', 5, 9, 'sıralama')
    assert not getattr(s, '_manset_yasak', set())
    assert [i['katman'] for i in s._manset_izi] == ['yayin_yonetmeni_takas']


def test_bilinmeyen_katman_guvenli_tarafta():
    """Tabloda olmayan katman yasak YAZMAZ ama izlenir."""
    s = _sistem()
    s._manset_takas('yeni_katman', 5, 9, 'bilinmeyen')
    assert not getattr(s, '_manset_yasak', set())
    assert s._manset_izi[0]['katman'] == 'yeni_katman'


def test_yasak_fikir_degismez():
    s = _sistem()
    s._manset_yasagi_koy(7, 'son_mukerrer_kapisi', 'mükerrer')
    s._manset_yasagi_koy(7, 'son_mukerrer_kapisi', 'mükerrer')
    assert s._manset_yasak == {7}
    assert len(s._manset_izi) == 1, 'aynı yasak ikinci kez ize yazıldı'


def test_iki_tablo_ayrik_ve_katman_adlari_gercek():
    """Tablolar çakışmaz ve adları gerçekten kullanılan katman adlarıdır."""
    kalici = main.HaberSistemi.MANSET_KALICI_KATMAN
    goreli = main.HaberSistemi.MANSET_GORELI_KATMAN
    assert not (kalici & goreli)
    kaynak = inspect.getsource(main)
    for ad in kalici | goreli:
        assert f"'{ad}'" in kaynak, ad


def test_araci_llm_cagrisi_yapmaz():
    """Maliyet nötrlüğü: aracı hiçbir LLM çağrısına dokunmaz."""
    for fn in (main.HaberSistemi._manset_yasagi_koy,
               main.HaberSistemi._manset_takas,
               main.HaberSistemi._manset_karar_kaydet):
        # Yorum/docstring katman ADLARINI anıyor; yalnızca KOD satırlarına bak.
        kod = [l for l in inspect.getsource(fn).splitlines()
               if l.strip() and not l.strip().startswith('#')]
        kod = '\n'.join(kod)
        for cagri in ('_gemini_call', '_llm.', 'genai'):
            assert cagri not in kod, (fn.__name__, cagri)
