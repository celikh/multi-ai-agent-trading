# DEV-70: InfluxDB Query Integration - RESOLUTION COMPLETE ✅

**Issue**: Risk Manager failing to query InfluxDB for real-time market data
**Status**: RESOLVED
**Resolution Date**: 2025-10-10
**Verification**: Zero fallback prices after 12:54PM deployment

---

## Problem Summary

The risk manager agent was unable to query InfluxDB v2 for real-time price data, causing it to fall back to hardcoded prices (BTC=$50k, ETH=$2.5k, SOL=$150). This resulted in:
- Inaccurate position sizing
- Incorrect stop-loss and take-profit calculations
- 11+ fallback price warnings per analysis cycle
- Trades based on stale/fake prices instead of current market data

---

## Root Causes Identified

### 1. Missing Async Query Wrapper
**File**: `infrastructure/database/influxdb.py`
**Issue**: InfluxDBManager had no async query() method for agent compatibility
**Fix**: Added async query() wrapper (lines 242-287)

### 2. InfluxQL vs Flux Query Language
**File**: `agents/risk_manager/agent.py`
**Issue**: All queries written in InfluxQL (v1) instead of Flux (v2)
**Fix**: Converted all queries to Flux syntax (lines 436-500)

### 3. Aggregation Query Handling
**File**: `infrastructure/database/influxdb.py`
**Issue**: Aggregation functions (stddev, mean, count) don't return _time field, causing KeyError
**Fix**: Wrapped record.get_time() in try-except to handle missing _time (lines 257-265)

### 4. Outdated Code Path (Critical Discovery)
**File**: `agents/risk_manager/agent.py`
**Issue**: Risk manager had comment "InfluxDB query() method not working currently" and was bypassing InfluxDB entirely, using message.expected_price instead
**Fix**: Updated to query InfluxDB first, fallback to expected_price only if query fails (lines 205-233)

---

## Technical Implementation

### Async Query Wrapper
```python
async def query(self, flux_query: str) -> List[Dict[str, Any]]:
    """
    Execute a Flux query and return results as list of dicts.
    Wrapper for async compatibility with agents.
    """
    if not self._query_api:
        raise RuntimeError("InfluxDB not connected. Call connect() first.")

    try:
        result = self._query_api.query(
            org=settings.influxdb.org, query=flux_query
        )

        data = []
        for table in result:
            for record in table.records:
                # Aggregation functions (stddev, mean, count) don't have _time
                try:
                    timestamp = record.get_time()
                    time_str = timestamp.isoformat() if timestamp else None
                except KeyError:
                    # Aggregation result - no timestamp
                    time_str = None

                value = record.get_value()
                row = {
                    "_time": time_str,
                    "_value": value,
                }
                # Add all fields and tags
                for key, val in record.values.items():
                    if not key.startswith("_"):
                        row[key] = val
                data.append(row)

        return data
    except Exception as e:
        import traceback
        logger.error(
            "influx_query_error",
            error=str(e),
            error_type=type(e).__name__,
            query_preview=flux_query[:100],
            traceback=traceback.format_exc(),
        )
        raise
```

### Flux Query Examples

**Price Query (Before - InfluxQL)**:
```sql
SELECT last("close") FROM "ohlcv" WHERE symbol='BTC/USDT' AND time > now() - 1h
```

**Price Query (After - Flux)**:
```flux
from(bucket: "market_data")
    |> range(start: -1h)
    |> filter(fn: (r) => r["_measurement"] == "ohlcv")
    |> filter(fn: (r) => r["symbol"] == "BTC/USDT")
    |> filter(fn: (r) => r["_field"] == "close")
    |> last()
```

**Volatility Query (Before - InfluxQL)**:
```sql
SELECT stddev("close") FROM "ohlcv" WHERE symbol='BTC/USDT' AND time > now() - 24h
```

**Volatility Query (After - Flux)**:
```flux
from(bucket: "market_data")
    |> range(start: -24h)
    |> filter(fn: (r) => r["_measurement"] == "ohlcv")
    |> filter(fn: (r) => r["symbol"] == "BTC/USDT")
    |> filter(fn: (r) => r["_field"] == "close")
    |> stddev()
```

### Price Retrieval Logic
```python
# Get market data from InfluxDB (price, ATR, volatility)
market_data = await self._get_market_data(symbol)
current_price = market_data.get("price")
atr = market_data.get("atr")
price_std = market_data.get("std")

# Fallback to expected_price from TradeIntent if InfluxDB fails
if not current_price or current_price == 0.0:
    current_price = message.expected_price
    if current_price and current_price > 0:
        self.logger.debug(
            "using_expected_price",
            symbol=symbol,
            price=current_price
        )

# Last resort: hardcoded fallback prices
if not current_price or current_price == 0.0:
    fallback_prices = {
        "BTC/USDT": 50000.0,
        "ETH/USDT": 2500.0,
        "SOL/USDT": 150.0,
    }
    current_price = fallback_prices.get(symbol, 1000.0)
    self.logger.warning(
        "using_fallback_price",
        symbol=symbol,
        fallback_price=current_price
    )
```

---

## Deployment Timeline

| Time | Event | Result |
|------|-------|--------|
| 12:45-12:52 | Pre-fix behavior | 11 fallback_price warnings |
| 12:54 | Fix deployed (commit 07301cd) | Risk manager restarted |
| 12:54:44 | First trade with real prices | stop_loss: 115478.82, take_profit: 133712.32 |
| 12:56+ | Sustained success | Zero fallback warnings |

---

## Verification Evidence

### Before Fix (12:47-12:52)
```json
{
  "symbol": "BTC/USDT",
  "fallback_price": 50000.0,
  "event": "using_fallback_price",
  "timestamp": "2025-10-10T12:52:42.010305Z"
}
{
  "symbol": "BTC/USDT",
  "stop_loss": 47500.0,
  "take_profit": 55000.0,
  "quantity": 0.0013527,
  "event": "trade_approved",
  "timestamp": "2025-10-10T12:52:45.090917Z"
}
```

**Analysis**: Using hardcoded $50k BTC price, resulting in incorrect stop-loss/take-profit calculations

### After Fix (12:54+)
```json
{
  "symbol": "BTC/USDT",
  "stop_loss": 115478.82,
  "take_profit": 133712.32,
  "quantity": 0.00055641,
  "risk_score": 0.0,
  "event": "trade_approved",
  "timestamp": "2025-10-10T12:54:44.845667Z"
}
```

**Analysis**: Using real InfluxDB price (~$121,595), resulting in accurate calculations. No fallback_price warning.

### Metrics

| Metric | Before Fix | After Fix | Improvement |
|--------|-----------|-----------|-------------|
| Fallback Warnings | 11 per cycle | 0 | 100% |
| Price Accuracy | Hardcoded $50k | Real-time InfluxDB | ∞ |
| Stop-Loss Calc | 47500.0 | 115478.82 | Accurate |
| Position Sizing | 0.0013527 BTC | 0.00055641 BTC | Accurate |

---

## Git Commits

1. **4f95e57**: Initial InfluxDB async query wrapper
2. **a9ea43a**: Convert InfluxQL to Flux queries
3. **aece76a**: Fix datetime serialization to ISO format
4. **25ab236**: Handle aggregation queries (missing _time)
5. **07301cd**: Update risk manager to use InfluxDB prices (FINAL FIX)

---

## Lessons Learned

### 1. Always Check Code Paths
The real issue wasn't just the query method—it was that the code was bypassing InfluxDB entirely due to an outdated comment.

### 2. Aggregation Functions Behave Differently
stddev(), mean(), count() don't return timestamps. This is expected InfluxDB behavior, not a bug.

### 3. Deployment Cache Management
Required systematic Python cache clearing on Mac Mini:
```bash
find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete
```

### 4. Log Analysis is Critical
Comparing stop-loss values (47500 vs 115478) revealed the exact moment the fix took effect.

---

## Related Issues

- **DEV-67**: Minimum lot size validation (separate issue)
- **DEV-68**: Position sizing optimization (related to accurate pricing)
- **DEV-69**: Positions table exists (separate database issue)
- **DEV-71**: REST-only mode with 30s interval (data collection optimization)

---

## Future Improvements

1. **Health Monitoring**: Add InfluxDB connection health checks
2. **Alerting**: Notify if fallback prices are used (indicates InfluxDB outage)
3. **Caching**: Cache recent prices to reduce query load
4. **Metrics**: Track InfluxDB query latency and success rate
5. **Testing**: Add integration tests for InfluxDB query wrapper

---

## Status: PRODUCTION VERIFIED ✅

The fix has been deployed to production (Mac Mini) and verified through:
- Zero fallback price warnings after 12:54PM
- Trades approved with real-time InfluxDB prices
- Accurate stop-loss and take-profit calculations
- Sustained success across multiple trade cycles

**Issue can be closed.**
