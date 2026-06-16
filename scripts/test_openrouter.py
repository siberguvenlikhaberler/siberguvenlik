#!/usr/bin/env python3
"""
OpenRouter (Gemini 3.x Flash) canlı smoke-testi.

Kullanım (yerel):
    export OPENROUTER_API_KEY=sk-or-...
    export LLM_PROVIDER=openrouter
    python scripts/test_openrouter.py

Gerçek bir API çağrısı yapar (küçük, ~birkaç token). Kredi yoksa OpenRouter
402 (insufficient credits) döndürür; bu durum da net olarak raporlanır —
yani "anahtar/endpoint doğru ama bakiye yok" ile "anahtar hatalı" ayırt edilir.
"""
import os
import sys

# Proje kökünü import yoluna ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import src.config as c
from src import llm_client as llm


def main():
    print("=== OpenRouter Smoke Test ===")
    print(f"LLM_PROVIDER        : {c.LLM_PROVIDER}")
    print(f"Anahtar mevcut mu   : {bool(c.OPENROUTER_API_KEY)}")
    print(f"Base URL            : {c.OPENROUTER_BASE_URL}")
    print(f"Birincil model      : {c.OPENROUTER_MODEL}")
    print(f"Yedek modeller      : {c.OPENROUTER_FALLBACK_MODELS}")
    print(f"Reasoning           : {llm._reasoning_config()}")
    print("-" * 40)

    if not c.OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY tanımlı değil. Test edilemez.")
        return 1

    # 1) Basit metin üretimi
    print("\n[1] Metin testi...")
    txt = llm.generate_text(
        "Tek kelimeyle yanıtla: Türkiye'nin başkenti neresidir?",
        max_output_tokens=32, label='smoke-text',
    )
    print("   Yanıt:", repr(txt))

    # 2) JSON modu testi
    print("\n[2] JSON modu testi...")
    data = llm.generate_json(
        'Sadece şu JSON nesnesini döndür: {"durum": "ok", "model": "gemini"}',
        max_output_tokens=64, label='smoke-json',
    )
    print("   Ayrıştırılmış:", data, "| tip:", type(data).__name__)

    ok = bool(txt) and isinstance(data, dict)
    print("\n" + ("✅ SMOKE TEST BAŞARILI" if ok else "⚠️  Bazı çağrılar boş döndü — yukarıdaki log'lara bak (kredi/oran sınırı?)"))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
