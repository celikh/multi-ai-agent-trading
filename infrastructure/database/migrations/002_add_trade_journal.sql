-- Add Trade Journal table for comprehensive trade documentation
-- Migration: 002_add_trade_journal.sql

-- Trade journal entries for pre-trade planning and post-trade review
CREATE TABLE IF NOT EXISTS trade_journal (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    position_id UUID REFERENCES positions(id) ON DELETE CASCADE,

    -- Setup Phase (Pre-Trade)
    setup_type VARCHAR(50),
    timeframe VARCHAR(10),
    reasoning TEXT NOT NULL,
    technical_indicators JSONB,
    market_condition TEXT,
    confidence_level INTEGER CHECK (
        confidence_level >= 1 AND confidence_level <= 10
    ),
    chart_screenshot TEXT,  -- Base64 or URL
    risk_reward_ratio DECIMAL(10, 2),

    -- Execution Phase
    execution_quality INTEGER CHECK (
        execution_quality >= 1 AND execution_quality <= 10
    ),
    slippage DECIMAL(10, 4),
    entry_timing VARCHAR(20) CHECK (
        entry_timing IN ('early', 'perfect', 'late')
    ),

    -- Review Phase (Post-Trade)
    exit_reason VARCHAR(50) CHECK (
        exit_reason IN ('TP', 'SL', 'manual', 'time-based', 'trailing-stop')
    ),
    emotional_state JSONB,  -- Array of emotions
    rule_following INTEGER CHECK (
        rule_following >= 1 AND rule_following <= 10
    ),
    what_went_well TEXT,
    what_went_wrong TEXT,
    lessons_learned TEXT,
    tags TEXT[],  -- Array of tags for categorization

    -- Metadata
    status VARCHAR(20) DEFAULT 'planned' CHECK (
        status IN ('planned', 'active', 'closed', 'cancelled')
    ),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    review_completed_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_trade_journal_position
ON trade_journal(position_id);

CREATE INDEX idx_trade_journal_setup_type
ON trade_journal(setup_type)
WHERE setup_type IS NOT NULL;

CREATE INDEX idx_trade_journal_status
ON trade_journal(status);

CREATE INDEX idx_trade_journal_tags
ON trade_journal USING GIN(tags);

CREATE INDEX idx_trade_journal_created_at
ON trade_journal(created_at DESC);

-- Trigger for updated_at
CREATE TRIGGER update_trade_journal_updated_at
    BEFORE UPDATE ON trade_journal
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE trade_journal IS
'Comprehensive trade journal for planning, execution notes, and post-trade review';

COMMENT ON COLUMN trade_journal.setup_type IS
'Type of setup (e.g., breakout, pullback, support/resistance)';

COMMENT ON COLUMN trade_journal.confidence_level IS
'Trader confidence in setup (1-10 scale)';

COMMENT ON COLUMN trade_journal.execution_quality IS
'Quality of trade execution (1-10 scale)';

COMMENT ON COLUMN trade_journal.rule_following IS
'How well trading rules were followed (1-10 scale)';

COMMENT ON COLUMN trade_journal.tags IS
'Tags for categorization (e.g., mistake-overtrading, win-breakout)';

-- View for active journal entries with position details
CREATE OR REPLACE VIEW active_journal_entries AS
SELECT
    tj.id,
    tj.position_id,
    p.symbol,
    p.side,
    p.quantity,
    p.entry_price,
    p.current_price,
    p.unrealized_pnl,
    p.stop_loss,
    p.take_profit,
    p.strategy_tag,
    p.opened_at,
    tj.setup_type,
    tj.timeframe,
    tj.reasoning,
    tj.confidence_level,
    tj.risk_reward_ratio,
    tj.status,
    tj.created_at
FROM trade_journal tj
JOIN positions p ON tj.position_id = p.id
WHERE tj.status IN ('planned', 'active')
AND p.status = 'OPEN'
ORDER BY tj.created_at DESC;

-- View for completed trades needing review
CREATE OR REPLACE VIEW trades_pending_review AS
SELECT
    tj.id,
    tj.position_id,
    p.symbol,
    p.side,
    p.realized_pnl,
    p.closed_at,
    tj.setup_type,
    tj.confidence_level,
    tj.created_at,
    tj.review_completed_at
FROM trade_journal tj
JOIN positions p ON tj.position_id = p.id
WHERE tj.status = 'closed'
AND tj.review_completed_at IS NULL
AND p.status = 'CLOSED'
ORDER BY p.closed_at DESC;
