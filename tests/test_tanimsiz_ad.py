"""TANIMSIZ AD TARAYICISI — NameError üretimde patlamadan yakalanmalı.

NEDEN VAR — ÖLÇÜLEN VAKA (2026-09-30 koşusu ÇÖKTÜ): `_kritik3_cesitlilik`
çağrısına `recent_report_views` geçiriliyordu ama o ad `create_html`
kapsamında tanımlı değildi (doğrusu `recent_report`). 682 birim testi
geçti çünkü `create_html` uçtan uca LLM gerektiriyor ve testlerde hiç
koşmuyor; hata ancak sabah 09:00 üretim koşusunda, 15 dakikalık LLM
işinin SONUNDA ortaya çıktı ve o günün raporu üretilemedi.

Tarayıcı `symtable` ile çalışır: her kapsamda REFERANS verilen ama o
kapsamda, kapsayan kapsamlarda, modül düzeyinde ve builtins'te BULUNMAYAN
adları bildirir. Bu, çalıştırmadan yakalanabilecek tek hata sınıfıdır ve
projenin LLM'siz test edilemeyen yollarını kapsar.
"""
import builtins
import pathlib
import symtable

_KOK = pathlib.Path(__file__).resolve().parent.parent
_MUAF = {'__file__', '__name__', '__doc__', '__package__', '__spec__',
         '__builtins__', '__loader__'}


def _tanimsiz_adlar(kaynak, dosya):
    st = symtable.symtable(kaynak, dosya, 'exec')
    bilinen_modul = {s.get_name() for s in st.get_symbols()}
    bi = set(dir(builtins)) | _MUAF
    bulunan = []

    def gez(tablo, ust):
        kapsam = {s.get_name() for s in tablo.get_symbols()
                  if s.is_assigned() or s.is_parameter() or s.is_imported()}
        gorunur = ust | kapsam
        for s in tablo.get_symbols():
            ad = s.get_name()
            if (s.is_referenced() and ad not in gorunur
                    and ad not in bilinen_modul and ad not in bi):
                bulunan.append(f'{dosya}:{tablo.get_lineno()} '
                               f'{tablo.get_name()}() → {ad}')
        for alt in tablo.get_children():
            # Sınıf gövdesindeki adlar metotlardan GÖRÜNMEZ.
            gez(alt, gorunur if tablo.get_type() != 'class' else ust)

    gez(st, set())
    return bulunan


def _dosyalar():
    return ([_KOK / 'main.py'] + sorted((_KOK / 'src').glob('*.py'))
            + sorted((_KOK / 'scripts').glob('*.py')))


def test_hicbir_dosyada_tanimsiz_ad_yok():
    hatalar = []
    for yol in _dosyalar():
        hatalar += _tanimsiz_adlar(yol.read_text(encoding='utf-8'), yol.name)
    assert not hatalar, 'tanımsız ad(lar):\n  ' + '\n  '.join(hatalar)


def test_tarayici_gercek_vakayi_yakaliyor():
    """Regresyon: tarayıcı 30 Eylül'ü çökerten hatayı görebilmeli."""
    kaynak = 'def f():\n    a = 1\n    return g(a, recent_report_views)\n'
    assert any('recent_report_views' in h
               for h in _tanimsiz_adlar(kaynak, 'x.py'))
