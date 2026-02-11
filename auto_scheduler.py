#!/usr/bin/env python3
"""
Otomatik Zamanlanmış Siber Güvenlik Haberleri Toplayıcı
Her gün belirli saatte otomatik olarak haberleri toplar
"""

import schedule
import time
from datetime import datetime
import os
import sys

# Ana script'i import et
from cyber_news_genisletilmis import ExtendedCyberNewsAggregator


def scheduled_news_collection():
    """Zamanlanmış haber toplama işlevi"""
    print("\n" + "="*60)
    print(f"🕐 Zamanlanmış görev çalışıyor: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    try:
        aggregator = ExtendedCyberNewsAggregator()
        
        # Haberleri topla
        news_data = aggregator.aggregate_news()
        
        if news_data:
            # Rapor oluştur
            summary = aggregator.generate_summary(news_data)
            print(summary)
            
            # Dosyalara kaydet
            aggregator.save_to_file(summary)
            aggregator.save_to_json(news_data)
            aggregator.save_html_report(news_data)
            
            print("\n✅ Günlük rapor başarıyla oluşturuldu!")
        else:
            print("\n⚠️ Bugün haber bulunamadı.")
    
    except Exception as e:
        print(f"\n❌ Hata oluştu: {e}")


def main():
    """Zamanlayıcıyı başlat"""
    print("🤖 Otomatik Siber Güvenlik Haberleri Toplayıcı Başlatıldı")
    print("="*60)
    print("\n📋 Zamanlanmış görevler:")
    print("   • Her gün saat 09:00'da haber toplama")
    print("   • Her gün saat 18:00'de haber toplama")
    print("\n⌨️  Çıkmak için Ctrl+C tuşlayın\n")
    print("="*60 + "\n")
    
    # Zamanlamaları ayarla
    schedule.every().day.at("09:00").do(scheduled_news_collection)
    schedule.every().day.at("18:00").do(scheduled_news_collection)
    
    # İlk çalıştırmayı hemen yap
    print("🚀 İlk toplama işlemi başlatılıyor...\n")
    scheduled_news_collection()
    
    # Sonsuz döngüde zamanlamaları kontrol et
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Her dakika kontrol et
    except KeyboardInterrupt:
        print("\n\n👋 Program kapatılıyor...")
        sys.exit(0)


if __name__ == "__main__":
    main()
