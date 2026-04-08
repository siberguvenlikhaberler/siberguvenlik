"""
503 / Retry Logic Tests
_requests_get_with_retry fonksiyonunun geçici HTTP ve ağ hatalarını
doğru şekilde işlediğini doğrular.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from src.http_utils import requests_get_with_retry as _requests_get_with_retry


def _mock_response(status_code):
    """Verilen status_code ile mock bir requests.Response döndürür."""
    r = MagicMock()
    r.status_code = status_code
    return r


# ── Başarılı senaryolar ───────────────────────────────────────────────────────

class TestSuccessCases:

    @patch('src.http_utils.time.sleep')
    @patch('src.http_utils.requests.get')
    def test_success_on_first_attempt(self, mock_get, mock_sleep):
        """200 → tek denemede döner, sleep çağrılmaz."""
        mock_get.return_value = _mock_response(200)

        result = _requests_get_with_retry('https://example.com', {}, (5, 10))

        assert result.status_code == 200
        assert mock_get.call_count == 1
        mock_sleep.assert_not_called()

    @patch('src.http_utils.time.sleep')
    @patch('src.http_utils.requests.get')
    def test_non_retryable_status_returns_immediately(self, mock_get, mock_sleep):
        """404, 401, 500 gibi statüler retry yapılmaz, direkt döner."""
        for status in (400, 401, 403, 404, 500):
            mock_get.reset_mock()
            mock_sleep.reset_mock()
            mock_get.return_value = _mock_response(status)

            result = _requests_get_with_retry('https://example.com', {}, (5, 10))

            assert result.status_code == status
            assert mock_get.call_count == 1, f"HTTP {status} için retry olmamalı"
            mock_sleep.assert_not_called()


# ── HTTP hata retry senaryoları ───────────────────────────────────────────────

class TestHTTPRetry:

    @patch('src.http_utils.time.sleep')
    @patch('src.http_utils.requests.get')
    def test_503_retries_then_succeeds(self, mock_get, mock_sleep):
        """503 → 503 → 200 sıralamasında, 2 denemeden sonra başarılı olur."""
        mock_get.side_effect = [
            _mock_response(503),
            _mock_response(503),
            _mock_response(200),
        ]

        result = _requests_get_with_retry('https://example.com', {}, (5, 10),
                                          max_retries=3)

        assert result.status_code == 200
        assert mock_get.call_count == 3
        # İlk 503 → 1s, ikinci 503 → 2s
        assert mock_sleep.call_args_list == [call(1), call(2)]

    @patch('src.http_utils.time.sleep')
    @patch('src.http_utils.requests.get')
    def test_502_retries_then_succeeds(self, mock_get, mock_sleep):
        """502 de retry edilir."""
        mock_get.side_effect = [_mock_response(502), _mock_response(200)]

        result = _requests_get_with_retry('https://example.com', {}, (5, 10))

        assert result.status_code == 200
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once_with(1)

    @patch('src.http_utils.time.sleep')
    @patch('src.http_utils.requests.get')
    def test_504_retries_then_succeeds(self, mock_get, mock_sleep):
        """504 de retry edilir."""
        mock_get.side_effect = [_mock_response(504), _mock_response(200)]

        result = _requests_get_with_retry('https://example.com', {}, (5, 10))

        assert result.status_code == 200
        assert mock_get.call_count == 2

    @patch('src.http_utils.time.sleep')
    @patch('src.http_utils.requests.get')
    def test_429_retries_then_succeeds(self, mock_get, mock_sleep):
        """429 Too Many Requests de retry edilir."""
        mock_get.side_effect = [_mock_response(429), _mock_response(200)]

        result = _requests_get_with_retry('https://example.com', {}, (5, 10))

        assert result.status_code == 200
        assert mock_get.call_count == 2

    @patch('src.http_utils.time.sleep')
    @patch('src.http_utils.requests.get')
    def test_503_exhausted_returns_last_response(self, mock_get, mock_sleep):
        """Tüm retry'lar tükenirse son 503 yanıtı döner (exception atılmaz)."""
        mock_get.return_value = _mock_response(503)

        result = _requests_get_with_retry('https://example.com', {}, (5, 10),
                                          max_retries=2)

        assert result.status_code == 503
        assert mock_get.call_count == 3   # 0, 1, 2. denemeler
        # 2^0=1s, 2^1=2s — son denemeden sonra sleep yok
        assert mock_sleep.call_args_list == [call(1), call(2)]

    @patch('src.http_utils.time.sleep')
    @patch('src.http_utils.requests.get')
    def test_exponential_backoff_timing(self, mock_get, mock_sleep):
        """Backoff süreleri: 2^0=1s, 2^1=2s, 2^2=4s."""
        mock_get.return_value = _mock_response(503)

        _requests_get_with_retry('https://example.com', {}, (5, 10), max_retries=3)

        sleep_calls = [c.args[0] for c in mock_sleep.call_args_list]
        assert sleep_calls == [1, 2, 4]


# ── Ağ hatası retry senaryoları ───────────────────────────────────────────────

class TestNetworkErrorRetry:

    @patch('src.http_utils.time.sleep')
    @patch('src.http_utils.requests.get')
    def test_connection_error_retries_then_succeeds(self, mock_get, mock_sleep):
        """ConnectionError → başarılı: retry çalışır."""
        mock_get.side_effect = [
            requests.exceptions.ConnectionError("refused"),
            _mock_response(200),
        ]

        result = _requests_get_with_retry('https://example.com', {}, (5, 10))

        assert result.status_code == 200
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once_with(1)

    @patch('src.http_utils.time.sleep')
    @patch('src.http_utils.requests.get')
    def test_timeout_retries_then_succeeds(self, mock_get, mock_sleep):
        """Timeout → başarılı: retry çalışır."""
        mock_get.side_effect = [
            requests.exceptions.Timeout("timed out"),
            _mock_response(200),
        ]

        result = _requests_get_with_retry('https://example.com', {}, (5, 10))

        assert result.status_code == 200
        assert mock_get.call_count == 2

    @patch('src.http_utils.time.sleep')
    @patch('src.http_utils.requests.get')
    def test_chunked_encoding_error_retries(self, mock_get, mock_sleep):
        """ChunkedEncodingError → başarılı: retry çalışır."""
        mock_get.side_effect = [
            requests.exceptions.ChunkedEncodingError("chunked"),
            _mock_response(200),
        ]

        result = _requests_get_with_retry('https://example.com', {}, (5, 10))

        assert result.status_code == 200
        assert mock_get.call_count == 2

    @patch('src.http_utils.time.sleep')
    @patch('src.http_utils.requests.get')
    def test_connection_error_exhausted_raises(self, mock_get, mock_sleep):
        """Tüm retry'larda ConnectionError → exception fırlatılır."""
        mock_get.side_effect = requests.exceptions.ConnectionError("refused")

        with pytest.raises(requests.exceptions.ConnectionError):
            _requests_get_with_retry('https://example.com', {}, (5, 10),
                                     max_retries=2)

        assert mock_get.call_count == 3

    @patch('src.http_utils.time.sleep')
    @patch('src.http_utils.requests.get')
    def test_timeout_exhausted_raises(self, mock_get, mock_sleep):
        """Tüm retry'larda Timeout → exception fırlatılır."""
        mock_get.side_effect = requests.exceptions.Timeout("timed out")

        with pytest.raises(requests.exceptions.Timeout):
            _requests_get_with_retry('https://example.com', {}, (5, 10),
                                     max_retries=1)

        assert mock_get.call_count == 2


# ── kwargs iletme testleri ────────────────────────────────────────────────────

class TestKwargsPassthrough:

    @patch('src.http_utils.time.sleep')
    @patch('src.http_utils.requests.get')
    def test_params_passed_through(self, mock_get, mock_sleep):
        """params= argümanı requests.get'e iletilir."""
        mock_get.return_value = _mock_response(200)
        params = {'q': 'security', 'limit': 25}

        _requests_get_with_retry('https://example.com', {'User-Agent': 'bot'},
                                 (5, 10), params=params)

        mock_get.assert_called_once_with(
            'https://example.com',
            headers={'User-Agent': 'bot'},
            timeout=(5, 10),
            params=params,
        )

    @patch('src.http_utils.time.sleep')
    @patch('src.http_utils.requests.get')
    def test_stream_passed_through(self, mock_get, mock_sleep):
        """stream=True argümanı requests.get'e iletilir."""
        mock_get.return_value = _mock_response(200)

        _requests_get_with_retry('https://example.com', {}, (5, 10), stream=True)

        mock_get.assert_called_once_with(
            'https://example.com',
            headers={},
            timeout=(5, 10),
            stream=True,
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
