import aiosqlite
import asyncio

DB_PATH_SETTINGS = 'backend/settings.db'  # Für trading_settings
DB_PATH_TRADES = 'backend/trades.db'     # Für trades

async def check_peak_profits():
    # trade_settings (Trades DB)
    try:
        print('--- trade_settings (trades.db) ---')
        async with aiosqlite.connect(DB_PATH_TRADES) as db:
            async with db.execute("SELECT trade_id, peak_profit, peak_progress_percent FROM trade_settings") as cursor:
                print(f"{'Trade ID':<30} | {'Peak-Profit':>12} | {'Peak-Progress':>13}")
                print("-" * 60)
                async for row in cursor:
                    trade_id, peak_profit, peak_progress = row
                    peak_str = f"{peak_profit:.2f}" if peak_profit is not None else "-"
                    progress_str = f"{peak_progress:.2f}" if peak_progress is not None else "-"
                    print(f"{trade_id:<30} | {peak_str:>12} | {progress_str:>13}")
    except Exception as e:
        print(f"trade_settings Fehler: {e}")

    # trades (Trades DB)
    try:
        print('\n--- trades (trades.db) ---')
        async with aiosqlite.connect(DB_PATH_TRADES) as db:
            async with db.execute("SELECT id, peak_profit FROM trades") as cursor:
                print(f"{'Trade ID':<20} | {'Peak-Profit':>12}")
                print("-" * 36)
                async for row in cursor:
                    trade_id, peak_profit = row
                    peak_str = f"{peak_profit:.2f}" if peak_profit is not None else "-"
                    print(f"{trade_id:<20} | {peak_str:>12}")
    except Exception as e:
        print(f"trades Fehler: {e}")

if __name__ == "__main__":
    asyncio.run(check_peak_profits())
