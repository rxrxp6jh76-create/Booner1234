"""
Automatisches Symbol-Mapping für neuen MT5-Broker
Dieses Script hilft beim Wechsel zu einem neuen Broker
"""
import asyncio
import aiohttp
import os
from dotenv import load_dotenv
import json

load_dotenv()

BACKEND_URL = "http://localhost:8000"

# Rohstoffe und ihre möglichen Symbol-Varianten bei verschiedenen Brokern
COMMODITY_PATTERNS = {
    "GOLD": {
        "keywords": ["GOLD", "XAU", "GC"],
        "current": "XAUUSD"
    },
    "SILVER": {
        "keywords": ["SILVER", "XAG", "SI"],
        "current": "XAGUSD"
    },
    "PLATINUM": {
        "keywords": ["PLAT", "XPT", "PL"],
        "current": "XPTUSD"
    },
    "PALLADIUM": {
        "keywords": ["PALL", "XPD", "PA"],
        "current": "XPDUSD"
    },
    "WTI_CRUDE": {
        "keywords": ["WTI", "USOIL", "CL", "CRUDE"],
        "current": "WTI_F6"
    },
    "BRENT_CRUDE": {
        "keywords": ["BRENT", "UKOIL", "BZ"],
        "current": "BRENT_F6"
    },
    "WHEAT": {
        "keywords": ["WHEAT", "ZW"],
        "current": "Wheat_H6"
    },
    "CORN": {
        "keywords": ["CORN", "ZC", "MAIZ"],
        "current": "Corn_H6"
    },
    "SOYBEANS": {
        "keywords": ["SOY", "SBEAN", "ZS"],
        "current": "Sbean_F6"
    },
    "COFFEE": {
        "keywords": ["COFFEE", "KC"],
        "current": "Coffee_H6"
    },
    "SUGAR": {
        "keywords": ["SUGAR", "SB"],
        "current": "Sugar_H6"
    },
    "COTTON": {
        "keywords": ["COTTON", "CT"],
        "current": "Cotton_H6"
    },
    "COCOA": {
        "keywords": ["COCOA", "CC"],
        "current": "Cocoa_H6"
    }
}

async def fetch_broker_symbols():
    """Hole alle verfügbaren Symbole vom aktuellen Broker"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/api/mt5/symbols") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('all_symbols', [])
                else:
                    print(f"❌ Fehler beim Abrufen der Symbole: {response.status}")
                    return []
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return []

def find_matching_symbol(commodity_id, patterns, broker_symbols):
    """Finde das passende Symbol beim Broker"""
    keywords = patterns['keywords']
    current = patterns['current']
    
    # Prüfe zuerst, ob das aktuelle Symbol verfügbar ist
    if current in broker_symbols:
        return current
    
    # Suche nach exakten Matches oder Teilübereinstimmungen
    matches = []
    for symbol in broker_symbols:
        symbol_upper = symbol.upper()
        # Scoring-System für bessere Matches
        score = 0
        for keyword in keywords:
            if keyword == symbol_upper:
                score += 100  # Exakter Match
            elif symbol_upper.startswith(keyword):
                score += 50  # Beginnt mit Keyword
            elif keyword in symbol_upper:
                score += 10  # Enthält Keyword
        if score > 0:
            # Bevorzuge kürzere Symbole
            length_penalty = len(symbol) / 10
            final_score = score - length_penalty
            matches.append((symbol, final_score))
    # Sortiere nach Score (höchster zuerst)
    matches.sort(key=lambda x: x[1], reverse=True)
    if matches:
        return matches[0][0]  # Bestes Match
    return None


# Automatische Zuordnung von Kategorie und Einheit für bekannte Rohstoffe
COMMODITY_META = {
    "GOLD": {"category": "Metall", "unit": "Unze"},
    "SILVER": {"category": "Metall", "unit": "Unze"},
    "PLATINUM": {"category": "Metall", "unit": "Unze"},
    "PALLADIUM": {"category": "Metall", "unit": "Unze"},
    "WTI_CRUDE": {"category": "Energie", "unit": "Barrel"},
    "BRENT_CRUDE": {"category": "Energie", "unit": "Barrel"},
    "WHEAT": {"category": "Agrar", "unit": "Bushel"},
    "CORN": {"category": "Agrar", "unit": "Bushel"},
    "SOYBEANS": {"category": "Agrar", "unit": "Bushel"},
    "COFFEE": {"category": "Soft Commodity", "unit": "Pfund"},
    "SUGAR": {"category": "Soft Commodity", "unit": "Pfund"},
    "COTTON": {"category": "Soft Commodity", "unit": "Pfund"},
    "COCOA": {"category": "Soft Commodity", "unit": "Tonne"},
}

def get_meta_for_symbol(symbol):
    # Rohstoff-Erkennung
    for commodity_id, patterns in COMMODITY_PATTERNS.items():
        if symbol == patterns["current"] or any(symbol.upper().startswith(k) for k in patterns["keywords"]):
            meta = COMMODITY_META.get(commodity_id, None)
            if meta:
                return meta["category"], meta["unit"]
    # Aktien
    if symbol.upper().endswith(".DE") or symbol.upper().endswith(".F") or symbol.upper().endswith(".US") or symbol.upper().endswith(".FR") or symbol.upper().endswith(".L"):
        return "Aktie", "Stück"
    # Indizes
    if symbol.upper().startswith("DAX") or symbol.upper().startswith("SPX") or symbol.upper().startswith("NDX") or symbol.upper().startswith("DJI") or symbol.upper().startswith("FTSE") or symbol.upper().startswith("HSI") or symbol.upper().startswith("EU50"):
        return "Index", "Punkt"
    # Forex
    if len(symbol) == 6 and symbol.isalpha():
        return "Forex", "Lot"
    # Krypto
    if symbol.upper().startswith("BTC") or symbol.upper().startswith("ETH") or symbol.upper().startswith("XRP") or symbol.upper().startswith("SOL") or symbol.upper().startswith("ADA"):
        return "Krypto", "Coin"
    # ETF
    if symbol.upper().endswith(".ETF") or "ETF" in symbol.upper():
        return "ETF", "Stück"
    return "Unbekannt", "Unbekannt"

async def auto_map_symbols():
    """Automatisches Mapping der Rohstoff-Symbole"""
    print("="*80)
    print("AUTOMATISCHES SYMBOL-MAPPING FÜR NEUEN BROKER")
    print("="*80)
    
    # Hole alle verfügbaren Symbole vom Broker
    print("\n📡 Rufe verfügbare Symbole vom MT5-Broker ab...")
    broker_symbols = await fetch_broker_symbols()
    
    if not broker_symbols:
        print("❌ Keine Symbole gefunden! Bitte überprüfen Sie:")
        print("   1. MT5-Verbindung ist aktiv")
        print("   2. Neue Broker-Zugangsdaten sind in .env eingetragen")
        print("   3. Backend ist neu gestartet")
        return
    
    print(f"✅ {len(broker_symbols)} Symbole vom Broker gefunden\n")
    
    # Mapping für alle Broker-Symbole
    print("="*80)
    print("ALLE BROKER-SYMBOLE STATISCH")
    print("="*80)
    print("\nCOMMODITIES = {")
    for symbol in broker_symbols:
        category, unit = get_meta_for_symbol(symbol)
        print(f'    "{symbol}": {{"name": "{symbol}", "symbol": "{symbol}", "mt5_symbol": "{symbol}", "category": "{category}", "unit": "{unit}", "platform": "MT5"}},')
    print("}")
    print("\nMT5_TRADEABLE = [")
    for symbol in broker_symbols:
        print(f'    "{symbol}",')
    print("]")
    print("\nHinweis: Kategorie und Einheit werden für bekannte Rohstoffe automatisch gesetzt.")

if __name__ == "__main__":
    asyncio.run(auto_map_symbols())
