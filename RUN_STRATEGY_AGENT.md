# 🚀 Strategy Agent - Hızlı Başlangıç

Bu rehber Strategy Agent'ı test etmek ve çalıştırmak için adım adım talimatlar içerir.

## 📋 Ön Koşullar

```bash
# 1. Python bağımlılıkları yüklü mü kontrol et
pip list | grep -E "numpy|pandas|pydantic|asyncpg|influxdb-client|pika|talib"

# Eksik varsa:
pip install -r requirements.txt
```

## 🧪 Test 1: Signal Fusion Testleri

Strategy Agent'ın füzyon algoritmalarını test et:

```bash
# Test script'i çalıştır
python scripts/test_strategy.py
```

**Beklenen Çıktı**:
```
============================================================
🧪 STRATEGY AGENT - SIGNAL FUSION TESTS
============================================================

============================================================
🧮 TESTING BAYESIAN FUSION
============================================================

📊 Result:
  Signal: BUY
  Confidence: 75.23%
  Buy Score: 75.23%
  Sell Score: 0.00%

🏋️ Agent Weights:
  technical_analysis: 45.67%
  sentiment_analysis: 29.33%
  fundamental_analysis: 25.00%

...

============================================================
✅ ALL TESTS COMPLETED SUCCESSFULLY
============================================================
```

## 🔄 Test 2: Full System Integration

Tüm sistemi çalıştır ve Strategy Agent'ı test et.

### Adım 1: Infrastructure'ı Başlat

```bash
# Terminal 1: PostgreSQL, InfluxDB, RabbitMQ'yu başlat
docker-compose up -d postgresql influxdb rabbitmq

# Servislerin hazır olmasını bekle (15-30 saniye)
docker-compose ps

# Database schema'yı uygula (ilk çalıştırmada)
docker exec -i postgres-trading psql -U trading -d trading_system < infrastructure/database/schema.sql
```

### Adım 2: Data Collection Agent'ı Başlat

```bash
# Terminal 2: Data Collection Agent
python agents/data_collection/agent.py

# Beklenen çıktı:
# INFO  data_collection_initialized symbols=['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
# INFO  websocket_connected symbol=BTC/USDT
# INFO  ticker_published symbol=BTC/USDT price=43250.50
```

### Adım 3: Technical Analysis Agent'ı Başlat

```bash
# Terminal 3: Technical Analysis Agent
python agents/technical_analysis/agent.py

# Beklenen çıktı:
# INFO  technical_analysis_initialized symbols=['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
# INFO  analysis_complete symbol=BTC/USDT signal=BUY confidence=0.75
# INFO  signal_published symbol=BTC/USDT signal_type=BUY
```

### Adım 4: Strategy Agent'ı Başlat

```bash
# Terminal 4: Strategy Agent
python agents/strategy/agent.py

# Beklenen çıktı:
# INFO  strategy_agent_initialized fusion_strategy=hybrid min_signals=2 min_confidence=0.6
# DEBUG signal_buffered symbol=BTC/USDT agent_type=technical_analysis buffer_size=1
# INFO  decision_made symbol=BTC/USDT signal=BUY confidence=0.7523 num_signals=2
# INFO  signals_fused signal=BUY confidence=0.7523 buy_score=0.7523 sell_score=0.0
```

## 📊 Monitoring ve Validation

### RabbitMQ Web UI

```bash
# Browser'da aç:
open http://localhost:15672

# Login: guest / guest

# Kontrol edilecekler:
# 1. Exchanges → "trading" exchange var mı?
# 2. Queues → İlgili queue'lar var mı?
#    - data_collection
#    - technical_analysis
#    - strategy_agent
#    - trade_intent
# 3. Messages → "trade_intent" queue'da mesaj var mı?
```

### PostgreSQL Database

```bash
# Strategy decisions tablosunu kontrol et
docker exec -i postgres-trading psql -U trading -d trading_system << EOF
-- Son kararlar
SELECT
    symbol,
    signal_type,
    confidence,
    fusion_strategy,
    num_signals,
    created_at
FROM strategy_decisions
ORDER BY created_at DESC
LIMIT 10;

-- Strateji performansı
SELECT
    fusion_strategy,
    COUNT(*) as total_decisions,
    AVG(confidence) as avg_confidence,
    COUNT(*) FILTER (WHERE signal_type = 'BUY') as buy_count,
    COUNT(*) FILTER (WHERE signal_type = 'SELL') as sell_count,
    COUNT(*) FILTER (WHERE signal_type = 'HOLD') as hold_count
FROM strategy_decisions
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY fusion_strategy;
EOF
```

### InfluxDB

```bash
# InfluxDB UI'da veri kontrol et
open http://localhost:8086

# Login bilgileri .env'den al
# Data Explorer → trading bucket → ohlcv measurement
```

## 🔧 Konfigürasyon Seçenekleri

Strategy Agent'ı farklı parametrelerle çalıştır:

### Bayesian Fusion

```bash
# agents/strategy/agent.py dosyasını düzenle:
# fusion_strategy="bayesian"

python agents/strategy/agent.py
```

### Consensus Strategy

```bash
# agents/strategy/agent.py dosyasını düzenle:
# fusion_strategy="consensus"

python agents/strategy/agent.py
```

### Time Decay Fusion

```bash
# agents/strategy/agent.py dosyasını düzenle:
# fusion_strategy="time_decay"

python agents/strategy/agent.py
```

### Custom Configuration

```bash
# agents/strategy/agent.py dosyasında main() fonksiyonunu düzenle:

agent = StrategyAgent(
    name="strategy_agent_main",
    fusion_strategy="hybrid",           # Strateji seçimi
    min_signals=3,                      # Daha fazla sinyal bekle
    signal_timeout_seconds=600,         # 10 dakika timeout
    min_confidence=0.7,                 # Daha yüksek güven iste
    decision_interval_seconds=60,       # 1 dakikada bir karar
)
```

## 🧹 Temizlik

Testi bitirdiğinizde:

```bash
# Tüm agent'ları durdur (Ctrl+C ile her terminalde)

# Infrastructure'ı durdur
docker-compose down

# Verileri temizlemek istersen (DİKKAT: Tüm data silinir!)
docker-compose down -v
```

## ❌ Sorun Giderme

### Problem: "No signals buffered"

**Sebep**: Technical Analysis Agent çalışmıyor veya sinyal üretmiyor.

**Çözüm**:
```bash
# Technical Analysis loglarını kontrol et
# En az 2 dakika bekle (100 candle için)

# Manuel test:
python scripts/test_technical_analysis.py
```

### Problem: "Low confidence decision"

**Sebep**: Sinyaller zayıf veya çelişkili.

**Çözüm**:
```bash
# min_confidence'ı düşür
# agents/strategy/agent.py içinde:
min_confidence=0.5  # 0.6'dan 0.5'e düşür
```

### Problem: "Database connection failed"

**Sebep**: PostgreSQL henüz hazır değil.

**Çözüm**:
```bash
# PostgreSQL durumunu kontrol et
docker-compose ps postgresql

# Logları kontrol et
docker-compose logs postgresql

# Yeniden başlat
docker-compose restart postgresql
sleep 10
```

### Problem: "RabbitMQ connection timeout"

**Sebep**: RabbitMQ henüz hazır değil.

**Çözüm**:
```bash
# RabbitMQ durumunu kontrol et
docker-compose ps rabbitmq

# Logları kontrol et
docker-compose logs rabbitmq

# Yeniden başlat
docker-compose restart rabbitmq
sleep 15
```

## 📈 Başarı Kriterleri

Sistem düzgün çalışıyorsa:

✅ **Test Suite**: Tüm testler geçti (PASSED)
✅ **Data Collection**: Her 5 saniyede ticker mesajı
✅ **Technical Analysis**: Her 60 saniyede analiz
✅ **Strategy Agent**: 2+ sinyal toplandığında karar
✅ **RabbitMQ**: `trade_intent` queue'da mesajlar var
✅ **PostgreSQL**: `strategy_decisions` tablosunda kayıtlar var

## 📚 Ek Kaynaklar

- [Strategy Agent README](agents/strategy/README.md) - Detaylı dokümantasyon
- [Signal Fusion Module](agents/strategy/signal_fusion.py) - Algoritma implementasyonu
- [Test Suite](scripts/test_strategy.py) - Test kodları
- [Database Schema](infrastructure/database/schema.sql) - Veritabanı yapısı

## 🎯 Sonraki Adımlar

Strategy Agent başarıyla çalışıyorsa:

1. **Risk Manager Agent** implement et (Hafta 11-12)
2. **Execution Agent** implement et (Hafta 13-15)
3. **Backtesting Engine** ekle
4. **Paper Trading** test et
5. **Production Deployment** hazırla

---

**Hazırlayan**: Multi-Agent AI Trading System
**Tarih**: 2025-10-10
**Versiyon**: 1.0
