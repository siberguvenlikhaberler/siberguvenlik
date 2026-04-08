"""
HTTP utility helpers — ağır bağımlılıklardan bağımsız olarak import edilebilir.
"""
import time
import requests


def requests_get_with_retry(url, headers, timeout, max_retries=3,
                            retry_statuses=(503, 502, 504, 429), **kwargs):
    """HTTP GET with exponential-backoff retry for transient HTTP and network errors.

    Retries on HTTP status codes : 503, 502, 504, 429 (configurable via retry_statuses).
    Also retries on network-level: ConnectionError, Timeout, ChunkedEncodingError.
    Backoff                       : 2^attempt seconds  (1 s → 2 s → 4 s for max_retries=3).

    Returns the last response object on HTTP error exhaustion.
    Re-raises the last network exception when all retries are exhausted.
    """
    _NETWORK_ERRORS = (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.ChunkedEncodingError,
    )
    for attempt in range(max_retries + 1):
        try:
            r = requests.get(url, headers=headers, timeout=timeout, **kwargs)
        except _NETWORK_ERRORS as exc:
            if attempt == max_retries:
                raise
            wait = 2 ** attempt
            print(f"      ⚠️  {type(exc).__name__} — {wait}s sonra tekrar deneniyor "
                  f"({attempt + 1}/{max_retries})...")
            time.sleep(wait)
            continue

        if r.status_code not in retry_statuses or attempt == max_retries:
            return r
        wait = 2 ** attempt
        print(f"      ⚠️  HTTP {r.status_code} — {wait}s sonra tekrar deneniyor "
              f"({attempt + 1}/{max_retries})...")
        time.sleep(wait)
    return r  # unreachable; satisfies linters
