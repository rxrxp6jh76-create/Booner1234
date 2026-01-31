import asyncio
from database_v2 import SettingsDatabase

async def main():
    db = SettingsDatabase()
    await db.connect()
    await db.initialize_schema()
    print("Settings-Datenbank und Tabelle trading_settings initialisiert.")
    await db.close()

if __name__ == "__main__":
    asyncio.run(main())
