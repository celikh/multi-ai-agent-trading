-- Dashboard Schema Enhancements
-- Based on StonkJournal analysis and trading system requirements

-- =====================================================
-- 1. Enhance positions table with dashboard fields
-- =====================================================

-- Add missing columns to positions table
ALTER TABLE positions
ADD COLUMN IF NOT EXISTS strategy_tag VARCHAR(100),
ADD COLUMN IF NOT EXISTS reasoning TEXT,
ADD COLUMN IF NOT EXISTS execution_quality DECIMAL(5,2),
ADD COLUMN IF NOT EXISTS fees DECIMAL(20,8) DEFAULT 0,
ADD COLUMN IF NOT EXISTS slippage DECIMAL(10,4),
ADD COLUMN IF NOT EXISTS avg_entry_price DECIMAL(20,8),
ADD COLUMN IF NOT EXISTS avg_exit_price DECIMAL(20,8);

-- Add comment for documentation
COMMENT ON COLUMN positions.strategy_tag IS 'Trade strategy identifier (e.g., "BTC Breakout", "ETH Swing Long")';
COMMENT ON COLUMN positions.reasoning IS 'Why this trade was taken - AI-generated or manual notes';
COMMENT ON COLUMN positions.execution_quality IS 'Quality score 0-100 based on slippage, timing, fill quality';

-- =====================================================
-- 2. Create trade_setups table for pre-planned trades
-- =====================================================

CREATE TABLE IF NOT EXISTS trade_setups (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  symbol VARCHAR(50) NOT NULL,
  exchange VARCHAR(50) NOT NULL DEFAULT 'binance',
  side VARCHAR(10) NOT NULL CHECK (side IN ('LONG', 'SHORT')),

  -- Planning details
  planned_entry DECIMAL(20,8) NOT NULL,
  planned_sl DECIMAL(20,8),
  planned_tp DECIMAL(20,8),
  planned_quantity DECIMAL(20,8),
  risk_reward_ratio DECIMAL(10,2),

  -- Strategy and reasoning
  strategy_tag VARCHAR(100),
  reasoning TEXT,
  confidence DECIMAL(5,4),

  -- Status tracking
  status VARCHAR(20) NOT NULL DEFAULT 'PLANNED'
    CHECK (status IN ('PLANNED', 'EXECUTED', 'CANCELLED', 'EXPIRED')),

  -- Timestamps
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  executed_at TIMESTAMP,
  cancelled_at TIMESTAMP,
  expires_at TIMESTAMP,

  -- Link to actual position if executed
  position_id UUID REFERENCES positions(id),

  -- Additional metadata
  metadata JSONB,

  CONSTRAINT valid_risk_reward CHECK (risk_reward_ratio IS NULL OR risk_reward_ratio > 0)
);

CREATE INDEX idx_trade_setups_status ON trade_setups(status);
CREATE INDEX idx_trade_setups_symbol ON trade_setups(symbol);
CREATE INDEX idx_trade_setups_created ON trade_setups(created_at DESC);

COMMENT ON TABLE trade_setups IS 'Pre-planned trade setups before execution';

-- =====================================================
-- 3. Create performance_snapshots table
-- =====================================================

CREATE TABLE IF NOT EXISTS performance_snapshots (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  timestamp TIMESTAMP NOT NULL DEFAULT NOW(),

  -- Account metrics
  total_balance DECIMAL(20,8) NOT NULL,
  available_balance DECIMAL(20,8),
  reserved_balance DECIMAL(20,8),

  -- P&L metrics
  total_pnl DECIMAL(20,8) NOT NULL,
  total_pnl_pct DECIMAL(10,4),
  realized_pnl DECIMAL(20,8),
  unrealized_pnl DECIMAL(20,8),

  -- Position metrics
  open_positions INT DEFAULT 0,
  total_positions INT DEFAULT 0,

  -- Win/Loss metrics
  total_wins INT DEFAULT 0,
  total_losses INT DEFAULT 0,
  total_breakeven INT DEFAULT 0,
  win_rate DECIMAL(5,2),

  -- Average metrics
  avg_win DECIMAL(20,8),
  avg_loss DECIMAL(20,8),
  avg_hold_time INTERVAL,

  -- Risk metrics
  sharpe_ratio DECIMAL(10,4),
  sortino_ratio DECIMAL(10,4),
  max_drawdown DECIMAL(10,4),
  max_drawdown_pct DECIMAL(10,4),

  -- Trade distribution
  long_trades INT DEFAULT 0,
  short_trades INT DEFAULT 0,

  -- Additional analytics
  best_trade_pnl DECIMAL(20,8),
  worst_trade_pnl DECIMAL(20,8),

  -- Metadata
  metadata JSONB
);

CREATE INDEX idx_perf_snapshots_time ON performance_snapshots(timestamp DESC);
CREATE INDEX idx_perf_snapshots_daily ON performance_snapshots(DATE(timestamp));

COMMENT ON TABLE performance_snapshots IS 'Periodic snapshots of portfolio performance for analytics';

-- =====================================================
-- 4. Create trade_journal table for notes
-- =====================================================

CREATE TABLE IF NOT EXISTS trade_journal (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  position_id UUID REFERENCES positions(id),
  trade_setup_id UUID REFERENCES trade_setups(id),

  -- Journal entry
  entry_type VARCHAR(20) CHECK (entry_type IN ('PRE_TRADE', 'DURING_TRADE', 'POST_TRADE', 'REVIEW')),
  title VARCHAR(200),
  content TEXT NOT NULL,

  -- Sentiment/Emotion tracking
  emotional_state VARCHAR(50), -- 'confident', 'fearful', 'greedy', 'disciplined'
  market_condition VARCHAR(50), -- 'trending', 'choppy', 'volatile', 'calm'

  -- Timestamps
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP,

  -- Attachments/Screenshots
  attachments JSONB,

  -- Tags
  tags VARCHAR(100)[],

  CONSTRAINT journal_ref_check CHECK (
    (position_id IS NOT NULL) OR (trade_setup_id IS NOT NULL)
  )
);

CREATE INDEX idx_trade_journal_position ON trade_journal(position_id);
CREATE INDEX idx_trade_journal_setup ON trade_journal(trade_setup_id);
CREATE INDEX idx_trade_journal_created ON trade_journal(created_at DESC);

COMMENT ON TABLE trade_journal IS 'Trading journal entries for reflection and improvement';

-- =====================================================
-- 5. Create daily_summary table
-- =====================================================

CREATE TABLE IF NOT EXISTS daily_summary (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  trade_date DATE NOT NULL UNIQUE,

  -- Daily P&L
  daily_pnl DECIMAL(20,8),
  daily_pnl_pct DECIMAL(10,4),

  -- Trade counts
  trades_count INT DEFAULT 0,
  wins_count INT DEFAULT 0,
  losses_count INT DEFAULT 0,

  -- Metrics
  win_rate DECIMAL(5,2),
  largest_win DECIMAL(20,8),
  largest_loss DECIMAL(20,8),

  -- Execution quality
  avg_execution_quality DECIMAL(5,2),
  avg_slippage DECIMAL(10,4),
  total_fees DECIMAL(20,8),

  -- Notes
  daily_notes TEXT,
  market_notes TEXT,

  -- Emotional tracking
  overall_discipline_score DECIMAL(3,2), -- 0-10 self-rating
  mistakes_made TEXT[],
  lessons_learned TEXT[],

  -- Timestamps
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP,

  -- Metadata
  metadata JSONB
);

CREATE INDEX idx_daily_summary_date ON daily_summary(trade_date DESC);

COMMENT ON TABLE daily_summary IS 'Daily trading performance summary and reflection';

-- =====================================================
-- 6. Create analytics views for dashboard
-- =====================================================

-- View: Current portfolio status
CREATE OR REPLACE VIEW v_portfolio_status AS
SELECT
  COUNT(*) FILTER (WHERE status = 'OPEN') as open_positions,
  SUM(unrealized_pnl) FILTER (WHERE status = 'OPEN') as total_unrealized_pnl,
  SUM(realized_pnl) as total_realized_pnl,
  SUM(CASE WHEN status = 'OPEN' THEN unrealized_pnl ELSE realized_pnl END) as total_pnl,
  AVG(execution_quality) FILTER (WHERE execution_quality IS NOT NULL) as avg_execution_quality,
  SUM(fees) as total_fees,
  COUNT(*) as total_positions
FROM positions
WHERE opened_at > CURRENT_DATE - INTERVAL '30 days';

-- View: Win/Loss statistics
CREATE OR REPLACE VIEW v_win_loss_stats AS
SELECT
  COUNT(*) FILTER (WHERE status = 'CLOSED' AND realized_pnl > 0) as wins,
  COUNT(*) FILTER (WHERE status = 'CLOSED' AND realized_pnl < 0) as losses,
  COUNT(*) FILTER (WHERE status = 'CLOSED' AND realized_pnl = 0) as breakeven,
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE status = 'CLOSED' AND realized_pnl > 0) /
    NULLIF(COUNT(*) FILTER (WHERE status = 'CLOSED'), 0),
    2
  ) as win_rate,
  AVG(realized_pnl) FILTER (WHERE status = 'CLOSED' AND realized_pnl > 0) as avg_win,
  AVG(realized_pnl) FILTER (WHERE status = 'CLOSED' AND realized_pnl < 0) as avg_loss,
  MAX(realized_pnl) as best_trade,
  MIN(realized_pnl) as worst_trade
FROM positions
WHERE closed_at > CURRENT_DATE - INTERVAL '30 days';

-- View: Position details for dashboard
CREATE OR REPLACE VIEW v_position_dashboard AS
SELECT
  p.id,
  p.symbol,
  p.side,
  p.status,
  p.quantity,
  p.entry_price,
  p.current_price,
  p.stop_loss,
  p.take_profit,
  CASE
    WHEN p.status = 'OPEN' THEN p.unrealized_pnl
    ELSE p.realized_pnl
  END as pnl,
  CASE
    WHEN p.status = 'OPEN' AND p.entry_price > 0 THEN
      ROUND(100.0 * (p.current_price - p.entry_price) / p.entry_price, 4)
    WHEN p.status = 'CLOSED' AND p.entry_price > 0 THEN
      ROUND(100.0 * p.realized_pnl / (p.entry_price * p.quantity), 4)
    ELSE 0
  END as pnl_pct,
  p.strategy_tag,
  p.execution_quality,
  CASE
    WHEN p.closed_at IS NOT NULL THEN p.closed_at - p.opened_at
    ELSE NOW() - p.opened_at
  END as hold_duration,
  p.opened_at,
  p.closed_at,
  p.fees,
  p.slippage,
  p.reasoning
FROM positions p
ORDER BY
  CASE WHEN p.status = 'OPEN' THEN 0 ELSE 1 END,
  p.opened_at DESC;

-- =====================================================
-- 7. Functions for dashboard calculations
-- =====================================================

-- Function: Calculate current portfolio value
CREATE OR REPLACE FUNCTION get_portfolio_metrics(
  p_start_date TIMESTAMP DEFAULT CURRENT_DATE - INTERVAL '30 days',
  p_end_date TIMESTAMP DEFAULT NOW()
)
RETURNS TABLE (
  metric_name VARCHAR(50),
  metric_value DECIMAL(20,8),
  metric_pct DECIMAL(10,4)
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    'total_pnl'::VARCHAR(50),
    SUM(CASE WHEN status = 'OPEN' THEN unrealized_pnl ELSE realized_pnl END),
    NULL::DECIMAL(10,4)
  FROM positions
  WHERE opened_at BETWEEN p_start_date AND p_end_date

  UNION ALL

  SELECT
    'realized_pnl'::VARCHAR(50),
    SUM(realized_pnl),
    NULL::DECIMAL(10,4)
  FROM positions
  WHERE closed_at BETWEEN p_start_date AND p_end_date

  UNION ALL

  SELECT
    'unrealized_pnl'::VARCHAR(50),
    SUM(unrealized_pnl),
    NULL::DECIMAL(10,4)
  FROM positions
  WHERE status = 'OPEN'
    AND opened_at BETWEEN p_start_date AND p_end_date;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 8. Insert initial performance snapshot
-- =====================================================

-- Create a function to generate performance snapshot
CREATE OR REPLACE FUNCTION create_performance_snapshot()
RETURNS UUID AS $$
DECLARE
  v_snapshot_id UUID;
  v_total_balance DECIMAL(20,8) := 10000.00; -- Initial balance, adjust as needed
BEGIN
  INSERT INTO performance_snapshots (
    total_balance,
    total_pnl,
    total_pnl_pct,
    realized_pnl,
    unrealized_pnl,
    open_positions,
    total_positions,
    total_wins,
    total_losses,
    win_rate,
    avg_win,
    avg_loss
  )
  SELECT
    v_total_balance + COALESCE(SUM(CASE WHEN status = 'OPEN' THEN unrealized_pnl ELSE realized_pnl END), 0),
    COALESCE(SUM(CASE WHEN status = 'OPEN' THEN unrealized_pnl ELSE realized_pnl END), 0),
    ROUND(100.0 * COALESCE(SUM(CASE WHEN status = 'OPEN' THEN unrealized_pnl ELSE realized_pnl END), 0) / v_total_balance, 4),
    COALESCE(SUM(realized_pnl), 0),
    COALESCE(SUM(unrealized_pnl) FILTER (WHERE status = 'OPEN'), 0),
    COUNT(*) FILTER (WHERE status = 'OPEN'),
    COUNT(*),
    COUNT(*) FILTER (WHERE status = 'CLOSED' AND realized_pnl > 0),
    COUNT(*) FILTER (WHERE status = 'CLOSED' AND realized_pnl < 0),
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'CLOSED' AND realized_pnl > 0) /
      NULLIF(COUNT(*) FILTER (WHERE status = 'CLOSED'), 0), 2),
    AVG(realized_pnl) FILTER (WHERE status = 'CLOSED' AND realized_pnl > 0),
    AVG(realized_pnl) FILTER (WHERE status = 'CLOSED' AND realized_pnl < 0)
  FROM positions
  RETURNING id INTO v_snapshot_id;

  RETURN v_snapshot_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION create_performance_snapshot IS 'Creates a snapshot of current performance metrics';

-- =====================================================
-- 9. Scheduled job for daily snapshots (optional)
-- =====================================================

-- Note: Requires pg_cron extension
-- To enable: CREATE EXTENSION IF NOT EXISTS pg_cron;
--
-- Schedule daily snapshot at midnight:
-- SELECT cron.schedule('daily-performance-snapshot', '0 0 * * *',
--   'SELECT create_performance_snapshot()');
