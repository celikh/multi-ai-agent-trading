# Phase 2 Plan - Position Monitoring & Risk Management

**Start Date**: 2025-10-10 18:20 UTC
**Target Completion**: 2025-10-11 (1 day)
**Status**: PLANNING

---

## 🎯 Phase 2 Objectives

Enable **real-time position monitoring** and **automated risk management** for open positions.

### Success Criteria
- Positions updated periodically (every 10 seconds)
- Stop-loss orders monitored and trigger position closure
- Take-profit orders monitored and trigger position closure
- PnL tracked in real-time
- All functionality verified with automated reality checks

---

## 🔴 CRITICAL ISSUES (Phase 2)

### DEV-75: Implement Position Monitoring Service 🔴

**Priority**: CRITICAL
**Estimated Time**: 2-3 hours
**Blockers**: None (DEV-74 complete)

#### Problem
ExecutionAgent doesn't monitor positions after creation. No periodic updates for:
- Current market price
- Unrealized PnL
- Position value
- Risk metrics

#### Current State
```python
class ExecutionAgent(BaseAgent):  # ❌ Not periodic
    # Creates positions but never updates them
    # No execute() method for periodic tasks
```

#### Solution Design

**Convert ExecutionAgent to PeriodicAgent**:
```python
class ExecutionAgent(PeriodicAgent):  # ✅ Periodic
    def __init__(self, ...):
        super().__init__(
            name="execution_agent_main",
            agent_type="execution",
            interval_seconds=10,  # Update every 10 seconds
            description="Order execution and position monitoring"
        )

    async def execute(self) -> None:
        """Periodic position monitoring"""
        await self._update_all_positions()
        await self._check_sl_tp_triggers()
```

#### Implementation Tasks
1. ✅ Verify PeriodicAgent base class exists
2. ⏳ Change ExecutionAgent to inherit from PeriodicAgent
3. ⏳ Add interval_seconds parameter (default: 10s)
4. ⏳ Implement execute() method:
   - Fetch current prices for all open positions
   - Calculate unrealized PnL
   - Update position records in database
   - Publish PositionUpdateMessage
5. ⏳ Keep existing message-driven execution (on trade.order)
6. ⏳ Test: Verify positions update every 10 seconds
7. ⏳ Add logging for position updates

#### Reality Check Criteria
```bash
# DEV-75 checks to add:
- Position updates logged (> 6 per minute)
- Unrealized PnL calculated and stored
- Position current_price updating
- No errors in position monitoring
```

#### Files to Modify
- `agents/execution/agent.py` - Change BaseAgent to PeriodicAgent
- `agents/execution/agent.py` - Add execute() method

---

### DEV-76: Implement SL/TP Order Monitoring 🔴

**Priority**: CRITICAL
**Estimated Time**: 2-3 hours
**Blockers**: DEV-75 must complete first

#### Problem
Stop-loss and take-profit orders placed but never monitored:
- Orders exist on exchange
- When SL triggers → position stays open (not closed)
- When TP triggers → position stays open (not closed)
- No automatic position closure

#### Current State
```python
# SL/TP orders placed:
await self._place_stop_loss(...)
await self._place_take_profit(...)

# But never checked! ❌
# Position remains open even when SL/TP fills
```

#### Solution Design

**Add SL/TP monitoring to execute() method**:
```python
async def execute(self) -> None:
    """Periodic position and SL/TP monitoring"""
    # 1. Update position prices
    await self._update_all_positions()

    # 2. Check SL/TP orders
    await self._check_sl_tp_orders()

async def _check_sl_tp_orders(self) -> None:
    """Check if any SL/TP orders have filled"""
    for position in self.position_manager.get_open_positions():
        # Check if SL order exists and filled
        if position.sl_order_id:
            order_status = await self._fetch_order_status(
                position.symbol,
                position.sl_order_id
            )

            if order_status == OrderStatus.FILLED:
                await self._handle_sl_trigger(position)

        # Check if TP order exists and filled
        if position.tp_order_id:
            order_status = await self._fetch_order_status(
                position.symbol,
                position.tp_order_id
            )

            if order_status == OrderStatus.FILLED:
                await self._handle_tp_trigger(position)

async def _handle_sl_trigger(self, position):
    """Handle stop-loss trigger"""
    self.logger.warning(
        "stop_loss_triggered",
        position_id=position.position_id,
        symbol=position.symbol,
        sl_price=position.stop_loss
    )

    # Close position
    self.position_manager.close_position(
        position.position_id,
        close_price=position.stop_loss,
        reason="stop_loss"
    )

    # Update database
    await self._update_position_in_db(position)

    # Publish position closed event
    await self._publish_position_closed(position, "stop_loss")

async def _handle_tp_trigger(self, position):
    """Handle take-profit trigger"""
    self.logger.info(
        "take_profit_triggered",
        position_id=position.position_id,
        symbol=position.symbol,
        tp_price=position.take_profit
    )

    # Close position
    self.position_manager.close_position(
        position.position_id,
        close_price=position.take_profit,
        reason="take_profit"
    )

    # Update database
    await self._update_position_in_db(position)

    # Publish position closed event
    await self._publish_position_closed(position, "take_profit")
```

#### Implementation Tasks
1. ⏳ Add `_fetch_order_status()` method using order executor
2. ⏳ Implement `_check_sl_tp_orders()` method
3. ⏳ Implement `_handle_sl_trigger()` method
4. ⏳ Implement `_handle_tp_trigger()` method
5. ⏳ Add sl_order_id and tp_order_id tracking to Position
6. ⏳ Store order IDs when placing SL/TP orders
7. ⏳ Test: Manually trigger SL/TP and verify auto-closure
8. ⏳ Add logging for SL/TP triggers

#### Reality Check Criteria
```bash
# DEV-76 checks to add:
- SL/TP orders monitored (check interval matches position updates)
- Position auto-closes on SL trigger (test with mock)
- Position auto-closes on TP trigger (test with mock)
- Closed positions have correct close_reason
```

#### Files to Modify
- `agents/execution/agent.py` - Add SL/TP monitoring methods
- `agents/execution/position_manager.py` - Add order_id tracking

---

## 📊 Phase 2 Dependencies

```
Phase 1 (Complete) ✅
    ↓
DEV-75: Position Monitoring
    ↓
DEV-76: SL/TP Monitoring
    ↓
Phase 2 Complete
```

**Critical Path**: DEV-75 → DEV-76 (sequential dependency)

---

## 🤖 Reality Check Updates

### New Checks to Add

```python
"DEV-75": {
    "title": "Position monitoring service",
    "checks": [
        {
            "name": "Position updates logged (every 10s)",
            "command": "ssh mac-mini 'tail -100 ~/projects/multi-ai-agent-trading/logs/execution.log | grep -c \"position_updated\"'",
            "expected_min": "6",  # At least 6 updates per minute
            "alert_if_not": True
        },
        {
            "name": "Unrealized PnL calculated",
            "command": "ssh mac-mini 'tail -50 ~/projects/multi-ai-agent-trading/logs/execution.log | grep position_updated | grep unrealized_pnl | tail -1'",
            "alert_if_not": False
        }
    ]
},
"DEV-76": {
    "title": "SL/TP order monitoring",
    "checks": [
        {
            "name": "SL/TP orders monitored",
            "command": "ssh mac-mini 'tail -100 ~/projects/multi-ai-agent-trading/logs/execution.log | grep -c \"checking_sl_tp_orders\"'",
            "expected_min": "6",
            "alert_if_not": True
        },
        {
            "name": "No unhandled SL triggers",
            "command": "ssh mac-mini 'tail -200 ~/projects/multi-ai-agent-trading/logs/execution.log | grep stop_loss_triggered | wc -l'",
            "alert_if_not": False
        }
    ]
}
```

---

## ⏱️ Timeline

### Day 1 (2025-10-10) - Remaining Hours
- [x] Phase 1 completion (DONE)
- [x] Reality check automation (DONE)
- [ ] Phase 2 planning (IN PROGRESS)
- [ ] Start DEV-75 implementation

### Day 2 (2025-10-11) - Full Day
- [ ] Complete DEV-75 (morning)
- [ ] Test position monitoring (morning)
- [ ] Complete DEV-76 (afternoon)
- [ ] Test SL/TP monitoring (afternoon)
- [ ] Update reality checks (evening)
- [ ] Phase 2 verification (evening)

**Estimated Total**: 6-8 hours of work

---

## 🎯 Success Metrics

### Phase 2 Complete When:
1. ✅ ExecutionAgent inherits from PeriodicAgent
2. ✅ Positions update every 10 seconds
3. ✅ Unrealized PnL calculated correctly
4. ✅ SL orders monitored and trigger auto-closure
5. ✅ TP orders monitored and trigger auto-closure
6. ✅ Reality checks pass (2/2 new checks)
7. ✅ No errors in position monitoring logs

### Reality Check Target
```
📊 Summary: 7/7 issues passing all checks

Phase 1 (5/5) ✅
Phase 2 (2/2) ✅
```

---

## 🚨 Risks & Mitigation

### Risk 1: Periodic Task Conflicts
**Issue**: Message-driven execution might conflict with periodic tasks
**Mitigation**: Keep both - message-driven for order processing, periodic for monitoring

### Risk 2: Exchange API Rate Limits
**Issue**: Checking order status every 10s might hit rate limits
**Mitigation**:
- Cache order status for 5 seconds
- Only check orders for open positions
- Use batch order status if available

### Risk 3: Position Manager In-Memory State
**Issue**: Position manager stores state in memory, periodic updates might not persist
**Mitigation**: Always update database after position changes (already implemented in DEV-74)

### Risk 4: SL/TP Order IDs Not Tracked
**Issue**: Need to store order IDs when placing SL/TP
**Mitigation**: Update `_place_stop_loss()` and `_place_take_profit()` to return and store order IDs

---

## 📝 Notes

- ExecutionAgent will be **hybrid**: message-driven + periodic
- Message-driven: Process trade.order messages (existing functionality)
- Periodic: Monitor positions and SL/TP orders (new functionality)
- Both can coexist using asyncio tasks

---

**Last Updated**: 2025-10-10 18:20 UTC
**Next Review**: After DEV-75 completion
