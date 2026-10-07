"""KRİTİK 3 GİRİŞ ARACISI — TEK UYGUNLUK YÜKLEMİ (P0, bkz. KRITIK3_PLAN.md).

"Bu aday manşete girebilir mi?" sorusu YEDİ ayrı yerde elle yanıtlanıyordu ve
her süzgeç FARKLI bir kapıyı atlıyordu. ÖLÇÜLDÜ (2026-10-07, son 31 gün):
93 yayımlanmış manşetin 8'i (%8,6) defterin "bu olay zaten manşet oldu"
dediği haberdi; kapı dağılımı dominans 3, çapraz-gün 2, ilk seçim 2,
yönetmen 1.

Yüklem ELEME yetkisi taşımaz, yalnızca TAKASIN adayını belirler; "KRİTİK 3
asla 2'ye düşmez" kuralı çağıranlarda kalır.
"""
import inspect

import main


ICERIK = {
    1: {'tr_title': 'LockBit Grubunun Berlin Eyalet Verilerini Sızdırması',
        'paragraph': 'LockBit grubu Berlin eyalet yönetiminden veri sızdırdı.'},
    2: {'tr_title': 'Osaka Üniversitesinde Fidye Yazılımı Saldırısı',
        'paragraph': 'Osaka Metropolitan Üniversitesi dersleri iptal etti.'},
    3: {'tr_title': 'Zbtlink Yönlendiricilerinde Fabrika Çıkışlı Arka Kapı',
        'paragraph': 'Yonlendiricilerde arka kapi tespit edilmistir.'},
    4: {'tr_title': 'LockBit Grubunun Yeni Kurban Listesi Yayımlaması',
        'paragraph': 'LockBit grubu yeni kurbanlarını duyurdu.'},
}
KAYITLAR = {
    1: {'kat': 'nation_state_apt', 'toplam': 90},
    2: {'kat': 'stratejik_kurum_saldirisi', 'toplam': 83},
    3: {'kat': 'zafiyet_rutin', 'toplam': 88},
    4: {'kat': 'nation_state_apt', 'toplam': 60},
}


def _sistem(**kw):
    s = main.HaberSistemi.__new__(main.HaberSistemi)
    for k, v in kw.items():
        setattr(s, k, v)
    return s


def _view_fn():
    return lambda aid: dict(ICERIK[aid], title='', full_text='')


def test_kapi_sirasi_sabit():
    """Kapı listesi ve SIRASI sözleşmedir; yeni kapı testi güncellemeye zorlar."""
    assert main.HaberSistemi.MANSET_UYGUNLUK_KAPILARI == (
        'kategori', 'yasak', 'defter_tekrari', 'capraz_gun',
        'ayni_gun_ayni_olay', 'cesitlilik', 'puan_bandi')


def test_temiz_aday_uygun():
    s = _sistem()
    uygun, neden = s._manset_uygun_mu(2, [1], KAYITLAR, _view_fn())
    assert uygun, neden


def test_zafiyet_kategorisi_reddedilir():
    s = _sistem()
    uygun, neden = s._manset_uygun_mu(3, [1], KAYITLAR, _view_fn())
    assert not uygun and 'kategori manşete uygun değil' in neden
    # Kategori etiketi KRITIK3_HARIC'te yoksa zafiyet kapısı YEDEKTİR
    # (`_manset_disi_ids` ile aynı sözleşme).
    s2 = _sistem()
    kayitlar = dict(KAYITLAR)
    kayitlar[3] = {'kat': 'zafiyet_aktif_apt', 'toplam': 88}
    assert not s2._manset_uygun_mu(3, [1], kayitlar, _view_fn())[0]


def test_manset_yasagi_reddedilir():
    s = _sistem(_manset_yasak={2})
    uygun, neden = s._manset_uygun_mu(2, [1], KAYITLAR, _view_fn())
    assert not uygun and 'mükerrer' in neden


def test_defter_tekrari_reddedilir():
    """10-07 Linux vakası: olay 3 Ekim'de manşet olmuştu."""
    class _Defter:
        def manset_gunu_sayisi(self, view):
            return 1 if 'Osaka' in (view.get('tr_title') or '') else 0
    s = _sistem(_olay_defteri=_Defter())
    uygun, neden = s._manset_uygun_mu(2, [1], KAYITLAR, _view_fn())
    assert not uygun and 'manşet oldu' in neden
    assert s._manset_uygun_mu(1, [2], KAYITLAR, _view_fn())[0]


def test_ayni_hat_reddedilir():
    """Aynı marka aktör iki manşette olamaz (çeşitlilik kapısı)."""
    s = _sistem()
    uygun, neden = s._manset_uygun_mu(4, [1], KAYITLAR, _view_fn())
    assert not uygun and 'aynı hat' in neden


def test_puan_bandi_reddedilir():
    s = _sistem()
    uygun, neden = s._manset_uygun_mu(
        4, [2], KAYITLAR, _view_fn(), bant_tavani=95)
    assert not uygun and 'puan bandı' in neden
    # Tavan verilmezse bant uygulanmaz.
    assert s._manset_uygun_mu(4, [2], KAYITLAR, _view_fn())[0]


def test_atla_yalnizca_belirtilen_kapiyi_kapatir():
    s = _sistem(_manset_yasak={2})
    assert not s._manset_uygun_mu(2, [1], KAYITLAR, _view_fn())[0]
    assert s._manset_uygun_mu(2, [1], KAYITLAR, _view_fn(),
                              atla=('yasak',))[0]


def test_aday_kendisiyle_karsilastirilmaz():
    """Aday zaten manşetteyse (yerinde doğrulama) kendisi engel olmaz."""
    s = _sistem()
    assert s._manset_uygun_mu(1, [1, 2], KAYITLAR, _view_fn())[0]


def test_hat_tanimi_tek_yerde():
    """`_manset_hatti` TEK tanımdır; çeşitlilik katmanı kopya tutmamalı."""
    kaynak = inspect.getsource(main.HaberSistemi._manset_uygun_mu)
    assert '_manset_hatti' in kaynak
    hat = inspect.getsource(main.HaberSistemi._manset_hatti)
    govde = hat.split('"""')[-1]          # docstring'den SONRASI = kod
    assert 'kod:' not in govde, 'kod adı hatta BİLEREK girmez (SpyCloud)'


def test_yuklem_llm_cagrisi_yapmaz():
    """Giriş aracısı da maliyet nötrdür."""
    kod = [l for l in inspect.getsource(
        main.HaberSistemi._manset_uygun_mu).splitlines()
        if l.strip() and not l.strip().startswith('#')]
    for cagri in ('_gemini_call', '_llm.', 'genai'):
        assert cagri not in '\n'.join(kod), cagri
