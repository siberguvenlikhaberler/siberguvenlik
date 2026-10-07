"""KRİTİK 3'Ü LLM SEÇER — sözleşme ve güvenlik ağları.

NEDEN VAR: manşet bugüne dek DETERMİNİSTİK seçiliyordu (en yüksek puanlı üç
uygun haber) ve LLM yalnızca sonradan İTİRAZ ediyordu. Puan rubriği kaba bir
vekildir ve tekrar tekrar yanlış manşet üretti:
  • 2026-08-19 yamalanmış Apple açığı 94 puanla manşet oldu.
  • 2026-08-21 satıcının kapattığı Entra ID açığı (95), süregelen bir
    casusluk kampanyasının (94) yerine manşete çıkarıldı.
  • 2026-08-24 araştırmacıların NASA yazılımında bulduğu açık (91) manşet
    oldu — saldırı, saldırgan, kurban yok.

GÜVENLİK: kısa liste KODDA süzülür; LLM listeden seçer, liste dışına çıkamaz
ve geçersiz cevapta deterministik seçim korunur.
"""
import main


def _sistem(yanit):
    s = main.HaberSistemi.__new__(main.HaberSistemi)
    s._gemini_call_json = lambda *a, **k: yanit
    s._manset_izi = []
    return s


def _veri(n=6):
    records = {i: {'kat': 'nation_state_apt', 'toplam': 100 - i}
               for i in range(1, n + 1)}
    content = {i: {'tr_title': f'Haber {i}', 'paragraph': f'Paragraf {i}.'}
               for i in records}
    arts = {i: {'id': i, 'title': f'T{i}', 'full_text': ''} for i in records}
    return records, content, arts


def test_llm_secimi_uygulanir():
    records, content, arts = _veri()
    s = _sistem({'secim': [4, 5, 6],
                 'gerekce': [{'id': 4, 'neden': 'süren kampanya'}]})
    secim = s._manset_llm_sec([1, 2, 3, 4, 5, 6], [1, 2, 3],
                              records, content, arts, [])
    assert secim == [4, 5, 6], 'LLM seçimi uygulanmadı'
    assert any(iz['katman'] == 'manset_llm_secim' for iz in s._manset_izi), \
        'seçim karar izine yazılmadı'


def test_liste_disi_id_reddedilir():
    """LLM aday listesinde OLMAYAN bir id döndüremez — o id mükerrer,
    yanlış kategori ya da defterin yasakladığı bir haber olabilir."""
    records, content, arts = _veri()
    s = _sistem({'secim': [4, 5, 99]})
    secim = s._manset_llm_sec([1, 2, 3, 4, 5, 6], [1, 2, 3],
                              records, content, arts, [])
    assert secim == [1, 2, 3], 'liste dışı id kabul edildi'


def test_eksik_secim_deterministige_duser():
    records, content, arts = _veri()
    for yanit in ({'secim': [4, 5]}, {'secim': []}, {}, None, {'secim': 'x'}):
        s = _sistem(yanit)
        assert s._manset_llm_sec([1, 2, 3, 4, 5, 6], [1, 2, 3],
                                 records, content, arts, []) == [1, 2, 3], \
            f'geçersiz yanıtta deterministik seçim korunmadı: {yanit}'


def test_mukerrer_secim_reddedilir():
    """Aynı id iki kez → 3 farklı manşet yok → deterministiğe düş."""
    records, content, arts = _veri()
    s = _sistem({'secim': [4, 4, 5]})
    assert s._manset_llm_sec([1, 2, 3, 4, 5, 6], [1, 2, 3],
                             records, content, arts, []) == [1, 2, 3]


def test_aday_azsa_llm_cagrilmaz():
    """3 veya daha az aday varsa seçilecek bir şey yok — maliyet harcanmaz."""
    records, content, arts = _veri(3)
    cagri = []
    s = _sistem({'secim': [1, 2, 3]})
    s._gemini_call_json = lambda *a, **k: cagri.append(1) or {'secim': [1, 2, 3]}
    assert s._manset_llm_sec([1, 2, 3], [1, 2, 3],
                             records, content, arts, []) == [1, 2, 3]
    assert not cagri, 'gereksiz LLM çağrısı yapıldı'


def test_secici_kisa_listeyi_kodda_suzer():
    """LLM'e yalnızca manşete UYGUN adaylar gitmeli — kapı kararları
    seçicinin ÜSTÜNDEDİR."""
    import inspect
    kaynak = inspect.getsource(main.HaberSistemi._derive_top3_by_score)
    # Kapı artık TEK YÜKLEMDEN sorulur (P3): `_manset_yasak`/defter
    # okumaları katmandan kalktı, yerine `_manset_uygun_mu` geldi.
    i_kapi = kaynak.index('_manset_uygun_mu(')
    i_llm = kaynak.index('_manset_llm_sec(')
    assert i_kapi < i_llm, 'LLM seçimi manşet kapısından ÖNCE çalışıyor'
    # Karakter penceresi DEĞİL sıra karşılaştırması: araya yorum/katman
    # eklendiğinde sabit pencere testi yanlış yere kırılıyordu.
    assert kaynak.index('eligible') < kaynak.index('kisa_liste'), \
        'kısa liste süzülmüş havuzdan kurulmuyor'


def test_kisa_liste_capraz_gun_temiz():
    """LLM seçimi, SONRA elenecek adaylar arasından yapılmamalı.

    ÖLÇÜLDÜ (2026-08-24): LLM 19, 4 ve 18'i seçti; üçü de sonraki çapraz-gün
    katmanlarında mükerrer çıkıp mekanik yedeklerle değiştirildi ve manşet
    74-76 puanlık zayıf haberlere düştü. Seçimin bir anlamı olması için kısa
    liste elenmeyecek adaylardan kurulmalı.
    """
    import inspect
    kaynak = inspect.getsource(main.HaberSistemi._derive_top3_by_score)
    parca = kaynak.split('kisa_liste')[0][-1200:]
    assert 'mukerrer_karari(' in parca, \
        'kısa liste çapraz-gün mükerrerlerinden arındırılmıyor'
    assert '_aday or list(top3_ids)' in kaynak, \
        'tüm adaylar elenirse deterministik seçime düşülmüyor'


def test_yedek_bulucu_manset_yasagina_uyar():
    """Manşet yasağı YEDEK seçiminde de geçerli olmalı.

    ÖLÇÜLDÜ (2026-08-24): İran/Birleşik Krallık enerji santrali haberi
    manşet oldu — aynı olay 08-23'te de manşetti ve GELISME olarak yasak
    almıştı. Yasak yalnızca ana kapıda uygulanıyordu; bir çapraz-gün elemesi
    tetiklenince yasaklı haber YEDEK olarak manşete geri geldi.
    """
    import inspect
    kaynak = inspect.getsource(main.HaberSistemi._kritik3_yedek_bul)
    # Ölçütler artık TEK YÜKLEMDE (P1, KRITIK3_PLAN.md): yedek bulucu
    # yüklemi çağırmalı, yüklem de kapıyı taşımalı.
    assert '_manset_uygun_mu' in kaynak, 'yedek bulucu yüklemi çağırmıyor'
    yuklem = inspect.getsource(main.HaberSistemi._manset_uygun_mu)
    assert '_manset_yasak' in yuklem, 'yüklem manşet yasağına bakmıyor'
    assert 'mukerrer_karari(' in yuklem, \
        'yüklem geçmişi eski karşılaştırıcıyla ölçüyor'


def test_hakem_secimden_once_de_kosar():
    """Seçicinin göremediği bir eleyici seçimden SONRA çalışmamalı.

    ÖLÇÜLDÜ (2026-08-24): LLM Myanmar/CoolClient casusluk haberini manşet
    seçti; SON kapıdaki LLM HAKEMİ onu çapraz-gün mükerreri diye eledi ve
    manşet, yerine geçen CISA günlükleme kılavuzuna düştü. Deterministik
    temizlik yetmiyor — hakem de kısa listeye seçimden ÖNCE bakmalı.
    """
    import inspect
    kaynak = inspect.getsource(main.HaberSistemi._derive_top3_by_score)
    on = kaynak.split('kisa_liste = ')[0]
    assert '_mukerrer_llm_hakem(' in on, \
        'hakem manşet seçiminden önce çalışmıyor'


def test_puan_bandi_ucurumu_kapatir():
    """LLM puanı EZEBİLİR ama UÇURUM AÇAMAZ.

    ÖLÇÜLDÜ (2026-08-24): elenmemiş adaylar arasında 89, 83, 81, 80, 77, 76,
    75 puanlılar dururken 51 puanlık bir SEO zehirlenmesi haberi manşet
    seçildi.
    """
    records = {1: {'kat': 'nation_state_apt', 'toplam': 89},
               2: {'kat': 'kolluk_operasyonu', 'toplam': 83},
               3: {'kat': 'veri_ihlali', 'toplam': 77},
               4: {'kat': 'nation_state_apt', 'toplam': 76},
               5: {'kat': 'phishing_sosyal_muhendislik', 'toplam': 51}}
    content = {i: {'tr_title': f'Haber {i}', 'paragraph': f'P{i}'} for i in records}
    arts = {i: {'id': i, 'title': '', 'full_text': ''} for i in records}
    s = _sistem({'secim': [1, 5, 2]})
    secim = s._manset_llm_sec([1, 2, 3, 4, 5], [1, 2, 3],
                              records, content, arts, [])
    assert 5 not in secim, 'uçurum açan seçim kabul edildi'
    assert 3 in secim, 'yerine en yüksek puanlı uygun yedek konmadı'
    assert len(secim) == 3


def test_puan_bandi_icinde_ezme_serbest():
    """Bant içinde kalan editoryal ezme ENGELLENMEMELİ — yönetmenin asıl
    işi budur."""
    records = {1: {'kat': 'zafiyet_rutin', 'toplam': 95},
               2: {'kat': 'nation_state_apt', 'toplam': 80},
               3: {'kat': 'veri_ihlali', 'toplam': 78},
               4: {'kat': 'kolluk_operasyonu', 'toplam': 76}}
    content = {i: {'tr_title': f'Haber {i}', 'paragraph': f'P{i}'} for i in records}
    arts = {i: {'id': i, 'title': '', 'full_text': ''} for i in records}
    s = _sistem({'secim': [2, 3, 4]})
    secim = s._manset_llm_sec([1, 2, 3, 4], [1, 2, 3],
                              records, content, arts, [])
    assert secim == [2, 3, 4], 'bant içindeki meşru ezme engellendi'


def test_kisa_liste_kendi_icinde_tekil():
    """Kısa listede aynı olayın birden çok kopyası bulunmamalı.

    ÖLÇÜLDÜ (2026-08-26): Interpol Jackal IV operasyonunun YEDİ kopyası vardı
    (94-95 puan). Çapraz-gün temizliği yalnızca GEÇMİŞ günlere baktığı için
    kopyalar listede kaldı; LLM manşete ikisini birden seçti (ID 71 ve 83),
    sonraki katmanlar ikisini de temizleyince manşet 74 ve 76 puanlık
    haberlere düştü. Kopyalar ayrıca 10 kişilik listenin slotlarını yiyor.
    """
    import inspect
    kaynak = inspect.getsource(main.HaberSistemi._derive_top3_by_score)
    i_tekil = kaynak.index('_dusen_kopya')
    i_kap = kaynak.index('_aday = _tekil[:self.MANSET_ADAY_SAYISI]')
    i_llm = kaynak.index('_manset_llm_sec(')
    assert i_tekil < i_kap < i_llm, \
        'kısa liste tekilleştirme LLM seçiminden önce/kırpmadan önce değil'
    assert 'ayni_olay' in kaynak[i_tekil - 800:i_kap], \
        'tekilleştirme kapının olay tanımını (ayni_olay) kullanmıyor'


def test_tekillestirme_en_yuksek_puanliyi_tutar():
    """Kopyalardan hangisinin kalacağı rastgele olamaz — puan belirler."""
    import inspect
    kaynak = inspect.getsource(main.HaberSistemi._derive_top3_by_score)
    i_tekil = kaynak.index('_tekil, _dusen_kopya')
    parca = kaynak[i_tekil:i_tekil + 400]
    assert 'sorted(_aday, key=lambda x: -_p_aday(x))' in parca, \
        'kopya taraması puan sırasında yapılmıyor — düşük puanlı kopya kalabilir'


def test_secilen_uclu_cesitlilik_yukleminden_gecer():
    """ÖLÇÜLDÜ (2026-09-29): FBI personel ihlali ile Hollanda'daki
    ShinyHunters yakalaması aynı hattan (`aktor:shinyhunters`) iki manşet
    oldu. Kısa liste tek tek temizdi; sınanmayan şey ÜÇLÜNÜN KENDİSİYDİ.
    Çeşitlilik kuralı bunu üç katman sonra takasla düzeltiyordu."""
    records = {i: {'kat': 'nation_state_apt', 'toplam': 100 - i}
               for i in range(1, 6)}
    content = {
        1: {'tr_title': 'FBI personel verilerinin ShinyHunters tarafından ele geçirilmesi',
            'paragraph': 'ShinyHunters grubu FBI personel veri tabanını ele geçirdi.'},
        2: {'tr_title': 'Hollanda\'da ShinyHunters bağlantılı bir şahsın yakalanması',
            'paragraph': 'Hollanda polisi ShinyHunters ile bağlantılı bir şüpheliyi yakaladı.'},
        3: {'tr_title': 'Brezilya hükümet sunucularının ele geçirilmesi',
            'paragraph': 'Brezilya hükümet sunucuları kimlik avı altyapısı olarak kullanıldı.'},
        4: {'tr_title': 'Kuzey Koreli bilişim çalışanlarına yönelik yaptırımlar',
            'paragraph': 'ABD Hazine Bakanlığı Kuzey Koreli bilişim çalışanlarına yaptırım uyguladı.'},
        5: {'tr_title': 'Xinbi dolandırıcılık pazarının çökertilmesi',
            'paragraph': 'Xinbi Guarantee adlı dolandırıcılık pazarı kapatıldı.'},
    }
    arts = {i: {'id': i, 'title': f'T{i}', 'full_text': ''} for i in records}
    s = _sistem({'secim': [1, 2, 3]})
    secim = s._manset_llm_sec([1, 2, 3, 4, 5], [3, 4, 5],
                              records, content, arts, [])
    assert len(secim) == 3 and len(set(secim)) == 3
    assert not (1 in secim and 2 in secim), \
        'aynı hattın iki haberi manşette kaldı'
    assert 4 in secim or 5 in secim, 'temiz yedek alınmadı'


def test_temiz_yedek_yoksa_manset_uce_sadik_kalir():
    """KRİTİK 3 ASLA 2'YE DÜŞMEZ: aynı hattın iki haberi seçilmiş ve havuzda
    temiz aday yoksa seçim olduğu gibi kalır, karar sonraki katmanlara
    bırakılır."""
    records = {i: {'kat': 'nation_state_apt', 'toplam': 100 - i}
               for i in range(1, 4)}
    content = {
        1: {'tr_title': 'FBI personel verilerinin ShinyHunters tarafından ele geçirilmesi',
            'paragraph': 'ShinyHunters grubu FBI personel veri tabanını ele geçirdi.'},
        2: {'tr_title': 'Hollanda\'da ShinyHunters bağlantılı bir şahsın yakalanması',
            'paragraph': 'Hollanda polisi ShinyHunters ile bağlantılı bir şüpheliyi yakaladı.'},
        3: {'tr_title': 'Brezilya hükümet sunucularının ele geçirilmesi',
            'paragraph': 'Brezilya hükümet sunucuları kimlik avı altyapısı olarak kullanıldı.'},
    }
    arts = {i: {'id': i, 'title': f'T{i}', 'full_text': ''} for i in records}
    s = _sistem({'secim': [1, 2, 3]})
    # Aday sayısı 3'ten fazla olmalı ki seçici LLM'e gitsin; 4 havuzdadır
    # ama o da aynı hattan.
    records[4] = {'kat': 'nation_state_apt', 'toplam': 90}
    content[4] = {'tr_title': 'ShinyHunters\'ın Salesforce verilerini sızdırması',
                  'paragraph': 'ShinyHunters grubu Salesforce müşteri verilerini sızdırdı.'}
    arts[4] = {'id': 4, 'title': 'T4', 'full_text': ''}
    secim = s._manset_llm_sec([1, 2, 3, 4], [1, 3, 4],
                              records, content, arts, [])
    assert len(secim) == 3, 'manşet üçten aza düştü'


def test_havuz_kapisi_uretim_gorunumuyle_sorulur():
    """ÖLÇÜLDÜ (2026-10-07, `scripts/kritik3_olc.py --gorunum`): havuz kapısı
    deftere `_kaynak_view` ile soruyordu (tr_title/paragraph BOŞ, title
    İNGİLİZCE) oysa defterin geçmişi yalnızca Türkçedir. Son 31 günün 93
    manşetinde defter Türkçe görünümle 4 tekrar buluyor, kaynak görünümüyle
    0 — kapı fiilen ölüydü."""
    import inspect
    kaynak = inspect.getsource(main.HaberSistemi._derive_top3_by_score)
    kod = '\n'.join(l for l in kaynak.split('\n')
                    if not l.lstrip().startswith('#'))
    assert '_kaynak_view' not in kod, \
        'havuz kapısı deftere kaynak görünümüyle soruyor'
    assert '_manset_uygun_mu(' in kod, 'havuz kapısı yüklemden geçmiyor'
