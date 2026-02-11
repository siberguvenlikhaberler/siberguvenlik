FROM python:3.11-slim

# Çalışma dizini oluştur
WORKDIR /app

# Bağımlılıkları kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Proje dosyalarını kopyala
COPY cyber_news_genisletilmis.py .
COPY auto_scheduler.py .
COPY advanced_news_api.py .

# Çıktı klasörü oluştur
RUN mkdir -p /app/output

# Ana scripti çalıştır
CMD ["python", "cyber_news_genisletilmis.py"]
