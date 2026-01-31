"""
🔧 Booner Trade V3.1.0 - Backend Konfiguration

Zentrale Konfigurationsdatei für alle Backend-Services.
Ersetzt verteilte Konstanten und hardcoded Werte.
"""

import os
from typing import Dict, List, Any
from enum import Enum
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════════════════════════
# ENVIRONMENT VARIABLES
# ═══════════════════════════════════════════════════════════════════════════

class EnvConfig:
    """Umgebungsvariablen mit Fallbacks"""
    
    # MetaAPI
    METAAPI_TOKEN = os.getenv('METAAPI_TOKEN', '')
    METAAPI_ACCOUNT_ID = os.getenv('METAAPI_ACCOUNT_ID', '')
    METAAPI_ICMARKETS_ACCOUNT_ID = os.getenv('METAAPI_ICMARKETS_ACCOUNT_ID', '')
    
    # Database
    MONGO_URL = os.getenv('MONGO_URL', 'mongodb://localhost:27017')
    DB_NAME = os.getenv('DB_NAME', 'booner_trade')
    
    # API Keys
    NEWS_API_KEY = os.getenv('NEWS_API_KEY', '')
    ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY', '')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    
    # Server
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', '8001'))


# ═══════════════════════════════════════════════════════════════════════════
# TRADING CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

class TradingMode(Enum):
    """Trading-Modi"""
    CONSERVATIVE = 'conservative'
    STANDARD = 'standard'
    AGGRESSIVE = 'aggressive'


@dataclass
class TradingModeConfig:
    """Konfiguration pro Trading-Modus"""
    name: str
    sl_multiplier: float
    tp_multiplier: float
    spread_buffer_multiplier: float
    min_confidence: int
    max_positions: int
    
    
TRADING_MODES: Dict[str, TradingModeConfig] = {
    'conservative': TradingModeConfig(
        name='Konservativ',
        sl_multiplier=2.5,
        tp_multiplier=4.0,
        spread_buffer_multiplier=2.0,
        min_confidence=75,
        max_positions=3,
    ),
    'standard': TradingModeConfig(
        name='Standard',
        sl_multiplier=1.5,
        tp_multiplier=3.0,
        spread_buffer_multiplier=1.5,
        min_confidence=70,
        max_positions=5,
    ),
    'aggressive': TradingModeConfig(
        name='Aggressiv',
        sl_multiplier=1.0,
        tp_multiplier=2.0,
        spread_buffer_multiplier=1.2,
        min_confidence=65,
        max_positions=10,
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# ASSET CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

class AssetClass(Enum):
    """Asset-Klassen"""
    COMMODITY_METAL = 'commodity_metal'
    COMMODITY_ENERGY = 'commodity_energy'
    COMMODITY_AGRIC = 'commodity_agric'
    FOREX_MAJOR = 'forex_major'
    FOREX_MINOR = 'forex_minor'
    CRYPTO = 'crypto'
    INDEX = 'index'


@dataclass
class AssetConfig:
    """Konfiguration pro Asset"""
    name: str
    asset_class: AssetClass
    mt5_libertex_symbol: str = ''
    mt5_icmarkets_symbol: str = ''
    yahoo_symbol: str = ''
    min_sl_percent: float = 2.0
    typical_spread_percent: float = 0.2
    max_spread_percent: float = 0.5


# V3.0.0: Alle 20 Assets
ASSETS: Dict[str, AssetConfig] = {
    # Metalle
    'GOLD': AssetConfig('Gold', AssetClass.COMMODITY_METAL, 'XAUUSD', 'XAUUSD', 'GC=F', 1.5, 0.15, 0.3),
    'SILVER': AssetConfig('Silber', AssetClass.COMMODITY_METAL, 'XAGUSD', 'XAGUSD', 'SI=F', 2.0, 0.2, 0.4),
    'PLATINUM': AssetConfig('Platin', AssetClass.COMMODITY_METAL, 'XPTUSD', 'XPTUSD', 'PL=F', 2.0, 0.2, 0.5),
    'PALLADIUM': AssetConfig('Palladium', AssetClass.COMMODITY_METAL, 'XPDUSD', 'XPDUSD', 'PA=F', 2.5, 0.25, 0.6),
    'COPPER': AssetConfig('Kupfer', AssetClass.COMMODITY_METAL, 'COPPER', 'HGF6', 'HG=F', 2.0, 0.2, 0.5),
    'ZINC': AssetConfig('Zink', AssetClass.COMMODITY_METAL, 'ZINC', 'ZINC', 'ZN=F', 2.5, 0.3, 0.6),
    
    # Energie
    'WTI_CRUDE': AssetConfig('WTI Crude Oil', AssetClass.COMMODITY_ENERGY, 'USOILCash', 'WTI_F6', 'CL=F', 2.0, 0.2, 0.4),
    'BRENT_CRUDE': AssetConfig('Brent Crude Oil', AssetClass.COMMODITY_ENERGY, 'UKOUSD', 'BRENT', 'BZ=F', 2.0, 0.2, 0.4),
    'NATURAL_GAS': AssetConfig('Natural Gas', AssetClass.COMMODITY_ENERGY, 'NGASCash', 'NG', 'NG=F', 3.0, 0.3, 0.6),
    
    # Agrar
    'WHEAT': AssetConfig('Weizen', AssetClass.COMMODITY_AGRIC, 'WHEAT', 'WHEAT', 'ZW=F', 2.5, 0.4, 0.8),
    'CORN': AssetConfig('Mais', AssetClass.COMMODITY_AGRIC, 'CORN', 'CORN', 'ZC=F', 2.5, 0.4, 0.8),
    'SOYBEANS': AssetConfig('Sojabohnen', AssetClass.COMMODITY_AGRIC, 'SOYBEAN', 'SOYBEAN', 'ZS=F', 2.5, 0.4, 0.8),
    'COFFEE': AssetConfig('Kaffee', AssetClass.COMMODITY_AGRIC, 'COFFEE', 'COFFEE', 'KC=F', 2.5, 0.4, 0.8),
    'SUGAR': AssetConfig('Zucker', AssetClass.COMMODITY_AGRIC, 'SUGAR', 'SUGAR', 'SB=F', 2.5, 0.5, 1.0),
    'COCOA': AssetConfig('Kakao', AssetClass.COMMODITY_AGRIC, 'COCOA', 'COCOA', 'CC=F', 2.5, 0.4, 0.8),
    
    # Crypto
    'BITCOIN': AssetConfig('Bitcoin', AssetClass.CRYPTO, 'BTCUSD', 'BTCUSD', 'BTC-USD', 3.0, 0.3, 0.6),
    'ETHEREUM': AssetConfig('Ethereum', AssetClass.CRYPTO, 'ETHUSD', 'ETHUSD', 'ETH-USD', 3.0, 0.35, 0.7),
    
    # Forex
    'USDJPY': AssetConfig('USD/JPY', AssetClass.FOREX_MAJOR, 'USDJPY', 'USDJPY', 'JPY=X', 0.5, 0.02, 0.05), 
    'GBPUSD': AssetConfig('GBP/USD', AssetClass.FOREX_MAJOR, 'GBPUSD', 'GBPUSD', 'GBPUSD=X', 0.5, 0.02, 0.05),
    'EURUSD': AssetConfig('EUR/USD', AssetClass.FOREX_MAJOR, 'EURUSD', 'EURUSD', 'EURUSD=X', 0.5, 0.02, 0.05),
    'AUDUSD': AssetConfig('AUD/USD', AssetClass.FOREX_MAJOR, 'AUDUSD', 'AUDUSD', 'AUDUSD=X', 0.5, 0.02, 0.05),
    'USDCHF': AssetConfig('USD/CHF', AssetClass.FOREX_MAJOR, 'USDCHF', 'USDCHF', 'USDCHF=X', 0.5, 0.02, 0.05),
    'USDCAD': AssetConfig('USD/CAD', AssetClass.FOREX_MAJOR, 'USDCAD', 'USDCAD', 'USDCAD=X', 0.5, 0.02, 0.05),
    'NZDUSD': AssetConfig('NZD/USD', AssetClass.FOREX_MAJOR, 'NZDUSD', 'NZDUSD', 'NZDUSD=X', 0.5, 0.02, 0.05),
    'EURGBP': AssetConfig('EUR/GBP', AssetClass.FOREX_MINOR, 'EURGBP', 'EURGBP', 'EURGBP=X', 0.5, 0.02, 0.05),
    'EURJPY': AssetConfig('EUR/JPY', AssetClass.FOREX_MINOR, 'EURJPY', 'EURJPY', 'EURJPY=X', 0.5, 0.02, 0.05),
    'GBPJPY': AssetConfig('GBP/JPY', AssetClass.FOREX_MINOR, 'GBPJPY', 'GBPJPY', 'GBPJPY=X', 0.5, 0.02, 0.05),
    'AUDJPY': AssetConfig('AUD/JPY', AssetClass.FOREX_MINOR, 'AUDJPY', 'AUDJPY', 'AUDJPY=X', 0.5, 0.02, 0.05),
    'CHFJPY': AssetConfig('CHF/JPY', AssetClass.FOREX_MINOR, 'CHFJPY', 'CHFJPY', 'CHFJPY=X', 0.5, 0.02, 0.05),
    'CADJPY': AssetConfig('CAD/JPY', AssetClass.FOREX_MINOR, 'CADJPY', 'CADJPY', 'CADJPY=X', 0.5, 0.02, 0.05),
    'AUDCAD': AssetConfig('AUD/CAD', AssetClass.FOREX_MINOR, 'AUDCAD', 'AUDCAD', 'AUDCAD=X', 0.5, 0.02, 0.05),
    'AUDNZD': AssetConfig('AUD/NZD', AssetClass.FOREX_MINOR, 'AUDNZD', 'AUDNZD', 'AUDNZD=X', 0.5, 0.02, 0.05),
    'EURNZD': AssetConfig('EUR/NZD', AssetClass.FOREX_MINOR, 'EURNZD', 'EURNZD', 'EURNZD=X', 0.5, 0.02, 0.05),
    'EURAUD': AssetConfig('EUR/AUD', AssetClass.FOREX_MINOR, 'EURAUD', 'EURAUD', 'EURAUD=X', 0.5, 0.02, 0.05),
    'GBPAUD': AssetConfig('GBP/AUD', AssetClass.FOREX_MINOR, 'GBPAUD', 'GBPAUD', 'GBPAUD=X', 0.5, 0.02, 0.05),
    
    # Indizes
    'NASDAQ100': AssetConfig('NASDAQ 100', AssetClass.INDEX, 'US100Cash', 'NAS100', '^NDX', 1.5, 0.15, 0.3),
    'SP500': AssetConfig('S&P 500', AssetClass.INDEX, 'SP500', 'US500', '^GSPC', 1.5, 0.15, 0.3),
    'DOWJONES30': AssetConfig('Dow Jones 30', AssetClass.INDEX, 'DJ30', 'US30', '^DJI', 1.5, 0.15, 0.3),
    'DAX40': AssetConfig('DAX 40', AssetClass.INDEX, 'DAX40', 'GER40', '^GDAXI', 1.5, 0.15, 0.3),
    'FTSE100': AssetConfig('FTSE 100', AssetClass.INDEX, 'FTSE100', 'UK100', '^FTSE', 1.5, 0.15, 0.3),
    'EUROSTOXX50': AssetConfig('Euro Stoxx 50', AssetClass.INDEX, 'EUROSTOXX50', 'EU50', '^STOXX50E', 1.5, 0.15, 0.3),
    'NIKKEI225': AssetConfig('Nikkei 225', AssetClass.INDEX, 'NIKKEI225', 'JP225', '^N225', 1.5, 0.15, 0.3),
    'HANGSENG50': AssetConfig('Hang Seng 50', AssetClass.INDEX, 'HANGSENG50', 'HK50', '^HSI', 1.5, 0.15, 0.3),
    'ASX200': AssetConfig('ASX 200', AssetClass.INDEX, 'ASX200', 'AU200', '^AXJO', 1.5, 0.15, 0.3),
    'CAC40': AssetConfig('CAC 40', AssetClass.INDEX, 'CAC40', 'FRA40', '^FCHI', 1.5, 0.15, 0.3),
    'IBEX35': AssetConfig('IBEX 35', AssetClass.INDEX, 'IBEX35', 'ESP35', '^IBEX', 1.5, 0.15, 0.3),
    'SMI20': AssetConfig('SMI 20', AssetClass.INDEX, 'SMI20', 'SWI20', '^SSMI', 1.5, 0.15, 0.3),
    'AEX25': AssetConfig('AEX 25', AssetClass.INDEX, 'AEX25', 'NED25', '^AEX', 1.5, 0.15, 0.3),
    'RUSSELL2000': AssetConfig('Russell 2000', AssetClass.INDEX, 'RUSSELL2000', 'US2000', '^RUT', 1.5, 0.15, 0.3),
    'VIX': AssetConfig('Volatility Index', AssetClass.INDEX, 'VIX', 'VIX', '^VIX', 1.5, 0.15, 0.3),
}


# ═══════════════════════════════════════════════════════════════════════════
# API CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class APIConfig:
    """API-Konfiguration"""
    timeout: int = 30
    retry_count: int = 3
    retry_delay: float = 2.0
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds


API = APIConfig()


# ═══════════════════════════════════════════════════════════════════════════
# 4-PILLAR ENGINE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PillarConfig:
    """4-Pillar Confidence Engine Konfiguration"""
    # Default Weights
    base_signal_weight: int = 25
    trend_confluence_weight: int = 25
    volatility_weight: int = 25
    sentiment_weight: int = 25
    
    # Thresholds
    high_confidence_threshold: int = 70
    medium_confidence_threshold: int = 50
    low_confidence_threshold: int = 30
    
    # RSI Levels
    rsi_overbought: int = 70
    rsi_oversold: int = 30
    
    # ADX Levels
    adx_strong_trend: int = 25
    adx_very_strong_trend: int = 40


PILLAR_CONFIG = PillarConfig()


# ═══════════════════════════════════════════════════════════════════════════
# BAYESIAN LEARNING CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class BayesianConfig:
    """Bayesian Self-Learning Konfiguration"""
    learning_rate: float = 0.05
    min_weight: float = 5.0
    max_weight: float = 60.0
    min_trades_for_learning: int = 10
    optimization_interval_hours: int = 24


BAYESIAN_CONFIG = BayesianConfig()


# ═══════════════════════════════════════════════════════════════════════════
# VERSION INFO
# ═══════════════════════════════════════════════════════════════════════════

VERSION = {
    'number': '3.1.0',
    'name': 'Booner Trade',
    'codename': 'Modular Refactor',
    'features': [
        'spread_adjustment',
        'bayesian_learning',
        '4_pillar_engine',
        'imessage_bridge',
        'ai_managed_sl_tp',
        'modular_routes',
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def get_trading_mode_config(mode: str) -> TradingModeConfig:
    """Holt die Konfiguration für einen Trading-Modus"""
    return TRADING_MODES.get(mode, TRADING_MODES['standard'])


def get_asset_config(asset_id: str) -> AssetConfig:
    """Holt die Konfiguration für ein Asset"""
    return ASSETS.get(asset_id)


def get_all_asset_ids() -> List[str]:
    """Liefert alle Asset-IDs"""
    return list(ASSETS.keys())


def get_assets_by_class(asset_class: AssetClass) -> List[str]:
    """Liefert alle Assets einer Klasse"""
    return [
        asset_id for asset_id, config in ASSETS.items()
        if config.asset_class == asset_class
    ]


# Export
__all__ = [
    'EnvConfig',
    'TradingMode',
    'TradingModeConfig',
    'TRADING_MODES',
    'AssetClass',
    'AssetConfig',
    'ASSETS',
    'APIConfig',
    'API',
    'PillarConfig',
    'PILLAR_CONFIG',
    'BayesianConfig',
    'BAYESIAN_CONFIG',
    'VERSION',
    'get_trading_mode_config',
    'get_asset_config',
    'get_all_asset_ids',
    'get_assets_by_class',
]
