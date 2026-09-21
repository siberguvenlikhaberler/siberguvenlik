"""YATIRIM/FONLAMA DUYURUSU haber değildir — iki katmanda da yazılı.

ÖLÇÜLDÜ (2026-09-20): "TigerByte Cyber Emerges From Stealth With $3 Million in
funding" haberi `politika_hukuk` etiketlenip 57 puan aldı. O gün arz kurumuştu
(18 haberin 7'si zaten haber değildi, çapraz-gün filtresi kalanların yarısını
aldı) ve üç manşet garantisi bu haberi RAPORUN BİRİNCİ MANŞETİ yaptı.

Manşet garantisi kaldırılmıyor (kullanıcı kararı: manşet asla 2'ye düşmez).
Bunun yerine böyle bir haberin havuza hiç girmemesi sağlanıyor:
  • Skorlayıcı → `urun_icerik` (0 puan, KRITIK3_HARIC_KATEGORILER'de)
  • Pass 5     → kriter dışı (yedek kapı)
"""
from src.config import get_scoring_prompt, get_quality_review_prompt


def test_skorlayici_sirket_finans_duyurusunu_urun_icerik_sayar():
    s = get_scoring_prompt('=== HABER ===')
    assert 'ŞİRKET/FİNANS DUYURUSU' in s
    assert 'yatırım turu' in s


def test_skorlayici_olculen_vakayi_ornekler():
    s = get_scoring_prompt('=== HABER ===')
    assert 'YATIRIM/FONLAMA DUYURUSU HABER DEĞİLDİR' in s
    assert 'TigerByte' in s


def test_siber_sirketi_olmak_haber_yapmaz_uyarisi_var():
    """En olası hata: şirketin siber güvenlik şirketi olması haberi siber
    güvenlik OLAYI sanmak. İki promptta da açıkça yazılı olmalı."""
    for p in (get_scoring_prompt('x'), get_quality_review_prompt('x')):
        assert 'siber güvenlik şirketi olması' in p


def test_p5_yedek_kapisi_var():
    p = get_quality_review_prompt('=== HABER ID: 1 ===')
    assert 'ŞİRKET/FİNANS DUYURUSU' in p
    for k in ('satın alma', 'birleşme', 'gizlilikten çıkma'):
        assert k in p, k


def test_devlet_karari_muafiyeti_bozulmadi():
    """Önceki düzeltme (2026-09-18) ayakta kalmalı: devlet/kurum eylemleri
    hâlâ haberdir; yeni madde onları kapsamamalı."""
    p = get_quality_review_prompt('x')
    assert 'DEVLET/KURUM EYLEMLERİ' in p
    assert 'somut bir gelişme mi' in p
