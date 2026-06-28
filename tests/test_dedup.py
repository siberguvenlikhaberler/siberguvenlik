"""
src/dedup.py — aynı-olay (same-event) tespiti ve KRİTİK 3 ayrıklık garantisi testleri.

Bu testler LLM veya ağ gerektirmez; saf string mantığını doğrular.
Senaryolar 28.06.2026 raporundaki gerçek mükerrer vakadan türetilmiştir:
iki kaynak aynı Rus istihbarat / Signal kimlik-avı kampanyasını FARKLI
başlıklarla anlatıyordu ve ikisi de KRİTİK 3'e girmişti.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import dedup


# ── Gerçek vakadan türetilmiş görünümler ───────────────────────────────────
SIGNAL_A = {  # securityaffairs — "Signal Recovery Keys"
    'tr_title': 'Rus İstihbaratının Signal Yedekleme Kurtarma Anahtarlarını Ele Geçirmesi',
    'title': 'New FBI Alert: Russian Intelligence Uses Signal Recovery Keys to Access Messages',
    'paragraph': ('FBI ve CISA, Rus istihbarat servislerinin Signal kullanıcılarını hedef '
                  'alan kimlik avı kampanyaları hakkında uyarı yayımlamıştır. FSB bağlantılı '
                  'UNC5792 ve UNC4221 gruplarının Ukraynalı yetkilileri, askeri personeli ve '
                  'gazetecileri hedef aldığı, sahte destek mesajlarıyla Signal yedekleme '
                  'kurtarma anahtarlarını ele geçirdiği bildirilmektedir.'),
    'full_text': '',
}
SIGNAL_B = {  # thehackernews — "Fake Support Texts"
    'tr_title': 'Rus İstihbarat Servislerinin Ukraynalı Yetkililerin Mesajlaşma Hesaplarını Ele Geçirmesi',
    'title': 'Ukraine Says Russian Intelligence Used Fake Support Texts to Steal Messaging Credentials',
    'paragraph': ('Ukrayna Güvenlik Servisi ve FBI, Rus istihbarat servislerinin hükümet '
                  'yetkililerini, askeri personeli ve aktivistleri hedef alan siber casusluk '
                  'operasyonunu ortaya çıkarmıştır. Saldırganlar sahte destek mesajlarıyla '
                  'kullanıcıları yedekleme kurtarma anahtarlarını paylaşmaya zorlamaktadır. '
                  'Faaliyetler Star Blizzard ve UNC5792 gruplarıyla ilişkilendirilmektedir.'),
    'full_text': '',
}
SHARKLOADER = {  # helpnetsecurity — farklı olay
    'tr_title': 'Bilinmeyen Saldırganların SharkLoader Yazılımıyla Hükümetleri Hedeflemesi',
    'title': 'Mystery hackers use novel SharkLoader dropper against governments, software devs',
    'paragraph': ('Kaspersky araştırmacıları, çok sayıda ülkedeki hükümet kurumlarını hedef '
                  'alan StrikeShark operasyonunu tespit etmiştir. Saldırganlar SharkLoader '
                  'yükleyicisiyle ağlara sızmakta ve Cobalt Strike ile kalıcılık sağlamaktadır.'),
    'full_text': '',
}
MOZILLA = {  # bleepingcomputer — farklı olay
    'tr_title': 'Mozilla Araştırmacılarının Yapay Zeka Kodlama Araçlarını Kötü Amaçlı Yazılım Çalıştırmakla Suçlaması',
    'title': 'Clean GitHub repo tricks AI coding agents into running malware',
    'paragraph': ('Mozilla 0DIN ekibi, otonom yapay zeka kodlama araçlarının temiz görünen '
                  'GitHub depoları üzerinden kötü amaçlı yazılım çalıştırmak üzere '
                  'kandırılabildiğini tespit etmiştir.'),
    'full_text': '',
}
OPENAI = {  # thehackernews — farklı olay (AI ama farklı konu)
    'tr_title': "OpenAI'ın GPT-5.6 Sol Modelini Siber Güvenlik Korumalarıyla Ön İzlemeye Sunması",
    'title': 'OpenAI Previews GPT-5.6 Sol With Restricted Access and Stronger Cyber Safeguards',
    'paragraph': ('OpenAI, GPT-5.6 Sol modelini sınırlı bir kullanıcı grubuna açmıştır. '
                  'Model savunma amaçlı kod incelemesi ve yama geliştirme için '
                  'tasarlanmıştır.'),
    'full_text': '',
}


def test_same_event_positive_signal_campaign():
    """Aynı kampanyayı farklı başlıkla anlatan iki haber → AYNI OLAY."""
    same, why = dedup.same_event(SIGNAL_A, SIGNAL_B, explain=True)
    assert same, f"Mükerrer yakalanamadı: {why}"
    assert 'unc5792' in why.lower() or 'topic' in why.lower()


def test_same_event_negatives():
    """Farklı olaylar AYNI OLAY sayılmamalı (yanlış-pozitif yok)."""
    assert not dedup.same_event(SIGNAL_A, SHARKLOADER)
    assert not dedup.same_event(SIGNAL_A, MOZILLA)
    assert not dedup.same_event(SHARKLOADER, MOZILLA)
    # Mozilla & OpenAI ikisi de "yapay zeka" ama farklı olay
    assert not dedup.same_event(MOZILLA, OPENAI)
    assert not dedup.same_event(SHARKLOADER, OPENAI)


def test_codename_shared():
    """Ortak ayırt edici kod adı tek başına yeterli sinyaldir."""
    a = {'tr_title': 'FortiBleed Kampanyasının Yayılması', 'title': 'FortiBleed spreads', 'paragraph': '', 'full_text': ''}
    b = {'tr_title': 'Yeni FortiBleed Saldırısı Tespit Edildi', 'title': 'New FortiBleed attack', 'paragraph': '', 'full_text': ''}
    assert dedup.same_event(a, b)


def test_codename_denylist_not_triggered():
    """Yaygın vendor adı (Fortinet) tek başına aynı-olay sinyali DEĞİLDİR."""
    a = {'tr_title': 'Fortinet Ürününde Açık', 'title': 'Fortinet flaw A', 'paragraph': 'Bir zafiyet bulundu.', 'full_text': ''}
    b = {'tr_title': 'Fortinet Cihazında Sorun', 'title': 'Fortinet flaw B', 'paragraph': 'Başka bir konu.', 'full_text': ''}
    assert not dedup.same_event(a, b)


def test_different_cve_not_same():
    """Farklı CVE'ler + farklı konu → aynı olay değil."""
    a = {'tr_title': 'Cisco CVE-2026-1111 Açığı', 'title': 'Cisco CVE-2026-1111', 'paragraph': 'Cisco router zafiyeti.', 'full_text': ''}
    b = {'tr_title': 'Apache CVE-2026-2222 Açığı', 'title': 'Apache CVE-2026-2222', 'paragraph': 'Apache sunucu sorunu.', 'full_text': ''}
    assert not dedup.same_event(a, b)


def _views(mapping):
    return lambda i: mapping[i]


def test_pick_distinct_guarantees_no_duplicate_in_top3():
    """KRİTİK 3 garantisi: dup aday atlanır, sıradaki ayrık adayla doldurulur."""
    mapping = {4: SIGNAL_A, 1: SIGNAL_B, 9: SHARKLOADER, 3: MOZILLA, 2: OPENAI}
    # LLM sırası dup'ı 1. ve 2. sıraya koymuş olsun: [4, 1, 9, 3, 2]
    top3 = dedup.pick_distinct([4, 1, 9, 3, 2], _views(mapping), n=3)
    assert len(top3) == 3
    assert 4 in top3 and 1 not in top3, f"Dup [1] elenmeliydi: {top3}"
    # Sonuçta hiçbir çift aynı-olay olmamalı
    for i in range(len(top3)):
        for j in range(i + 1, len(top3)):
            assert not dedup.same_event(mapping[top3[i]], mapping[top3[j]])


def test_drop_duplicates_against_top3():
    """Gövde, KRİTİK 3 ile aynı-olay olan haberi göstermemeli."""
    mapping = {4: SIGNAL_A, 1: SIGNAL_B, 9: SHARKLOADER, 3: MOZILLA}
    body = dedup.drop_duplicates_against([1, 3, 9], reference_ids=[4], get_view=_views(mapping))
    assert 1 not in body, "Dup gövdeye sızdı"
    assert 3 in body and 9 in body
