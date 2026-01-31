"""
Commodity Market Hours Manager
Verwaltet individuelle Handelszeiten für jedes Asset/Commodity
"""

from datetime import datetime, timezone, time
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


# Default Handelszeiten für alle Commodities (Libertex, UTC Werte, MEZ/MESZ in Beschreibung)
FOREX_HOURS_DISPLAY = "Mo 00:05 – Fr 23:55 MEZ/MESZ (Libertex 24/5, minimale Pausen zum Tageswechsel)"
US_INDICES_HOURS_DISPLAY = "Mo 01:00 – Fr 23:00 MEZ/MESZ (Libertex Extended Hours)"
EU_INDICES_HOURS_DISPLAY = "Mo 01:00 – Fr 23:00 MEZ/MESZ (Libertex Extended Hours, außer IBEX/SMI/AEX)"
ASIA_INDICES_HOURS_DISPLAY = "Mo 01:00 – Fr 23:00 MEZ/MESZ (Libertex, tägliche Pausen je nach Index)"
METALS_HOURS_DISPLAY = "Mo 01:00 – Fr 23:00 MEZ/MESZ (Libertex, COMEX)"
ENERGY_HOURS_DISPLAY = "Mo 01:00 – Fr 23:00 MEZ/MESZ (Libertex, fast durchgehend)"
INDUSTRIAL_METALS_HOURS_DISPLAY = "Mo 01:00 – Fr 23:00 MEZ/MESZ (Libertex, LME/COMEX)"
AGRAR_HOURS_DISPLAY = "Mo-Fr, individuelle Zeiten je Produkt (Libertex, ICE/CBOT)"
CRYPTO_HOURS_DISPLAY = "24/7 (Libertex, keine Pause)"

FOREX_ASSETS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF", "USDCAD", "NZDUSD",
    "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "CHFJPY", "CADJPY",
    "AUDCAD", "AUDNZD", "EURNZD", "EURAUD", "GBPAUD"
]

US_INDICES_ASSETS = ["SP500", "DOWJONES30", "NASDAQ100", "RUSSELL2000", "VIX"]
EU_INDICES_ASSETS = ["DAX40", "FTSE100", "EUROSTOXX50", "CAC40", "IBEX35", "SMI20", "AEX25"]
ASIA_INDICES_ASSETS = ["NIKKEI225", "HANGSENG50", "ASX200"]
METAL_ASSETS = ["GOLD", "SILVER", "PLATINUM", "PALLADIUM"]
ENERGY_ASSETS = ["WTI_CRUDE", "BRENT_CRUDE", "NATURAL_GAS"]
INDUSTRIAL_ASSETS = ["COPPER", "ZINC"]
AGRAR_ASSETS = ["WHEAT", "CORN", "SOYBEANS", "COFFEE", "SUGAR", "COCOA"]
CRYPTO_ASSETS = ["BITCOIN", "ETHEREUM"]


FOREX_TEMPLATE = {
    "enabled": True,
    "days": [0, 1, 2, 3, 4],
    "open_time": "22:05",  # Mo 23:05 MEZ/MESZ (Libertex UTC)
    "close_time": "21:55", # Fr 22:55 MEZ/MESZ (Libertex UTC)
    "is_24_5": True,
    "description": "Mo 23:05 – Fr 22:55 UTC (Libertex 24/5, minimale Pausen zum Tageswechsel)"
}
METALS_TEMPLATE = {
    "enabled": True,
    "days": [0, 1, 2, 3, 4],
    "open_time": "00:00",  # Mo 01:00 MEZ/MESZ (Libertex UTC)
    "close_time": "22:00", # Fr 23:00 MEZ/MESZ (Libertex UTC)
    "is_24_5": True,
    "description": "Mo 01:00 – Fr 23:00 MEZ/MESZ (Libertex, COMEX)"
}
INDUSTRIAL_TEMPLATE = {
    "enabled": True,
    "days": [0, 1, 2, 3, 4],
    "open_time": "00:00",  # Mo 01:00 MEZ/MESZ (Libertex UTC)
    "close_time": "22:00", # Fr 23:00 MEZ/MESZ (Libertex UTC)
    "is_24_5": True,
    "description": "Mo 01:00 – Fr 23:00 MEZ/MESZ (Libertex, LME/COMEX)"
}
ENERGY_TEMPLATE = {
    "enabled": True,
    "days": [0, 1, 2, 3, 4],
    "open_time": "00:00",  # Mo 01:00 MEZ/MESZ (Libertex UTC)
    "close_time": "22:00", # Fr 23:00 MEZ/MESZ (Libertex UTC)
    "is_24_5": True,
    "description": "Mo 01:00 – Fr 23:00 MEZ/MESZ (Libertex, fast durchgehend)"
}
AGRAR_TEMPLATE = {
    "enabled": True,
    "days": [0, 1, 2, 3, 4],
    "open_time": "13:00",  # Default fallback (Mo 14:00 MEZ/MESZ, Libertex UTC)
    "close_time": "19:45", # Default fallback (Fr 20:45 MEZ/MESZ, Libertex UTC)
    "is_24_5": False,
    "description": "Mo-Fr, individuelle Zeiten je Produkt (Libertex, ICE/CBOT)"
}
US_INDICES_TEMPLATE = {
    "enabled": True,
    "days": [0, 1, 2, 3, 4],
    "open_time": "01:00",  # Mo 02:00 MEZ/MESZ (Libertex UTC)
    "close_time": "21:00", # Fr 22:00 MEZ/MESZ (Libertex UTC)
    "is_24_5": False,
    "description": "Mo 02:00 – Fr 22:00 MEZ/MESZ (Libertex Extended Hours)"
}
EU_INDICES_TEMPLATE = {
    "enabled": True,
    "days": [0, 1, 2, 3, 4],
    "open_time": "07:00",  # Mo 08:00 MEZ/MESZ (Libertex UTC)
    "close_time": "15:30", # Fr 16:30 MEZ/MESZ (Libertex UTC)
    "is_24_5": False,
    "description": "Mo 08:00 – Fr 16:30 MEZ/MESZ (Libertex Extended Hours, außer IBEX/SMI/AEX)"
}
ASIA_INDICES_TEMPLATE = {
    "enabled": True,
    "days": [0, 1, 2, 3, 4],
    "open_time": "00:15",  # Mo 01:15 MEZ/MESZ (Libertex UTC)
    "close_time": "20:00", # Fr 21:00 MEZ/MESZ (Libertex UTC)
    "is_24_5": False,
    "description": "Mo 01:15 – Fr 21:00 MEZ/MESZ (Libertex, tägliche Pausen je nach Index)"
}
CRYPTO_TEMPLATE = {
    "enabled": True,
    "days": [0, 1, 2, 3, 4, 5, 6],
    "open_time": "00:00",
    "close_time": "23:59",
    "is_24_7": True,
    "description": "24/7 (Libertex, keine Pause)"
}

INDUSTRIAL_TEMPLATE = {
    "enabled": True,
    "days": [0, 1, 2, 3, 4],
    "open_time": "00:00",  # Mo 01:00 MEZ/MESZ (Libertex UTC)
    "close_time": "22:00", # Fr 23:00 MEZ/MESZ (Libertex UTC)
    "is_24_5": True,
}
ENERGY_TEMPLATE = {
    "enabled": True,
    "days": [0, 1, 2, 3, 4],
    "open_time": "00:00",  # Mo 01:00 MEZ/MESZ (Libertex UTC)
    "close_time": "22:00", # Fr 23:00 MEZ/MESZ (Libertex UTC)
    "is_24_5": True,
    "description": "Mo 01:00 – Fr 23:00 MEZ/MESZ (Libertex, fast durchgehend)"
}
AGRAR_TEMPLATE = {
    "enabled": True,
    "days": [0, 1, 2, 3, 4],
    "open_time": "13:00",  # Default fallback (Mo 14:00 MEZ/MESZ, Libertex UTC)
    "close_time": "19:45", # Default fallback (Fr 20:45 MEZ/MESZ, Libertex UTC)
    "is_24_5": False,
    "description": "Mo-Fr, individuelle Zeiten je Produkt (Libertex, ICE/CBOT)"
}
US_INDICES_TEMPLATE = {
    "enabled": True,
    "days": [0, 1, 2, 3, 4],
    "open_time": "01:00",  # Mo 02:00 MEZ/MESZ (Libertex UTC)
    "close_time": "21:00", # Fr 22:00 MEZ/MESZ (Libertex UTC)
    "is_24_5": False,
    "description": "Mo 02:00 – Fr 22:00 MEZ/MESZ (Libertex Extended Hours)"
}
EU_INDICES_TEMPLATE = {
    "enabled": True,
    "days": [0, 1, 2, 3, 4],
    "open_time": "07:00",  # Mo 08:00 MEZ/MESZ (Libertex UTC)
    "close_time": "15:30", # Fr 16:30 MEZ/MESZ (Libertex UTC)
    "is_24_5": False,
    "description": "Mo 08:00 – Fr 16:30 MEZ/MESZ (Libertex Extended Hours, außer IBEX/SMI/AEX)"
}
ASIA_INDICES_TEMPLATE = {
    "enabled": True,
    "days": [0, 1, 2, 3, 4],
    "open_time": "00:15",  # Mo 01:15 MEZ/MESZ (Libertex UTC)
    "close_time": "20:00", # Fr 21:00 MEZ/MESZ (Libertex UTC)
    "is_24_5": False,
    "description": "Mo 01:15 – Fr 21:00 MEZ/MESZ (Libertex, tägliche Pausen je nach Index)"
}
CRYPTO_TEMPLATE = {
    "enabled": True,
    "days": [0, 1, 2, 3, 4, 5, 6],
    "open_time": "00:00",
    "close_time": "23:59",
    "is_24_7": True,
    "description": "24/7 (Libertex, keine Pause)"
}

# Asset-spezifische Anpassungen (UTC, Mo=0)
AGRAR_ASSET_HOURS = {
    "WHEAT":      {"open_time": "13:00", "close_time": "19:45"}, # Mo 14:00 – Fr 20:45 MEZ/MESZ (Libertex UTC)
    "CORN":       {"open_time": "13:00", "close_time": "19:45"},
    "SOYBEANS":   {"open_time": "13:00", "close_time": "19:45"},
    "COFFEE":     {"open_time": "09:15", "close_time": "17:30"}, # Mo 10:15 – Fr 18:30 MEZ/MESZ (Libertex UTC)
    "SUGAR":      {"open_time": "08:00", "close_time": "17:00"}, # Mo 09:00 – Fr 18:00 MEZ/MESZ (Libertex UTC)
    "COCOA":      {"open_time": "09:45", "close_time": "18:30"}, # Mo 10:45 – Fr 19:30 MEZ/MESZ (Libertex UTC)
}
EU_INDEX_SPECIALS = {
    "IBEX35":     {"open_time": "07:00", "close_time": "15:30"}, # Mo 08:00 – Fr 16:30 MEZ/MESZ (Libertex UTC)
    "SMI20":      {"open_time": "07:00", "close_time": "15:30"},
    "AEX25":      {"open_time": "07:00", "close_time": "15:30"},
}
ASIA_INDEX_SPECIALS = {
    "HANGSENG50": {"open_time": "00:15", "close_time": "20:00"}, # Mo 01:15 – Fr 21:00 MEZ/MESZ (Libertex UTC)
    "ASX200":     {"open_time": "22:50", "close_time": "20:00"}, # Mo 23:50 – Fr 21:00 MEZ/MESZ (Libertex UTC)
}
INDUSTRIAL_SPECIALS = {
    "ZINC":       {"open_time": "00:00", "close_time": "21:00"}, # Mo 01:00 – Fr 22:00 MEZ/MESZ (Libertex UTC)
}

DEFAULT_MARKET_HOURS = {
    **{asset: {**METALS_TEMPLATE} for asset in METAL_ASSETS},
    **{asset: {**ENERGY_TEMPLATE} for asset in ENERGY_ASSETS},
    **{asset: {**INDUSTRIAL_TEMPLATE} for asset in INDUSTRIAL_ASSETS},
    **{asset: {**AGRAR_TEMPLATE} for asset in AGRAR_ASSETS},
    **{asset: {**FOREX_TEMPLATE} for asset in FOREX_ASSETS},
    **{asset: {**US_INDICES_TEMPLATE} for asset in US_INDICES_ASSETS},
    **{asset: {**EU_INDICES_TEMPLATE} for asset in EU_INDICES_ASSETS},
    **{asset: {**ASIA_INDICES_TEMPLATE} for asset in ASIA_INDICES_ASSETS},
    **{asset: {**CRYPTO_TEMPLATE} for asset in CRYPTO_ASSETS}
}


def is_market_open(commodity_id: str, market_hours: Optional[Dict] = None, current_time: Optional[datetime] = None) -> bool:
    """
    Prüft ob ein spezifisches Commodity aktuell handelbar ist
    
    Args:
        commodity_id: ID des Commodities (z.B. "GOLD", "WTI_CRUDE")
        market_hours: Optional - Custom Handelszeiten (aus DB)
        current_time: Optional - Zeitpunkt zum Prüfen (default: jetzt UTC)
    
    Returns:
        True wenn Markt offen, False wenn geschlossen
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    # Hole Handelszeiten (Custom oder Default)
    if market_hours and commodity_id in market_hours:
        hours = market_hours[commodity_id]
    elif commodity_id in DEFAULT_MARKET_HOURS:
        hours = DEFAULT_MARKET_HOURS[commodity_id]
    else:
        # Unbekanntes Commodity - Standard 24/5
        logger.warning(f"Keine Handelszeiten für {commodity_id} definiert - verwende Standard 24/5")
        hours = {
            "enabled": True,
            "days": [0, 1, 2, 3, 4],
            "open_time": "00:00",
            "close_time": "23:59",
            "is_24_5": True
        }
    
    # Check ob Handelszeiten deaktiviert sind
    if not hours.get("enabled", True):
        return False
    
    # Check Wochentag (0=Montag, 6=Sonntag)
    current_weekday = current_time.weekday()
    
    # Für 24/7 Märkte (Crypto)
    if hours.get("is_24_7", False):
        return True
    
    # Für 24/5 Märkte (Forex, Edelmetalle, Energie)
    if hours.get("is_24_5", False):
        # Öffnet Sonntag Abend (6), schließt Freitag Abend (4)
        # Montag (0) bis Donnerstag (3): Immer offen
        if current_weekday in [0, 1, 2, 3]:
            return True
        
        # Sonntag (6): Offen ab open_time
        if current_weekday == 6:
            open_time_str = hours.get("open_time", "22:00")
            open_hour, open_min = map(int, open_time_str.split(":"))
            open_time_obj = time(open_hour, open_min)
            current_time_obj = current_time.time()
            return current_time_obj >= open_time_obj
        
        # Freitag (4): Offen bis close_time
        if current_weekday == 4:
            close_time_str = hours.get("close_time", "21:00")
            close_hour, close_min = map(int, close_time_str.split(":"))
            close_time_obj = time(close_hour, close_min)
            current_time_obj = current_time.time()
            return current_time_obj <= close_time_obj
        
        # Samstag (5): Geschlossen
        return False
    
    # Für normale Börsenzeiten (Agrar, Aktien)
    if current_weekday not in hours.get("days", [0, 1, 2, 3, 4]):
        return False
    
    # Prüfe Tageszeit
    open_time_str = hours.get("open_time", "00:00")
    close_time_str = hours.get("close_time", "23:59")
    
    open_hour, open_min = map(int, open_time_str.split(":"))
    close_hour, close_min = map(int, close_time_str.split(":"))
    
    open_time_obj = time(open_hour, open_min)
    close_time_obj = time(close_hour, close_min)
    current_time_obj = current_time.time()
    
    return open_time_obj <= current_time_obj <= close_time_obj


async def get_market_hours(db, use_cache: bool = True) -> Dict:
    """
    Holt die konfigurierten Marktöffnungszeiten aus der Datenbank.
    Fällt auf DEFAULT_MARKET_HOURS zurück wenn nichts konfiguriert ist.
    
    V2.3.35 FIX: Verwendet trading_settings statt separater Collection
    V3.3.x: Schreibt Defaults automatisch in Settings, damit UI sofort richtige Zeiten hat
    """
    try:
        # Lade aus trading_settings (market_hours Feld)
        settings = await db.trading_settings.find_one({"id": "trading_settings"})

        if settings and 'market_hours' in settings:
            saved_hours = settings.get('market_hours', {})
            # Merge mit Defaults
            result = {**DEFAULT_MARKET_HOURS}
            for commodity_id, hours in saved_hours.items():
                if commodity_id in result:
                    result[commodity_id].update(hours)
                else:
                    result[commodity_id] = hours
            # Falls leer gespeichert, sofort Defaults persistieren
            if not saved_hours:
                try:
                    await db.trading_settings.update_one(
                        {"id": "trading_settings"},
                        {"$set": {"market_hours": DEFAULT_MARKET_HOURS}},
                        upsert=True
                    )
                    logger.info("✅ Default Market Hours in Settings gespeichert (waren leer)")
                except Exception as write_err:
                    logger.warning(f"Konnte Default Market Hours nicht speichern: {write_err}")
            return result

        # Keine market_hours hinterlegt → Defaults zurückgeben und direkt speichern
        try:
            await db.trading_settings.update_one(
                {"id": "trading_settings"},
                {"$set": {"market_hours": DEFAULT_MARKET_HOURS}},
                upsert=True
            )
            logger.info("✅ Default Market Hours in Settings gespeichert (fehlten)")
        except Exception as write_err:
            logger.warning(f"Konnte Default Market Hours nicht speichern: {write_err}")
        return DEFAULT_MARKET_HOURS
        
    except Exception as e:
        logger.error(f"Error loading market hours: {e}")
        return DEFAULT_MARKET_HOURS


async def update_market_hours(db, commodity_id: str, hours_config: Dict):
    """
    Aktualisiert die Handelszeiten für ein bestimmtes Commodity.
    
    V2.3.35 FIX: Speichert in trading_settings.market_hours
    """
    try:
        # Hole aktuelle Settings
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        
        if not settings:
            settings = {"id": "trading_settings", "market_hours": {}}
        
        # Update market_hours
        market_hours = settings.get('market_hours', {})
        market_hours[commodity_id] = hours_config
        
        # Speichere zurück
        await db.trading_settings.update_one(
            {"id": "trading_settings"},
            {"$set": {"market_hours": market_hours}},
            upsert=True
        )
        
        logger.info(f"✅ Handelszeiten für {commodity_id} gespeichert: {hours_config}")
        return hours_config
        
    except Exception as e:
        logger.error(f"Error updating market hours for {commodity_id}: {e}")
        raise


# ═══════════════════════════════════════════════════════════════════════════
# V3.2.1: AUTO-CLOSE FUNKTIONEN
# ═══════════════════════════════════════════════════════════════════════════

# Strategien die NICHT täglich geschlossen werden (laufen über mehrere Tage)
MULTI_DAY_STRATEGIES = ['swing', 'swing_trading', 'grid', 'breakout']

# Strategien die täglich geschlossen werden können
INTRADAY_STRATEGIES = ['day', 'day_trading', 'scalping', 'momentum', 'mean_reversion']


def get_minutes_to_close(
    commodity_id: str,
    current_time: Optional[datetime] = None,
    market_hours: Optional[Dict] = None
) -> Optional[int]:
    """
    Berechnet die Minuten bis zum Handelsschluss für ein Asset.
    
    Returns:
        Minuten bis Schluss, oder None wenn 24/7 Markt oder Markt geschlossen
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    if market_hours and commodity_id in market_hours:
        hours = market_hours[commodity_id]
    else:
        hours = DEFAULT_MARKET_HOURS.get(commodity_id, {})
    
    # 24/7 Märkte (Crypto) haben keinen Handelsschluss
    if hours.get('is_24_7', False):
        return None
    
    # Für 24/5 Märkte: Immer tägliche Schlusszeit nutzen, nicht nur Freitag
    # (Freitag-Abend wird separat im Caller via is_friday behandelt)
    if hours.get('is_24_5', False):
        close_time_str = hours.get('close_time', '21:00')
    else:
        # Normale Börsenzeiten
        close_time_str = hours.get('close_time', '20:00')
    
    close_hour, close_min = map(int, close_time_str.split(':'))
    close_time = current_time.replace(hour=close_hour, minute=close_min, second=0, microsecond=0)
    
    # Wenn Schlusszeit bereits vorbei
    if current_time >= close_time:
        return 0
    
    diff = close_time - current_time
    return int(diff.total_seconds() / 60)


def should_close_before_market_close(
    commodity_id: str, 
    strategy: str, 
    is_friday: bool,
    minutes_before_close: int = 10,
    current_time: Optional[datetime] = None,
    market_hours: Optional[Dict] = None
) -> bool:
    """
    Prüft ob ein Trade vor Marktschluss geschlossen werden sollte.
    
    Args:
        commodity_id: Asset-ID
        strategy: Trading-Strategie
        is_friday: Ob es Freitag ist (für Wochenend-Schließung)
        minutes_before_close: Minuten vor Schluss
        current_time: Aktueller Zeitpunkt
    
    Returns:
        True wenn Trade geschlossen werden sollte
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    minutes_to_close = get_minutes_to_close(commodity_id, current_time, market_hours)
    
    # Kein Handelsschluss (24/7 oder Markt geschlossen)
    if minutes_to_close is None:
        return False
    
    # Innerhalb des Zeitfensters?
    if minutes_to_close > minutes_before_close:
        return False
    
    # Freitag: ALLE Strategien schließen
    if is_friday:
        return True
    
    # Täglich: NUR Intraday-Strategien schließen
    strategy_lower = strategy.lower()
    if strategy_lower in INTRADAY_STRATEGIES or any(s in strategy_lower for s in INTRADAY_STRATEGIES):
        return True
    
    return False


async def get_positions_to_close_before_market_end(
    db,
    positions: list,
    close_profitable_daily: bool = True,
    close_all_friday: bool = True,
    minutes_before_close: int = 10
) -> list:
    """
    Filtert Positionen die vor Marktschluss geschlossen werden sollten.
    
    Args:
        db: Datenbank-Connection
        positions: Liste der offenen Positionen
        close_profitable_daily: Toggle für tägliches Schließen (Intraday-Strategien)
        close_all_friday: Toggle für Freitag-Schließen (alle Strategien)
        minutes_before_close: Minuten vor Schluss
    
    Returns:
        Liste der zu schließenden Positionen (nur im Plus!)
    """
    from datetime import datetime, timezone
    
    current_time = datetime.now(timezone.utc)
    is_friday = current_time.weekday() == 4

    # Lade konfigurierte Handelszeiten aus Settings (falls vorhanden)
    try:
        settings = await db.trading_settings.find_one({"id": "trading_settings"})
        market_hours_cfg = settings.get('market_hours', {}) if settings else {}
    except Exception:
        market_hours_cfg = {}
    
    positions_to_close = []
    
    for pos in positions:
        # Nur Positionen im Plus schließen!
        profit = pos.get('profit', 0) or pos.get('unrealizedProfit', 0) or 0
        if profit <= 0:
            continue
        
        symbol = pos.get('symbol', '')
        ticket = pos.get('ticket', pos.get('id', ''))
        
        # Commodity-ID aus Symbol ermitteln
        commodity_id = _symbol_to_commodity(symbol)
        if not commodity_id:
            continue
        
        # Strategie aus trade_settings holen
        trade_settings = await db.trade_settings.find_one({'trade_id': f'mt5_{ticket}'})
        strategy = trade_settings.get('strategy', 'day') if trade_settings else 'day'
        
        # Prüfe ob Toggle aktiviert und ob geschlossen werden soll
        should_close = False
        
        if is_friday and close_all_friday:
            # Freitag: Alle Strategien prüfen
            should_close = should_close_before_market_close(
                commodity_id, strategy, is_friday=True, 
                minutes_before_close=minutes_before_close, 
                current_time=current_time,
                market_hours=market_hours_cfg
            )
            if should_close:
                logger.info(f"📅 FREITAG-CLOSE: {symbol} #{ticket} (Profit: €{profit:.2f}, Strategie: {strategy})")
        
        elif close_profitable_daily and not is_friday:
            # Täglich: Nur Intraday-Strategien
            should_close = should_close_before_market_close(
                commodity_id, strategy, is_friday=False,
                minutes_before_close=minutes_before_close,
                current_time=current_time,
                market_hours=market_hours_cfg
            )
            if should_close:
                logger.info(f"🔔 TAGES-CLOSE: {symbol} #{ticket} (Profit: €{profit:.2f}, Strategie: {strategy})")
        
        if should_close:
            positions_to_close.append({
                'ticket': ticket,
                'symbol': symbol,
                'commodity_id': commodity_id,
                'strategy': strategy,
                'profit': profit,
                'reason': 'friday_close' if is_friday else 'daily_close',
                'position': pos
            })
    
    return positions_to_close


def _symbol_to_commodity(symbol: str) -> Optional[str]:
    """Mappt MT5-Symbol auf Commodity-ID"""
    symbol_upper = symbol.upper()
    
    # Direktes Mapping
    symbol_map = {
        'XAUUSD': 'GOLD', 'GOLD': 'GOLD',
        'XAGUSD': 'SILVER', 'SILVER': 'SILVER',
        'XPTUSD': 'PLATINUM', 'PLATINUM': 'PLATINUM', 'PL': 'PLATINUM',
        'XPDUSD': 'PALLADIUM', 'PALLADIUM': 'PALLADIUM',
        'XTIUSD': 'WTI_CRUDE', 'USOUSD': 'WTI_CRUDE', 'WTI': 'WTI_CRUDE',
        'XBRUSD': 'BRENT_CRUDE', 'UKOUSD': 'BRENT_CRUDE', 'BRENT': 'BRENT_CRUDE',
        'XNGUSD': 'NATURAL_GAS', 'NATGAS': 'NATURAL_GAS',
        'XCUUSD': 'COPPER', 'COPPER': 'COPPER',
        'WHEAT': 'WHEAT', 'CORN': 'CORN', 'SOYBEAN': 'SOYBEANS', 'SOYBEANS': 'SOYBEANS',
        'COFFEE': 'COFFEE', 'SUGAR': 'SUGAR', 'COCOA': 'COCOA',
        'EURUSD': 'EURUSD', 'GBPUSD': 'GBPUSD', 'USDJPY': 'USDJPY',
        'BTCUSD': 'BITCOIN', 'ETHUSD': 'ETHEREUM',
        'ZINC': 'ZINC', 'USTEC': 'NASDAQ100', 'NAS100': 'NASDAQ100'
    }
    
    if symbol_upper in symbol_map:
        return symbol_map[symbol_upper]
    
    # Teilstring-Suche
    for key, value in symbol_map.items():
        if key in symbol_upper:
            return value
    
    return None
