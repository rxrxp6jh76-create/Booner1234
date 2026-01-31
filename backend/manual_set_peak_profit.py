import asyncio
import json
import aiosqlite


# Für echten Test: trades.db und eine existierende mt5_...-ID
DB_PATH = 'backend/trades.db'
TRADE_ID = 'mt5_75957850'  # Beispiel-ID aus aktueller Auslese
PEAK_PROFIT = 999.99  # Testwert

async def set_peak_profit(trade_id, peak_profit):
    async with aiosqlite.connect(DB_PATH) as db:
        # Prüfe, ob Eintrag existiert
        async with db.execute("SELECT trade_id FROM trade_settings WHERE trade_id = ?", (trade_id,)) as cursor:
            row = await cursor.fetchone()
        if row:
            # Update
            await db.execute(
                "UPDATE trade_settings SET peak_profit = ? WHERE trade_id = ?",
                (peak_profit, trade_id)
            )
        else:
            # Insert
            await db.execute(
                "INSERT INTO trade_settings (trade_id, peak_profit) VALUES (?, ?)",
                (trade_id, peak_profit)
            )
        await db.commit()
        print(f"Peak-Profit für {trade_id} gesetzt: {peak_profit}")

if __name__ == "__main__":
    asyncio.run(set_peak_profit(TRADE_ID, PEAK_PROFIT))
