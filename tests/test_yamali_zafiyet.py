"""YAMALANMIŞ VARSAYIMSAL ZAFİYET başka kategori kılığında manşete çıkamaz.

ÖLÇÜLDÜ (2026-11-20): WinGet moderasyon aracındaki yamalanmış, istismar
kanıtı olmayan açık `tedarik_zinciri` etiketiyle 94 puan alıp ikinci manşet
oldu. Gövde deposunda (2.129 kayıt) kural 6 kayda uyar: 5'i zaten zafiyet,
tek istisna bu vaka.
"""
import main


def _s():
    return main.HaberSistemi.__new__(main.HaberSistemi)


WINGET_BASLIK = ("A single pull request could have handed attackers the keys "
                 "to Microsoft's software supply chain")
WINGET_GOVDE = (
    "A now patched vulnerability in WinGet's moderation tooling could have "
    "handed attackers a Microsoft employee's GitHub credentials through a "
    "single pull request. There is currently no evidence that the flaw has "
    "been exploited in the wild.")


def test_winget_vakasi_zafiyet_sayilir():
    assert _s()._yamali_varsayimsal_zafiyet(WINGET_BASLIK, WINGET_GOVDE)


def test_gercek_olay_varsa_sayilmaz():
    assert not _s()._yamali_varsayimsal_zafiyet(
        "Hackers breached Acme via a now-patched flaw",
        "Attackers stole customer data. The now patched bug could have let "
        "anyone log in; the company confirmed victims were notified.")


def test_aktif_istismar_varsa_sayilmaz():
    assert not _s()._yamali_varsayimsal_zafiyet(
        "Vendor patched flaw exploited in the wild",
        "The flaw has been patched but was actively exploited and could "
        "allow remote code execution.")


def test_varsayim_yoksa_sayilmaz():
    """Yalnızca 'yamalandı' demek yetmez — olay haberi de yamadan söz eder."""
    assert not _s()._yamali_varsayimsal_zafiyet(
        "Supply chain attack on build server",
        "Malicious code was pushed to the registry; the issue has since been "
        "fixed.")


def test_kategori_indirilir():
    s = _s()
    rec = {'kat': 'tedarik_zinciri', 's': 30, 'e': 25, 'a': 20, 'k': 19}
    inen = s._enforce_apt_attribution(
        {38: rec}, {38: {'title': WINGET_BASLIK, 'full_text': WINGET_GOVDE}})
    assert 38 in inen and rec['kat'] == 'zafiyet_rutin'
