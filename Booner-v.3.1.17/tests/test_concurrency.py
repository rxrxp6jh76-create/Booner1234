import asyncio
import sys
import types
import logging

# Enable logging to debug test failures
logging.basicConfig(level=logging.DEBUG)

# Prevent heavy external SDK import during tests by inserting a dummy module
sys.modules['metaapi_sdk_connector'] = types.ModuleType('metaapi_sdk_connector')
setattr(sys.modules['metaapi_sdk_connector'], 'MetaAPISDKConnector', lambda *args, **kwargs: None)

from backend.multi_platform_connector import MultiPlatformConnector


class DummyConnector:
    def __init__(self, delay=0.2):
        self.delay = delay

    async def create_market_order(self, symbol, order_type, volume, sl=None, tp=None):
        # Simulate network latency / remote execution
        print(f"[DummyConnector] create_market_order called for {symbol}")
        await asyncio.sleep(self.delay)
        return {"success": True, "ticket": "T123"}


def test_execute_trade_concurrent_same_symbol():
    """Test dass simultane Trade-Öffnungen für gleiches Asset blockiert werden"""
    async def inner():
        mpc = MultiPlatformConnector()

        # Prepare a dummy platform (mimic the real platform object structure)
        mpc.platforms['MT5_LIBERTEX_DEMO'] = {
            'type': 'MT5',
            'name': 'MT5 Libertex Demo',
            'connector': DummyConnector(delay=0.1),
            'active': True,
            'balance': 10000.0,
            'is_real': False
        }

        print("\n[TEST] Starte parallele execute_trade Aufrufe...")
        
        # Run two concurrent execute_trade calls for the same symbol
        task1 = mpc.execute_trade('MT5_LIBERTEX_DEMO', 'XAUUSD', 'BUY', 0.01)
        task2 = mpc.execute_trade('MT5_LIBERTEX_DEMO', 'XAUUSD', 'BUY', 0.01)
        
        results = await asyncio.gather(task1, task2)

        print(f"\n[TEST] Ergebnisse: {results}")
        
        successes = [r for r in results if r and r.get('success')]
        failures = [r for r in results if not (r and r.get('success'))]

        print(f"[TEST] Erfolge: {len(successes)}, Fehler: {len(failures)}")
        print(f"[TEST] Erfolg-Details: {successes}")
        print(f"[TEST] Fehler-Details: {failures}")

        # Exactly one success, at least one failure indicating duplicate prevention
        assert len(successes) == 1, f"Erwartet exakt einen erfolgreichen Trade, got {results}"
        assert len(failures) == 1, f"Erwartet ein Fehlschlag durch Lock, got {results}"
        error_msg = failures[0].get('error')
        assert error_msg in ['Another trade for this commodity is in progress', 'Cooldown active for this commodity'], \
            f"Erwarteter Lock-Fehler, got: {error_msg}"

    asyncio.run(inner())
