"""YIL SONU HAZIRLIĞI — adım SIRASI ve varsayılan kuru koşu.

NEDEN VAR: iki adım arşive YAZAR (önem alanı üretim hattından, varlık alanı
`varlik_cikar`), iki adım arşivden TÜRETİR (`arsiv_kapsam`, `olay_kaydi`).
Türetenler yazanlardan önce koşarsa hata vermez — sessizce eski arşivi ölçer
ve yıl sonu raporu eski sayılarla kurulur. Sıra bu yüzden sabitlenir.
"""
import importlib.util
import pathlib
import sys

_yol = (pathlib.Path(__file__).resolve().parent.parent
        / 'scripts' / 'yilsonu_hazirla.py')


def _yukle(argv):
    eski = sys.argv
    sys.argv = argv
    try:
        spec = importlib.util.spec_from_file_location('yilsonu_hazirla', _yol)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m
    finally:
        sys.argv = eski


def _komutlar(m):
    return [' '.join(k) for _, k, _ in m.ADIMLAR]


def test_yazanlar_turetenlerden_once_kosar():
    k = _komutlar(_yukle(['yilsonu_hazirla.py', '--yaz']))
    yazan = max(i for i, c in enumerate(k) if 'varlik_cikar' in c)
    for tureten in ('arsiv_kapsam', 'olay_kaydi'):
        i = next(i for i, c in enumerate(k) if tureten in c)
        assert i > yazan, f'{tureten} varlık yazımından önce koşuyor'


def test_yaz_bayragi_yoksa_hicbir_adim_yazmaz():
    for _, komut, _ in _yukle(['yilsonu_hazirla.py']).ADIMLAR:
        assert '--yaz' not in komut, komut


def test_yaz_bayragiyla_yazan_adimlar_yazar():
    k = _komutlar(_yukle(['yilsonu_hazirla.py', '--yaz']))
    for betik in ('varlik_cikar', 'arsiv_kapsam', 'olay_kaydi'):
        c = next(c for c in k if betik in c)
        assert c.endswith('--yaz'), c
    # `retro_etiket durum/denetim` ASLA yazmaz — okuma adımlarıdır.
    for c in k:
        if 'retro_etiket' in c:
            assert '--yaz' not in c, c


def test_adimlar_dort_betigi_de_kapsar():
    k = _komutlar(_yukle(['yilsonu_hazirla.py', '--yaz']))
    for betik in ('retro_etiket.py durum', 'retro_etiket.py denetim',
                  'varlik_cikar.py', 'arsiv_kapsam.py', 'olay_kaydi.py'):
        assert any(betik in c for c in k), betik
