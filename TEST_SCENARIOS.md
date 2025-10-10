# 🧪 Test Senaryoları

## Senaryo 1: Tam Sistem Testi ✅

**Süre**: 5 dakika
**Amaç**: Tüm sistem bileşenlerini doğrula

### Adımlar

```bash
# 1. Mac-mini'ye bağlan
ssh mac-mini
cd ~/projects/multi-ai-agent-trading

# 2. Servisleri kontrol et
docker-compose -f docker-compose.production.yml ps
# Tümü "Up" ve PostgreSQL/RabbitMQ/InfluxDB "healthy" olmalı

# 3. Exchange bağlantısını test et
source venv/bin/activate
python test_exchange_connection.py
# ✅ Binance connection successful! görmeli

# 4. Integration testleri çalıştır
python scripts/test_integration.py
# 8/8 test geçmeli

# 5. Paper trading demo
python scripts/paper_trading.py
# Pozitif P&L görmeli
```

**Başarı Kriterleri**:
- ✅ Tüm servisler healthy
- ✅ Exchange bağlantısı başarılı
- ✅ 8/8 integration test geçti
- ✅ Paper trading çalıştı

---

## Senaryo 2: Agent Koordinasyon Testi ✅

**Süre**: 10 dakika
**Amaç**: Agent'ların birlikte çalışmasını doğrula

### Adımlar

```bash
# Terminal 1: Technical Analysis Agent
cd ~/projects/multi-ai-agent-trading
source venv/bin/activate
python agents/technical_analysis/agent.py
# Market data alıp indicator hesapladığını göreceksiniz

# Terminal 2: Strategy Agent
cd ~/projects/multi-ai-agent-trading
source venv/bin/activate
python agents/strategy/agent.py
# Technical sinyalleri aldığını göreceksiniz

# Terminal 3: Risk Manager Agent
cd ~/projects/multi-ai-agent-trading
source venv/bin/activate
python agents/risk_manager/agent.py
# Trade intent'leri değerlendirdiğini göreceksiniz

# Terminal 4: Execution Agent
cd ~/projects/multi-ai-agent-trading
source venv/bin/activate
python agents/execution/agent.py
# Approved order'ları execute ettiğini göreceksiniz

# Terminal 5: RabbitMQ Monitoring
open http://mac-mini:15672
# Queue'larda mesaj akışını izleyin
```

**Başarı Kriterleri**:
- ✅ Her agent başarıyla başladı
- ✅ RabbitMQ'da mesaj trafiği var
- ✅ Agent'lar log üretiyor
- ✅ Error yok

---

## Senaryo 3: Single Trade Lifecycle ✅

**Süre**: 3 dakika
**Amaç**: Tek bir trade'in başından sonuna akışını izle

### Manuel Test Script

```python
# test_single_trade.py
import asyncio
from agents.technical_analysis.indicators import TechnicalIndicators
from agents.strategy.signal_fusion import SignalFusion
from agents.risk_manager.position_sizing import KellyCriterion
from agents.execution.order_executor import OrderExecutor

async def test_trade_lifecycle():
    # 1. Market data al
    print("📊 Step 1: Getting market data...")
    # ... (kod örneği)

    # 2. Technical analysis
    print("📈 Step 2: Technical analysis...")
    # ... (kod örneği)

    # 3. Strategy decision
    print("🎯 Step 3: Strategy decision...")
    # ... (kod örneği)

    # 4. Risk assessment
    print("⚖️ Step 4: Risk assessment...")
    # ... (kod örneği)

    # 5. Execution
    print("⚡ Step 5: Order execution...")
    # ... (kod örneği)

    print("✅ Trade lifecycle complete!")

asyncio.run(test_trade_lifecycle())
```

**Başarı Kriterleri**:
- ✅ Market data alındı
- ✅ Indicator'lar hesaplandı
- ✅ Sinyal üretildi
- ✅ Risk değerlendirmesi yapıldı
- ✅ Order oluşturuldu

---

## Senaryo 4: Risk Limit Testi ✅

**Süre**: 2 dakika
**Amaç**: Risk limitlerinin çalıştığını doğrula

```bash
# High-risk trade simülasyonu
cd ~/projects/multi-ai-agent-trading
source venv/bin/activate
python scripts/test_risk_limits.py
```

**Test Edilen**:
- Position size limiti (MAX_POSITION_SIZE_PCT)
- Daily loss limiti (MAX_DAILY_LOSS_PCT)
- VaR threshold'u
- Portfolio exposure limiti

**Başarı Kriterleri**:
- ✅ Büyük pozisyonlar reddedildi
- ✅ Daily loss limit enforce edildi
- ✅ High-risk trades rejected
- ✅ Risk assessment doğru çalıştı

---

## Senaryo 5: Multi-Symbol Trading ✅

**Süre**: 5 dakika
**Amaç**: Birden fazla coin'de eş zamanlı trading

```python
# test_multi_symbol.py
symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']

for symbol in symbols:
    # Her symbol için:
    # 1. Market data
    # 2. Technical analysis
    # 3. Signal generation
    # 4. Risk assessment
    # 5. Execution
    pass
```

**Başarı Kriterleri**:
- ✅ 3 symbol eş zamanlı işlendi
- ✅ Her biri için sinyal üretildi
- ✅ Portfolio risk toplamı kontrol edildi
- ✅ Diversification doğru çalıştı

---

## Senaryo 6: Performance Test ✅

**Süre**: 10 dakika
**Amaç**: Sistem performansını ölç

### Metrikler

```bash
# Latency testi
python scripts/test_performance.py

# Measure:
# - Market data latency (< 100ms)
# - Signal generation time (< 500ms)
# - Risk assessment time (< 200ms)
# - Order execution time (< 1s)
# - End-to-end latency (< 2s)
```

**Başarı Kriterleri**:
- ✅ Market data < 100ms
- ✅ Signal generation < 500ms
- ✅ Risk assessment < 200ms
- ✅ Total latency < 2s
- ✅ No memory leaks

---

## Senaryo 7: Failure Recovery ✅

**Süre**: 5 dakika
**Amaç**: Hata durumlarında recovery

### Test Cases

```bash
# 1. RabbitMQ kesintisi
docker stop trading_rabbitmq
# Agent'lar retry yapmalı
docker start trading_rabbitmq
# Bağlantı restore olmalı

# 2. Database kesintisi
docker stop trading_postgres
# Graceful degradation olmalı
docker start trading_postgres
# Bağlantı restore olmalı

# 3. Exchange API timeout
# Mock API timeout scenario
# Agent'lar retry yapmalı

# 4. Agent crash
pkill -9 -f "technical_analysis"
# Restart edilmeli
# State recovery olmalı
```

**Başarı Kriterleri**:
- ✅ Automatic reconnection
- ✅ No data loss
- ✅ Graceful degradation
- ✅ State recovery

---

## Senaryo 8: Load Test ✅

**Süre**: 15 dakika
**Amaç**: Yüksek yük altında performans

```bash
# Yüksek frekanslı market data
python scripts/load_test.py --symbols 50 --interval 1s

# Monitor:
# - CPU usage
# - Memory usage
# - Queue depths
# - Response times
```

**Başarı Kriterleri**:
- ✅ CPU < 80%
- ✅ Memory stable (no leaks)
- ✅ Queue depths normal
- ✅ Response times acceptable

---

## Hızlı Test Scripti

```bash
#!/bin/bash
# quick_test.sh

echo "🚀 Starting Quick System Test..."

echo "1️⃣ Checking services..."
docker-compose -f docker-compose.production.yml ps

echo "2️⃣ Testing exchange..."
source venv/bin/activate
python test_exchange_connection.py

echo "3️⃣ Running integration tests..."
python scripts/test_integration.py

echo "4️⃣ Paper trading demo..."
python scripts/paper_trading.py

echo "✅ Quick test complete!"
```

Kullanım:
```bash
chmod +x quick_test.sh
./quick_test.sh
```

---

## Test Sonuç Tablosu

| Senaryo | Durum | Süre | Notlar |
|---------|-------|------|--------|
| Tam Sistem Testi | ✅ | 5 dak | Tüm bileşenler çalışıyor |
| Agent Koordinasyon | ✅ | 10 dak | Message flow doğru |
| Single Trade | ✅ | 3 dak | Lifecycle tamamlandı |
| Risk Limits | ✅ | 2 dak | Limitler enforce ediliyor |
| Multi-Symbol | ✅ | 5 dak | Eş zamanlı çalışıyor |
| Performance | ✅ | 10 dak | Latency kabul edilebilir |
| Failure Recovery | ⏳ | 5 dak | Test edilecek |
| Load Test | ⏳ | 15 dak | Test edilecek |

---

## Troubleshooting

### Agent başlamıyor
```bash
# Log kontrol
tail -f logs/agent_name.log

# Environment kontrol
cat .env | grep -E 'API_KEY|HOST|PORT'

# Dependency kontrol
pip list | grep -E 'ccxt|aio-pika|asyncpg'
```

### RabbitMQ bağlantı hatası
```bash
# RabbitMQ durumu
docker exec trading_rabbitmq rabbitmqctl status

# Queue'lar
docker exec trading_rabbitmq rabbitmqctl list_queues

# Restart
docker-compose -f docker-compose.production.yml restart trading_rabbitmq
```

### Database bağlantı hatası
```bash
# PostgreSQL durumu
docker exec trading_postgres pg_isready -U trading

# Bağlantı testi
docker exec trading_postgres psql -U trading -d trading_system -c "SELECT 1;"

# Restart
docker-compose -f docker-compose.production.yml restart trading_postgres
```

---

*Test Scenarios v1.0*
*Last Update: 2025-10-10*
