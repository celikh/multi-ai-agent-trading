-- PostgreSQL Schema for Multi-Agent Trading System
-- Tracks trades, positions, portfolio state, and agent decisions

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "timescaledb";

-- ============================================================================
-- CORE TRADING TABLES
-- ============================================================================

-- Trades table: Record all executed trades
CREATE TABLE IF NOT EXISTS trades (
    id UUID DEFAULT uuid_generate_v4(),
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    order_type VARCHAR(20) NOT NULL CHECK (order_type IN ('MARKET', 'LIMIT', 'STOP_LOSS', 'TAKE_PROFIT')),
    quantity DECIMAL(20, 8) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    total_value DECIMAL(20, 8) GENERATED ALWAYS AS (quantity * price) STORED,
    fee DECIMAL(20, 8),
    fee_currency VARCHAR(10),
    status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING', 'FILLED', 'PARTIAL', 'CANCELLED', 'FAILED')),
    order_id VARCHAR(100),
    execution_time TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB,
    PRIMARY KEY (id, created_at)
);

CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_exchange ON trades(exchange);
CREATE INDEX idx_trades_created_at ON trades(created_at DESC);
CREATE INDEX idx_trades_status ON trades(status);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('trades', 'created_at', if_not_exists => TRUE);

-- Positions table: Current open positions
CREATE TABLE IF NOT EXISTS positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('LONG', 'SHORT')),
    quantity DECIMAL(20, 8) NOT NULL,
    entry_price DECIMAL(20, 8) NOT NULL,
    current_price DECIMAL(20, 8),
    unrealized_pnl DECIMAL(20, 8),
    realized_pnl DECIMAL(20, 8) DEFAULT 0,
    stop_loss DECIMAL(20, 8),
    take_profit DECIMAL(20, 8),
    leverage DECIMAL(10, 2) DEFAULT 1.0,
    margin DECIMAL(20, 8),
    status VARCHAR(20) NOT NULL CHECK (status IN ('OPEN', 'CLOSED', 'LIQUIDATED')),
    opened_at TIMESTAMP NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMP,
    metadata JSONB
);

CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_positions_status ON positions(status);
CREATE UNIQUE INDEX idx_positions_open_unique ON positions(exchange, symbol, status) WHERE status = 'OPEN';

-- Portfolio state: Track overall portfolio value
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id UUID DEFAULT uuid_generate_v4(),
    total_value DECIMAL(20, 8) NOT NULL,
    cash_balance DECIMAL(20, 8) NOT NULL,
    positions_value DECIMAL(20, 8) NOT NULL,
    unrealized_pnl DECIMAL(20, 8) NOT NULL,
    realized_pnl DECIMAL(20, 8) NOT NULL,
    daily_pnl DECIMAL(20, 8),
    snapshot_time TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB,
    PRIMARY KEY (id, snapshot_time)
);

CREATE INDEX idx_portfolio_time ON portfolio_snapshots(snapshot_time DESC);
SELECT create_hypertable('portfolio_snapshots', 'snapshot_time', if_not_exists => TRUE);

-- ============================================================================
-- AGENT DECISION TABLES
-- ============================================================================

-- Signals: Trading signals from various agents
CREATE TABLE IF NOT EXISTS signals (
    id UUID DEFAULT uuid_generate_v4(),
    agent_type VARCHAR(50) NOT NULL CHECK (agent_type IN ('TECHNICAL', 'FUNDAMENTAL', 'SENTIMENT', 'STRATEGY')),
    agent_name VARCHAR(100) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    signal_type VARCHAR(20) NOT NULL CHECK (signal_type IN ('BUY', 'SELL', 'HOLD')),
    confidence DECIMAL(5, 4) CHECK (confidence >= 0 AND confidence <= 1),
    price_target DECIMAL(20, 8),
    stop_loss DECIMAL(20, 8),
    take_profit DECIMAL(20, 8),
    reasoning TEXT,
    indicators JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMP,
    metadata JSONB,
    PRIMARY KEY (id, created_at)
);

CREATE INDEX idx_signals_symbol ON signals(symbol);
CREATE INDEX idx_signals_agent ON signals(agent_type, agent_name);
CREATE INDEX idx_signals_created_at ON signals(created_at DESC);
SELECT create_hypertable('signals', 'created_at', if_not_exists => TRUE);

-- Risk assessments: Risk evaluations before trade execution
CREATE TABLE IF NOT EXISTS risk_assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    signal_id UUID,
    symbol VARCHAR(50) NOT NULL,
    risk_score DECIMAL(5, 4) CHECK (risk_score >= 0 AND risk_score <= 1),
    position_size DECIMAL(20, 8),
    var_estimate DECIMAL(20, 8),
    max_loss DECIMAL(20, 8),
    approved BOOLEAN NOT NULL,
    rejection_reason TEXT,
    assessed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB
);

CREATE INDEX idx_risk_signal ON risk_assessments(signal_id);
CREATE INDEX idx_risk_assessed_at ON risk_assessments(assessed_at DESC);

-- ============================================================================
-- CONFIGURATION & MONITORING
-- ============================================================================

-- Agent configurations
CREATE TABLE IF NOT EXISTS agent_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name VARCHAR(100) NOT NULL UNIQUE,
    agent_type VARCHAR(50) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    config JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Performance metrics
CREATE TABLE IF NOT EXISTS performance_metrics (
    id UUID DEFAULT uuid_generate_v4(),
    metric_type VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    value DECIMAL(20, 8) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB,
    PRIMARY KEY (id, timestamp)
);

CREATE INDEX idx_metrics_type ON performance_metrics(metric_type);
CREATE INDEX idx_metrics_timestamp ON performance_metrics(timestamp DESC);
SELECT create_hypertable('performance_metrics', 'timestamp', if_not_exists => TRUE);

-- ============================================================================
-- TRIGGERS & FUNCTIONS
-- ============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_trades_updated_at BEFORE UPDATE ON trades
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_configs_updated_at BEFORE UPDATE ON agent_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Active positions summary
CREATE OR REPLACE VIEW active_positions AS
SELECT
    p.symbol,
    p.exchange,
    p.side,
    p.quantity,
    p.entry_price,
    p.current_price,
    p.unrealized_pnl,
    p.stop_loss,
    p.take_profit,
    p.opened_at,
    (p.current_price - p.entry_price) / p.entry_price * 100 AS pnl_pct
FROM positions p
WHERE p.status = 'OPEN'
ORDER BY p.unrealized_pnl DESC;

-- Daily performance summary
CREATE OR REPLACE VIEW daily_performance AS
SELECT
    DATE(created_at) AS trade_date,
    COUNT(*) AS total_trades,
    SUM(CASE WHEN side = 'BUY' THEN 1 ELSE 0 END) AS buy_trades,
    SUM(CASE WHEN side = 'SELL' THEN 1 ELSE 0 END) AS sell_trades,
    SUM(total_value) AS total_volume,
    SUM(fee) AS total_fees
FROM trades
WHERE status = 'FILLED'
GROUP BY DATE(created_at)
ORDER BY trade_date DESC;

-- Strategy decisions: Fused signals and trade intents
CREATE TABLE IF NOT EXISTS strategy_decisions (
    id UUID DEFAULT uuid_generate_v4(),
    symbol VARCHAR(50) NOT NULL,
    signal_type VARCHAR(20) NOT NULL CHECK (signal_type IN ('BUY', 'SELL', 'HOLD')),
    confidence DECIMAL(5, 4) CHECK (confidence >= 0 AND confidence <= 1),
    fusion_strategy VARCHAR(50) NOT NULL,
    num_signals INTEGER NOT NULL,
    reasoning TEXT,
    fusion_details JSONB,
    price_target DECIMAL(20, 8),
    stop_loss DECIMAL(20, 8),
    take_profit DECIMAL(20, 8),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB,
    PRIMARY KEY (id, created_at)
);

CREATE INDEX idx_strategy_decisions_symbol ON strategy_decisions(symbol);
CREATE INDEX idx_strategy_decisions_created_at ON strategy_decisions(created_at DESC);
SELECT create_hypertable('strategy_decisions', 'created_at', if_not_exists => TRUE);

-- Recent signals by agent
CREATE OR REPLACE VIEW recent_signals AS
SELECT
    s.agent_type,
    s.agent_name,
    s.symbol,
    s.signal_type,
    s.confidence,
    s.created_at,
    ra.approved,
    ra.rejection_reason
FROM signals s
LEFT JOIN risk_assessments ra ON s.id = ra.signal_id
WHERE s.created_at > NOW() - INTERVAL '24 hours'
ORDER BY s.created_at DESC;
