"""Koşu süre bekçisi (2026-11-06): yoğun günde rapor süre sınırına yetişsin
diye YALNIZCA kozmetik onarımlar atlanır."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import main


def _sistem():
    s = main.HaberSistemi.__new__(main.HaberSistemi)
    s._atlanan_onarimlar = []
    s._gemini_call_json = lambda *a, **k: (_ for _ in ()).throw(
        AssertionError('süre dolduktan sonra LLM çağrılmamalı'))
    return s


def test_esik_asilinca_kozmetik_onarim_llm_cagirmaz(monkeypatch):
    monkeypatch.setattr(main, '_KOSU_T0', main.time.time() - 60 * 60)
    s = _sistem()
    icerik = {1: {'tr_title': 'Bir İki Üç Dört Beş Altı Yedi Sekiz Dokuz On',
                  'paragraph': 'kısa paragraf.'}}
    s._enforce_baslik_uzunlugu([1], icerik, {})
    s._enforce_govde_paragraf_uzunlugu([1], icerik, {})
    s._enforce_kritik3_paragraph_length([1], icerik, {})
    gecisler = [x['gecis'] for x in s._atlanan_onarimlar]
    assert gecisler == ['Başlık kısaltma', 'Gövde paragraf uzatma',
                        'Manşet paragraf uzatma']
    assert icerik[1]['tr_title'].startswith('Bir İki')   # dokunulmadı


def test_esik_asilmadan_atlama_yok(monkeypatch):
    monkeypatch.setattr(main, '_KOSU_T0', main.time.time())
    assert not main.sure_doldu_mu(main.KOZMETIK_ONARIM_SINIRI_DK, 'x')


def test_esikler_is_akisi_sinirinin_altinda():
    import re
    yml = (Path(__file__).parent.parent / '.github/workflows/daily.yml'
           ).read_text('utf-8')
    sinir = int(re.search(r'timeout-minutes:\s*(\d+)', yml).group(1))
    assert main.KOZMETIK_ONARIM_SINIRI_DK < main.MANSET_ONARIM_SINIRI_DK
    # Manşet onarımı kesildikten sonra zorunlu işe en az 10 dk kalmalı.
    assert main.MANSET_ONARIM_SINIRI_DK <= sinir - 10


def test_rapor_sonrasi_adim_hatasi_raporu_dusurmez(capsys):
    def patla():
        raise RuntimeError('disk dolu')
    assert main._rapor_sonrasi_adim('Arşiv yazımı', patla) is None
    out = capsys.readouterr().out
    assert '::warning' in out and 'Arşiv yazımı' in out


def test_rapor_yazildiktan_sonra_dogrudan_cagri_yok():
    """create_html ve legacy yolda rapor yazıldıktan sonra geçmiş/arşiv
    adımları yalnızca _rapor_sonrasi_adim üzerinden çağrılır."""
    import re
    kod = (Path(__file__).parent.parent / 'main.py').read_text('utf-8')
    for ad in ('_save_kritik3_history', '_save_report_history',
               'save_summary_to_archive', '_cleanup_old_reports'):
        dogrudan = re.findall(r'^\s+self\.' + ad + r'\(', kod, re.M)
        assert not dogrudan, ad
