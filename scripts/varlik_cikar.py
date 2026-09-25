#!/usr/bin/env python3
"""VARLIK ÇIKARIMI — sektör / ülke rolü / aktör alanlarını arşive yazar.

NEDEN VAR: yıl sonu raporu "hangi sektör en çok vuruldu", "hangi ülkeler
hedefti", "hangi aktör kaç olayda geçti" sorularını soracak. Bu üç eksen şu an
YALNIZCA serbest metinde var; ham kelime sayımı ise yanıltıcı (ölçüldü:
arşivde "su " 1.114 kez geçiyor ama çoğu su altyapısı değil, Türkçe'de sık
geçen bir hece dizisi).

BU BİR YARGI DEĞİL, ÇIKARIMDIR — bu yüzden LLM'e değil KURALLARA bağlandı:
  • Tekrar üretilebilir: aynı arşiv her koşuda aynı sonucu verir.
  • Kayma üretmez: `onem` etiketlemesinde ölçülen oturumlar arası kayma
    (bkz. RETRO_RUBRIK.md v2) burada yapısal olarak imkânsızdır.
  • Denetlenebilir: hangi anahtar kelimenin eşleştiği `--ornek` ile görülür.

Yazılan satır (boş alan YAZILMAZ):
    » varlik | sektor=finans,kamu | hedef=ABD | aktor_ulke=Rusya | aktor=APT28

ÜÇ TASARIM KARARI:
1. SEKTÖR ÇOK ETİKETLİDİR. Bir haber hem `kamu` hem `saglik` olabilir
   (eyalet sağlık sistemi). Tek etiket seçmek, seçimi sözlük sırasına
   bırakır: ilk prototipte `finans` 961, `enerji` 45 çıkmıştı — gerçek
   dağılım değil, sıralama yanlılığıydı.
2. ÜLKE İKİ ROLDE AYRILIR. "Çin bağlantılı grup ABD'yi hedefledi"
   cümlesinde iki ülke de geçer ama biri fail biri kurbandır; tek alanda
   toplamak "ABD en çok saldıran ülke" gibi sonuçlar üretirdi. Rol,
   Türkçe ipucu kalıplarıyla ayrılır (`bağlantılı/menşeli/destekli` → aktör;
   `-deki/-e yönelik/hükümeti` → hedef).
3. EŞLEŞME YOKSA ALAN BOŞ BIRAKILIR. Tahmin yürütülmez; kapsam oranı
   raporlanır ve raporda açıkça yazılır.

Kullanım: python3 scripts/varlik_cikar.py [--yaz] [--ornek N] [--kuru]
"""
import collections
import datetime
import importlib.util
import pathlib
import re
import sys

ARSIV = 'data/haberler_arsiv.txt'

# Arşiv yazımı KOPYALANMAZ — tek kapı: atomik yazım + kayıt sayısı
# kapısı (bkz. scripts/arsiv_yaz.py).
_yaz_spec = importlib.util.spec_from_file_location(
    'arsiv_yaz', pathlib.Path(__file__).resolve().parent / 'arsiv_yaz.py')
_arsiv_yaz = importlib.util.module_from_spec(_yaz_spec)
_yaz_spec.loader.exec_module(_arsiv_yaz)

_AY = {'JANUARY': 1, 'FEBRUARY': 2, 'MARCH': 3, 'APRIL': 4, 'MAY': 5,
       'JUNE': 6, 'JULY': 7, 'AUGUST': 8, 'SEPTEMBER': 9, 'OCTOBER': 10,
       'NOVEMBER': 11, 'DECEMBER': 12}
_GUN_RE = re.compile(r'📅 (\d+) ([A-ZÇĞİÖŞÜ]+) (\d{4})')
_BAS_RE = re.compile(r'\[\s*(\d+)\]\s+(.+)')
_VARLIK_RE = re.compile(r'^»\s*varlik\b')

# ── SEKTÖR ────────────────────────────────────────────────────────────────
# Anahtarlar küçük harfle aranır. Kısa ve çok anlamlı diziler (ör. "su")
# BİLEREK kullanılmaz; yalnızca ayırt edici tamlamalar alınır.
SEKTOR = {
    'saglik': ('hastane', 'sağlık sistem', 'sağlık kuruluş', 'sağlık hizmet',
               'sağlık teknoloji', 'tıbbi cihaz', 'tıbbi kayıt', 'hasta veri',
               'hasta bilgi', 'ilaç', 'klinik', 'teşhis', 'sağlık sektör',
               'teletıp', 'diş hekim'),
    'finans': ('banka', 'bankacılık', 'finans kuruluş', 'finans sektör',
               'finansal teknoloji', 'fintek', 'sigorta', 'ödeme platform',
               'ödeme uygulama', 'kredi şirket', 'borsa', 'yatırım',
               'finans altyapı', 'kart veri'),
    'kamu': ('bakanlı', 'hükümet', 'belediye', 'kamu kurum', 'kamu hizmet',
             'devlet kurum', 'federal kurum', 'eyalet yönetim', 'valilik',
             'kamu ağ', 'resmi kurum', 'seçim', 'mahkeme', 'savcılık',
             'vergi dair', 'nüfus kay',
             # Sözcük BAŞI kuralı bileşikleri düşürür; ikisi de kamudur.
             'başsavcılık', 'başbakanlık'),
    'savunma': ('savunma sanayi', 'savunma bakan', 'savunma sektör', 'ordu',
                'askeri', 'donanma', 'nato', 'pentagon', 'silah',
                'savunma yüklenici', 'savunma tedarikçi', 'istihbarat servis'),
    'enerji': ('enerji şirket', 'enerji sektör', 'enerji şebeke',
               'enerji altyapı', 'elektrik şebeke', 'güç santral',
               'nükleer', 'petrol', 'doğal gaz', 'enerji tesis',
               'enerji arz', 'şebeke operatör'),
    'su': ('su tesis', 'su sistem', 'su altyapı', 'su idaresi', 'su şebeke',
           'su kuruluş', 'atık su', 'içme suyu', 'su servis'),
    'telekom': ('telekom', 'mobil operatör', 'mobil ağ operatör',
                'internet servis sağlayıc', 'geniş bant', 'gsm operatör',
                'telefon operatör', 'iletişim sağlayıc'),
    'ulastirma': ('havalimanı', 'havayol', 'demiryol', 'liman', 'lojistik',
                  'taşımacılık', 'kargo', 'nakliye', 'taksi operatör',
                  'uçuş', 'gemi'),
    'egitim': ('üniversite', 'okul', 'öğrenci', 'akademi', 'eğitim kurum',
               'eğitim bakan', 'kampüs'),
    'kripto': ('kripto para', 'kripto varlık', 'bitcoin', 'blokzincir',
               'blok zinciri', 'kripto cüzdan', 'kripto borsa',
               'merkeziyetsiz', 'kripto ticaret'),
    'teknoloji': ('yazılım şirket', 'yazılım firma', 'teknoloji şirket',
                  'teknoloji devi', 'bulut sağlayıc', 'bulut hizmet',
                  'geliştirici', 'yazılım geliştirme platform',
                  'paket yöneticisi', 'açık kaynak proje',
                  'veri merkezi', 'barındırma sağlayıc',
                  'sosyal medya platform'),
    'perakende': ('perakende', 'süpermarket', 'e-ticaret', 'market zincir',
                  'mağaza zincir', 'restoran zincir', 'otel zincir',
                  'konaklama sektör'),
    'uretim': ('üretim tesis', 'fabrika', 'imalat', 'otomotiv', 'sanayi',
               'üretici firma', 'endüstriyel üretic'),
    'medya': ('gazeteci', 'haber kuruluş', 'medya kuruluş', 'yayıncı',
              'televizyon kanal', 'basın'),
}

# ── ÜLKE ──────────────────────────────────────────────────────────────────
# Değer: eşleşme kalıpları (büyük/küçük harf DUYARLI aranır; "Rus " gibi
# kısa biçimler yalnızca sonda boşlukla, "Ruslar"a takılmasın diye).
ULKE = {
    # 'Amerikan'/'Amerikalı' 2026-09-25'te eklendi (58+60 geçiş kaçıyordu).
    'ABD': ('ABD', 'Amerika Birleşik Devletleri', 'Birleşik Devletler',
            'Amerikan', 'Amerikalı'),
    'Çin': ('Çin', 'Çinli', 'Çince'),
    'Rusya': ('Rusya', 'Rus ', 'Rusça'),
    'İran': ('İran', 'İranlı'),
    'Kuzey Kore': ('Kuzey Kore', 'Kuzey Koreli'),
    'Ukrayna': ('Ukrayna', 'Ukraynalı'), 'İsrail': ('İsrail', 'İsrailli'),
    'Almanya': ('Almanya', 'Alman '), 'Fransa': ('Fransa', 'Fransız'),
    'Birleşik Krallık': ('Birleşik Krallık', 'İngiltere', 'İngiliz'),
    'Hollanda': ('Hollanda', 'Hollandalı'),
    'İspanya': ('İspanya', 'İspanyol'),
    'İtalya': ('İtalya', 'İtalyan'), 'Polonya': ('Polonya', 'Polonyalı'),
    'Japonya': ('Japonya', 'Japon '),
    # 'Koreli' TEK BAŞINA EKLENMEZ: "Kuzey Koreli" geçişlerini (150) yutar.
    'Güney Kore': ('Güney Kore', 'Güney Koreli'),
    'Hindistan': ('Hindistan', 'Hintli'), 'Pakistan': ('Pakistan',),
    'Brezilya': ('Brezilya', 'Brezilyalı'),
    'Kanada': ('Kanada', 'Kanadalı'),
    'Avustralya': ('Avustralya',), 'Türkiye': ('Türkiye',),
    'Kuzey Makedonya': ('Kuzey Makedonya',),
    'AB': ('Avrupa Birliği', 'Avrupa Komisyonu', 'Avrupa Parlamentosu'),
    # 2026-09-25 taramasında eklendi: sözlükte YOKTU ama arşivde 15+ kez
    # geçiyorlardı. Tayvan 78 geçişle en büyük boşluktu — Çin-Tayvan
    # ekseni ülke kırılımında tamamen görünmezdi.
    'Tayvan': ('Tayvan',), 'Meksika': ('Meksika', 'Meksikalı'),
    'Belarus': ('Belarus', 'Beyaz Rusya', 'Belaruslu'),
    'Kamboçya': ('Kamboçya', 'Kamboçyalı'), 'Romanya': ('Romanya', 'Rumen'),
    'Vietnam': ('Vietnam',), 'Nijerya': ('Nijerya', 'Nijeryalı'),
    'Tayland': ('Tayland',), 'Venezuela': ('Venezuela', 'Venezüella'),
    'BAE': ('Birleşik Arap Emirlikleri', 'BAE'),
    'Belçika': ('Belçika', 'Belçikalı'), 'Portekiz': ('Portekiz',),
    'İsviçre': ('İsviçre', 'İsviçreli'), 'Singapur': ('Singapur',),
    'Litvanya': ('Litvanya', 'Litvanyalı'),
    'Suudi Arabistan': ('Suudi Arabistan', 'Suudi '),
    'Endonezya': ('Endonezya',), 'İrlanda': ('İrlanda',),
    'Malezya': ('Malezya',), 'İsveç': ('İsveç', 'İsveçli'),
    'Filipinler': ('Filipinler', 'Filipin '),
    'Afganistan': ('Afganistan', 'Afgan '),
    'Yeni Zelanda': ('Yeni Zelanda',), 'Kenya': ('Kenya', 'Kenyalı'),
    'Finlandiya': ('Finlandiya', 'Finlandiyalı'),
    'Ürdün': ('Ürdün', 'Ürdünlü'), 'Irak': ('Irak', 'Iraklı'),
    'Mısır': ('Mısır', 'Mısırlı'), 'Danimarka': ('Danimarka', 'Danimarkalı'),
}
# ÜLKEYİ FAİL yapan ipuçları (ülke adının HEMEN ARDINDAN aranır).
AKTOR_IPUCU = ('bağlantılı', 'menşeli', 'merkezli siber', 'destekli',
               'devlet destekli', 'kaynaklı siber', 'hükümetiyle bağlantılı',
               'istihbarat', 'bağlantısı')
# ÜLKEYİ HEDEF yapan ipuçları.
# Sert ünsüzle biten ülke adlarında bulunma eki SERTLEŞİR: "Birleşik
# Krallık'taki". Yalnızca `'daki/'deki` aranınca bu kayıtlar hedef ipucunu
# kaçırıyordu; ölçüldü (2026-09-25) 32 geçiş, hepsi Birleşik Krallık.
HEDEF_IPUCU = ("'deki", "'daki", "'teki", "'taki", "'de", "'da", "'te", "'ta",
               "'ye yönelik", "'ya yönelik", "'yi hedef", "'yı hedef",
               "'nin", "'nın", 'hükümeti', "'e yönelik", "'a yönelik",
               'kurumları', 'şirketleri')

# ── AKTÖR ─────────────────────────────────────────────────────────────────
# Arşivden frekansla çıkarılan kalıplar. Kod adları (APT28, UNC2814…) zaten
# biçimseldir; adlandırılmış gruplar elle onaylanmış bir listeden gelir.
_KOD_RE = re.compile(
    r'\b(APT\d{1,3}|UNC\d{3,5}|TA\d{3,4}|UAT-\d{3,5}|Storm-\d{3,5}'
    r'|CL-[A-Z]{3}-\d{3,5}|REF\d{3,5}|TAG-\d{2,4}|Larva-\d{3,6})\b')
ADLI_AKTOR = (
    'ShinyHunters', 'Scattered Spider', 'The Gentlemen', 'Lazarus',
    'DragonForce', 'TeamPCP', 'Qilin', 'Handala', 'Conti', 'Interlock',
    'Clop', 'Cl0p', 'Phobos', 'Akira', 'Medusa', 'Rhysida', 'LockBit',
    'BlackCat', 'Sandworm', 'Turla', 'Salt Typhoon', 'Volt Typhoon',
    'ToddyCat', 'Mustang Panda', 'Transparent Tribe', 'Dark Caracal',
    'Midnight Blizzard', 'Head Mare', 'Armored Likho', 'Toy Ghouls',
    'Fire Ant', 'SilkParasite', 'Nimbus Manticore', 'Mirage Kitten',
    'Cavern Manticore', 'FamousSparrow', 'Webworm', 'SideCopy',
    'JADEPUFFER', 'Slim Spider', 'Breeze Comet', 'ExfilSquad', 'Aurora',
    'Black Axe', 'Ransom Cartel', 'Jewelbug', 'Red Heron', 'NightEagle',
    'Silver Fox', 'Sapphire Sleet', 'SapphireSleet', 'Hacking Cat',
    # 2026-09-25 taraması: arşivde "grubu/çetesi/tehdit aktörü/olarak
    # bilinen" bağlamında geçtiği DOĞRULANAN, sözlükte OLMAYAN adlar.
    # Aynı taramada eşit sıklıkta çıkan ama aktör OLMAYAN adlar bilerek
    # DIŞARIDA bırakıldı: Rokarolla/RESURGE/GRIDTIDE/FIRESTARTER (zararlı
    # yazılım), DarkSword/Coruna/BlueMoon (istismar kiti), EvilTokens
    # (PhaaS platformu), Nexcorium (Mirai varyantı), Asocks/Doppelganger
    # (hizmet), Nightmare Eclipse (ARAŞTIRMACI), Gold Eagle (ABD federal
    # merkezi), Mythos (yapay zekâ modeli), Play (Google Play).
    'MuddyWater', 'Kimsuky', 'Lotus Blossom', 'Famous Chollima',
    'CyberAv3ngers', 'Dust Specter', 'FishMonger', 'Earth Lusca',
    'Space Pirates', 'Erudite Mogwai', 'Fox Tempest', 'Rapid Brigantine',
    'Vice Society', 'Hunters International', 'World Leaks', 'WorldLeaks',
    'Kamacite', 'Karakurt', 'Trigona', 'Yanluowang', 'Termite', 'Nitrogen',
    'Icarus', 'FulcrumSec', 'The Com', 'REvil', 'Sodinokibi', 'INC',
    'Pay2Key', 'Anubis', 'C77L', 'Payouts King', 'KongTuke',
)
# Aynı aktörün yazım varyantları tek ada indirgenir.
ESANLAM = {'Cl0p': 'Clop', 'SapphireSleet': 'Sapphire Sleet',
           'Gentlemen': 'The Gentlemen', 'WorldLeaks': 'World Leaks',
           'Sodinokibi': 'REvil', 'Vice Society': 'Rapid Brigantine',
           'Earth Lusca': 'FishMonger', 'Space Pirates': 'Webworm',
           'Erudite Mogwai': 'Webworm'}


# Anahtar SÖZCÜK BAŞINDA aranır (sonu serbesttir — Türkçe ek alır).
# ÖLÇÜLDÜ (2026-09-25): düz alt dizi araması 6 sektöre sahte kayıt
# yazıyordu — "senatosu"nda `nato` (57), "havalimanı"nda `liman` (32),
# "kullanıyordu"nda `ordu` (28), "çabasının"da `basın` (20),
# "çokuluslu"da `okul` (7), "web sunucusu altyapısı"nda `su altyapı`.
# Aynı sınıf hata ülke alanında da düzeltilmişti.
_SEK_RE = {k: tuple(re.compile(r'(?<![0-9a-zçğıöşü])' + re.escape(i))
                    for i in ip) for k, ip in SEKTOR.items()}


def sektorler(metin):
    kucuk = metin.lower()
    return sorted(k for k, kaliplar in _SEK_RE.items()
                  if any(r.search(kucuk) for r in kaliplar))


# İpucu penceresi ÖĞE SINIRINDA kesilir. 40 karakterlik ham kuyruk
# komşu öğeye taşıyordu: "Japonya hükümeti, Çin menşeli saldırılara maruz
# kaldı" cümlesinde Japonya'nın kuyruğu "menşeli" ipucunu yakalayıp
# Japonya'yı FAİL sayıyordu. Virgül/nokta ve " ve " bağlacı sınırdır.
_SINIR_RE = re.compile(r'[,.;:!?]| ve | ile | ancak | fakat ')


def _kuyruk(metin, son):
    ham = metin[son:son + 40]
    kesme = _SINIR_RE.search(ham)
    return (ham[:kesme.start()] if kesme else ham).lower()


def _rol(metin, kalip):
    """Ülke adından sonraki öğe sınırına kadar bakıp rolü belirler."""
    aktor = hedef = False
    for m in re.finditer(re.escape(kalip), metin):
        kuyruk = _kuyruk(metin, m.end())
        # EN YAKIN İPUCU KAZANIR. Önce fail ipuçlarına bakmak yanlıştı:
        # "Birleşik Krallık'taki yetkililerin Rus menşeli saldırıya maruz
        # kalması" kuyruğunda hemen bitişikteki `'taki` (hedef) varken
        # ilerideki `menşeli` (fail) kazanıyor ve kurban ülke FAİL
        # sayılıyordu. Konum, ipucu türünden daha güvenilir bir sinyaldir.
        ay = min((kuyruk.find(i) for i in AKTOR_IPUCU if i in kuyruk),
                 default=None)
        hy = min((kuyruk.find(i) for i in HEDEF_IPUCU if i in kuyruk),
                 default=None)
        if ay is not None and (hy is None or ay < hy):
            aktor = True
        elif hy is not None:
            hedef = True
        else:
            hedef = hedef or None  # ipucu yok: kararsız
    return aktor, hedef


def ulkeler(metin):
    """({fail ülkeler}, {hedef ülkeler}) — ipucu yoksa hedef sayılır."""
    fail, hedef = set(), set()
    for ad, kaliplar in ULKE.items():
        a = h = False
        gecti = False
        for kalip in kaliplar:
            if kalip not in metin:
                continue
            gecti = True
            ai, hi = _rol(metin, kalip)
            a = a or ai
            h = h or bool(hi)
        if not gecti:
            continue
        if a:
            # FAİL ROLÜ HEDEFİ EZER — bir ülke aynı kayıtta iki rolde
            # görünmez. ÖLÇÜLDÜ (2026-09-25): 5.109 kaydın 108'inde
            # (%2) ülke her iki listeye de giriyordu ve örnekler
            # bakıldığında hedef ipucu neredeyse hep yanlıştı:
            # "Tayvan'ın Çin Menşeli Saldırılara Maruz Kalması" kaydında
            # Çin yalnızca faildir, "Birleşik Krallık'taki Yetkililerin
            # Rus Menşeli Saldırısı"nda Rusya yalnızca faildir. İpucusuz
            # varsayılan (hedef) ZAYIF bir kestirimdir; açık fail ipucu
            # ona üstün gelir.
            # KABUL EDİLEN KAYIP: gerçekten iki rollü kayıtlar ("İran
            # Destekli Hackerların İranlıları Hedeflemesi") kurban
            # rolünü yitirir — 108 kaydın küçük bir azınlığı.
            fail.add(ad)
        else:
            # İpucu hiç yoksa ülke HEDEF sayılır: arşiv ağırlıklı olarak
            # kurban perspektifinden yazılmış ("X şirketi saldırıya uğradı").
            hedef.add(ad)
    return sorted(fail), sorted(hedef)


def aktorler(metin):
    bulunan = set(_KOD_RE.findall(metin))
    for ad in ADLI_AKTOR:
        if re.search(r'\b' + re.escape(ad) + r'\b', metin):
            bulunan.add(ad)
    return sorted({ESANLAM.get(a, a) for a in bulunan})


def arsivi_tara(yol=ARSIV):
    kayitlar, gun, cur = [], None, None
    for no, satir in enumerate(open(yol, encoding='utf-8')):
        m = _GUN_RE.match(satir)
        if m:
            gun = datetime.date(int(m.group(3)), _AY[m.group(2)],
                                int(m.group(1))).isoformat()
            cur = None
            continue
        m = _BAS_RE.match(satir)
        if m:
            cur = {'gun': gun, 'sira': int(m.group(1)),
                   'baslik': m.group(2).strip(), 'para': [],
                   'satir_no': no, 'meta': [], 'meta_no': []}
            kayitlar.append(cur)
            continue
        if cur is None:
            continue
        if satir.startswith('»'):
            cur['meta'].append(satir.rstrip('\n'))
            cur['meta_no'].append(no)
            continue
        if satir.strip() and not satir.startswith(('─', '=', '(')):
            cur['para'].append(satir.strip())
    return kayitlar


def cikar(kayit):
    metin = kayit['baslik'] + ' ' + ' '.join(kayit['para'])
    fail, hedef = ulkeler(metin)
    return {'sektor': sektorler(metin), 'aktor_ulke': fail,
            'hedef': hedef, 'aktor': aktorler(metin)}


def satir_kur(v):
    parca = []
    for alan in ('sektor', 'hedef', 'aktor_ulke', 'aktor'):
        if v[alan]:
            parca.append(f'{alan}={",".join(v[alan])}')
    return ('» varlik | ' + ' | '.join(parca) + '\n') if parca else None


def main():
    kayitlar = arsivi_tara()
    cikti = [cikar(k) for k in kayitlar]
    n = len(kayitlar)
    ks = sum(1 for v in cikti if v['sektor'])
    kh = sum(1 for v in cikti if v['hedef'])
    kf = sum(1 for v in cikti if v['aktor_ulke'])
    ka = sum(1 for v in cikti if v['aktor'])
    print(f'kayıt {n} | sektör %{100*ks//n} | hedef ülke %{100*kh//n} '
          f'| fail ülke %{100*kf//n} | adlandırılmış aktör %{100*ka//n}')
    sk = collections.Counter(s for v in cikti for s in v['sektor'])
    print('sektör (çok etiketli):', sk.most_common())
    print('fail ülke:', collections.Counter(
        u for v in cikti for u in v['aktor_ulke']).most_common(8))
    print('hedef ülke:', collections.Counter(
        u for v in cikti for u in v['hedef']).most_common(8))
    print('aktör:', collections.Counter(
        a for v in cikti for a in v['aktor']).most_common(10))

    ornek = next((int(a) for a in sys.argv[1:] if a.isdigit()), 0)
    if '--ornek' in sys.argv and ornek:
        print('\n-- örnek --')
        for k, v in list(zip(kayitlar, cikti))[:ornek]:
            print(f'{k["gun"]} {k["baslik"][:58]}\n   {satir_kur(v) or "(boş)"}',
                  end='')

    if '--yaz' not in sys.argv:
        print('\n(yazmak için --yaz)')
        return 0

    satirlar = open(ARSIV, encoding='utf-8').readlines()
    ekle = guncelle = 0
    for k, v in sorted(zip(kayitlar, cikti),
                       key=lambda p: -p[0]['satir_no']):
        yeni = satir_kur(v)
        mevcut = next((no for no, m in zip(k['meta_no'], k['meta'])
                       if _VARLIK_RE.match(m)), None)
        if yeni is None:
            continue
        if mevcut is not None:
            if satirlar[mevcut] != yeni:
                satirlar[mevcut] = yeni
                guncelle += 1
        else:
            # Üstveri bloğunun SONUNA: mevcut » satırlarından sonra.
            yer = (max(k['meta_no']) + 1) if k['meta_no'] else None
            if yer is None:
                continue
            satirlar.insert(yer, yeni)
            ekle += 1
    print(f'\neklenecek: {ekle} | güncellenecek: {guncelle}')
    if '--kuru' in sys.argv:
        print('(kuru koşu)')
        return 0
    _arsiv_yaz.guvenli_yaz(ARSIV, satirlar)
    print(f'✅ {ARSIV} güncellendi')
    return 0


if __name__ == '__main__':
    sys.exit(main())
