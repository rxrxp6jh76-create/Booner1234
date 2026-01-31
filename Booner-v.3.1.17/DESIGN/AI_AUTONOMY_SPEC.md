# AI Autonomy - Technical Specification (Short)

## Goals
- Fully autonomous in-app trade lifecycle management: open, monitor, adjust, close.
- MT5 (or connectors) only execute open/close actions (no in-platform SL/TP management).
- Per-account (platform) single-trade per asset + platform-scoped cooldown (default 15 minutes).
- DB-backed reservations to prevent duplicates across processes; in-memory locks for same-process.
- EoD (asset trading day end) and Friday pre-close profit-taking option.
- Trade openings gated by 4-pillar confidence thresholds (conservative/standard/aggressive settings).
- Monitoring loop to adjust strategy or SL/TP to maximize profit probability.

## Key Components and Acceptance Criteria

1. Platform-scoped DB Reservations
   - Resource id format: `<platform>:<commodity>`.
   - Methods: `reserve_resource`, `release_resource`, `is_resource_reserved` (already implemented in `database_v2.py`).
   - Acceptance: concurrent reservation attempts only allow one owner.

2. Per-account Cooldown
   - Implemented in `AITradingBot.mark_trade_opened` as platform-scoped cooldown key.
   - Default minutes: 15 (configurable via `ai_per_account_cooldown_minutes`).
   - Acceptance: preventing openings on same platform & commodity within cooldown window.

3. AI Trade Lifecycle
   - `execute_ai_trade`: do platform selection, reserve DB resource, acquire in-process lock, open trade via connector with SL/TP = None, write trade to DB (strategy, analysis, confidence), set cooldown.
   - `monitor_open_positions`: periodic task to evaluate open trades and optionally adjust strategy or SL/TP in-app; closes via connector when close condition met.
   - `adjust_open_trade`: logic to apply new SL/TP or strategy in DB and triggers action if immediate close required.

4. EoD & Friday Close
   - Scheduler checks asset trading times (via `commodity_processor`) and closes profitable trades at day end or on Friday pre-close when configured.

5. Confidence Gate
   - Settings provide thresholds for conservative/standard/aggressive; analyses must meet min_confidence per strategy to open.

6. Tests
   - Unit tests for per-account cooldown, DB reservation multi-process simulation, monitor/adjust/close behaviors and EoD/Friday closures.

## Implementation Plan (Short)
1. Add/adjust methods in `AITradingBot` for platform-scoped reservation/cooldown and monitoring task.
2. Add tests: `tests/test_db_reservations.py` (exists), `tests/test_ai_per_account_cooldown.py` (exists), plus `tests/test_ai_monitoring.py`.
3. Add logging instrumentation in platform selection to debug Libertex bias.
4. Commit changes on branch `feature/ai-autonomy` and open PR.

## Config Keys
- `ai_per_account_cooldown_minutes` (int, default 15)
- `ai_db_reservation_ttl_seconds` (int, default 60)
- `ai_monitor_interval_seconds` (int, default 30)
- `confidence_profile` (one of `conservative|standard|aggressive`) and mapping to numeric thresholds
- `auto_close_profitable_daily`, `auto_close_all_friday` (existing flags supported)


# Notes
- All changes aim to modify existing code and tests primarily. New helper tests/files may be added for coverage.
