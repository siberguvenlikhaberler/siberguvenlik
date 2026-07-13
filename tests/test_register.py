"""src.register — resmi-dil (register) tespiti birim testleri.

Gövde paragraflarında istenmeyen laubali (-DI) CÜMLE SONU basit geçmiş zamanı
yakalar; resmi (-mIştIr/-mAktAdIr) ve birleşik geçmiş kiplerini yakalamaz.
"""
from src.register import has_casual_past, find_casual_past_words


class TestCasualPastYakalanir:
    """Laubali basit geçmiş (cümle sonunda) YAKALANMALI."""

    def test_bare_simple_past(self):
        for s in ("Saldırı dün gerçekleşti.",
                  "Şirket sistemleri izole etti.",
                  "Grup 30 BTC fidye talep etti.",
                  "Araştırmacılar yeni bir yöntem buldu.",
                  "FBI operasyonu duyurdu.",
                  "Fidye talebi 1,9 milyon dolara ulaştı."):
            assert has_casual_past(s), s

    def test_plural_simple_past(self):
        assert has_casual_past("Yetkililer olayı doğruladılar.")

    def test_multiple_sentences_one_casual(self):
        # ilk cümle resmi, ikincisi laubali → yakalanır
        assert has_casual_past(
            "Olay tespit edilmiştir. Ardından sistem çöktü.")

    def test_copula_and_continuous_past_are_casual(self):
        # copula geçmiş ("değildi") ve anlatı süreklisi ("geliyordu") resmi değildir
        assert has_casual_past("Bu durum beklenen bir sonuç değildi.")
        assert has_casual_past("Zararlı yazılım arka planda çalışıyordu.")


class TestResmiYakalanmaz:
    """Resmi / birleşik kipler YANLIŞ-POZİTİF ÜRETMEMELİ."""

    def test_formal_mistir(self):
        for s in ("Saldırı dün gerçekleşmiştir.",
                  "Şirket sistemlerini izole etmiştir.",
                  "Grup 30 BTC fidye talep etmiştir.",
                  "Saldırganın adı açıklanmamıştır."):
            assert not has_casual_past(s), s

    def test_formal_maktadir(self):
        for s in ("Bu durum güvenlik açığını ortaya koymaktadır.",
                  "Uzmanlar dikkatli olunmasını tavsiye etmektedir.",
                  "Açık, altyapıları tehdit eden bir unsur olarak tanımlanmaktadır."):
            assert not has_casual_past(s), s

    def test_pluperfect_and_compound_ok(self):
        # -mıştı/-mişti (mişli birleşik) ve -maktaydı, -abilirdi kabul edilir
        for s in ("Veri 2018'de çalınmıştı.",
                  "Şirket daha önce açıklama yapmıştı.",
                  "Sistem o dönemde savunmasız durumdaydı ve izlenmekteydi.",
                  "Saldırgan koda erişebilirdi."):
            assert not has_casual_past(s), s

    def test_noun_possessive_not_flagged(self):
        # cümle ortasındaki isim+iyelik ("kaydı", "adı") yanlış-pozitif olmamalı
        assert not has_casual_past("Etkilenen sistemlerin kaydı tutulmaktadır.")
        assert not has_casual_past("Saldırganın adı henüz açıklanmamıştır.")

    def test_empty_and_none(self):
        assert not has_casual_past("")
        assert not has_casual_past(None)
        assert find_casual_past_words(None) == []
