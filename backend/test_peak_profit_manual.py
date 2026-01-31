
import asyncio
from database import trade_settings, init_database

async def test_peak_profit_update():
    # Initialisiere die Datenbank (Multi-DB oder Legacy)
    await init_database()
    # Testdaten
    trade_id = "mt5_TEST123"
    entry_price = 100.0
    quantity = 1.0

    # Simuliere verschiedene aktuelle Preise
    prices = [105.0, 110.0, 108.0, 115.0, 112.0]
    expected_peak = 15.0  # Höchster Gewinn: 115 - 100 = 15

    # Setze initialen Wert
    await trade_settings.update_one({"trade_id": trade_id}, {"$set": {"entry_price": entry_price, "peak_profit": 0}}, upsert=True)

    for current_price in prices:
        profit_now = (current_price - entry_price) * quantity
        settings = await trade_settings.find_one({"trade_id": trade_id})
        prev_peak = settings.get("peak_profit") if settings else None
        if prev_peak is None or profit_now > prev_peak:
            await trade_settings.update_one({"trade_id": trade_id}, {"$set": {"peak_profit": profit_now}}, upsert=True)
        print(f"Aktueller Preis: {current_price}, Peak: {prev_peak} -> {profit_now}")

    # Endgültigen Wert prüfen
    settings = await trade_settings.find_one({"trade_id": trade_id})
    print(f"Gespeicherter Peak-Profit: {settings.get('peak_profit')}, Erwartet: {expected_peak}")
    assert abs(settings.get('peak_profit') - expected_peak) < 0.01, "Peak-Profit wurde nicht korrekt gespeichert!"


if __name__ == "__main__":
    asyncio.run(test_peak_profit_update())
