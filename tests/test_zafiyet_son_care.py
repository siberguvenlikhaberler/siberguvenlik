"""ZAFİYET SON ÇARE (kullanıcı kararı, 2026-11-07 — KRITIK3_PLAN §9).

Mükerrer/tekrar bir manşetin yerine konacak TEMİZ siber-olay adayı kesin
olarak yoksa, en yüksek puanlı uygun zafiyet (≥70) manşete girer; en fazla bir
zafiyet; önce temiz haber (bant altı dahil). Başka her durumda zafiyet manşete
giremez.
"""
import main
from src import rapor_durumu

KAT = {1: 'stratejik_kurum_saldirisi', 2: 'politika_hukuk', 3: 'kolluk_operasyonu',
       10: 'zafiyet_rutin', 11: 'zafiyet_aktif_apt', 12: 'zafiyet_rutin',
       13: 'urun_icerik', 20: 'veri_ihlali'}
PUAN = {1: 94, 2: 90, 3: 86, 10: 76, 11: 89, 12: 59, 13: 95, 20: 40}
BASLIK = {1: 'Avrupa süpermarket soğutma saldırısı', 2: 'Japonya acil siber paket',
          3: 'FBI ajanı kripto hırsızlığı', 10: 'OpenSSH SSHole açığı istismarı',
          11: 'SonicWall SSL-VPN MFA atlatma', 12: 'GLPI ayrıcalık yükseltme',
          13: 'Yeni ürün duyurusu', 20: 'Küçük bir veri ihlali'}


def _kur(yasak=()):
    s = main.HaberSistemi.__new__(main.HaberSistemi)
    s._manset_yasak = set(yasak)
    s._zafiyet_son_care_ids = set()
    s._olay_sozlugu = None
    s._olay_defteri = None
    rec = {i: {'kat': KAT[i], 'toplam': PUAN[i], 'siber': 1} for i in KAT}
    vf = lambda i: {'tr_title': BASLIK[i], 'paragraph': BASLIK[i] + ' ayrıntı.',  # noqa: E731
                    'title': '', 'full_text': ''}
    return s, rec, vf


def test_s1_temiz_olay_yoksa_en_yuksek_uygun_zafiyet_girer():
    # 7 Kasım: SonicWall (89) tekrar → yasaklı; OpenSSH (76) girer.
    s, rec, vf = _kur(yasak={11})
    y = s._kritik3_yedek_bul([10, 11, 12, 13], [2, 3], rec, vf, [],
                             haric={1}, zafiyet_son_care=True)
    assert y == 10
    assert s._zafiyet_son_care_ids == {10}


def test_bayraksiz_cagri_zafiyeti_asla_almaz():
    s, rec, vf = _kur()
    assert s._kritik3_yedek_bul([10, 11, 12], [2, 3], rec, vf, [],
                                haric={1}) is None


def test_s2_zafiyet_de_uygun_degilse_bos_doner():
    s, rec, vf = _kur(yasak={10, 11})
    assert s._kritik3_yedek_bul([10, 11, 12, 13], [2, 3], rec, vf, [],
                                haric={1}, zafiyet_son_care=True) is None


def test_70_puan_esigi_ve_urun_icerik_hic_girmez():
    s, rec, vf = _kur(yasak={10, 11})
    # 12 (59 puan) eşik altı, 13 urun_icerik — ikisi de giremez.
    assert s._zafiyet_son_care_bul([12, 13], [2, 3], rec, vf) is None


def test_s3_once_temiz_haber_bant_alti_dahil():
    # 20 (40 puan) bandın altında ama TEMİZ siber olay → zafiyetten önce gelir.
    s, rec, vf = _kur()
    y = s._kritik3_yedek_bul([20, 10, 11], [2, 3], rec, vf, [], haric={1},
                             aday_puanlari={20: 40, 10: 76, 11: 89},
                             zafiyet_son_care=True)
    assert y == 20 and not s._zafiyet_son_care_ids


def test_s4_mansette_en_fazla_bir_zafiyet():
    s, rec, vf = _kur()
    assert s._zafiyet_son_care_bul([11], [10, 2], rec, vf) is None


def test_bekci_son_care_zafiyetini_ihlal_saymaz():
    istisna = {10}
    d = rapor_durumu.RaporDurumu(
        [2, 3, 10], [], [], kat_fn=lambda a: KAT[a],
        manset_disi_katlar=main.KRITIK3_HARIC_KATEGORILER,
        manset_istisna=istisna)
    d.senkronla('test', [2, 3, 10], [], [])
    assert not d.ihlaller
    d2 = rapor_durumu.RaporDurumu(
        [2, 3, 11], [], [], kat_fn=lambda a: KAT[a],
        manset_disi_katlar=main.KRITIK3_HARIC_KATEGORILER, manset_istisna=istisna)
    d2.senkronla('test', [2, 3, 11], [], [])
    assert d2.ihlaller, 'istisna dışındaki zafiyet manşeti yine ihlal olmalı'

