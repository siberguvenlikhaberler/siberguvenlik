"""MANŞET DOMİNANS KAPISI — domine edilen manşet takas edilir.

Vakalar gerçek üretim günlerinden alındı; üçü de aynı sınıf hatanın
tekrarıdır ve üçünde de prompt'a yazılı "zayıf manşet" ölçütü tutmamıştır:

  2026-09-09  F5 BIG-IP rootkit (85, zafiyet_aktif_apt) manşet oldu;
              Slim Spider (85, nation_state_apt) gövdedeydi.
  2026-09-16  PhantomRaven (77, zafiyet_aktif_apt) manşet oldu;
              BambooToken (86, nation_state_apt) gövdedeydi.
  2026-09-17  Pixel modem sıfır-günü (89, zafiyet_aktif_apt) manşet oldu;
              Chosen Brick (94, nation_state_apt) gövdedeydi.
"""
import main


def _sistem():
    s = main.HaberSistemi.__new__(main.HaberSistemi)
    s._olay_sozlugu = None
    s._manset_yasak = set()
    s._manset_izi = []
    s._enforce_kritik3_paragraph_length = lambda *a, **k: None
    s._manset_karar_kaydet = lambda *a, **k: None
    return s


# Her haber BELİRGİN biçimde farklı olmalı: jenerik metinler ("Olay 1",
# "Olay 2") aynı-olay muafiyetini tetikleyip takası engelliyordu.
_METIN = {
    1: ('Sogou girdi yöntemi arka kapısı', 'Sogou yazılımına arka kapı yerleştirildi'),
    2: ('Pixel modem sıfır gün yaması', 'Google Pixel modem bileşeninde sıfır gün yamalandı'),
    3: ('NightEagle Rus şirketlerinde', 'NightEagle grubu Rus şirketlerini hedef aldı'),
    4: ('Chosen Brick casus yazılımı', 'İran menşeli Chosen Brick casus yazılımı ifşa edildi'),
    5: ('Revolut veri sızıntısı', 'Revolut müşteri verileri İtalyan hesaplarıyla sızdırıldı'),
}


def _calistir(s, top3, top10, records, icerik=None):
    if icerik is None:
        icerik = {}
        for i in set(top3) | set(top10):
            b, p = _METIN.get(i, (f'Benzersiz konu {i}', f'Ayrik olay {i} kaydi'))
            icerik[i] = {'tr_title': b, 'paragraph': p}
    art = {i: {'title': c['tr_title'], 'full_text': c['paragraph']}
           for i, c in icerik.items()}
    return s._kritik3_dominans_takasi(top3, top10, [], records, icerik, art)


def test_17_eylul_pixel_takas_edilir():
    s = _sistem()
    records = {1: {'kat': 'nation_state_apt', 'toplam': 95},        # SparroWocky
               2: {'kat': 'zafiyet_aktif_apt', 'toplam': 89},       # Pixel
               3: {'kat': 'nation_state_apt', 'toplam': 89},        # NightEagle
               4: {'kat': 'nation_state_apt', 'toplam': 94}}        # Chosen Brick
    t3, t10, _ = _calistir(s, [1, 2, 3], [4], records)
    assert 2 not in t3, 'Pixel manşette kaldı'
    assert 4 in t3, 'Chosen Brick manşete alınmadı'
    assert 2 == t10[0], 'düşen manşet gövdenin başına dönmedi'
    assert len(t3) == 3


def test_16_eylul_phantomraven_takas_edilir():
    s = _sistem()
    records = {1: {'kat': 'nation_state_apt', 'toplam': 87},
               2: {'kat': 'kolluk_operasyonu', 'toplam': 89},
               3: {'kat': 'zafiyet_aktif_apt', 'toplam': 77},   # PhantomRaven
               4: {'kat': 'nation_state_apt', 'toplam': 86}}    # BambooToken
    t3, _, _ = _calistir(s, [1, 2, 3], [4], records)
    assert 3 not in t3 and 4 in t3


def test_09_eylul_esit_puanda_kategori_belirler():
    """F5 (85, zafiyet_aktif_apt) ↔ Slim Spider (85, nation_state_apt):
    puan eşit, kategori önceliği üstün → takas."""
    s = _sistem()
    records = {1: {'kat': 'zafiyet_aktif_apt', 'toplam': 85},
               2: {'kat': 'nation_state_apt', 'toplam': 93},
               3: {'kat': 'kolluk_operasyonu', 'toplam': 97},
               4: {'kat': 'nation_state_apt', 'toplam': 85}}
    t3, _, _ = _calistir(s, [1, 2, 3], [4], records)
    assert 1 not in t3 and 4 in t3


def test_saglikli_gunde_takas_olmaz():
    """15 Eylül: Black Axe (kolluk, 94) manşette; havuzda önceliği yüksek ama
    puanı 94'e ulaşan aday YOK → dokunulmaz."""
    s = _sistem()
    records = {1: {'kat': 'stratejik_kurum_saldirisi', 'toplam': 92},
               2: {'kat': 'stratejik_kurum_saldirisi', 'toplam': 91},
               3: {'kat': 'kolluk_operasyonu', 'toplam': 94},
               4: {'kat': 'nation_state_apt', 'toplam': 88},
               5: {'kat': 'politika_hukuk', 'toplam': 90}}
    t3, _, _ = _calistir(s, [1, 2, 3], [4, 5], records)
    assert t3 == [1, 2, 3]


def test_dusuk_puanli_aday_takas_etmez():
    """Kategori önceliği yüksek ama puanı DÜŞÜK aday manşeti alamaz."""
    s = _sistem()
    records = {1: {'kat': 'kolluk_operasyonu', 'toplam': 90},
               2: {'kat': 'veri_ihlali', 'toplam': 88},
               3: {'kat': 'tedarik_zinciri', 'toplam': 85},
               4: {'kat': 'nation_state_apt', 'toplam': 60}}
    t3, _, _ = _calistir(s, [1, 2, 3], [4], records)
    assert 4 not in t3


def test_mukerrer_ve_yasakli_aday_kullanilmaz():
    s = _sistem()
    s._manset_yasak = {5}
    records = {1: {'kat': 'zafiyet_aktif_apt', 'toplam': 80},
               2: {'kat': 'kolluk_operasyonu', 'toplam': 90},
               3: {'kat': 'veri_ihlali', 'toplam': 88},
               4: {'kat': 'nation_state_apt', 'toplam': 95, 'mukerrer': 1},
               5: {'kat': 'nation_state_apt', 'toplam': 95}}
    t3, _, _ = _calistir(s, [1, 2, 3], [4, 5], records)
    assert 4 not in t3 and 5 not in t3, 'mükerrer/yasaklı aday manşete alındı'
    assert t3 == [1, 2, 3]


def test_kritik3_disi_kategori_aday_olamaz():
    s = _sistem()
    records = {1: {'kat': 'zafiyet_aktif_apt', 'toplam': 80},
               2: {'kat': 'kolluk_operasyonu', 'toplam': 90},
               3: {'kat': 'veri_ihlali', 'toplam': 88},
               4: {'kat': 'zafiyet_rutin', 'toplam': 99}}
    t3, _, _ = _calistir(s, [1, 2, 3], [4], records)
    assert 4 not in t3


def test_manset_sayisi_hep_uc_kalir():
    s = _sistem()
    records = {1: {'kat': 'zafiyet_aktif_apt', 'toplam': 70},
               2: {'kat': 'zafiyet_aktif_apt', 'toplam': 71},
               3: {'kat': 'zafiyet_aktif_apt', 'toplam': 72},
               4: {'kat': 'nation_state_apt', 'toplam': 90},
               5: {'kat': 'politika_hukuk', 'toplam': 91}}
    t3, t10, _ = _calistir(s, [1, 2, 3], [4, 5], records)
    assert len(t3) == 3 and len(set(t3)) == 3


def test_eksik_manset_dokunulmaz():
    s = _sistem()
    records = {1: {'kat': 'zafiyet_aktif_apt', 'toplam': 70},
               4: {'kat': 'nation_state_apt', 'toplam': 90}}
    t3, _, _ = _calistir(s, [1], [4], records)
    assert t3 == [1]


def test_mansette_temsil_edilen_olay_ikinci_kez_manset_olamaz():
    """Muafiyet olmadan kural, manşetteki olayın gövdedeki kopyasını manşete
    taşırdı. 10 Eylül'de tam bu risk vardı: aynı Chrome sıfır-gün olayı hem
    manşette hem gövdedeydi ve gövdedeki kopya daha yüksek puanlıydı."""
    s = _sistem()
    icerik = {
        1: {'tr_title': 'Çinli gruplar Chrome sıfır gün zincirini kullandı',
            'paragraph': 'BlueMoon istismar kitiyle Chrome sıfır günü kullanıldı'},
        2: {'tr_title': 'Xinbi dolandırıcılık pazarı çökertildi',
            'paragraph': 'ABD Xinbi Guarantee pazarını çökertti'},
        3: {'tr_title': 'Brezilya hükümet sunucuları ele geçirildi',
            'paragraph': 'Brezilya hükümet sunucuları kimlik avı için kullanıldı'},
        4: {'tr_title': 'Çin bağlantılı gruplar Chrome sıfır gün kitini paylaştı',
            'paragraph': 'BlueMoon istismar kiti Chrome sıfır günü ile kullanıldı'},
    }
    records = {1: {'kat': 'nation_state_apt', 'toplam': 97},
               2: {'kat': 'kolluk_operasyonu', 'toplam': 97},
               3: {'kat': 'stratejik_kurum_saldirisi', 'toplam': 90},
               4: {'kat': 'nation_state_apt', 'toplam': 99}}
    t3, _, _ = _calistir(s, [1, 2, 3], [4], records, icerik)
    assert 4 not in t3, 'manşetteki olayın kopyası manşete taşındı'
