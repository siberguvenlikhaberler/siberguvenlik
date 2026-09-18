"""PASS 5 — devlet/kurum eylemleri "genel tavsiye" sayılıp elenmez.

ÖLÇÜLDÜ (2026-09-11..18): üretime giren 333 haberin %19'u Pass 5'te düştü ama
dağılım dengesizdi — politika_hukuk %57 (54 haberin 31'i), nation_state_apt ve
tedarik_zinciri %0. Elenen 31 politika haberinin ~19'u gerçek haberdi: FBI
siber stratejisi (94), CISA/NSA ortak rehberi (89), AB CRA yürürlüğü (87),
FERC NERC CIP-014-4 onayı (82), İngiltere'nin 23 milyon kullanıcıda parolayı
kaldırması (81), Ukrayna'nın siber koordinasyon ataması (83). Günde ~2,4
politika haberi kaybı.

Kök neden: Kontrol 3'teki "genel tavsiye" maddesi devlet rehberini/
düzenlemesini/atamasını kapsıyordu (bunlar "saldırı" anlatmıyor), oysa manşet
denetim promptu ölçütün "somut bir gelişme mi" olduğunu zaten söylüyordu.
İki denetim ayrışmıştı.
"""
from src.config import (get_quality_review_prompt,
                        get_kritik3_selection_audit_prompt)


def _p5():
    return get_quality_review_prompt('=== HABER ID: 1 ===')


def test_devlet_eylemi_muafiyeti_var():
    p = _p5()
    assert 'DEVLET/KURUM EYLEMLERİ' in p
    assert 'genel tavsiye' in p.lower()


def test_olcut_saldiri_degil_somut_gelisme():
    """Manşet denetimindeki ölçütün aynısı Pass 5'te de yazılı olmalı."""
    assert 'somut bir gelişme mi' in _p5()


def test_iki_denetim_ayni_olcutu_tasir():
    """İki prompt ayrışırsa aynı haber bir kapıdan geçip diğerinde düşer."""
    k3 = get_kritik3_selection_audit_prompt('m', 'g')
    assert 'somut bir gelişme mi' in k3
    assert 'somut bir gelişme mi' in _p5()


def test_kalan_ornekleri_listeleniyor():
    p = _p5()
    for ornek in ('FBI', 'CISA/NSA', 'CRA', 'FERC', 'NIST'):
        assert ornek in p, ornek


def test_cikan_ornekleri_de_listeleniyor():
    """Muafiyet ters yöne kaçmamalı: köşe yazısı, röportaj, satıcı duyurusu ve
    şirketin kendi öz değerlendirmesi elenmeye devam eder."""
    p = _p5()
    for ornek in ('köşe yazısı', 'röportaj', 'Entrust', 'Stratom',
                  'scheme documents now available'):
        assert ornek in p, ornek
