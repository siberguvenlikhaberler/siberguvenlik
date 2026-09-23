"""ARŞİV KAPSAM KÜNYESİ — kaynak satırı kalıbı ve payda ölçümü.

NEDEN VAR: yıl sonu analizi ham aylık toplamlara bakarsa "olay sayısı" yerine
"o ay kaç haber çekilebildiği"ni ölçer. Kapsam künyesi paydayı yazar. Kalıbın
kendisi de ölçüldü: sabit alan sayısı bekleyen bir kalıp 2026-09-23'te 70
kaydı sessizce "ayrışmadı" sayıyordu; gerçek bozuk sayısı 4'tü.
"""
import importlib.util
import pathlib

_yol = pathlib.Path(__file__).resolve().parent.parent / 'scripts' / 'arsiv_kapsam.py'
_spec = importlib.util.spec_from_file_location('arsiv_kapsam', _yol)
kapsam = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kapsam)

GECERLI = [
    ('(XXXXXXX, AÇIK -thehackernews.com, 13.02.2026)',
     'thehackernews.com', 'AÇIK'),
    ('(KAYNAK, AÇIK - bleepingcomputer.com, 01.03.2026)',
     'bleepingcomputer.com', 'AÇIK'),
    # 11 Mayıs: erişim etiketi ÖZET
    ('(KAYNAK, ÖZET -securityaffairs.com, 10.05.2026)',
     'securityaffairs.com', 'ÖZET'),
    # araya tam URL giren varyant
    ('(XXXXXXX, AÇIK - https://thehackernews.com/2026/02/x.html, '
     'thehackernews.com, 26.02.2026)', 'thehackernews.com', 'AÇIK'),
    # ilk alan kaynağın adı
    ('(THE HACKER NEWS, AÇIK -thehackernews.com, 05.04.2026)',
     'thehackernews.com', 'AÇIK'),
]

BOZUK = [
    '(XXXXXXX, AÇIK -, )',
    '(XXXXXXX, AÇIK -csoonline.2026)',
    'Bu bir paragraf cümlesidir.',
]


def test_gecerli_kaynak_satirlari_ayrisir():
    for satir, alan, erisim in GECERLI:
        m = kapsam._KAYNAK_RE.match(satir)
        assert m, f'ayrışmadı: {satir}'
        assert m.group(1) == erisim
        assert m.group(2) == alan


def test_bozuk_satirlar_ayrismaz():
    for satir in BOZUK:
        assert not kapsam._KAYNAK_RE.match(satir), f'yanlışlıkla ayrıştı: {satir}'


def test_gercek_arsivde_ayrismayan_orani_dusuk():
    """Kalıp bozulursa sayımın paydası sessizce şişer; eşik bunu yakalar."""
    k = kapsam.olc()
    ayrismayan = sum(k['kaynak_ayrismayan'].values())
    assert k['kayit'] > 4000, 'arşiv beklenenden küçük'
    assert ayrismayan / k['kayit'] < 0.01, (
        f'{ayrismayan}/{k["kayit"]} kayıtta kaynak satırı ayrışmıyor')


def test_seyrek_ve_yogun_donem_ayri_raporlanir():
    """İki dönemin ham sayımı kıyaslanamaz; künye ikisini ayrı tutmalı."""
    k = kapsam.olc()
    s, y = k['donem']['seyrek'], k['donem']['yogun']
    assert s['gun_basina'] < 5 < y['gun_basina'], (s, y)
    assert k['eksik_gun'], 'eksik gün listesi boş — ölçüm yapılmamış olabilir'
