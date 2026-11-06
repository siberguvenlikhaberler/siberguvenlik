"""Manşet çapraz-gün LLM işaretinin KANIT kapısı (2026-11-06).

Vaka: 5 Kasım'da Fransa Ulusal Kan Hizmeti'nin soğutma sistemlerine saldırı
(99 puan) manşet çapraz-gün LLM'i tarafından "son günlerin tekrarı" denip
manşetten çıkarıldı; oysa soğutma kampanyasının YENİ KURBANIYDI. Görünümler
üretim kayıtlarından alınmıştır (tests/fixtures/manset_capraz_kanit.json).
"""
import json
from pathlib import Path

from src import dedup
from src import olay_iliski as oi

V = json.loads((Path(__file__).parent / 'fixtures' /
                'manset_capraz_kanit.json').read_text('utf-8'))


def test_yeni_kurban_kanitsiz_reddedilir():
    kan = V['kan_hizmeti_2026_11_05']
    for gecmis in ('abd_ussleri_2026_10_30', 'fransa_market_2026_10_16'):
        for ortak in ('soğutma sistemleri', 'Soğutma Sistemleri', 'Fransa',
                      'Ulusal', 'Copeland', ''):
            kabul, _ = oi.capraz_gun_kaniti(kan, V[gecmis], ortak)
            assert not kabul, (gecmis, ortak)


def test_iki_tanim_da_kan_hizmetini_ayri_olay_sayar():
    kan = V['kan_hizmeti_2026_11_05']
    for gecmis in ('abd_ussleri_2026_10_30', 'fransa_market_2026_10_16'):
        assert oi.mukerrer_karari(kan, V[gecmis]) == oi.FARKLI
        assert oi.iliski_belirle(kan, V[gecmis]) == oi.ILISKISIZ


def test_gercek_tekrar_ortak_adla_kabul_edilir():
    # 29 Eylül OpenAI/Avustralya — 24 Eylül Medicare haberinin devamı;
    # deterministik tanımlar kaçırıyor, LLM kanıtı yakalıyor.
    a = V['openai_avustralya_2026_09_29']
    m = V['openai_medicare_2026_09_24']
    assert oi.capraz_gun_kaniti(a, m, 'Medicare')[0]
    assert oi.capraz_gun_kaniti(a, m, 'OpenAI')[0]
    # Ülke adı tek başına kanıt değildir.
    assert not oi.capraz_gun_kaniti(a, m, 'Avustralya')[0]


def test_ayristirici_iki_bicimi_de_okur():
    assert dedup.parse_cross_day_kanit({'duplicates': [7, '15']}, [7, 15]) \
        == {7: (None, ''), 15: (None, '')}
    yanit = {'duplicates': [{'id': 7, 'gecmis': 'R3', 'ortak': 'Binance'},
                            {'id': 99, 'gecmis': 'R1'}, {'gecmis': 'R2'},
                            'bozuk']}
    assert dedup.parse_cross_day_kanit(yanit, [7, 15]) == {7: (3, 'Binance')}
    # Gövde yolu yalnızca id kullanır, yeni biçimde de çalışmalı.
    assert dedup.parse_cross_day_dupes(yanit, [7, 15]) == {7}


def test_prompt_kanit_istiyor():
    from src.config import get_cross_day_dedup_prompt
    p = get_cross_day_dedup_prompt('X', 'Y')
    assert '"gecmis"' in p and '"ortak"' in p


def test_stablecoin_ihraccisi_olay_kimligi_degildir():
    """30 Ekim: Binance soygunu (100) 1 Ekim Bitget manşetiyle
    `ad:circle,ad:tether` üzerinden AYNI_GELISME sayılıyor ve 'zaten manşet
    oldu' diye manşete kapanıyordu. İki ayrı borsa, iki ayrı olay."""
    b, g = V['binance_2026_10_30'], V['bitget_2026_10_01']
    assert oi.iliski_belirle(b, g) == oi.ILISKISIZ
    d = oi.OlayDefteri().gunleri_isle([('2026-10-01', [g], [g])])
    assert d.manset_gunu_sayisi(b) == 0
