"""ÜRETİM HATTINDA ÖNEM EKSENİ — `» sonradan` satırının kaynağı.

NEDEN VAR: 23 Eylül'e kadarki 5.043 kayıt geriye dönük etiketlenerek tek bir
`onem` ölçeğine taşındı, ama üretim hattı bu alanı YAZMIYORDU. Yıl sonuna 99
gün ve bu tempoyla ~2.300 yeni kayıt vardı — havuzun üçte biri. Hattı
değiştirmeseydik "iki ayrı ölçek" sorunu, üstelik yılın son çeyreğini
kapsayarak geri gelecekti.

Eksenler skorlama ajanının aynı çağrısında üretilir (ek LLM maliyeti yok) ve
çapalara OTURTULUR: rubrik ara değer tanımaz, serbest sayıya izin vermek aynı
kaymayı üretim hattına taşırdı.
"""
import itertools

import main

S = main.HaberSistemi


def _ham(**kw):
    t = {'kat': 'veri_ihlali', 'siber': 1, 'mukerrer': 0,
         's': 20, 'e': 10, 'a': 8, 'k': 10}
    t.update(kw)
    return t


def test_eksenler_capalara_oturur():
    """LLM ara değer verirse en yakın çapaya çekilir."""
    rec = S._normalize_record(S, _ham(oe=20, ok=5, oa=24, os=1))
    assert rec['eksen'] == [17, 8, 25, 0]
    assert rec['onem'] == 50


def test_eksen_toplami_kafes_uzerinde():
    """Çapa toplamları rubriğin kafesini üretir; ara toplam çıkamaz."""
    kafes = {sum(c) for c in itertools.combinations_with_replacement(
        S.ONEM_CAPA, 4)}
    for combo in itertools.product(S.ONEM_CAPA, repeat=4):
        rec = S._normalize_record(S, _ham(oe=combo[0], ok=combo[1],
                                          oa=combo[2], os=combo[3]))
        assert rec['onem'] in kafes


def test_tavan_kategorisinde_kirpilir():
    rec = S._normalize_record(S, _ham(kat='urun_icerik',
                                      oe=25, ok=25, oa=17, os=8))
    assert rec['onem'] == S.ONEM_TAVAN == 39
    assert rec['eksen'] == [25, 25, 17, 8], 'tavan eksenleri değiştirmemeli'


def test_eksen_eksikse_alan_yazilmaz():
    """Uydurma değer yazmaktansa alan BOŞ kalır; eksik kaydı `durum` raporlar."""
    for eksik in ({}, {'oe': 17}, {'oe': 17, 'ok': 8, 'oa': 25},
                  {'oe': 17, 'ok': 8, 'oa': 25, 'os': None},
                  {'oe': 17, 'ok': 8, 'oa': 25, 'os': 'abc'}):
        rec = S._normalize_record(S, _ham(**eksik))
        assert 'eksen' not in rec, eksik
        assert 'onem' not in rec, eksik


def test_meta_eksenleri_tasir():
    meta = S._arsiv_meta_kur(
        [1], {1: {'tr_title': 'A'}},
        {1: {'kat': 'nation_state_apt', 'toplam': 95,
             'eksen': [17, 25, 25, 17], 'onem': 84}})
    assert meta['A']['onem'] == 84 and meta['A']['eksen'] == [17, 25, 25, 17]


def test_skorlama_prompt_eksenleri_istiyor():
    """Prompt dört ekseni de adıyla istemeli; biri düşerse alan hiç gelmez."""
    from src.config import get_scoring_prompt
    p = get_scoring_prompt('=== HABER ID: 1 ===\nBaşlık: x\n')
    for anahtar in ('oe', 'ok', 'oa', 'os'):
        assert f'"{anahtar}"' in p or f'{anahtar} =' in p or f'{anahtar} ' in p
    assert 'RETRO_RUBRIK.md' in p


def test_yazilan_satir_retro_ayristiricisiyla_okunur():
    """ÜRETİM yazıcısı ile GERİYE DÖNÜK okuyucu aynı biçimi konuşmalı.

    İkisi ayrı dosyada olduğu için biçim sessizce ayrışabilir; o zaman yeni
    kayıtlar arşive yazılır ama `retro_etiket topla` onları göremez ve depo
    ile arşiv ayrışır.
    """
    import importlib.util
    import pathlib
    yol = (pathlib.Path(__file__).resolve().parent.parent
           / 'scripts' / 'retro_etiket.py')
    spec = importlib.util.spec_from_file_location('retro_etiket', yol)
    retro = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(retro)

    m = {'kat': 'nation_state_apt', 'onem': 84, 'eksen': [17, 25, 25, 17]}
    satir = (f"» sonradan | kategori={m['kat']} | onem={m['onem']}"
             f" | eksen={'/'.join(str(x) for x in m['eksen'])} | rubrik=v2")
    eslesme = retro._SONRADAN_AYRIS.match(satir)
    assert eslesme, 'üretim satırı retro ayrıştırıcısına uymuyor'
    assert eslesme.group(1) == 'nation_state_apt'
    assert int(eslesme.group(2)) == 84
    assert [int(x) for x in eslesme.groups()[2:]] == [17, 25, 25, 17]
    assert retro.dogrula(m['kat'], m['onem'], m['eksen']) == ''


def test_yazici_kaynaginda_bicim_korunuyor():
    """Biçim dizesi main.py içinde; testin gördüğü kalıpla aynı olmalı."""
    src = open('main.py', encoding='utf-8').read()
    assert '» sonradan | kategori=' in src
    assert '| rubrik=v2' in src
    assert "m.get('eksen') and m.get('onem') is not None" in src
