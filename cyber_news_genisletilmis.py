#!/usr/bin/env python3
"""
GENÄ°ÅžLETÄ°LMÄ°Åž Siber GÃ¼venlik Haberleri ToplayÄ±cÄ±
Daha fazla kaynak ile gÃ¼ncellenmiÅŸ versiyon
"""

import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import json
import time
from typing import List, Dict
from xml.etree import ElementTree as ET


class ExtendedCyberNewsAggregator:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # TÃ¼m haber kaynaklarÄ± ve RSS feed'leri
        self.sources = {
            # Mevcut kaynaklar
            'The Hacker News': 'https://feeds.feedburner.com/TheHackersNews',
            'BleepingComputer': 'https://www.bleepingcomputer.com/feed/',
            'SecurityWeek': 'https://www.securityweek.com/feed/',                 
            'Krebs on Security': 'https://krebsonsecurity.com/feed/',
            'Dark Reading': 'https://www.darkreading.com/rss_simple.asp',
            'Threatpost': 'https://threatpost.com/feed/',
            'Security Affairs': 'https://securityaffairs.com/feed',
            'Naked Security': 'https://nakedsecurity.sophos.com/feed/',
            'Graham Cluley': 'https://grahamcluley.com/feed/',
            'SANS ISC': 'https://isc.sans.edu/rssfeed.xml',
            'US-CERT': 'https://www.cisa.gov/cybersecurity-advisories/all.xml',
            'Recorded Future': 'https://www.recordedfuture.com/feed',
           'Cyberscoop': 'https://cyberscoop.com/feed/',
        }
    
    def fetch_rss_feed(self, url: str, source_name: str) -> List[Dict]:
        """RSS feed'lerinden haberleri Ã§eker"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            
            articles = []
            
            # Atom feed mi RSS feed mi kontrol et
            if root.tag.endswith('feed'):  # Atom feed
                for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry')[:3]:
                    title_elem = entry.find('{http://www.w3.org/2005/Atom}title')
                    link_elem = entry.find('{http://www.w3.org/2005/Atom}link')
                    summary_elem = entry.find('{http://www.w3.org/2005/Atom}summary')
                    published_elem = entry.find('{http://www.w3.org/2005/Atom}published')
                    
                    if title_elem is not None:
                        articles.append({
                            'title': title_elem.text,
                            'link': link_elem.get('href') if link_elem is not None else '',
                            'description': summary_elem.text if summary_elem is not None else '',
                            'date': published_elem.text if published_elem is not None else '',
                            'source': source_name
                        })
            else:  # RSS feed
                for item in root.findall('.//item')[:3]:
                    title = item.find('title')
                    link = item.find('link')
                    description = item.find('description')
                    pub_date = item.find('pubDate')
                    
                    if title is not None:
                        articles.append({
                            'title': title.text,
                            'link': link.text if link is not None else '',
                            'description': description.text if description is not None else '',
                            'date': pub_date.text if pub_date is not None else '',
                            'source': source_name
                        })
            
            return articles
            
        except Exception as e:
            print(f"  âš ï¸  Hata ({source_name}): {str(e)[:50]}...")
            return []
    
    def clean_html(self, html_text: str) -> str:
        """HTML etiketlerini temizler"""
        if not html_text:
            return ""
        soup = BeautifulSoup(html_text, 'html.parser')
        return soup.get_text().strip()
    
    def aggregate_news(self) -> Dict[str, List[Dict]]:
        """TÃ¼m kaynaklardan haberleri toplar"""
        print("ðŸ“° Siber gÃ¼venlik haberleri toplanÄ±yor...\n")
        print(f"ðŸ” Toplam {len(self.sources)} kaynak taranacak\n")
        
        all_news = {}
        successful = 0
        failed = 0
        
        for idx, (source_name, rss_url) in enumerate(self.sources.items(), 1):
            print(f"[{idx}/{len(self.sources)}] ðŸ” {source_name} kontrol ediliyor...")
            
            articles = self.fetch_rss_feed(rss_url, source_name)
            
            if articles:
                all_news[source_name] = articles
                print(f"  âœ… {len(articles)} haber bulundu")
                successful += 1
            else:
                print(f"  âŒ Haber bulunamadÄ±")
                failed += 1
            
            # Rate limiting - sunuculara aÅŸÄ±rÄ± yÃ¼k bindirmeyelim
            if idx < len(self.sources):
                time.sleep(1)
        
        print(f"\n{'='*60}")
        print(f"ðŸ“Š Ã–zet: {successful} kaynak baÅŸarÄ±lÄ±, {failed} kaynak baÅŸarÄ±sÄ±z")
        print(f"{'='*60}\n")
        
        return all_news
    
    def generate_summary(self, news_data: Dict[str, List[Dict]]) -> str:
        """Haberlerin Ã¶zetini oluÅŸturur"""
        total_articles = sum(len(articles) for articles in news_data.values())
        
        summary = f"""
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘      SÄ°BER GÃœVENLÄ°K HABERLERÄ° - GENÄ°ÅžLETÄ°LMÄ°Åž Ã–ZET       â•‘
â•‘      Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}                      â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

ðŸ“Š Toplam {total_articles} haber | {len(news_data)} kaynak

"""
        
        for source, articles in news_data.items():
            summary += f"\n{'='*60}\n"
            summary += f"ðŸ“° {source} ({len(articles)} haber)\n"
            summary += f"{'='*60}\n\n"
            
            for idx, article in enumerate(articles, 1):
                summary += f"{idx}. {article['title']}\n"
                
                description = self.clean_html(article.get('description', ''))
                if description:
                    description = description[:200] + '...' if len(description) > 200 else description
                    summary += f"   ðŸ“ {description}\n"
                
                summary += f"   ðŸ”— {article['link']}\n"
                if article.get('date'):
                    summary += f"   ðŸ“… {article['date']}\n"
                summary += "\n"
        
        return summary
    
    def generate_html_report(self, news_data: Dict[str, List[Dict]]) -> str:
        """GeliÅŸmiÅŸ HTML rapor"""
        total_articles = sum(len(articles) for articles in news_data.values())
        
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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #2d3748;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 50px 40px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}
        
        .header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="20" cy="20" r="2" fill="rgba(255,255,255,0.1)"/><circle cx="80" cy="80" r="2" fill="rgba(255,255,255,0.1)"/><circle cx="50" cy="50" r="2" fill="rgba(255,255,255,0.1)"/></svg>');
            opacity: 0.3;
        }}
        
        .header h1 {{
            font-size: 42px;
            margin-bottom: 15px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            position: relative;
            z-index: 1;
        }}
        
        .header .subtitle {{
            font-size: 20px;
            opacity: 0.9;
            position: relative;
            z-index: 1;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 30px 40px;
            background: #f7fafc;
            border-bottom: 2px solid #e2e8f0;
        }}
        
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.07);
            text-align: center;
        }}
        
        .stat-number {{
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}
        
        .stat-label {{
            color: #718096;
            font-size: 14px;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .source-section {{
            margin-bottom: 50px;
        }}
        
        .source-header {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 3px solid #667eea;
        }}
        
        .source-icon {{
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
            font-weight: bold;
        }}
        
        .source-title {{
            flex: 1;
        }}
        
        .source-title h2 {{
            color: #2d3748;
            font-size: 28px;
            margin-bottom: 5px;
        }}
        
        .source-count {{
            color: #718096;
            font-size: 14px;
        }}
        
        .articles-grid {{
            display: grid;
            gap: 20px;
        }}
        
        .article {{
            background: #f7fafc;
            border-radius: 12px;
            padding: 25px;
            border-left: 5px solid #667eea;
            transition: all 0.3s ease;
            position: relative;
        }}
        
        .article:hover {{
            transform: translateX(5px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.15);
        }}
        
        .article-number {{
            position: absolute;
            top: 25px;
            left: -15px;
            width: 30px;
            height: 30px;
            background: #667eea;
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 14px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .article-title {{
            font-size: 20px;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 15px;
            line-height: 1.5;
            padding-left: 20px;
        }}
        
        .article-description {{
            color: #4a5568;
            line-height: 1.8;
            margin-bottom: 15px;
            padding-left: 20px;
        }}
        
        .article-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            padding-left: 20px;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #e2e8f0;
        }}
        
        .meta-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
            color: #718096;
        }}
        
        .article-link {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            text-decoration: none;
            margin-top: 15px;
            margin-left: 20px;
            font-weight: 500;
            transition: all 0.3s ease;
        }}
        
        .article-link:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 15px rgba(102, 126, 234, 0.3);
        }}
        
        .footer {{
            background: #f7fafc;
            padding: 30px 40px;
            text-align: center;
            color: #718096;
            border-top: 2px solid #e2e8f0;
        }}
        
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 32px; }}
            .content {{ padding: 20px; }}
            .article {{ padding: 20px; }}
            .source-header {{ flex-direction: column; text-align: center; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>ðŸ”’ Siber GÃ¼venlik Haberleri</h1>
            <p class="subtitle">GÃ¼ncel Tehditler ve GeliÅŸmeler</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{total_articles}</div>
                <div class="stat-label">Toplam Haber</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(news_data)}</div>
                <div class="stat-label">Kaynak</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{datetime.now().strftime('%d.%m.%Y')}</div>
                <div class="stat-label">Tarih</div>
            </div>
        </div>
        
        <div class="content">
"""
        
        for source, articles in news_data.items():
            source_initial = source[0].upper()
            
            html += f"""
            <div class="source-section">
                <div class="source-header">
                    <div class="source-icon">{source_initial}</div>
                    <div class="source-title">
                        <h2>{source}</h2>
                        <div class="source-count">{len(articles)} haber bulundu</div>
                    </div>
                </div>
                
                <div class="articles-grid">
"""
            
            for idx, article in enumerate(articles, 1):
                title = article.get('title', 'BaÅŸlÄ±k Yok')
                description = self.clean_html(article.get('description', ''))
                if description:
                    description = description[:300] + '...' if len(description) > 300 else description
                
                url = article.get('link', '#')
                date_str = article.get('date', '')
                
                html += f"""
                    <div class="article">
                        <div class="article-number">{idx}</div>
                        <h3 class="article-title">{title}</h3>
"""
                
                if description:
                    html += f"""
                        <p class="article-description">{description}</p>
"""
                
                html += """
                        <div class="article-meta">
"""
                
                if date_str:
                    html += f"""
                            <div class="meta-item">
                                <span>ðŸ“…</span>
                                <span>{date_str}</span>
                            </div>
"""
                
                html += f"""
                        </div>
                        <a href="{url}" target="_blank" class="article-link">
                            <span>ðŸ“– Haberi Oku</span>
                            <span>â†’</span>
                        </a>
                    </div>
"""
            
            html += """
                </div>
            </div>
"""
        
        html += f"""
        </div>
        
        <div class="footer">
            <p>Bu rapor otomatik olarak {datetime.now().strftime('%d.%m.%Y %H:%M')} tarihinde oluÅŸturulmuÅŸtur.</p>
            <p style="margin-top: 10px; font-size: 12px;">ðŸ”’ Siber GÃ¼venlik Haberleri ToplayÄ±cÄ±</p>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def save_to_file(self, content: str, filename: str = None):
        """Ã–zeti dosyaya kaydeder"""
        if filename is None:
            filename = f"cyber_news_extended_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"âœ… Metin rapor kaydedildi: {filename}")
        return filename
    
    def save_to_json(self, news_data: Dict, filename: str = None):
        """Haberleri JSON formatÄ±nda kaydeder"""
        if filename is None:
            filename = f"cyber_news_extended_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(news_data, f, ensure_ascii=False, indent=2)
        
        print(f"âœ… JSON rapor kaydedildi: {filename}")
        return filename
    
    def save_html_report(self, news_data: Dict, filename: str = None):
        """HTML raporunu kaydeder"""
        if filename is None:
            filename = f"cyber_news_extended_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        html_content = self.generate_html_report(news_data)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"âœ… HTML rapor kaydedildi: {filename}")
        return filename


def main():
    """Ana fonksiyon"""
    print("="*60)
    print("ðŸš€ GENÄ°ÅžLETÄ°LMÄ°Åž Siber GÃ¼venlik Haberleri ToplayÄ±cÄ±")
    print("="*60)
    print()
    
    aggregator = ExtendedCyberNewsAggregator()
    
    # Aktif kaynaklarÄ± gÃ¶ster
    print("ðŸ“‹ Aktif Kaynaklar:")
    for idx, source_name in enumerate(aggregator.sources.keys(), 1):
        print(f"  {idx}. {source_name}")
    print()
    
    # Haberleri topla
    news_data = aggregator.aggregate_news()
    
    if not news_data:
        print("\nâŒ HiÃ§ haber bulunamadÄ±!")
        return
    
    # RaporlarÄ± oluÅŸtur
    print("\nðŸ“ Raporlar oluÅŸturuluyor...\n")
    
    summary = aggregator.generate_summary(news_data)
    print(summary)
    
    # Dosyalara kaydet
    aggregator.save_to_file(summary)
    aggregator.save_to_json(news_data)
    aggregator.save_html_report(news_data)
    
    print("\n" + "="*60)
    print("âœ¨ Ä°ÅŸlem tamamlandÄ±!")
    print("="*60)


if __name__ == "__main__":
    main()
