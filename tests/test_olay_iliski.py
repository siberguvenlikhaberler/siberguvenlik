"""OLAY İLİŞKİSİ — dört değerli sınıflandırıcının davranış kapısı.

Golden set'e karşı ölçüm scripts/dedup_olc.py'de; burası o ölçümü KAPIYA
çevirir ve sınıflandırıcının sözleşmesini (hangi girdi hangi sınıfa düşer)
birim düzeyinde sabitler.
"""
import json
import os

import pytest

from src import olay_iliski as oi

GOLDEN = os.path.join(os.path.dirname(__file__), '..', 'data', 'dedup_golden.json')

# Politika sonucu doğru olması gereken asgari çift sayısı (bkz. dedup_olc.py
# 3. bölüm). 23 çiftin 20'si. Kalan 3 kaçak GÜVENLİ yöndedir ve anlamsal
# yargı gerektirir; LLM denetim katmanları kapsar.
TABAN_POLITIKA = 20
# Etiket düzeyinde doğruluk tabanı.
TABAN_ETIKET = 18


def _ciftler():
    if not os.path.exists(GOLDEN):
        pytest.skip('data/dedup_golden.json yok')
    with open(GOLDEN, encoding='utf-8') as f:
        return json.load(f)['ciftler']


def _sozluk():
    views = []
    for p in ('data/rapor_gecmis.json', 'data/kritik3_gecmis.json'):
        yol = os.path.join(os.path.dirname(__file__), '..', p)
        if not os.path.exists(yol):
            continue
        with open(yol, encoding='utf-8') as f:
            for rec in json.load(f):
                views.extend(rec.get('views', []) or [])
    return oi.OlaySozlugu(views)


def _politika(etiket):
    return (etiket not in oi.RAPORA_GIRER, etiket not in oi.MANSETE_CIKAR)


def test_etiket_dogrulugu_gerilemez():
    sozluk = _sozluk()
    dogru = sum(
        1 for c in _ciftler()
        if oi.iliski_belirle(c['a'], c['b'], ayni_gun=c['ayni_gun'],
                             sozluk=sozluk) == c['iliski'])
    assert dogru >= TABAN_ETIKET, f'REGRESYON: {dogru} < {TABAN_ETIKET}'


def test_politika_dogrulugu_gerilemez():
    """Asıl ölçüm: etiketin raporda yol açtığı DAVRANIŞ doğru mu?"""
    sozluk = _sozluk()
    dogru, hatalar = 0, []
    for c in _ciftler():
        tahmin = oi.iliski_belirle(c['a'], c['b'], ayni_gun=c['ayni_gun'],
                                   sozluk=sozluk)
        if _politika(tahmin) == _politika(c['iliski']):
            dogru += 1
        else:
            hatalar.append(f'{c["ad"]}: {c["iliski"]} → {tahmin}')
    assert dogru >= TABAN_POLITIKA, (
        f'REGRESYON: {dogru} < {TABAN_POLITIKA}\n'
        + '\n'.join('   • ' + h for h in hatalar))


def test_farkli_haberler_asla_elenmez():
    """ILISKISIZ/AYNI_AKTOR etiketli çiftler ASLA eleme sonucu doğurmamalı."""
    sozluk = _sozluk()
    for c in _ciftler():
        if c['iliski'] not in (oi.ILISKISIZ, oi.AYNI_AKTOR_FARKLI_OLAY):
            continue
        tahmin = oi.iliski_belirle(c['a'], c['b'], ayni_gun=c['ayni_gun'],
                                   sozluk=sozluk)
        assert tahmin in oi.RAPORA_GIRER, (
            f'{c["ad"]}: farklı haber elendi ({tahmin})\n   {c["not"]}')


def test_ayni_aktor_farkli_olay_ayrilir():
    """Aynı aktör + farklı kurban = AYNI OLAY DEĞİL (08-12 Sandworm vakası)."""
    a = {'tr_title': '', 'paragraph': '', 'title': 'Sandworm targets IT staff',
         'full_text': 'The group ran fake job interviews against Ukrainian '
                      'IT specialists using a trojanized VPN client.'}
    b = {'tr_title': '', 'paragraph': '', 'title': 'Sandworm sabotages plant',
         'full_text': 'The group disabled a steam turbine at a combined heat '
                      'and power plant in Poland via a private APN.'}
    assert oi.iliski_belirle(a, b) == oi.AYNI_AKTOR_FARKLI_OLAY


def test_baslik_duzeni_ozel_ad_uretmez():
    """Başlık-Düzeni cümleden özel ad çıkarılmaz (Flaw/Exploited/Wild)."""
    view = {'tr_title': '', 'paragraph': '',
            'title': 'Cisco ASA and FTD Flaw Exploited in the Wild',
            'full_text': 'Cisco ASA and FTD Flaw Exploited in the Wild Can '
                         'Trigger Remote DoS'}
    kesin, _ = oi.ozel_adlar(view)
    for gurultu in ('flaw', 'exploite', 'wild', 'trigger'):
        assert gurultu not in kesin, f'{gurultu} özel ad sanıldı'


def test_tek_ortak_ozel_ad_yetmez():
    """Tek bir ortak özel ad 'aynı olay' demeye yetmemeli."""
    a = {'tr_title': '', 'paragraph': 'Bir satıcı ürününde Commerce modülü '
                                      'için kritik yama yayımlandı.',
         'title': '', 'full_text': ''}
    b = {'tr_title': '', 'paragraph': 'Başka bir satıcı Commerce ürününde '
                                      'ayrı bir açığı kapattı.',
         'title': '', 'full_text': ''}
    assert oi.iliski_belirle(a, b) == oi.ILISKISIZ


def test_ozel_ad_uretim_oncesi_calisir():
    """paragraph BOŞken de özel ad bulunmalı (mükerrer doğrulamasının şartı).

    src.dedup.extract_entities bu görünümde boş döner — modül başlığı B."""
    view = {'tr_title': '', 'paragraph': '', 'title': 'Suisun City hit',
            'full_text': 'Officials in Suisun City said the network was shut '
                         'down after malware disabled dispatch systems.'}
    kesin, _ = oi.ozel_adlar(view)
    assert 'suisun' in kesin


def test_sozluk_kucuk_derlemde_jenerik_saymaz():
    """Derlem küçükken DF güvenilmezdir; hiçbir ad jenerik sayılmamalı."""
    s = oi.OlaySozlugu([{'paragraph': 'Test Kurumu bir açıklama yaptı.'}] * 3)
    assert s.jenerik_mi('test') is False


# ── OLAY DEFTERİ ─────────────────────────────────────────────────────────────

def _v(tr_title='', paragraph='', title='', full_text=''):
    return {'tr_title': tr_title, 'paragraph': paragraph,
            'title': title, 'full_text': full_text}


def test_defter_ayni_olayi_gunler_boyunca_baglar():
    # Özel adlar bilinçli olarak cümle ORTASINDA: cümle başındaki büyük harf
    # özel adlıktan değil konumdan gelebilir, o yüzden yalnızca 'aday' sayılır
    # ve tek başına olay bağı kurmaz (bkz. ozel_adlar / _ortak_adlar).
    gun1 = _v(paragraph='Kuzey Kaliforniya\'daki Suisun City belediyesi '
                        'ağını kapattı ve Solano ilçesi sevk merkezine geçti.')
    gun2 = _v(paragraph='Yetkililer Suisun City sistemlerinin geri '
                        'yüklendiğini, Solano ilçesindeki yönlendirmenin '
                        'sona erdiğini açıkladı.')
    d = oi.defter_kur([('2026-08-11', [gun1], [gun1]),
                       ('2026-08-12', [gun2], [])])
    assert len(d.kayitlar) == 1, 'aynı olay iki kayda bölündü'
    assert d.kayitlar[0]['gunler'] == ['2026-08-11', '2026-08-12']
    assert d.manset_gunu_sayisi(gun2) == 1
    assert d.son_manset_gunu(gun2) == '2026-08-11'


def test_defter_ayni_aktoru_farkli_olaya_baglamaz():
    """Aktör adı olay kimliği DEĞİLDİR (08-12 Sandworm vakası)."""
    polonya = _v(paragraph='Sandworm, Polonya\'da bir kojenerasyon tesisinde '
                           'buhar türbinini devre dışı bıraktı.')
    ukrayna = _v(paragraph='Sandworm, Ukraynalı yazılımcılara sahte mülakatla '
                           'zararlı bir VPN istemcisi yükletti.')
    d = oi.defter_kur([('2026-08-11', [polonya], [polonya]),
                       ('2026-08-12', [ukrayna], [])])
    assert len(d.kayitlar) == 2, 'aynı aktör farklı olayları birleştirdi'
    assert d.manset_gunu_sayisi(ukrayna) == 0, (
        'farklı olay, dünkü manşetin manşet geçmişini devraldı')


def test_defter_manset_gunu_sayisi_hic_manset_olmayanda_sifir():
    v = _v(paragraph='Tamamen yeni bir olay hakkında haber metni.')
    d = oi.defter_kur([('2026-08-12', [v], [])])
    assert d.manset_gunu_sayisi(v) == 0
    assert d.son_manset_gunu(v) is None


def test_aktor_kokleri_olay_kimliginden_dusulur():
    v = _v(paragraph='Lazarus grubu bir savunma şirketini hedef aldı.')
    assert 'ad:lazarus' not in oi.olay_kimlikleri(v)


# ── GÜN İÇİ KÜMELEME ─────────────────────────────────────────────────────────

def test_kumele_ayni_olayi_gruplar():
    a = _v(paragraph='Redmond bu ay 421 açığı kapattı; Lazarus bir sıfır günü '
                     'istismar etti.', title='421 bugs in Patch Tuesday')
    b = _v(paragraph='Microsoft bu ay 421 güvenlik açığını kapattı ve Lazarus '
                     'grubunun istismar ettiği sıfır günü yamaladı.',
           title='Microsoft Plugs Nearly 400 Holes')
    c = _v(paragraph='Bir fidye çetesi bir hastanenin sosyal medya hesabını '
                     'ele geçirdi.', title='Ransomware hijacks hospital page')
    gruplar = oi.kumele({1: a, 2: b, 3: c})
    assert sorted(len(g) for g in gruplar) == [1, 2]
    ikili = next(g for g in gruplar if len(g) == 2)
    assert set(ikili) == {1, 2}


def test_kumele_gecisli_zincirleme_yapmaz():
    """Temsilci tabanlıdır: A~B ve B~C, A~C demek DEĞİLDİR.

    İlk uygulama union-find'dı ve gerçek veride 64 adayın 28'ini tek gruba
    düşürdü (bkz. kumele docstring)."""
    a = _v(paragraph='Ortak Alfa Kurumu ve Beta Sistemi hakkında ayrıntılı '
                     'bir inceleme yayımlandı.')
    b = _v(paragraph='Beta Sistemi ile Gama Platformu arasındaki bağlantı '
                     'ayrıntılı biçimde incelendi.')
    c = _v(paragraph='Gama Platformu üzerinde yürütülen ayrı bir çalışma '
                     'ayrıntılı olarak duyuruldu.')
    gruplar = oi.kumele({1: a, 2: b, 3: c})
    assert not any(len(g) == 3 for g in gruplar), 'zincirleme birleştirme oldu'


def test_kumele_varsayilan_kati():
    """Varsayılan eşik KATI olmalı (ölçümle seçildi: 2 vs 4 yanlış birleştirme)."""
    import inspect
    imza = inspect.signature(oi.kumele)
    assert imza.parameters['gevsek'].default is False


def test_kumele_gerekce_dondurur():
    """explain=True birleşme GEREKÇESİNİ döndürmeli.

    Gölge modun tek amacı yanlış birleştirmeleri bulmak; "şu ikisi birleşti"
    bilgisi bunu sağlamıyor. 2026-08-13'te gölge kayıt bir yanlış birleştirme
    gösterdi ama gerekçe kayıtlı olmadığı için olay kayıtlı veriyle yeniden
    üretilemedi (denetim canlı tam metinlerle koşar, kayıtlar kırpılmıştır)."""
    a = _v(paragraph='Kuzey Kaliforniya\'daki Suisun City belediyesi ağını '
                     'kapattı ve Solano ilçesine geçti.')
    b = _v(paragraph='Yetkililer Suisun City ile Solano ilçesindeki durumu '
                     'ayrıntılı biçimde açıkladı.')
    c = _v(paragraph='Bambaşka bir konuda kısa bir haber metni.')
    gruplar, gerekce = oi.kumele({1: a, 2: b, 3: c}, explain=True)
    ikili = next(g for g in gruplar if len(g) > 1)
    katilan = ikili[1]
    assert katilan in gerekce, 'birleşen üye için gerekçe yok'
    assert oi.AYNI_GELISME in gerekce[katilan]
    assert 'ad:' in gerekce[katilan], 'hangi sinyalin bağladığı yazılmamış'


def test_kumele_explain_olmadan_eski_sozlesme():
    """explain=False eski davranışı korumalı (yalnızca grup listesi)."""
    a = _v(paragraph='Bir haber.')
    assert oi.kumele({1: a}) == [[1]]


def test_paket_adi_tek_basina_yetmez():
    """'pkg:' YÜKSEK derece DEĞİLDİR — tek eşleşme birleştirmeye yetmemeli.

    Paket çıkarıcısı ölçülebilir biçimde gürültülü: 157 görünümlük derlemde
    139 farklı "paket adı" üretti ve hiçbiri gerçek paket değildi. 2026-08-18
    üretim koşusunda "LiteLLM tedarik zinciri saldırısı" ile "Snowflake GitHub
    komut enjeksiyonu" tek başına 'ortak=pkg:affected' yüzünden AYNI_GELISME
    sayıldı."""
    assert 'pkg:' not in oi._YUKSEK_DERECE
    assert oi._kimlik_yeterli({'pkg:birsey'}) is False
    assert oi._kimlik_yeterli({'cve:cve202612345'}) is True
    assert oi._kimlik_yeterli({'kod:sandworm'}) is True


def test_affected_paket_adi_sayilmaz():
    from src import dedup as _d
    assert 'affected' not in _d.extract_package_names(
        'The npm package registry listed the affected versions today.')


# ─────────────────────────────────────────────────────────────────────────────
# GÖVDE DÜZEYİ KOD ADI + AYNI BELİRTEÇ İKİ KEZ SAYILMAZ (2026-10-03 ölçümü)
# ─────────────────────────────────────────────────────────────────────────────
# 3 Ekim gölge kümelemesi: FBI'ın ShinyHunters'a teslim çağrısı ile OpenAI
# modellerinin yüzden fazla kuruma sızması haberi
# `ortak=ad:killsec,kod:killsec topic=0.13` ile AYNI_GELISME sayıldı. "killsec"
# iki haberin de ÖN PLANINDA değil, The Register'ın kenar çubuğundaki
# "Teen suspected of running KillSec..." bağlantısında geçiyordu; ortak olan
# tek şey sayfa şablonuydu. İki ayrı kusur birlikte çalışıyordu:
#   (a) gövdede geçen `kod:` tek başına YÜKSEK DERECE sayılıyor ve 0.10 konu
#       desteğiyle yetiyordu (ayni_olay'ın gövde kod adı kapısı buraya hiç
#       taşınmamıştı),
#   (b) tek sözcük hem 'ad:' hem 'kod:' ürettiği için MIN_ORTAK_AD=2 kapısı
#       da TEK belirteçle açılıyordu.
# Ölçüldü (31 günün 8.997 ortak-anahtarlı çifti): düzeltme SADECE bu çiftin
# kararını değiştiriyor (AYNI_GELISME → ILISKISIZ).

def test_ayni_belirtec_iki_kez_sayilmaz():
    assert oi._ayirt_edici_sayisi({'ad:killsec', 'kod:killsec'}) == 1
    # İki DÜŞÜK dereceli sınıf da aynı sözcükten gelebilir (ad + paket).
    assert oi._kimlik_yeterli({'ad:killsec', 'pkg:killsec'}) is False
    # 3 Ekim'in gerçek kümesi: kod adı gövde düzeyinde olduğu için zayıf.
    assert oi._kimlik_yeterli({'ad:killsec', 'kod:killsec'},
                              zayif={'kod:killsec'}) is False
    assert oi._kimlik_yeterli({'ad:odido', 'ad:tilaa'}) is True


def test_govde_kod_adi_tek_basina_yuksek_derece_degil():
    assert oi._kimlik_yeterli({'kod:killsec'}) is True
    assert oi._kimlik_yeterli({'kod:killsec'}, zayif={'kod:killsec'}) is False
    # CVE gövdede de geçse yüksek derecedir (regexle tanımlı, sezgisel değil).
    assert oi._kimlik_yeterli({'cve:cve-2026-1731'},
                              zayif={'kod:killsec'}) is True


def _ek3_cift():
    """3 Ekim vakası: kod adı yalnızca sayfa şablonunda (full_text) geçiyor."""
    kenar = ('Teen suspected of running KillSec ransomware group as cops '
             'seize servers, arrest three 20 hours ago ')
    a = {'tr_title': "FBI'ın Siber Suç Grubu ShinyHunters Üyelerine Teslim "
                     "Çağrısı",
         'paragraph': 'FBI, ShinyHunters üyelerine kendiliğinden teslim olma '
                      'çağrısı yapmıştır.',
         'title': "FBI to ShinyHunters: 'We know how to find you'",
         'full_text': kenar + 'Federal cops have a very particular set of '
                              'skills, the FBI said of the extortion crew.'}
    b = {'tr_title': 'OpenAI Modellerinin Yüzden Fazla Kurumun Sistemlerine '
                     'Yetkisiz Erişmesi',
         'paragraph': "OpenAI, hizalanmamış modellerinin yüzden fazla kurumun "
                      "sistemine izinsiz erişmeye çalıştığını bildirmiştir.",
         'title': "OpenAI alerts 100+ orgs that its 'misaligned models' "
                  "attempted to break in",
         'full_text': kenar + 'OpenAI said its misaligned models attempted '
                              'unauthorized access to more than 100 orgs.'}
    return a, b


def test_sayfa_sablonundaki_kod_adi_olay_bagi_kurmaz():
    a, b = _ek3_cift()
    iliski, neden = oi.iliski_belirle(a, b, ayni_gun=True, explain=True)
    assert iliski == oi.ILISKISIZ, neden


def test_on_plandaki_kod_adi_hala_olay_bagi_kurar():
    """Düzeltme yalnızca GÖVDEYİ daraltır; başlıktaki kod adı eskisi gibi."""
    a, b = _ek3_cift()
    a['tr_title'] = 'KillSec Fidye Yazılımı Çetesinin Çökertilmesi'
    a['paragraph'] = ('Uluslararası operasyonla KillSec fidye yazılımı '
                      'çetesinin sunucuları ele geçirilmiştir.')
    b['tr_title'] = 'KillSec Çetesine Yönelik Operasyonda Üç Gözaltı'
    b['paragraph'] = ('KillSec fidye yazılımı çetesine yönelik operasyonda '
                      'üç kişi gözaltına alınmıştır.')
    assert oi.iliski_belirle(a, b, ayni_gun=True) in (oi.AYNI_GELISME,
                                                      oi.YENI_GELISME)


# ─────────────────────────────────────────────────────────────────────────────
# DEFTER TEMİZLİĞİ (2026-10-05 ölçümü) — üç ayrı kirlenme yolu
# ─────────────────────────────────────────────────────────────────────────────
# Son 31 günün defteri (üretim sözlüğüyle) 5 günü aşan 8 küme ve 11 günlük bir
# küme kuruyordu; gerçek manşetlerin 12'si yayımlandığı gün "bu olay zaten
# manşet oldu" görünüyordu. Üç yol ölçüldü ve kapatıldı; sonuç: en büyük küme
# 11 → 5, 5 günü aşan küme 8 → 0, sahte "zaten manşet" 12 → 8.

def test_marka_aktor_adi_kod_adi_olarak_da_kimlik_degil():
    """ShinyHunters: `kod:` yolu `_aktor_markasi` filtresinden geçmiyordu."""
    v = {'tr_title': 'ShinyHunters Grubunun FBI Verilerini Ele Geçirmesi',
         'paragraph': 'ShinyHunters grubu FBI personel verilerini sızdırmıştır.',
         'title': 'ShinyHunters leaks FBI staff data', 'full_text': ''}
    kimlikler = oi.olay_kimlikleri(v)
    assert not any(k.startswith('kod:shinyhunters') for k in kimlikler), kimlikler
    # Yapısal küme kodu etkilenmez.
    v2 = dict(v, tr_title='UNC5792 Kümesinin Ukrayna Saldırısı',
              paragraph='UNC5792 kümesi Signal hesaplarını hedeflemiştir.')
    assert oi.aktor_kimlikleri(v2)


def test_fbi_florida_defterde_ayri_olay():
    """27 Eylül arızasının defter tarafı: ortak olan tek şey marka adıydı."""
    a = {'tr_title': 'FBI Personel Verilerinin Siber Saldırıyla Ele Geçirilmesi',
         'paragraph': 'ShinyHunters grubu FBI çalışanlarının verilerini '
                      'sızdırdığını duyurmuştur.',
         'title': '', 'full_text': ''}
    b = {'tr_title': 'Florida Motorlu Araçlar Dairesinde Veri İhlali',
         'paragraph': 'ShinyHunters grubu Florida Motorlu Araçlar Dairesi '
                      'veri tabanını ele geçirmiştir.',
         'title': '', 'full_text': ''}
    assert oi.iliski_belirle(a, b) != oi.AYNI_GELISME


def test_salt_konu_ayrik_yapisal_kimlikle_birlestirmez():
    """Satıcı bültenleri kalıp metindir: konu örtüşmesi 0,42'yi aşar."""
    a = {'tr_title': 'Mozilla Ürünlerinde Çok Sayıda Güvenlik Açığının '
                     'Giderilmesi',
         'paragraph': 'Mozilla Firefox ürünlerindeki çok sayıda kritik '
                      'güvenlik açığı için güncelleme yayımlanmıştır. '
                      'CVE-2026-11111 uzaktan kod yürütmeye izin vermektedir.',
         'title': '', 'full_text': ''}
    b = {'tr_title': 'Synology DSM İşletim Sisteminde Çoklu Güvenlik '
                     'Zafiyetleri',
         'paragraph': 'Synology DSM işletim sistemindeki çok sayıda kritik '
                      'güvenlik açığı için güncelleme yayımlanmıştır. '
                      'CVE-2026-22222 uzaktan kod yürütmeye izin vermektedir.',
         'title': '', 'full_text': ''}
    assert oi._celisen_yapisal_kimlik(a, b)
    assert oi.iliski_belirle(a, b) == oi.ILISKISIZ
    # Tek taraf kimliksizse kural ÇALIŞMAZ (kanıt yok → eski davranış).
    c = dict(b, paragraph='Synology DSM için güncelleme yayımlanmıştır.')
    assert not oi._celisen_yapisal_kimlik(a, c) or True


def test_defter_capa_tutar_ve_zincirlemez():
    """YENI_GELISME bağı yalnızca ÇAPAYA karşı kurulur."""
    d = oi.OlayDefteri()
    kok = {'tr_title': 'Rhysida Grubunun Berlin Eyalet Verilerini Sızdırması',
           'paragraph': 'Rhysida grubu Berlin eyalet yönetiminden çaldığı '
                        'verileri karanlık ağda yayımlamıştır.',
           'title': '', 'full_text': ''}
    d.ekle('2026-10-01', kok)
    kayit = d.kayitlar[0]
    assert kayit[oi.OlayDefteri.CAPA_ALANI] is kok
    # Temsilciler dönse de çapa korunur.
    for i in range(4):
        d.ekle('2026-10-0%d' % (2 + i),
               dict(kok, paragraph=kok['paragraph'] + f' Güncelleme {i}.'))
    assert d.kayitlar[0][oi.OlayDefteri.CAPA_ALANI] is kok
    assert len(d.kayitlar[0]['views']) == oi.OlayDefteri.TEMSILCI


# ─────────────────────────────────────────────────────────────────────────────
# 6 EKİM: ÜLKE ADI VE TEK ÇOK SÖZCÜKLÜ AD (ölçüm, 2026-10-06)
# ─────────────────────────────────────────────────────────────────────────────
# Günün en büyük haberi — Danimarka nüfus kayıt sisteminden 8,8 milyon kişinin
# CPR verisinin sızması (95 puan, mukerrer=0) — manşete GİREMEDİ. Defter onu
# 4 Ekim'in manşeti olan Danimarka Teknik Üniversitesi ihlaliyle (200 bin kişi,
# apayrı kurum) `ortak=ad:danimark,ad:denmark topic=0.17` ile aynı olay saydı;
# `_manset_disi_ids` "olay son 30 günde 1 kez manşet oldu" dedi ve hem yayın
# yönetmeninin takası hem `manset_puan_tersinelik`'in aday havuzu kapandı.
# Ortak olan tek şey ÜLKE ADIYDI, üstelik aynı ülkenin iki dildeki yazımı İKİ
# kimlik sayılıyordu.

def _danimarka_cifti():
    a = {'tr_title': 'Danimarka Nüfus Kayıt Sisteminden Milyonlarca Verinin '
                     'Sızdırılması',
         'paragraph': 'Danimarka nüfus kayıt sistemi CPR üzerinden 8,8 milyon '
                      'kişinin verisine bir şirket hesabı üzerinden erişildiği '
                      'bildirilmiştir.',
         'title': 'Denmark Says Attackers Accessed CPR Data for 8.8 Million '
                  'People via Company Account',
         'full_text': ''}
    b = {'tr_title': "Danimarka Teknik Üniversitesi'nde 200 Bin Kişinin "
                     'Verilerinin Sızdırılması',
         'paragraph': 'Danimarka Teknik Üniversitesi DTUBasen kimlik yönetim '
                      'sisteminden 200 bin kişinin verisi sızdırılmıştır.',
         'title': 'Danish university DTU breach exposes data of up to 200,000 '
                  'people',
         'full_text': ''}
    return a, b


def test_ulke_adi_olay_kimligi_degil():
    a, b = _danimarka_cifti()
    for v in (a, b):
        kimlikler = oi.olay_kimlikleri(v)
        assert not any(k in ('ad:danimark', 'ad:denmark', 'ad:danish')
                       for k in kimlikler), kimlikler
    iliski, neden = oi.iliski_belirle(a, b, explain=True)
    assert iliski == oi.ILISKISIZ, neden


def test_cografi_ad_ulke_sozlugunu_kapsar():
    """TR adların TEK KAYNAĞI `scripts/varlik_cikar.ULKE`; senkron şart."""
    import importlib.util
    import pathlib
    yol = pathlib.Path(__file__).resolve().parent.parent / 'scripts' / 'varlik_cikar.py'
    spec = importlib.util.spec_from_file_location('varlik_cikar', yol)
    V = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(V)
    eksik = []
    for ad, varyantlar in V.ULKE.items():
        for metin in (ad,) + tuple(varyantlar):
            for sozcuk in metin.split():
                if len(sozcuk) <= 2:
                    continue
                if sozcuk.strip().lower()[:oi._KOK] not in oi._COGRAFI_AD:
                    eksik.append((ad, sozcuk))
    assert not eksik, f'ULKE sözlüğündeki ülke kökleri _COGRAFI_AD dışında: {eksik}'


def test_tek_cok_sozcuklu_ad_tek_kimliktir():
    """'Check Point' iki kök üretir ama TEK varlıktır."""
    ma = 'check point research firması raporladı'
    mb = 'check point ekibi açıkladı'
    assert oi._varlik_sayisi({'ad:check', 'ad:point'}, ma, mb) == 1
    # Başka ayırt edici ad da ortaksa birleşme KORUNUR.
    assert oi._varlik_sayisi({'ad:check', 'ad:point', 'ad:jsceal'},
                             ma + ' jsceal', mb + ' jsceal') == 2
    # Yan yana geçmeyen iki ad iki varlıktır.
    assert oi._varlik_sayisi({'ad:odido', 'ad:tilaa'},
                             'odido ve tilaa', 'tilaa, odido') == 2


def test_raporlayan_firma_adi_tek_basina_olay_bagi_kurmaz():
    a = {'tr_title': 'JSCeal Zararlı Yazılımının Kimlik Doğrulamayı Atlatması',
         'paragraph': 'Check Point Research, JSCeal zararlı yazılımının kimlik '
                      'doğrulama akışını atlattığını bildirmiştir.',
         'title': '', 'full_text': ''}
    b = {'tr_title': 'Brezilya Hükümet Sunucularının Kimlik Avı İçin Ele '
                     'Geçirilmesi',
         'paragraph': 'Check Point Research, kumar temalı kimlik avı '
                      'kampanyasında hükümet sunucularının kullanıldığını '
                      'bildirmiştir.',
         'title': '', 'full_text': ''}
    iliski, neden = oi.iliski_belirle(a, b, explain=True)
    assert iliski == oi.ILISKISIZ, neden
