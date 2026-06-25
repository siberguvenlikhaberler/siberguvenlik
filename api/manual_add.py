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
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

# Repo kökünü import yoluna ekle (src/ paketine erişim için)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import requests
from bs4 import BeautifulSoup

from src.config import HEADERS, get_deep_analysis_prompt
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
def fetch_article(url):
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

    def _extract(element):
        if not element:
            return ""
        parts = []
        for p in element.find_all(["p", "h1", "h2", "h3", "li"]):
            t = p.get_text().strip()
            if len(t) > 20 and not any(
                x in t.lower() for x in ["cookie", "subscribe", "newsletter"]
            ):
                parts.append(t)
        return "\n\n".join(parts)

    text = ""
    for tag in ["article", "main"]:
        el = soup.find(tag)
        if el:
            text = _extract(el)
            if text:
                break
    if not text:
        el = soup.find(
            "div",
            class_=lambda c: c
            and any(x in str(c).lower() for x in ["content", "article", "body", "post"]),
        )
        if el:
            text = _extract(el)
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

    # Çıktı şekli: {"1": {tr_title, paragraph}} veya {tr_title, paragraph}
    entry = None
    if isinstance(data, dict):
        if "tr_title" in data or "paragraph" in data:
            entry = data
        else:
            for v in data.values():
                if isinstance(v, dict) and ("tr_title" in v or "paragraph" in v):
                    entry = v
                    break
    if not entry:
        return None, None, f"LLM beklenmeyen biçim döndürdü: {list(data)[:5]}"
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


_CARD_RE = re.compile(
    r'                <div class="top3-card">.*?\n                </div>\n',
    re.DOTALL,
)


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


# ─────────────────────────────────────────────────────────────────────────────
# Çekirdek iş akışı
# ─────────────────────────────────────────────────────────────────────────────
def process(payload):
    password = (payload.get("password") or "")
    url = (payload.get("url") or "").strip()
    try:
        remove_index = int(payload.get("remove_index"))
    except (TypeError, ValueError):
        return 400, {"error": "Geçersiz remove_index."}

    expected = os.getenv("MANUAL_ADD_PASSWORD", "")
    if not expected:
        return 500, {"error": "Sunucuda MANUAL_ADD_PASSWORD tanımlı değil."}
    if not hmac.compare_digest(password, expected):
        return 401, {"error": "Şifre hatalı."}

    if not re.match(r"^https?://", url, re.IGNORECASE):
        return 400, {"error": "Geçerli bir URL giriniz."}
    if remove_index not in (0, 1, 2):
        return 400, {"error": "Çıkarılacak haber 0-2 aralığında olmalı."}

    token = os.getenv("GH_TOKEN", "")
    if not token:
        return 500, {"error": "Sunucuda GH_TOKEN tanımlı değil."}
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
    except Exception as e:
        return 500, {"error": f"index.html kart değişimi başarısız: {str(e)[:160]}"}

    archive_html = archive_sha = None
    try:
        archive_html, archive_sha = gh_get_file(archive_path, token)
        new_archive = replace_top3_card(archive_html, remove_index, card_html)
    except Exception:
        # Arşiv dosyası yoksa/okunamıyorsa yalnızca index güncellenir.
        new_archive = None

    # 5) Commit
    msg = f"manuel: kritik haber güncellendi ({report_date})"
    try:
        gh_put_file(INDEX_PATH, new_index, index_sha, token, msg)
        if new_archive is not None:
            gh_put_file(archive_path, new_archive, archive_sha, token, msg)
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
