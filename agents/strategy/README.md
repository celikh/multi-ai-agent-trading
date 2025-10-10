# Strategy Agent

**Strateji Ajanı** - Çoklu sinyal füzyonu ve ticaret kararları

## 📋 İçindekiler

- [Genel Bakış](#genel-bakış)
- [Mimari](#mimari)
- [Sinyal Füzyon Stratejileri](#sinyal-füzyon-stratejileri)
- [Kurulum](#kurulum)
- [Kullanım](#kullanım)
- [Konfigürasyon](#konfigürasyon)
- [Test](#test)
- [Monitoring](#monitoring)

## Genel Bakış

Strategy Agent, birden fazla analiz ajanından gelen sinyalleri birleştirerek optimal ticaret kararları oluşturur. Bayesian istatistik, konsensüs mekanizmaları ve zaman ağırlıklı algoritmaları kullanarak yüksek güvenilirlikli trade intent'ler üretir.

### Temel Özellikler

- **🔀 Multi-Strategy Fusion**: 4 farklı füzyon algoritması
- **📊 Bayesian Averaging**: Ajan performans geçmişine dayalı ağırlıklandırma
- **🤝 Consensus Voting**: Çoğunluk tabanlı karar mekanizması
- **⏰ Time Decay**: Yakın zamanlı sinyallere daha fazla ağırlık
- **🎯 Hybrid Approach**: Tüm stratejilerin kombinasyonu
- **📈 Adaptive Learning**: Ajan performansını sürekli güncelleme
- **🛡️ Risk Awareness**: Minimum güven eşiği kontrolü

### Mesaj Akışı

```
Technical Analysis  ─┐
                     │
Fundamental Analysis ├─→ [Signal Buffer] → [Fusion Engine] → [Trade Intent] → Risk Manager
                     │
Sentiment Analysis  ─┘
```

## Mimari

### Sistem Bileşenleri

```
Strategy Agent
│
├── Signal Collection
│   ├── Subscribe: signals.tech
│   ├── Subscribe: signals.fundamental
│   └── Subscribe: signals.sentiment
│
├── Signal Buffering
│   ├── By Symbol
│   ├── Time-Based Expiry
│   └── Pending Count Tracking
│
├── Fusion Engine
│   ├── Bayesian Fusion
│   ├── Consensus Strategy
│   ├── Time Decay Fusion
│   └── Hybrid Fusion
│
├── Decision Making
│   ├── Confidence Validation
│   ├── Trade Intent Generation
│   └── Target Calculation
│
└── Output
    ├── Publish: trade.intent
    └── Store: PostgreSQL
```

### Veri Yapıları

**Signal Buffer**:
```python
@dataclass
class SignalBuffer:
    signals: List[TradingSignal]      # Toplanan sinyaller
    last_decision: Optional[datetime] # Son karar zamanı
    pending_count: int                # Bekleyen sinyal sayısı
```

**Fusion Signal**:
```python
@dataclass
class Signal:
    agent_type: str          # Ajan tipi
    symbol: str              # Sembol
    signal: SignalType       # BUY/SELL/HOLD
    confidence: float        # 0-1 arası güven skoru
    timestamp: datetime      # Sinyal zamanı
    reasoning: str          # Gerekçe
    metadata: Dict          # Ek bilgiler
```

## Sinyal Füzyon Stratejileri

### 1. Bayesian Fusion

Ajan performans geçmişine dayalı optimal ağırlıklandırma.

**Algoritma**:
```python
# 1. Her ajan için geçmiş performans ağırlığı hesapla
agent_weight = historical_accuracy * signal_confidence

# 2. Ağırlıkları normalize et
total_weight = sum(all_weights)
normalized_weights = weights / total_weight

# 3. Ağırlıklı oylama
buy_score = sum(weight for signal in BUY signals)
sell_score = sum(weight for signal in SELL signals)

# 4. Final karar
if buy_score > sell_score and buy_score > 0.3:
    return BUY
elif sell_score > buy_score and sell_score > 0.3:
    return SELL
else:
    return HOLD
```

**Özellikler**:
- **Adaptive Learning**: Her ticaret sonrası ajan doğruluğu güncellenir
- **Exponential Decay**: Yakın geçmiş performansı daha önemli
- **Confidence Weighting**: Yüksek güvenli sinyaller daha fazla ağırlık
- **History Window**: Son 100 karar dikkate alınır

**Kullanım Senaryosu**: Uzun vadeli, kararlı strateji için ideal

### 2. Consensus Strategy

Çoğunluk anlaşması gerektiren karar mekanizması.

**Algoritma**:
```python
# 1. Yüksek güvenli sinyalleri filtrele
strong_signals = filter(confidence >= min_confidence)

# 2. Oylama
buy_count = count(BUY signals)
sell_count = count(SELL signals)
total = len(strong_signals)

# 3. Anlaşma kontrolü
buy_agreement = buy_count / total
if buy_agreement >= min_agreement (0.6):
    return BUY with avg_confidence
```

**Özellikler**:
- **Threshold Filtering**: Minimum güven kontrolü (varsayılan 0.6)
- **Majority Required**: En az %60 anlaşma gerekir
- **Average Confidence**: Anlaşan sinyallerin ortalama güveni
- **Safe Default**: Anlaşma yoksa HOLD

**Kullanım Senaryosu**: Yüksek güvenilirlik gereken durumlarda

### 3. Time Decay Fusion

Yakın zamanlı sinyallere daha fazla ağırlık veren sistem.

**Algoritma**:
```python
# 1. Her sinyal için zaman ağırlığı hesapla
age_minutes = (now - signal_time).total_seconds() / 60
time_weight = 0.5 ** (age_minutes / half_life_minutes)

# 2. Zaman ve güven ağırlıklı skor
signal_weight = time_weight * confidence

# 3. Toplam skorları normalize et
buy_score = sum(weights for BUY) / total_weight
sell_score = sum(weights for SELL) / total_weight
```

**Özellikler**:
- **Exponential Decay**: Yarı ömür 30 dakika (yapılandırılabilir)
- **Fresh Signals Priority**: Yeni sinyaller 2x daha önemli
- **Age Tolerance**: 60 dakikaya kadar sinyal kabul edilir
- **Smooth Transition**: Ani ağırlık değişimi yok

**Kullanım Senaryosu**: Hızlı değişen piyasalarda

### 4. Hybrid Fusion

Üç stratejinin kombinasyonu ile en güvenilir karar.

**Algoritma**:
```python
# 1. Her stratejiyi uygula
bayesian_result = bayesian.fuse_signals(signals)
consensus_result = consensus.fuse_signals(signals)
time_decay_result = time_decay.fuse_signals(signals)

# 2. Stratejilerin skorlarını topla
for each strategy:
    signal_scores[strategy.signal] += strategy.confidence

# 3. En yüksek skoru seç
final_signal = max(signal_scores)
final_confidence = signal_scores[final_signal] / 3  # Ortalama
```

**Özellikler**:
- **Multi-Strategy Voting**: Her strateji bir oy
- **Confidence Averaging**: Ortalama güven skoru
- **Strategy Transparency**: Her stratejinin sonucu görünür
- **Robust Decision**: Tek strateji hatasına karşı dayanıklı

**Kullanım Senaryosu**: Üretim ortamı için önerilen

## Kurulum

### Gereksinimler

```bash
# Python bağımlılıkları (requirements.txt'de mevcut)
numpy>=1.24.0
pandas>=2.0.0
pydantic>=2.0.0
asyncio
```

### Database Schema

```sql
-- Strategy decisions tablosu
CREATE TABLE IF NOT EXISTS strategy_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(50) NOT NULL,
    signal_type VARCHAR(20) NOT NULL,
    confidence DECIMAL(5, 4),
    fusion_strategy VARCHAR(50) NOT NULL,
    num_signals INTEGER NOT NULL,
    reasoning TEXT,
    fusion_details JSONB,
    price_target DECIMAL(20, 8),
    stop_loss DECIMAL(20, 8),
    take_profit DECIMAL(20, 8),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_strategy_decisions_symbol ON strategy_decisions(symbol);
CREATE INDEX idx_strategy_decisions_created_at ON strategy_decisions(created_at DESC);
SELECT create_hypertable('strategy_decisions', 'created_at', if_not_exists => TRUE);
```

### Altyapı Kurulumu

```bash
# 1. PostgreSQL'i başlat
docker-compose up -d postgresql

# 2. Schema'yı uygula
psql -U trading -d trading_system -f infrastructure/database/schema.sql

# 3. RabbitMQ'yu başlat
docker-compose up -d rabbitmq
```

## Kullanım

### Temel Kullanım

```python
import asyncio
from agents.strategy import StrategyAgent

async def main():
    # Agent'ı oluştur
    agent = StrategyAgent(
        name="strategy_agent_main",
        fusion_strategy="hybrid",      # veya "bayesian", "consensus", "time_decay"
        min_signals=2,                 # Minimum sinyal sayısı
        signal_timeout_seconds=300,    # Sinyal geçerlilik süresi
        min_confidence=0.6,            # Minimum güven eşiği
        decision_interval_seconds=30,  # Karar periyodu
    )

    # Başlat
    await agent.initialize()
    await agent.start()

    # Çalışmaya devam et
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
```

### Terminal'den Çalıştırma

```bash
# Strategy Agent'ı başlat
python agents/strategy/agent.py
```

### Docker ile Çalıştırma

```bash
# Docker image oluştur
docker build -t strategy-agent -f agents/strategy/Dockerfile .

# Container'ı başlat
docker run -d \
  --name strategy-agent \
  --network trading-network \
  -e FUSION_STRATEGY=hybrid \
  -e MIN_CONFIDENCE=0.6 \
  strategy-agent
```

## Konfigürasyon

### Environment Variables

```bash
# Agent Configuration
STRATEGY_FUSION_STRATEGY=hybrid          # bayesian|consensus|time_decay|hybrid
STRATEGY_MIN_SIGNALS=2                   # Minimum sinyal sayısı
STRATEGY_SIGNAL_TIMEOUT=300              # Sinyal timeout (saniye)
STRATEGY_MIN_CONFIDENCE=0.6              # Minimum güven eşiği
STRATEGY_DECISION_INTERVAL=30            # Karar periyodu (saniye)

# Bayesian Settings
BAYESIAN_HISTORY_WINDOW=100              # Performans geçmişi penceresi

# Consensus Settings
CONSENSUS_MIN_CONFIDENCE=0.6             # Minimum güven
CONSENSUS_MIN_AGREEMENT=0.6              # Minimum anlaşma (0-1)

# Time Decay Settings
TIME_DECAY_HALF_LIFE=30                  # Yarı ömür (dakika)
```

### Python Configuration

```python
from agents.strategy import StrategyAgent

# Custom configuration
agent = StrategyAgent(
    name="custom_strategy",
    fusion_strategy="hybrid",
    min_signals=3,                    # Daha fazla sinyal iste
    signal_timeout_seconds=600,       # 10 dakika timeout
    min_confidence=0.7,               # Daha yüksek güven iste
    decision_interval_seconds=60,     # 1 dakikada bir karar
)

# Bayesian performans güncelleme
await agent.update_agent_performance("technical_analysis", 0.85)
await agent.update_agent_performance("sentiment_analysis", 0.70)
```

## Test

### Unit Tests

```bash
# Signal fusion testleri
python scripts/test_strategy.py
```

**Test Çıktısı**:
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

💭 Reasoning:
  • technical_analysis: BUY (85.00%) - RSI oversold + MACD bullish crossover
  • sentiment_analysis: BUY (70.00%) - Positive social sentiment spike
  • fundamental_analysis: HOLD (60.00%) - Mixed on-chain metrics

============================================================
✅ ALL TESTS COMPLETED SUCCESSFULLY
============================================================
```

### Integration Tests

```bash
# Tam sistem testi
# Terminal 1: Data Collection
python agents/data_collection/agent.py

# Terminal 2: Technical Analysis
python agents/technical_analysis/agent.py

# Terminal 3: Strategy Agent
python agents/strategy/agent.py

# Terminal 4: Log monitoring
docker-compose logs -f rabbitmq
```

### Manual Testing

```python
import asyncio
from datetime import datetime
from agents.strategy.signal_fusion import *

async def test_fusion():
    # Hybrid fusion oluştur
    fusion = HybridFusion()

    # Test sinyalleri
    signals = [
        Signal(
            agent_type="technical_analysis",
            symbol="BTC/USDT",
            signal=SignalType.BUY,
            confidence=0.85,
            timestamp=datetime.utcnow(),
            reasoning="Strong bullish indicators",
            metadata={"rsi": 35, "macd": "bullish"}
        ),
        Signal(
            agent_type="sentiment_analysis",
            symbol="BTC/USDT",
            signal=SignalType.BUY,
            confidence=0.70,
            timestamp=datetime.utcnow(),
            reasoning="Positive sentiment",
            metadata={"score": 0.75}
        )
    ]

    # Füzyon uygula
    result = fusion.fuse_signals(signals)

    print(f"Signal: {result['signal'].value}")
    print(f"Confidence: {result['confidence']:.2%}")

asyncio.run(test_fusion())
```

## Monitoring

### Metrics

**PostgreSQL Queries**:

```sql
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
LIMIT 20;

-- Strateji başarı oranı
SELECT
    fusion_strategy,
    COUNT(*) as total_decisions,
    AVG(confidence) as avg_confidence,
    COUNT(*) FILTER (WHERE signal_type = 'BUY') as buy_count,
    COUNT(*) FILTER (WHERE signal_type = 'SELL') as sell_count
FROM strategy_decisions
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY fusion_strategy;

-- Sembol bazında karar dağılımı
SELECT
    symbol,
    signal_type,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence
FROM strategy_decisions
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY symbol, signal_type
ORDER BY symbol, count DESC;
```

### Logging

```python
# Log seviyeleri
logger.debug("signal_buffered", symbol=symbol, buffer_size=len(buffer))
logger.info("decision_made", symbol=symbol, confidence=confidence)
logger.warning("low_confidence_decision", confidence=confidence)
logger.error("fusion_error", error=str(e))
```

### RabbitMQ Monitoring

```bash
# Message queue durumu
rabbitmqadmin list queues name messages

# Exchange durumu
rabbitmqadmin list exchanges name type

# Bindings
rabbitmqadmin list bindings
```

### Grafana Dashboard

**Önerilen Metrikler**:
- Karar sayısı (zaman serisi)
- Ortalama güven skoru
- BUY/SELL/HOLD dağılımı
- Strateji kullanım istatistikleri
- Agent performans trendleri
- Sinyal füzyon süreleri

## Performans Optimizasyonu

### Best Practices

1. **Signal Buffer Management**:
   - Timeout'u piyasa volatilitesine göre ayarla
   - Minimum sinyal sayısını likiditeye göre belirle

2. **Fusion Strategy Selection**:
   - Trending markets → Time Decay
   - Ranging markets → Consensus
   - Mixed conditions → Hybrid (önerilen)

3. **Confidence Thresholds**:
   - Yüksek volatilite → 0.7+
   - Normal koşullar → 0.6
   - Backtesting → 0.5

4. **Agent Performance**:
   - Her 100 karar sonrası performans güncelle
   - Düşük performanslı ajanları devre dışı bırak
   - A/B test farklı stratejileri

### Troubleshooting

**Problem**: Çok az karar üretiliyor
- **Çözüm**: `min_signals` azalt veya `signal_timeout` artır

**Problem**: Düşük güven skorları
- **Çözüm**: Agent performanslarını kontrol et, `min_confidence` düşür

**Problem**: Gecikmeli kararlar
- **Çözüm**: `decision_interval` azalt, buffer boyutunu kontrol et

## Sonraki Adımlar

✅ **Tamamlandı**:
- [x] Signal fusion algoritmaları
- [x] Multi-strategy implementation
- [x] Database integration
- [x] Message bus integration
- [x] Test suite

🔄 **Devam Eden**:
- [ ] Risk Manager entegrasyonu
- [ ] Performance analytics
- [ ] Backtesting engine

📋 **Planlanan**:
- [ ] Machine learning optimization
- [ ] Real-time strategy tuning
- [ ] Advanced risk metrics
- [ ] Multi-timeframe analysis

## Kaynaklar

- [Signal Fusion Theory](../docs/SIGNAL_FUSION.md)
- [Bayesian Methods](../docs/BAYESIAN_TRADING.md)
- [Agent Architecture](../docs/AGENT_ARCHITECTURE.md)
- [Risk Management](../agents/risk_manager/README.md)
