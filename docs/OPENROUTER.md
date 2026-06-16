# OpenRouter / Gemini 3 Flash Geçişi — Altyapı Notları

Bu sistem LLM çağrıları için varsayılan olarak **Gemini** (`google-genai` SDK)
kullanır. OpenRouter üzerinden **Gemini 3 Flash**'a geçiş için altyapı hazır ve
**pasif** beklemektedir. Aktifleşmesi için tek gereken: sağlayıcıyı seçmek ve
API anahtarını tanımlamak.

## Aktifleştirme (anahtar geldiğinde)

GitHub repo ayarlarında:

1. **Secret** ekle: `OPENROUTER_API_KEY = sk-or-...`
2. **Variable** ekle: `LLM_PROVIDER = openrouter`
3. (Opsiyonel) **Variable**: `OPENROUTER_MODEL = google/gemini-3.5-flash`

Workflow (`.github/workflows/daily.yml`) bu değerleri zaten ortama aktarıyor.
Anahtar/değişken boş kaldıkça sistem otomatik olarak Gemini ile çalışmaya
devam eder (`is_openrouter_active()` False döner).

Yerel test için:

```bash
export LLM_PROVIDER=openrouter
export OPENROUTER_API_KEY=sk-or-...
python -u main.py
```

## Nasıl çalışır

- OpenRouter **OpenAI uyumlu** bir API sunar. `requirements.txt`'te zaten bulunan
  `openai` paketi yalnızca `base_url` değiştirilerek kullanılır.
  - Endpoint: `https://openrouter.ai/api/v1/chat/completions`
- Tüm LLM çağrıları `is_openrouter_active()` kontrolünden geçer:
  - **Pasif** → mevcut Gemini akışı (hiç değişiklik yok).
  - **Aktif** → `src/llm_client.py` üzerinden OpenRouter.
- Yönlendirilen çağrı noktaları (`main.py`):
  - `_gemini_call_json` → `llm_client.generate_json` (sıralama, derin analiz,
    batch özet, top-3 — ana boru hattı)
  - `_complete_missing_paragraphs` → `llm_client.generate_text`
  - `_translate_social_signals` → `llm_client.generate_text`

## Gemini 3 Flash parametreleri (OpenRouter)

| Özellik | Değer |
|---|---|
| Model slug | `google/gemini-3.5-flash` (GA, 19 May 2026) |
| Bağlam penceresi | ~1M token |
| Giriş | metin, görsel, PDF, ses, video (çoklu-mod) |
| Çıkış | metin |
| JSON modu | `response_format={"type": "json_object"}` |
| Reasoning | "thinking" modeli — `reasoning.effort` |

### Reasoning (thinking) ayarı

Gemini 3 Flash bir akıl yürütme modelidir. Güç `reasoning.effort` ile ayarlanır:
`minimal | low | medium | high | xhigh`. `effort` ve `max_tokens` **aynı anda
gönderilemez**. Reasoning çıktısı `exclude: true` ile yanıttan gizlenebilir
(token tasarrufu). Sıralama/özet gibi JSON görevlerinde varsayılan `low`
yeterli ve hızlıdır.

OpenAI SDK'sında bu alan standart şemada olmadığından `extra_body` ile gönderilir:

```python
client.chat.completions.create(
    model="google/gemini-3-flash-preview",
    messages=[{"role": "user", "content": prompt}],
    max_tokens=4096,
    temperature=0.3,
    response_format={"type": "json_object"},
    extra_body={"reasoning": {"effort": "low", "exclude": True}},
)
```

## Yapılandırma değişkenleri (`src/config.py`)

| Ortam değişkeni | Varsayılan | Açıklama |
|---|---|---|
| `LLM_PROVIDER` | `gemini` | `openrouter` yapılınca geçiş açılır |
| `OPENROUTER_API_KEY` | _(boş)_ | OpenRouter anahtarı (`sk-or-...`) |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | API kök adresi |
| `OPENROUTER_MODEL` | `google/gemini-3.5-flash` | Birincil model (GA) |
| `OPENROUTER_FALLBACK_MODELS` | `gemini-3.5-flash,gemini-3-flash-preview,gemini-2.5-flash` | Yedek modeller (virgüllü) |
| `OPENROUTER_REASONING_EFFORT` | `low` | `minimal/low/medium/high/xhigh`; `none`→kapalı |
| `OPENROUTER_REASONING_EXCLUDE` | `1` | Reasoning çıktısını gizle |
| `OPENROUTER_TEMPERATURE` | `0.3` | Örnekleme sıcaklığı |
| `OPENROUTER_TIMEOUT` | `300` | HTTP timeout (sn) |
| `OPENROUTER_HTTP_REFERER` | repo URL | OpenRouter sıralama başlığı (ops.) |
| `OPENROUTER_APP_TITLE` | `Siber Guvenlik Haberleri` | OpenRouter sıralama başlığı (ops.) |

> Not: Varsayılan model artık **GA (kararlı)** olan `google/gemini-3.5-flash`tır
> (19 May 2026). `google/gemini-3-flash-preview` hâlâ preview olduğundan yalnızca
> yedek listesinde tutulur. Başka bir modele geçmek için `OPENROUTER_MODEL`
> değişkenini değiştirmek yeterlidir; kod değişikliği gerekmez.
