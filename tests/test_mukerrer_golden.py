"""MÜKERRER GOLDEN SET KAPISI — set bir daha sessizce ölçmez olmasın.

NEDEN VAR: `data/mukerrer_golden.json`ın 38 çifti yalnızca GÜN + BAŞLIK
tutuyordu; görünümler `rapor_gecmis`ten okunuyordu ve o dosya 30 günde
döndüğü için 2026-10-07'de çiftlerin TAMAMI "geçmişten düşmüş, atlandı" diye
atlanıyordu. Yani elle etiketli referans aylarca ölçüyor sanılırken hiçbir şey
ölçmüyordu; arıza ancak P6 ölçümünde fark edildi. Görünümler artık setin
İÇİNDE (`a`/`b`) — bu dosya o sözleşmeyi kapıya çevirir.

Ayrıntılı rapor: python scripts/mukerrer_olc.py
"""
import json
import os

from src import dedup, olay_iliski as O

GOLDEN = os.path.join(os.path.dirname(__file__), '..', 'data',
                      'mukerrer_golden.json')
ALAN = ('tr_title', 'paragraph', 'title', 'full_text')

# TABAN ÇİZGİSİ — 2026-10-07'de gömülü görünümlerle ölçülen doğru karar
# sayısı. `ayni_olay` 38/38'dir ama bu ÖRNEKLEM İÇİ bir uyumdur: eleme
# süzgeçleri (gövde kod adı konu kapısı, salt başlık reddi, DF sözlüğü) tam
# bu 38 çifte bakılarak seçildi. Sayı bir KALİTE KANITI değil, REGRESYON
# EŞİĞİDİR; kapının işi yükseltmek değil düşmesini engellemektir.
TABAN = {'same_event': 33, 'dört-değerli': 32, 'ayni_olay': 38}


def _ciftler():
    with open(GOLDEN, encoding='utf-8') as f:
        return json.load(f)['ciftler']


def test_gorunumler_setin_icinde():
    """Her çiftin iki tarafı da setten OKUNABİLMELİ — dış dosyaya bağlı
    olmamalı. Eksik alan sessiz bir ölçüm kaybıdır."""
    for c in _ciftler():
        for s in ('a', 'b'):
            assert isinstance(c.get(s), dict), f"çift {c['no']}: {s} görünümü yok"
            assert set(c[s]) == set(ALAN), f"çift {c['no']}: {s} alanları eksik"
            assert (c[s]['tr_title'] or c[s]['title']), \
                f"çift {c['no']}: {s} metinsiz"


def test_baslik_gorunumle_tutarli():
    """Gömülü görünüm, çiftin adlandırdığı haberin kendisi olmalı; yanlış
    görünüm gömmek seti sessizce başka bir şeyi ölçer hale getirir."""
    for c in _ciftler():
        for s in ('a', 'b'):
            assert c[s]['tr_title'] == c[f'baslik_{s}'], \
                f"çift {c['no']}: {s} başlığı görünümle uyuşmuyor"


def _sozluk():
    views = []
    for p in ('data/rapor_gecmis.json', 'data/kritik3_gecmis.json'):
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                for r in json.load(f):
                    views.extend(r.get('views') or [])
    return O.OlaySozlugu(views)


def test_taban_cizgisinin_altina_dusulmez():
    """ÖLÇÜLDÜ (2026-10-07): sözlük penceresi bu sette sonucu DEĞİŞTİRMİYOR —
    güncel derlem (703 görünüm) ile ağustos derlemi (533) aynı skoru veriyor,
    sözlüksüz koşuda yalnızca dört-değerli 1 puan düşüyor. Bu yüzden taban
    çizgisi pencereye bağlı değildir."""
    ciftler = _ciftler()
    sz = _sozluk()
    yontem = {
        'same_event': lambda a, b: dedup.same_event(a, b, cross_day=True),
        'dört-değerli': lambda a, b: O.iliski_belirle(a, b, sozluk=sz)
        in (O.AYNI_GELISME, O.YENI_GELISME),
        'ayni_olay': lambda a, b: O.ayni_olay(a, b, sozluk=sz),
    }
    for ad, fn in yontem.items():
        dogru = sum(bool(fn(c['b'], c['a'])) == c['mukerrer'] for c in ciftler)
        assert dogru >= TABAN[ad], \
            f'{ad} gerileme: {dogru} < taban {TABAN[ad]}'


def test_ayni_olay_yanlis_birlestirme_yapmaz():
    """EN ZARARLI HATA SINIFI: iki farklı haberi birleştirmek, bir mükerreri
    kaçırmaktan kötüdür (bkz. src/dedup.py Kural 5). Manşet yolunun tanımı
    (`ayni_olay`) bu sette hiç sahte birleştirme yapmamalı."""
    sz = _sozluk()
    sahte = [c['no'] for c in _ciftler()
             if not c['mukerrer'] and O.ayni_olay(c['b'], c['a'], sozluk=sz)]
    assert not sahte, f'sahte birleştirme yapılan çiftler: {sahte}'
