#!/usr/bin/env python3
"""
Test AI monitoring evaluate & close logic.
"""
import asyncio
import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.DEBUG, format='[%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

backend_path = str(Path(__file__).parent.parent / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from ai_trading_bot import AITradingBot

async def test_evaluate_and_close_called():
    bot = AITradingBot()
    # Minimal settings
    bot.settings = {
        'ai_monitor_interval_seconds': 1,
        'ai_per_account_cooldown_minutes': 15,
        'ai_db_reservation_ttl_seconds': 60
    }

    # Stub get_price_history to return price info
    async def fake_price_history(commodity_id, days=1):
        return [{'price': 100.0}, {'price': 101.0}]
    bot.get_price_history = fake_price_history

    # Stub _analyze_and_suggest_adjustments to force close
    async def fake_suggest(commodity_id, strategy, price_history, trade_type=None):
        return {'close_now': True, 'confidence': 100}
    bot._analyze_and_suggest_adjustments = fake_suggest

    # Track if close called
    called = {'closed': False}
    async def fake_close(trade):
        called['closed'] = True
        return True
    bot._close_trade_via_connector = fake_close

    # Provide dummy db to avoid attribute errors
    class DummyDB:
        async def update_one(self, *a, **k):
            return True
    bot.db = type('DB', (), {'trades': DummyDB(), 'trade_settings': DummyDB()})()

    # Fake trade
    trade = {
        'trade_id': 't1',
        'commodity_id': 'GOLD',
        'platform': 'MT5_LIBERTEX_DEMO',
        'strategy': 'day',
        'type': 'BUY',
        'mt5_ticket': 'TICKET_1'
    }

    await bot._evaluate_and_adjust_trade(trade)

    assert called['closed'] is True
    print("✅ TEST PASSED: monitor triggered close via connector")

if __name__ == '__main__':
    rc = asyncio.run(test_evaluate_and_close_called())
    sys.exit(0)
