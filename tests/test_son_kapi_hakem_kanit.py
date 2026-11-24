"""SON KAPI HAKEMİNİN MANŞET İŞARETİ KANITLA SINANIR (2026-11-24).

Bulgaristan'daki beş yıllık hükümet casusluğu (96) son kapıdaki LLM hakemi
tarafından "Infoblox tedarik zinciri ve SharePoint veri ihlali" ile aynı
olay sayılıp manşetten düştü; iki ad da metinde geçmiyordu.
"""
import inspect

import main
from src import olay_iliski as oi

BULGAR = {
    'tr_title': "Bulgaristan'da Beş Yıl Süren Hükümet Veri İhlalinin Tespiti",
    'paragraph': ("Bulgaristan İnovasyon ve Dijital Dönüşüm Bakanlığı, 2021 "
                  "yılından bu yana hükümet veri tabanlarından 130 GB belge "
                  "indirildiğini açıklamıştır."),
    'title': 'Bulgaria Discovers Massive Government Breach',
    'full_text': ("Minister Ivan Vassilev said that since 2021 more than "
                  "130 GB of documents had been downloaded."),
}
INFOBLOX = {
    'tr_title': 'Infoblox Tedarik Zinciri İhlali Sonucu Hassas Verilerin Sızdırılması',
    'paragraph': ("Siber güvenlik şirketi Infoblox, bir veri taşıma "
                  "tedarikçisinin sistemlerinin ele geçirilmesi sonucunda "
                  "müşteri verilerinin sızdığını açıklamıştır."),
    'title': 'Infoblox confirms supply chain breach',
    'full_text': 'Infoblox said a data migration vendor was compromised.',
}
EQUINOR_A = {
    'tr_title': "Norveçli Enerji Devi Equinor'un Siber Saldırıya Uğraması",
    'paragraph': ("Norveç merkezli enerji devi Equinor, 17 Kasım 2026 "
                  "tarihinde siber saldırıya uğradığını açıklamıştır."),
    'title': 'Equinor under cyberattack', 'full_text': '',
}
EQUINOR_B = {
    'tr_title': "Equinor'a Yönelik Siber Saldırının Ayrıntıları",
    'paragraph': ("Gaz tedarikçisi Equinor, saldırının üretimi "
                  "etkilemediğini bildirmiştir."),
    'title': 'Norwegian Gas Giant Equinor Says It Is Under Cyberattack',
    'full_text': 'The company Equinor said production was not affected.',
}


def test_bulgaristan_isareti_kanitsiz():
    kabul, _ = oi.capraz_gun_kaniti(
        BULGAR, INFOBLOX,
        ortak='Infoblox tedarik zinciri ve SharePoint veri ihlali')
    assert not kabul


def test_ortak_ad_iki_metinde_varsa_kabul():
    kabul, gerekce = oi.capraz_gun_kaniti(
        EQUINOR_B, EQUINOR_A,
        ortak="Equinor'un 17 Kasım 2026 tarihli siber saldırısı")
    assert kabul and 'equinor' in gerekce


def test_ay_ve_isletim_sistemi_adi_kanit_degil():
    for s in ('kasım', 'november', 'android', 'windows'):
        assert s[:8] in oi._KANIT_JENERIK


def test_son_kapi_hakemi_manseti_kanitla_sinar():
    kaynak = inspect.getsource(main.HaberSistemi._son_mukerrer_kapisi)
    i = kaynak.index('_mukerrer_llm_hakem(ciftler)')
    parca = kaynak[i:i + 2500]
    assert 'capraz_gun_kaniti' in parca and 'manset_kume' in parca
