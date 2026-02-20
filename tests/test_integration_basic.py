"""
Basic Integration Test
Main.py'deki kritik fonksiyonların temel testi
"""
import pytest
import sys
from pathlib import Path

# main.py'nin bulunduğu dizini path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import _calculate_content_hash, _normalize_url_advanced


class TestURLNormalization:
    """URL normalizasyonu testleri"""

    def test_normalize_url_removes_utm_params(self):
        """UTM parametreleri kaldırılıyor mu?"""
        url = "https://example.com/article?utm_source=twitter&utm_medium=social"
        normalized = _normalize_url_advanced(url)
        assert "utm_" not in normalized
        assert "https://example.com/article" in normalized

    def test_normalize_url_removes_trailing_slash(self):
        """Trailing slash kaldırılıyor mu?"""
        url = "https://example.com/article/"
        normalized = _normalize_url_advanced(url)
        assert not normalized.endswith('/')

    def test_normalize_url_http_to_https(self):
        """HTTP -> HTTPS dönüşümü"""
        url = "http://example.com/article"
        normalized = _normalize_url_advanced(url)
        assert normalized.startswith("https://")

    def test_normalize_url_the_register_redirect(self):
        """The Register proxy URL'leri çöz"""
        url = "https://go.theregister.com/feed/www.theregister.com/article"
        normalized = _normalize_url_advanced(url)
        assert "go.theregister.com" not in normalized
        assert normalized.startswith("https://www.theregister.com")

    def test_normalize_url_google_feedburner(self):
        """Google FeedBurner redirect'lerini çöz"""
        url = "https://feedproxy.google.com/~r/somesite/~3/article-id/page"
        normalized = _normalize_url_advanced(url)
        assert "feedproxy.google.com" not in normalized


class TestContentHash:
    """Content hash hesaplama testleri"""

    def test_hash_consistency(self):
        """Aynı içerik aynı hash'i üretiyor mu?"""
        title = "Test Article Title"
        desc = "Test Description"
        hash1 = _calculate_content_hash(title, desc)
        hash2 = _calculate_content_hash(title, desc)
        assert hash1 == hash2

    def test_hash_different_content(self):
        """Farklı içerik farklı hash üretiyor mu?"""
        hash1 = _calculate_content_hash("Title 1", "Description 1")
        hash2 = _calculate_content_hash("Title 2", "Description 2")
        assert hash1 != hash2

    def test_hash_case_insensitive(self):
        """Hash case-insensitive mi?"""
        hash1 = _calculate_content_hash("Test Title", "Test Description")
        hash2 = _calculate_content_hash("TEST TITLE", "TEST DESCRIPTION")
        assert hash1 == hash2

    def test_hash_length(self):
        """Hash uzunluğu 16 karakter mi?"""
        hash_val = _calculate_content_hash("Title", "Description")
        assert len(hash_val) == 16


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
