"""KURBAN ALANI — kurallı çıkarımın başarısız olduğu tek alan.

NEDEN LLM'E BAĞLI: ÖLÇÜLDÜ (2026-09-23). Arşiv başlıkları Başlık Düzeninde
yazılmıştır, yani HER kelime büyük harfle başlar ve büyük harf özel ad
sinyali TAŞIMAZ. Kurallı çıkarım başlıktan %2 kapsamla "Veri", "Lüks
Markalara Veri" gibi yanlış parçalar üretti; gövdeden kapsam %1'e düştü ve
raporlayan taraf (Resecurity, Mandiant) kurban sanıldı. `» varlik`,
`» teknik` ve `» olcek`in aksine bu alan YARGIDIR ve satırda `kaynak=llm`
yazar.

Geçmiş 2.859 kayıt tek seferlik geçişle etiketlendi; üretim hattı da
skorlama çağrısında `kurban` alanını istiyor (ek maliyet yok).
"""
import importlib.util
import pathlib

_yol = (pathlib.Path(__file__).resolve().parent.parent
        / 'scripts' / 'kurban_etiket.py')
_spec = importlib.util.spec_from_file_location('kurban_etiket', _yol)
kur = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kur)


def test_hedef_kume_kategoriyle_daraltilir():
    """Bir Chrome yamasının ya da bir yasa tasarısının kurbanı yoktur."""
    assert 'zafiyet_rutin' not in kur.HEDEF_KATEGORI
    assert 'urun_icerik' not in kur.HEDEF_KATEGORI
    assert 'politika_hukuk' not in kur.HEDEF_KATEGORI
    assert {'veri_ihlali', 'tedarik_zinciri'} <= kur.HEDEF_KATEGORI


def test_kurbansiz_isaret_satir_uretmez():
    for bos in ('-', '', 'yok', 'bilinmiyor', None):
        assert kur.temizle(bos) is None
        assert kur.satir_kur({'ad': kur.temizle(bos)}) is None


def test_coklu_kurban_virgulle_yazilir():
    assert kur.temizle(' Twilio , Cloudflare ') == 'Twilio,Cloudflare'
    assert kur.satir_kur({'ad': 'Twilio,Cloudflare'}) == (
        '» kurban | ad=Twilio,Cloudflare | kaynak=llm\n')


def test_satir_kaynagi_acikca_yazar():
    """Yargı alanı olduğu satırdan okunabilmeli."""
    assert 'kaynak=llm' in kur.satir_kur({'ad': 'Odido'})


def test_gercek_depo_tam_ve_tutarli():
    d = kur.depo_yukle()
    h = kur.hedefler(kur.arsivi_tara())
    assert len(h) > 2500
    eksik = [k['anahtar'] for k in h if k['anahtar'] not in d]
    assert not eksik, f'{len(eksik)} kayıt etiketsiz: {eksik[:5]}'
    adli = sum(1 for k in h if d[k['anahtar']].get('ad'))
    assert adli > 900, adli


def test_arsivde_kurban_satiri_var_ve_tekil_ad_cok():
    satirlar = [l for l in open(kur.ARSIV, encoding='utf-8')
                if l.startswith('» kurban')]
    assert len(satirlar) > 900
    adlar = {a for l in satirlar
             for a in l.split('ad=')[1].split(' | ')[0].strip().split(',')}
    assert len(adlar) > 400, len(adlar)
    # Raporlayan taraf tuzağı: CISA ve Mandiant kurban listesinde başı
    # ÇEKMEMELİ (kurallı prototipte ilk sıradaydılar).
    assert 'Mandiant' not in adlar


def test_uretim_hatti_kurbani_normalize_eder():
    import main
    S = main.HaberSistemi
    ham = {'kat': 'veri_ihlali', 'siber': 1, 'mukerrer': 0,
           's': 20, 'e': 10, 'a': 8, 'k': 10}
    assert S._normalize_record(S, {**ham, 'kurban': 'Odido'})['kurban'] == 'Odido'
    assert 'kurban' not in S._normalize_record(S, {**ham, 'kurban': '-'})
    assert 'kurban' not in S._normalize_record(S, ham)


def test_skorlama_promptu_kurban_istiyor():
    from src.config import get_scoring_prompt
    p = get_scoring_prompt('=== HABER ID: 1 ===\nBaşlık: x\n')
    assert '"kurban"' in p
    assert 'SALDIRIYA UĞRAYAN' in p


def test_meta_kurbani_tasir():
    import main
    m = main.HaberSistemi._arsiv_meta_kur(
        [1], {1: {'tr_title': 'A'}},
        {1: {'kat': 'veri_ihlali', 'toplam': 50, 'kurban': 'Odido'}})
    assert m['A']['kurban'] == 'Odido'


def test_ingilizce_ulke_adi_turkcelesir():
    """ÖLÇÜLDÜ (2026-09-24, hattın ilk günü): LLM "Ukraine", "UAE",
    "European Union" döndürdü; geriye dönük 1.036 etiketin tamamı Türkçe.
    Eşlemesiz bırakmak aynı kurumu iki kurban olarak saydırırdı."""
    assert kur.temizle('Ukraine') == 'Ukrayna'
    assert kur.temizle('UAE') == 'BAE'
    assert kur.temizle('European Union') == 'Avrupa Birliği'
    assert kur.temizle('Saudi Arabia') == 'Suudi Arabistan'
    # Özgün kurum adı DEĞİŞMEZ.
    assert kur.temizle('Odido') == 'Odido'
    assert kur.temizle('SUSE Linux') == 'SUSE Linux'


def test_kitle_tanimi_kurban_sayilmaz():
    for jenerik in ('Developers', 'Windows users', 'Online retailers',
                    'US Federal Agencies', 'Government contractor',
                    'Chilean retail and financial institutions',
                    'Android users in Europe and Canada'):
        assert kur.temizle(jenerik) is None, jenerik


def test_sirket_adindaki_sistem_kelimesi_dusurulmez():
    """'systems'/'servers' jenerik listeye alınamaz: gerçek şirket
    adlarında geçiyor ve kuralı geçmişe uygulamak kaydı düşürüyordu."""
    assert kur.temizle('Unlimited Technology Systems') == (
        'Unlimited Technology Systems')


def test_normalizasyon_gecmis_etiketleri_bozmaz():
    d = kur.depo_yukle()
    bozulan = [v['ad'] for v in d.values()
               if v.get('ad') and kur.temizle(v['ad']) != v['ad']]
    assert not bozulan, bozulan[:5]


def test_hat_kurallari_kopyalamaz():
    import main
    assert main.HaberSistemi._kurban_modulu().__file__.endswith(
        'scripts/kurban_etiket.py')
    ham = {'kat': 'veri_ihlali', 'siber': 1, 'mukerrer': 0,
           's': 20, 'e': 10, 'a': 8, 'k': 10}
    S = main.HaberSistemi
    assert S._normalize_record(S, {**ham, 'kurban': 'Ukraine'})['kurban'] == 'Ukrayna'
    assert 'kurban' not in S._normalize_record(S, {**ham, 'kurban': 'Windows users'})


def test_prompt_turkce_ad_ve_kitle_kuralini_soyluyor():
    from src.config import get_scoring_prompt
    p = get_scoring_prompt('=== HABER ID: 1 ===\nBaşlık: x\n')
    assert 'ADI TÜRKÇE YAZ' in p
    assert 'KİTLE TANIMI KURBAN DEĞİLDİR' in p
