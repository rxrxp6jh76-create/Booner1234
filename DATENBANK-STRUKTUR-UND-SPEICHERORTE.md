# Datenbankstruktur und Speicherorte (Booner Desktop)

## Wichtige Datenbankdateien

- **Trades und Settings:**
  - Pfad: `~/Library/Application Support/booner-trade/database/trades.db`
  - Enthält: 
    - Tabelle `trade_settings`: SL, TP, Strategie, Entry-Preis, Commodity, Typ, peak_profit (neu)
    - Tabelle `trades`: Geschlossene Trades
- **Globale Einstellungen:**
  - Pfad: `~/Library/Application Support/booner-trade/database/settings.db`
  - Enthält: Tabelle `trading_settings`
- **Marktdaten:**
  - Pfad: `~/Library/Application Support/booner-trade/database/market_data.db`
  - Enthält: Tabelle `market_data`

## Peak-Profit Speicherung
- Der aktuelle Peak-Profit für offene Trades wird in der Spalte `peak_profit` der Tabelle `trade_settings` gespeichert.
- Die Zuordnung erfolgt über die Spalte `trade_id` (z.B. `mt5_123456`).

## Hinweise
- Alle Pfade beziehen sich auf den aktuellen macOS-User.
- Die Datenbank wird beim Start der App automatisch angelegt und erweitert.
- Änderungen an der Struktur (z.B. neue Spalten) werden migrationssicher per `ALTER TABLE` durchgeführt.
