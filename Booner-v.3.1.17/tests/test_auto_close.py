import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from backend.ai_trading_bot import AITradingBot

@pytest.mark.asyncio
async def test_check_auto_close_events_closes_profitable_trades(monkeypatch):
    bot = AITradingBot()
    bot.settings = {
        'active_platforms': ['MT5_LIBERTEX_DEMO'],
        'auto_close_profitable_daily': True,
        'auto_close_all_friday': False,
        'auto_close_minutes_before': 60
    }

    # Mock positions: one profitable position for platform
    profit_pos = {'ticket': '111', 'symbol': 'XAUUSD', 'profit': 12.5}

    import multi_platform_connector
    multi_platform_connector.multi_platform.get_open_positions = AsyncMock(return_value=[profit_pos])

    # Mock commodity_market_hours to return that this position should be closed
    import commodity_market_hours
    async def fake_get_positions_to_close_before_market_end(db, positions, close_profitable_daily, close_all_friday, minutes_before_close):
        return [{'ticket': '111', 'symbol': 'XAUUSD', 'commodity_id': 'GOLD', 'profit': 12.5}]
    monkeypatch.setattr('backend.ai_trading_bot.commodity_market_hours.get_positions_to_close_before_market_end', fake_get_positions_to_close_before_market_end)

    # Mock DB and close method
    bot.db = SimpleNamespace(trade_settings=SimpleNamespace(find_one=AsyncMock(return_value={'trade_id': 'mt5_111'})))
    closed = {}
    async def fake_close(trade):
        closed['called_with'] = trade
        return True
    bot._close_trade_via_connector = AsyncMock(side_effect=fake_close)

    await bot.check_auto_close_events()

    assert 'called_with' in closed
    assert closed['called_with'].get('trade_id') == 'mt5_111'