"""
Hybrid Data Fetcher - Multi-Source Commodity Data
Combines MetaAPI, Yahoo Finance, and other sources to avoid rate limits
"""

import asyncio
import yfinance as yf
from datetime import datetime, timezone, timedelta
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Data source priorities for each commodity
COMMODITY_DATA_SOURCES = {
    # MetaAPI verfügbar - verwende als PRIMARY
    "GOLD": ["metaapi", "yfinance"],
    "SILVER": ["metaapi", "yfinance"],
    "PLATINUM": ["metaapi", "yfinance"],
    "PALLADIUM": ["metaapi", "yfinance"],
    "WTI_CRUDE": ["metaapi", "yfinance"],
    "BRENT_CRUDE": ["metaapi", "yfinance"],
    "NATURAL_GAS": ["metaapi", "yfinance"],
    "BITCOIN": ["metaapi", "yfinance"],
    "EURUSD": ["metaapi", "yfinance"],
    "GBPUSD" : ["metaapi", "yfinance"],
    "AUDUSD": ["metaapi", "yfinance"],
    "USDCHF": ["metaapi", "yfinance"],
    "USDCAD": ["metaapi", "yfinance"],
    "NZDUSD": ["metaapi", "yfinance"],
    "EURGBP": ["metaapi", "yfinance"],
    "EURJPY": ["metaapi", "yfinance"],
    "GBPJPY": ["metaapi", "yfinance"],
    "AUDJPY": ["metaapi", "yfinance"],
    "CHFJPY": ["metaapi", "yfinance"],
    "CADJPY": ["metaapi", "yfinance"],
    "AUDCAD": ["metaapi", "yfinance"],
    "AUDNZD": ["metaapi", "yfinance"],
    "EURNZD": ["metaapi", "yfinance"],
    "EURAUD": ["metaapi", "yfinance"],
    "GBPAUD": ["metaapi", "yfinance"],

    # V3.0.0: Neue Assets
    "USDJPY": ["metaapi", "yfinance"],  # Forex
    "ETHEREUM": ["metaapi", "yfinance"],  # Crypto 24/7
    "NASDAQ100": ["metaapi", "yfinance"],  # US Index
    "SP500": ["metaapi", "yfinance"],
    "DOWJONES30": ["metaapi", "yfinance"],
    "DAX40": ["metaapi", "yfinance"],
    "FTSE100": ["metaapi", "yfinance"],
    "EUROSTOXX50": ["metaapi", "yfinance"],
    "NIKKEI225": ["metaapi", "yfinance"],
    "HANGSENG50": ["metaapi", "yfinance"],
    "ASX200": ["metaapi", "yfinance"],
    "CAC40": ["metaapi", "yfinance"],
    "IBEX35": ["metaapi", "yfinance"],
    "SMI20": ["metaapi", "yfinance"],
    "AEX25": ["metaapi", "yfinance"],
    "RUSSELL2000": ["metaapi", "yfinance"],
    "VIX": ["metaapi", "yfinance"],
    "ZINC": ["yfinance"],  # LME - nur Yahoo
    
    # NUR Yahoo Finance (weil MetaAPI Symbol evtl. nicht verfügbar)
    "WHEAT": ["yfinance", "metaapi"],
    "CORN": ["yfinance", "metaapi"],
    "SOYBEANS": ["yfinance", "metaapi"],
    "COFFEE": ["yfinance", "metaapi"],
    "SUGAR": ["yfinance", "metaapi"],
    "COCOA": ["yfinance", "metaapi"],
    
    # COPPER - NEU
    "COPPER": ["yfinance"],
}

# Yahoo Finance Symbole
YFINANCE_SYMBOLS = {
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "PLATINUM": "PL=F",
    "PALLADIUM": "PA=F",
    "WTI_CRUDE": "CL=F",
    "BRENT_CRUDE": "BZ=F",
    "NATURAL_GAS": "NG=F",
    "COPPER": "HG=F",  # COPPER Symbol
    "WHEAT": "ZW=F",
    "CORN": "ZC=F",
    "SOYBEANS": "ZS=F",
    "COFFEE": "KC=F",
    "SUGAR": "SB=F",
    "COCOA": "CC=F",
    "EURUSD": "EURUSD=X",
    "BITCOIN": "BTC-USD",
    "GBPUSD": "GBPUSD=X",
    "AUDUSD": "AUDUSD=X",
    "USDCHF": "USDCHF=X",
    "USDCAD": "USDCAD=X",
    "NZDUSD": "NZDUSD=X",
    "EURGBP": "EURGBP=X",
    "EURJPY": "EURJPY=X",
    "GBPJPY": "GBPJPY=X",
    "AUDJPY": "AUDJPY=X",
    "CHFJPY": "CHFJPY=X",
    "CADJPY": "CADJPY=X",
    "AUDCAD": "AUDCAD=X",
    "AUDNZD": "AUDNZD=X",
    "EURNZD": "EURNZD=X",
    "EURAUD": "EURAUD=X",
    "GBPAUD": "GBPAUD=X",
    # V3.0.0: Neue Assets
    "USDJPY": "JPY=X",  # USD/JPY
    "ETHEREUM": "ETH-USD",  # Ethereum
    "NASDAQ100": "^NDX",  # Nasdaq 100 Index
    "SP500": "^GSPC",
    "DOWJONES30": "^DJI",
    "DAX40": "^GDAXI",
    "FTSE100": "^FTSE",
    "EUROSTOXX50": "^STOXX50E",
    "NIKKEI225": "^N225",
    "HANGSENG50": "^HSI",
    "ASX200": "^AXJO",
    "CAC40": "^FCHI",
    "IBEX35": "^IBEX",
    "SMI20": "^SSMI",
    "AEX25": "^AEX",
    "RUSSELL2000": "^RUT",
    "VIX": "^VIX",
    "ZINC": "ZN=F",  # Zink Futures (LME)
}

# MetaAPI Symbole - CASE SENSITIVE!
METAAPI_SYMBOLS = {
    "GOLD": "XAUUSD",
    "SILVER": "XAGUSD",
    "PLATINUM": "XPTUSD",  # Oder "PL" für Libertex
    "PALLADIUM": "XPDUSD",  # Oder "PA" für Libertex
    "WTI_CRUDE": "WTI_F6",  # ICMarkets oder "CL" für Libertex
    "BRENT_CRUDE": "BRENT_F6",  # ICMarkets oder "BRN" für Libertex
    "NATURAL_GAS": "NG",  # Nur Libertex
    "BITCOIN": "BTCUSD",
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "AUDUSD": "AUDUSD",
    "USDCHF": "USDCHF",
    "USDCAD": "USDCAD",
    "NZDUSD": "NZDUSD",
    "EURGBP": "EURGBP",
    "EURJPY": "EURJPY",
    "GBPJPY": "GBPJPY",
    "AUDJPY": "AUDJPY",
    "CHFJPY": "CHFJPY",
    "CADJPY": "CADJPY",
    "AUDCAD": "AUDCAD",
    "AUDNZD": "AUDNZD",
    "EURNZD": "EURNZD",
    "EURAUD": "EURAUD",
    "GBPAUD": "GBPAUD",
    # V3.0.0: Neue Assets
    "USDJPY": "USDJPY",  # Forex
    "ETHEREUM": "ETHUSD",  # Crypto
    "NASDAQ100": "USTEC",  # US Tech 100
    "SP500": "SP500",
    "DOWJONES30": "DJ30",
    "DAX40": "DAX40",
    "FTSE100": "FTSE100",
    "EUROSTOXX50": "EUROSTOXX50",
    "NIKKEI225": "NIKKEI225",
    "HANGSENG50": "HANGSENG50",
    "ASX200": "ASX200",
    "CAC40": "CAC40",
    "IBEX35": "IBEX35",
    "SMI20": "SMI20",
    "AEX25": "AEX25",
    "RUSSELL2000": "RUSSELL2000",
    "VIX": "VIX",
    # Agrar - oft nicht verfügbar oder falsche Symbole
    "WHEAT": "WHEAT",  # Könnte falsch sein
    "CORN": "CORN",
    "SOYBEANS": "SOYBEAN",
    "COFFEE": "COFFEE",
    "SUGAR": "SUGAR",
    "COCOA": "COCOA",
}

# Cache für Yahoo Finance um Rate Limits zu vermeiden
yf_cache = {}
yf_cache_timeout = 180  # 3 Minuten Cache (für schnellere Updates bei Echtzeit-Trading)


async def fetch_from_metaapi(commodity_id: str, connector):
    """
    Fetch live price from MetaAPI
    """
    if commodity_id not in METAAPI_SYMBOLS:
        return None
    
    symbol = METAAPI_SYMBOLS[commodity_id]
    
    try:
        tick = await connector.get_symbol_price(symbol)
        if tick and 'price' in tick:
            logger.info(f"✅ MetaAPI: {commodity_id} ({symbol}) = ${tick['price']:.2f}")
            return {
                'price': tick['price'],
                'source': 'metaapi',
                'symbol': symbol,
                'timestamp': datetime.now(timezone.utc)
            }
    except Exception as e:
        logger.warning(f"⚠️ MetaAPI failed for {commodity_id} ({symbol}): {e}")
    
    return None


def fetch_from_yfinance(commodity_id: str):
    """
    Fetch data from Yahoo Finance with caching
    """
    if commodity_id not in YFINANCE_SYMBOLS:
        return None
    
    symbol = YFINANCE_SYMBOLS[commodity_id]
    
    # Check cache
    now = datetime.now(timezone.utc)
    if commodity_id in yf_cache:
        cached = yf_cache[commodity_id]
        age = (now - cached['timestamp']).total_seconds()
        if age < yf_cache_timeout:
            logger.debug(f"📦 Cache hit for {commodity_id} (age: {age:.0f}s)")
            return cached
    
    try:
        ticker = yf.Ticker(symbol)
        
        # Hole 2 Tage Daten um sicherzugehen dass wir aktuelle haben
        hist = ticker.history(period='2d', interval='1h')
        
        if hist.empty:
            logger.warning(f"⚠️ Yahoo Finance: No data for {commodity_id} ({symbol})")
            return None
        
        latest_price = float(hist['Close'].iloc[-1])
        
        result = {
            'price': latest_price,
            'source': 'yfinance',
            'symbol': symbol,
            'timestamp': now,
            'hist': hist  # Für Indicator-Berechnung
        }
        
        # Cache speichern
        yf_cache[commodity_id] = result
        
        logger.info(f"✅ Yahoo Finance: {commodity_id} ({symbol}) = ${latest_price:.2f}")
        return result
        
    except Exception as e:
        logger.warning(f"⚠️ Yahoo Finance failed for {commodity_id} ({symbol}): {e}")
        return None


async def fetch_commodity_price_hybrid(commodity_id: str, connector=None):
    """
    Hybrid fetcher - tries multiple sources in priority order
    
    Returns:
        dict with 'price', 'source', 'symbol', 'timestamp'
    """
    sources = COMMODITY_DATA_SOURCES.get(commodity_id, ["yfinance"])
    
    for source in sources:
        try:
            if source == "metaapi" and connector:
                result = await fetch_from_metaapi(commodity_id, connector)
                if result:
                    return result
            
            elif source == "yfinance":
                # Run in executor to avoid blocking
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, fetch_from_yfinance, commodity_id)
                if result:
                    return result
        
        except Exception as e:
            logger.error(f"Error fetching {commodity_id} from {source}: {e}")
            continue
    
    logger.error(f"❌ All sources failed for {commodity_id}")
    return None


def get_yahoo_finance_history(commodity_id: str, period='1mo'):
    """
    Get historical data from Yahoo Finance for indicator calculation
    """
    if commodity_id not in YFINANCE_SYMBOLS:
        return None
    
    symbol = YFINANCE_SYMBOLS[commodity_id]
    
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval='1d')
        
        if hist.empty:
            return None
        
        logger.debug(f"📈 Yahoo Finance history: {commodity_id} - {len(hist)} days")
        return hist
        
    except Exception as e:
        logger.error(f"Error getting history for {commodity_id}: {e}")
        return None


async def fetch_all_commodities_parallel(commodity_ids: list, connector=None):
    """
    Fetch all commodities in parallel to maximize speed
    
    Returns:
        dict: {commodity_id: price_data}
    """
    tasks = []
    for cid in commodity_ids:
        task = fetch_commodity_price_hybrid(cid, connector)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Map results to commodity IDs
    data = {}
    for cid, result in zip(commodity_ids, results):
        if isinstance(result, Exception):
            logger.error(f"Error fetching {cid}: {result}")
            data[cid] = None
        else:
            data[cid] = result
    
    success_count = sum(1 for v in data.values() if v is not None)
    logger.info(f"✅ Fetched {success_count}/{len(commodity_ids)} commodities")
    
    return data
