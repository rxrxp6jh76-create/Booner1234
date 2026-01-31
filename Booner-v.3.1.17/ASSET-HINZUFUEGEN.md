# Anleitung: Neues Asset/Commodity hinzufügen (Booner V3.2.9)

**Stand:** 15.01.2026

Diese Kurz-Checkliste kombiniert die bestehende Anleitung mit den Fixes für GBPUSD (Card-Sichtbarkeit & Handelszeiten).

## Schritte

1) **COMMODITIES pflegen (Backend)**
   - Datei: backend/server.py
   - Block: COMMODITIES (ca. Zeile 400 ff.)
    - Eintrag hinzufügen inkl. `trading_hours`, Plattformen, Symbole.
   - Beispiel GBPUSD:
     ```python
     "GBPUSD": {
         "name": "GBP/USD",
         "symbol": "GBPUSD=X",
         "mt5_libertex_symbol": "GBPUSD",
         "mt5_icmarkets_symbol": "GBPUSD",
         "category": "Forex",
         "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS"],
         "trading_hours": "24/5 (So 22:00 - Fr 21:00 UTC)"
     }
     ```

2) **COMMODITIES spiegeln (Processor)**
   - Datei: backend/commodity_processor.py
   - Gleichen Eintrag mit `trading_hours` hinterlegen (wird für Markt/DB genutzt).

3) **AssetConfig**
   - Datei: backend/config.py
   - AssetConfig-Eintrag anlegen (Name, Klasse, Symbole, Spreads, Volatilität).

4) **Data Feeds / Mappings**
   - Datei: backend/hybrid_data_fetcher.py → Maps für MetaAPI/YFinance ergänzen.
   - MetaAPI-Whitelist in backend/commodity_processor.py (Live + OHLCV) erweitern.
   - Marktzeiten bei Bedarf in backend/commodity_market_hours.py ergänzen.

5) **Enabled-Listen**
   - Primäre Liste in backend/server.py (`enabled_commodities`) ergänzen.
   - Default-Settings in server.py (DB-Defaults) prüfen, falls dort gespiegelt.

6) **Routen/Mapping**
   - trade_routes, market_routes, ggf. ai_routes prüfen, ob Symbol-Mappings nötig.
   - Backend-Route `/market/all` (backend/server.py) muss Platzhalter liefern, wenn keine Marktdaten existieren, damit neue Cards sofort erscheinen.
   - Hinweis: market_routes in electron-app liefert ebenfalls Platzhalter, falls die App den gebündelten Backend-Code nutzt.

7) **Settings-DB aktualisieren**
   - Falls bestehende `trading_settings` ohne neues Asset gespeichert sind: `/settings/reset` oder `/settings` mit neuer `enabled_commodities`-Liste aufrufen.

8) **Frontend**
   - Cards rendern aus `/market/all` → `markets` + `commodities`. Nach Backend-Änderungen hart neu laden.
   - Settings (Tab "Allgemein" → Handelszeiten-Block): Der neue `MarketHoursManager` lädt alle Assets dynamisch über `/api/market/hours/all` und zeigt oben den Debug-Balken „Geladene Assets / Aktiv ausgewählt“. Wenn dort < 50 angezeigt werden, liefert Backend/Cache nicht alle Assets.

9) **Backend neu starten**
   - z.B. `./Neustart der App/neustart-backend.command` oder Supervisor.

10) **Verifizieren**
   - `/market/all` prüfen: Neues Asset in `markets` und `commodities` vorhanden? trading_hours sichtbar?
   - Dashboard: Neue Card erscheint, Handelszeiten nicht "nicht verfügbar".

## Troubleshooting (Card fehlt / Zeiten fehlen)
- Card fehlt: Prüfe `/market/all`; wenn Asset fehlt, ist es nicht in COMMODITIES oder `enabled_commodities`/Settings.
- Preis 0: Erstes Fetch/Refresh abwarten oder `fetch_commodity_data` anstoßen.
- Handelszeiten "nicht verfügbar": `trading_hours` im COMMODITIES-Eintrag setzen (server.py + commodity_processor.py).
- Settings-Altlast: `trading_settings` resetten oder `enabled_commodities` per API aktualisieren.
- Settings zeigt weniger als 50 Assets: `/api/market/hours/all` prüfen und Backend/Cache neu starten; der MarketHoursManager rendert exakt, was die Route zurückgibt.

## Mini-Template für neue Assets
```python
"MY_ASSET": {
    "name": "My Asset",
    "symbol": "TICKER",
   "mt5_libertex_symbol": "TICKER_MT5",
   "mt5_icmarkets_symbol": "TICKER_ICM",
    "category": "Forex|Edelmetalle|Energie|Agrar|Industriemetalle|Crypto|Indizes",
    "platforms": ["MT5_LIBERTEX", "MT5_ICMARKETS"],
    "trading_hours": "24/5 (So 22:00 - Fr 21:00 UTC)",
    "note": "Optional"
}
```
