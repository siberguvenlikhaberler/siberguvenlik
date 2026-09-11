"""MÜKERRER HAKEMİ — aynı araştırma bulgusu iki yayında çıkarsa AYNI OLAYDIR.

ÖLÇÜLDÜ (2026-09-11): Bitdefender'ın Google Play Erken Erişim incelemesi
gövdede İKİ KEZ yayımlandı — The Hacker News (ID 6) ve CSO Online (ID 37),
ikisi de 47 puan, aynı bulgu ve aynı TikTok/Facebook ayrıntısı.

Deterministik katman haklı olarak eşleştiremedi: paylaşılan kod adı/CVE/kurban
yok ve 'bitdefender' bilerek denylist'te (ölçümde 38 çiftin 7'si tam olarak
araştırmacı adından sahte eşleşmişti). Çift hakeme BİRİNCİ SIRADA geldi
(5.57; ikinci aday 2.98) — yani aday ağı kaçırmadı, hakem "farklı" dedi.

Nedeni tanımdaydı: AYNI OLAY listesi saldırı/kampanya/ihlal/ifşa/operasyon/dava
sayıyordu, ARAŞTIRMA BULGUSU saymıyordu.
"""
from src.config import get_mukerrer_hakem_prompt


def _prompt():
    return get_mukerrer_hakem_prompt('--- ÇİFT 1 ---')


def test_arastirma_bulgusu_ayni_olay_tanimina_dahil():
    assert 'AYNI ARAŞTIRMA BULGUSU' in _prompt()


def test_ayni_arastirmanin_iki_yayinda_cikmasi_fark_saymaz():
    p = _prompt()
    assert 'AYNI ARAŞTIRMANIN İKİ HABER SİTESİNDE ÇIKMASI' in p
    assert 'VURGU farkıdır' in p


def test_karar_kurali_arastirmayi_adlandirilabilir_kiliyor():
    """'Paylaşılan somut olayı adlandır' kuralı araştırma bulgusunda da
    sağlanabilmeli; yoksa hakem otomatik FARKLI demeye zorlanır."""
    p = _prompt()
    assert 'Araştırma bulgularında somut olay RAPORUN KENDİSİDİR' in p


def test_ayni_firmanin_farkli_arastirmasi_karsi_ornegi_durur():
    """Genişletme ters yöne kaçmamalı: ortak olan yalnızca araştırmacıysa
    bu aynı bulgu DEĞİLDİR."""
    p = _prompt()
    assert 'Aynı firmanın FARKLI iki araştırması' in p
    assert 'Ortak olan yalnızca' in p
