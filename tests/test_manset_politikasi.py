"""MANŞET POLİTİKASI — 2026-08-12 regresyonunun kapısı.

O gün ne oldu: günün 2. (96 puan, İran'ın ABD su altyapısına saldırısı) ve
3. (92 puan, Sandworm/UAC-0145) en yüksek puanlı haberleri KRİTİK 3'e
giremedi; yerlerine 90 puanlı iki haber girdi.

İki ayrı sebep vardı ve ikisi de aynı kök nedene bağlıydı — 'mukerrer' tek
bitinin üç durumu karıştırması:
  • İran haberi mukerrer=1 yedi (aslında YENİ gelişme: yeni eyaletler) ve
    manşet kapısı bayrağa baktığı için elendi.
  • Sandworm haberi mukerrer=0'dı; onu bir LLM manşet katmanı düşürdü
    (dünkü Polonya sabotajıyla ortak olan tek şey AKTÖRDÜ).

Bu dosya politikanın deterministik yarısını kapıya bağlar: aynı girdilerle
manşet havuzunun doğru üç haberi üretmesi gerekir. Fikstür o günün GERÇEK
adaylarını, skorlarını ve önceki 7 günün geçmişini taşır.
"""
import json
import os

import pytest

from src import dedup as _dedup
from src import olay_iliski as oi

FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures',
                       'manset_2026_08_12.json')

# main.HaberSistemi.MANSET_TEKRAR_SINIRI ile aynı olmalı.
MANSET_TEKRAR_SINIRI = 1


@pytest.fixture(scope='module')
def fx():
    with open(FIXTURE, encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture(scope='module')
def baglam(fx):
    """(sozluk, defter, gecmis_views) — üretimdeki kurulumun aynısı."""
    tum = [v for g in fx['gecmis'] for v in g['views']]
    sozluk = oi.OlaySozlugu(tum)
    defter = oi.defter_kur(
        [(g['gun'], g['views'], g['manset']) for g in fx['gecmis']],
        sozluk=sozluk)
    gecmis = [v for g in fx['gecmis'] for v in g['views']]
    return sozluk, defter, gecmis


def _gercek_mukerrer(view, gecmis, sozluk):
    return any(oi.iliski_belirle(view, ev, sozluk=sozluk) == oi.AYNI_GELISME
               for ev in gecmis)


def _manset_havuzu(fx, baglam):
    """Politikanın uyguladığı manşet havuzu (puan sırasında)."""
    sozluk, defter, gecmis = baglam
    havuz = []
    for a in sorted(fx['adaylar'], key=lambda x: -x['puan']):
        # (a) gerçek mükerrer mi? — yalnızca skorlayıcı bayrak koyduysa bakılır
        if a['mukerrer'] and _gercek_mukerrer(a['view'], gecmis, sozluk):
            continue
        # (b) bu olay son günlerde zaten manşet oldu mu?
        if defter.manset_gunu_sayisi(a['view']) >= MANSET_TEKRAR_SINIRI:
            continue
        havuz.append(a)
    return havuz


def test_manset_en_yuksek_puanli_uc_ayrik_olayi_secer(fx, baglam):
    """Beklenen sonuç: 97, 96, 92 — üretimde 97, 90, 90 çıkmıştı."""
    sozluk, defter, gecmis = baglam
    havuz = _manset_havuzu(fx, baglam)
    by_id = {a['id']: a for a in fx['adaylar']}
    manset_gecmisi = [v for g in fx['gecmis'] for v in g['manset']]
    secilen = _dedup.pick_distinct(
        [a['id'] for a in havuz], lambda i: by_id[i]['view'],
        n=3, exclude_views=manset_gecmisi)
    puanlar = [by_id[i]['puan'] for i in secilen]
    assert puanlar == [97, 96, 92], (
        f'manşet puanları {puanlar}; seçilenler: '
        + ' | '.join(by_id[i]['baslik'][:55] for i in secilen))


def test_iran_su_altyapisi_manşete_cikabilir(fx, baglam):
    """YENİ gelişme (yeni eyaletler) manşet yasağı YEMEMELİ."""
    sozluk, defter, gecmis = baglam
    iran = next(a for a in fx['adaylar'] if 'Iran-Linked' in a['baslik'])
    assert iran['mukerrer'] == 1, 'fikstür bozulmuş: bayrak beklenen gibi değil'
    assert not _gercek_mukerrer(iran['view'], gecmis, sozluk), (
        'İran su altyapısı haberi gerçek mükerrer sayıldı — YENİ eyaletler '
        'bildiriyor')
    assert iran['id'] in [a['id'] for a in _manset_havuzu(fx, baglam)]


def test_sandworm_ayni_aktor_yuzunden_dusmez(fx, baglam):
    """Dünkü manşetle ortak olan tek şey AKTÖRSE manşet geçmişi devralınmaz."""
    sozluk, defter, gecmis = baglam
    sw = next(a for a in fx['adaylar'] if 'Sandworm-Linked UAC' in a['baslik'])
    assert defter.manset_gunu_sayisi(sw['view']) == 0, (
        'Sandworm/UAC-0145, dünkü Sandworm/Polonya manşetinin geçmişini '
        'devraldı — aktör adı olay kimliği sayılıyor')
    assert sw['id'] in [a['id'] for a in _manset_havuzu(fx, baglam)]


def test_gercek_mukerrerler_hala_elenir(fx, baglam):
    """Politika gevşemesi gerçek mükerreri kaçırmamalı (Gunra, Head Mare)."""
    sozluk, defter, gecmis = baglam
    havuz_ids = {a['id'] for a in _manset_havuzu(fx, baglam)}
    for parca in ('Gunra Ransomware Exploits', 'Head Mare APT'):
        aday = next(a for a in fx['adaylar'] if parca in a['baslik'])
        assert aday['id'] not in havuz_ids, (
            f'{parca}: gerçek mükerrer manşet havuzuna girdi')


def test_uretimdeki_sonuc_gercekten_hataliydi(fx):
    """Fikstürün taşıdığı üretim sonucu, düzeltilen hatayı gösteriyor olmalı."""
    assert sorted(fx['uretimdeki_kritik3']) == [90, 90, 97]


def test_manset_gecmisi_sorgusu_tek_ortak_kimlikle_eslesir():
    """Defterin manşet sorgusu, gövde elemesinden GEVŞEK olmalı.

    ÖLÇÜLDÜ (2026-08-21): "Kritik Altyapılardaki Siemens PLC Cihazlarının
    Yapay Zekayla Hedeflenmesi" (08-20 manşeti) ile "ABD Kurumlarının Siemens
    S7 PLC Cihazlarına Yönelik Yapay Zeka Destekli Saldırı Uyarısı" (08-21)
    aynı olaydır, ama paylaşılan tek düşük dereceli kimlik (ad:siemens)
    MIN_ORTAK_AD=2 eşiğini geçmediği için defter ILISKISIZ dedi ve haber üst
    üste iki gün manşet oldu.

    Maliyet asimetriktir: yanlış pozitif bir manşet yuvasını başka habere
    bırakır (telafi edilebilir), yanlış negatif üst üste aynı manşet demektir.
    """
    from src import olay_iliski as _olay

    dun = {'tr_title': 'Kritik Altyapılardaki Siemens PLC Cihazlarının Yapay '
                       'Zekayla Hedeflenmesi',
           'title': 'US warns of AI-powered attacks on Siemens PLCs',
           'paragraph': 'NSA, CISA, FBI, EPA ve DOE, Amerika Birleşik '
                        'Devletleri\'ndeki kritik altyapı kuruluşlarını Siemens '
                        'programlanabilir mantık denetleyicilerine (PLC) yönelik '
                        'siber saldırılar konusunda uyarmıştır. Kimliği belirsiz '
                        'tehdit aktörlerinin internete açık S7 serisi cihazları '
                        'tespit ettiği belirtilmiştir.',
           'full_text': ''}
    bugun = {'tr_title': 'ABD Kurumlarının Siemens S7 PLC Cihazlarına Yönelik '
                         'Yapay Zeka Destekli Saldırı Uyarısı',
             'title': 'AI-Generated Exploit Scripts Target Siemens S7 PLCs',
             'paragraph': 'NSA, CISA, FBI, DOE ve EPA tarafından yayımlanan '
                          'ortak bildiride, ABD\'deki kritik altyapı '
                          'kuruluşlarının yapay zeka destekli kötü amaçlı '
                          'yazılım betikleriyle hedef alındığı duyurulmuştur. '
                          'Siber saldırganlar, Siemens S7-200, 300, 400, 1200 ve '
                          '1500 serisi programlanabilir mantık '
                          'denetleyicilerini (PLC) hedef alarak Python tabanlı '
                          'saldırı kodları geliştirmektedir.',
             'full_text': ''}
    alakasiz = {'tr_title': 'Manic Zararlısının Çevrimdışı Cihazlardan Veri '
                            'Sızdırması',
                'title': 'Manic Android Malware Exfiltrates Data',
                'paragraph': 'Manic zararlısı çevrimdışı Android cihazlardan '
                             'mesh ağı üzerinden veri sızdırmaktadır.',
                'full_text': ''}

    defter = _olay.defter_kur([('2026-08-20', [dun], [dun])])
    assert defter.manset_gunu_sayisi(bugun) >= 1, \
        'dün manşet olan olay bugün manşet geçmişsiz görünüyor'
    assert defter.son_manset_gunu(bugun) == '2026-08-20'
    assert defter.manset_gunu_sayisi(alakasiz) == 0, \
        'ilgisiz haber manşet geçmişine bağlandı (fazla gevşek)'


def test_manset_sorgusu_govde_politikasini_degistirmez():
    """Gevşetme YALNIZCA manşet geçmişi sorgusundadır; dört değerli
    sınıflandırıcı (gövde elemesinin dayanağı) aynı kalmalıdır."""
    from src import olay_iliski as _olay
    a = {'tr_title': 'Siemens PLC Cihazlarının Hedeflenmesi', 'title': 'x',
         'paragraph': 'Siemens denetleyicileri hedef alınmıştır.',
         'full_text': ''}
    b = {'tr_title': 'Siemens Ürünlerinde Yama Yayımlanması', 'title': 'y',
         'paragraph': 'Siemens ürünleri için güncelleme yayımlanmıştır.',
         'full_text': ''}
    iliski, _ = _olay.iliski_belirle(a, b, explain=True)
    assert iliski in _olay.ILISKILER, 'sınıflandırıcı sözleşmesi bozuldu'


def test_manset_yasagi_havuzu_ackta_birakmaz():
    """Gevşetme DAR olmalı: tek ortak kimlik + zayıf konu desteği yetmez.

    İlk sürüm eşiği KIMLIK_ILE_KONU_MIN'e (0.10) bağladı; o değer İKİ ortak
    kimlik varsayar. ÖLÇÜLDÜ (2026-08-21, 38 haberlik rapor): 0.10'da 38
    haberin 12'si manşete yasaklandı ve havuz açlıktan zayıf haberlere düştü
    (86 puanlı bir zafiyet duyurusu manşet oldu, 94 puanlı iki haber gövdede
    kaldı). 0.25'te yalnızca gerçek tekrar (Siemens) yasaklanıyor.
    """
    from src import olay_iliski as _olay
    assert _olay.MANSET_TEK_KIMLIK_KONU >= 0.20, \
        'tek kimlik eşiği fazla gevşek — manşet havuzu açlığa düşer'

    gecmis = {'tr_title': 'Kritik Altyapılardaki Siemens PLC Cihazlarının Yapay '
                          'Zekayla Hedeflenmesi',
              'title': 'US warns of AI-powered attacks on Siemens PLCs',
              'paragraph': 'NSA, CISA, FBI, EPA ve DOE, ABD\'deki kritik altyapı '
                           'kuruluşlarını Siemens programlanabilir mantık '
                           'denetleyicilerine (PLC) yönelik siber saldırılar '
                           'konusunda uyarmıştır. İnternete açık S7 serisi '
                           'cihazlar hedeftedir.',
              'full_text': ''}
    # Aynı geçmiş kayıtla YALNIZCA bir jenerik ortaklık taşıyan, konuca uzak
    # bir haber yasaklanmamalı.
    uzak = {'tr_title': 'Bir Sağlık Kuruluşunda Fidye Yazılımı Saldırısı',
            'title': 'Ransomware hits healthcare provider',
            'paragraph': 'Bir sağlık kuruluşu fidye yazılımı saldırısı sonrası '
                         'hasta kayıtlarının sızdırıldığını bildirmiştir.',
            'full_text': ''}
    defter = _olay.defter_kur([('2026-08-20', [gecmis], [gecmis])])
    assert defter.manset_gunu_sayisi(uzak) == 0, \
        'konuca uzak haber manşet geçmişine bağlandı'


def test_kurum_adi_stratejik_etiketi_hak_ettirmez_kurali_var():
    """Skorlama ve Critique promptları bu ayrımı AÇIKÇA söylemeli.

    ÖLÇÜLDÜ (2026-08-21): Cycode araştırmacılarının NASA'nın AMMOS/AIT-GUI
    yazılımında bulduğu açıklar `stratejik_kurum_saldirisi` etiketiyle 91 puan
    aldı ve KRİTİK 3'e çıktı — ortada saldırı, saldırgan ve kurban yoktu.
    Doğru etiketle (zafiyet_rutin, KRITIK3_HARIC_KATEGORILER içinde) manşete
    zaten çıkamazdı.
    """
    from src import config
    skor = config.get_scoring_prompt('x') if hasattr(config, 'get_scoring_prompt') \
        else ''
    metinler = [skor, config.get_critique_prompt('x')]
    for metin in metinler:
        if not metin:
            continue
        assert 'KURUM ADI ETİKET YAPMAZ' in metin or \
               'ARAŞTIRMACILARIN bulduğu açık' in metin, \
            'kurum adı → stratejik etiket ayrımı prompta girmemiş'


def test_manset_capraz_gun_karsilastirmasi_tum_raporu_kapsar():
    """Manşet seçicisi geçmişi SON 7 GÜNÜN TÜM RAPORU üzerinden görmeli.

    Eski sürüm yalnızca eski MANŞETLERE bakıyordu: bir olay üç gün önce
    GÖVDEDE yayımlandıysa bugün manşet olmasını hiçbir deterministik katman
    engellemiyordu (gövde çapraz-gün elemesi manşeti kapsam dışı bırakır).

    ÖLÇÜLDÜ — iki manşet arka arkaya bu boşluktan geçti:
      2026-08-23  ToxicPanda (08-21 raporunda vardı)
      2026-08-24  Threema DDoS (08-17 raporunda vardı)
    """
    import inspect
    import main
    kaynak = inspect.getsource(main.HaberSistemi._derive_top3_by_score)
    assert '_load_recent_report_views()' in kaynak, \
        'manşet seçicisi tam rapor geçmişini görmüyor — çapraz-gün kaçağı riski'
    assert '_load_recent_kritik3_views()' in kaynak, \
        'manşet geçmişi karşılaştırmadan çıkmış'


def test_auditorun_manset_reddi_kalicidir():
    """Auditor "manşetlik değil" dediği haber yedek olarak geri gelmemeli.

    ÖLÇÜLDÜ (2026-08-25): Auditor "ABD'de yaşlıları dolandıran şebeke"
    haberini "siber güvenlik olayı değil" gerekçesiyle manşetten çıkardı;
    birkaç katman sonra SON KAPI aynı haberi yedek olarak geri getirdi ve
    63 puanla manşette kaldı.
    """
    import inspect
    import main
    kaynak = inspect.getsource(main.HaberSistemi._audit_kritik3_selection)
    # Yazım artık ARACIDAN geçer (bkz. tests/test_manset_araci.py): katman
    # kalıcı tabloda olmalı ve yasağı aracı koymalı.
    assert '_manset_yasagi_koy' in kaynak, \
        'Auditor manşet reddi hiçbir yere yazılmıyor — yedek olarak geri gelir'
    assert 'auditor_manset_secimi' in main.HaberSistemi.MANSET_KALICI_KATMAN


def test_yedek_bulucu_puan_bandi_uygular():
    """Puan bandı yalnızca LLM seçiminde değil, YEDEK seçiminde de geçerli.

    ÖLÇÜLDÜ (2026-08-25): 44 puanlık "Weedhack zararlısının sahte Minecraft
    istemcileri üzerinden yayılması" haberi manşet oldu; aynı raporda 96
    puanlı İran yaptırımı manşetteydi.
    """
    import inspect
    import main
    kaynak = inspect.getsource(main.HaberSistemi._kritik3_yedek_bul)
    # Bant artık tek yüklemde (P1): bulucu yüklemi çağırır, bant oradadır.
    assert '_manset_uygun_mu' in kaynak, 'yedek bulucu yüklemi çağırmıyor'
    assert 'MANSET_PUAN_TOLERANSI' in inspect.getsource(
        main.HaberSistemi._manset_uygun_mu), 'yüklemde puan bandı yok'
    assert 'sorted(aday_ids' in kaynak, 'yedek havuzu puan sırasında taranmıyor'


def test_denetim_kapsami_etki_operasyonlarini_dislamaz():
    """"Siber güvenlik haberi değil" kuralı DAR okunmamalı.

    ÖLÇÜLDÜ (2026-08-27): denetim, OpenAI'nın Rusya bağlantılı etki operasyonu
    hesaplarını kapatmasını (85 puan, nation_state_apt) "siber saldırı değil,
    dezenformasyon amaçlı hesap kapatma" diyerek manşetten çıkardı. Bu bir
    SEÇİM reddi olduğu için haberi manşete KALICI olarak kapatıyor; oysa
    devlet bağlantılı bilgi harbi operasyonlarının ifşası siber güvenlik
    haberidir. Prompt kapsamı hiç tanımlamadığı için model "saldırı var mı"
    diye okumuştu.
    """
    from src.config import get_kritik3_selection_audit_prompt
    p = get_kritik3_selection_audit_prompt('m', 'g')
    for parca in ('ETKİ/DEZENFORMASYON', 'yapay zekâ', 'Yaptırım',
                  'DEVLET EYLEMLERİ', 'Kritik altyapı'):
        assert parca in p, f'denetim kapsamında {parca} tanımlı değil'
    assert 'somut bir gelişme mi' in p, \
        'ölçüt "saldırı var mı" olmaktan çıkarılmamış'


def test_zafiyet_haberi_manset_olamaz():
    """ZAFİYET HABERİ KRİTİK 3'E GİRMEZ — İSTİSNASIZ (kullanıcı kararı,
    2026-09-28).

    Eski kural `zafiyet_aktif_apt`ı serbest bırakıyordu ("aktif istismar +
    APT atfı varsa manşet olabilir"). ÖLÇÜLEN SONUÇ (2026-09-27): Oracle
    PeopleSoft açığının istismarı (92) KRİTİK 3'e girdi — üstelik LLM
    mükerrer hakemi onu mükerrer saymışken — ve atıfsız ama YAMASIZ, vahşi
    doğada istismar edilen iki Citrix NetScaler sıfır-günü (88) gövdede
    kaldı. Kısıt artık hem editoryal hem MEKANİK doldurmada geçerlidir;
    kategori `KRITIK3_HARIC_KATEGORILER` içindedir.
    """
    import main
    s = main.HaberSistemi.__new__(main.HaberSistemi)
    s._olay_defteri = None
    s._manset_yasak = set()
    kayit = {1: {'kat': 'zafiyet_aktif_apt', 'toplam': 89},
             2: {'kat': 'politika_hukuk', 'toplam': 75}}
    vf = lambda aid: {'tr_title': f'H{aid}', 'title': '',
                      'paragraph': '', 'full_text': ''}
    for yonetmen in (True, False):
        assert 1 in s._manset_disi_ids([1, 2], kayit, vf, yonetmen=yonetmen), \
            f'zafiyet haberi manşet havuzunda (yonetmen={yonetmen})'
        assert 2 not in s._manset_disi_ids([1, 2], kayit, vf,
                                           yonetmen=yonetmen)


def test_zafiyet_kategorileri_kritik3_disidir():
    from src.config import KRITIK3_HARIC_KATEGORILER, ZAFIYET_KATEGORILERI
    assert ZAFIYET_KATEGORILERI <= KRITIK3_HARIC_KATEGORILER


def test_son_kapi_mekanik_kisit_kullanir():
    """Kanca yerinde mi — son kapı `yonetmen=False` ile çağırmalı."""
    import inspect
    import main
    kaynak = inspect.getsource(main.HaberSistemi._son_mukerrer_kapisi)
    assert 'yonetmen=False' in kaynak, \
        'son kapı yönetmene özel kısıtı mekanik doldurmaya uyguluyor'


def test_tersinelik_alarmi_gurultuyu_susturur_gercegi_bildirir():
    """Alarm ancak SUSABİLDİĞİNDE bilgi taşır.

    Eşik yokken 1 puanlık fark bile alarm üretiyordu. ÖLÇÜLDÜ
    (kalite_denetim.jsonl, 38 satır): dağılım iki kutuplu — gerçek
    tersinelikler 14-45 puan, gürültü 1-7 puan. 10 puanlık eşik ikisini temiz
    ayırıyor; 08-28'deki PaperCut hatasını (89↔75, 14 puan) bu alarm
    yakalatmıştı, o eşiğin üstünde kalmalı.
    """
    import main
    esik = main.HaberSistemi.MANSET_TERSINELIK_MIN
    assert 8 <= esik <= 14, f'eşik ölçülen aralığın dışında: {esik}'
    # 08-28 gerçek bulgusu bildirilmeye devam etmeli
    assert 89 - 75 >= esik, 'gerçek tersinelik eşiğin altında kalıyor'
    # 09-02 gürültüsü susmalı
    for gurultu in (1, 2, 5, 7):
        assert gurultu < esik, f'{gurultu} puanlık gürültü hâlâ alarm üretiyor'


def test_tersinelik_esigi_kodda_uygulaniyor():
    import inspect
    import main
    kaynak = inspect.getsource(main.HaberSistemi._kalite_denetimi_yaz)
    assert 'MANSET_TERSINELIK_MIN' in kaynak, \
        'tersinelik alarmı eşiği kullanmıyor'


def _cv(tr, para, tam=''):
    return {'tr_title': tr, 'paragraph': para, 'title': '', 'full_text': tam}


def _sistem(kayit, views):
    import main
    s = main.HaberSistemi.__new__(main.HaberSistemi)
    s._olay_defteri = None
    s._olay_sozlugu = None
    s._manset_yasak = set()
    s._manset_karar = []
    s._dedup_view_fn = lambda *a, **k: (lambda aid: views[aid])
    s._enforce_kritik3_paragraph_length = lambda *a, **k: None
    s._manset_karar_kaydet = lambda *a, **k: s._manset_karar.append(a)
    return s


def test_ayni_hattin_iki_haberi_manset_olmaz():
    """ÖLÇÜLEN VAKA (2026-09-29): FBI ihlali (93, stratejik_kurum_saldirisi)
    ile Hollanda'daki ShinyHunters yakalaması (94, kolluk_operasyonu) aynı
    gün manşetti. Kategori ağırlığı düşük olan iner — saf puan KÖK OLAYI
    düşürürdü."""
    views = {
        1: _cv('FBI Personel Verilerinin Ele Geçirilmesi',
               "ShinyHunters grubu FBI'a ait veri tabanını ihlal etmiştir."),
        2: _cv("Hollanda'da ShinyHunters Bağlantılı Yakalama",
               'Hollanda polisi ShinyHunters soruşturmasında bir şüpheliyi '
               'yakalamıştır.'),
        3: _cv('Renfe Demiryolu Ağına Siber Saldırı',
               'İspanya ulusal demiryolu işletmesi Renfe saldırıya uğradı.'),
        4: _cv('Çin Bağlantılı Grubun NeedyMantis Kampanyası',
               'NeedyMantis zararlısıyla uzun süreli erişim sağlanmıştır.'),
    }
    kayit = {1: {'kat': 'stratejik_kurum_saldirisi', 'toplam': 93},
             2: {'kat': 'kolluk_operasyonu', 'toplam': 94},
             3: {'kat': 'stratejik_kurum_saldirisi', 'toplam': 90},
             4: {'kat': 'tedarik_zinciri', 'toplam': 93}}
    s = _sistem(kayit, views)
    top3, top10, kalan = s._kritik3_cesitlilik(
        [1, 2, 3], [4], [], kayit, {}, {}, [])
    assert 2 not in top3, 'aynı hattın ikinci haberi manşette kaldı'
    assert 1 in top3, 'kök olay (kategori ağırlığı yüksek) inmiş'
    assert 4 in top3, 'temiz aday manşete çıkmadı'
    assert len(top3) == 3, 'KRİTİK 3 eksildi'
    assert 2 in top10, 'inen haber gövdeye alınmadı'


def test_temiz_aday_yoksa_manset_eksilmez():
    views = {
        1: _cv('LockBit Acme Saldırısı', 'LockBit Acme ağını şifreledi.'),
        2: _cv('LockBit Beta Saldırısı', 'LockBit Beta ağını şifreledi.'),
        3: _cv('Bağımsız Haber', 'İlgisiz bir olay yaşanmıştır.'),
    }
    kayit = {1: {'kat': 'veri_ihlali', 'toplam': 80},
             2: {'kat': 'veri_ihlali', 'toplam': 75},
             3: {'kat': 'politika_hukuk', 'toplam': 70}}
    s = _sistem(kayit, views)
    top3, _, _ = s._kritik3_cesitlilik([1, 2, 3], [], [], kayit, {}, {}, [])
    assert len(top3) == 3 and set(top3) == {1, 2, 3}


def test_manset_sirasi_kaydi_onceligi_de_yazar():
    """SIRA KENDİNİ AÇIKLAMALI (2026-10-08).

    `_kritik3_sirala` sırayı ETKİN öncelikle (`_kat_oncelik`) dizer: atıfı
    doğrulanmamış bir `nation_state_apt` iddiası önceliğini 10'dan 4'e
    kaybeder. Kalite kaydı yalnızca puanı tutuyordu ve 8 Ekim raporu
    (90/80/**97**) adli incelemede "sıra uygulanmamış" diye okundu — oysa
    97 puanlı haber `apt_dogrulanmadi=1` taşıdığı için üçüncüydü, kural
    doğru çalışmıştı. Arşivden kategori okuyup yeniden hesaplamak da
    yanıltır: arşiv atıf bayrağını taşımaz, bu yüzden kayıt taşımalı."""
    import inspect
    import main as uretim
    kaynak = inspect.getsource(uretim.HaberSistemi._kalite_denetimi_yaz)
    parca = kaynak.split("'manset_sirasi'", 1)[1][:700]
    for alan in ("'kat'", "'oncelik'", "'apt_dogrulanmadi'"):
        assert alan in parca, f'manşet sırası kaydında {alan} yok'
    assert '_kat_oncelik(' in parca, \
        'öncelik HAM KATEGORI_ONCELIK ile yazılıyor — etkin öncelik olmalı'
