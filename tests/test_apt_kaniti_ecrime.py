"""APT ATIF KANITI — eCrime adlandırması tek başına devlet atfı sayılmaz.

Yaygın aktör taksonomisinde hayvan son eki aktörün TÜRÜNÜ belirtir: *Bear
(Rusya), *Panda (Çin), *Kitten (İran), *Chollima (K. Kore) devlet bağlantılı;
*Spider finansal motivasyonlu suç gruplarını, *Jackal hacktivist/suç
operasyonlarını gösterir.

ÖLÇÜLDÜ (2026-09-09): "Slim Spider Steals Crypto Custody Secrets From Brazilian
Financial Institutions" — finansal motivasyonlu bir grup — metinde hiçbir atıf
ifadesi olmadan yalnızca 'slimspider' aktör kimliği sayesinde nation_state_apt
önceliğini (10) korudu ve manşet havuzunda kaldı.

KAPSAM (son 30 günün 554 yayımlanmış haberi): atıf ifadesi olmadan yalnızca
aktör kimliğinden geçen 16 kayıt var; bunların yalnızca 2'si bu kalıpta.
"""
import main


def _s():
    return main.HaberSistemi.__new__(main.HaberSistemi)


def test_spider_tek_basina_kanit_sayilmaz():
    s = _s()
    assert not s._has_apt_evidence(
        'Slim Spider Steals Crypto Custody Secrets From Brazilian Financial '
        'Institutions',
        'CrowdStrike said Slim Spider has targeted Brazilian banks since March, '
        'stealing digital asset custody secrets for financial gain.')


def test_jackal_tek_basina_kanit_sayilmaz():
    s = _s()
    assert not s._has_apt_evidence(
        'Global Crackdown on West African Crime Networks Leads to 58 Arrests',
        'Operation Jackal targeted online fraud networks across four countries.')


def test_mesru_aktor_kimlikleri_etkilenmez():
    """Kural dar olmalı: UNC/Storm/UAT/Cl0p gibi kimlikler geçmeye devam eder."""
    s = _s()
    for ttl, gov in (
        ('UAT-10147: Chinese-speaking adversary integrates agentic AI',
         'UAT-10147 deployed SPECTRE against exposed servers.'),
        ('CopyCop Targets AI Investment in Armenia',
         'Storm-1516 ran the influence operation.'),
        ('US Bank investigates LockBit claims',
         'LockBit listed the bank on its leak site.'),
    ):
        assert s._has_apt_evidence(ttl, gov), ttl


def test_acik_atif_varsa_spider_adi_engellemez():
    """(a) yolu bağımsızdır: metinde gerçek atıf ifadesi varsa kural devreye
    girmez — aktör adının eCrime kalıbında olması haberi cezalandırmaz."""
    s = _s()
    assert s._has_apt_evidence(
        'Wizard Spider linked to Russian state services',
        'Researchers said the Russia-linked group operated with state backing.')


def test_devlet_hayvan_ekleri_kanit_olmaya_devam_eder():
    s = _s()
    assert s._has_apt_evidence('Fancy Bear hits ministry',
                               'Fancy Bear targeted the ministry network.')
    assert s._has_apt_evidence('Charming Kitten phishing wave',
                               'Charming Kitten sent lures to researchers.')


# ── Skorlama logunda görünürlük ───────────────────────────────────────────
# attr_guard YALNIZCA zafiyet_rutin'e indirilenleri sayar; nation_state_apt
# dalı kategoriyi değiştirmediği için kararı hiç yazmıyordu. Ölçüm sırasında
# (2026-09-18) bu, "hiçbir katman iddiayı sorgulamamış" sanılmasına yol açtı.

def test_apt_dogrulanmadi_loga_yazilir(tmp_path, monkeypatch):
    s = _s()
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'data').mkdir()
    articles = [{'id': 1, 'source': 'X', 'title': 'A'},
                {'id': 2, 'source': 'Y', 'title': 'B'}]
    records = {
        1: {'kat': 'nation_state_apt', 'toplam': 90, 's': 1, 'e': 1, 'a': 1,
            'k': 1, 'siber': 1, 'mukerrer': 0, 'apt_dogrulanmadi': True},
        2: {'kat': 'nation_state_apt', 'toplam': 90, 's': 1, 'e': 1, 'a': 1,
            'k': 1, 'siber': 1, 'mukerrer': 0},
    }
    s._write_scoring_log(articles, records, [1], [2], [], {})
    import json
    satir = [json.loads(l) for l in
             (tmp_path / 'data' / 'skorlama_log.jsonl').read_text(
                 encoding='utf-8').splitlines() if l.strip()]
    bayrak = {r['id']: r.get('apt_dogrulanmadi') for r in satir}
    assert bayrak[1] == 1, 'doğrulanmamış APT kararı loga yazılmadı'
    assert bayrak[2] == 0
