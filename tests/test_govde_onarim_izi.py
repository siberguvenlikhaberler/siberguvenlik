"""GÖVDE PARAGRAF ONARIMI — sonucun koşu kaydına yazılması.

ÖLÇÜLDÜ (2026-09-23 raporu): gövdede üç paragraf 110 kelimenin altında
yayımlandı (105, 106, 109). `metin_onarim` izi o gün yalnızca kritik3'ü
kaydettiği için hiçbirinin nedeni belirlenemedi — manşet tarafında kapatılan
boşluğun tam olarak aynısı gövdede açıktı. Onarım zaten çalışıyordu; eksik
olan, ne yaptığının kayda geçmesiydi.
"""
import main

KISA = 'kelime ' * 105
HEDEF = 'genisletilmis ozet ' * 60   # 120 kelime
MIN = main.HaberSistemi.GOVDE_PARA_MIN_WORDS


def _sistem(yanit):
    s = main.HaberSistemi.__new__(main.HaberSistemi)
    s._gemini_call_json = lambda *a, **k: yanit
    return s


def _veri(kaynak='kaynak metin ' * 200):
    return ({1: {'tr_title': 'Test', 'paragraph': KISA}},
            {1: {'full_text': kaynak}})


def _izler(s):
    return [i for i in getattr(s, '_metin_onarim_izi', [])
            if i['tur'] == 'govde']


def test_hedefe_ulasan_onarim_kaydedilir():
    s = _sistem({'paragraphs': [{'id': 1, 'paragraph': HEDEF}]})
    cnt, art = _veri()
    s._enforce_govde_paragraf_uzunlugu([1], cnt, art)
    iz = _izler(s)
    assert iz and iz[-1]['sonuc'] == 'hedef'
    assert iz[-1]['once'] == 105 and iz[-1]['sonra'] >= MIN


def test_hedef_altinda_kalan_onarim_kaydedilir():
    """2026-09-23'teki üç vakanın en olası nedeni; artık ayırt edilebilir."""
    s = _sistem({'paragraphs': [{'id': 1, 'paragraph': 'kelime ' * 108}]})
    cnt, art = _veri()
    s._enforce_govde_paragraf_uzunlugu([1], cnt, art)
    iz = _izler(s)
    assert iz and iz[-1]['sonuc'] == 'hedef_altinda'
    assert iz[-1]['sonra'] == 108


def test_kaynak_kisaysa_nedeni_kaydedilir():
    s = _sistem({'paragraphs': [{'id': 1, 'paragraph': HEDEF}]})
    cnt, art = _veri(kaynak='kisa ' * 10)
    s._enforce_govde_paragraf_uzunlugu([1], cnt, art)
    iz = _izler(s)
    assert iz and iz[-1]['sonuc'] == 'kaynak_kisa'
    assert iz[-1]['kaynak_kelime'] == 10
    assert cnt[1]['paragraph'] == KISA, 'kaynak kısayken paragraf değişti'


def test_kisalan_yanit_reddedilir_ve_kaydedilir():
    s = _sistem({'paragraphs': [{'id': 1, 'paragraph': 'daha da kisa'}]})
    cnt, art = _veri()
    s._enforce_govde_paragraf_uzunlugu([1], cnt, art)
    iz = _izler(s)
    assert iz and iz[-1]['sonuc'] == 'kisaldi'
    assert cnt[1]['paragraph'] == KISA


def test_yanitsiz_kalem_kaydedilir():
    """Parti yanıtı geldi ama bu ID yoktu — sessizce kaybolmamalı."""
    s = _sistem({'paragraphs': []})
    cnt, art = _veri()
    s._enforce_govde_paragraf_uzunlugu([1], cnt, art)
    iz = _izler(s)
    assert iz and iz[-1]['sonuc'] == 'yanit_yok'


def test_butce_disi_kalan_ihlaller_kaydedilir():
    """Bütçe dolunca kalanlar denenmez; denenmediği kayıttan görülmeli."""
    n = main.HaberSistemi.GOVDE_ONARIM_BUTCESI + 3
    s = _sistem({'paragraphs': [{'id': i, 'paragraph': HEDEF}
                                for i in range(n)]})
    # Hepsi sınırın ALTINDA olmalı; 110+ bir paragraf zaten aday değildir.
    cnt = {i: {'tr_title': 'Test', 'paragraph': 'kelime ' * (100 + i % 9)}
           for i in range(n)}
    art = {i: {'full_text': 'kaynak metin ' * 200} for i in range(n)}
    s._enforce_govde_paragraf_uzunlugu(list(range(n)), cnt, art)
    iz = _izler(s)
    assert sum(1 for i in iz if i['sonuc'] == 'hak_doldu') == 3
    assert len(iz) == n, 'her ihlal için tam bir iz kaydı bekleniyordu'
