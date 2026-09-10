"""Başlık ve gövde paragrafı ÖLÇÜ denetimleri.

Sınırlar prompt'ta yazılı ("EN FAZLA 8 KELİME (kesin sınır)", "110-130
kelime") ama LLM kelime saymakta güvenilir değil. Deterministik ağlar da
sınırlıydı: başlık ağı yalnızca sabit bir dolgu listesini atabiliyor, gövde
paragrafı için hiç ağ yoktu.

ÖLÇÜLDÜ (18 rapor, 2026-08-20..09-08): başlıkların %9-66'sı sınırı aşıyor.
08 Eylül raporunda 21 başlığın 14'ü 9-10 kelimeydi (KRİTİK 3'ün üçü dahil),
gövdedeki 18 paragrafın biri 83, ikisi 105 kelimeydi.
"""
import main


def _sistem(yanit):
    s = main.HaberSistemi.__new__(main.HaberSistemi)
    s._gemini_call_json = lambda *a, **k: yanit
    return s


UZUN = 'ABD Enerji Bakanliginin Elektrik Sebekesi Guvenliginde Yapay Zeka Kullanmasi'
KISA = 'Enerji Bakanligi Sebeke Guvenliginde Yapay Zeka Kullaniyor'


def _icerik(baslik, para='Ayrintili bir ozet metni. ' * 20):
    return {1: {'tr_title': baslik, 'paragraph': para}}


def _art(kelime=200):
    return {1: {'id': 1, 'title': '', 'full_text': 'kaynak metin ' * kelime}}


# ── Başlık ────────────────────────────────────────────────────────────────

def test_uzun_baslik_yeniden_yazilir():
    cnt = _icerik(UZUN)
    _sistem({'tr_title': KISA})._enforce_baslik_uzunlugu([1], cnt, _art())
    assert cnt[1]['tr_title'] == KISA
    assert len(cnt[1]['tr_title'].split()) <= main.TR_TITLE_MAX_WORDS


def test_sinir_icindeki_baslik_llme_gitmez():
    cnt = _icerik(KISA)
    cagri = []
    s = main.HaberSistemi.__new__(main.HaberSistemi)
    s._gemini_call_json = lambda *a, **k: cagri.append(1) or {}
    s._enforce_baslik_uzunlugu([1], cnt, _art())
    assert not cagri, 'sınır içindeki başlık için gereksiz LLM çağrısı'


def test_hala_uzun_yanit_reddedilir():
    """Regresyon olmasın: yeni başlık da sınırı aşıyorsa orijinal kalır."""
    cnt = _icerik(UZUN)
    _sistem({'tr_title': UZUN + ' Ve Daha Fazlasi'})._enforce_baslik_uzunlugu(
        [1], cnt, _art())
    assert cnt[1]['tr_title'] == UZUN


def test_bos_yanit_reddedilir():
    cnt = _icerik(UZUN)
    _sistem({'tr_title': ''})._enforce_baslik_uzunlugu([1], cnt, _art())
    assert cnt[1]['tr_title'] == UZUN


def test_llm_sessizse_baslik_korunur():
    cnt = _icerik(UZUN)
    _sistem(None)._enforce_baslik_uzunlugu([1], cnt, _art())
    assert cnt[1]['tr_title'] == UZUN


# ── Gövde paragrafı ───────────────────────────────────────────────────────

def test_kisa_govde_paragrafi_uzatilir():
    cnt = _icerik(KISA, 'kisa ozet ' * 30)          # 60 kelime
    uzun = 'genisletilmis ozet ' * 60               # 120 kelime
    # Onarım TOPLU çalışır: yanıt {"paragraphs": [{"id", "paragraph"}]}.
    _sistem({'paragraphs': [{'id': 1, 'paragraph': uzun}]}) \
        ._enforce_govde_paragraf_uzunlugu([1], cnt, _art())
    assert len(cnt[1]['paragraph'].split()) >= main.HaberSistemi.GOVDE_PARA_MIN_WORDS


def test_kaynak_kisaysa_denenmez():
    """Uzatacak malzeme yoksa deneme yalnızca halüsinasyon riski katardı."""
    cnt = _icerik(KISA, 'kisa ozet ' * 30)
    cagri = []
    s = main.HaberSistemi.__new__(main.HaberSistemi)
    s._gemini_call_json = lambda *a, **k: cagri.append(1) or {}
    s._enforce_govde_paragraf_uzunlugu([1], cnt, _art(kelime=10))
    assert not cagri, 'kaynak metin kısayken uzatma denendi'


def test_kisalan_yanit_reddedilir():
    kisa = 'kisa ozet ' * 30
    cnt = _icerik(KISA, kisa)
    _sistem({'paragraphs': [{'id': 1, 'paragraph': 'daha da kisa'}]}) \
        ._enforce_govde_paragraf_uzunlugu([1], cnt, _art())
    assert cnt[1]['paragraph'] == kisa


def test_govde_esigi_kritik3_ile_ayni():
    """İki taraf sessizce ayrışmasın."""
    assert (main.HaberSistemi.GOVDE_PARA_MIN_WORDS
            == main.HaberSistemi.KRITIK3_PARA_MIN_WORDS)


def test_kanca_rapor_kesinlestikten_sonra():
    """Onarım LLM çağrısı harcar; sonradan elenecek habere para ödenmemeli."""
    import inspect
    kaynak = inspect.getsource(main.HaberSistemi.create_html)
    i_son = kaynak.index("_senkron('manset_puan_tersinelik')")
    i_bas = kaynak.index('_enforce_baslik_uzunlugu(')
    i_gov = kaynak.index('_enforce_govde_paragraf_uzunlugu(')
    assert i_son < i_gov < i_bas or i_son < i_bas, \
        'ölçü denetimi rapor kesinleşmeden çalışıyor'


def test_butce_siniri_var():
    """İhlal sayısı bazı günlerde 14'e çıkıyor; hepsini onarmak koşuyu şişirir."""
    assert 1 <= main.HaberSistemi.METIN_ONARIM_BUTCESI <= 20
    cnt = {i: {'tr_title': UZUN, 'paragraph': 'x ' * 200} for i in range(30)}
    art = {i: {'id': i, 'title': '', 'full_text': 'k ' * 200} for i in range(30)}
    cagri = []
    s = main.HaberSistemi.__new__(main.HaberSistemi)
    s._gemini_call_json = lambda *a, **k: cagri.append(1) or {'tr_title': KISA}
    s._enforce_baslik_uzunlugu(list(cnt), cnt, art)
    assert len(cagri) == main.HaberSistemi.METIN_ONARIM_BUTCESI


# ── Gövde uzunluk onarımı: bütçe ve partileme ─────────────────────────────
# ÖLÇÜLDÜ (2026-09-10): 33 gövde paragrafının 12'si 110 kelimenin altındaydı
# (en kötüsü 86) ve bu sayı o günkü bütçeyle (METIN_ONARIM_BUTCESI = 12) TAM
# eşitti — bütçe ihlal kadar, onarım payı sıfırdı. Onarım artık toplu çalışır:
# maliyet kalem sayısına değil PARTİ sayısına bağlıdır.

def _toplu_sistem():
    """Her partiyi 120 kelimeye uzatan sahte LLM; çağrıları kaydeder."""
    s = main.HaberSistemi.__new__(main.HaberSistemi)
    cagrilar = []

    def _yanit(prompt, **k):
        ids = [int(x) for x in __import__('re').findall(r'HABER ID: (\d+)', prompt)]
        cagrilar.append(ids)
        return {'paragraphs': [{'id': i, 'paragraph': 'genisletilmis ozet ' * 60}
                               for i in ids]}

    s._gemini_call_json = _yanit
    return s, cagrilar


def _cok_kalem(adet):
    cnt = {i: {'tr_title': KISA, 'paragraph': 'kisa ozet ' * 30}
           for i in range(1, adet + 1)}
    art = {i: {'id': i, 'title': '', 'full_text': 'kaynak metin ' * 200}
           for i in range(1, adet + 1)}
    return cnt, art


def test_12_ihlal_tek_partide_onarilir():
    """2026-09-10 senaryosu: 12 kısa paragraf, tek çağrıda onarılır."""
    s, cagrilar = _toplu_sistem()
    cnt, art = _cok_kalem(12)
    s._enforce_govde_paragraf_uzunlugu(list(cnt), cnt, art)

    assert len(cagrilar) == 1, f"kalem başına çağrı yapıldı: {len(cagrilar)}"
    kisa_kalan = [i for i, c in cnt.items()
                  if len(c['paragraph'].split())
                  < main.HaberSistemi.GOVDE_PARA_MIN_WORDS]
    assert not kisa_kalan, f"onarılmadan kalan kalem: {kisa_kalan}"


def test_parti_boyutu_asilinca_bolunur():
    s, cagrilar = _toplu_sistem()
    cnt, art = _cok_kalem(25)
    s._enforce_govde_paragraf_uzunlugu(list(cnt), cnt, art)

    parti = main.HaberSistemi.GOVDE_ONARIM_PARTI
    assert len(cagrilar) == 3, f"beklenen 3 parti, gelen {len(cagrilar)}"
    assert all(len(c) <= parti for c in cagrilar)
    assert sorted(sum(cagrilar, [])) == sorted(cnt)


def test_butce_asilirsa_en_kotu_ihlaller_once_onarilir():
    s, cagrilar = _toplu_sistem()
    adet = main.HaberSistemi.GOVDE_ONARIM_BUTCESI + 3
    cnt, art = _cok_kalem(adet)
    # ID 1 en kısa (en kötü ihlal), ID adet en uzun.
    for i in range(1, adet + 1):
        cnt[i]['paragraph'] = 'kelime ' * (50 + i)

    s._enforce_govde_paragraf_uzunlugu(list(cnt), cnt, art)

    islenen = sum(cagrilar, [])
    assert len(islenen) == main.HaberSistemi.GOVDE_ONARIM_BUTCESI
    assert 1 in islenen, 'en kötü ihlal bütçe dışı kaldı'
    assert adet not in islenen, 'en hafif ihlal bütçeyi tüketti'


def test_partideki_diger_kalem_bozuk_yanittan_etkilenmez():
    """Bir kalem için eksik/kısa yanıt gelse bile diğerleri onarılır."""
    s = main.HaberSistemi.__new__(main.HaberSistemi)
    s._gemini_call_json = lambda *a, **k: {
        'paragraphs': [{'id': 1, 'paragraph': 'cok kisa'},
                       {'id': 2, 'paragraph': 'genisletilmis ozet ' * 60}]}
    cnt, art = _cok_kalem(2)
    s._enforce_govde_paragraf_uzunlugu([1, 2], cnt, art)

    assert cnt[1]['paragraph'].startswith('kisa ozet'), 'kısalan yanıt kabul edildi'
    assert (len(cnt[2]['paragraph'].split())
            >= main.HaberSistemi.GOVDE_PARA_MIN_WORDS)
