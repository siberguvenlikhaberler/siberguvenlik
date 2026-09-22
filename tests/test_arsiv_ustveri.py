"""ARŞİV ÜSTVERİSİ — kategori ve manşet işareti arşive yazılır.

NEDEN: arşiv 7 aylık ve budanmıyor (13 Şubat'tan beri 4.809 haber) ama
yalnızca başlık + paragraf + kaynak + tarih taşıyordu. Kategori, puan ve
hangi haberin manşet olduğu yalnızca skorlama_log (67 gün), rapor_gecmis ve
kritik3_gecmis (31 gün) dosyalarındaydı; günlük raporlar da 30 günde
siliniyor. "Kategoriye göre dağılım" ya da "yılın manşetleri" gibi yıl sonu
soruları bu yüzden cevaplanamıyordu.
"""
import re
import main


def test_meta_kur_manset_ve_kategori_tasir():
    meta = main.HaberSistemi._arsiv_meta_kur(
        [1], {1: {'tr_title': 'A haberi'}, 2: {'tr_title': 'B haberi'}},
        {1: {'kat': 'nation_state_apt', 'toplam': 95},
         2: {'kat': 'veri_ihlali', 'toplam': 70}})
    assert meta['A haberi'] == {'manset': True, 'kat': 'nation_state_apt', 'puan': 95}
    assert meta['B haberi']['manset'] is False


def test_meta_kur_kayit_yoksa_cokmez():
    meta = main.HaberSistemi._arsiv_meta_kur([1], {1: {'tr_title': 'A'}}, None)
    assert meta['A'] == {'manset': True, 'kat': '', 'puan': 0}


def test_bassiz_kayit_atlanir():
    assert main.HaberSistemi._arsiv_meta_kur([], {1: {'tr_title': '  '}}, {}) == {}


# ── Üstveri satırı biçimi: mevcut okuyucuları BOZMAMALI ──────────────────
_SATIR = '» manset=evet | kategori=nation_state_apt | puan=95'


def test_ustveri_satiri_baslik_kalibina_uymaz():
    """_load_recent_events başlıkları '\\n[ N] ...' kalıbıyla topluyor."""
    assert not re.match(r'\[\s*\d+\]\s*(.+)', _SATIR)


def test_ustveri_satiri_entity_gurultusu_uretmez():
    """_load_recent_events kod adlarını CamelCase / ALL-CAPS ile çıkarır;
    üstveri satırı bilerek küçük harf ve alt çizgilidir."""
    for pat in (r'\b[A-Za-z]+[A-Z][A-Za-z0-9]{2,}\b',
                r'\b[A-Z][a-z]+[A-Z]+\b',
                r'\b[A-Z]{2,}[A-Z0-9]*-?[0-9]{2,}\b',
                r'\b[A-Z]{4,}\b'):
        assert not re.findall(pat, _SATIR), pat


def test_geri_doldurma_betigi_ustveriyi_paragrafa_katmaz():
    src = open('scripts/gecmis_geri_doldur.py', encoding='utf-8').read()
    assert "startswith('»')" in src
