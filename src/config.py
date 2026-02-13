#!/usr/bin/env python3
"""Gemini API Test"""
import os
import sys

print("="*60)
print("GEMİNİ API TEST")
print("="*60)

# 1. API Key kontrol
key = os.getenv('GEMINI_API_KEY', '')
if not key:
    print("\n❌ GEMINI_API_KEY environment variable yok!")
    print("GitHub Secrets'e ekledin mi?")
    sys.exit(1)

print(f"\n✅ API Key bulundu: {key[:25]}...")

# 2. Kütüphane kontrol
try:
    import google.generativeai as genai
    print("✅ google-generativeai kütüphanesi yüklü")
except ImportError as e:
    print(f"❌ Kütüphane yüklenemedi: {e}")
    sys.exit(1)

# 3. API bağlantı testi
try:
    print("\n🤖 Gemini'ye bağlanıyor...")
    genai.configure(api_key=key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    response = model.generate_content("Test: Merhaba, çalışıyor musun?")
    
    print(f"✅ BAŞARILI!")
    print(f"Yanıt: {response.text[:100]}...")
    
except Exception as e:
    print(f"\n❌ HATA!")
    print(f"Tip: {type(e).__name__}")
    print(f"Mesaj: {str(e)[:300]}")
    sys.exit(1)

print("\n" + "="*60)
print("✅ TÜM TESTLER BAŞARILI - GEMİNİ HAZIR!")
print("="*60)
