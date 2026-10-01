"""PASS 5 — EDİTORYAL YARGI SINIRI.

1 Ekim 2026 raporunda "ABD'de Yapay Zeka Güvenliği İçin Gönüllü Mutabakat
İmzalanması" (93 puan, politika_hukuk) KRİTİK 3'teyken Pass 5 kalite kapısında
silindi ve gerekçesi hiçbir yerde kayıtlı değildi. Ölçüm (son 30 gün): mükerrer
bayrağı olmayan 122 haber bu kapıda düştü; 80+ puanlı 35'inin 27'si gerçek
haberdi, 4'ü çöptü. Politika haberlerinde eleme %43 (174/407), sonraki kategori
%20.

KURAL: Pass 5 METİN kalitesi kapısıdır. KONTROL 3 ("kriter dışı") ve
SPEKÜLASYON editoryal yargıdır; 80 puan ve üstünde REDDEDİLİR. KONTROL 1/2
(bozuk/İngilizce metin) ve KONTROL 4 (kopya) her puanda geçerlidir.
"""
import pytest

from main import p5_editoryal_sinir
from src.config import (KALITE_EDITORYAL_ESIK, KALITE_EDITORYAL_NEDENLER,
                        get_quality_review_prompt)


def _rec(puan):
    return {'toplam': puan}


def test_yuksek_puanli_kriter_disi_kaldirilamaz():
    """1 Ekim vakası: 93 puanlık politika haberi 'kriter dışı' ile düşmez."""
    kalan, korunan = p5_editoryal_sinir(
        {40}, {40: 'kontrol3'}, {40: _rec(93)})
    assert kalan == set()
    assert korunan == [(40, 93, 'kontrol3')]


def test_yuksek_puanli_spekulasyon_da_kaldirilamaz():
    kalan, _ = p5_editoryal_sinir({7}, {7: 'spekulasyon'}, {7: _rec(86)})
    assert kalan == set()


@pytest.mark.parametrize('neden', ['kontrol1', 'kontrol2', 'kontrol4'])
def test_metin_hatasi_ve_kopya_her_puanda_kaldirilir(neden):
    """Bozuk metin ve mükerrer editoryal yargı DEĞİLDİR — muaf değil, serbest."""
    kalan, korunan = p5_editoryal_sinir({5}, {5: neden}, {5: _rec(98)})
    assert kalan == {5}
    assert korunan == []


def test_esigin_altinda_eski_davranis_surer():
    """70 altı bant promptun kendi 'ÇIKAR' örnekleriyle dolu — eleme sürmeli."""
    kalan, korunan = p5_editoryal_sinir({9}, {9: 'kontrol3'}, {9: _rec(68)})
    assert kalan == {9}
    assert korunan == []


def test_esik_sinirinda_korunur():
    kalan, _ = p5_editoryal_sinir(
        {1}, {1: 'kontrol3'}, {1: _rec(KALITE_EDITORYAL_ESIK)})
    assert kalan == set()
    kalan, _ = p5_editoryal_sinir(
        {1}, {1: 'kontrol3'}, {1: _rec(KALITE_EDITORYAL_ESIK - 1)})
    assert kalan == {1}


def test_gerekcesiz_kaldirma_eski_davranisi_korur():
    """LLM 'neden' vermezse sınır devreye girmez; puan kaydı yoksa da."""
    assert p5_editoryal_sinir({3}, {}, {3: _rec(95)})[0] == {3}
    assert p5_editoryal_sinir({3}, {3: 'kontrol3'}, {})[0] == {3}


def test_karisik_kume_yalnizca_editoryal_olani_korur():
    kalan, korunan = p5_editoryal_sinir(
        {1, 2, 3, 4},
        {1: 'kontrol3', 2: 'kontrol1', 3: 'spekulasyon', 4: 'kontrol3'},
        {1: _rec(94), 2: _rec(94), 3: _rec(81), 4: _rec(60)})
    assert kalan == {2, 4}
    assert [r for r, _, _ in korunan] == [1, 3]


def test_prompt_neden_alanini_zorunlu_kiliyor():
    """Sınır 'neden' alanına dayanır; prompt onu istemiyorsa kural ölü koddur."""
    p = get_quality_review_prompt('=== HABER ID: 1 ===')
    assert '"neden"' in p
    for kod in KALITE_EDITORYAL_NEDENLER | {'kontrol1', 'kontrol2', 'kontrol4'}:
        assert f'"{kod}"' in p, kod
