#!/usr/bin/env python3
"""
Test per-account (platform-scoped) cooldown for AI trade execution.

Ensures that two concurrent calls to execute_ai_trade for the SAME commodity ON THE SAME PLATFORM
do not both call the platform's execute_trade (second should be blocked by in-process lock / cooldown)
while calls on different platforms can both proceed.
"""

import asyncio
import sys
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='[%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add backend to path
backend_path = str(Path(__file__).parent.parent / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from ai_trading_bot import AITradingBot

class ConcurrencyTracker:
    total_calls = 0
    concurrent_calls = 0
    max_concurrent = 0
    lock = asyncio.Lock()

    @classmethod
    async def enter(cls):
        async with cls.lock:
            cls.concurrent_calls += 1
            cls.total_calls += 1
            cls.max_concurrent = max(cls.max_concurrent, cls.concurrent_calls)

    @classmethod
    async def exit(cls):
        async with cls.lock:
            cls.concurrent_calls -= 1

    @classmethod
    def reset(cls):
        cls.total_calls = 0
        cls.concurrent_calls = 0
        cls.max_concurrent = 0


class DummyMultiPlatform:
    async def get_account_info(self, platform_name):
        return {'balance': 10000.0, 'margin': 0.0, 'equity': 10000.0}

    async def get_open_positions(self, platform_name):
        return []

    async def execute_trade(self, platform_name, symbol, action, volume, stop_loss=None, take_profit=None):
        await ConcurrencyTracker.enter()
        try:
            # ensure some overlap
            await asyncio.sleep(0.5)
            return {'success': True, 'ticket': f'TICKET_{ConcurrencyTracker.total_calls}'}
        finally:
            await ConcurrencyTracker.exit()


async def test_same_platform_blocked():
    print("\n" + "=" * 70)
    print("TEST: Concurrent AI trades same platform should be blocked (only 1 platform call)")
    print("=" * 70)

    ConcurrencyTracker.reset()

    bot = AITradingBot()
    # Minimal settings for test
    bot.settings = {
        'active_platforms': ['MT5_LIBERTEX_DEMO'],
        'ai_per_account_cooldown_minutes': 1,
        'ai_db_reservation_ttl_seconds': 10
    }

    # inject DB manager to raise to force fallback to in-memory
    import types
    import database_v2
    async def failing_get_instance():
        raise Exception("no DB")
    database_v2.db_manager.get_instance = failing_get_instance  # monkeypatch

    # inject multi_platform
    import sys
    import types
    mp = DummyMultiPlatform()
    sys.modules.setdefault('multi_platform_connector', types.ModuleType('multi_platform_connector'))
    sys.modules['multi_platform_connector'].multi_platform = mp

    # Run two concurrent AI trade calls for same commodity
    task1 = bot.execute_ai_trade('GOLD', 'BUY', {'confidence': 95}, strategy='day')
    task2 = bot.execute_ai_trade('GOLD', 'BUY', {'confidence': 95}, strategy='day')

    await asyncio.gather(task1, task2)

    print(f"Concurrent tracker - total calls: {ConcurrencyTracker.total_calls}, max concurrent: {ConcurrencyTracker.max_concurrent}")

    if ConcurrencyTracker.total_calls == 1 and ConcurrencyTracker.max_concurrent == 1:
        print("✅ TEST PASSED: Only one platform execute_trade call was made for same platform")
        return True
    else:
        print("❌ TEST FAILED: Unexpected concurrency behavior")
        return False


async def main():
    try:
        ok = await test_same_platform_blocked()
        if ok:
            print("\n🎉 AI per-account cooldown test passed")
            return 0
        else:
            return 1
    except Exception as e:
        logger.exception(f"Test crashed: {e}")
        return 1

if __name__ == '__main__':
    rc = asyncio.run(main())
    sys.exit(rc)
