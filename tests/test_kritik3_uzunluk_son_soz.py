"""MANŞET PARAGRAF UZUNLUĞU — deneme hakkı ve yayından önce son söz.

ÖLÇÜLDÜ (2026-09-11): manşetin ikinci haberi ("Çin Bağlantılı Grubun Sogou
Yazılımına Arka Kapı Yerleştirmesi") 103 kelime yayımlandı; alt sınır 110.

İki boşluk vardı:
  • Uzatma metodu haber başına TEK çağrı yapıyordu; hedef tutmayınca "en iyi
    deneme" olarak bırakılıyordu. Manşet en fazla 3 haberdir, ikinci deneme
    ucuzdur.
  • Metot manşeti değiştiren katmanların ardından tek tek çağrılıyordu;
    manşete SONRADAN giren bir haberi kaçıran her yol sessizce kısa paragraf
    yayımlıyordu.
"""
import main

KISA = 'kelime ' * 103          # 2026-09-11'de yayımlanan uzunluk
HEDEF = 'genisletilmis ozet ' * 60   # 120 kelime


def _sistem(yanitlar):
    """Sıralı yanıt döndüren sahte LLM; çağrıları sayar."""
    s = main.HaberSistemi.__new__(main.HaberSistemi)
    cagri = {'n': 0}

    def _yanit(*a, **k):
        y = yanitlar[min(cagri['n'], len(yanitlar) - 1)]
        cagri['n'] += 1
        return y

    s._gemini_call_json = _yanit
    return s, cagri


def _veri():
    return ({1: {'tr_title': 'Test', 'paragraph': KISA}},
            {1: {'full_text': 'kaynak metin ' * 200}})


def test_ilk_deneme_yetmezse_ikinci_deneme_yapilir():
    """İlk deneme 106'da kalırsa ikinci hak kullanılır."""
    s, cagri = _sistem([{'paragraph': 'kelime ' * 106},
                        {'paragraph': HEDEF}])
    cnt, art = _veri()
    s._enforce_kritik3_paragraph_length([1], cnt, art)
    s._enforce_kritik3_paragraph_length([1], cnt, art)   # yayından önce son söz
    assert cagri['n'] == 2
    assert len(cnt[1]['paragraph'].split()) >= main.HaberSistemi.KRITIK3_PARA_MIN_WORDS


def test_deneme_hakki_dolunca_durur():
    """Metot boru hattında birçok kez çağrılır; sayaç olmadan aynı haber
    defalarca denenirdi."""
    s, cagri = _sistem([{'paragraph': 'kelime ' * 104}])
    cnt, art = _veri()
    for _ in range(5):
        s._enforce_kritik3_paragraph_length([1], cnt, art)
    assert cagri['n'] == main.HaberSistemi.KRITIK3_UZUNLUK_DENEME


def test_hedefe_ulasinca_tekrar_denenmez():
    s, cagri = _sistem([{'paragraph': HEDEF}])
    cnt, art = _veri()
    s._enforce_kritik3_paragraph_length([1], cnt, art)
    s._enforce_kritik3_paragraph_length([1], cnt, art)
    assert cagri['n'] == 1, 'hedef tutmuşken yeniden denendi'


def test_kaynak_kisaysa_deneme_hakki_harcanmaz():
    s, cagri = _sistem([{'paragraph': HEDEF}])
    cnt = {1: {'tr_title': 'Test', 'paragraph': KISA}}
    art = {1: {'full_text': 'kisa ' * 10}}
    s._enforce_kritik3_paragraph_length([1], cnt, art)
    assert cagri['n'] == 0
    assert cnt[1]['paragraph'] == KISA


def test_kisalan_yanit_reddedilir():
    s, cagri = _sistem([{'paragraph': 'daha da kisa'}])
    cnt, art = _veri()
    s._enforce_kritik3_paragraph_length([1], cnt, art)
    assert cnt[1]['paragraph'] == KISA
