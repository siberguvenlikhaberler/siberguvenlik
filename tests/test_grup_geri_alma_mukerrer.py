"""GRUP GERİ ALMA — çapası raporda duran haber geri ALINMAZ.

ÖLÇÜLDÜ (2026-09-10): Proofpoint'in BlueMoon sıfır-gün kiti olayının altı
kopyası vardı. Çapa ID 84 (99 puan) gövdede DURURKEN `_restore_orphaned_groups`
ID 37'yi geri aldı; rapor aynı olayı hem KRİTİK 3'te hem gövdede yayımladı ve
iki metin kampanya başlangıcını farklı verdi (Ağustos 2026 / Ağustos 2024).

Kök neden: geri alma, mükerrer ilişkisini tek bir `ayni_olay` çağrısıyla
SIFIRDAN türetiyordu; oysa ilişki daha önceki katmanlarda ZATEN kurulmuştu.
"""
import main


def _sistem():
    s = main.HaberSistemi.__new__(main.HaberSistemi)
    s._olay_sozlugu = None
    s._mukerrer_capa = {}
    return s


# Metinler bilerek FARKLI sözcüklerle yazıldı: deterministik `ayni_olay`
# kaçırsa bile çapa kaydı ilişkiyi taşımalı.
_VIEWS = {
    84: {'tr_title': 'Çin Bağlantılı Grupların Chrome Sıfır Gün Açığını Kullanması',
         'paragraph': 'Proofpoint, TA412 dahil dört casusluk grubunun BlueMoon '
                      'istismar kitiyle Chrome sıfır gün açığını kullandığını '
                      'tespit etmiştir.',
         'title': '', 'full_text': ''},
    37: {'tr_title': 'Üçlü Zincir Üzerinden Yürütülen Casusluk Faaliyetleri',
         'paragraph': 'Devlet bağlantılı aktörlerin tarayıcı ve işletim sistemi '
                      'zafiyetlerini birleştirerek hedef kurumlara sızdığı '
                      'bildirilmiştir.',
         'title': '', 'full_text': ''},
    44: {'tr_title': 'Yeni Nesil İstismar Kitinin Ortaya Çıkması',
         'paragraph': 'Araştırmacılar, BlueMoon adlı kitin Chrome ve Windows '
                      'zafiyetlerini hedef aldığını açıklamıştır.',
         'title': '', 'full_text': ''},
}
_view_fn = _VIEWS.get
_PUANLAR = {84: {'toplam': 99}, 37: {'toplam': 97}, 44: {'toplam': 97}}


def test_capasi_raporda_duran_haber_geri_alinmaz():
    s = _sistem()
    # Önceki katmanlar 37 ve 44'ü 84'ün mükerreri saymıştı.
    s._mukerrer_capa_kaydet(37, 84)
    s._mukerrer_capa_kaydet(44, 84)

    # 84 gövdede DURUYOR; 37 ve 44 elendi.
    _, restored = s._restore_orphaned_groups(
        candidates_before=[84, 37, 44], kept_ids=[84], top3_ids=[],
        view_fn=_view_fn, score_records=_PUANLAR)

    assert restored == [], f"çapası raporda dururken geri alındı: {restored}"


def test_capa_zinciri_dolayli_temsili_de_gorur():
    """37 → 44 → 84 zinciri: 84 rapordaysa 37 de temsil ediliyordur."""
    s = _sistem()
    s._mukerrer_capa_kaydet(37, 44)
    s._mukerrer_capa_kaydet(44, 84)

    _, restored = s._restore_orphaned_groups(
        candidates_before=[84, 37, 44], kept_ids=[84], top3_ids=[],
        view_fn=_view_fn, score_records=_PUANLAR)

    assert restored == [], f"dolaylı çapa görülmedi: {restored}"


def test_capa_da_elendiyse_grup_bosalmasi_korunur():
    """Asıl koruma bozulmamalı: olayın TÜM kopyaları düştüyse en yüksek
    puanlı haber gövdeye geri döner."""
    s = _sistem()
    s._mukerrer_capa_kaydet(37, 84)
    s._mukerrer_capa_kaydet(44, 84)

    _, restored = s._restore_orphaned_groups(
        candidates_before=[84, 37, 44], kept_ids=[], top3_ids=[],
        view_fn=_view_fn, score_records=_PUANLAR)

    assert restored == [84], f"grup boşalması korunmadı: {restored}"


def test_capa_kaydi_dongude_takilmaz():
    s = _sistem()
    s._mukerrer_capa_kaydet(37, 44)
    s._mukerrer_capa_kaydet(44, 37)
    assert 37 not in s._mukerrer_capa_zinciri(37)


def test_kendine_capa_kaydedilmez():
    s = _sistem()
    s._mukerrer_capa_kaydet(84, 84)
    assert s._mukerrer_capa_zinciri(84) == []
