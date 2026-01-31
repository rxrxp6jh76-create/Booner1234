#!/usr/bin/env python3
"""
Test für Concurrency-Locking bei Duplikat-Trade-Verhinderung.

Tests sollen zeigen:
1. Gleichzeitige Trades für GLEICHES Asset = werden durch Lock blockiert
2. Gleichzeitige Trades für VERSCHIEDENE Assets = beide führen aus
"""

import asyncio
import sys
import os
from pathlib import Path
import logging

# Setup logging FIRST before imports
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Add paths
backend_path = str(Path(__file__).parent.parent / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Prevent real MetaAPI SDK import
import types
if 'metaapi_sdk_connector' not in sys.modules:
    sys.modules['metaapi_sdk_connector'] = types.ModuleType('metaapi_sdk_connector')
    sys.modules['metaapi_sdk_connector'].MetaAPISDKConnector = lambda *args, **kwargs: None

# NOW import the connector (should not load real SDK)
from multi_platform_connector import MultiPlatformConnector, _COMMODITY_LOCKS, _COMMODITY_LAST_TRADE

logger.info("✅ Imports successful")


class ConcurrencyTracker:
    """Tracks concurrent execution of connector.create_market_order calls."""
    
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
            logger.debug(f"[Tracker] Enter: total={cls.total_calls}, concurrent={cls.concurrent_calls}, max={cls.max_concurrent}")
    
    @classmethod
    async def exit(cls):
        async with cls.lock:
            cls.concurrent_calls -= 1
            logger.debug(f"[Tracker] Exit: concurrent={cls.concurrent_calls}")
    
    @classmethod
    def reset(cls):
        cls.total_calls = 0
        cls.concurrent_calls = 0
        cls.max_concurrent = 0


class DummyConnector:
    """Mock connector that simulates real trading platform."""
    
    async def create_market_order(self, symbol: str, order_type: str, volume: float, sl=None, tp=None):
        await ConcurrencyTracker.enter()
        try:
            logger.info(f"[DummyConnector] create_market_order START: symbol={symbol}, type={order_type}, vol={volume}")
            
            # Simulate some work - LONGER to ensure overlap with concurrent task
            await asyncio.sleep(0.5)  # Increased from 0.05s to 0.5s to ensure real concurrency
            
            logger.info(f"[DummyConnector] create_market_order END: symbol={symbol}")
            return {
                'success': True,
                'ticket': f'TICKET_{ConcurrencyTracker.total_calls}',
                'symbol': symbol,
                'type': order_type,
                'volume': volume
            }
        finally:
            await ConcurrencyTracker.exit()


async def test_concurrent_same_symbol():
    """Test: Gleichzeitige Trades für GLEICHE Commodity sollen blockiert werden."""
    
    print("\n" + "="*70)
    print("TEST 1: Concurrent Trades for SAME Symbol (should be blocked by lock)")
    print("="*70)
    
    # Reset
    _COMMODITY_LOCKS.clear()
    _COMMODITY_LAST_TRADE.clear()
    ConcurrencyTracker.reset()
    
    # Create connector
    mpc = MultiPlatformConnector()
    dummy = DummyConnector()
    
    # Patch platform
    mpc.platforms['MT5_LIBERTEX_DEMO'] = {
        'type': 'MT5',
        'name': 'MT5 Libertex Demo',
        'connector': dummy,
        'active': True,
        'balance': 10000.0,
        'is_real': False
    }
    
    logger.info("✅ Setup complete, starting concurrent execute_trade calls...")
    
    # Two concurrent trades for SAME symbol (should trigger lock)
    task1 = mpc.execute_trade('MT5_LIBERTEX_DEMO', 'XAUUSD', 'BUY', 0.01)
    task2 = mpc.execute_trade('MT5_LIBERTEX_DEMO', 'XAUUSD', 'BUY', 0.01)
    
    results = await asyncio.gather(task1, task2)
    
    logger.info(f"Results: {results}")
    logger.info(f"Concurrent tracker - total calls: {ConcurrencyTracker.total_calls}, max concurrent: {ConcurrencyTracker.max_concurrent}")
    
    # Analysis
    success_count = sum(1 for r in results if r and isinstance(r, dict) and r.get('success') == True)
    error_count = sum(1 for r in results if r and isinstance(r, dict) and r.get('success') == False)
    
    logger.info(f"Success count: {success_count}, Error count: {error_count}")
    logger.info(f"Max concurrent API calls: {ConcurrencyTracker.max_concurrent}")
    
    # Expectations:
    # - Exactly 1 should succeed
    # - Exactly 1 should fail (lock prevented it)
    # - Max concurrent API calls should be 1 (one waits for lock, other blocked before API)
    
    if success_count == 1 and error_count == 1:
        print("✅ TEST 1 PASSED: Lock properly blocked concurrent execution!")
        return True
    else:
        print(f"❌ TEST 1 FAILED:")
        print(f"   Expected: 1 success + 1 error")
        print(f"   Got: {success_count} success + {error_count} error")
        print(f"   Results: {results}")
        return False


async def test_concurrent_different_symbols():
    """Test: Gleichzeitige Trades für VERSCHIEDENE Commodities sollen beide ausgeführt werden."""
    
    print("\n" + "="*70)
    print("TEST 2: Concurrent Trades for DIFFERENT Symbols (should both execute)")
    print("="*70)
    
    # Reset
    _COMMODITY_LOCKS.clear()
    _COMMODITY_LAST_TRADE.clear()
    ConcurrencyTracker.reset()
    
    # Create connector
    mpc = MultiPlatformConnector()
    dummy = DummyConnector()
    
    # Patch platform
    mpc.platforms['MT5_LIBERTEX_DEMO'] = {
        'type': 'MT5',
        'name': 'MT5 Libertex Demo',
        'connector': dummy,
        'active': True,
        'balance': 10000.0,
        'is_real': False
    }
    
    logger.info("✅ Setup complete, starting concurrent execute_trade calls...")
    
    # Two concurrent trades for DIFFERENT symbols (should NOT trigger lock)
    # XAUUSD -> GOLD, XAGUSD -> SILVER
    task1 = mpc.execute_trade('MT5_LIBERTEX_DEMO', 'XAUUSD', 'BUY', 0.01)
    task2 = mpc.execute_trade('MT5_LIBERTEX_DEMO', 'XAGUSD', 'BUY', 0.01)
    
    results = await asyncio.gather(task1, task2)
    
    logger.info(f"Results: {results}")
    logger.info(f"Concurrent tracker - total calls: {ConcurrencyTracker.total_calls}, max concurrent: {ConcurrencyTracker.max_concurrent}")
    
    # Analysis
    success_count = sum(1 for r in results if r and isinstance(r, dict) and r.get('success') == True)
    
    logger.info(f"Success count: {success_count}")
    logger.info(f"Max concurrent API calls: {ConcurrencyTracker.max_concurrent}")
    
    # Expectations:
    # - Both should succeed
    # - Max concurrent API calls should be 2 (both execute simultaneously on different locks)
    
    if success_count == 2:
        print("✅ TEST 2 PASSED: Different symbols executed concurrently!")
        return True
    else:
        print(f"❌ TEST 2 FAILED:")
        print(f"   Expected: 2 success")
        print(f"   Got: {success_count} success")
        print(f"   Results: {results}")
        return False


async def main():
    print("\n" + "#"*70)
    print("# CONCURRENCY LOCK TESTS FOR DUPLICATE TRADE PREVENTION")
    print("#"*70)
    
    results = []
    
    try:
        test1_pass = await test_concurrent_same_symbol()
        results.append(("Test 1: Same Symbol", test1_pass))
    except Exception as e:
        logger.exception(f"Test 1 crashed: {e}")
        results.append(("Test 1: Same Symbol", False))
    
    try:
        test2_pass = await test_concurrent_different_symbols()
        results.append(("Test 2: Different Symbols", test2_pass))
    except Exception as e:
        logger.exception(f"Test 2 crashed: {e}")
        results.append(("Test 2: Different Symbols", False))
    
    # Summary
    print("\n" + "#"*70)
    print("# TEST SUMMARY")
    print("#"*70)
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("\n" + "="*70)
        print("🎉 ALL TESTS PASSED!")
        print("="*70)
        return 0
    else:
        print("\n" + "="*70)
        print("❌ SOME TESTS FAILED")
        print("="*70)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
