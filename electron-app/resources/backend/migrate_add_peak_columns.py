import sqlite3

DB_PATH = './trades.db'  # Passe den Pfad ggf. an

with sqlite3.connect(DB_PATH) as conn:
    cur = conn.cursor()
    # Füge peak_profit und peak_progress_percent zu trade_settings hinzu
    try:
        cur.execute("ALTER TABLE trade_settings ADD COLUMN peak_profit REAL")
        print("Spalte peak_profit zu trade_settings hinzugefügt.")
    except Exception as e:
        print(f"trade_settings: peak_profit: {e}")
    try:
        cur.execute("ALTER TABLE trade_settings ADD COLUMN peak_progress_percent REAL")
        print("Spalte peak_progress_percent zu trade_settings hinzugefügt.")
    except Exception as e:
        print(f"trade_settings: peak_progress_percent: {e}")
    # Füge peak_profit und peak_progress_percent zu trades hinzu
    try:
        cur.execute("ALTER TABLE trades ADD COLUMN peak_profit REAL")
        print("Spalte peak_profit zu trades hinzugefügt.")
    except Exception as e:
        print(f"trades: peak_profit: {e}")
    try:
        cur.execute("ALTER TABLE trades ADD COLUMN peak_progress_percent REAL")
        print("Spalte peak_progress_percent zu trades hinzugefügt.")
    except Exception as e:
        print(f"trades: peak_progress_percent: {e}")
    conn.commit()
print("Migration abgeschlossen.")
