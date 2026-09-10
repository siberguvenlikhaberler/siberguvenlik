"""FEED GÜRÜLTÜSÜ — yayın takvimi kayıtları ve sayfa iskeleti çıkarımları.

ÖLÇÜLDÜ (2026-09-10): SANS ISC'nin günlük "ISC Stormcast" podcast bölümü haber
olarak yutuldu; makale gövdesi çıkmadığı için proxy okuyucuya düştü ve dönen
209 kelimenin yalnızca 56'sı düz metindi (gerisi navigasyon, "Sign In",
"Handler on Duty", tehdit seviyesi kutusu). Ham kelime eşiği (100) geçildiği
için sistem bunu "tam metin çıktı" sayıp skorlamaya taşıdı.
"""
import main


# ── Başlık gürültüsü ──────────────────────────────────────────────────────

def test_stormcast_elenir():
    assert main.HaberSistemi._feed_baslik_gurultusu(
        'ISC Stormcast For Wednesday, September 9th, 2026')


def test_gercek_sans_haberi_elenmez():
    assert not main.HaberSistemi._feed_baslik_gurultusu(
        'Scans for Proxmox Servers, (Wed, Sep 9th)')


def test_eslesme_basta_aranir():
    """Podcast'ten BAHSEDEN gerçek haber elenmemeli."""
    assert not main.HaberSistemi._feed_baslik_gurultusu(
        'Attackers abused the ISC Stormcast feed to spread malware')


def test_bos_baslik_cokmez():
    assert not main.HaberSistemi._feed_baslik_gurultusu(None)
    assert not main.HaberSistemi._feed_baslik_gurultusu('')


# ── Düz metin payı ────────────────────────────────────────────────────────
# Değerler 2026-09-10 ham verisinden ölçüldü.

SANS_ISKELET = (
    '# [](https://isc.sans.edu/)[Internet Storm Center](https://isc.sans.edu/)\n'
    '[Sign In](https://isc.sans.edu/login.html)'
    '[Sign Up](https://isc.sans.edu/register.html)\n'
    'Handler on Duty: [Guy Bruneau](https://isc.sans.edu/handler_list.html)\n'
    'Threat Level: [green](https://isc.sans.edu/infocon.html)\n'
    '*   [previous](https://isc.sans.edu/diary/33321)\n'
)

MAKALE = ('CRPx0 is a cybercrime operation that started off operating a scam '
          'before pivoting into a fully-blown ransomware business. ') * 12


def test_iskelet_duz_metni_dusuk_cikar():
    assert (main.HaberSistemi._duz_metin_sayisi(SANS_ISKELET)
            < main.FEED_SUMMARY_MIN_WORDS)


def test_gercek_makale_duz_metni_esigi_gecer():
    assert (main.HaberSistemi._duz_metin_sayisi(MAKALE)
            >= main.FEED_SUMMARY_MIN_WORDS)


def test_baglantisi_yogun_ama_govdesi_gercek_bulten_gecer():
    """ANSSI/CERT-FR bültenleri navigasyon ağırlıklıdır ama gövdeleri
    gerçektir — eşik onları elememeli."""
    metin = ('Toggle navigation[![Logo](https://x/logo.svg)](https://x/)\n'
             '*   [Publications](https://x/avis/)\n' + MAKALE)
    assert (main.HaberSistemi._duz_metin_sayisi(metin)
            >= main.FEED_SUMMARY_MIN_WORDS)


# ── Proxy okuyucu kapısı (uçtan uca) ──────────────────────────────────────

def _proxy_sistem(donen_metin):
    s = main.HaberSistemi.__new__(main.HaberSistemi)
    s.headers = {}
    s._proxy_calls = 0
    s._proxy_seconds = 0.0

    class _R:
        status_code = 200
        text = donen_metin

    return s, _R


def test_proxy_iskelet_dondurunce_tam_metin_sayilmaz(monkeypatch):
    s, _R = _proxy_sistem('Markdown Content:' + SANS_ISKELET * 4)
    monkeypatch.setattr(main, 'ARTICLE_PROXY', 'https://r.example/{url}')
    monkeypatch.setattr(main, '_requests_get_with_retry',
                        lambda *a, **k: _R())
    art = {'link': 'https://isc.sans.edu/diary/rss/33322'}
    s._article_proxy_fallback(art, 'SANS ISC')
    assert not art.get('success'), 'sayfa iskeleti tam metin sayıldı'
    assert 'full_text' not in art
    assert s._proxy_calls == 1, 'harcanan proxy denemesi sayılmadı'


def test_proxy_gercek_makale_kabul_edilir(monkeypatch):
    s, _R = _proxy_sistem('Markdown Content:' + MAKALE)
    monkeypatch.setattr(main, 'ARTICLE_PROXY', 'https://r.example/{url}')
    monkeypatch.setattr(main, '_requests_get_with_retry',
                        lambda *a, **k: _R())
    art = {'link': 'https://example.com/makale'}
    s._article_proxy_fallback(art, 'Test Kaynak')
    assert art.get('success') and art.get('from_article_proxy')
