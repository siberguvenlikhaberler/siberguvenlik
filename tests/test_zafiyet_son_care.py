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



def test_guncelleme_etiketi_yalnizca_isaretli_mansete_ve_baslik_disinda():
    """2026-11-08: üç manşetin üçü de tekrardı; okura GÜNCELLEME olarak
    gösterilir. Etiket başlık div'ine girmez (arşiv başlığı okur)."""
    arts = [{'id': i, 'title': f'T{i}', 'link': 'https://ornek.test/x',
             'source': 'Kaynak', 'art_date': '2026-11-08', 'full_text': ''}
            for i in (1, 2, 3)]
    icerik = {i: {'tr_title': f'Başlık {i}', 'paragraph': 'Paragraf.'}
              for i in (1, 2, 3)}
    html = main.HaberSistemi._build_html(
        arts, [], [], icerik, '08 Kasım 2026', top3_ids=[1, 2, 3],
        guncelleme_ids={2})
    assert html.count('class="top3-guncelleme"') == 1
    import re
    basliklar = re.findall(r'class="top3-card-title">(.*?)</div>', html, re.S)
    assert not any('GÜNCELLEME' in b for b in basliklar)


def test_tekrar_ve_gelisme_ayri_etiket():
    arts = [{'id': i, 'title': f'T{i}', 'link': 'https://ornek.test/x',
             'source': 'Kaynak', 'art_date': '2026-11-08', 'full_text': ''}
            for i in (1, 2, 3)]
    icerik = {i: {'tr_title': f'Başlık {i}', 'paragraph': 'Paragraf.'}
              for i in (1, 2, 3)}
    html = main.HaberSistemi._build_html(
        arts, [], [], icerik, '08 Kasım 2026', top3_ids=[1, 2, 3],
        guncelleme_ids={1: 'gelisme', 3: 'tekrar'})
    assert html.count('🔄 GELİŞME') == 1 and html.count('↩️ TEKRAR') == 1


def test_tur_onceligi_deterministik_karar(monkeypatch):
    s, rec, vf = _kur()
    s._guncelleme_ids = {1, 2, 3}
    s._guncelleme_ipucu = {1: 'tekrar', 2: 'tekrar'}
    s._load_recent_report_views = lambda *a, **k: [{'tr_title': 'g'}]
    s._load_recent_kritik3_views = lambda *a, **k: []
    monkeypatch.setattr(main._olay, 'aday_anahtarlari', lambda v: {'k'})
    kararlar = {'Başlık 1': main._olay.GELISME, 'Başlık 2': main._olay.FARKLI,
                'Başlık 3': main._olay.FARKLI}
    monkeypatch.setattr(main._olay, 'mukerrer_karari',
                        lambda v, ev, **k: kararlar[v['tr_title']])
    icerik = {i: {'tr_title': f'Başlık {i}', 'paragraph': ''} for i in (1, 2, 3)}
    t = s._guncelleme_turleri([1, 2, 3], icerik, {})
    # 1: deterministik GELISME ipucunu ezer; 2: karar yok → ipucu;
    # 3: ne karar ne ipucu → gelisme (defter bağı yeni olgu yokluğunu kanıtlamaz)
    assert t == {1: 'gelisme', 2: 'tekrar', 3: 'gelisme'}
