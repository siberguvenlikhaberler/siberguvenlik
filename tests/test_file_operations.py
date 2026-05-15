"""
File Operations Tests
Dosya I/O, encoding, error handling testleri
"""
import pytest
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import HaberSistemi


class TestFileOperations:
    """Dosya işlemleri testleri"""

    def test_create_data_directory(self, tmp_path):
        """data/ klasörü oluşturuluyor mu?"""
        original_cwd = os.getcwd()
        os.chdir(str(tmp_path))
        try:
            sistema = HaberSistemi()
            articles = [{'link': 'https://example.com', 'title': 'Test', 'description': 'Test'}]
            sistema._save_used_links(articles)
            assert (tmp_path / "data").exists()
        finally:
            os.chdir(original_cwd)

    def test_save_and_load_consistency(self, tmp_path):
        """Kaydedilen veriler doğru şekilde yüklenebiliyor mu?"""
        links_file = tmp_path / "haberler_linkler.txt"

        sistem = HaberSistemi()
        sistem.used_links_file = str(links_file)

        # Veri kaydet
        articles = [
            {'link': 'https://example1.com', 'title': 'Article 1', 'description': 'Desc 1'},
            {'link': 'https://example2.com', 'title': 'Article 2', 'description': 'Desc 2'},
            {'link': 'https://example3.com', 'title': 'Article 3', 'description': 'Desc 3'},
        ]
        sistem._save_used_links(articles)

        # Veri yükle
        links, titles, hashes = sistem._load_used_links()

        # Kontrol et
        assert len(links) == 3
        assert len(titles) == 3
        assert len(hashes) == 3

    def test_utf8_encoding(self, tmp_path):
        """UTF-8 encoding doğru çalışıyor mu?"""
        links_file = tmp_path / "haberler_linkler.txt"

        sistem = HaberSistemi()
        sistem.used_links_file = str(links_file)

        # Türkçe karakterler
        articles = [
            {
                'link': 'https://example.com/türkçe',
                'title': 'Türkçe Başlık - Siber Güvenlik Haberi',
                'description': 'Açıklama: Kritik güvenlik açığı bulundu'
            }
        ]
        sistem._save_used_links(articles)

        # Yükle ve kontrol et
        links, titles, hashes = sistem._load_used_links()
        assert len(links) == 1
        assert 'Türkçe' in list(titles.values())[0]

    def test_malformed_lines_skipped(self, tmp_path):
        """Hatalı satırlar atlanıyor mu?"""
        today = datetime.now().strftime('%Y-%m-%d')
        links_file = tmp_path / "haberler_linkler.txt"
        content = (
            f"{today}\thttps://example.com/1\tTitle 1\thash1\n"
            "INVALID_LINE_WITHOUT_TABS\n"
            f"{today}\thttps://example.com/2\tTitle 2\thash2\n"
            "\n"
            f"{today}\thttps://example.com/3\tTitle 3\n"
        )
        links_file.write_text(content, encoding='utf-8')

        sistem = HaberSistemi()
        sistem.used_links_file = str(links_file)
        links, titles, hashes = sistem._load_used_links()

        # 3 geçerli satır okumalı
        assert len(links) >= 2  # En az 2 (3-sütunlu da sayılır)

    def test_empty_file_handling(self, tmp_path):
        """Boş dosya doğru handlelanıyor mu?"""
        links_file = tmp_path / "haberler_linkler.txt"
        links_file.write_text("", encoding='utf-8')

        sistem = HaberSistemi()
        sistem.used_links_file = str(links_file)
        links, titles, hashes = sistem._load_used_links()

        assert links == set()
        assert titles == {}
        assert hashes == set()

    def test_file_permission_error_handling(self, tmp_path):
        """Dosya permisyon hatası gracefully handle ediliyor mu?"""
        links_file = tmp_path / "haberler_linkler.txt"
        links_file.write_text("test", encoding='utf-8')

        sistem = HaberSistemi()
        sistem.used_links_file = str(links_file)

        # Dosya izinlerini kaldır (sadece read)
        os.chmod(str(links_file), 0o444)

        # Read işlemi başarılı olmalı
        links, titles, hashes = sistem._load_used_links()
        assert isinstance(links, set)

        # İzinleri geri yükle
        os.chmod(str(links_file), 0o644)


class TestDateHandling:
    """Tarih işlemleri testleri"""

    def test_old_articles_filtered_correctly(self, tmp_path):
        """7 günden eski makaleler filtreleniyor mu?"""
        links_file = tmp_path / "haberler_linkler.txt"

        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        six_days_ago = (datetime.now() - timedelta(days=6)).strftime('%Y-%m-%d')
        two_weeks_ago = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')

        links_file.write_text(
            f"{today}\thttps://example.com/today\tToday\thash1\n"
            f"{yesterday}\thttps://example.com/yesterday\tYesterday\thash2\n"
            f"{six_days_ago}\thttps://example.com/recent\tRecent\thash3\n"
            f"{two_weeks_ago}\thttps://example.com/old\tOld\thash4\n",
            encoding='utf-8'
        )

        sistem = HaberSistemi()
        sistem.used_links_file = str(links_file)
        links, titles, hashes = sistem._load_used_links()

        # 3 geçerli (bugün + dün + 6 gün önce); 14 gün öncesi filtrelendi
        assert len(links) == 3
        assert not any('old' in str(link).lower() for link in links)

    def test_same_day_multiple_entries(self, tmp_path):
        """Aynı gün içinde birden fazla entry olabilir mi?"""
        links_file = tmp_path / "haberler_linkler.txt"
        today = datetime.now().strftime('%Y-%m-%d')

        links_file.write_text(
            f"{today}\thttps://example.com/1\tTitle 1\thash1\n"
            f"{today}\thttps://example.com/2\tTitle 2\thash2\n"
            f"{today}\thttps://example.com/3\tTitle 3\thash3\n",
            encoding='utf-8'
        )

        sistem = HaberSistemi()
        sistem.used_links_file = str(links_file)
        links, titles, hashes = sistem._load_used_links()

        assert len(links) == 3


class TestErrorRecovery:
    """Hata kurtarma testleri"""

    def test_corrupted_hash_fallback(self, tmp_path):
        """Bozuk hash'le de çalışıyor mu?"""
        today = datetime.now().strftime('%Y-%m-%d')
        links_file = tmp_path / "haberler_linkler.txt"
        links_file.write_text(
            f"{today}\thttps://example.com/1\tTitle 1\tinvalidhash\n"  # Kısa hash
            f"{today}\thttps://example.com/2\tTitle 2\t1234567890abcdef\n",  # Geçerli
            encoding='utf-8'
        )

        sistem = HaberSistemi()
        sistem.used_links_file = str(links_file)
        links, titles, hashes = sistem._load_used_links()

        # Her ikisi de yüklenmeli
        assert len(links) == 2

    def test_missing_required_fields(self, tmp_path):
        """Eksik alanlarla nasıl davranılıyor?"""
        links_file = tmp_path / "haberler_linkler.txt"
        links_file.write_text(
            "2026-02-20\t\tEmpty Link\thash1\n"  # Boş link
            "\thttps://example.com/2\tNo Date\thash2\n"  # Boş date
            "2026-02-20\thttps://example.com/3\t\thash3\n",  # Boş title
            encoding='utf-8'
        )

        sistem = HaberSistemi()
        sistem.used_links_file = str(links_file)

        # Hata vermeden çalışmalı
        try:
            links, titles, hashes = sistem._load_used_links()
            # En azından geçerli olanları yükledi
            assert isinstance(links, set)
        except Exception as e:
            pytest.fail(f"Exception raised: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
