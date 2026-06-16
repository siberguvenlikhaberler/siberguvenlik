"""
OpenRouter LLM istemcisi — Gemini 3 Flash için PASİF altyapı.

Bu modül, sistemin LLM çağrılarını Gemini (google-genai) yerine OpenRouter
üzerinden yapabilmesi için hazır bekler. OpenRouter OpenAI uyumlu bir API
sunduğundan, requirements.txt'te zaten bulunan `openai` paketi yalnızca
base_url değiştirilerek kullanılır.

AKTİFLEŞME KOŞULU (config.is_openrouter_active):
    LLM_PROVIDER=openrouter  VE  OPENROUTER_API_KEY tanımlı.
Anahtar gelene kadar bu modüldeki fonksiyonlar çağrılmaz; sistem Gemini ile
çalışmaya devam eder. Yani altyapı tamamen pasiftir.

Gemini 3 Flash notları (OpenRouter):
    model     : google/gemini-3-flash-preview
    bağlam    : 1M token, çoklu-mod (metin/görsel/PDF/ses/video) giriş, metin çıkış
    reasoning : "thinking" modeli — reasoning.effort = minimal|low|medium|high|xhigh
                effort ve max_tokens AYNI ANDA gönderilemez (API hata verir).
    json      : response_format={"type":"json_object"} ile JSON modu desteklenir.

OpenAI SDK'sında OpenRouter'a özel alanlar (reasoning, vb.) standart şemada
olmadığı için `extra_body` ile gönderilir.
"""
import re
import json
import time

from src.config import (
    OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL,
    OPENROUTER_FALLBACK_MODELS, OPENROUTER_REASONING_EFFORT,
    OPENROUTER_REASONING_EXCLUDE, OPENROUTER_TEMPERATURE, OPENROUTER_TIMEOUT,
    OPENROUTER_HTTP_REFERER, OPENROUTER_APP_TITLE,
)

# Geçerli reasoning effort seviyeleri (OpenRouter birleşik reasoning şeması)
_VALID_EFFORTS = {'minimal', 'low', 'medium', 'high', 'xhigh'}


def _extract_json_from_text(text):
    """AI yanıtından JSON nesnesini güvenli biçimde çıkarır.

    main.py'deki aynı adlı yardımcının kopyasıdır (modül bağımsız kalsın diye).
    """
    text = (text or '').strip()
    # Olası thinking bloklarını temizle (<think>...</think>)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    start = text.find('{')
    if start == -1:
        raise ValueError("Yanıtta JSON nesnesi bulunamadı")
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    break
    raise ValueError("Geçerli JSON çıkarılamadı")


def _build_client():
    """OpenRouter'a yönlendirilmiş OpenAI istemcisi oluşturur.

    İçe aktarma fonksiyon içinde yapılır: modül import edilse bile, OpenRouter
    aktif değilken `openai` paketinin mevcut olmasına gerek kalmaz (pasiflik).
    """
    from openai import OpenAI
    return OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
        timeout=OPENROUTER_TIMEOUT,
        default_headers={
            # OpenRouter sıralama panosu için opsiyonel kimlik başlıkları
            'HTTP-Referer': OPENROUTER_HTTP_REFERER,
            'X-Title': OPENROUTER_APP_TITLE,
        },
    )


def _reasoning_config():
    """reasoning.effort yapılandırmasını döndürür; kapalıysa None."""
    effort = OPENROUTER_REASONING_EFFORT
    if effort in ('', 'none', 'off', '0'):
        return None
    if effort not in _VALID_EFFORTS:
        effort = 'low'
    cfg = {'effort': effort}
    if OPENROUTER_REASONING_EXCLUDE:
        cfg['exclude'] = True
    return cfg


def _models_to_try():
    """Birincil model + yedekleri tekrarsız sırayla döndürür."""
    seq = [OPENROUTER_MODEL] + list(OPENROUTER_FALLBACK_MODELS)
    seen, ordered = set(), []
    for m in seq:
        if m and m not in seen:
            seen.add(m)
            ordered.append(m)
    return ordered


def generate_text(prompt, max_output_tokens=4096, temperature=None,
                  json_mode=False, label=''):
    """OpenRouter (Gemini 3 Flash) ile metin üretir, ham metni döndürür.

    Başarısızlıkta None döner. Model sırası: birincil → yedekler; her model bir
    kez denenir, ağ/サ hatalarında 15s bekleyip sonraki modele geçer. Bu, mevcut
    _gemini_call_json'daki davranışla aynı felsefededir.
    """
    if not OPENROUTER_API_KEY:
        print(f"   ⚠️  [{label}] OPENROUTER_API_KEY yok, atlanıyor.")
        return None

    client = _build_client()
    reasoning = _reasoning_config()
    temp = OPENROUTER_TEMPERATURE if temperature is None else temperature
    models = _models_to_try()

    extra_body = {}
    if reasoning is not None:
        extra_body['reasoning'] = reasoning

    kwargs = {}
    if json_mode:
        # OpenRouter, OpenAI uyumlu JSON modunu destekler
        kwargs['response_format'] = {'type': 'json_object'}

    for attempt, model in enumerate(models):
        try:
            print(f"   [{label}] OpenRouter deneme {attempt + 1}/{len(models)} [{model}]...")
            resp = client.chat.completions.create(
                model=model,
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=max_output_tokens,
                temperature=temp,
                extra_body=extra_body or None,
                **kwargs,
            )
            text = resp.choices[0].message.content or ''
            if not text.strip():
                print(f"   [{label}] ⚠️  Boş yanıt — sonraki model deneniyor.")
                continue
            print(f"   [{label}] ✅ OpenRouter başarılı [{model}].")
            return text
        except Exception as e:
            print(f"   [{label}] ⚠️  OpenRouter hata [{type(e).__name__}]: {e}")
            if attempt < len(models) - 1:
                print(f"   [{label}] ⏳ 15s bekleniyor...")
                time.sleep(15)

    print(f"   [{label}] ❌ OpenRouter {len(models)} deneme başarısız.")
    return None


def generate_json(prompt, max_output_tokens=4096, temperature=None, label=''):
    """OpenRouter ile JSON yanıt üretir ve ayrıştırılmış nesneyi döndürür.

    _gemini_call_json'ın OpenRouter karşılığıdır. Başarısızlıkta None döner.
    """
    text = generate_text(
        prompt, max_output_tokens=max_output_tokens, temperature=temperature,
        json_mode=True, label=label,
    )
    if text is None:
        return None
    try:
        return _extract_json_from_text(text)
    except Exception as e:
        print(f"   [{label}] ⚠️  JSON ayrıştırma hatası: {e}")
        return None
