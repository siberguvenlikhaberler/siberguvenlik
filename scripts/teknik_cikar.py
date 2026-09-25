#!/usr/bin/env python3
"""TEKNİK ÇIKARIM — CVE / etkilenen ürün / aktif istismar alanlarını yazar.

NEDEN VAR: yıl sonu raporu "yılın en çok istismar edilen açıkları",
"hangi satıcının ürünleri kaç olayda geçti", "kaç açık aktif istismar
altındaydı" sorularını soracak. ÖLÇÜLDÜ (2026-09-23): 956 kayıtta CVE
geçiyor, 874 tekil açık var, 352 kayıt birden çok CVE taşıyor — yani bilgi
arşivde VAR ama yalnızca serbest metinde; yapılı alan olmadan her sorgu
elle regex yazmayı gerektiriyor ve iki analiz iki farklı sonuç veriyor.

VARLIK ALANIYLA AYNI DESEN, aynı gerekçelerle: yargı değil çıkarım olduğu
için LLM'e değil KURALLARA bağlı — tekrar üretilebilir, kayma üretmez,
`--ornek` ile denetlenir. Hem geriye dönük koşar hem üretim hattında yazar.

Yazılan satır (boş alan YAZILMAZ):
    » teknik | cve=CVE-2026-1731,CVE-2026-2441 | urun=Cisco,Windows | istismar=aktif

ÜÇ TASARIM KARARI:
1. CVE ÇOK ETİKETLİDİR. 352 kayıt birden çok açık anlatıyor (en yüksek 14).
   Tek CVE seçmek, bir kampanyanın istismar zincirini tek açığa indirger.
2. ÜRÜN yalnızca TEKNİK BAĞLAM varsa yazılır. "Microsoft" arşivde 1.652 kez
   geçiyor ama çoğu satıcı raporu ya da şirket haberidir, etkilenen ürün
   değil. Kayıt bir CVE ya da açık/zafiyet/yama/istismar ipucu taşımıyorsa
   ürün alanı BOŞ bırakılır — kapsam düşer ama alan anlamlı kalır.
3. `istismar=aktif` yalnızca AÇIK ipucu ile. "aktif olarak istismar",
   "vahşi doğada", "sıfır gün" gibi kalıplar aranır; "istismar edilebilir"
   (potansiyel) BİLEREK sayılmaz — ikisi karışırsa "yılın kaç açığı aktif
   istismar altındaydı" sorusu şişer.

Kullanım: python3 scripts/teknik_cikar.py [--yaz] [--ornek N] [--kuru]
"""
import collections
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

_TEKNIK_RE = re.compile(r'^»\s*teknik\b')

# Tarayıcı KOPYALANMAZ — varlik_cikar tek kaynaktır; iki tarayıcı zamanla
# ayrışır ve aynı arşivde iki farklı kayıt kümesi oluşurdu.
_spec = importlib.util.spec_from_file_location(
    'varlik_cikar', pathlib.Path(__file__).resolve().parent / 'varlik_cikar.py')
_varlik = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_varlik)
arsivi_tara = _varlik.arsivi_tara

_CVE_RE = re.compile(r'CVE-\d{4}-\d{4,7}', re.I)

# Teknik bağlam ipucu — ürün alanının yazılabilmesi için ŞART.
# `açı[ğk]` KULLANILMAZ: "açıklamıştır" ve "dava açmıştır" ile eşleşiyordu
# ve kolluk/duyuru haberlerine teknik ipucu uyduruyordu. Yalnızca yumuşamış
# gövde (`açığ`) ve çoğul biçimler alınır.
_TEKNIK_IPUCU = re.compile(
    r'açığ|açıklar|güvenlik açı|zafiyet|yama|güncellem|istismar|exploit|'
    r'sıfır gün|zero.?day|CVE-|kod çalıştır|yetki yükselt|kimlik doğrulama '
    r'atlat|arka kapı|RCE\b', re.I)

# Aktif istismar — POTANSİYEL ifadeler bilerek dışarıda.
_ISTISMAR_RE = re.compile(
    r'aktif olarak istismar|aktif istismar|vahşi doğada|in the wild|'
    r'istismar edilmekte|istismar edildiği (?:tespit|doğrulan|bildiril)|'
    r'sıfır gün(?:ü|ünü)? (?:açığ|zafiyet|olarak)|zero.?day (?:açığ|exploit)|'
    r'KEV kataloğ|bilinen istismar edilen', re.I)

# Satıcı / ürün — anahtar: kanonik ad, değer: aranacak diziler.
# Kısa ve çok anlamlı diziler (ör. "F5", "React") ancak ayırt edici
# bağlamla alınır; yoksa Türkçe metinde rastgele eşleşir.
URUN = {
    'Microsoft': ('microsoft', 'windows', 'exchange server', 'sharepoint',
                  'outlook', 'active directory', 'azure', 'office 365',
                  'microsoft 365', 'defender'),
    'Cisco': ('cisco', 'ios xe', 'firepower', 'adaptive security appliance',
              'asa yazılım', 'webex'),
    'Fortinet': ('fortinet', 'fortios', 'fortigate', 'fortimanager',
                 'fortiweb'),
    'Ivanti': ('ivanti', 'connect secure', 'endpoint manager'),
    'Palo Alto': ('palo alto', 'pan-os', 'globalprotect'),
    'Citrix': ('citrix', 'netscaler'),
    'SonicWall': ('sonicwall',),
    'VMware': ('vmware', 'vcenter', 'esxi', 'workspace one'),
    'Oracle': ('oracle', 'weblogic', 'e-business suite'),
    'SAP': ('sap netweaver', 'sap',),
    'Google': ('google chrome', 'chrome', 'android', 'google workspace',
               'chromium'),
    'Apple': ('apple', 'macos', 'ios ', 'ipados', 'safari', 'iphone'),
    'Linux': ('linux çekirde', 'linux kernel', 'linux sistem', 'ubuntu',
              'red hat', 'debian'),
    'Adobe': ('adobe', 'acrobat', 'coldfusion'),
    'WordPress': ('wordpress', 'woocommerce', 'wp eklenti'),
    'Atlassian': ('atlassian', 'confluence', 'jira'),
    'GitLab': ('gitlab',),
    'GitHub': ('github',),
    'Zimbra': ('zimbra',),
    'Veeam': ('veeam',),
    'Progress': ('progress software', 'moveit', 'whatsup gold'),
    'Zoho': ('zoho', 'manageengine'),
    'Juniper': ('juniper', 'junos'),
    'F5': ('f5 big-ip', 'big-ip', 'f5 network'),
    'Salesforce': ('salesforce', 'salesloft'),
    'Splunk': ('splunk',),
    'QNAP': ('qnap',),
    'Samsung': ('samsung',),
    'Kubernetes': ('kubernetes', 'k8s'),
    'Docker': ('docker',),
    'npm': ('npm paket', 'npm depo', 'node package'),
    'PyPI': ('pypi', 'python paket dep'),
    'Jenkins': ('jenkins',),
    'Apache': ('apache struts', 'apache tomcat', 'apache http', 'log4j'),
    # 2026-09-25 taraması: teknik bağlamlı kayıtlarda 6+ kez geçtiği
    # ÖLÇÜLEN ama sözlükte olmayan satıcılar. Yapay zekâ ürünleri bu
    # arşivde ayrı bir küme oluşturuyor; satıcı adı olarak eklendiler.
    'Anthropic': ('anthropic', 'claude code', 'claude '),
    'OpenAI': ('openai', 'chatgpt'), 'Telegram': ('telegram',),
    'Mozilla': ('mozilla', 'firefox'), 'Check Point': ('check point',),
    # 'intel' TEK BAŞINA ALINMAZ: arşivdeki geçişlerin çoğu tehdit
    # istihbaratı firması "Intel 471" ve "watchTowr Intel"dir, çip
    # satıcısı değil.
    'Intel': ('intel işlemci', 'intel cpu', 'intel sunucu', 'intel çip'),
    'WhatsApp': ('whatsapp',), 'Signal': ('signal',),
    'Nginx': ('nginx',), 'Trend Micro': ('trend micro', 'apex one'),
    'LiteLLM': ('litellm',), 'Broadcom': ('broadcom',),
    'NVIDIA': ('nvidia',), 'PostgreSQL': ('postgresql', 'postgres'),
    'Redis': ('redis',), 'Magento': ('magento',), 'Siemens': ('siemens',),
    'Dell': ('dell',), 'TP-Link': ('tp-link',),
    'SolarWinds': ('solarwinds',), 'Joomla': ('joomla',),
    'Zoom': ('zoom',),
    'Qualcomm': ('qualcomm',), 'AWS': ('aws', 'amazon web'),
    'Cloudflare': ('cloudflare',), 'Kaspersky': ('kaspersky',),
    'ESET': ('eset',), 'CrowdStrike': ('crowdstrike',),
    'Akamai': ('akamai',), 'Okta': ('okta',),
    'SentinelOne': ('sentinelone',), 'Sophos': ('sophos',),
    'Hugging Face': ('hugging face', 'huggingface'),
    'Roundcube': ('roundcube',), 'Huawei': ('huawei',),
    'Elastic': ('elasticsearch', 'elastic stack'),
    'Notepad++': ('notepad++',), 'JetBrains': ('jetbrains', 'teamcity'),
    'Snowflake': ('snowflake',), 'WinRAR': ('winrar',),
    'D-Link': ('d-link',), 'Netgear': ('netgear',),
    'MikroTik': ('mikrotik',), 'Ubiquiti': ('ubiquiti', 'unifi'),
    'Ollama': ('ollama',), 'Opera': ('opera tarayıc', 'opera browser'),
}


def _metin(kayit):
    """Başlık noktayla kapatılır: arşivde başlıklar çoğu kez noktasızdır ve
    gövdeye bitişik yazılınca cümle ayırıcı ilk paragrafı başlıkla TEK
    cümle sayıyordu — "RedVDS'nin Çökertilmesi Microsoft, ..." böyle tek
    cümle görünüp ürün alanına yanlış satıcı yazdırıyordu."""
    bas = kayit['baslik'].rstrip()
    if bas and bas[-1] not in '.!?':
        bas += '.'
    return bas + ' ' + ' '.join(kayit['para'])


def cveler(metin):
    """Tekil ve sıralı — aynı açık iki kez sayılmasın."""
    return sorted({c.upper() for c in _CVE_RE.findall(metin)})


# Anahtarlar SÖZCÜK SINIRIYLA aranır. Düz alt dizi araması ölçüldü ve
# yanlış eşleşti: `sap` anahtarı "hesap" içinde geçtiği için SAP 240 kayıtta
# çıkmıştı. Sondaki sınır ARANMAZ — Türkçe ekler bitişik yazılır
# ("Windows'ta", "Cisco'nun").
# SON SINIR da aranır, ama KÜÇÜK harfle devam ediyorsa. ÖLÇÜLDÜ
# (2026-09-25): yalnızca baş sınır aranınca `sap` "saptanmıştır" içinde
# 161 kez, `opera` "operasyon" içinde 698 kez eşleşiyordu — `hesap`
# hatasının sondan tekrarı. Büyük harf, rakam ve alt çizgi devamı SERBEST
# bırakılır: AppleScript, CitrixBleed, AzureHound, github_token gerçek
# ürün sinyalidir. Türkçe ek apostrofla yazıldığı için ("Windows'ta")
# zaten sınır sayılır; ölçümde apostrofsuz ek alan tek bir ürün adı yok.
# Son sınır BÜYÜK/küçük harfe DUYARLI olmalıdır — `re.I` altında
# [a-z] büyük harfi de yakalar ve CitrixBleed'i düşürürdü; `(?-i:...)`.
_URUN_RE = {ad: re.compile(
    r'(?<![\w\u00c0-\u024f])(?:' +
    '|'.join(re.escape(a) for a in sorted(anahtarlar, key=len, reverse=True))
    + r')(?-i:(?![a-zçğıöşü]))', re.I)
    for ad, anahtarlar in URUN.items()}


_CUMLE_RE = re.compile(r'[^.!?]*[.!?]|[^.!?]+$')


def urunler(metin):
    """Ürün adı, teknik ipucuyla AYNI CÜMLEDE geçmelidir.

    Tüm metinde aramak satıcıyı RAPORLAYAN taraf olduğunda da yazıyordu:
    "RedVDS'nin çökertilmesi — Microsoft, Mart 2025'ten bu yana..." kaydı
    `urun=Microsoft` alıyordu; Microsoft orada etkilenen ürün değil,
    haberi veren şirkettir. Ülke rolündeki fail/hedef ayrımının teknik
    karşılığı budur.
    """
    if not _TEKNIK_IPUCU.search(metin):
        return []
    bulunan = set()
    for c in _CUMLE_RE.finditer(metin):
        cumle = c.group()
        if not _TEKNIK_IPUCU.search(cumle):
            continue
        bulunan.update(ad for ad, r in _URUN_RE.items() if r.search(cumle))
    return sorted(bulunan)


def istismar(metin):
    return 'aktif' if _ISTISMAR_RE.search(metin) else None


def cikar(kayit):
    metin = _metin(kayit)
    return {'cve': cveler(metin), 'urun': urunler(metin),
            'istismar': istismar(metin)}


def satir_kur(v):
    parca = []
    if v['cve']:
        parca.append('cve=' + ','.join(v['cve']))
    if v['urun']:
        parca.append('urun=' + ','.join(v['urun']))
    if v['istismar']:
        parca.append('istismar=' + v['istismar'])
    return ('» teknik | ' + ' | '.join(parca) + '\n') if parca else None


def main():
    kayitlar = arsivi_tara()
    cikti = [cikar(k) for k in kayitlar]
    n = len(kayitlar)
    kc = sum(1 for v in cikti if v['cve'])
    ku = sum(1 for v in cikti if v['urun'])
    ki = sum(1 for v in cikti if v['istismar'])
    print(f'kayıt {n} | CVE %{100*kc//n} ({kc}) | ürün %{100*ku//n} ({ku}) '
          f'| aktif istismar %{100*ki//n} ({ki})')
    cs = collections.Counter(c for v in cikti for c in v['cve'])
    print('tekil CVE:', len(cs), '| en çok geçen:', cs.most_common(6))
    print('ürün:', collections.Counter(
        u for v in cikti for u in v['urun']).most_common(12))

    ornek = next((int(a) for a in sys.argv[1:] if a.isdigit()), 0)
    if '--ornek' in sys.argv and ornek:
        print('\n-- örnek --')
        for k, v in [(k, v) for k, v in zip(kayitlar, cikti)
                     if satir_kur(v)][:ornek]:
            print(f'{k["gun"]} {k["baslik"][:58]}\n   {satir_kur(v)}', end='')

    if '--yaz' not in sys.argv:
        print('\n(yazmak için --yaz)')
        return 0

    satirlar = open(ARSIV, encoding='utf-8').readlines()
    ekle = guncelle = 0
    for k, v in sorted(zip(kayitlar, cikti), key=lambda p: -p[0]['satir_no']):
        yeni = satir_kur(v)
        if yeni is None:
            continue
        mevcut = next((no for no, m in zip(k['meta_no'], k['meta'])
                       if _TEKNIK_RE.match(m)), None)
        if mevcut is not None:
            if satirlar[mevcut] != yeni:
                satirlar[mevcut] = yeni
                guncelle += 1
        elif k['meta_no']:
            satirlar.insert(max(k['meta_no']) + 1, yeni)
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
