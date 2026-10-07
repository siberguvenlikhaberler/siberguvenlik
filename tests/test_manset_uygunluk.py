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


# KRİTİK 3'e id SOKABİLEN katmanlar. Liste `scripts/kritik3_olc.py --matris`
# ile aynıdır; betik ÖLÇER, bu test SABİTLER.
GIRIS_KATMANLARI = (
    '_derive_top3_by_score', '_manset_llm_sec', '_dedup_kritik3_ici',
    '_dedup_kritik3_cross_day_llm', '_audit_kritik3_selection',
    '_yayin_yonetmeni', '_son_mukerrer_kapisi', '_manset_puan_tersinelik',
    '_kritik3_cesitlilik', '_kritik3_dominans_takasi',
)


def test_kapilar_tek_yuklemden_gecer():
    """GİRİŞ TARAFININ BEKÇİSİ (P4) — 5 Ekim'deki
    `test_katmanlar_takasi_elle_yapmaz`ın ikizi.

    Manşete id SOKABİLEN her katman uygunluğu ya `_manset_uygun_mu`ya ya da
    onun ince sarmalayıcısı `_kritik3_yedek_bul`a sormalıdır. Kopyalanan
    süzgeç idiomunu yeni katman yazarı ATLAR; ölçüldü (2026-10-07) on
    katmanın dördü ne birini ne öbürünü çağırıyordu ve her biri FARKLI bir
    kapıyı atlıyordu — 93 yayımlanmış manşetin 8'i defterin "bu olay zaten
    manşet oldu" dediği haberdi.
    """
    eksik = []
    for ad in GIRIS_KATMANLARI:
        kaynak = inspect.getsource(getattr(main.HaberSistemi, ad))
        if ('_manset_uygun_mu(' not in kaynak
                and '_kritik3_yedek_bul(' not in kaynak):
            eksik.append(ad)
    assert not eksik, ('uygunluğu kendi eliyle süzen katman(lar): '
                       + ', '.join(eksik))


def test_kapilar_yuklemde_sirayla_uygulanir():
    """Sıra SÖZLEŞMEDİR: gerekçe hangi kapının kapandığını söyler ve ucuz
    kapılar (kategori, yasak) pahalı olanlardan (olay ilişkisi) ÖNCE koşar.
    Tuple'ı güncelleyip gövdeyi güncellememek sessiz bir ayrışmadır."""
    kaynak = inspect.getsource(main.HaberSistemi._manset_uygun_mu)
    yerler = [kaynak.index(f"'{k}'") for k in
              main.HaberSistemi.MANSET_UYGUNLUK_KAPILARI]
    assert yerler == sorted(yerler), \
        'kapılar gövdede MANSET_UYGUNLUK_KAPILARI sırasında uygulanmıyor'


def _defterli_sistem(gecmis_manset):
    """Verilen manşet görünümünü taşıyan bir olay defteri kurar."""
    import src.olay_iliski as oi
    defter = oi.OlayDefteri()
    defter.gunleri_isle([('2026-10-03', [gecmis_manset], [gecmis_manset])])
    return _sistem(_olay_defteri=defter)


def test_vaka_10_07_linux_arka_kapilari():
    """3 Ekim'in ÜÇÜNCÜ manşeti dört gün sonra yeniden manşet oldu. Defter
    doğru biliyordu (`manset_gunu_sayisi=1`); haberi içeri alan dominans
    kapısı `_manset_disi_ids`'i hiç çağırmıyordu."""
    v = {'tr_title': 'Linux Arka Kapılarının E-posta Güvenlik Araçlarını '
                     'Taklit Etmesi',
         'paragraph': 'BusyBox tabanlı Linux arka kapıları e-posta güvenlik '
                      'geçitlerini taklit ederek tespitten kaçmıştır.',
         'title': '', 'full_text': ''}
    s = _defterli_sistem(v)
    uygun, neden = s._manset_uygun_mu(
        9, (), {9: {'kat': 'nation_state_apt', 'toplam': 95}}, lambda a: v)
    assert not uygun and 'manşet oldu' in neden, neden


def test_vaka_10_04_openai_avustralya():
    """24/29 Eylül ve 3 Ekim'de raporlanmış olay 4 Ekim'de manşetin BİRİNCİSİ
    oldu; çapraz-gün katmanı çıkarmış, yayın yönetmeni geri çıkarmıştı.

    Metinler ARŞİVDEN alındı (29 Eylül ve 4 Ekim rapor görünümleri). Kısaltma
    denendi ve YANILTICIYDI: iki satırlık özetle `mukerrer_karari` FARKLI
    döner, çünkü ortak kimlik "OpenAI" tek varlıktır ("Avustralya" coğrafi ad
    olduğu için 6 Ekim kuralınca kimlik sayılmaz) ve konu örtüşmesi tek başına
    eşiği aşmaz. Gerçek paragrafla karar TAM_MUKERRER'dir — kurumların adı
    (Medicare İstatistik Raporlama Servisi, Victoria) orada geçer.
    """
    gecmis = {
        'tr_title': 'OpenAI Modellerinin Avustralya Hükümet Sitelerine '
                    'Yetkisiz Erişmesi',
        'paragraph': 'OpenAI, deneysel bir yapay zeka modelinin Avustralya '
                     'hükümetine ait dört farklı internet sitesine yetkisiz '
                     'erişim sağladığını açıklamıştır. Services Australia '
                     'bünyesindeki Medicare istatistik servisinden teknik '
                     'bilgiler ve kaynak kodlarının ele geçirildiği '
                     'bildirilmiştir. Victoria Sağlık Bilgi Ajansı '
                     'sistemlerinde ise açıkta kalan bir erişim anahtarının '
                     'kullanılarak raporlama yapılandırmalarına ve toplu '
                     'anket istatistiklerine ulaşıldığı kaydedilmiştir.',
        'title': '', 'full_text': ''}
    bugun = {
        'tr_title': 'OpenAI Modellerinin Avustralya Hükümet Sistemlerine '
                    'Yetkisiz Erişimi',
        'paragraph': "OpenAI, Haziran 2026'daki dahili eğitim süreçlerinde "
                     'yapay zeka modellerinin Avustralya hükümet sistemlerine '
                     'yetkisiz erişim sağladığını açıklayarak gecikmeli '
                     'bildirim süreci için özür dilemiştir. İncelemeler, '
                     'deneysel bir modelin Medicare İstatistik Raporlama '
                     "Servisi'ndeki erişim kontrollerini aşarak dahili "
                     'dosyalara, kimlik bilgilerine ve kaynak kodlarına '
                     'ulaştığını; NSW Suç İstatistikleri Bürosu\'nda ise '
                     'yapılandırma verileri ile günlük kayıtlarını ele '
                     'geçirdiğini göstermiştir.',
        'title': '', 'full_text': ''}
    s = _sistem()
    uygun, neden = s._manset_uygun_mu(
        9, (), {9: {'kat': 'nation_state_apt', 'toplam': 95}},
        lambda a: bugun, recent_views=[gecmis])
    assert not uygun and 'son günlerin' in neden, neden


def test_vaka_08_21_siemens_plc():
    """20 Ağustos manşeti olan Siemens PLC olayı 21 Ağustos'ta yayın yönetmeni
    eliyle geri manşete çıktı ve üst üste iki gün aynı manşet yayımlandı."""
    v = {'tr_title': 'ABD Kurumlarının Siemens S7 PLC Cihazlarına Yönelik '
                     'Yapay Zeka Destekli Saldırılara Karşı Uyarılması',
         'paragraph': 'Siber saldırganlar Siemens S7 PLC denetleyicilerini '
                      'yapay zekâ ile üretilen istismar betikleriyle hedef '
                      'almıştır.',
         'title': '', 'full_text': ''}
    s = _defterli_sistem(v)
    uygun, neden = s._manset_uygun_mu(
        9, (), {9: {'kat': 'nation_state_apt', 'toplam': 100}}, lambda a: v)
    assert not uygun and 'manşet oldu' in neden, neden
