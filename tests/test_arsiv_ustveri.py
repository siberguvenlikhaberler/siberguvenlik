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


# ── Tam kaynak URL ────────────────────────────────────────────────────────
# Arşivde yalnızca alan adı vardı; tam adres HTML raporda ve 7 günlük
# haberler_linkler.txt'deydi. Rapor 30 günde silindiği için bir habere geri
# dönüp kaynağı açmak 30 gün sonra imkânsızdı.

def _arsiv_uret(html):
    s = main.HaberSistemi.__new__(main.HaberSistemi)
    s._check_archive_size = lambda: None
    import tempfile, os, importlib
    d = tempfile.mkdtemp()
    eski = os.getcwd()
    try:
        os.chdir(d)
        os.makedirs('data', exist_ok=True)
        main.ARCHIVE_FILE = 'data/haberler_arsiv.txt'
        s.save_summary_to_archive(html, {'Test Başlığı': {
            'manset': True, 'kat': 'nation_state_apt', 'puan': 95}})
        return open('data/haberler_arsiv.txt', encoding='utf-8').read()
    finally:
        os.chdir(eski)


_HTML = '''<html><body>
<div class="top3-card">
  <div class="top3-card-title"><a href="https://ornek.com/haber/1">Test Başlığı</a></div>
  <div class="top3-card-paragraph">Paragraf metni burada yer almaktadir.</div>
  <p class="source">(XXXXXXX, AÇIK -ornek.com, 21.09.2026)</p>
</div></body></html>'''


def test_tam_url_arsive_yazilir():
    out = _arsiv_uret(_HTML)
    assert '» url=https://ornek.com/haber/1' in out


def test_ustveri_ve_url_birlikte_yazilir():
    out = _arsiv_uret(_HTML)
    assert '» manset=evet | kategori=nation_state_apt | puan=95' in out
    assert out.index('» url=') < out.index('» manset=')


def test_url_yoksa_cokmez():
    html = _HTML.replace('<a href="https://ornek.com/haber/1">', '<span>').replace('</a>', '</span>')
    out = _arsiv_uret(html)
    assert 'Test Başlığı' in out and '» url=' not in out
