"""RAPOR İÇİ MÜKERRER KAPISI — denetimin gördüğünü engeller, ama hakem onayıyla.

ÖLÇÜLDÜ (2026-09-19): Hacktron araştırmacılarının Claude ile libheif açığını
istismar edip OpenAI çalışan hesaplarını ele geçirmesi gövdede İKİ KEZ
yayımlandı (ID 27 ve 41). Kalite denetimi bunu "entity:discours" gerekçesiyle
`rapor_ici_kacak` olarak KAYDETMİŞTİ; tespit vardı, yaptırım yoktu.

ÖLÇÜLDÜ (53 denetim günü, 8 günde 9 çift): ham deterministik sinyalin ancak
yarısı gerçek mükerrerdi. Sahte çiftler gerçek haberleri sileceği için karar
mükerrer hakemine onaylatılır:
  GERÇEK isolated-vm (08-21 ×2), Çin Chrome sıfır-günü (09-10), OpenAI (09-19)
  SAHTE  Jewelbug ↔ JWR (ortak: asya/doğu), Berlin bakanlıkları ↔ Teksas
         Üniversitesi (ortak: cuma/friday), Medusa ↔ Windows IKE (ortak:
         altyapı/güvenlik)
"""
import main


# Deterministik katmanın TAM_MUKERRER diyeceği çift. Ortak CVE + yüksek konu
# örtüşmesi şart: yalnızca "aynı firma + aynı konu" GELISME sayılıyor ve kapı
# hiç tetiklenmiyordu (ilk fixture denemesinde böyle oldu).
_GOVDE = ('Hacktron araştırmacıları libheif kütüphanesindeki CVE-2026-77123 '
          'açığını istismar ederek OpenAI çalışanlarının ChatGPT hesaplarını '
          'ele geçirmiştir. Ekip, OpenAI topluluk forumundaki görüntü işleme '
          'hatasını zincirleyerek dahili kod depolarına erişmiştir.')
A = {'tr_title': 'Hacktron ekibinin OpenAI hesaplarını ele geçirmesi',
     'paragraph': _GOVDE}
B = {'tr_title': 'OpenAI dahili kodlarına yapay zeka destekli erişim',
     'paragraph': _GOVDE + ' Rapor 18 Eylül 2026 tarihinde yayımlanmıştır.'}
C = {'tr_title': 'Medusa fidye yazılımının kritik altyapıyı hedeflemesi',
     'paragraph': 'Medusa fidye yazılımı grubu beş yüzden fazla kritik altyapı '
                  'kuruluşunu hedef almıştır.'}


def _sistem(hakem_yaniti):
    s = main.HaberSistemi.__new__(main.HaberSistemi)
    s._olay_sozlugu = None
    s._hakem_onbellek = {}
    s.cagri = []

    def _llm(prompt, **k):
        s.cagri.append(prompt)
        return hakem_yaniti

    s._gemini_call_json = _llm
    return s


def _veri(icerik):
    art = {i: {'title': c['tr_title'], 'full_text': c['paragraph']}
           for i, c in icerik.items()}
    return icerik, art


def test_hakem_onaylayinca_zayif_olan_elenir():
    s = _sistem({'kararlar': [{'no': 20001, 'ayni': True, 'olay': 'OpenAI ihlali'}]})
    cnt, art = _veri({1: A, 2: B})
    rec = {1: {'toplam': 90}, 2: {'toplam': 70}}
    nedenler = {}
    t3, t10, kalan = s._rapor_ici_mukerrer_kapisi(
        [], [1, 2], [], rec, cnt, art, eleme_nedeni=nedenler)
    assert t10 == [1], f'zayıf olan elenmedi: {t10}'
    assert nedenler.get(2) == 'rapor_ici_mukerrer'


def test_hakem_reddedince_haber_kalir():
    """Sahte çift silme yapmamalı — 53 günün yarısı sahteydi."""
    s = _sistem({'kararlar': [{'no': 20001, 'ayni': False, 'olay': ''}]})
    cnt, art = _veri({1: A, 2: B})
    rec = {1: {'toplam': 90}, 2: {'toplam': 70}}
    t3, t10, kalan = s._rapor_ici_mukerrer_kapisi([], [1, 2], [], rec, cnt, art)
    assert t10 == [1, 2], 'hakem reddetmesine rağmen haber elendi'


def test_hakem_yanit_vermezse_haber_kalir():
    """Güvenli degrade: karar verilemeyen çift mükerrer SAYILMAZ."""
    s = _sistem(None)
    cnt, art = _veri({1: A, 2: B})
    rec = {1: {'toplam': 90}, 2: {'toplam': 70}}
    t3, t10, kalan = s._rapor_ici_mukerrer_kapisi([], [1, 2], [], rec, cnt, art)
    assert t10 == [1, 2]


def test_kritik3_haberi_asla_elenmez():
    """Manşette temsil edilen olayın GÖVDEDEKİ kopyası elenir, tersi değil —
    gövdedeki daha yüksek puanlı olsa bile."""
    s = _sistem({'kararlar': [{'no': 20001, 'ayni': True, 'olay': 'OpenAI ihlali'}]})
    cnt, art = _veri({1: A, 2: B})
    rec = {1: {'toplam': 60}, 2: {'toplam': 95}}
    t3, t10, kalan = s._rapor_ici_mukerrer_kapisi(
        [1], [1, 2], [], rec, cnt, art)
    assert t3 == [1] and 1 in t10 and 2 not in t10


def test_farkli_olaylar_hakeme_hic_sorulmaz():
    """Deterministik katman AYNI OLAY demiyorsa LLM çağrısı YAPILMAZ."""
    s = _sistem({'kararlar': []})
    cnt, art = _veri({1: A, 2: C})
    rec = {1: {'toplam': 90}, 2: {'toplam': 70}}
    t3, t10, kalan = s._rapor_ici_mukerrer_kapisi([], [1, 2], [], rec, cnt, art)
    assert t10 == [1, 2]
    assert not s.cagri, 'farklı olaylar için gereksiz LLM çağrısı yapıldı'


def test_tek_haberli_raporda_cokmez():
    s = _sistem({'kararlar': []})
    cnt, art = _veri({1: A})
    t3, t10, kalan = s._rapor_ici_mukerrer_kapisi([], [1], [], {1: {'toplam': 9}}, cnt, art)
    assert t10 == [1]
