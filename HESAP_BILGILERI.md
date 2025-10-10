# Binance Hesap ve Sistem Bilgileri

## 📊 Binance Hesap Durumu

### Bakiye Detayları
✅ **TOPLAM BAKIYE: $1.60 USD**

| Asset | Miktar | USD Değeri |
|-------|--------|------------|
| **BTC** | 0.00000748 | $0.91 |
| **USDC** | 0.69260725 | $0.69 |
| **LUNA** | 0.0000048 | $0.00 |

### Hesap Bilgileri
- **Hesap Tipi**: SPOT
- **API Bağlantısı**: ✅ Çalışıyor
- **API Key**: f3K7Hv1EJqte9EKdeXaDWRH0kXDemXB1r4dBHIwkuDAMj7hhd1GtSnTL2kUZE7K4
- **API Secret**: Y5C0b9xylFGx45Csp0493nqh7zY0dO5F39sG7rGegeaY9PR8RZC4YBxvwQPUf3MO

## 🌐 Sistem IP ve Adresler

### Mac Mini Server
- **IP**: 192.168.1.150
- **API Endpoint**: http://192.168.1.150:8000
- **API Durumu**: ✅ Çalışıyor

### Dashboard Adresleri
- **Local (Development)**: http://localhost:3000
- **Mac Mini (Production)**: http://192.168.1.150:3000 (kurulacak)

## 🔧 Durum Özeti

### ✅ Çalışan Sistemler
1. **API Server** (mac-mini:8000)
   - Balance endpoint çalışıyor
   - Positions endpoint çalışıyor
   - Binance bağlantısı aktif

2. **Trading Agents** (5 agent)
   - Data Collection ✅
   - Technical Analysis ✅
   - Strategy ✅
   - Risk Manager ✅
   - Execution ✅

3. **Infrastructure**
   - PostgreSQL ✅
   - RabbitMQ ✅
   - InfluxDB ✅

### ⚠️ CORS Sorunu (Development)
Dashboard (localhost:3000) → API (192.168.1.150:8000) arasında CORS hatası var.

**Çözüm 1: API'yi localhost'ta çalıştır**
```bash
cd ~/Development/Projects/Multi\ AI\ Agent\ Trading
source venv/bin/activate
cd api
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Çözüm 2: Dashboard'u mac-mini'de çalıştır**
```bash
# mac-mini'de
cd ~/projects/multi-ai-agent-trading/trading-dashboard
npm run dev -- -H 0.0.0.0
# Sonra http://192.168.1.150:3000 adresinden aç
```

**Çözüm 3: Production build (Önerilen)**
```bash
# Dashboard'u build et ve serve et
cd trading-dashboard
npm run build
npm start
```

## 📝 Bakiye Neden Küçük Görünüyor?

Hesabınızda gerçekten küçük bakiye var:
- BTC: 0.00000748 (~$0.91)
- USDC: 0.69 (~$0.69)

Bu bir **test/demo hesabı** olabilir veya bakiyeniz başka yerde (Futures, Margin, Savings vb.) olabilir.

### Bakiye Kontrol
```bash
# Spot bakiye
curl http://192.168.1.150:8000/api/balance | jq

# Futures bakiyesi için (eğer varsa)
# api/main.py içinde defaultType'ı 'future' yap
```

## 🚀 Web UI Erişim

### Şu Anda API'ye Erişim
```bash
# Bakiye
curl http://192.168.1.150:8000/api/balance

# Pozisyonlar
curl http://192.168.1.150:8000/api/positions

# Sistem metrikleri
curl http://192.168.1.150:8000/api/metrics
```

### Dashboard Erişim (CORS düzeltildikten sonra)
- Development: http://localhost:3000
- Production: http://192.168.1.150:3000

## 💡 Öneriler

1. **Bakiye Artırma**
   - Test için daha fazla USDT transfer edin
   - Veya gerçek trading için yeterli bakiye yükleyin

2. **Dashboard Production'a Alma**
   ```bash
   # Dashboard'u mac-mini'ye deploy et
   cd trading-dashboard
   npm run build
   # Build'i mac-mini'ye kopyala
   rsync -avz .next/ mac-mini:~/projects/multi-ai-agent-trading/trading-dashboard/.next/
   ```

3. **Futures/Margin Hesapları**
   - Eğer Futures kullanıyorsanız, api/main.py'de `defaultType: 'future'` yapın
   - Margin hesapları için ayrı endpoint eklenebilir

## 🔐 Güvenlik Notu

⚠️ API key ve secret bu dokümanda gösterilmiştir. **Production'da bu dosyayı paylaşmayın!**

.env dosyasında saklanmalı ve .gitignore'a eklenmelidir.
