"""
Vercel serverless fonksiyonu — Manuel Haber Ekle uç noktası (/api/manual-add).

TAMAMEN SUNUCU TARAFINDA çalışır. Anasayfadaki pop-up buraya POST eder:
    { "password": "...", "url": "https://...", "remove_index": 0|1|2 }

Yapılan iş:
  1. Şifre (MANUAL_ADD_PASSWORD env) sunucuda doğrulanır.
  2. URL çekilir, makale metni çıkarılır.
  3. BİZİM sistemin promptu (src.config.get_deep_analysis_prompt) + LLM istemcisi
     (src.llm_client) ile, raporun geri kalanıyla BİREBİR aynı yöntem/format/üslupta
     Türkçe başlık + paragraf üretilir.
  4. main.py'deki kritik-kart kalıbının AYNISIYLA bir <div class="top3-card"> üretilir.
  5. docs/index.html VE o günün arşiv raporunda (docs/raporlar/YYYY-MM-DD.html)
     YALNIZCA işaretlenen kritik kart değiştirilir — başka hiçbir şey değişmez.
  6. Her iki dosya GitHub API ile main'e commit edilir.
  7. Üretilen kart HTML'i tarayıcıya döner; pop-up sayfadaki kartı anında değiştirir.

Gerekli ortam değişkenleri (Vercel):
  OPENROUTER_API_KEY   — LLM çağrısı (Actions'taki ile aynı)
  LLM_PROVIDER         — "openrouter"
  MANUAL_ADD_PASSWORD  — pop-up'ta girilecek şifre
  GH_TOKEN             — bu repo'ya contents:write yetkili GitHub token (commit için)
"""
import os
import re
import sys
import json
import base64
import hmac
import socket
import ipaddress
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

# Repo kökünü import yoluna ekle (src/ paketine erişim için)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
from bs4 import BeautifulSoup

from src.config import HEADERS, get_deep_analysis_prompt, get_executive_summary_prompt
from src import llm_client
from src.http_utils import requests_get_with_retry

REPO = "siberguvenlikhaberler/siberguvenlik"
BRANCH = "main"
GH_API = "https://api.github.com"
INDEX_PATH = "docs/index.html"

# Tarayıcı (github.io) → fonksiyon (vercel.app) çapraz-köken istekleri için CORS.
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


# ─────────────────────────────────────────────────────────────────────────────
# Makale metni çekme (main.py: HaberSistemi.fetch_full_article mantığının
# tek-iş parçacıklı, genel-seçicili sadeleştirilmiş kopyası)
# ─────────────────────────────────────────────────────────────────────────────
def assert_public_url(url):
    """SSRF koruması: URL şemasını ve çözümlenen TÜM IP'leri doğrular.

    Uç nokta şifre korumalı olsa bile, kullanıcı verdiği URL sunucu tarafında
    çekildiğinden iç ağ / bulut metadata uçları (169.254.169.254 vb.) hedef
    alınabilir. Bu yüzden yalnızca http/https'e ve PUBLIC (özel/loopback/
    link-local/reserved olmayan) IP'lere izin verilir. Sorun varsa ValueError.
    """
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError("Yalnızca http/https URL'lerine izin verilir.")
    host = parsed.hostname
    if not host:
        raise ValueError("URL host bilgisi yok.")
    try:
        infos = socket.getaddrinfo(host, parsed.port or 0, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise ValueError(f"Host çözümlenemedi: {e}")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            raise ValueError("Özel/iç ağ adreslerine istek yapılamaz.")


def fetch_article(url):
    assert_public_url(url)
    r = requests_get_with_retry(url, headers=HEADERS, timeout=(5, 12), stream=True)
    chunks, total = [], 0
    for chunk in r.iter_content(chunk_size=8192):
        chunks.append(chunk)
        total += len(chunk)
        if total > 800_000:
            break
    r.close()
    raw = b"".join(chunks).decode(r.encoding or "utf-8", errors="replace")
    soup = BeautifulSoup(raw, "html.parser")
    domain = urlparse(url).netloc.replace("www.", "")

    # Gövde metnini kirleten yapısal öğeleri en baştan ayıkla (nav/menü/altbilgi
    # vb.). Bunlar kalırsa "20+ karakter" filtresini geçen menü/footer bağlantıları
    # metne karışıp hem gürültü yapar hem de yanlış öğenin seçilmesine yol açar.
    for junk in soup.find_all(["script", "style", "noscript", "nav", "header",
                               "footer", "aside", "form"]):
        junk.decompose()

    _SKIP = ("cookie", "subscribe", "newsletter", "abone ol", "çerez",
             "gizlilik politika", "tüm hakları", "all rights reserved",
             "advertisement", "reklam")

    def _extract(element):
        if not element:
            return ""
        parts, seen = [], set()
        for p in element.find_all(["p", "h1", "h2", "h3", "h4", "li", "blockquote"]):
            t = " ".join(p.get_text().split())  # iç boşlukları normalize et
            if len(t) <= 20 or any(x in t.lower() for x in _SKIP):
                continue
            if t in seen:  # tekrar eden öğeleri (ör. iki kez basılmış başlık) atla
                continue
            seen.add(t)
            parts.append(t)
        return "\n\n".join(parts)

    # 1) Anlamsal ana içerik etiketleri
    text = ""
    for tag in ["article", "main"]:
        el = soup.find(tag)
        if el:
            text = _extract(el)
            if len(text.split()) >= 50:
                break

    # 2) Sık kullanılan içerik kapsayıcıları: class VEYA id'de tipik kalıplar,
    #    div dışında section/figure gibi etiketleri de kapsar. Birden çok aday
    #    bulunursa EN UZUN metni veren seçilir (gövde genelde en zengin bloktur).
    if len(text.split()) < 50:
        _PAT = ("content", "article", "article-body", "story", "entry",
                "post", "haber", "icerik", "metin", "detay", "main-text",
                "news-body", "body-text", "text-body")

        def _looks_like_content(val):
            return val and any(x in str(val).lower() for x in _PAT)

        candidates = soup.find_all(
            ["div", "section"],
            attrs={"class": _looks_like_content},
        ) + soup.find_all(
            ["div", "section"],
            attrs={"id": _looks_like_content},
        )
        best = text
        for el in candidates:
            cand = _extract(el)
            if len(cand.split()) > len(best.split()):
                best = cand
        text = best

    # 3) Son çare: tüm sayfadaki <p>'ler (yapısı kalıba uymayan siteler için)
    if len(text.split()) < 50:
        fallback = _extract(soup.body or soup)
        if len(fallback.split()) > len(text.split()):
            text = fallback

    # 4) Hâlâ kısaysa meta açıklama/og:description ile destekle — JS ile render
    #    edilen sayfalarda en azından özet metni yakalamayı sağlar.
    if len(text.split()) < 50:
        metas = []
        for attr, key in (("name", "description"), ("property", "og:description"),
                          ("name", "twitter:description")):
            m = soup.find("meta", attrs={attr: key})
            if m and m.get("content"):
                metas.append(" ".join(m["content"].split()))
        if metas:
            text = (text + "\n\n" + "\n\n".join(metas)).strip()

    text = text.replace("\t", " ").replace("\r", "")
    return text, domain


# ─────────────────────────────────────────────────────────────────────────────
# LLM ile başlık + paragraf üretimi — raporun geri kalanıyla AYNI prompt/format
# ─────────────────────────────────────────────────────────────────────────────
def generate_content(url, full_text, report_date):
    block = (
        f"=== HABER ID: 1 ===\n"
        f"Kaynak: Manuel\n"
        f"Başlık: \n"
        f"Tarih: {report_date}\n"
        f"Link: {url}\n\n"
        f"TAM METİN:\n{full_text}\n"
    )
    model = os.getenv("OPENROUTER_MODEL", "") or "google/gemini-3-flash-preview (varsayılan)"
    data = llm_client.generate_json(
        get_deep_analysis_prompt(block),
        max_output_tokens=4096,
        label="ManuelEkle",
    )
    if not data:
        return None, None, (
            f"LLM yanıt döndürmedi. OPENROUTER_API_KEY geçerli mi ve "
            f"OPENROUTER_MODEL ('{model}') hesabında erişilebilir mi? "
            f"(Vercel env + redeploy gerekir.)"
        )

    # LLM çıktısı farklı biçimlerde gelebilir; hepsini özyinelemeli tara:
    #   {tr_title, paragraph}
    #   {"1": {tr_title, paragraph}}
    #   [{tr_title, paragraph}]
    #   [{"1": {tr_title, paragraph}}]   ← gözlemlenen biçim
    # İlk geçerli (tr_title/paragraph içeren) sözlük kabul edilir.
    def _find_entry(node, depth=0):
        if depth > 6:
            return None
        if isinstance(node, dict):
            if "tr_title" in node or "paragraph" in node:
                return node
            for v in node.values():
                found = _find_entry(v, depth + 1)
                if found:
                    return found
        elif isinstance(node, list):
            for v in node:
                found = _find_entry(v, depth + 1)
                if found:
                    return found
        return None

    entry = _find_entry(data)
    if not entry:
        preview = list(data)[:5] if isinstance(data, (dict, list)) else str(data)[:160]
        return None, None, f"LLM beklenmeyen biçim döndürdü: {preview}"
    return (entry.get("tr_title") or "").strip(), (entry.get("paragraph") or "").strip(), None


# ─────────────────────────────────────────────────────────────────────────────
# Kritik kart HTML'i — main.py:1275 kalıbının BİREBİR aynısı (NATO rozeti yok)
# ─────────────────────────────────────────────────────────────────────────────
def build_card_html(tr_title, paragraph, link, domain, art_date):
    return (
        '                <div class="top3-card">\n'
        '                    <div class="top3-card-title">'
        f'<a href="{link}" target="_blank" style="color:inherit;text-decoration:none;">'
        f"{tr_title}</a></div>\n"
        f'                    <p class="top3-card-paragraph">{paragraph}</p>\n'
        '                    <p class="source"><b>(XXXXXXX, AÇIK - '
        f'<a href="{link}" target="_blank">{domain}</a>, {art_date})</b></p>\n'
        "                </div>\n"
    )


# NOT: main.py:create_html kart şablonu 16 boşluk girintiyle üretir; ancak
# girinti ileride değişirse regex SESSİZCE kırılmasın diye baştaki/kapanıştaki
# boşluk esnek bırakıldı ([ \t]*). Kapanış </div> kendi satırında olmalıdır.
_CARD_RE = re.compile(
    r'[ \t]*<div class="top3-card">.*?\n[ \t]*</div>\n',
    re.DOTALL,
)


# Rapordaki "diğer haber" (.news-item) bloğu — _CARD_RE ile aynı mantık: dış
# <div> kapanışı KENDİ satırında (indentasyonlu) olduğundan, news-title'ın
# satır-içi </div>'i değil, dış kapanış yakalanır. id'ye göre tekil eşleşir.
def _news_item_re(news_id):
    return re.compile(
        r'[ \t]*<div class="news-item[^"]*" id="' + re.escape(news_id) + r'">'
        r'.*?\n[ \t]*</div>\n',
        re.DOTALL,
    )


def extract_news_item(html, news_id):
    """Verilen news-item bloğundan (tr_title, paragraph, link, domain, art_date) çıkarır.

    Yalnızca eşleşen FRAGMAN BeautifulSoup ile parse edilir; tüm döküman yeniden
    serialize EDİLMEZ (mevcut format/diff korunur).
    """
    m = _news_item_re(news_id).search(html)
    if not m:
        raise ValueError("haber bloğu bulunamadı")
    frag = BeautifulSoup(m.group(0), "html.parser")
    title_el = frag.find(class_="news-title")
    content_el = frag.find(class_="news-content")
    source_el = frag.find(class_="source")

    tr_title = title_el.get_text(" ", strip=True) if title_el else ""
    paragraph = content_el.decode_contents().strip() if content_el else ""
    link = domain = art_date = ""
    if source_el:
        a = source_el.find("a")
        if a:
            link = a.get("href", "")
            domain = a.get_text(strip=True)
        dm = re.search(r"\d{2}\.\d{2}\.\d{4}", source_el.get_text())
        if dm:
            art_date = dm.group(0)
    if not tr_title or not paragraph:
        raise ValueError("başlık/metin çıkarılamadı")
    return tr_title, paragraph, link, domain, art_date


def remove_news_item(html, news_id):
    """news-item bloğunu ve (varsa) yönetici tablosundaki ilgili satırı kaldırır.

    Yönetici tablosu satırı best-effort silinir; bulunamazsa sessizce geçilir.
    """
    new_html = _news_item_re(news_id).sub("", html, count=1)
    row_re = re.compile(
        r'[ \t]*<tr>\s*<td><a href="#' + re.escape(news_id) + r'">.*?</a></td>\s*</tr>\n',
        re.DOTALL,
    )
    new_html = row_re.sub("", new_html, count=1)
    return new_html


def replace_top3_card(html, index, new_card_html):
    matches = list(_CARD_RE.finditer(html))
    if len(matches) < 3:
        raise ValueError(f"Beklenen 3 kritik kart bulunamadı (bulunan: {len(matches)}).")
    if index < 0 or index >= len(matches):
        raise ValueError("Geçersiz kart indeksi.")
    m = matches[index]
    return html[: m.start()] + new_card_html + html[m.end():]


def report_date_from_html(html):
    """index.html <title>'ından rapor tarihini çıkarır → (dd.mm.yyyy, arşiv yolu)."""
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", html)
    if not m:
        raise ValueError("Rapor tarihi index.html içinde bulunamadı.")
    dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
    return f"{dd}.{mm}.{yyyy}", f"docs/raporlar/{yyyy}-{mm}-{dd}.html"


# ─────────────────────────────────────────────────────────────────────────────
# Yönetici Özeti senkronizasyonu
#
# Sorun: bir kritik kart takas edildiğinde (URL ile yeni haber VEYA rapordan
# taşıma) #yonetici-ozeti-block içindeki özet paragrafı dokunulmadan kaldığı
# için çıkarılan habere değinmeye devam eder, yeni haberden hiç söz etmez.
#
# Çözüm: takas HTML'e uygulandıktan SONRA, güncel sayfadan main.py:Pass6 ile
# AYNI kaynak kümesini (3 kritik kart + belge sırasındaki ilk 6 normal haber)
# toplayıp get_executive_summary_prompt ile paragrafı bütün olarak yeniden üret;
# yalnızca .exec-brief-paragraph içeriğini değiştir. LLM başarısız olursa
# main.py'deki deterministik başlık-tabanlı yedeğin aynısıyla doldur — böylece
# bayat/yanlış metin asla kalmaz.
# ─────────────────────────────────────────────────────────────────────────────
_EXEC_BRIEF_PARA_RE = re.compile(
    r'(<p class="exec-brief-paragraph">).*?(</p>)', re.DOTALL
)


def _collect_exec_sources(html):
    """Güncel HTML'den özet kaynak kümesini (en fazla 9 kalem) çıkarır.

    main.py:Pass6 mantığı: 3 kritik kart (top3) + belge sırasındaki ilk 6 normal
    haber (.news-item). Her kalem (tr_title, snippet) olarak döner.
    """
    soup = BeautifulSoup(html, "html.parser")
    items = []

    for card in soup.select(".top3-card"):
        title_el = card.find(class_="top3-card-title")
        para_el = card.find(class_="top3-card-paragraph")
        tr_title = title_el.get_text(" ", strip=True) if title_el else ""
        paragraph = para_el.get_text(" ", strip=True) if para_el else ""
        if tr_title:
            items.append((tr_title, paragraph))

    regular = 0
    for ni in soup.select(".news-item"):
        if regular >= 6:
            break
        title_el = ni.find(class_="news-title")
        para_el = ni.find(class_="news-content")
        tr_title = title_el.get_text(" ", strip=True) if title_el else ""
        paragraph = para_el.get_text(" ", strip=True) if para_el else ""
        if tr_title:
            items.append((tr_title, paragraph))
            regular += 1

    return items


def _deterministic_exec_summary(items):
    """LLM başarısızsa main.py:Pass6 yedeğinin aynısı — başlıklardan tek paragraf."""
    titles = [t.strip().rstrip(".") for t, _ in items if t and t.strip()]
    if not titles:
        return ""
    lead = ("Son 48 saatin siber güvenlik gündeminde öne çıkan "
            "başlıca gelişmeler şunlardır: ")
    return lead + "; ".join(titles[:8]) + "."


def regenerate_exec_summary(html):
    """Güncel HTML'e göre Yönetici Özeti paragrafını yeniden üretir.

    .exec-brief-paragraph içeriği yeni özetle değiştirilmiş HTML döner. Özet
    bloğu yoksa veya kaynak çıkmıyorsa HTML değiştirilmeden döner (best-effort).
    """
    if not _EXEC_BRIEF_PARA_RE.search(html):
        return html  # Bu raporda Yönetici Özeti kutusu yok → dokunma.

    items = _collect_exec_sources(html)
    if not items:
        return html

    es_lines = []
    for i, (tr_title, paragraph) in enumerate(items, 1):
        snippet = " ".join(paragraph.split()[:90])
        es_lines.append(
            f"=== HABER {i} ===\n"
            f"Başlık: {tr_title}\n"
            f"Özet: {snippet}\n"
        )

    # main.py:Pass6 ile aynı: tek geçici hatada özet kaybolmasın diye 3 deneme.
    exec_summary = ""
    if os.getenv("OPENROUTER_API_KEY", ""):
        for attempt in range(3):
            try:
                data = llm_client.generate_json(
                    get_executive_summary_prompt("\n".join(es_lines)),
                    max_output_tokens=1024,
                    label=f"ManuelEkle-YoneticiOzeti(d{attempt + 1})",
                )
            except Exception:
                data = None
            if data and isinstance(data.get("ozet"), str) and data["ozet"].strip():
                exec_summary = data["ozet"].strip()
                break

    # Deterministik yedek — LLM yok/başarısız olsa bile bayat metin kalmaz.
    if not exec_summary:
        exec_summary = _deterministic_exec_summary(items)
    if not exec_summary:
        return html

    # HTML kaçışı: özet metni HTML gövdesine düz metin olarak girer; <, &
    # karakterleri kaçırılmazsa sayfayı bozabilir.
    safe = exec_summary.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return _EXEC_BRIEF_PARA_RE.sub(
        lambda m: m.group(1) + safe + m.group(2), html, count=1
    )


# ─────────────────────────────────────────────────────────────────────────────
# GitHub Contents API yardımcıları
# ─────────────────────────────────────────────────────────────────────────────
def _gh_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def gh_get_file(path, token):
    r = requests.get(
        f"{GH_API}/repos/{REPO}/contents/{path}",
        headers=_gh_headers(token),
        params={"ref": BRANCH},
        timeout=30,
    )
    r.raise_for_status()
    j = r.json()
    content = base64.b64decode(j["content"]).decode("utf-8")
    return content, j["sha"]


def gh_put_file(path, new_content, sha, token, message):
    r = requests.put(
        f"{GH_API}/repos/{REPO}/contents/{path}",
        headers=_gh_headers(token),
        json={
            "message": message,
            "content": base64.b64encode(new_content.encode("utf-8")).decode("ascii"),
            "sha": sha,
            "branch": BRANCH,
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def gh_commit_files(files, token, message):
    """Birden çok dosyayı TEK commit'te ATOMİK yazar (Git Data API).

    files: [(path, content_str), ...]. Contents API ile dosya-dosya commit
    yapıldığında index güncellenip arşiv güncellenmeden hata olursa tutarsız
    durum doğardı. Tek tree + tek commit ile ya hepsi ya hiçbiri uygulanır.
    """
    h = _gh_headers(token)
    base = f"{GH_API}/repos/{REPO}/git"

    r = requests.get(f"{base}/ref/heads/{BRANCH}", headers=h, timeout=30)
    r.raise_for_status()
    base_commit_sha = r.json()["object"]["sha"]

    r = requests.get(f"{base}/commits/{base_commit_sha}", headers=h, timeout=30)
    r.raise_for_status()
    base_tree_sha = r.json()["tree"]["sha"]

    tree = []
    for path, content in files:
        r = requests.post(
            f"{base}/blobs", headers=h, timeout=30,
            json={"content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                  "encoding": "base64"},
        )
        r.raise_for_status()
        tree.append({"path": path, "mode": "100644", "type": "blob", "sha": r.json()["sha"]})

    r = requests.post(
        f"{base}/trees", headers=h, timeout=30,
        json={"base_tree": base_tree_sha, "tree": tree},
    )
    r.raise_for_status()
    new_tree_sha = r.json()["sha"]

    r = requests.post(
        f"{base}/commits", headers=h, timeout=30,
        json={"message": message, "tree": new_tree_sha, "parents": [base_commit_sha]},
    )
    r.raise_for_status()
    new_commit_sha = r.json()["sha"]

    r = requests.patch(
        f"{base}/refs/heads/{BRANCH}", headers=h, timeout=30,
        json={"sha": new_commit_sha, "force": False},
    )
    r.raise_for_status()
    return r.json()


# ─────────────────────────────────────────────────────────────────────────────
# Çekirdek iş akışı
# ─────────────────────────────────────────────────────────────────────────────
def process(payload):
    """Ortak doğrulama + moda göre dallanma.

    mode = "url"    → URL'den LLM ile yeni haber üret (mevcut akış).
    mode = "report" → rapordaki diğer bir haberi kritik karta TAŞI (URL/LLM yok).
    Geriye dönük uyum: mode yoksa ama url varsa "url" kabul edilir.
    """
    password = (payload.get("password") or "")
    mode = (payload.get("mode") or "").strip().lower()
    if not mode:
        mode = "url" if (payload.get("url") or "").strip() else ""

    expected = os.getenv("MANUAL_ADD_PASSWORD", "")
    if not expected:
        return 500, {"error": "Sunucuda MANUAL_ADD_PASSWORD tanımlı değil."}
    if not hmac.compare_digest(password, expected):
        return 401, {"error": "Şifre hatalı."}

    try:
        remove_index = int(payload.get("remove_index"))
    except (TypeError, ValueError):
        return 400, {"error": "Geçersiz remove_index."}
    if remove_index not in (0, 1, 2):
        return 400, {"error": "Çıkarılacak haber 0-2 aralığında olmalı."}

    token = os.getenv("GH_TOKEN", "")
    if not token:
        return 500, {"error": "Sunucuda GH_TOKEN tanımlı değil."}

    if mode == "report":
        return process_report(payload, remove_index, token)
    if mode == "url":
        return process_url(payload, remove_index, token)
    return 400, {"error": "Geçersiz mod."}


def process_report(payload, remove_index, token):
    """Rapordaki bir 'diğer haber'i kritik karta TAŞI: kritik kartı değiştir,
    seçilen haberi alt listeden (ve yönetici tablosundan) kaldır. URL/LLM yok."""
    news_id = (payload.get("news_id") or "").strip()
    if not re.match(r"^haber-\d+$", news_id):
        return 400, {"error": "Geçersiz haber kimliği."}

    try:
        index_html, _ = gh_get_file(INDEX_PATH, token)
        report_date, archive_path = report_date_from_html(index_html)
    except Exception as e:
        return 502, {"error": f"index.html okunamadı: {str(e)[:160]}"}

    try:
        tr_title, paragraph, link, domain, art_date = extract_news_item(index_html, news_id)
    except Exception as e:
        return 422, {"error": f"Seçilen haber çıkarılamadı: {str(e)[:160]}"}

    card_html = build_card_html(tr_title, paragraph, link, domain, art_date or report_date)
    try:
        new_index = replace_top3_card(index_html, remove_index, card_html)
        new_index = remove_news_item(new_index, news_id)
        # Takas sonrası Yönetici Özeti'ni güncel kart kümesine göre yeniden üret.
        new_index = regenerate_exec_summary(new_index)
    except Exception as e:
        return 500, {"error": f"index.html güncellenemedi: {str(e)[:160]}"}

    try:
        archive_html, _ = gh_get_file(archive_path, token)
        new_archive = remove_news_item(
            replace_top3_card(archive_html, remove_index, card_html), news_id
        )
        new_archive = regenerate_exec_summary(new_archive)
    except Exception:
        # Arşiv dosyası yoksa/okunamıyorsa yalnızca index güncellenir.
        new_archive = None

    msg = f"manuel: kritik haber rapordan taşındı ({report_date})"
    files = [(INDEX_PATH, new_index)]
    if new_archive is not None:
        files.append((archive_path, new_archive))
    try:
        gh_commit_files(files, token, msg)
    except Exception as e:
        return 502, {"error": f"Commit başarısız: {str(e)[:160]}"}

    return 200, {
        "ok": True,
        "card_html": card_html,
        "removed_news_id": news_id,
        "tr_title": tr_title,
        "domain": domain,
        "date": report_date,
    }


def process_url(payload, remove_index, token):
    url = (payload.get("url") or "").strip()
    if not re.match(r"^https?://", url, re.IGNORECASE):
        return 400, {"error": "Geçerli bir URL giriniz."}
    if not os.getenv("OPENROUTER_API_KEY", ""):
        return 500, {"error": "Sunucuda OPENROUTER_API_KEY tanımlı değil."}

    # 1) Makaleyi çek
    try:
        full_text, domain = fetch_article(url)
    except Exception as e:
        return 502, {"error": f"URL çekilemedi: {str(e)[:160]}"}
    if not full_text or len(full_text.split()) < 50:
        return 422, {"error": "Makale metni çıkarılamadı veya çok kısa."}

    # 2) index.html + tarih + arşiv yolu
    try:
        index_html, index_sha = gh_get_file(INDEX_PATH, token)
        report_date, archive_path = report_date_from_html(index_html)
    except Exception as e:
        return 502, {"error": f"index.html okunamadı: {str(e)[:160]}"}

    # 3) BİZİM formatımızda içerik üret
    try:
        tr_title, paragraph, gen_err = generate_content(url, full_text, report_date)
    except Exception as e:
        return 502, {"error": f"İçerik üretilemedi: {str(e)[:200]}"}
    if not tr_title or not paragraph:
        return 502, {"error": gen_err or "LLM geçerli başlık/paragraf döndürmedi."}

    # 4) Kartı kur ve her iki dosyada ilgili kartı değiştir
    card_html = build_card_html(tr_title, paragraph, url, domain, report_date)
    try:
        new_index = replace_top3_card(index_html, remove_index, card_html)
        # Takas sonrası Yönetici Özeti'ni güncel kart kümesine göre yeniden üret.
        new_index = regenerate_exec_summary(new_index)
    except Exception as e:
        return 500, {"error": f"index.html kart değişimi başarısız: {str(e)[:160]}"}

    archive_html = archive_sha = None
    try:
        archive_html, archive_sha = gh_get_file(archive_path, token)
        new_archive = replace_top3_card(archive_html, remove_index, card_html)
        new_archive = regenerate_exec_summary(new_archive)
    except Exception:
        # Arşiv dosyası yoksa/okunamıyorsa yalnızca index güncellenir.
        new_archive = None

    # 5) Commit — index + (varsa) arşiv TEK atomik commit'te yazılır.
    msg = f"manuel: kritik haber güncellendi ({report_date})"
    files = [(INDEX_PATH, new_index)]
    if new_archive is not None:
        files.append((archive_path, new_archive))
    try:
        gh_commit_files(files, token, msg)
    except Exception as e:
        return 502, {"error": f"Commit başarısız: {str(e)[:160]}"}

    return 200, {
        "ok": True,
        "card_html": card_html,
        "tr_title": tr_title,
        "domain": domain,
        "date": report_date,
    }


class handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            self._send(400, {"error": "Geçersiz istek gövdesi."})
            return
        try:
            code, result = process(payload)
        except Exception as e:
            code, result = 500, {"error": f"Beklenmeyen hata: {str(e)[:200]}"}
        self._send(code, result)
