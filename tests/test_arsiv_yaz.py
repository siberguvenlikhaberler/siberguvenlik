"""ARŞİVE GÜVENLİ YAZIM — tek geri döndürülemez dosyanın koruması.

NEDEN VAR: beş betik 10,6 MB'lık arşivin tamamını yeniden yazıyor ve bunu
düz `open(...,'w')` ile yapıyordu; workflow'un 25 dakikalık sınırı yazımın
ortasında işi öldürürse dosya yarım kalıp commit ediliyordu. `main.py`
aynı dosya için zaten atomik yazım kullanıyordu — betikler kullanmıyordu.
"""
import importlib.util
import pathlib

import pytest

_yol = (pathlib.Path(__file__).resolve().parent.parent
        / 'scripts' / 'arsiv_yaz.py')
_spec = importlib.util.spec_from_file_location('arsiv_yaz', _yol)
yaz = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(yaz)

ICERIK = ['[ 1] Birinci haber\n', 'Paragraf.\n', '» varlik | sektor=kamu\n',
          '[ 2] İkinci haber\n', 'Paragraf.\n']


def test_ustveri_eklemek_serbesttir(tmp_path):
    p = tmp_path / 'arsiv.txt'
    p.write_text(''.join(ICERIK), encoding='utf-8')
    yeni = ICERIK + ['» teknik | cve=CVE-2026-1\n']
    assert yaz.guvenli_yaz(str(p), yeni) == 2
    assert p.read_text(encoding='utf-8') == ''.join(yeni)


def test_kayit_dusuren_yazim_reddedilir(tmp_path):
    """Ayrıştırma hatası dosyayı budamak üzereyse dosyaya DOKUNULMAZ."""
    p = tmp_path / 'arsiv.txt'
    p.write_text(''.join(ICERIK), encoding='utf-8')
    with pytest.raises(RuntimeError, match='YAZIM REDDEDİLDİ'):
        yaz.guvenli_yaz(str(p), ICERIK[:3])
    assert p.read_text(encoding='utf-8') == ''.join(ICERIK)


def test_gecici_dosya_birakilmaz(tmp_path):
    p = tmp_path / 'arsiv.txt'
    p.write_text(''.join(ICERIK), encoding='utf-8')
    yaz.guvenli_yaz(str(p), ICERIK)
    assert [f.name for f in tmp_path.iterdir()] == ['arsiv.txt']


def test_yeni_dosya_yazilabilir(tmp_path):
    p = tmp_path / 'yeni.txt'
    assert yaz.guvenli_yaz(str(p), ICERIK) == 2
