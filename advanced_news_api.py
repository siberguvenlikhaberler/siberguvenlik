#!/usr/bin/env python3
"""
GeliÅŸmiÅŸ Siber GÃ¼venlik Haberleri ToplayÄ±cÄ±
NewsAPI ve diÄŸer API'ler ile entegrasyon
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict
import os


class AdvancedCyberNewsAggregator:
    """
    NewsAPI kullanarak siber gÃ¼venlik haberlerini toplayan geliÅŸmiÅŸ versiyon
    
    KullanÄ±m:
    1. https://newsapi.org adresinden Ã¼cretsiz API key alÄ±n
    2. API_KEY deÄŸiÅŸkenini ayarlayÄ±n veya environment variable kullanÄ±n
    """
    
    def __init__(self, api_key: str = None):
        # NewsAPI key - https://newsapi.org'dan Ã¼cretsiz alabilirsiniz
        self.api_key = api_key or os.getenv('NEWSAPI_KEY', 'YOUR_API_KEY_HERE')
        self.base_url = 'https://newsapi.org/v2/everything'
        
        # Siber gÃ¼venlik anahtar kelimeleri
        self.keywords = [
            'cybersecurity',
            'data breach',
            'ransomware',
            'malware',
            'phishing',
            'zero-day',
            'vulnerability',
            'cyber attack',
            'hacking',
            'InfoSec'
        ]
    
    def fetch_news_from_api(self, days: int = 1) -> List[Dict]:
        """NewsAPI'den haberleri Ã§eker"""
        
        if self.api_key == 'YOUR_API_KEY_HERE':
            print("âš ï¸  UYARI: NewsAPI key ayarlanmamÄ±ÅŸ!")
            print("ðŸ“ https://newsapi.org adresinden Ã¼cretsiz key alabilirsiniz")
            return []
        
        # Tarih aralÄ±ÄŸÄ±
        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        all_articles = []
        
        for keyword in self.keywords[:3]:  # Ä°lk 3 keyword (API limiti iÃ§in)
            try:
                params = {
                    'q': keyword,
                    'from': from_date,
                    'sortBy': 'publishedAt',
                    'language': 'en',
                    'apiKey': self.api_key,
                    'pageSize': 10
                }
                
                response = requests.get(self.base_url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                if data['status'] == 'ok':
                    articles = data.get('articles', [])
                    all_articles.extend(articles)
                    print(f"âœ… '{keyword}' iÃ§in {len(articles)} haber bulundu")
                
            except Exception as e:
                print(f"âŒ '{keyword}' iÃ§in hata: {e}")
        
        # Tekrar edenleri temizle (aynÄ± URL)
        seen_urls = set()
        unique_articles = []
        
        for article in all_articles:
            url = article.get('url')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)
        
        return unique_articles[:20]  # En fazla 20 haber
    
    def generate_report(self, articles: List[Dict]) -> str:
        """Haberleri formatlar ve rapor oluÅŸturur"""
        
        report = f"""
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘      SÄ°BER GÃœVENLÄ°K HABERLERÄ° - API VERSIYONU            â•‘
â•‘      Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}                      â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

ðŸ“Š Toplam {len(articles)} benzersiz haber bulundu
"""
        
        for idx, article in enumerate(articles, 1):
            report += f"\n{'='*60}\n"
            report += f"{idx}. {article.get('title', 'BaÅŸlÄ±k Yok')}\n\n"
            
            if article.get('description'):
                report += f"ðŸ“ {article['description']}\n\n"
            
            if article.get('source', {}).get('name'):
                report += f"ðŸ“° Kaynak: {article['source']['name']}\n"
            
            if article.get('author'):
                report += f"âœï¸  Yazar: {article['author']}\n"
            
            if article.get('publishedAt'):
                pub_date = datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00'))
                report += f"ðŸ“… Tarih: {pub_date.strftime('%d.%m.%Y %H:%M')}\n"
            
            if article.get('url'):
                report += f"ðŸ”— Link: {article['url']}\n"
        
        return report
    
    def generate_html_report(self, articles: List[Dict]) -> str:
        """HTML formatÄ±nda rapor oluÅŸturur"""
        
        html = f"""
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Siber GÃ¼venlik Haberleri - {datetime.now().strftime('%d.%m.%Y')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 36px;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        .stats {{
            background: rgba(255,255,255,0.2);
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
            font-size: 18px;
        }}
        .content {{
            padding: 40px;
        }}
        .article {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 25px;
            border-left: 5px solid #667eea;
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        .article:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .article-number {{
            display: inline-block;
            background: #667eea;
            color: white;
            width: 35px;
            height: 35px;
            border-radius: 50%;
            text-align: center;
            line-height: 35px;
            font-weight: bold;
            margin-right: 10px;
        }}
        .article-title {{
            font-size: 22px;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 15px;
            line-height: 1.4;
        }}
        .article-description {{
            color: #4a5568;
            line-height: 1.7;
            margin-bottom: 15px;
        }}
        .article-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            font-size: 14px;
            color: #718096;
            margin-top: 15px;
        }}
        .meta-item {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        .article-link {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            text-decoration: none;
            margin-top: 15px;
            transition: background 0.3s;
        }}
        .article-link:hover {{
            background: #5a67d8;
        }}
        .source-badge {{
            background: #764ba2;
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: 600;
        }}
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 28px; }}
            .content {{ padding: 20px; }}
            .article {{ padding: 15px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ðŸ”’ Siber GÃ¼venlik Haberleri</h1>
            <p style="font-size: 18px; margin-top: 10px;">GÃ¼ncel Tehditler ve GeliÅŸmeler</p>
            <div class="stats">
                ðŸ“… {datetime.now().strftime('%d %B %Y, %H:%M')} | ðŸ“Š {len(articles)} Haber
            </div>
        </div>
        
        <div class="content">
"""
        
        for idx, article in enumerate(articles, 1):
            source_name = article.get('source', {}).get('name', 'Bilinmeyen Kaynak')
            title = article.get('title', 'BaÅŸlÄ±k Yok')
            description = article.get('description', '')
            author = article.get('author', '')
            url = article.get('url', '#')
            
            pub_date = ''
            if article.get('publishedAt'):
                try:
                    pub_date_obj = datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00'))
                    pub_date = pub_date_obj.strftime('%d.%m.%Y %H:%M')
                except:
                    pub_date = article['publishedAt']
            
            html += f"""
            <div class="article">
                <div class="article-title">
                    <span class="article-number">{idx}</span>
                    {title}
                </div>
"""
            
            if description:
                html += f"""
                <div class="article-description">
                    {description}
                </div>
"""
            
            html += """
                <div class="article-meta">
"""
            
            if source_name:
                html += f"""
                    <div class="meta-item">
                        <span class="source-badge">{source_name}</span>
                    </div>
"""
            
            if author:
                html += f"""
                    <div class="meta-item">
                        âœï¸ {author}
                    </div>
"""
            
            if pub_date:
                html += f"""
                    <div class="meta-item">
                        ðŸ“… {pub_date}
                    </div>
"""
            
            html += f"""
                </div>
                <a href="{url}" target="_blank" class="article-link">
                    ðŸ“– Haberi Oku â†’
                </a>
            </div>
"""
        
        html += """
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def run(self):
        """Ana Ã§alÄ±ÅŸtÄ±rma fonksiyonu"""
        print("ðŸš€ GeliÅŸmiÅŸ Siber GÃ¼venlik Haberleri ToplayÄ±cÄ±\n")
        print("ðŸ“¡ NewsAPI'den haberler Ã§ekiliyor...\n")
        
        articles = self.fetch_news_from_api(days=2)
        
        if not articles:
            print("\nâŒ Haber bulunamadÄ±!")
            return
        
        print(f"\nâœ… Toplam {len(articles)} benzersiz haber bulundu\n")
        
        # RaporlarÄ± oluÅŸtur
        text_report = self.generate_report(articles)
        print(text_report)
        
        # Dosyalara kaydet
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # TXT
        txt_filename = f"cyber_news_api_{timestamp}.txt"
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(text_report)
        print(f"\nâœ… Metin rapor kaydedildi: {txt_filename}")
        
        # HTML
        html_report = self.generate_html_report(articles)
        html_filename = f"cyber_news_api_{timestamp}.html"
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html_report)
        print(f"âœ… HTML rapor kaydedildi: {html_filename}")


def main():
    """Ana fonksiyon"""
    
    # API Key'i buraya yazÄ±n veya environment variable kullanÄ±n
    # Ãœcretsiz key iÃ§in: https://newsapi.org
    
    api_key = os.getenv('NEWSAPI_KEY')  # veya direkt "your_api_key_here"
    
    aggregator = AdvancedCyberNewsAggregator(api_key=api_key)
    aggregator.run()


if __name__ == "__main__":
    main()
