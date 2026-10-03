"""AUDITOR MANŞET SEÇİM DENETİMİ — GÖRELİ GEREKÇENİN PUAN SINIRI.

3 Ekim 2026 raporunda günün ortak en yüksek puanlı iki temiz haberi
(93 puan, mukerrer=0) manşete girmedi ve manşet 87/83/78 ile kapandı.
Zincir: auditor, 93 puanlı Mississippi fidye yazılımı haberini madde 3 ile
("gövdedeki uluslararası operasyon ve kritik finansal zafiyet haberlerinin
gerisinde kalıyor") manşetten çıkardı — oysa gösterilen 12 gövde haberinin
yalnızca BİRİ (94) ondan yüksekti, yani maddenin kendi "ÇOĞU" ölçütü
sağlanmıyordu. Yerine giren 93 puanlı haber bir sonraki katmanda çapraz-gün
mükerreri çıkınca, kalıcı yasak yüzünden ilk haber yedek havuzunda bir daha
değerlendirilemedi ve manşet önce 60, sonra 78 puanlı habere düştü.

KURALLAR:
- Madde 3 GÖRELİDİR ve puanla sınanır: gösterilen gövde haberlerinin
  ÇOĞUNLUĞU işaretli manşetten yüksek puanlı değilse işaret REDDEDİLİR.
- Madde 1/2 (siber değil / olay yok) NİTELİK yargısıdır; sınanmaz ve manşet
  yasağı KALICIDIR. Madde 3 ile çıkarma kalıcı yasak üretmez.
- Madde bildirilmezse eski davranış korunur.
"""
from main import auditor_goreli_sinir
from src.config import (AUDITOR_GORELI_MADDE, AUDITOR_GOVDE_PENCERE,
                        get_kritik3_selection_audit_prompt)


def _kayitlar(puanlar):
    return {aid: {'toplam': p} for aid, p in puanlar.items()}


# 3 Ekim'in gerçek tablosu: işaretli manşet 93, gövde penceresi 12 haber.
EKIM3_GOVDE = {37: 94, 36: 93, 21: 91, 27: 90, 17: 84, 40: 80, 19: 78,
               6: 68, 16: 67, 1: 60, 3: 58, 15: 55}


def test_ekim3_vakasi_goreli_gerekce_reddedilir():
    kayitlar = _kayitlar({42: 93, **EKIM3_GOVDE})
    red, ayrinti = auditor_goreli_sinir(
        {42: AUDITOR_GORELI_MADDE}, kayitlar, list(EKIM3_GOVDE))
    assert red == [42]
    assert ayrinti == [(42, 93, 1, 12)]


def test_gercekten_govdenin_altindaysa_isaret_gecerli():
    """Gövdenin çoğunluğu daha yüksek puanlıysa madde 3 reddedilmez."""
    govde = {i: 90 for i in range(1, 10)}
    govde.update({10: 40, 11: 41, 12: 42})
    kayitlar = _kayitlar({99: 55, **govde})
    red, ayrinti = auditor_goreli_sinir(
        {99: AUDITOR_GORELI_MADDE}, kayitlar, list(govde))
    assert red == []
    assert ayrinti == []


def test_tam_yari_cogunluk_sayilmaz():
    """Yarısı değil, YARISINDAN FAZLASI gerekir."""
    govde = {1: 95, 2: 95, 3: 50, 4: 50}
    red, _ = auditor_goreli_sinir(
        {9: AUDITOR_GORELI_MADDE}, _kayitlar({9: 80, **govde}), list(govde))
    assert red == [9]


def test_nitelik_maddeleri_sinanmaz():
    """Madde 1/2 puanla çelişmez; sınır onlara dokunmaz."""
    kayitlar = _kayitlar({42: 93, **EKIM3_GOVDE})
    for madde in (1, 2, 4):
        red, _ = auditor_goreli_sinir({42: madde}, kayitlar,
                                      list(EKIM3_GOVDE))
        assert red == [], madde


def test_madde_bildirilmezse_eski_davranis():
    red, _ = auditor_goreli_sinir({}, _kayitlar({42: 93}), [1, 2, 3])
    assert red == []


def test_bos_govde_karsilastirilamaz_isaret_reddedilir():
    red, ayrinti = auditor_goreli_sinir(
        {42: AUDITOR_GORELI_MADDE}, _kayitlar({42: 93}), [])
    assert red == [42]
    assert ayrinti == [(42, 93, 0, 0)]


def test_pencere_promptla_ayni():
    """Çoğunluk, LLM'e GÖSTERİLEN gövde kümesi üzerinden sayılır."""
    govde = {i: 99 for i in range(1, 20)}          # 19 haber, hepsi yüksek
    kayitlar = _kayitlar({42: 50, **govde})
    red, _ = auditor_goreli_sinir({42: AUDITOR_GORELI_MADDE}, kayitlar,
                                  list(govde))
    assert red == []                                # pencere içinde de çoğunluk
    # Pencere dışındaki haberler sayıma GİRMEZ: ilk 12'si düşük olursa işaret
    # reddedilir, sonraki 7'si yüksek olsa bile.
    govde2 = {i: (10 if i <= 12 else 99) for i in range(1, 20)}
    red2, ayrinti2 = auditor_goreli_sinir(
        {42: AUDITOR_GORELI_MADDE}, _kayitlar({42: 50, **govde2}), list(govde2))
    assert red2 == [42]
    assert ayrinti2[0][3] == AUDITOR_GOVDE_PENCERE


def test_prompt_madde_alanini_istiyor():
    p = get_kritik3_selection_audit_prompt('MANŞET', 'GÖVDE')
    assert '"madde"' in p
    assert 'MADDE 3 PUANLA SINANIR' in p
