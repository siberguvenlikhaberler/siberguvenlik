"""KRİTİK 3 İÇ SIRASI — stratejik ağırlık, sonra puan.

ÖLÇÜLDÜ (2026-09-10): manşetin ilk sırasında Brezilya hükümet sunucularının
kimlik avı barındırması (90, stratejik_kurum_saldirisi) vardı; günün en
stratejik haberi olan dört Çin devlet grubunun ortak sıfır gün istismar kiti
(97, nation_state_apt) ÜÇÜNCÜ sıradaydı. 2026-09-09'da sıra puanla da ters
düşmüştü (85, 93, 97).

Kök neden: manşetin SEÇİMİ üzerine çok katman vardı ama SIRASI hiçbir yerde
belirlenmiyordu — katmanların listeye dokunma sırasından artakalıyordu.
"""
import main


def _sistem():
    return main.HaberSistemi.__new__(main.HaberSistemi)


def test_10_eylul_sirasi_duzelir():
    s = _sistem()
    records = {
        # (gerçek 2026-09-10 manşeti, yayımlanan sırayla)
        90: {'kat': 'stratejik_kurum_saldirisi', 'toplam': 90},   # Brezilya
        97: {'kat': 'kolluk_operasyonu',         'toplam': 97},   # Xinbi
        37: {'kat': 'nation_state_apt',          'toplam': 97},   # Çin/BlueMoon
    }
    assert s._kritik3_sirala([90, 97, 37], records) == [37, 90, 97]


def test_esit_kategoride_puan_belirler():
    s = _sistem()
    records = {
        1: {'kat': 'nation_state_apt', 'toplam': 85},
        2: {'kat': 'nation_state_apt', 'toplam': 97},
        3: {'kat': 'nation_state_apt', 'toplam': 91},
    }
    assert s._kritik3_sirala([1, 2, 3], records) == [2, 3, 1]


def test_secimi_degistirmez():
    """Sıralama yalnızca dizer; hiçbir haberi düşürmez ya da eklemez."""
    s = _sistem()
    records = {
        1: {'kat': 'kolluk_operasyonu', 'toplam': 99},
        2: {'kat': 'politika_hukuk',    'toplam': 70},
        3: {'kat': 'veri_ihlali',       'toplam': 80},
    }
    assert sorted(s._kritik3_sirala([1, 2, 3], records)) == [1, 2, 3]


def test_bilinmeyen_kategori_en_sona_dusmez_puanla_dizilir():
    """Kayıtsız/bilinmeyen kategori 0 önceliğe düşer ama akış kırılmaz."""
    s = _sistem()
    records = {
        1: {'kat': 'bilinmeyen', 'toplam': 95},
        2: {'kat': 'politika_hukuk', 'toplam': 60},
    }
    assert s._kritik3_sirala([1, 2], records) == [2, 1]


def test_eksik_kayit_cokmez():
    s = _sistem()
    assert s._kritik3_sirala([5, 6], {}) == [5, 6]
