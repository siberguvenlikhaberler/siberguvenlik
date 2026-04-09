"""
Siber Güvenlik Haberleri - Günlük Rapor Sistemi
v2.2 - Gemini 2.5 Flash + HTML Doğrulama + Eksik Paragraf Tamamlama
"""

import os
import re
import time
import hashlib
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from google import genai
from google.genai import types as genai_types
from openai import OpenAI as OpenAIClient

from src.config import (
    GEMINI_API_KEY, OPENROUTER_API_KEY, NEWS_SOURCES, HEADERS, CONTENT_SELECTORS,
    ARCHIVE_FILE, get_claude_prompt,
    SOCIAL_SIGNAL_CONFIG, SKIP_URL_PATTERNS
)
from src.http_utils import requests_get_with_retry as _requests_get_with_retry


# ===== YARDIMCI FONKSİYONLAR =====

def _calculate_content_hash(title, description):
    """Title + description'dan MD5 hash hesapla (16 karakter hex)"""
    content = f"{title or ''}{description or ''}".lower().strip()
    return hashlib.md5(content.encode('utf-8')).hexdigest()  # tam 32 karakter


def _normalize_url_advanced(link):
    """
    Gelişmiş URL normalizasyonu:
    - UTM parametrelerini kaldırma
    - Protocol standardizasyonu (http→https)
    - Query parametreleri sorting
    - The Register proxy URL'lerini çözme
    - Google FeedBurner redirect'lerini çözme
    - Trailing slash normalizasyonu
    """
    if not link:
        return ''

    try:
        # The Register proxy URL fix
        if 'go.theregister.com' in link:
            parsed = urlparse(link)
            qs = parse_qs(parsed.query)
            if 'td' in qs:
                link = qs['td'][0]

        # FeedBurner redirect fix
        if 'feedproxy.google.com' in link or 'feeds.feedburner.com' in link:
            try:
                r = requests.head(link, allow_redirects=True, timeout=5)
                if r.url and r.url != link:
                    link = r.url
            except:
                pass

        parsed = urlparse(link)

        # Protocol → https
        scheme = 'https'
        netloc = parsed.netloc.lower().replace('www.', '')
        path = parsed.path

        # UTM ve tracking parametrelerini kaldır
        utm_params = {'utm_source', 'utm_medium', 'utm_campaign', 'utm_term',
                      'utm_content', 'ref', 'source', 'mc_cid', 'mc_eid'}
        qs = parse_qs(parsed.query, keep_blank_values=False)
        filtered_qs = {k: v for k, v in qs.items() if k.lower() not in utm_params}

        # Query parametrelerini sıralı birleştir
        query_string = urlencode(sorted(filtered_qs.items()), doseq=True)

        # Yeniden oluştur
        normalized = urlunparse((scheme, netloc, path, '', query_string, ''))

        # Trailing slash kaldır
        normalized = normalized.rstrip('/')

        return normalized
    except:
        # Parse hatası durumunda orijinalini döndür
        return link.rstrip('/')



def _parse_article_date(date_str, fallback):
    """RSS tarihini DD.MM.YYYY formatına çevirir (TR UTC+3), parse edilemezse bugünün tarihini kullanır"""
    from datetime import timezone, timedelta as td
    TR = timezone(td(hours=3))
    if not date_str:
        return fallback.strftime('%d.%m.%Y')
    date_str = date_str.strip()
    # Timezone-aware formatlar: UTC→TR dönüşümü yap
    for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S.%f%z']:
        try:
            return datetime.strptime(date_str, fmt).astimezone(TR).strftime('%d.%m.%Y')
        except:
            pass
    # Z sonekini +00:00 ile değiştirip tekrar dene
    if date_str.endswith('Z'):
        try:
            return datetime.strptime(date_str[:-1], '%Y-%m-%dT%H:%M:%S.%f').replace(
                tzinfo=timezone.utc).astimezone(TR).strftime('%d.%m.%Y')
        except:
            pass
        try:
            return datetime.strptime(date_str[:-1], '%Y-%m-%dT%H:%M:%S').replace(
                tzinfo=timezone.utc).astimezone(TR).strftime('%d.%m.%Y')
        except:
            pass
    # Timezone-naive formatlar: olduğu gibi al
    for fmt in ['%a, %d %b %Y %H:%M:%S %Z', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d']:
        try:
            return datetime.strptime(date_str, fmt).strftime('%d.%m.%Y')
        except:
            pass
    return fallback.strftime('%d.%m.%Y')




def fetch_social_signals(config):
    """
    Reddit (unauthenticated public API), Hacker News, GitHub Advisories ve
    HN, GitHub Advisories (max 2), Mastodon (infosec.exchange) kaynaklarından sinyal çeker.
    Reddit via Tavily ayrı havuzda top 3 seçilir, sona eklenir.
    Toplam: max 8 sinyal (5 ana + 3 Reddit).
    """
    hours_back     = config.get('hours_back', 24)
    cutoff_ts      = int((datetime.now() - timedelta(hours=hours_back)).timestamp())
    yesterday      = (datetime.now() - timedelta(hours=hours_back)).strftime('%Y-%m-%d')
    results        = []   # HN + Mastodon + GitHub (max 2) → ana havuz
    reddit_results = []   # Reddit via PullPush → ayrı havuz

    print("\n" + "=" * 70)
    print("📡 SOSYAL MEDYA SİNYALLERİ ÇEKILIYOR")
    print("=" * 70)

    # ── Mastodon (infosec.exchange) ───────────────────────────────────────────
    # Açık API, kimlik doğrulama gerektirmez. Hashtag timeline endpoint kullanılır.
    # Engagement skoru: favourites_count + reblogs_count * 2 + replies_count
    mastodon_cfg      = config.get('mastodon', {})
    mastodon_instance = mastodon_cfg.get('instance', 'infosec.exchange')
    mastodon_tags     = mastodon_cfg.get('hashtags', ['cybersecurity', 'infosec', 'vulnerability'])
    mastodon_limit    = mastodon_cfg.get('limit', 20)
    mastodon_min_eng  = mastodon_cfg.get('min_score', 2)
    mastodon_top_n    = mastodon_cfg.get('top_n', 3)
    mastodon_hours    = mastodon_cfg.get('hours_back', 48)
    mastodon_cutoff   = int((datetime.now() - timedelta(hours=mastodon_hours)).timestamp())
    mastodon_pool     = []
    seen_mastodon_ids = set()
    mastodon_fallback_instances = mastodon_cfg.get(
        'fallback_instances', ['mastodon.social', 'fosstodon.org'])
    instances_to_try = [mastodon_instance] + [
        i for i in mastodon_fallback_instances if i != mastodon_instance]

    for tag in mastodon_tags:
        tag_fetched = False
        for instance in instances_to_try:
            try:
                url = (f'https://{instance}/api/v1/timelines/tag/{tag}'
                       f'?limit={mastodon_limit}')
                r = _requests_get_with_retry(url, headers=HEADERS, timeout=(5, 15))
                if r.status_code == 422:
                    print(f"   Mastodon #{tag} ({instance}): HTTP 422, RSS feed deneniyor...")
                    # API auth gerektiriyor → RSS feed fallback (/tags/{tag}.rss kimlik doğrulama istemez)
                    try:
                        import email.utils as _eu
                        rss_url = f'https://{instance}/tags/{tag}.rss'
                        rr = _requests_get_with_retry(rss_url, headers=HEADERS, timeout=(5, 15))
                        if rr.status_code == 200:
                            root = ET.fromstring(rr.content)
                            items = root.findall('.//item')
                            rss_added = 0
                            for item in items:
                                pub_date_str = item.findtext('pubDate', '')
                                try:
                                    ts = _eu.mktime_tz(_eu.parsedate_tz(pub_date_str))
                                    if ts and ts < mastodon_cutoff:
                                        continue
                                except Exception:
                                    pass
                                link = item.findtext('link', '#')
                                if link in seen_mastodon_ids:
                                    continue
                                seen_mastodon_ids.add(link)
                                desc_html = item.findtext('description', '')
                                raw_text = BeautifulSoup(desc_html, 'html.parser').get_text(' ', strip=True)
                                raw_text = re.sub(r'https?://\S+', '', raw_text).strip()
                                raw_text = re.sub(r'#\w+', '', raw_text).strip()
                                raw_text = ' '.join(raw_text.split())
                                if len(raw_text) < 30:
                                    continue
                                if any(kw in raw_text.lower() for kw in (
                                        'autopsie', 'dossier', 'pour les', 'avec ', 'dans ',
                                        'selon ', 'mais ', 'sont ', 'cette ', 'über ', 'wurde ')):
                                    continue
                                mastodon_pool.append({
                                    'platform':   'mastodon',
                                    'source':     'Mastodon',
                                    'title':      raw_text[:200],
                                    'link':       link,
                                    'score':      1,
                                    'comments':   0,
                                    'favourites': 0,
                                    'reblogs':    0,
                                })
                                rss_added += 1
                            print(f"   Mastodon #{tag} ({instance}): RSS ile {rss_added} post eklendi")
                            tag_fetched = True
                            time.sleep(0.5)
                            break
                        else:
                            print(f"   Mastodon #{tag} ({instance}): RSS HTTP {rr.status_code}")
                    except Exception as rss_e:
                        print(f"   Mastodon #{tag} ({instance}): RSS hatası: {rss_e}")
                    time.sleep(0.5)
                    continue
                if r.status_code != 200:
                    print(f"   Mastodon #{tag} ({instance}): HTTP {r.status_code}")
                    time.sleep(0.5)
                    continue
                for s in r.json():
                    sid = s.get('id', '')
                    if sid in seen_mastodon_ids:
                        continue
                    seen_mastodon_ids.add(sid)
                    try:
                        cdt = datetime.fromisoformat(
                            s.get('created_at', '').replace('Z', '+00:00'))
                        if cdt.timestamp() < mastodon_cutoff:
                            continue
                    except Exception:
                        pass
                    favs    = s.get('favourites_count', 0)
                    reblogs = s.get('reblogs_count', 0)
                    replies = s.get('replies_count', 0)
                    eng     = favs + reblogs * 2 + replies
                    if eng < mastodon_min_eng:
                        continue
                    # HTML içerikten düz metin çıkar
                    raw_text = BeautifulSoup(s.get('content', ''), 'html.parser')\
                                   .get_text(' ', strip=True)
                    raw_text = re.sub(r'https?://\S+', '', raw_text).strip()
                    raw_text = ' '.join(raw_text.split())
                    if len(raw_text) < 30:
                        continue
                    # Dil filtresi: sadece İngilizce ağırlıklı postlar
                    # Fransızca/diğer dil belirteci kelimeleri içeriyorsa atla
                    _lang_skip = ('autopsie', 'dossier', 'pour les', 'avec ',
                                  'dans ', 'selon ', 'mais ', 'sont ', 'cette ',
                                  'une vulnérabilité', 'les hackers', ' les ',
                                  'über ', 'wurde ', 'einer ', 'diesem ')
                    if any(kw in raw_text.lower() for kw in _lang_skip):
                        continue
                    # Kalite filtresi: konferans duyurusu / günlük digest / sadece hashtag postları atla
                    _low_quality = ('new event added', 'daily digest', 'your daily dose',
                                    'conference', 'meetup', '📅', '📌 ', '🗓',
                                    'read more:', 'stories you should not miss')
                    if any(kw in raw_text.lower() for kw in _low_quality):
                        continue
                    # Hashtag temizleme: #tag # tag # tag → temiz metin
                    raw_text = re.sub(r'#\w+', '', raw_text).strip()
                    raw_text = ' '.join(raw_text.split())
                    if len(raw_text) < 20:
                        continue
                    mastodon_pool.append({
                        'platform':   'mastodon',
                        'source':     'Mastodon',
                        'title':      raw_text[:200],
                        'link':       s.get('url', '#'),
                        'score':      eng,
                        'comments':   replies,
                        'favourites': favs,
                        'reblogs':    reblogs,
                    })
                print(f"   Mastodon #{tag} ({instance}): {mastodon_limit} post tarandı")
                tag_fetched = True
                time.sleep(0.5)
                break
            except Exception as e:
                print(f"   Mastodon #{tag} ({instance}) hatasi: {e}")
        if not tag_fetched:
            print(f"   Mastodon #{tag}: Tüm instancelar başarısız")

    mastodon_pool.sort(key=lambda x: x['score'], reverse=True)
    results.extend(mastodon_pool[:mastodon_top_n])
    print(f"   Mastodon toplam: {len(mastodon_pool)} nitelikli → "
          f"en iyi {min(mastodon_top_n, len(mastodon_pool))} eklendi")

    # ── Hacker News (Algolia API) ────────────────────────────────────────────
    # Skor modeli: combined_score = points + (num_comments × comment_weight)
    # search endpoint: relevance + popularity ağırlıklı (search_by_date'den
    # daha güvenilir çünkü points filtresi bazı saatlerde 0 sonuç dönderebilir)
    hn_cfg         = config.get('hackernews', {})
    min_points     = hn_cfg.get('min_points', 15)
    hn_limit       = hn_cfg.get('limit', 25)
    comment_weight = hn_cfg.get('comment_weight', 3)
    try:
        # params dict kullanılarak URL encode sorunu giderildi (>= raw string sorun yapıyor)
        # points filtresi URL'den kaldırıldı → Python'da uygulanıyor (daha güvenilir)
        hn_params = {
            'query':          'security cybersecurity vulnerability malware breach',
            'tags':           'story',
            'numericFilters': f'created_at_i>{cutoff_ts}',
            'hitsPerPage':    hn_limit,
        }
        r = _requests_get_with_retry("https://hn.algolia.com/api/v1/search_by_date",
                                     headers=HEADERS, timeout=(5, 10),
                                     params=hn_params)
        if r.status_code == 200:
            hits  = r.json().get('hits', [])
            found = 0
            for hit in hits:
                points   = int(hit.get('points', 0) or 0)
                if points < min_points:
                    continue
                comments = int(hit.get('num_comments', 0) or 0)
                combined = points + comments * comment_weight
                item_url = hit.get('url') or \
                           f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                domain = urlparse(item_url).netloc or 'news.ycombinator.com'
                results.append({
                    'platform': 'hackernews',
                    'source':   'HackerNews',
                    'title':    hit.get('title', ''),
                    'link':     item_url,
                    'score':    combined,
                    'comments': comments,
                    'date':     hit.get('created_at', ''),
                    'domain':   domain,
                    'full_text': '',
                    'success':  True,
                })
                found += 1
            print(f"   HackerNews: {found} nitelikli hikaye")
        else:
            print(f"   HackerNews: HTTP {r.status_code}")
    except Exception as e:
        print(f"   HackerNews hatasi: {e}")

    # ── GitHub Security Advisories ───────────────────────────────────────────
    # En güncel incelenmiş advisory'leri çeker; severity'ye göre önceliklendirir.
    # top_n=2 ile ana havuzda GitHub'un ağırlığı sınırlandırılır.
    severity_rank = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
    gh_cfg        = config.get('github_advisories', {})
    min_severity  = gh_cfg.get('min_severity', ['critical', 'high', 'medium'])
    gh_limit      = gh_cfg.get('limit', 10)
    gh_top_n      = gh_cfg.get('top_n', 2)
    try:
        gh_url  = f"https://api.github.com/advisories?type=reviewed&per_page={gh_limit}"
        gh_hdrs = {
            'Accept':              'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent':          'siberguvenlik-bot/1.0',
        }
        r = _requests_get_with_retry(gh_url, headers=gh_hdrs, timeout=(5, 15))
        if r.status_code == 200:
            advisories = r.json()
            gh_pool = []
            for adv in advisories:
                sev = (adv.get('severity') or 'unknown').lower()
                if sev not in min_severity:
                    continue
                cvss_obj   = adv.get('cvss') or {}
                cvss_score = float(cvss_obj.get('score') or 0) if isinstance(cvss_obj, dict) else 0.0
                rank       = severity_rank.get(sev, 0)
                sort_score = rank * 10 + cvss_score  # nihai sıralama için karma puan
                gh_pool.append({
                    'platform':  'github_advisories',
                    'source':    'GitHub Advisory',
                    'title':     adv.get('summary') or adv.get('ghsa_id', ''),
                    'link':      adv.get('html_url') or
                                 f"https://github.com/advisories/{adv.get('ghsa_id', '')}",
                    'score':     sort_score,
                    'comments':  0,
                    'severity':  sev,
                    'cvss':      cvss_score,
                    'date':      adv.get('published_at', ''),
                    'domain':    'github.com',
                    'full_text': (adv.get('description') or '')[:300],
                    'success':   True,
                })
            gh_pool.sort(key=lambda x: x['score'], reverse=True)
            results.extend(gh_pool[:gh_top_n])
            print(f"   GitHub Advisories: {len(gh_pool)} nitelikli → "
                  f"en iyi {min(gh_top_n, len(gh_pool))} eklendi")
        else:
            print(f"   GitHub Advisories: HTTP {r.status_code}")
    except Exception as e:
        print(f"   GitHub Advisories hatasi: {e}")

    # ── Reddit (PullPush API — Pushshift halefi) ────────────────────────────
    # PullPush: ücretsiz, API key gerektirmez, Azure IP bloğu yok.
    # Tam post içeriği + yorum derinliği mevcut.
    # Kendi havuzunda tutulur (main_results sıralamasını etkilemez).
    reddit_cfg      = config.get('reddit', {})
    reddit_subs     = reddit_cfg.get('subreddits', ['cybersecurity', 'netsec'])
    reddit_query    = reddit_cfg.get('query',
                        'cybersecurity vulnerability exploit malware breach')
    reddit_size     = reddit_cfg.get('size', 25)
    reddit_min_ups  = reddit_cfg.get('min_upvotes', 3)
    reddit_top_n    = reddit_cfg.get('top_n', 3)
    reddit_hours    = reddit_cfg.get('hours_back', 48)
    fetch_comments  = reddit_cfg.get('fetch_comments', True)
    max_comments    = reddit_cfg.get('max_comments', 5)
    # ── Reddit (Resmi RSS — Hot Feed) ──────────────────────────────────────────
    # PullPush arşivi ~10 ay geride kaldığı için kullanılamaz hale geldi.
    # Reddit'in /r/{sub}/hot.rss endpoint'i API key gerektirmez ve güncel veri döndürür.
    # JSON endpoint Azure/GH Actions'tan 403 alıyor; RSS daha geniş erişime sahip.
    _ATOM = 'http://www.w3.org/2005/Atom'
    # Düşük kalite post filtresi (kariyer/moderasyon/haftalık thread vb.)
    _REDDIT_SKIP = ('mentorship monday', 'career thread', 'hiring thread',
                    'monthly discussion', 'weekly thread', 'question thread',
                    'what are you working', 'show hn', '[hiring]', '[who is hiring]',
                    'who wants to be hired', 'megathread', 'ama:')
    rss_cutoff_dt = datetime.now() - timedelta(hours=reddit_hours)

    try:
        rss_pool = []
        seen_rss_links = set()
        for sub in reddit_subs:
            rss_url = f'https://www.reddit.com/r/{sub}/hot.rss?limit={reddit_size}'
            r = _requests_get_with_retry(rss_url, headers=HEADERS, timeout=(5, 15))
            if r.status_code != 200:
                print(f"   Reddit RSS r/{sub}: HTTP {r.status_code}")
                time.sleep(0.5)
                continue
            root = ET.fromstring(r.content)
            sub_found = 0
            for entry in root.findall(f'{{{_ATOM}}}entry'):
                # Başlık
                title_el = entry.find(f'{{{_ATOM}}}title')
                title = (title_el.text or '').strip() if title_el is not None else ''
                if not title:
                    continue
                # Düşük kalite filtresi
                if any(kw in title.lower() for kw in _REDDIT_SKIP):
                    continue
                # Link
                link_el = entry.find(f'{{{_ATOM}}}link')
                url = link_el.get('href', '') if link_el is not None else ''
                if not url or url in seen_rss_links:
                    continue
                # Tarih filtresi
                updated_el = entry.find(f'{{{_ATOM}}}updated')
                if updated_el is not None and updated_el.text:
                    try:
                        post_dt = datetime.fromisoformat(
                            updated_el.text.replace('Z', '+00:00')).replace(tzinfo=None)
                        if post_dt < rss_cutoff_dt:
                            continue
                    except Exception:
                        pass   # Tarih parse edilemezse geç
                seen_rss_links.add(url)
                # RSS'te upvote bilgisi yok; sıra indeksini ters puan olarak kullan
                # (hot feed zaten engagement'a göre sıralı)
                rss_pool.append({
                    'platform':     'reddit',
                    'source':       f'Reddit: r/{sub}',
                    'title':        title,
                    'link':         url,
                    'score':        reddit_size - sub_found,   # pozisyon puanı
                    'comments':     0,
                    'full_text':    '',
                    'top_comments': [],
                    'subreddit':    sub,
                })
                sub_found += 1
            print(f"   Reddit RSS r/{sub}: {sub_found} nitelikli post")
            time.sleep(0.5)
        reddit_results.extend(rss_pool)
        top_reddit = rss_pool[:reddit_top_n]
        print(f"   Reddit (RSS): toplam {len(rss_pool)} post → "
              f"en iyi {len(top_reddit)} eklendi")
    except Exception as e:
        top_reddit = []
        print(f"   Reddit RSS hatası: {e}")

    # HN + Mastodon + GitHub (max 1): karma puana göre top 7
    results.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_main = results[:7]

    # Reddit sonuçları her zaman sona eklenir (ayrı havuz)
    final = top_main + top_reddit

    print(f"\n   Sosyal sinyal toplami: {len(final)} icerik "
          f"({len(top_main)} ana + {len(top_reddit)} Reddit)")
    return final


# ===== ANA SİSTEM =====

class HaberSistemi:
    def __init__(self):
        self.headers = HEADERS
        self.sources = NEWS_SOURCES
        self.selectors = CONTENT_SELECTORS
        self.rss_errors = []
        self.used_links_file = "data/haberler_linkler.txt"
        self.rss_errors_file = "data/rss_errors.txt"
        self.social_data = []  # fetch_social_signals() sonuçları; topla() tarafından doldurulur

    def fetch_full_article(self, url, source_name):
        """Tam metin çeker — max 10 saniye, sonra geç"""
        import threading
        result = {'full_text': "", 'word_count': 0, 'success': False, 'domain': ''}
        _session_holder = [None]  # thread'den response'a erişim için

        def _fetch():
            try:
                r = _requests_get_with_retry(url, headers=self.headers, timeout=(5, 8), stream=True)
                _session_holder[0] = r
                chunks = []
                total_size = 0
                for chunk in r.iter_content(chunk_size=8192):
                    chunks.append(chunk)
                    total_size += len(chunk)
                    if total_size > 500_000:
                        break
                r.close()
                raw = b''.join(chunks).decode(r.encoding or 'utf-8', errors='replace')
                soup = BeautifulSoup(raw, 'html.parser')
                domain = urlparse(url).netloc.replace('www.', '')
                text = ""
                if source_name in self.selectors:
                    for sel in self.selectors[source_name]:
                        el = soup.find(**sel)
                        if el:
                            text = self._extract(el)
                            break
                if not text:
                    for tag in ['article', 'main']:
                        el = soup.find(tag)
                        if el:
                            text = self._extract(el)
                            if text:
                                break
                if not text:
                    el = soup.find('div', class_=lambda c: c and any(
                        x in str(c).lower() for x in ['content', 'article', 'body', 'post']))
                    if el:
                        text = self._extract(el)
                wc = len(text.split()) if text else 0
                text = text.replace('\t', ' ').replace('\r', '')
                if wc > 100:
                    result.update({'full_text': text, 'word_count': wc, 'success': True, 'domain': domain})
                else:
                    result['domain'] = domain
            except Exception:
                pass

        print(f"      📄 Tam metin...", end='', flush=True)
        t = threading.Thread(target=_fetch, daemon=True)
        t.start()
        t.join(timeout=10)
        if t.is_alive():
            # Timeout: bağlantıyı zorla kapat ki thread bloklanmasın
            try:
                if _session_holder[0] is not None:
                    _session_holder[0].close()
            except Exception:
                pass
            print(f" ⏱️  (timeout)")
        elif result['success']:
            print(f" ✅ ({result['word_count']})")
        else:
            print(f" ⚠️  (0)")
        return result

    def _extract(self, element):
        """Temiz metin"""
        if not element:
            return ""
        parts = []
        for p in element.find_all(['p', 'h1', 'h2', 'h3', 'li']):
            t = p.get_text().strip()
            if len(t) > 20 and not any(x in t.lower() for x in ['cookie', 'subscribe', 'newsletter']):
                parts.append(t)
        return '\n\n'.join(parts)

    def _crawl_newsletter_links(self, newsletter_urls, source_name):
        """
        Newsletter/digest sayfasındaki iç makale linklerini çıkarır ve
        her birinin tam metnini çeker.

        Yalnızca source domain'ine ait, sayısal ID içeren makale URL'leri
        alınır (kategori/etiket/ana sayfa linkleri atlanır).
        Deduplication sonraki aşamada (_filter_duplicates) yapılır.
        """
        import re as _re
        crawled_articles = []
        seen_hrefs = set()

        for nl_entry in newsletter_urls:
            # (url, pub_date) tuple veya plain string (geriye dönük uyumluluk)
            if isinstance(nl_entry, tuple):
                nl_url, nl_pub_date = nl_entry
            else:
                nl_url, nl_pub_date = nl_entry, ''

            try:
                print(f"   └─ 📰 Newsletter çekiliyor: {nl_url[:70]}...")
                r = _requests_get_with_retry(nl_url, headers=self.headers, timeout=(5, 15))
                if r.status_code != 200:
                    print(f"      ⚠️  HTTP {r.status_code}")
                    continue
                soup = BeautifulSoup(r.content, 'html.parser')
                nl_domain = urlparse(nl_url).netloc.replace('www.', '')

                # Makale içerik alanını bul (entry-content veya article)
                content_el = None
                for sel in [{'class': 'entry-content'}, {'class': 'post-content'},
                            {'class': 'article-content'}]:
                    content_el = soup.find('div', **sel) or soup.find('article')
                    if content_el:
                        break
                if not content_el:
                    content_el = soup  # tüm sayfa fallback

                found = 0
                for a in content_el.find_all('a', href=True):
                    href = a.get('href', '').strip()
                    if not href or href.startswith('#'):
                        continue
                    # Sadece aynı domain'e ait linkler
                    parsed = urlparse(href)
                    link_domain = parsed.netloc.replace('www.', '')
                    if link_domain and link_domain != nl_domain:
                        continue
                    # Tam URL'ye dönüştür
                    if not parsed.scheme:
                        href = f"https://{nl_domain}{href}"
                    # Sayısal ID içeren makale URL'si mi? (/12345/ gibi)
                    if not _re.search(r'/\d{4,}/', href):
                        continue
                    # Newsletter URL'si değil
                    if any(pat in href.lower() for pat in SKIP_URL_PATTERNS):
                        continue
                    norm = _normalize_url_advanced(href)
                    if norm in seen_hrefs:
                        continue
                    seen_hrefs.add(norm)

                    title = a.get_text(strip=True)
                    if not title or len(title) < 15:
                        continue

                    crawled_articles.append({
                        'title':       title,
                        'link':        href,
                        'description': '',
                        'date':        nl_pub_date,  # newsletter'ın yayın tarihi
                        'source':      source_name,
                    })
                    found += 1

                print(f"      ✅ {found} makale linki bulundu")
                time.sleep(1)

            except Exception as e:
                print(f"      ❌ Newsletter crawl hatası: {e}")

        if not crawled_articles:
            return []

        # Her makale için tam metin çek
        print(f"   └─ 📄 Newsletter makaleleri ({len(crawled_articles)}) tam metin çekiliyor:")
        result = []
        for i, art in enumerate(crawled_articles, 1):
            print(f"      [{i}/{len(crawled_articles)}]", end=' ', flush=True)
            res = self.fetch_full_article(art['link'], source_name)
            art.update(res)
            if res['success']:
                result.append(art)
            time.sleep(2)
        print(f"   └─ ✅ {len(result)}/{len(crawled_articles)} newsletter makalesi tam metin çekildi")
        return result

    def fetch_rss(self, url, source_name):
        """RSS çeker — max 15 saniye timeout korumalı"""
        import threading
        result_holder = {'articles': [], 'error': None}

        def _fetch_rss():
            try:
                r = _requests_get_with_retry(url, headers=self.headers, timeout=(5, 12))
                if r.status_code != 200:
                    result_holder['error'] = Exception(f"HTTP {r.status_code}")
                    return
                root = ET.fromstring(r.content)

                if root.tag.endswith('feed'):  # Atom
                    for entry in root.findall('.//{http://www.w3.org/2005/Atom}entry')[:10]:
                        t = entry.find('{http://www.w3.org/2005/Atom}title')
                        l = entry.find('{http://www.w3.org/2005/Atom}link')
                        s = entry.find('{http://www.w3.org/2005/Atom}summary')
                        d = entry.find('{http://www.w3.org/2005/Atom}published')
                        if t is not None:
                            result_holder['articles'].append({
                                'title': t.text,
                                'link': l.get('href') if l is not None else '',
                                'description': s.text if s is not None else '',
                                'date': d.text if d is not None else '',
                                'source': source_name
                            })
                else:  # RSS
                    for item in root.findall('.//item')[:10]:
                        t = item.find('title')
                        l = item.find('link')
                        d = item.find('description')
                        p = item.find('pubDate')
                        if t is not None:
                            result_holder['articles'].append({
                                'title': t.text,
                                'link': l.text if l is not None else '',
                                'description': d.text if d is not None else '',
                                'date': p.text if p is not None else '',
                                'source': source_name
                            })
            except Exception as e:
                result_holder['error'] = e

        t = threading.Thread(target=_fetch_rss, daemon=True)
        t.start()
        t.join(timeout=15)

        if t.is_alive():
            error_msg = f"RSS hatası - {source_name}: Timeout (15s)"
            self.rss_errors.append(error_msg)
            print(f"      ⏱️  RSS TIMEOUT (15s) — geçiliyor")
            return []

        if result_holder['error']:
            e = result_holder['error']
            error_msg = f"RSS hatası - {source_name}: {str(e)[:100]}"
            self.rss_errors.append(error_msg)
            print(f"      ❌ RSS HATA: {str(e)[:50]}")
            return []

        return result_holder['articles']

    def _load_used_links(self):
        """
        Kullanılan linkleri 7 günden yükle
        Backward compatibility: eski format (3 sütun) ve yeni format (4 sütun + hash) destekler
        """
        if not os.path.exists(self.used_links_file):
            return set(), {}, set()

        cutoff = datetime.now() - timedelta(days=7)
        used_links = set()
        used_titles = {}
        used_hashes = set()

        try:
            with open(self.used_links_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        parts = line.split('\t')
                        date_str = parts[0]
                        date = datetime.strptime(date_str, '%Y-%m-%d')

                        if date < cutoff:
                            continue

                        if len(parts) >= 4:
                            link, title, content_hash = parts[1], '\t'.join(parts[2:-1]), parts[-1]
                            used_links.add(_normalize_url_advanced(link))
                            used_titles[link] = title
                            used_hashes.add(content_hash)
                        elif len(parts) >= 3:
                            link, title = parts[1], '\t'.join(parts[2:])
                            used_links.add(_normalize_url_advanced(link))
                            used_titles[link] = title
                    except Exception:
                        continue
        except IOError as e:
            print(f"   ⚠️  Uyarı: Linkler dosyası okunurken hata - {e}")

        return used_links, used_titles, used_hashes

    def _similarity(self, a, b):
        """Başlık benzerliği"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def _save_used_links(self, articles):
        """Kullanılan linkleri kaydet (7 günden eski olanları sil)"""
        if not articles:
            return

        now = datetime.now()
        cutoff = now - timedelta(days=7)

        existing = []
        if os.path.exists(self.used_links_file):
            try:
                with open(self.used_links_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            parts = line.split('\t')
                            date_str = parts[0]
                            date = datetime.strptime(date_str, '%Y-%m-%d')
                            if date >= cutoff:
                                existing.append(line)
                        except:
                            pass
            except IOError:
                pass

        today = now.strftime('%Y-%m-%d')
        for art in articles:
            if art.get('link'):
                title = art.get('title', '')
                description = art.get('description', '')
                content_hash = _calculate_content_hash(title, description)
                existing.append(f"{today}\t{art['link']}\t{title}\t{content_hash}")

        os.makedirs("data", exist_ok=True)
        try:
            with open(self.used_links_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(existing) + '\n')
        except IOError as e:
            print(f"   ❌ Hata: Linkler dosyasına yazılamadı - {e}")

    def _save_rss_errors(self):
        """RSS hatalarını kaydet (7 günden eski olanları sil)"""
        if not self.rss_errors:
            return

        now = datetime.now()
        cutoff = now - timedelta(days=7)

        existing = []
        if os.path.exists(self.rss_errors_file):
            with open(self.rss_errors_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        date_str = line.split(' | ')[0]
                        date = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
                        if date >= cutoff:
                            existing.append(line)
                    except:
                        pass

        timestamp = now.strftime('%Y-%m-%d %H:%M')
        for error in self.rss_errors:
            existing.append(f"{timestamp} | {error}")

        os.makedirs("data", exist_ok=True)
        with open(self.rss_errors_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(existing) + '\n')

        print(f"⚠️  {len(self.rss_errors)} RSS hatası kaydedildi: {self.rss_errors_file}")

    def _normalize_link(self, link):
        """Link normalizasyonu (DEPRECATED - _normalize_url_advanced() kullan)"""
        return _normalize_url_advanced(link)

    def _filter_duplicates(self, all_news):
        """
        Tekrar eden haberleri filtrele (3 seviye: link + hash + benzerlik)
        """
        used_links, used_titles, used_hashes = self._load_used_links()

        filtered = {}
        removed_count = 0
        detail_removed = {'link': 0, 'hash': 0, 'similarity': 0}

        for src, articles in all_news.items():
            filtered_articles = []

            for art in articles:
                link = art.get('link', '')
                title = art.get('title', '')
                description = art.get('description', '')
                link_norm = _normalize_url_advanced(link)

                # Seviye 1: Link kontrolü
                if link_norm in used_links:
                    removed_count += 1
                    detail_removed['link'] += 1
                    continue

                # Seviye 2: Content hash kontrolü
                content_hash = _calculate_content_hash(title, description)
                if content_hash in used_hashes:
                    removed_count += 1
                    detail_removed['hash'] += 1
                    continue

                # Seviye 3: Başlık benzerliği
                is_similar = False
                for used_title in used_titles.values():
                    similarity = SequenceMatcher(None, title.lower(), used_title.lower()).ratio()
                    if similarity >= 0.85:
                        is_similar = True
                        removed_count += 1
                        detail_removed['similarity'] += 1
                        break

                if is_similar:
                    continue

                filtered_articles.append(art)

            if filtered_articles:
                filtered[src] = filtered_articles

        if removed_count > 0:
            print(f"🔄 {removed_count} tekrar eden haber filtrelendi")
            print(f"   ├─ URL: {detail_removed['link']}")
            print(f"   ├─ Hash: {detail_removed['hash']}")
            print(f"   └─ Benzerlik: {detail_removed['similarity']}")

        return filtered

    def _filter_old_articles(self, all_news):
        """Son 30 saatte yayınlanmayan haberleri filtrele.

        Tarih değil datetime karşılaştırması kullanılır:
        - "yesterday_tr" (tarih bazlı) sabah 07 UTC çalışmasında
          tüm dünü kabul eder → %70 dünkü haber dolardı.
        - "today_tr" (tarih bazlı) sabah 07 UTC'de yalnızca 1-2 haber bırakır
          (ABD iş saatlerindeki haberler henüz yayınlanmamış).
        - 30 saatlik datetime penceresi her iki sorunu da çözer.
        """
        from datetime import timezone, timedelta as td
        UTC = timezone.utc
        cutoff_dt = datetime.now(UTC) - td(hours=30)

        filtered = {}
        removed_count = 0

        for src, articles in all_news.items():
            filtered_articles = []
            for art in articles:
                raw_date = art.get('date', '')
                art_dt = None

                # Timezone-aware formatları dene
                for fmt in [
                    '%a, %d %b %Y %H:%M:%S %z',
                    '%Y-%m-%dT%H:%M:%S%z',
                    '%Y-%m-%dT%H:%M:%S.%f%z',
                ]:
                    try:
                        art_dt = datetime.strptime(raw_date, fmt)
                        break
                    except Exception:
                        pass

                # Z sonekini dene
                if art_dt is None and isinstance(raw_date, str) and raw_date.endswith('Z'):
                    for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ']:
                        try:
                            art_dt = datetime.strptime(raw_date, fmt).replace(tzinfo=UTC)
                            break
                        except Exception:
                            pass

                if art_dt is None:
                    # Tarih parse edilemezse dahil et (güvenli taraf)
                    filtered_articles.append(art)
                    continue

                if not art_dt.tzinfo:
                    art_dt = art_dt.replace(tzinfo=UTC)

                if art_dt >= cutoff_dt:
                    filtered_articles.append(art)
                else:
                    removed_count += 1

            if filtered_articles:
                filtered[src] = filtered_articles

        if removed_count > 0:
            print(f"📅 {removed_count} eski haber filtrelendi (>30 saat)")

        return filtered

    def topla(self):
        """Tüm haberleri topla"""
        print("=" * 70)
        print("📰 HABERLERİ TOPLAMA")
        print("=" * 70)
        print(f"🔍 {len(self.sources)} kaynak | ⏱️  15-25 dakika\n")

        all_news = {}
        total = 0
        full_text_success = 0

        for idx, (src, url) in enumerate(self.sources.items(), 1):
            print(f"[{idx}/{len(self.sources)}] 🔍 {src}")
            articles = self.fetch_rss(url, src)

            if articles:
                # Newsletter URL'lerini ayır: atlamak yerine içlerindeki
                # makale linklerini çıkararak pipeline'a sok
                regular_articles  = []
                newsletter_urls   = []  # list of (url, pub_date) tuples
                for a in articles:
                    link_lower = (a.get('link') or '').lower()
                    if any(pat in link_lower for pat in SKIP_URL_PATTERNS):
                        newsletter_urls.append((a['link'], a.get('date', '')))
                    else:
                        regular_articles.append(a)

                if newsletter_urls:
                    print(f"   └─ 🔗 {len(newsletter_urls)} newsletter sayfası genişletilecek")
                    crawled = self._crawl_newsletter_links(newsletter_urls, src)
                    regular_articles.extend(crawled)

                articles = regular_articles
                if not articles:
                    print(f"   └─ ❌ Bulunamadı (tümü filtrelendi)")
                    time.sleep(1)
                    continue

                print(f"   └─ ✅ {len(articles)} haber")
                total += len(articles)
                print(f"   └─ 📄 Tam metinler:")
                for i, art in enumerate(articles, 1):
                    if art['link'] and not art.get('success'):  # crawled makalelerde zaten çekildi
                        print(f"      [{i}/{len(articles)}]", end=' ', flush=True)
                        res = self.fetch_full_article(art['link'], src)
                        art.update(res)
                        if res['success']:
                            full_text_success += 1
                        time.sleep(2)
                    elif art.get('success'):
                        full_text_success += 1
                all_news[src] = articles
            else:
                print(f"   └─ ❌ Bulunamadı")

            time.sleep(1)

        if self.rss_errors:
            self._save_rss_errors()

        # ── Sosyal medya sinyalleri (Reddit, HN, GitHub) ──
        # Haber akışından ayrı tutulur, sadece HTML enjeksiyonu için saklanır
        self.social_data = fetch_social_signals(SOCIAL_SIGNAL_CONFIG)

        all_news = self._filter_duplicates(all_news)
        all_news = self._filter_old_articles(all_news)

        total        = sum(len(arts) for arts in all_news.values())
        full_text_ok = sum(1 for arts in all_news.values() for art in arts if art.get('success'))

        print(f"\n{'=' * 70}")
        print(f"📊 {total} haber (tekrarsız) | {full_text_ok} tam metin | 📡 {len(self.social_data)} sosyal sinyal")
        print(f"{'=' * 70}\n")
        return all_news

    def save_txt(self, news_data):
        """Ham RSS'i günlük kaydet (üzerine yaz)"""
        print("💾 TXT dosyaları kaydediliyor...")
        now = datetime.now()
        os.makedirs("data", exist_ok=True)

        # SESSION_DATE ilk satırda — git checkout mtime'a güvenmek yerine
        # içerik kontrolü için kullanılır (bkz. main() ham_exists_for_today kontrolü)
        txt = f"SESSION_DATE: {now.strftime('%Y-%m-%d')}\n"
        txt += f"\n{'=' * 80}\n📅 {now.strftime('%d %B %Y').upper()} - SİBER GÜVENLİK HABERLERİ (HAM RSS)\n{'=' * 80}\n\n"

        all_articles = []
        num = 0
        skipped_no_content = 0
        for src, articles in news_data.items():
            for art in articles:
                all_articles.append(art)
                # Tam metni olmayan haberleri Gemini'ye gönderme — sadece başlık varsa
                # Gemini içerik üretemez ve halüsinasyon yapar, bu yüzden kesinlikle dışla
                if not art.get('success') or art.get('word_count', 0) == 0:
                    skipped_no_content += 1
                    continue
                num += 1
                txt += f"[{num}] {src} - {art['title']}\n{'─' * 80}\n"
                txt += f"Tarih: {art['date']}\nLink: {art['link']}\n"
                txt += f"\n[TAM METİN - {art['word_count']} kelime]\n{art['full_text']}\n"
                art_date = _parse_article_date(art.get('date', ''), now)
                txt += f"\n(XXXXXXX, AÇIK - {art.get('link', '')}, {art.get('domain', '')}, {art_date})\n\n{'=' * 80}\n\n"

        if skipped_no_content > 0:
            print(f"⚠️  {skipped_no_content} haber tam metin olmadığı için rapor dışı bırakıldı (halüsinasyon önleme)")

        # Sosyal sinyaller — haber değil, arşiv amaçlı referans kaydı
        if self.social_data:
            txt += f"\n{'=' * 80}\n"
            txt += f"SOSYAL MEDYA SİNYALLERİ — HABER DEĞİL, SADECE REFERANS KAYDI\n"
            txt += f"[S1]-[S5] etiketleri haber sayılmaz, Gemini bu bölümü işlemez.\n"
            txt += f"{'=' * 80}\n\n"
            for i, art in enumerate(self.social_data, 1):
                platform = art.get('platform', 'unknown')
                score    = art.get('score', 0)
                comments = art.get('comments', 0)
                txt += f"[S{i}] {art['source']} | Skor: {score} | Yorum: {comments}\n"
                txt += f"Baslik: {art['title']}\n"
                txt += f"Link: {art['link']}\n"
                if art.get('full_text'):
                    txt += f"{art['full_text'][:200]}\n"
                txt += f"\n"

        with open("data/haberler_ham.txt", 'w', encoding='utf-8') as f:
            f.write(txt)

        print(f"✅ data/haberler_ham.txt (günlük - üzerine yazıldı)")

        self._save_used_links(all_articles)

        return txt

    def save_summary_to_archive(self, html_content):
        """Gemini'nin seçtiği EN ÖNEMLİ 43 HABERİ TXT arşivine EKLE (sürekli birikim)"""
        print("📚 En önemli 43 haber arşive ekleniyor...")
        now = datetime.now()

        soup = BeautifulSoup(html_content, 'html.parser')

        archive_entry = f"\n{'=' * 80}\n📅 {now.strftime('%d %B %Y').upper()} - EN ÖNEMLİ 43 HABER (SEÇİLMİŞ)\n{'=' * 80}\n\n"

        news_items = soup.find_all('div', class_='news-item')[:43]

        for idx, item in enumerate(news_items, 1):
            title_elem = item.find('div', class_='news-title')
            content_elem = item.find('p', class_='news-content')
            source_elem = item.find('p', class_='source')

            if title_elem and content_elem:
                title = title_elem.get_text(strip=True).replace('<b>', '').replace('</b>', '')
                content = content_elem.get_text(strip=True)
                source = source_elem.get_text(strip=True) if source_elem else ""

                archive_entry += f"[{idx:2d}] {title}\n"
                archive_entry += f"─────────────────────────────────────────────────────────\n"
                archive_entry += f"{content}\n"
                if source:
                    archive_entry += f"{source}\n"
                archive_entry += "\n" + "─" * 80 + "\n\n"

        os.makedirs("data", exist_ok=True)
        with open(ARCHIVE_FILE, 'a', encoding='utf-8') as f:
            f.write(archive_entry)

        print(f"✅ {ARCHIVE_FILE} (en önemli {len(news_items)} haber arşivlendi)")

        self._check_archive_size()

    def _check_archive_size(self):
        """Arşiv boyutunu kontrol et ve 100 MB'ı geçince uyar (SİLMEZ)"""
        if not os.path.exists(ARCHIVE_FILE):
            return

        file_size = os.path.getsize(ARCHIVE_FILE) / (1024 * 1024)
        print(f"📦 Arşiv boyutu: {file_size:.1f} MB")

        if file_size >= 100:
            print("")
            print("=" * 70)
            print("🚨 UYARI: ARŞİV DOSYASI 100 MB'I AŞTI!")
            print("=" * 70)
            print(f"📁 Dosya: {ARCHIVE_FILE}")
            print(f"📏 Boyut: {file_size:.1f} MB")
            print(f"📅 Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
            print("")
            print("⚠️  Lütfen aşağıdaki adımlardan birini uygulayın:")
            print("   1. Dosyayı yedekleyip harici depolamaya taşıyın")
            print("   2. Eski kayıtları manuel olarak arşivleyin")
            print("")
            print("❌ Arşiv otomatik olarak SİLİNMEYECEKTİR.")
            print("=" * 70)
            print("")

    # ═══════════════════════════════════════════════════════════════
    # HTML OLUŞTURMA — DOĞRULAMA + TAMAMLAMA MEKANİZMALI (v2.1)
    # ═══════════════════════════════════════════════════════════════

    def create_html(self, txt_content):
        """Gemini ile HTML oluştur — DOĞRULAMA + TAMAMLAMA MEKANİZMALI"""
        print("🤖 Gemini API...")
        if not GEMINI_API_KEY:
            raise ValueError("❌ GEMINI_API_KEY yok!")

        client = genai.Client(api_key=GEMINI_API_KEY)

        # ═══════════════════════════════════════════
        # AŞAMA 1: Gemini'den HTML al
        # 5 deneme, üstel geri çekilme (30s→60s→120s→240s)
        # Model sırası: gemini-2.5-pro (×2) → gemini-2.5-flash (×2) → gemini-2.0-flash (×1)
        # 503/yüksek yük hatalarında daha uzun bekleme + eski modele düşme.
        # ═══════════════════════════════════════════
        # Model başına parametreler — max_output_tokens model sınırını aşamaz
        _MODEL_CFG = {
            'gemini-2.5-pro':   {'max_output_tokens': 65000, 'accept_max_tokens': False},
            'gemini-2.5-flash': {'max_output_tokens': 65536, 'accept_max_tokens': False},
            'gemini-2.0-flash': {'max_output_tokens': 8192,  'accept_max_tokens': True},
        }
        _GEMINI_MODELS = list(_MODEL_CFG.keys())
        html = None
        max_attempts = 5
        last_error_type = None
        last_error_message = None

        for attempt in range(max_attempts):
            # Her 2 başarısız denemeden sonra bir sonraki modele geç
            model = _GEMINI_MODELS[min(attempt // 2, len(_GEMINI_MODELS) - 1)]
            cfg   = _MODEL_CFG[model]
            try:
                print(f"   Deneme {attempt + 1}/{max_attempts} [{model}]...")

                prompt = get_claude_prompt(txt_content)

                # Streaming kullan: büyük response'larda server disconnect riskini önler
                chunks     = []
                last_chunk = None
                for chunk in client.models.generate_content_stream(
                    model=model,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        max_output_tokens=cfg['max_output_tokens'],
                        temperature=0.7,
                        safety_settings=[
                            genai_types.SafetySetting(
                                category='HARM_CATEGORY_DANGEROUS_CONTENT',
                                threshold='BLOCK_ONLY_HIGH',
                            ),
                            genai_types.SafetySetting(
                                category='HARM_CATEGORY_HARASSMENT',
                                threshold='BLOCK_ONLY_HIGH',
                            ),
                        ],
                    )
                ):
                    if chunk.text:
                        chunks.append(chunk.text)
                    last_chunk = chunk

                # finish_reason son chunk'tan al
                # STOP: tam tamamlama. MAX_TOKENS: token limiti doldu — sadece düşük
                # limitli modelde (2.0-flash) kabul edilir; diğerlerinde hata sayılır.
                if last_chunk and last_chunk.candidates:
                    finish_reason = last_chunk.candidates[0].finish_reason
                    print(f"   Finish reason: {finish_reason}")
                    ok_reasons = {'STOP', 'FinishReason.STOP', '1'}
                    if cfg['accept_max_tokens']:
                        ok_reasons |= {'MAX_TOKENS', 'FinishReason.MAX_TOKENS', '2'}
                    if str(finish_reason) not in ok_reasons:
                        raise Exception(f"Stream tamamlanmadi (finish_reason={finish_reason})")
                elif not chunks:
                    raise Exception("Stream bos dondu")

                html = ''.join(chunks)
                break
            except Exception as e:
                last_error_type = type(e).__name__
                last_error_message = str(e)
                print(f"   ⚠️  Hata [{last_error_type}]: {last_error_message}")
                if attempt < max_attempts - 1:
                    wait_time = min(30 * (2 ** attempt), 240)  # 30s,60s,120s,240s
                    next_model = _GEMINI_MODELS[min((attempt + 1) // 2, len(_GEMINI_MODELS) - 1)]
                    model_note = f" → {next_model}" if next_model != model else ""
                    print(f"   ⏳ {wait_time}s bekleniyor{model_note}...")
                    time.sleep(wait_time)
                else:
                    print(f"   ❌ {max_attempts} deneme başarısız — OpenRouter fallback'i deneniyor...")
                    print(f"   ℹ️  Gemini başarısız, Qwen 3.6 Plus (OpenRouter) deneniyor.")
                    html = self._generate_html_with_openrouter(txt_content)
                    if html:
                        # OpenRouter başarılı
                        print("\n✅ OpenRouter başarılı — standart işlem akışı devam ediyor")
                    else:
                        # OpenRouter da başarısız → fallback HTML
                        print(f"   ❌ OpenRouter de başarısız — fallback HTML oluşturuluyor.")
                        return self._create_fallback_html(
                            txt_content,
                            error_type=last_error_type,
                            error_message=last_error_message,
                        )
                    break  # OpenRouter başarılı, döngüden çık

        if not html:
            return self._create_fallback_html(
                txt_content,
                error_type=last_error_type,
                error_message=last_error_message,
            )

        # HTML temizle — Gemini bazen "Elbette, işte rapor: ```html" şeklinde
        # konuşma metni ekler. DOCTYPE veya <html etiketini bulup öncesini sil.
        import re as _re_html
        doctype_pos = html.lower().find('<!doctype html')
        html_tag_pos = html.lower().find('<html')
        candidates = [p for p in [doctype_pos, html_tag_pos] if p != -1]
        if candidates:
            html_start = min(candidates)
            if html_start > 0:
                print(f"   ⚠️  HTML öncesi metin temizlendi ({html_start} karakter preamble)")
            html = html[html_start:]
        # Sondaki kod bloğu kapanışını temizle
        html = _re_html.sub(r'\s*```\s*$', '', html).strip()

        print(f"✅ HTML oluşturuldu ({len(html)} karakter)")

        # ═══════════════════════════════════════════
        # AŞAMA 2: DOĞRULAMA — Paragraf sayısı kontrolü
        # ═══════════════════════════════════════════
        validation = self._validate_html_completeness(html)

        # ═══════════════════════════════════════════
        # AŞAMA 3: EKSİK PARAGRAF TAMAMLAMA (max 2 tur)
        # ═══════════════════════════════════════════
        completion_attempts = 0
        max_completion_attempts = 2

        while not validation['is_valid'] and completion_attempts < max_completion_attempts:
            completion_attempts += 1
            print(f"\n   🔄 Tamamlama denemesi {completion_attempts}/{max_completion_attempts}...")

            html = self._complete_missing_paragraphs(html, txt_content, validation)
            validation = self._validate_html_completeness(html)

        if not validation['is_valid']:
            print(f"   ⚠️  {max_completion_attempts} tamamlama sonrası hâlâ eksik var")
            print(f"   📊 Final: Özet={validation['summary_count']}, Paragraf={validation['paragraph_count']}")
        else:
            print(f"   ✅ Tüm paragraflar tamam! ({validation['paragraph_count']} haber)")

        # ═══════════════════════════════════════════
        # AŞAMA 4: Mevcut post-processing
        # ═══════════════════════════════════════════
        self._translate_social_signals()
        html = self._inject_social_box(html)
        html = self._fix_source_dates(html, txt_content)
        html = self._fix_source_links(html)
        html = self._remove_commentary_sentences(html)
        html = self._fix_html_structure(html)   # </style> / report-header kontrolü

        html_index = self._add_archive_links(html, is_archive=False)
        html_archive = self._add_archive_links(html, is_archive=True)

        # Kaydet
        os.makedirs("docs/raporlar", exist_ok=True)
        now = datetime.now()

        with open("docs/index.html", 'w', encoding='utf-8') as f:
            f.write(html_index)

        with open(f"docs/raporlar/{now.strftime('%Y-%m-%d')}.html", 'w', encoding='utf-8') as f:
            f.write(html_archive)

        print("✅ docs/index.html")
        print(f"✅ docs/raporlar/{now.strftime('%Y-%m-%d')}.html")

        self.save_summary_to_archive(html)
        self._cleanup_old_reports()

        return html

    def _validate_html_completeness(self, html):
        """HTML'deki yönetici özeti sayısı ile haber paragrafı sayısını karşılaştır"""
        import re

        soup = BeautifulSoup(html, 'html.parser')

        # Önemli gelişmeler (5 adet) + tablodaki haberler
        important_items = soup.find_all('div', class_='important-item')
        table_links = []
        exec_table = soup.find('table', class_='executive-table')
        if exec_table:
            table_links = exec_table.find_all('a')

        summary_count = len(important_items) + len(table_links)

        # Haber paragraflarını say
        news_items = soup.find_all('div', class_='news-item')
        paragraph_count = len(news_items)

        # Mevcut paragrafların ID'lerini çıkar
        existing_ids = set()
        for item in news_items:
            item_id = item.get('id', '')
            match = re.search(r'haber-(\d+)', item_id)
            if match:
                existing_ids.add(int(match.group(1)))

        # Eksik ID'leri bul
        if summary_count > 0:
            expected_ids = set(range(1, summary_count + 1))
            missing_ids = sorted(expected_ids - existing_ids)
        else:
            missing_ids = []

        last_paragraph_id = max(existing_ids) if existing_ids else 0
        is_valid = paragraph_count >= summary_count and len(missing_ids) == 0

        result = {
            'is_valid': is_valid,
            'summary_count': summary_count,
            'paragraph_count': paragraph_count,
            'missing_ids': missing_ids,
            'last_paragraph_id': last_paragraph_id
        }

        status = "✅ TAMAM" if is_valid else "❌ EKSİK"
        print(f"   📊 Doğrulama: Özet={summary_count}, Paragraf={paragraph_count} {status}")
        if missing_ids:
            print(f"   ⚠️  Eksik haber ID'leri: {missing_ids}")

        return result

    def _complete_missing_paragraphs(self, html, txt_content, validation):
        """Eksik haber paragraflarını Gemini'ye tamamlattır ve HTML'e ekle"""
        import re

        missing_ids = validation['missing_ids']
        last_id = validation['last_paragraph_id']

        if not missing_ids:
            return html

        print(f"   🔄 {len(missing_ids)} eksik paragraf tamamlanıyor (ID: {missing_ids[0]}-{missing_ids[-1]})...")

        # Mevcut HTML'den eksik haberlerin başlıklarını çıkar
        soup = BeautifulSoup(html, 'html.parser')
        all_titles = {}

        # Önemli gelişmelerden
        for item in soup.find_all('div', class_='important-item'):
            link = item.find('a')
            if link:
                match = re.search(r'#haber-(\d+)', link.get('href', ''))
                if match:
                    haber_id = int(match.group(1))
                    title_text = re.sub(r'^\d+\.\s*', '', link.get_text(strip=True))
                    all_titles[haber_id] = title_text

        # Tablodan
        exec_table = soup.find('table', class_='executive-table')
        if exec_table:
            for link in exec_table.find_all('a'):
                match = re.search(r'#haber-(\d+)', link.get('href', ''))
                if match:
                    haber_id = int(match.group(1))
                    title_text = re.sub(r'^\d+\.\s*', '', link.get_text(strip=True))
                    all_titles[haber_id] = title_text

        # Eksik başlıkları listele
        missing_titles = []
        for mid in missing_ids:
            title = all_titles.get(mid, f"Haber #{mid}")
            missing_titles.append(f"  - haber-{mid}: {title}")

        titles_text = "\n".join(missing_titles)

        # Tamamlama prompt'u
        completion_prompt = f"""Aşağıdaki siber güvenlik haberlerinin SADECE eksik paragraf özetlerini yaz.

HAM HABER METNİ:
{txt_content}

EKSİK HABER PARAGRAFLARI (SADECE bu ID'lerin paragraflarını yaz):
{titles_text}

HER PARAGRAF İÇİN ÇIKTI FORMATI (SADECE BU FORMATTA, BAŞKA HİÇBİR ŞEY YAZMA):

<div class="news-item" id="haber-N">
    <div class="news-title"><b>Haberin Başlığı</b></div>
    <p class="news-content">MİNİMUM 100 kelime paragraf özet, resmi Türkçe. 5N1K sorularını kapsa, teknik detaylar ekle.</p>
    <p class="source"><b>(KAYNAK, AÇIK - <a href="LINK" target="_blank">domain.com</a>, TARİH)</b></p>
</div>

KURALLAR:
- SADECE eksik paragrafları yaz, CSS/başlık/açıklama YAZMA
- Her paragraf MİNİMUM 100 kelime (kesinlikle daha kısa yazma, 100'den az kelime HATALIDIIR)
- İdeal uzunluk: 110-150 kelime; 5N1K sorularını (kim/ne/nerede/ne zaman/nasıl/neden) kapsa
- Resmi Türkçe (-mıştır, -edilmiştir)
- Sıra: haber-{missing_ids[0]}'den haber-{missing_ids[-1]}'e
- Kod bloğu (```) KULLANMA, direkt HTML yaz
"""

        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model='gemini-2.5-pro',
                contents=completion_prompt,
                config=genai_types.GenerateContentConfig(
                    max_output_tokens=65000,
                    temperature=0.7,
                )
            )

            new_paragraphs = response.text

            # Temizle
            if new_paragraphs.startswith('```html'):
                new_paragraphs = new_paragraphs[7:]
            if new_paragraphs.startswith('```'):
                new_paragraphs = new_paragraphs[3:]
            if new_paragraphs.endswith('```'):
                new_paragraphs = new_paragraphs[:-3]
            new_paragraphs = new_paragraphs.strip()

            if not new_paragraphs:
                print("   ⚠️  Tamamlama yanıtı boş geldi")
                return html

            # Yeni paragraf sayısını kontrol et
            new_soup = BeautifulSoup(new_paragraphs, 'html.parser')
            new_items = new_soup.find_all('div', class_='news-item')
            print(f"   ✅ {len(new_items)} yeni paragraf alındı")

            if len(new_items) == 0:
                print("   ⚠️  Tamamlama yanıtında news-item bulunamadı")
                return html

            # HTML'e ekle: son news-item'ın source paragrafından sonra
            all_source_ends = list(re.finditer(
                r'</p>\s*</div>\s*(?=\s*(?:</div>|<div\s+class="news-item"|<a\s+href))',
                html
            ))

            if all_source_ends:
                insert_pos = all_source_ends[-1].end()
                html = html[:insert_pos] + "\n\n            " + new_paragraphs + "\n" + html[insert_pos:]
                print(f"   ✅ Eksik paragraflar HTML'e eklendi")
            else:
                # Fallback: </body> etiketinden önce
                body_close = html.rfind('</body>')
                if body_close > 0:
                    html = html[:body_close] + "\n" + new_paragraphs + "\n" + html[body_close:]
                    print(f"   ⚠️  Fallback: </body> önüne eklendi")
                else:
                    html += "\n" + new_paragraphs
                    print(f"   ⚠️  Fallback: HTML sonuna eklendi")

            return html

        except Exception as e:
            print(f"   ❌ Tamamlama hatası: {e}")
            return html

    def _translate_social_signals(self):
        """
        Sosyal sinyal başlıklarını Gemini ile resmi Türkçe tek cümleye çevirir.
        Sonuç her öğenin 'title_tr' alanına yazılır.
        Hata durumunda orijinal başlık kullanılmaya devam eder.
        """
        import re as _re
        if not self.social_data:
            return

        lines = [f"[S{i}]: {p.get('title', '')}"
                 for i, p in enumerate(self.social_data, 1)]
        prompt = (
            "Aşağıdaki sosyal medya paylaşım başlıklarını değerlendir.\n\n"
            "KARAR KURALI — Her başlık için şunu sor: Bu başlık Türkçeye çevrildiğinde "
            "ANLAMLI ve AKICI bir Türkçe cümle oluşuyor mu?\n"
            "  • EVET → Resmi Türkçeye çevir (-mıştır, -edilmiştir, -tespit edilmiştir "
            "gibi resmi fiil çekimleri zorunludur).\n"
            "  • HAYIR → Orijinal metni AYNEN geri yaz, hiç dokunma.\n\n"
            "Anlamlı çeviri YAPILAMAYAN durumlar (orijinali koru):\n"
            "  - Başlık yalnızca CVE numarası, versiyon, hash, komut satırı vb. içeriyorsa\n"
            "  - Başlıktaki kelimelerin büyük çoğunluğu teknik kısaltma / özel isimse\n"
            "  - Çevrildiğinde Türkçe cümle kurulamıyorsa\n"
            "  - Anlam bütünlüğü bozulacaksa\n\n"
            "KRİTİK: Teknik terimler, yazılım/şirket/ürün/protokol adları, CVE numaraları "
            "(Windows, Apache, Kubernetes, LockBit, Fortinet, RCE, SQL Injection vb.) "
            "çevrilmez — orijinal halleriyle cümle içinde bırakılır.\n\n"
            "[S1]'den [S" + str(len(self.social_data)) + "]'e kadar HER satır için "
            "mutlaka bir çıktı ver. Sadece sonuçları yaz, açıklama ekleme.\n"
            "Format:\n[S1]: <çeviri veya orijinal metin>\n[S2]: <çeviri veya orijinal metin>\n\n"
            + '\n'.join(lines)
        )
        for model_name in ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash']:
            try:
                client = genai.Client(api_key=GEMINI_API_KEY)
                chunks = []
                for chunk in client.models.generate_content_stream(
                    model=model_name,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        max_output_tokens=2048,
                        temperature=0.2,
                    ),
                ):
                    if chunk.text:
                        chunks.append(chunk.text)
                text = ''.join(chunks).strip()
                matched = 0
                for match in _re.finditer(r'\[S(\d+)\]:\s*(.+)', text):
                    idx = int(match.group(1)) - 1
                    if 0 <= idx < len(self.social_data):
                        self.social_data[idx]['title_tr'] = match.group(2).strip()
                        matched += 1
                print(f"   Sosyal sinyal Türkçe özetler ({model_name}): "
                      f"{matched}/{len(self.social_data)}")
                if matched > 0:
                    break   # Başarılı, ikinci modeli deneme
            except Exception as e:
                print(f"   Sosyal sinyal çeviri hatası [{model_name}]: {e}")
                continue

    def _inject_social_box(self, html):
        """
        Sosyal medya sinyalleri kutusunu HTML'e enjekte eder.
        Konum: .executive-table'dan sonra, .news-section'dan önce (B konumu).
        self.social_data listesini kullanır — Gemini'den bağımsız, programatik.
        """
        from bs4 import BeautifulSoup as _BS

        if not getattr(self, 'social_data', None):
            return html

        platform_css = {
            'reddit':            'reddit-item',
            'hackernews':        'hn-item',
            'github_advisories': 'github-item',
            'mastodon':          'mastodon-item',
        }
        platform_labels = {
            'reddit':            'Reddit',
            'hackernews':        'HackerNews',
            'github_advisories': 'GitHub Advisory',
            'mastodon':          'Mastodon',
        }

        items_html = ''
        for post in self.social_data:
            platform    = post.get('platform', '')
            source      = platform_labels.get(platform, post.get('source', ''))
            # title_tr varsa (Gemini çevirisi) onu kullan, yoksa orijinal başlık
            raw_title   = post.get('title_tr') or post.get('title', '')
            title       = raw_title.replace('<', '&lt;').replace('>', '&gt;')
            link        = post.get('link', '#')
            score       = post.get('score', 0)
            comments    = post.get('comments', 0)
            item_cls    = platform_css.get(platform, '')

            if platform == 'github_advisories':
                _sev_tr    = {'critical': 'KRİTİK', 'high': 'YÜKSEK',
                              'medium': 'ORTA', 'low': 'DÜŞÜK'}
                sev_raw    = post.get('severity', '').lower()
                sev_label  = _sev_tr.get(sev_raw, sev_raw.upper())
                cvss       = post.get('cvss', 0)
                engagement = f"ÖNEM: {sev_label}"
                if cvss:
                    engagement += f"  |  CVSS: {cvss}"
            elif platform == 'mastodon':
                favs    = post.get('favourites', 0)
                reblogs = post.get('reblogs', 0)
                engagement = f"★{favs}"
                if reblogs:
                    engagement += f"  |  ↺{reblogs}"
            elif platform == 'reddit':
                ups = post.get('score', 0)
                num_c = post.get('comments', 0)
                engagement = f"▲{ups}"
                if num_c:
                    engagement += f"  |  {num_c} yorum"
            else:
                # hackernews
                engagement = f"{score} puan"
                if comments > 0:
                    engagement += f"  |  {comments} yorum"

            items_html += (
                f'<div class="signal-item {item_cls}">'
                f'  <div class="signal-meta">'
                f'    <span class="signal-platform-label">{source}</span>'
                f'    <span class="signal-engagement">{engagement}</span>'
                f'  </div>'
                f'  <a href="{link}" target="_blank" rel="noopener noreferrer">{title}</a>'
                f'</div>\n'
            )

        box_html = (
            f'<div class="social-signals">'
            f'<h2>Sosyal Medya Sinyalleri</h2>'
            f'<div class="signal-list">{items_html}</div>'
            f'</div>'
        )

        soup = _BS(html, 'html.parser')

        # Konum B: executive-table'dan sonra, news-section'dan önce
        exec_table   = soup.find('table', class_='executive-table')
        news_section = soup.find('div', class_='news-section')

        if exec_table:
            exec_table.insert_after(_BS(box_html, 'html.parser'))
        elif news_section:
            news_section.insert_before(_BS(box_html, 'html.parser'))
        else:
            # Fallback: body'nin sonuna ekle
            body = soup.find('body')
            if body:
                body.append(_BS(box_html, 'html.parser'))

        return str(soup)

    # Kritik CSS sınıfları — bunlar eksikse sayfa düzgün görünmez
    REQUIRED_CSS_CLASSES = [
        '.executive-table',
        '.news-item',
        '.social-signals',
        '.back-to-top',
    ]

    # Eksik CSS sınıfları için yedek blok (config.py şablonundan)
    FALLBACK_CSS = """
        /* YÖNETİCİ ÖZETİ */
        .executive-summary {
            background: #f8f9fa;
            padding: 25px 30px;
            margin: 0;
            border-bottom: 1px solid #e1e8ed;
        }
        .executive-summary h2 {
            color: #1a237e;
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 2px solid #1a237e;
        }
        .executive-table {
            width: 100%;
            border-spacing: 8px;
        }
        .executive-table td {
            background: white;
            padding: 12px 16px;
            border-radius: 6px;
            border-left: 3px solid #1a237e;
            vertical-align: top;
            width: 50%;
        }
        .executive-table a {
            color: #1a237e;
            text-decoration: none;
            font-weight: 500;
            font-size: 14px;
            line-height: 1.4;
        }
        .executive-table a:hover {
            text-decoration: underline;
        }
        /* HABERLER BÖLÜMÜ */
        .news-section { padding: 30px; }
        .news-item {
            background: #f8f9fa;
            margin-bottom: 25px;
            border-radius: 8px;
            padding: 20px;
            border-left: 4px solid #1a237e;
        }
        .news-title {
            color: #1a237e;
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 12px;
            line-height: 1.3;
        }
        .news-content { color: #2c3e50; font-size: 15px; line-height: 1.6; margin-bottom: 10px; }
        .source { color: #666; font-size: 13px; margin: 0; }
        .source a { color: #1a237e; text-decoration: none; }
        .source a:hover { text-decoration: underline; }
        /* ── SOSYAL MEDYA SİNYALLERİ KUTUSU ── */
        .social-signals {
            background: #f8faff;
            border: 1px solid #c7d7fd;
            border-radius: 8px;
            padding: 24px 28px;
            margin-bottom: 20px;
        }
        .social-signals h2 {
            color: #1e3a8a;
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 16px;
            padding-bottom: 10px;
            border-bottom: 2px solid #dbeafe;
        }
        .social-signals .signal-list {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .social-signals .signal-item {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-left: 4px solid #3b82f6;
            border-radius: 6px;
            padding: 12px 16px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .social-signals .signal-item.reddit-item   { border-left-color: #ff4500; }
        .social-signals .signal-item.hn-item       { border-left-color: #ff6600; }
        .social-signals .signal-item.github-item   { border-left-color: #238636; }
        .social-signals .signal-item.mastodon-item { border-left-color: #6364ff; }
        .social-signals .signal-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
        .social-signals .signal-platform-label {
            font-size: 10px;
            font-weight: 700;
            color: #ffffff;
            background: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-radius: 3px;
            padding: 2px 7px;
        }
        .social-signals .reddit-item .signal-platform-label   { background: #ff4500; }
        .social-signals .hn-item .signal-platform-label       { background: #ff6600; }
        .social-signals .github-item .signal-platform-label   { background: #238636; }
        .social-signals .mastodon-item .signal-platform-label { background: #6364ff; }
        .social-signals .signal-engagement {
            font-size: 11px; color: #475569; background: #f1f5f9; border-radius: 3px; padding: 2px 8px;
        }
        .social-signals .signal-item a {
            color: #1e293b;
            text-decoration: none;
            font-size: 13px;
            font-weight: 500;
            line-height: 1.45;
            display: block;
        }
        .social-signals .signal-item a:hover { color: #1e3a8a; text-decoration: underline; }
        @media (max-width: 640px) {
            .social-signals { padding: 16px; }
            .social-signals .signal-list { grid-template-columns: 1fr; }
            .social-signals .signal-meta { gap: 6px; }
        }
        .back-to-top {
            position: fixed;
            top: 50%;
            left: calc(50% - 450px - 48px);
            transform: translateY(-50%);
            width: 36px;
            height: 36px;
            background: #1a237e;
            color: white;
            border: none;
            border-radius: 50%;
            font-size: 18px;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(0,0,0,0.25);
            display: flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            opacity: 0.85;
            transition: opacity 0.2s;
            z-index: 999;
        }
        .back-to-top:hover { opacity: 1; }"""

    def _fix_html_structure(self, html):
        """Gemini çıktısındaki yapısal HTML hatalarını otomatik düzelt.

        Bilinen sorun 1 — </style> eksik:
            Gemini bazen CSS bloğunu kapatmadan doğrudan HTML içeriğine geçer.
            Tarayıcı tüm içeriği CSS olarak yorumlar → boş sayfa.

        Bilinen sorun 2 — report-header div eksik:
            Gemini bazen mavi başlık bölümünü atlar.

        Bilinen sorun 3 — CSS kısmi kesilmiş:
            Gemini bazen </style>'ı erken kapatarak executive-table,
            news-item, social-signals gibi kritik stilleri atlar.
        """
        now = datetime.now()
        tarih = now.strftime('%d.%m.%Y')

        # ── Sorun 1: </style> etiketi eksik ────────────────────────────────
        # Kontrol: <body> etiketi hiç yok veya <style> bloğu kapatılmamış
        style_close_pos = html.find('</style>')
        body_pos        = html.find('<body>')
        first_div_pos   = html.find('<div')

        style_missing = (
            style_close_pos == -1 or           # </style> hiç yok
            (body_pos != -1 and body_pos < style_close_pos) or  # <body> </style>'dan önce geliyor (anlamsız)
            (body_pos == -1 and first_div_pos != -1 and
             first_div_pos < style_close_pos)  # div'ler </style>'dan önce
        )

        if style_missing:
            print("   ⚠️  HTML yapı hatası: </style> eksik veya yanlış konumda — otomatik düzeltiliyor")
            # CSS yorumunu veya ilk HTML etiketini bul, öncesine kapanış ekle
            insert_marker = None
            for marker in [
                '        /* YÖNETİCİ ÖZETİ */',
                '        <div class="executive-summary">',
                '        <div class="container">',
                '<div class="executive-summary">',
                '<div class="container">',
            ]:
                pos = html.find(marker)
                if pos != -1:
                    insert_marker = (pos, marker)
                    break

            if insert_marker:
                pos, marker = insert_marker
                # CSS bloğu yorumundan önceki gereksiz boşluğu temizle, kapanış ekle
                before = html[:pos].rstrip()
                after  = html[pos:]
                # Marker CSS yorumuysa sil, HTML etiketiyse koru
                if marker.startswith('/*'):
                    after = after[len(marker):]
                html = before + '\n    </style>\n</head>\n<body>\n<div class="container">\n' + after.lstrip()
            else:
                print("   ⚠️  Ekleme noktası bulunamadı, yapı düzeltilemiyor")

        # Bozuk kapanış etiketlerini temizle
        for bad, good in [
            ('</html></style></head></html>', '</div>\n</body>\n</html>'),
            ('</body>\n</div>\n</body>\n</html>', '</div>\n</body>\n</html>'),
        ]:
            html = html.replace(bad, good)

        # ── Sorun 2: report-header eksik ───────────────────────────────────
        if '<div class="report-header">' not in html:
            print("   ⚠️  HTML yapı hatası: report-header eksik — otomatik ekleniyor")
            header_html = f'<div class="report-header"><h1><span class="header-date">{tarih}</span> Siber Güvenlik Haber Özetleri</h1></div>\n'
            # <div class="container"> sonrasına ekle
            for anchor in ['<div class="container">\n', '<div class="container">']:
                if anchor in html:
                    html = html.replace(anchor, anchor + header_html, 1)
                    break

        # ── Sorun 3: CSS kısmi kesilmiş (kritik sınıflar eksik) ────────────
        # Gemini </style>'ı erken kapattıysa executive-table, news-item vb. eksik kalır
        style_end = html.find('</style>')
        if style_end != -1:
            css_block = html[:style_end]
            missing_classes = [cls for cls in self.REQUIRED_CSS_CLASSES if cls not in css_block]
            if missing_classes:
                print(f"   ⚠️  HTML yapı hatası: CSS eksik ({', '.join(missing_classes)}) — yedek CSS ekleniyor")
                html = html[:style_end] + self.FALLBACK_CSS + '\n    ' + html[style_end:]

        return html

    def _fix_source_dates(self, html, txt_content):
        """Gemini'nin yazdığı hatalı tarihleri ham TXT'deki gerçek tarihlerle düzelt"""
        import re

        link_to_date = {}
        pattern = re.compile(
            r'[(]XXXXXXX, AÇIK - (https?://[^\s,]+),\s*[^,]+,\s*(\d{2}[.]\d{2}[.]\d{4})[)]'
        )
        for m in pattern.finditer(txt_content):
            link_to_date[m.group(1).strip()] = m.group(2).strip()

        if not link_to_date:
            return html

        source_pattern = re.compile(r'<p class="source">.*?</p>', re.DOTALL)
        href_pattern = re.compile(r'href="(https?://[^"]+)"')
        date_pattern = re.compile(r'\d{2}[.]\d{2}[.]\d{4}(?=[)])')

        def fix_source(m):
            src = m.group(0)
            href_m = href_pattern.search(src)
            if not href_m:
                return src
            href = href_m.group(1).strip()
            if href not in link_to_date:
                return src
            return date_pattern.sub(link_to_date[href], src)

        fixed_html = source_pattern.sub(fix_source, html)
        print("   ✅ Kaynak tarihleri düzeltildi")
        return fixed_html

    def _fix_source_links(self, html):
        """Gemini'nin düz metin yazdığı kaynak URL'lerini tıklanabilir <a href> etiketine çevir.

        Girdi  (Gemini çıktısı):
            <p class="source"><b>(XXXXXXX, AÇIK - https://example.com/article, example.com, 10.03.2026)</b></p>
        Çıktı:
            <p class="source"><b>(XXXXXXX, AÇIK - <a href="https://example.com/article" target="_blank">example.com</a>, 10.03.2026)</b></p>
        """
        import re

        # Zaten <a href> olan satırları atlamak için negatif lookahead kullan
        pattern = re.compile(
            r'AÇIK - (?!<a[\s>])(https?://[^,\s<"]+),\s*([^,<)\s][^,<)]*?),\s*(\d{2}\.\d{2}\.\d{4})\)'
        )

        def replacer(m):
            url    = m.group(1).strip()
            domain = m.group(2).strip()
            date   = m.group(3).strip()
            return f'AÇIK - <a href="{url}" target="_blank">{domain}</a>, {date})'

        fixed, n = pattern.subn(replacer, html)
        if n > 0:
            print(f"   ✅ {n} kaynak linki tıklanabilir yapıldı")
        return fixed

    def _remove_commentary_sentences(self, html):
        """Gemini'nin haber paragraflarının sonuna eklediği yapay yorum cümlelerini sil.

        Hedef kalıplar (Türkçe):
          - "Bu olay/saldırı/durum ... göstermektedir."
          - "Bu yaklaşım/metodoloji ... ortaya koymaktadır."
          - "... bir kez daha ... vurgulamaktadır."
          - "Bu gelişme ... kanıtlamaktadır."
        Sadece <p class="news-content"> paragrafları içinde temizleme yapılır.
        """
        import re

        # Yorum cümlesini tanıyan regex
        COMMENTARY_RE = re.compile(
            r'\s+Bu\s+(?:olay|saldırı|gelişme|vaka|durum|yaklaşım|metodoloji|uygulama|süreç|tür\s+\w+|çift\s+\w+|'
            r'siber|tehdit|grup|operasyon|kampanya|teknik|yöntem|strateji|rapor|bulgu|durum|ihlal)[^<.]{0,400}?'
            r'(?:göstermektedir|ortaya koymaktadır|vurgulamaktadır|kanıtlamaktadır|taşımaktadır|'
            r'gözler önüne sermektedir|açıkça ortaya çıkmaktadır)\s*\.'
            r'|'
            r'\s+[^<.]{0,200}?bir kez daha[^<.]{0,150}?'
            r'(?:göstermektedir|vurgulamaktadır|ortaya koymaktadır|kanıtlamaktadır)\s*\.',
            re.IGNORECASE | re.DOTALL
        )

        cleaned_count = 0

        def process_paragraph(m):
            nonlocal cleaned_count
            content = m.group(1)
            cleaned = COMMENTARY_RE.sub('', content).strip()
            # Çift boşlukları temizle
            cleaned = re.sub(r'  +', ' ', cleaned)
            if cleaned != content:
                cleaned_count += 1
            return f'<p class="news-content">{cleaned}</p>'

        fixed = re.sub(
            r'<p class="news-content">(.*?)</p>',
            process_paragraph,
            html,
            flags=re.DOTALL
        )

        if cleaned_count > 0:
            print(f"   ✅ {cleaned_count} paragraftan yorum cümlesi temizlendi")
        return fixed

    def _add_archive_links(self, html, is_archive=False):
        """HTML'e son 30 günün linklerini ekle"""

        reports = []
        for i in range(30):
            date = datetime.now() - timedelta(days=i)
            filepath = f"docs/raporlar/{date.strftime('%Y-%m-%d')}.html"
            if os.path.exists(filepath):
                reports.append({
                    'date': date.strftime('%d.%m.%Y'),
                    'filename': date.strftime('%Y-%m-%d')
                })

        if not reports:
            print("   ℹ️  Henüz arşiv yok (ilk gün)")
            return html

        link_prefix = "./" if is_archive else "./raporlar/"

        archive_html = """
    <div class="archive-section">
        <h3>📚 Arşiv - Son 30 Gün</h3>
        <div class="archive-links">
"""
        for report in reports:
            archive_html += f'            <a href="{link_prefix}{report["filename"]}.html" class="archive-link">{report["date"]}</a>\n'

        archive_html += """        </div>
    </div>
"""

        if '</body>' in html:
            html = html.replace('</body>', archive_html + '\n</body>')
        elif '</html>' in html:
            html = html.replace('</html>', archive_html + '\n</html>')
        else:
            html += archive_html

        print(f"   ✅ {len(reports)} günlük arşiv linki eklendi")
        return html

    def _generate_html_with_openrouter(self, txt_content):
        """OpenRouter (Qwen 3.6 Plus) ile HTML oluştur — Gemini fallback'i"""
        print("🤖 OpenRouter API (Qwen 3.6 Plus)...")
        if not OPENROUTER_API_KEY:
            print("   ⚠️  OPENROUTER_API_KEY yok — fallback HTML oluşturuluyor.")
            return None

        try:
            client = OpenAIClient(
                api_key=OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1"
            )

            max_attempts = 3
            html = None

            for attempt in range(max_attempts):
                try:
                    print(f"   Deneme {attempt + 1}/{max_attempts} [qwen-3.6-plus-preview]...")

                    prompt = get_claude_prompt(txt_content)

                    # Streaming ile cevap al
                    chunks = []
                    with client.chat.completions.create(
                        model="qwen/qwen3.6-plus-preview:free",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=65536,
                        temperature=0.7,
                        stream=True
                    ) as stream:
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                chunks.append(chunk.choices[0].delta.content)

                    html = ''.join(chunks)

                    if not html or len(html) < 100:
                        raise Exception("Stream boş döndü")

                    print("   ✅ OpenRouter başarılı!")
                    break

                except Exception as e:
                    error_msg = str(e)
                    print(f"   ⚠️  Hata: {error_msg[:100]}")

                    if attempt < max_attempts - 1:
                        wait_time = min(10 * (2 ** attempt), 60)  # 10s, 20s, 60s
                        print(f"   ⏳ {wait_time}s bekleniyor...")
                        time.sleep(wait_time)

            if html:
                # HTML temizle
                import re as _re_html
                doctype_pos = html.lower().find('<!doctype html')
                html_tag_pos = html.lower().find('<html')
                candidates = [p for p in [doctype_pos, html_tag_pos] if p != -1]
                if candidates:
                    html_start = min(candidates)
                    if html_start > 0:
                        print(f"   ⚠️  HTML öncesi metin temizlendi ({html_start} karakter preamble)")
                    html = html[html_start:]
                html = _re_html.sub(r'\s*```\s*$', '', html).strip()

                print(f"✅ OpenRouter HTML oluşturuldu ({len(html)} karakter)")
                return html
            else:
                print(f"   ❌ {max_attempts} deneme başarısız")
                return None

        except Exception as e:
            print(f"   ❌ OpenRouter hatası: {str(e)[:100]}")
            return None

    def _create_fallback_html(self, txt_content, error_type=None, error_message=None):
        """Gemini API başarısız olursa — hata detaylarını içeren fallback HTML"""
        now = datetime.now()

        if error_type or error_message:
            import html as _html_escape
            safe_type = _html_escape.escape(str(error_type or 'Bilinmiyor'))
            safe_msg  = _html_escape.escape(str(error_message or 'Bilinmiyor'))
            error_section = f"""
    <div class="error-box">
        <h2>⚠️ Gemini API Hata Detayları</h2>
        <table class="error-table">
            <tr><th>Hata Türü</th><td><code>{safe_type}</code></td></tr>
            <tr><th>Hata Mesajı</th><td><code>{safe_msg}</code></td></tr>
            <tr><th>Oluşma Zamanı</th><td>{now.strftime('%d.%m.%Y %H:%M:%S')}</td></tr>
            <tr><th>Deneme Sayısı</th><td>5 deneme / 3 model (bu çalışmada) — tümü başarısız; 1 saat sonra yeniden denenecek</td></tr>
        </table>
    </div>"""
        else:
            error_section = ""

        html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Siber Güvenlik Raporu - {now.strftime('%d %B %Y')} [FALLBACK]</title>
    <style>
        body {{ font-family: system-ui, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        .header {{ background: #1e3c72; color: white; padding: 40px; border-radius: 10px; margin-bottom: 20px; }}
        .header h1 {{ margin: 0 0 10px 0; }}
        .header p {{ margin: 4px 0; opacity: 0.9; }}
        .error-box {{ background: #fff3cd; border: 2px solid #ffc107; border-radius: 10px; padding: 24px 30px; margin-bottom: 20px; }}
        .error-box h2 {{ color: #856404; margin: 0 0 16px 0; font-size: 18px; }}
        .error-table {{ width: 100%; border-collapse: collapse; }}
        .error-table th {{ text-align: left; padding: 8px 12px; background: #ffeeba; color: #533f03; width: 180px; font-size: 14px; }}
        .error-table td {{ padding: 8px 12px; font-size: 14px; }}
        .error-table tr {{ border-bottom: 1px solid #ffd875; }}
        .error-table code {{ background: #fff; border: 1px solid #ddd; border-radius: 3px; padding: 2px 6px; font-size: 13px; word-break: break-all; }}
        .content {{ background: white; padding: 40px; border-radius: 10px; white-space: pre-wrap; font-size: 13px; line-height: 1.5; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔒 Siber Güvenlik Günlük Raporu</h1>
        <p>{now.strftime('%d %B %Y')}</p>
        <p>⚠️ Gemini API yanıt vermedi — 1 saat sonra otomatik yeniden denenecek</p>
    </div>
    {error_section}
    <div class="content">{txt_content}</div>
</body>
</html>"""

        os.makedirs("docs/raporlar", exist_ok=True)
        with open("docs/index.html", 'w', encoding='utf-8') as f:
            f.write(html)
        with open(f"docs/raporlar/{now.strftime('%Y-%m-%d')}.html", 'w', encoding='utf-8') as f:
            f.write(html)

        print("✅ Fallback HTML oluşturuldu (hata detayları dahil)")
        return html

    def _cleanup_old_reports(self):
        """30 günden eski raporları sil"""
        import glob

        cutoff = datetime.now() - timedelta(days=30)
        deleted = 0

        for filepath in glob.glob("docs/raporlar/*.html"):
            try:
                filename = os.path.basename(filepath)
                if filename == '.gitkeep':
                    continue

                date_str = filename.replace('.html', '')
                file_date = datetime.strptime(date_str, '%Y-%m-%d')

                if file_date < cutoff:
                    os.remove(filepath)
                    deleted += 1
            except:
                pass

        if deleted > 0:
            print(f"🗑️  {deleted} eski rapor silindi (30+ gün)")
        else:
            print("📁 Arşiv temiz (30 gün içinde)")


def main():
    print("\n" + "=" * 70)
    print("🔒 SİBER GÜVENLİK HABERLERİ")
    print("=" * 70)
    print(f"📅 {datetime.now().strftime('%d %B %Y %H:%M')}")
    print("=" * 70 + "\n")

    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    today_report = f"docs/raporlar/{today_str}.html"
    ham_txt_path = "data/haberler_ham.txt"

    # ── Kontrol 1: Başarılı rapor zaten var mı? ────────────────────────────
    # Fallback içermeyen bir rapor mevcutsa hiçbir şey yapma.
    if os.path.exists(today_report):
        try:
            with open(today_report, encoding='utf-8') as f:
                report_content = f.read()
            if '[FALLBACK]' not in report_content and 'error-box' not in report_content:
                print(f"✅ Bugünün başarılı raporu zaten mevcut: {today_report}")
                print("   Yeniden oluşturma atlanıyor.")
                return 0
            else:
                print("⚠️  Bugünün raporu fallback — Gemini yeniden denenecek.")
        except Exception:
            pass  # Okuma hatası varsa devam et

    # ── Kontrol 2: Ham haber verisi bugüne ait mi? ─────────────────────────
    # Eğer bugün zaten haber çekildiyse (ama Gemini başarısız olduysa),
    # kaynaklara tekrar gitme — haberler_linkler.txt tüm haberleri
    # "görüldü" olarak işaretlediğinden sıfır haber döner.
    #
    # ÖNEMLİ: os.path.getmtime() kullanılmıyor — git checkout tüm dosyalara
    # o anki zamanı damgalar, dolayısıyla dünkü ham.txt de "bugün" gibi görünür.
    # Bunun yerine dosyanın içindeki SESSION_DATE satırı kontrol ediliyor.
    ham_exists_for_today = False
    if os.path.exists(ham_txt_path):
        try:
            with open(ham_txt_path, encoding='utf-8') as _f:
                first_line = _f.readline().strip()
            if first_line == f"SESSION_DATE: {today_str}":
                ham_exists_for_today = True
        except Exception:
            pass

    sistem = HaberSistemi()

    if ham_exists_for_today:
        print("📄 Bugünün ham haberleri mevcut — haber çekme atlanıyor, sadece Gemini çalıştırılıyor.")
        # topla() atlandığından social_data boş kalır — ayrıca çek
        print("📡 Sosyal medya sinyalleri çekiliyor...")
        sistem.social_data = fetch_social_signals(SOCIAL_SIGNAL_CONFIG)
        try:
            with open(ham_txt_path, encoding='utf-8') as f:
                txt = f.read()
        except Exception as e:
            print(f"❌ Ham TXT okunamadı: {e}")
            return 1
    else:
        # 1. Topla
        haberler = sistem.topla()
        if not haberler:
            print("❌ Haber yok!")
            return 1

        # 2. TXT
        txt = sistem.save_txt(haberler)

    # 3. HTML (Gemini)
    sistem.create_html(txt)

    print("\n" + "=" * 70)
    print("✨ TAMAMLANDI!")
    print("=" * 70)
    print("🌐 https://siberguvenlikhaberler.github.io/siberguvenlik/")
    print("=" * 70 + "\n")

    return 0


if __name__ == "__main__":
    exit(main())
