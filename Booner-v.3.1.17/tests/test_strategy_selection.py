import pytest
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from backend.ai_trading_bot import AITradingBot

@pytest.mark.asyncio
async def test_execute_ai_trade_switches_to_recommended_strategy(monkeypatch):
    bot = AITradingBot()

    # Minimal settings so that platform selection works
    bot.settings = {
        'active_platforms': ['MT5_LIBERTEX_DEMO'],
        'day_trading_enabled': True,
        'scalping_enabled': True,
        'swing_enabled': True,
        'momentum_enabled': True,
        'breakout_enabled': True,
        'mean_reversion_enabled': True,
        'grid_enabled': True,
        'combined_max_balance_percent_per_platform': 20.0,
        'ai_per_account_cooldown_minutes': 1,
        'ai_db_reservation_ttl_seconds': 30
    }

    # Mock autonomous_trading behaviour: initial strategy unsuitable, recommend 'scalping'
    monkeypatch.setattr('backend.ai_trading_bot.autonomous_trading.is_strategy_suitable_for_market', lambda s, m: (False, 'market not suitable'))
    monkeypatch.setattr('backend.ai_trading_bot.autonomous_trading.select_best_strategy', lambda ma, es, cid: ('scalping', 'alt fits market'))

    # Mock multi_platform connector
    import multi_platform_connector
    multi_platform_connector.multi_platform.get_account_info = AsyncMock(return_value={'balance': 1000, 'margin': 0, 'equity': 1000})
    multi_platform_connector.multi_platform.get_open_positions = AsyncMock(return_value=[])
    multi_platform_connector.multi_platform.execute_trade = AsyncMock(return_value={'success': True, 'ticket': '555'})

    # Mock DB (simple AsyncMock collections)
    async def fake_find_one(q):
        return None
    async def fake_insert_one(doc):
        fake_insert_one.called_with = doc
    bot.db = SimpleNamespace(
        trades=SimpleNamespace(insert_one=AsyncMock(side_effect=fake_insert_one)),
        trade_settings=SimpleNamespace(update_one=AsyncMock())
    )

    # Provide minimal analysis object
    analysis = {
        'signal': 'BUY',
        'confidence': 80,
        'indicators': {'current_price': 100}
    }

    # Run execute_ai_trade with initial strategy that is unsuitable
    await bot.execute_ai_trade('GOLD', 'BUY', analysis, strategy='swing')

    # Check that a trade insert happened and strategy written is 'scalping' (recommended)
    inserted = getattr(fake_insert_one, 'called_with', None)
    assert inserted is not None, "Trade was not inserted into db.trades"
    assert inserted.get('strategy') == 'scalping', f"Expected strategy to be 'scalping', got {inserted.get('strategy')}"


@pytest.mark.asyncio
async def test_execute_ai_trade_aborts_if_no_alternative(monkeypatch):
    bot = AITradingBot()
    bot.settings = {'active_platforms': ['MT5_LIBERTEX_DEMO']}

    monkeypatch.setattr('backend.ai_trading_bot.autonomous_trading.is_strategy_suitable_for_market', lambda s, m: (False, 'not ok'))
    # Recommend no alternative
    monkeypatch.setattr('backend.ai_trading_bot.autonomous_trading.select_best_strategy', lambda ma, es, cid: (None, None))

    # Mock multi_platform to avoid external calls
    import multi_platform_connector
    multi_platform_connector.multi_platform.get_account_info = AsyncMock(return_value={'balance': 1000, 'margin': 0, 'equity': 1000})
    multi_platform_connector.multi_platform.get_open_positions = AsyncMock(return_value=[])

    bot.db = SimpleNamespace(trades=SimpleNamespace(insert_one=AsyncMock()))

    analysis = {'signal': 'BUY', 'confidence': 85, 'indicators': {'current_price': 100}}

    # Should not raise but also not insert a trade
    await bot.execute_ai_trade('GOLD', 'BUY', analysis, strategy='swing')
    assert not bot.db.trades.insert_one.called, "Trade should not be inserted when no alternative strategy found"