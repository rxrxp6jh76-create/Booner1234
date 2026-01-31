import pytest
from datetime import datetime, timedelta, timezone

from backend.autonomous_trading_intelligence import AutonomousTradingIntelligence


def _entry_time(minutes_ago: int = 45) -> str:
    """Build an ISO timestamp that is safely past the 30 minute gate."""
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def test_profit_drawdown_exit_triggers_after_peak_loss():
    ati = AutonomousTradingIntelligence()
    entry_time = _entry_time()

    ati.register_trade_for_risk_monitoring(
        trade_id="t1",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        strategy="grid",
        entry_time_override=entry_time,
        initial_profit=100.0,
    )

    result = ati.check_risk_circuits(
        "t1",
        current_price=102.0,  # 20% progress to TP (below breakeven/trigger gates)
        current_profit=89.0,   # 11% below peak → should exit
    )

    assert result["action"] == "profit_drawdown_exit"
    assert "Gewinn -10% vom Peak" in result["reason"]


def test_profit_drawdown_exit_stays_idle_below_threshold():
    ati = AutonomousTradingIntelligence()
    entry_time = _entry_time()

    ati.register_trade_for_risk_monitoring(
        trade_id="t2",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        strategy="grid",
        entry_time_override=entry_time,
        initial_profit=100.0,
    )

    result = ati.check_risk_circuits(
        "t2",
        current_price=102.0,
        current_profit=93.0,  # 7% below peak → should do nothing
    )

    assert result["action"] == "none"


def test_progress_drawdown_exit_triggers_without_profit_value():
    ati = AutonomousTradingIntelligence()
    entry_time = _entry_time()

    ati.register_trade_for_risk_monitoring(
        trade_id="t3",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        strategy="grid",
        entry_time_override=entry_time,
        initial_profit=None,
    )

    # Erste Messung setzt den Peak-Fortschritt auf 40 %.
    first = ati.check_risk_circuits(
        "t3",
        current_price=104.0,
        current_profit=None,
    )
    assert first["action"] == "none"

    # Rückgang auf 35 % Fortschritt (−12.5 % vom Peak) nach >=30min löst den Fallback aus.
    result = ati.check_risk_circuits(
        "t3",
        current_price=103.5,
        current_profit=None,
    )

    assert result["action"] == "profit_drawdown_exit"
