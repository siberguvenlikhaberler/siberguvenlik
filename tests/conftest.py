"""
Test Configuration & Fixtures
pytest için global fixtures ve konfigürasyonlar
"""
import pytest
import os
import json
from pathlib import Path

# Test dosyaları için base directory
TEST_DIR = Path(__file__).parent
FIXTURES_DIR = TEST_DIR / 'fixtures'

@pytest.fixture
def sample_articles():
    """Mock haber verisi"""
    return [
        {
            'source': 'The Hacker News',
            'title': 'Critical Microsoft Exchange Vulnerability',
            'link': 'https://www.example.com/article1',
            'description': 'A critical vulnerability in Microsoft Exchange',
            'date': '2026-02-20T10:00:00Z',
            'full_text': 'Full article text here...',
            'word_count': 200,
            'domain': 'example.com',
            'success': True
        },
        {
            'source': 'Krebs on Security',
            'title': 'LockBit Ransomware Campaign',
            'link': 'https://www.example2.com/article2',
            'description': 'Lockbit targets healthcare',
            'date': '2026-02-20T09:00:00Z',
            'full_text': 'Ransomware content...',
            'word_count': 250,
            'domain': 'example2.com',
            'success': True
        }
    ]

@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API yanıtı"""
    return """
    <!DOCTYPE html>
    <html>
    <body>
        <div class="important-news">
            <h2>Önemli Gelişmeler</h2>
            <div class="important-item">
                <a href="#haber-1">1. Microsoft Exchange kritik açığı</a>
            </div>
        </div>
        <div class="news-section">
            <div class="news-item" id="haber-1">
                <div class="news-title"><b>Microsoft Exchange Kritik Açığı</b></div>
                <p class="news-content">Microsoft has disclosed a critical vulnerability...</p>
                <p class="source">(Kaynak, AÇIK - <a href="https://example.com">example.com</a>, 20.02.2026)</p>
            </div>
        </div>
    </body>
    </html>
    """

@pytest.fixture
def fixture_links_file(tmp_path):
    """Geçici test linker dosyası"""
    links_file = tmp_path / 'haberler_linkler.txt'
    content = """2026-02-19	https://www.example.com/old-article	Old Article	hash123456789abcd
2026-02-20	https://www.example.com/new-article	New Article	hash987654321dcba
"""
    links_file.write_text(content, encoding='utf-8')
    return links_file

@pytest.fixture
def fixture_archive_file(tmp_path):
    """Geçici test arşiv dosyası"""
    archive_file = tmp_path / 'haberler_arsiv.txt'
    content = """
================================================================================
📅 20 ŞUBAT 2026 - EN ÖNEMLİ 43 HABER (SEÇİLMİŞ)
================================================================================

[1] Microsoft Exchange Kritik Açığı
───────────────────────────────────────────────────────────────────────────────
Microsoft sunucularında kritik güvenlik açığı keşfedilmiştir...

"""
    archive_file.write_text(content, encoding='utf-8')
    return archive_file
