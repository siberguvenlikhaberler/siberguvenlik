#!/usr/bin/env python3
"""
GENİŞLETİLMİŞ Siber Güvenlik Haberleri Toplayıcı
TAM METİN ÇEKİMİ ÖZELLIĞI EKLENMIŞ VERSIYON
"""

import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import json
import time
from typing import List, Dict, Optional
from xml.etree import ElementTree as ET


class ExtendedCyberNewsAggregator:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Tüm haber kaynakları ve RSS feed'leri (Çalışan kaynaklar - 10 adet)
        self.sources = {
            'The Hacker News': 'https://feeds.feedburner.com/TheHackersNews',
            'BleepingComputer': 'https://www.bleepingcomputer.com/feed/',
            'Krebs on Security': 'https://krebsonsecurity.com/feed/',
            'Threatpost': 'https://threatpost.com/feed/',
            'Security Affairs': 'https://securityaffairs.com/feed',
            'Graham Cluley': 'https://grahamcluley.com/feed/',
            'SANS ISC': 'https://isc.sans.edu/rssfeed.xml',
            'Recorded Future': 'https://www.recordedfuture.com/feed',
            'Cyberscoop': 'https://cyberscoop.com/feed/',
            'The Register': 'https://www.theregister.com/security/cyber_crime/headlines.atom',
        }
        
        # Hata veren kaynaklar (devre dışı bırakıldı):
        # 'SecurityWeek': 'https://www.securityweek.com/feed/' - RSS erişim hatası
        # 'Dark Reading': 'https://www.darkreading.com/rss_simple.asp' - Bağlantı hatası
        # 'Naked Security': 'https://nakedsecurity.sophos.com/feed/' - Feed erişim hatası  
        # 'US-CERT': 'https://www.cisa.gov/cybersecurity-advisories/all.xml' - API hatası
        
        # Site-spesifik content selector'ları
        self.content_selectors = {
            'The Hacker News': [
                {'class': 'articlebody'},
                {'class': 'article-content'},
                {'id': 'articlebody'}
            ],
            'BleepingComputer': [
                {'class': 'articleBody'},
                {'class': 'article_section'},
                {'id': 'article-content'}
            ],
            'SecurityWeek': [
                {'class': 'article-content'},
                {'id': 'node-article-content'}
            ],
            'Krebs on Security': [
                {'class': 'entry-content'},
                {'class': 'post-content'}
            ],
            'Dark Reading': [
                {'class': 'article-content'},
                {'itemprop': 'articleBody'}
            ],
            'Security Affairs': [
                {'class': 'entry-content'},
                {'class': 'post-content'}
            ],
            'Naked Security': [
                {'class': 'article__body'},
                {'class': 'entry-content'}
            ],
            'Graham Cluley': [
                {'class': 'entry-content'},
                {'class': 'post-content'}
            ],
            'The Register': [
                {'class': 'article_text_wrapper'},
                {'id': 'article'},
                {'class': 'body'}
            ]
        }
    
    def fetch_full_article(self, url: str, source_name: str) -> Dict[str, any]:
        """
        Web sayfasından haberin tam metnini çeker
        
        Returns:
            Dict with 'full_text', 'word_count', 'success' keys
        """
        try:
            print(f"      📄 Tam metin çekiliyor...", end='')
            
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Gereksiz elementleri kaldır
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
                element.decompose()
            
            full_text = ""
            
            # Site-spesifik selector'ları dene
            if source_name in self.content_selectors:
                for selector in self.content_selectors[source_name]:
                    content = soup.find('div', selector) or soup.find('article', selector)
                    if content:
                        full_text = self.extract_text_from_element(content)
                        if len(full_text) > 500:  # Yeterli içerik var
                            break
            
            # Genel selector'ları dene (fallback)
            if not full_text or len(full_text) < 500:
                general_selectors = [
                    soup.find('article'),
                    soup.find('div', class_='content'),
                    soup.find('div', class_='post-content'),
                    soup.find('div', class_='entry-content'),
                    soup.find('main'),
                    soup.find('div', id='content'),
                    soup.find('div', class_='article'),
                ]
                
                for element in general_selectors:
                    if element:
                        text = self.extract_text_from_element(element)
                        if len(text) > len(full_text):
                            full_text = text
            
            # Son çare: tüm <p> taglerini topla
            if not full_text or len(full_text) < 200:
                paragraphs = soup.find_all('p')
                full_text = '\n\n'.join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50])
            
            word_count = len(full_text.split())
            
            if word_count > 100:
                print(f" ✅ ({word_count} kelime)")
                return {
                    'full_text': full_text,
                    'word_count': word_count,
                    'success': True
                }
            else:
                print(f" ⚠️  (Yetersiz içerik: {word_count} kelime)")
                return {
                    'full_text': "",
                    'word_count': 0,
                    'success': False
                }
                
        except Exception as e:
            print(f" ❌ ({str(e)[:30]}...)")
            return {
                'full_text': "",
                'word_count': 0,
                'success': False
            }
    
    def extract_text_from_element(self, element) -> str:
        """HTML elementinden temiz metin çıkarır"""
        if not element:
            return ""
        
        # Tüm paragrafları bul
        paragraphs = element.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'])
        
        text_parts = []
        for p in paragraphs:
            text = p.get_text().strip()
            # Çok kısa veya gereksiz metinleri atla
            if len(text) > 20 and not any(skip in text.lower() for skip in ['cookie', 'subscribe', 'newsletter', 'advertisement']):
                text_parts.append(text)
        
        return '\n\n'.join(text_parts)
    
    def fetch_rss_feed(self, url: str, source_name: str) -> List[Dict]:
        """RSS feed'lerinden haberleri çeker"""
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
            print(f"  ⚠️  Hata ({source_name}): {str(e)[:50]}...")
            return []
    
    def clean_html(self, html_text: str) -> str:
        """HTML etiketlerini temizler"""
        if not html_text:
            return ""
        soup = BeautifulSoup(html_text, 'html.parser')
        return soup.get_text().strip()
    
    def aggregate_news(self) -> Dict[str, List[Dict]]:
        """Tüm kaynaklardan haberleri toplar ve tam metinleri çeker"""
        print("📰 Siber güvenlik haberleri toplanıyor...\n")
        print(f"🔍 Toplam {len(self.sources)} kaynak taranacak")
        print(f"📄 Her haberin TAM METNİ çekilecek (bu ~7-10 dakika sürebilir)\n")
        
        all_news = {}
        successful = 0
        failed = 0
        total_articles = 0
        total_full_texts = 0
        
        for idx, (source_name, rss_url) in enumerate(self.sources.items(), 1):
            print(f"\n[{idx}/{len(self.sources)}] 🔍 {source_name}")
            print(f"   └─ RSS kontrol ediliyor...")
            
            articles = self.fetch_rss_feed(rss_url, source_name)
            
            if articles:
                print(f"   └─ ✅ {len(articles)} haber bulundu")
                total_articles += len(articles)
                
                # Her haber için tam metni çek
                print(f"   └─ 📄 Tam metinler çekiliyor:")
                for i, article in enumerate(articles, 1):
                    if article['link']:
                        print(f"      [{i}/{len(articles)}]", end=' ')
                        
                        result = self.fetch_full_article(article['link'], source_name)
                        article['full_text'] = result['full_text']
                        article['word_count'] = result['word_count']
                        article['full_text_success'] = result['success']
                        
                        if result['success']:
                            total_full_texts += 1
                        
                        # Rate limiting - her istekten sonra bekle
                        time.sleep(2)
                
                all_news[source_name] = articles
                successful += 1
            else:
                print(f"   └─ ❌ Haber bulunamadı")
                failed += 1
            
            # Kaynaklar arası rate limiting
            if idx < len(self.sources):
                time.sleep(1)
        
        print(f"\n{'='*70}")
        print(f"📊 ÖZET:")
        print(f"   • Başarılı kaynak: {successful}/{len(self.sources)}")
        print(f"   • Toplam haber: {total_articles}")
        print(f"   • Tam metin başarılı: {total_full_texts}/{total_articles} ({int(total_full_texts/total_articles*100) if total_articles > 0 else 0}%)")
        print(f"{'='*70}\n")
        
        return all_news
    
    def generate_summary(self, news_data: Dict[str, List[Dict]]) -> str:
        """Haberlerin özetini oluşturur - TAM METİN DAHİL"""
        total_articles = sum(len(articles) for articles in news_data.values())
        total_words = sum(
            sum(article.get('word_count', 0) for article in articles)
            for articles in news_data.values()
        )
        
        summary = f"""
╔═══════════════════════════════════════════════════════════════════════════╗
║      SİBER GÜVENLİK HABERLERİ - TAM METİN VERSİYONU                      ║
║      Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}                                          ║
╚═══════════════════════════════════════════════════════════════════════════╝

📊 Toplam {total_articles} haber | {len(news_data)} kaynak | {total_words:,} kelime

"""
        
        for source, articles in news_data.items():
            source_words = sum(article.get('word_count', 0) for article in articles)
            summary += f"\n{'='*80}\n"
            summary += f"📰 {source} ({len(articles)} haber, {source_words:,} kelime)\n"
            summary += f"{'='*80}\n\n"
            
            for idx, article in enumerate(articles, 1):
                summary += f"{idx}. {article['title']}\n"
                summary += f"   🔗 {article['link']}\n"
                
                # RSS özeti
                description = self.clean_html(article.get('description', ''))
                if description:
                    description = description[:200] + '...' if len(description) > 200 else description
                    summary += f"   📝 RSS Özet: {description}\n"
                
                # Tam metin bilgisi
                if article.get('full_text_success'):
                    word_count = article.get('word_count', 0)
                    summary += f"   ✅ TAM METİN: {word_count} kelime\n"
                    
                    # İlk 500 karakteri göster
                    full_text = article.get('full_text', '')
                    preview = full_text[:500] + '...' if len(full_text) > 500 else full_text
                    summary += f"\n   📄 İÇERİK ÖNİZLEME:\n"
                    summary += f"   {'-'*76}\n"
                    for line in preview.split('\n'):
                        if line.strip():
                            summary += f"   {line[:74]}\n"
                    summary += f"   {'-'*76}\n"
                else:
                    summary += f"   ⚠️  Tam metin çekilemedi\n"
                
                if article.get('date'):
                    summary += f"   📅 {article['date']}\n"
                summary += "\n"
        
        return summary
    
    def generate_html_report(self, news_data: Dict[str, List[Dict]]) -> str:
        """Gelişmiş HTML rapor - TAM METİN DAHİL"""
        total_articles = sum(len(articles) for articles in news_data.values())
        total_words = sum(
            sum(article.get('word_count', 0) for article in articles)
            for articles in news_data.values()
        )
        
        html = f"""
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Siber Güvenlik Haberleri - TAM METİN - {datetime.now().strftime('%d.%m.%Y')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #2d3748;
            line-height: 1.6;
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
        }}
        
        .header h1 {{
            font-size: 42px;
            margin-bottom: 15px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        
        .header .subtitle {{
            font-size: 20px;
            opacity: 0.9;
        }}
        
        .badge {{
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 5px 15px;
            border-radius: 20px;
            margin: 5px;
            font-size: 14px;
        }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
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
            margin-bottom: 60px;
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
        
        .article {{
            background: #f7fafc;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            border-left: 5px solid #667eea;
            position: relative;
        }}
        
        .article-number {{
            position: absolute;
            top: 30px;
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
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .article-title {{
            font-size: 22px;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 15px;
            padding-left: 20px;
        }}
        
        .article-description {{
            color: #4a5568;
            margin: 15px 0;
            padding-left: 20px;
            padding: 15px 20px;
            background: white;
            border-radius: 8px;
            border-left: 3px solid #e2e8f0;
        }}
        
        .full-text-container {{
            margin: 20px 0;
            padding: 25px;
            background: white;
            border-radius: 8px;
            border-left: 4px solid #48bb78;
        }}
        
        .full-text-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
            font-weight: 600;
            color: #2d3748;
        }}
        
        .word-count {{
            background: #48bb78;
            color: white;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 12px;
        }}
        
        .full-text {{
            color: #2d3748;
            line-height: 1.8;
            white-space: pre-wrap;
            max-height: 600px;
            overflow-y: auto;
            padding: 15px;
            background: #f7fafc;
            border-radius: 8px;
        }}
        
        .full-text-toggle {{
            color: #667eea;
            cursor: pointer;
            margin-top: 10px;
            font-size: 14px;
            text-decoration: underline;
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
        
        .no-full-text {{
            padding: 15px 20px;
            background: #fff5f5;
            border-left: 4px solid #fc8181;
            border-radius: 8px;
            color: #c53030;
            margin: 15px 0;
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
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔒 Siber Güvenlik Haberleri</h1>
            <p class="subtitle">TAM METİN VERSİYONU</p>
            <div>
                <span class="badge">📰 {total_articles} Haber</span>
                <span class="badge">📝 {total_words:,} Kelime</span>
                <span class="badge">📅 {datetime.now().strftime('%d.%m.%Y')}</span>
            </div>
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
                <div class="stat-number">{total_words:,}</div>
                <div class="stat-label">Toplam Kelime</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{sum(1 for articles in news_data.values() for a in articles if a.get('full_text_success'))}</div>
                <div class="stat-label">Tam Metin</div>
            </div>
        </div>
        
        <div class="content">
"""
        
        for source, articles in news_data.items():
            source_initial = source[0].upper()
            source_words = sum(article.get('word_count', 0) for article in articles)
            
            html += f"""
            <div class="source-section">
                <div class="source-header">
                    <div class="source-icon">{source_initial}</div>
                    <div class="source-title">
                        <h2>{source}</h2>
                        <div class="source-count">{len(articles)} haber • {source_words:,} kelime</div>
                    </div>
                </div>
"""
            
            for idx, article in enumerate(articles, 1):
                title = article.get('title', 'Başlık Yok')
                description = self.clean_html(article.get('description', ''))
                url = article.get('link', '#')
                date_str = article.get('date', '')
                
                html += f"""
                <div class="article">
                    <div class="article-number">{idx}</div>
                    <h3 class="article-title">{title}</h3>
"""
                
                # RSS Özeti
                if description:
                    desc_preview = description[:300] + '...' if len(description) > 300 else description
                    html += f"""
                    <div class="article-description">
                        <strong>📝 RSS Özeti:</strong><br>
                        {desc_preview}
                    </div>
"""
                
                # Tam Metin
                if article.get('full_text_success'):
                    full_text = article.get('full_text', '')
                    word_count = article.get('word_count', 0)
                    
                    html += f"""
                    <div class="full-text-container">
                        <div class="full-text-header">
                            <span>✅ TAM METİN</span>
                            <span class="word-count">{word_count} kelime</span>
                        </div>
                        <div class="full-text">{full_text}</div>
                    </div>
"""
                else:
                    html += """
                    <div class="no-full-text">
                        ⚠️ Tam metin çekilemedi - Sadece RSS özeti mevcut
                    </div>
"""
                
                html += """
                    <div class="article-meta">
"""
                
                if date_str:
                    html += f"""
                        <div class="meta-item">
                            <span>📅</span>
                            <span>{date_str}</span>
                        </div>
"""
                
                html += f"""
                    </div>
                    <a href="{url}" target="_blank" class="article-link">
                        <span>🔗 Kaynağı Görüntüle</span>
                        <span>→</span>
                    </a>
                </div>
"""
            
            html += """
            </div>
"""
        
        html += f"""
        </div>
        
        <div class="footer">
            <p><strong>Bu rapor TAM METİN içermektedir</strong></p>
            <p>Oluşturulma: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>
            <p style="margin-top: 10px; font-size: 12px;">🔒 Siber Güvenlik Haberleri Toplayıcı - Full Text Version</p>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    def save_to_file(self, content: str, filename: str = None):
        """Özeti dosyaya kaydeder"""
        if filename is None:
            filename = f"cyber_news_FULLTEXT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Metin rapor kaydedildi: {filename}")
        return filename
    
    def save_to_json(self, news_data: Dict, filename: str = None):
        """Haberleri JSON formatında kaydeder"""
        if filename is None:
            filename = f"cyber_news_FULLTEXT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(news_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ JSON rapor kaydedildi: {filename}")
        return filename
    
    def save_html_report(self, news_data: Dict, filename: str = None):
        """HTML raporunu kaydeder"""
        if filename is None:
            filename = f"cyber_news_FULLTEXT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        html_content = self.generate_html_report(news_data)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ HTML rapor kaydedildi: {filename}")
        return filename


def main():
    """Ana fonksiyon"""
    print("="*70)
    print("🚀 SİBER GÜVENLİK HABERLERİ TOPLAYICI - TAM METİN VERSİYONU")
    print("="*70)
    print()
    print("⚠️  DİKKAT: Bu versiyon her haberin TAM METNİNİ çeker!")
    print("   • 10 kaynak × 3 haber = 30 tam metin")
    print("   • Tahmini süre: 7-10 dakika")
    print("   • İnternet bağlantısı gereklidir")
    print()
    print("="*70)
    print()
    
    aggregator = ExtendedCyberNewsAggregator()
    
    # Aktif kaynakları göster
    print("📋 Aktif Kaynaklar:")
    for idx, source_name in enumerate(aggregator.sources.keys(), 1):
        print(f"  {idx}. {source_name}")
    print()
    
    # Haberleri topla (TAM METİNLERLE)
    news_data = aggregator.aggregate_news()
    
    if not news_data:
        print("\n❌ Hiç haber bulunamadı!")
        return
    
    # Raporları oluştur
    print("\n📝 Raporlar oluşturuluyor...\n")
    
    summary = aggregator.generate_summary(news_data)
    print(summary)
    
    # Dosyalara kaydet
    aggregator.save_to_file(summary)
    aggregator.save_to_json(news_data)
    aggregator.save_html_report(news_data)
    
    print("\n" + "="*70)
    print("✨ İşlem tamamlandı!")
    print("="*70)


if __name__ == "__main__":
    main()
