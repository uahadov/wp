# 🚀 Gemini API Setup (1 Dakika)

## Şu An Durum
- ✅ Config hazır (Gemini = PRIMARY AI)
- ✅ Model: `gemini-1.5-flash` (hızlı + iyi)
- ❌ API key eksik (sen ekleyeceksin)

---

## ADIMLAR:

### 1️⃣ .env Dosyasını Aç
```bash
notepad .env
```

### 2️⃣ Gemini API Key Ekle
Bu satırı bul:
```
GEMINI_API_KEY=your_gemini_api_key_here
```

AI Studio'dan aldığın key'i yapıştır:
```
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXX
```

### 3️⃣ Kaydet ve Kapat
**Ctrl+S** → Kapat

### 4️⃣ Test Et
```bash
python test-config.py
```

Beklenen çıktı:
```
✅ config.py dosyası bulundu

1️⃣  Birincil AI Sağlayıcı (Google Gemini) Token...
   ✅ Token bulundu: AIzaSy...
   🔄 API bağlantısı test ediliyor...
   ✅ Google Gemini API çalışıyor!
   ✅ Model: gemini-1.5-flash
```

### 5️⃣ Taramayı Başlat
```bash
python scanner.py
```

---

## 📊 Gemini vs GitHub

| Özellik | Gemini 1.5 Flash | GitHub GPT-4o |
|---------|------------------|---------------|
| **Hız** | ⚡⚡⚡ Çok hızlı | ⚡⚡ Orta |
| **Kalite** | ✅ İyi | ✅✅ Çok iyi |
| **Ücretsiz Limit** | 1500/gün | 10/dk (sınırlı) |
| **Setup** | 🟢 Kolay (2 dk) | 🔴 Zor (token sorunlu) |
| **Öneri** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

**Sonuç**: Gemini 1.5 Flash **ÇOK DAHA İYİ** bu proje için!

---

## 🎯 Sistem Yapısı (Otomatik)

Gemini key eklediğinde:
```
PRIMARY AI:   Gemini 1.5 Flash (ana analiz)
SECONDARY AI: GitHub GPT-4o (validator, opsiyonel)
```

Gemini key yoksa:
```
PRIMARY AI:   GitHub GPT-4o (fallback)
SECONDARY AI: Yok
```

---

## ⚠️ Sorun Giderme

### "Token eksik" hatası?
→ `.env` dosyasında `GEMINI_API_KEY=` satırını kontrol et

### "API hatası" alıyorsan?
→ Key doğru mu kontrol et (AI Studio'da)
→ Key'de boşluk var mı kontrol et

### GitHub token 401 hatası?
→ Sorun değil! Gemini PRIMARY olduğu için GitHub kullanılmayacak

---

## 🎊 Hazır mısın?

1. `notepad .env`
2. API key yapıştır
3. Kaydet
4. `python scanner.py`

**HIZLI VE KOLAY! 🚀**
