# 🔒 Siber Güvenlik Haberleri Toplayıcı

Her gün otomatik olarak en son siber güvenlik haberlerini toplayan ve özetleyen Python aracı.

## 📋 Özellikler

- ✅ Birden fazla güvenilir siber güvenlik kaynağından haber toplama
- ✅ RSS feed desteği
- ✅ HTML, JSON ve TXT formatlarında rapor oluşturma
- ✅ Otomatik zamanlanmış çalıştırma
- ✅ Türkçe arayüz ve raporlar
- ✅ Temiz ve okunabilir çıktılar

## 📰 Haber Kaynakları

1. **The Hacker News** - En güncel siber güvenlik haberleri
2. **BleepingComputer** - Teknik detaylar ve analiz
3. **SecurityWeek** - Kurumsal güvenlik haberleri
4. **Krebs on Security** - Derinlemesine araştırmalar
5. **Dark Reading** - Güvenlik profesyonelleri için haberler
6. **Threatpost** - Tehdit istihbaratı
7. **Security Affairs** - Uluslararası güvenlik haberleri
8. **Naked Security** - Sophos güvenlik blogu
9. **Graham Cluley** - Uzman yorumları
10. **SANS ISC** - İnternet fırtına merkezi
11. **US-CERT** - ABD siber güvenlik uyarıları
12. **Recorded Future** - Tehdit istihbaratı
13. **Cyberscoop** - Politika ve teknoloji haberleri

## 🚀 Kurulum

### 1. Gereksinimler

- Python 3.7 veya üstü
- pip (Python paket yöneticisi)

### 2. Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

veya manuel olarak:

```bash
pip install requests beautifulsoup4 schedule lxml
```

## 💻 Kullanım

### Manuel Çalıştırma (Tek Seferlik)

```bash
python cyber_news_genisletilmis.py
```

Bu komut:
- 13 farklı güvenilir kaynaktan haberleri toplar
- Ekrana özet yazdırır
- 3 farklı formatta dosya oluşturur:
  - `cyber_news_extended_YYYYMMDD_HHMMSS.txt` - Metin özet
  - `cyber_news_extended_YYYYMMDD_HHMMSS.json` - JSON formatı
  - `cyber_news_extended_YYYYMMDD_HHMMSS.html` - HTML rapor (tarayıcıda açılabilir)

### Otomatik Zamanlanmış Çalıştırma

```bash
python auto_scheduler.py
```

Bu komut:
- Her gün saat **09:00** ve **18:00**'de otomatik çalışır
- Program açık kaldığı sürece çalışmaya devam eder
- Ctrl+C ile durdurabilirsiniz

## 🔧 Özelleştirme

### Zamanlamayı Değiştirme

`auto_scheduler.py` dosyasında:

```python
# Mevcut zamanlamalar
schedule.every().day.at("09:00").do(scheduled_news_collection)
schedule.every().day.at("18:00").do(scheduled_news_collection)

# Örnekler:
schedule.every().hour.do(scheduled_news_collection)  # Her saat
schedule.every(3).hours.do(scheduled_news_collection)  # Her 3 saatte
schedule.every().monday.at("10:00").do(scheduled_news_collection)  # Pazartesi 10:00
```

### Yeni Haber Kaynağı Ekleme

`cyber_news_genisletilmis.py` dosyasında `sources` dictionary'sine ekleyin:

```python
self.sources = {
    # Mevcut kaynaklar
    'The Hacker News': 'https://feeds.feedburner.com/TheHackersNews',
    'BleepingComputer': 'https://www.bleepingcomputer.com/feed/',
    # ... diğer kaynaklar
    
    # Yeni kaynak ekle
    'Yeni Kaynak Adı': 'https://yenisite.com/rss-feed-url',
}

## 🐧 Linux'ta Arka Planda Sürekli Çalıştırma

### Systemd Servisi Oluşturma

1. Servis dosyası oluşturun:

```bash
sudo nano /etc/systemd/system/cybernews.service
```

2. Aşağıdaki içeriği ekleyin:

```ini
[Unit]
Description=Siber Güvenlik Haberleri Toplayıcı
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/your/script
ExecStart=/usr/bin/python3 /path/to/your/script/auto_scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Servisi etkinleştirin:

```bash
sudo systemctl daemon-reload
sudo systemctl enable cybernews.service
sudo systemctl start cybernews.service
```

4. Durumu kontrol edin:

```bash
sudo systemctl status cybernews.service
```

### Crontab ile Zamanlanmış Görev (Alternatif)

```bash
crontab -e
```

Aşağıdaki satırı ekleyin (her gün saat 9:00 ve 18:00'de çalıştırır):

```
0 9,18 * * * /usr/bin/python3 /path/to/cyber_news_aggregator.py
```

## 📧 E-posta ile Rapor Gönderme (İleri Seviye)

E-posta gönderimi için script'e ekleyebileceğiniz kod:

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_report(self, html_content, recipient_email):
    """HTML raporunu e-posta ile gönderir"""
    sender_email = "your_email@gmail.com"
    password = "your_app_password"  # Gmail App Password kullanın
    
    message = MIMEMultipart("alternative")
    message["Subject"] = f"Siber Güvenlik Haberleri - {datetime.now().strftime('%d.%m.%Y')}"
    message["From"] = sender_email
    message["To"] = recipient_email
    
    html_part = MIMEText(html_content, "html")
    message.attach(html_part)
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, recipient_email, message.as_string())
    
    print(f"✅ E-posta gönderildi: {recipient_email}")
```

## 🐛 Sorun Giderme

### RSS Feed Hatası

- İnternet bağlantınızı kontrol edin
- Kaynak siteler erişilebilir durumda mı kontrol edin
- Firewall veya proxy ayarlarınızı kontrol edin

### Encoding Hatası

Dosya kaydetme sırasında encoding hatası alırsanız:

```python
# Windows için
with open(filename, 'w', encoding='utf-8-sig') as f:
```

### Rate Limiting

Çok fazla istek gönderiyorsanız, `time.sleep()` sürelerini artırın:

```python
time.sleep(2)  # 1 saniye yerine 2 saniye bekle
```

## 📊 Çıktı Örnekleri

### Konsol Çıktısı
```
📰 Siber Güvenlik Haberleri Toplanıyor...

🔍 The Hacker News kontrol ediliyor...
✅ 10 haber bulundu
🔍 BleepingComputer kontrol ediliyor...
✅ 10 haber bulundu
...
```

### HTML Rapor
Tarayıcıda açılabilen, modern ve şık bir rapor oluşturur.

### JSON Çıktısı
Diğer programlarla entegrasyon için yapılandırılmış veri.

## 🔐 Güvenlik Notları

- API anahtarlarını kod içine yazmayın, environment variables kullanın
- E-posta şifrelerini düz metin olarak saklamayın
- Script'i güvenilir kaynaklardan çalıştırın

## 📝 Lisans

Bu proje MIT lisansı altında açık kaynak olarak sunulmaktadır.

## 🤝 Katkıda Bulunma

Pull request'ler memnuniyetle karşılanır. Büyük değişiklikler için lütfen önce bir issue açın.

## 📞 İletişim

Sorularınız için GitHub Issues kullanabilirsiniz.

---

**Not:** Bu araç eğitim amaçlıdır. Haber sitelerinin kullanım şartlarına uygun olarak kullanın.
