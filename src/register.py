"""Resmi-dil (register) denetimi — saf, LLM'siz test edilebilir yardımcılar.

Raporun gövde paragrafları RESMİ Türkçe haber-analiz üslubuyla yazılmalıdır:
geçmiş olaylar "-mIştIr" (olmuştur, yapmıştır, tespit edilmiştir), süregelenler
"-mAktAdIr" (belirtilmektedir) kipiyle anlatılır. Laubali/konuşma dili "-DI" basit
geçmiş zamanı (oldu, yaptı, etti, gerçekleşti, açıkladı) gövdede İSTENMEZ.

Bu modül yalnızca TESPİT eder (hangi paragraflar laubali geçmiş içeriyor); asıl
düzeltmeyi (yeniden yazım) Auditor'ın LLM adımı yapar. Deterministik suffix
değişimi (dı→mıştır) Türkçe ses uyumu/kök değişimi nedeniyle güvenilmez olduğu
için burada YAPILMAZ.
"""
import re

# Laubali (konuşma dili) 3. tekil/çoğul basit geçmiş zaman ekleri: -dı/-di/-du/-dü,
# -tı/-ti/-tu/-tü ve çoğul -lar/-ler. Türkçe SOV olduğundan resmi haber düzyazısında
# cümlenin ANA FİİLİ cümle SONUNDADIR; bu yüzden yalnızca CÜMLE SONU konumunu
# (kapanış tırnağı/parantezi opsiyonel, ardından . ! ? …) hedefleriz. Bu, "kaydı",
# "adı" gibi isim+iyelik yapılarının cümle ortasında yanlış-pozitif üretmesini
# büyük ölçüde önler.
#
# Resmi kipler bu kalıba TAKILMAZ: "-mıştır/-miştir" ve kopula "-dır/-dir",
# "-maktadır/-mektedir" hepsi "r" ile biter → ek doğrudan noktalamadan önce gelmez.
_CLOSERS = r'["\'»”’\)\]\}]*'
_CASUAL_PAST_AT_SENTENCE_END = re.compile(
    r'\b\w{2,}?(?:dı|di|du|dü|tı|ti|tu|tü)(?:lar|ler)?'
    r'(?=' + _CLOSERS + r'\s*[.!?…])',
    re.IGNORECASE | re.UNICODE,
)

# Laubali sayılmayacak bitişler. İkiye ayrılır:
#  (1) RESMİ kipler — zaten "r" ile biter, regex lookahead'i geçmez ama güvence:
#      -mıştır (geçmiş), -maktadır/-mektedir (süren), kopula -dır/-tır.
#  (2) BİRLEŞİK geçmiş kipler — "-DI" ile bitse de KONUŞMA DİLİ BASİT GEÇMİŞ
#      DEĞİLDİR; resmi anlatıda kabul edilir, yeniden yazdırılmaz:
#      -mıştı/-mişti (mişli birleşik/geçmişin geçmişi), -maktaydı/-mekteydi
#      (sürekli geçmiş), -abilirdi/-abildi (olasılık), -acaktı/-ecekti (niyet).
# NOT: Aorist -ırdı/-ardı KASITEN dışlanmaz çünkü çıplak basit geçmişle karışır
# (vardı/verdi çıplak ↔ gelirdi/yapardı birleşik); bu tür seyrek artık-pozitifleri
# Auditor'ın LLM adımı "zaten resmi" diyerek geçer.
_ACCEPTABLE_SUFFIXES = (
    # (1) resmi
    'mıştır', 'miştir', 'muştur', 'müştür',
    'maktadır', 'mektedir', 'dır', 'dir', 'dur', 'dür',
    'tır', 'tir', 'tur', 'tür',
    # (2) birleşik geçmiş
    'mıştı', 'mişti', 'muştu', 'müştü',
    'maktaydı', 'mekteydi', 'aktaydı', 'ektaydi',
    'abilirdi', 'ebilirdi', 'abildi', 'ebildi',
    'amazdı', 'emezdi', 'acaktı', 'ecekti',
)


def find_casual_past_words(text):
    """Metindeki CÜMLE SONU laubali (-DI) basit geçmiş zaman fiillerini döndürür.

    Yalnızca cümle-sonu noktalamasından (isteğe bağlı kapanış tırnağı/parantezi
    ardından . ! ? …) hemen önce gelen laubali geçmiş fiilleri yakalar. Resmi
    "-mıştır/-maktadır/-dır" kipleri yakalanmaz. Saf fonksiyon; LLM'siz test edilir.
    """
    if not text:
        return []
    hits = []
    for m in _CASUAL_PAST_AT_SENTENCE_END.finditer(text):
        w = m.group(0)
        wl = w.lower()
        if wl.endswith(_ACCEPTABLE_SUFFIXES):
            continue
        hits.append(w)
    return hits


def has_casual_past(text):
    """Metin, gövdede istenmeyen laubali (-DI) cümle-sonu geçmiş zaman içeriyorsa
    True döner. Auditor bu paragrafları resmi register'a yeniden yazdırır."""
    return bool(find_casual_past_words(text))
