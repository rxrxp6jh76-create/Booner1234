import asyncio
import sys
sys.path.append('../electron-app/resources/backend')
from database_v2 import DatabaseManager
import commodity_market_hours as cmh

async def update():
    dbm = DatabaseManager()
    await dbm.connect_all()
    await dbm.initialize_all()
    settings = await dbm.settings_db.get_settings()
    if not settings:
        settings = {"id": "trading_settings"}
    settings["market_hours"] = cmh.DEFAULT_MARKET_HOURS
    await dbm.settings_db.save_settings(settings)
    print('DB updated')
    await dbm.close_all()

if __name__ == "__main__":
    asyncio.run(update())
