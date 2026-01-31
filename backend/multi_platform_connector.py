"""
Multi-Platform Connector - SDK VERSION (Viel stabiler!)
Migrated from REST API to official metaapi-python-sdk
Supports: MT5 Libertex Demo, MT5 ICMarkets Demo, MT5 Libertex REAL
Removed: Bitpanda (as requested)
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv
from metaapi_sdk_connector import MetaAPISDKConnector
import asyncio
from datetime import datetime, timezone, timedelta

# CRITICAL: Load .env BEFORE reading environment variables!
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env', override=True)  # FORCE override system env

# Global per-process commodity locks (shared across connectors in same process)
_COMMODITY_LOCKS: Dict[str, asyncio.Lock] = {}
# Per-commodity last trade timestamps to enforce short cooldowns (prevents near-duplicate opens)
_COMMODITY_LAST_TRADE: Dict[str, datetime] = {}
# Default cooldown in seconds (can be overridden via env var in the future)
_DEFAULT_COMMODITY_COOLDOWN_SECONDS = 300  # 5 minutes

# Protect the lock registry from race conditions during lock creation
_LOCK_REGISTRY_LOCK = None

async def _get_or_create_lock(commodity_id: str) -> asyncio.Lock:
    """
    Thread-safe way to get or create a lock for a commodity.
    Uses a meta-lock to protect the registry from race conditions.
    """
    global _LOCK_REGISTRY_LOCK
    
    # Initialize the meta-lock if needed
    if _LOCK_REGISTRY_LOCK is None:
        _LOCK_REGISTRY_LOCK = asyncio.Lock()
    
    # Use the meta-lock to protect access to _COMMODITY_LOCKS dict
    async with _LOCK_REGISTRY_LOCK:
        if commodity_id not in _COMMODITY_LOCKS:
            _COMMODITY_LOCKS[commodity_id] = asyncio.Lock()
            logger.debug(f"[LOCK] Created new lock for {commodity_id}")
        return _COMMODITY_LOCKS[commodity_id]

logger = logging.getLogger(__name__)

class MultiPlatformConnector:
    """Manages connections to multiple MT5 platforms using stable SDK"""
    
    def __init__(self):
        self.platforms = {}
        self.metaapi_token = os.environ.get('METAAPI_TOKEN', '')
        self._metaapi_client = None  # Shared MetaApi client to prevent multiple instances
        
        # MT5 Libertex Demo
        libertex_demo_id = os.environ.get('METAAPI_ACCOUNT_ID', '5cc9abd1-671a-447e-ab93-5abbfe0ed941')
        self.platforms['MT5_LIBERTEX_DEMO'] = {
            'type': 'MT5',
            'name': 'MT5 Libertex Demo',
            'account_id': libertex_demo_id,
            'region': 'london',
            'connector': None,
            'active': False,
            'balance': 0.0,
            'is_real': False
        }
        
        # MT5 ICMarkets Demo
        icmarkets_demo_id = os.environ.get('METAAPI_ICMARKETS_ACCOUNT_ID', 'd2605e89-7bc2-4144-9f7c-951edd596c39')
        self.platforms['MT5_ICMARKETS_DEMO'] = {
            'type': 'MT5',
            'name': 'MT5 ICMarkets Demo',
            'account_id': icmarkets_demo_id,
            'region': 'london',
            'connector': None,
            'active': False,
            'balance': 0.0,
            'is_real': False
        }
        
        # MT5 Libertex REAL (wenn in .env konfiguriert)
        libertex_real_id = os.environ.get('METAAPI_LIBERTEX_REAL_ACCOUNT_ID', '')
        if libertex_real_id and libertex_real_id != 'PLACEHOLDER_REAL_ACCOUNT_ID':
            self.platforms['MT5_LIBERTEX_REAL'] = {
                'type': 'MT5',
                'name': '💰 MT5 Libertex REAL 💰',
                'account_id': libertex_real_id,
                'region': 'london',
                'connector': None,
                'active': False,
                'balance': 0.0,
                'is_real': True  # ECHTES GELD!
            }
            logger.warning("⚠️  REAL MONEY ACCOUNT available: MT5_LIBERTEX_REAL")
        else:
            logger.info("ℹ️  Libertex Real Account not configured (only Demo available)")
        
        # MT5 ICMarkets REAL (wenn in .env konfiguriert)
        icmarkets_real_id = os.environ.get('METAAPI_ICMARKETS_REAL_ACCOUNT_ID', '')
        if icmarkets_real_id and icmarkets_real_id != 'PLACEHOLDER_REAL_ACCOUNT_ID':
            self.platforms['MT5_ICMARKETS_REAL'] = {
                'type': 'MT5',
                'name': '💰 MT5 ICMarkets REAL 💰',
                'account_id': icmarkets_real_id,
                'region': 'london',
                'connector': None,
                'active': False,
                'balance': 0.0,
                'is_real': True  # ECHTES GELD!
            }
            logger.warning("⚠️  REAL MONEY ACCOUNT available: MT5_ICMARKETS_REAL")
        else:
            logger.info("ℹ️  ICMarkets Real Account not configured (only Demo available)")
        
        # Legacy compatibility mappings
        if 'MT5_LIBERTEX_DEMO' in self.platforms:
            self.platforms['MT5_LIBERTEX'] = self.platforms['MT5_LIBERTEX_DEMO']
            self.platforms['LIBERTEX'] = self.platforms['MT5_LIBERTEX_DEMO']  # Short alias
        if 'MT5_ICMARKETS_DEMO' in self.platforms:
            self.platforms['MT5_ICMARKETS'] = self.platforms['MT5_ICMARKETS_DEMO']
            self.platforms['ICMARKETS'] = self.platforms['MT5_ICMARKETS_DEMO']  # Short alias
        
        logger.info(f"MultiPlatformConnector (SDK) initialized with {len(self.platforms)} platform(s)")
    
    async def connect_platform(self, platform_name: str) -> bool:
        """Connect to platform using stable SDK"""
        try:
            # Handle legacy names
            if platform_name in ['MT5_LIBERTEX', 'LIBERTEX']:
                platform_name = 'MT5_LIBERTEX_DEMO'
            elif platform_name in ['MT5_ICMARKETS', 'ICMARKETS']:
                platform_name = 'MT5_ICMARKETS_DEMO'
            
            if platform_name not in self.platforms:
                logger.error(f"Unknown platform: {platform_name}")
                return False
            
            platform = self.platforms[platform_name]
            
            # Already connected?
            if platform.get('active') and platform.get('connector'):
                connector = platform['connector']
                if await connector.is_connected():
                    logger.debug(f"ℹ️  {platform_name} already connected")
                    return True
                else:
                    logger.warning(f"⚠️  {platform_name} connection lost, reconnecting...")
            
            # Check if we should force REST API mode (Desktop environment)
            import os
            force_rest_api = os.environ.get('USE_REST_API_ONLY', 'false').lower() == 'true'
            disable_sdk = os.environ.get('DISABLE_SDK', 'false').lower() == 'true'
            
            connector = None
            success = False
            
            # DESKTOP MODE: Force REST API only
            if force_rest_api or disable_sdk:
                logger.info(f"🔄 DESKTOP MODE: Using REST API only (SDK disabled)")
                try:
                    from metaapi_connector import MetaAPIConnector
                    connector = MetaAPIConnector(
                        account_id=platform['account_id'],
                        token=self.metaapi_token
                    )
                    success = await connector.connect()
                    if success:
                        logger.info("✅ Connected via REST API (Desktop Mode)")
                except Exception as rest_error:
                    logger.error(f"❌ REST API connection failed: {rest_error}")
                    success = False
            else:
                # SERVER MODE: Try SDK first (works on both Server and Desktop with monkey-patch)
                try:
                    logger.info(f"🔄 Connecting to {platform_name} via SDK...")
                    # Initialize shared MetaApi client if not already done
                    if not self._metaapi_client:
                        from metaapi_cloud_sdk import MetaApi
                        opts = {
                            'application': 'MetaApi',
                            'requestTimeout': 60000,
                            'connectTimeout': 60000,
                            'retryOpts': {
                                'retries': 3,
                                'minDelayInSeconds': 1,
                                'maxDelayInSeconds': 30
                            }
                        }
                        self._metaapi_client = MetaApi(self.metaapi_token, opts)
                        logger.info("✅ Shared MetaApi client initialized")
                    
                    connector = MetaAPISDKConnector(
                        account_id=platform['account_id'],
                        token=self.metaapi_token,
                        shared_api_client=self._metaapi_client
                    )
                    success = await connector.connect()
                except Exception as sdk_error:
                    logger.warning(f"⚠️  SDK failed ({sdk_error}), trying REST API fallback...")
                    try:
                        from metaapi_connector import MetaAPIConnector
                        connector = MetaAPIConnector(
                            account_id=platform['account_id'],
                            token=self.metaapi_token
                        )
                        success = await connector.connect()
                        if success:
                            logger.info("✅ Connected via REST API fallback")
                    except Exception as rest_error:
                        logger.error(f"❌ REST API fallback failed: {rest_error}")
                        success = False
            if success:
                account_info = await connector.get_account_info()
                
                platform['connector'] = connector
                platform['active'] = True
                platform['balance'] = account_info.get('balance', 0.0) if account_info else 0.0
                
                logger.info(f"✅ SDK Connected: {platform_name} | Balance: €{platform['balance']:.2f}")
                return True
            else:
                logger.error(f"❌ Failed to connect {platform_name}")
                return False
            
        except Exception as e:
            logger.error(f"Error connecting to {platform_name}: {e}", exc_info=True)
            return False
    
    async def disconnect_platform(self, platform_name: str) -> bool:
        """Disconnect from platform"""
        try:
            if platform_name in self.platforms:
                platform = self.platforms[platform_name]
                if platform.get('connector'):
                    await platform['connector'].disconnect()
                platform['active'] = False
                platform['connector'] = None
                logger.info(f"Disconnected from {platform_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error disconnecting from {platform_name}: {e}")
            return False
    
    async def get_account_info(self, platform_name: str) -> Optional[Dict[str, Any]]:
        """Get account information"""
        try:
            # Handle legacy names
            if platform_name in ['MT5_LIBERTEX', 'LIBERTEX']:
                platform_name = 'MT5_LIBERTEX_DEMO'
            elif platform_name in ['MT5_ICMARKETS', 'ICMARKETS']:
                platform_name = 'MT5_ICMARKETS_DEMO'
            
            if platform_name not in self.platforms:
                logger.error(f"Unknown platform: {platform_name}")
                return None
            
            platform = self.platforms[platform_name]
            
            # Connect if needed
            if not platform['active'] or not platform['connector']:
                await self.connect_platform(platform_name)
            
            if platform['connector']:
                account_info = await platform['connector'].get_account_info()
                if account_info:
                    platform['balance'] = account_info.get('balance', 0.0)
                return account_info
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting account info for {platform_name}: {e}")
            return None
    
    async def execute_trade(self, platform_name: str, symbol: str, action: str, 
                           volume: float, stop_loss: float = None, 
                           take_profit: float = None) -> Optional[Dict[str, Any]]:
        """Execute trade via SDK"""
        try:
            # Handle legacy names
            if platform_name in ['MT5_LIBERTEX', 'LIBERTEX']:
                platform_name = 'MT5_LIBERTEX_DEMO'
            elif platform_name in ['MT5_ICMARKETS', 'ICMARKETS']:
                platform_name = 'MT5_ICMARKETS_DEMO'
            
            if platform_name not in self.platforms:
                logger.error(f"Unknown platform: {platform_name}")
                return None
            
            platform = self.platforms[platform_name]
            
            # SAFETY: Warnung bei Real Account
            if platform.get('is_real', False):
                logger.warning(f"⚠️⚠️⚠️  EXECUTING REAL MONEY TRADE on {platform_name}! ⚠️⚠️⚠️")
            
            # Connect if needed
            if not platform['active'] or not platform['connector']:
                await self.connect_platform(platform_name)
            
            if not platform['connector']:
                logger.error(f"Platform {platform_name} not connected")
                return None
            
            # Concurrency: try to map symbol -> commodity and acquire lock to prevent duplicates in-process
            commodity_id = None
            
            # Try hardcoded fallback mapping first (for tests and resilience)
            symbol_to_commodity_fallback = {
                'XAUUSD': 'GOLD',
                'XAGUSD': 'SILVER',
                'XPTUSD': 'PLATINUM',
                'XPDUSD': 'PALLADIUM',
                'PL': 'PLATINUM',
                'PA': 'PALLADIUM',
                'CL': 'WTI_CRUDE',
                'BRN': 'BRENT_CRUDE',
                'NG': 'NATURAL_GAS',
                'COPPER': 'COPPER',
                'BTCUSD': 'BITCOIN',
                'WHEAT': 'WHEAT',
                'CORN': 'CORN',
                'SOYBEAN': 'SOYBEANS',
                'COFFEE': 'COFFEE',
                'SUGAR': 'SUGAR'
            }
            
            symbol_upper = (symbol or '').upper()
            
            # First try hardcoded fallback
            commodity_id = symbol_to_commodity_fallback.get(symbol_upper)
            logger.debug(f"[LOCK] Fallback mapping for {symbol_upper}: {commodity_id}")
            
            # Then try dynamic mapping via commodity_processor
            if not commodity_id:
                try:
                    import commodity_processor
                    for cid, cinfo in commodity_processor.COMMODITIES.items():
                        candidates = [cinfo.get('mt5_libertex_symbol','') or '', cinfo.get('mt5_icmarkets_symbol','') or '', cid]
                        if any(cand and cand.upper() in symbol_upper for cand in candidates):
                            commodity_id = cid
                            logger.debug(f"[LOCK] Dynamic mapping: {symbol} -> {commodity_id}")
                            break
                except Exception as e:
                    logger.debug(f"[LOCK] Exception during commodity mapping: {e}")
            
            if commodity_id:
                logger.debug(f"[LOCK] Mapped symbol {symbol} -> commodity {commodity_id}")
            else:
                logger.debug(f"[LOCK] Could not map symbol {symbol} to any commodity")

            # Use async context manager to hold lock throughout trade execution
            if commodity_id:
                # Enforce short cooldown: if we opened a trade for this commodity recently, block
                last = _COMMODITY_LAST_TRADE.get(commodity_id)
                if last and (datetime.now(timezone.utc) - last).total_seconds() < _DEFAULT_COMMODITY_COOLDOWN_SECONDS:
                    logger.warning(f"⚠️ Trade für {commodity_id} übersprungen: Kurzfristiger Cooldown aktiv ({_DEFAULT_COMMODITY_COOLDOWN_SECONDS}s)")
                    return {"success": False, "error": "Cooldown active for this commodity"}

                # Get or create lock (race-condition safe using meta-lock)
                lock = await _get_or_create_lock(commodity_id)
                
                # Check if lock is already held by another task
                # lock.locked() returns True if the lock is held
                if lock.locked():
                    logger.warning(f"⚠️ Trade für {commodity_id} blockiert: Anderer Trade läuft bereits (Lock held)")
                    return {"success": False, "error": "Another trade for this commodity is in progress"}
                
                # Try to acquire lock
                logger.debug(f"[LOCK] Attempting to acquire lock for {commodity_id}...")
                try:
                    # Acquire lock and hold it while executing the trade
                    async with lock:
                        logger.debug(f"[LOCK] Lock acquired for {commodity_id}, executing trade...")
                        # Execute via SDK WHILE holding the lock
                        result = await platform['connector'].create_market_order(
                            symbol=symbol,
                            order_type=action.upper(),
                            volume=volume,
                            sl=stop_loss,
                            tp=take_profit
                        )

                        # If successful, set last trade timestamp to enforce cooldown
                        try:
                            if result and isinstance(result, dict) and result.get('success') and commodity_id:
                                _COMMODITY_LAST_TRADE[commodity_id] = datetime.now(timezone.utc)
                                logger.debug(f"[LOCK] Trade succeeded, set cooldown for {commodity_id}")
                        except Exception:
                            pass

                        logger.debug(f"[LOCK] Releasing lock for {commodity_id}")
                        return result
                except Exception as e:
                    logger.error(f"⚠️ Fehler beim Lock für {commodity_id}: {e}")
                    return {"success": False, "error": str(e)}
            else:
                # No commodity mapping - execute without lock (not ideal but graceful fallback)
                result = await platform['connector'].create_market_order(
                    symbol=symbol,
                    order_type=action.upper(),
                    volume=volume,
                    sl=stop_loss,
                    tp=take_profit
                )
                return result
            
        except Exception as e:
            logger.error(f"Error executing trade on {platform_name}: {e}")
            return None
    
    async def get_symbol_price(self, platform_name: str, symbol: str) -> Optional[Dict[str, Any]]:
        """
        V3.1.0: Hole aktuelle Bid/Ask Preise für ein Symbol.
        
        Returns:
            Dict mit {'bid': float, 'ask': float, 'spread': float} oder None
        """
        try:
            # Handle legacy names
            if platform_name in ['MT5_LIBERTEX', 'LIBERTEX']:
                platform_name = 'MT5_LIBERTEX_DEMO'
            elif platform_name in ['MT5_ICMARKETS', 'ICMARKETS']:
                platform_name = 'MT5_ICMARKETS_DEMO'
            
            if platform_name not in self.platforms:
                logger.debug(f"Unknown platform for price: {platform_name}")
                return None
            
            platform = self.platforms[platform_name]
            
            # Connect if needed
            if not platform['active'] or not platform['connector']:
                await self.connect_platform(platform_name)
            
            if not platform['connector']:
                return None
            
            connector = platform['connector']
            
            # Versuche über SDK Symbol-Preis zu holen
            try:
                # MetaAPI SDK method: get_symbol_price oder get_price
                if hasattr(connector, 'get_symbol_price'):
                    price_data = await connector.get_symbol_price(symbol)
                elif hasattr(connector, 'get_price'):
                    price_data = await connector.get_price(symbol)
                elif hasattr(connector, 'terminal_state') and connector.terminal_state:
                    # Versuche über terminal_state
                    state = connector.terminal_state
                    if hasattr(state, 'price'):
                        price_info = state.price(symbol)
                        if price_info:
                            price_data = {
                                'bid': price_info.get('bid', 0),
                                'ask': price_info.get('ask', 0)
                            }
                        else:
                            price_data = None
                    else:
                        price_data = None
                else:
                    # Fallback: Hole über Positionen oder Market Data
                    price_data = None
                
                if price_data:
                    bid = price_data.get('bid', 0)
                    ask = price_data.get('ask', 0)
                    spread = ask - bid if ask > bid else 0
                    
                    logger.debug(f"📊 Price for {symbol}: Bid={bid:.5f}, Ask={ask:.5f}, Spread={spread:.5f}")
                    
                    return {
                        'symbol': symbol,
                        'bid': bid,
                        'ask': ask,
                        'spread': spread,
                        'spread_percent': (spread / ((bid + ask) / 2) * 100) if (bid + ask) > 0 else 0,
                        'platform': platform_name
                    }
                
            except Exception as sdk_error:
                logger.debug(f"SDK price fetch error: {sdk_error}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting symbol price for {symbol} on {platform_name}: {e}")
            return None
    
    async def create_market_order(
        self,
        platform: str,
        symbol: str,
        order_type: str,
        volume: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a market order on the specified platform
        """
        try:
            # Normalize platform name
            platform_name = platform
            if platform_name in ['MT5_LIBERTEX', 'LIBERTEX']:
                platform_name = 'MT5_LIBERTEX_DEMO'
            elif platform_name in ['MT5_ICMARKETS', 'ICMARKETS']:
                platform_name = 'MT5_ICMARKETS_DEMO'
            
            if platform_name not in self.platforms:
                logger.error(f"Unknown platform: {platform_name}")
                return None
            
            platform_obj = self.platforms[platform_name]
            
            # Connect if not connected
            if not platform_obj['active'] or not platform_obj['connector']:
                logger.info(f"Platform {platform_name} not connected, connecting now...")
                await self.connect_platform(platform_name)
            
            if not platform_obj['connector']:
                logger.error(f"Platform {platform_name} not connected")
                return None
            
            logger.info(f"📈 Creating market order: {symbol} {order_type} {volume} on {platform_name}")
            
            # Execute via connector
            result = await platform_obj['connector'].create_market_order(
                symbol=symbol,
                order_type=order_type.upper(),
                volume=volume,
                sl=sl,
                tp=tp
            )
            
            if result:
                logger.info(f"✅ Order created: {result}")
            else:
                logger.error(f"❌ Failed to create order")
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating market order on {platform}: {e}", exc_info=True)
            return None
    
    async def get_open_positions(self, platform_name: str) -> List[Dict[str, Any]]:
        """Get open positions - DIREKT von MT5, keine Deduplizierung"""
        try:
            # Handle legacy names
            if platform_name in ['MT5_LIBERTEX', 'LIBERTEX']:
                platform_name = 'MT5_LIBERTEX_DEMO'
            elif platform_name in ['MT5_ICMARKETS', 'ICMARKETS']:
                platform_name = 'MT5_ICMARKETS_DEMO'
            
            if platform_name not in self.platforms:
                logger.error(f"Unknown platform: {platform_name}")
                return []
            
            platform = self.platforms[platform_name]
            
            if not platform['active'] or not platform['connector']:
                return []
            
            # Hole Positionen DIREKT vom SDK (MT5-Sync)
            positions = await platform['connector'].get_positions()
            
            # Filter nur offensichtliche Fehler (TRADE_RETCODE)
            clean_positions = []
            for pos in positions:
                ticket = pos.get('ticket') or pos.get('id') or pos.get('positionId')
                symbol = pos.get('symbol', '')
                
                # Skip nur error positions
                if ticket and 'TRADE_RETCODE' in str(ticket):
                    continue
                if 'TRADE_RETCODE' in symbol:
                    continue
                
                clean_positions.append(pos)
            
            logger.info(f"{platform_name}: {len(clean_positions)} open positions from MT5")
            return clean_positions
            
        except Exception as e:
            logger.error(f"Error getting positions for {platform_name}: {e}")
            return []
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Alias for compatibility"""
        # Return positions from all active platforms
        all_positions = []
        for platform_name in ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO', 'MT5_LIBERTEX_REAL']:
            if platform_name in self.platforms:
                positions = await self.get_open_positions(platform_name)
                for pos in positions:
                    pos['platform'] = platform_name
                all_positions.extend(positions)
        return all_positions
    
    def get_active_platforms(self) -> List[str]:
        """Get list of active platforms"""
        return [name for name, platform in self.platforms.items() 
                if platform['active'] and name in ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO', 'MT5_LIBERTEX_REAL']]
    
    def get_platform_status(self) -> Dict[str, Any]:
        """Get status of all platforms"""
        # Only return actual platforms, not legacy aliases
        actual_platforms = ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO', 'MT5_LIBERTEX_REAL']
        return {
            name: {
                'active': platform['active'],
                'balance': platform['balance'],
                'name': platform['name'],
                'is_real': platform.get('is_real', False)
            }
            for name, platform in self.platforms.items()
            if name in actual_platforms
        }
    
    async def close_position(self, platform_name: str, position_id: str) -> dict:
        """
        Schließe Position auf Platform
        
        V2.3.31: Gibt jetzt dict mit Details zurück statt nur bool
        Returns: {'success': bool, 'error': str|None, 'error_type': str|None}
        """
        try:
            # Handle legacy names
            if platform_name in ['MT5_LIBERTEX', 'LIBERTEX']:
                platform_name = 'MT5_LIBERTEX_DEMO'
            elif platform_name in ['MT5_ICMARKETS', 'ICMARKETS']:
                platform_name = 'MT5_ICMARKETS_DEMO'
            
            if platform_name not in self.platforms:
                logger.error(f"Unknown platform: {platform_name}")
                return {'success': False, 'error': f'Unbekannte Plattform: {platform_name}', 'error_type': 'UNKNOWN_PLATFORM'}
            
            platform = self.platforms[platform_name]
            
            # Connect if needed
            if not platform['active'] or not platform['connector']:
                await self.connect_platform(platform_name)
            
            if not platform['connector']:
                logger.error(f"Platform {platform_name} not connected")
                return {'success': False, 'error': 'Plattform nicht verbunden', 'error_type': 'NOT_CONNECTED'}
            
            # Close via SDK - V2.3.31: Jetzt mit detaillierter Rückgabe
            result = await platform['connector'].close_position(position_id)
            
            # Handle both old (bool) and new (dict) return types
            if isinstance(result, bool):
                # Legacy: bool return
                if result:
                    logger.info(f"✅ Position {position_id} geschlossen auf {platform_name}")
                    return {'success': True, 'error': None, 'error_type': None}
                else:
                    return {'success': False, 'error': 'Position konnte nicht geschlossen werden', 'error_type': 'UNKNOWN'}
            else:
                # New: dict return with details
                if result.get('success'):
                    logger.info(f"✅ Position {position_id} geschlossen auf {platform_name}")
                else:
                    logger.warning(f"⚠️ Position {position_id}: {result.get('error_type')} - {result.get('error')}")
                return result
        except Exception as e:
            logger.error(f"Error closing position {position_id}: {e}")
            return {'success': False, 'error': str(e), 'error_type': 'EXCEPTION'}
    
    async def get_closed_trades(self, start_time: str = None, end_time: str = None, 
                                platform_filter: str = None) -> List[Dict[str, Any]]:
        """
        V2.3.38: Hole geschlossene Trades von ALLEN aktiven MT5-Plattformen
        FIXES: Real Account Support, mehr Daten abrufen (365 Tage default)
        
        Args:
            start_time: ISO Format oder None (default: letzte 365 Tage)
            end_time: ISO Format oder None (default: jetzt)
            platform_filter: Optional - nur von dieser Plattform
        
        Returns:
            Liste aller geschlossenen Trades mit MT5-Daten
        """
        from datetime import datetime, timezone, timedelta
        
        # Default: Letzte 365 Tage für vollständige History
        if not end_time:
            end_dt = datetime.now(timezone.utc)
            end_time = end_dt.isoformat()
        else:
            try:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except:
                end_dt = datetime.now(timezone.utc)
                end_time = end_dt.isoformat()
            
        if not start_time:
            start_dt = end_dt - timedelta(days=365)
            start_time = start_dt.isoformat()
        
        all_trades = []
        
        # V2.3.38: Alle verfügbaren Plattformen inkl. REAL
        platforms_to_check = list(self.platforms.keys())
        logger.info(f"📊 get_closed_trades: Checking platforms: {platforms_to_check}")
        
        if platform_filter:
            platforms_to_check = [platform_filter] if platform_filter in platforms_to_check else []
        
        for platform_name in platforms_to_check:
            if platform_name not in self.platforms:
                continue
                
            platform = self.platforms[platform_name]
            
            # Verbinde falls nötig
            if not platform['active'] or not platform['connector']:
                try:
                    logger.info(f"🔄 Connecting to {platform_name} for history...")
                    await self.connect_platform(platform_name)
                except Exception as e:
                    logger.warning(f"Could not connect to {platform_name}: {e}")
                    continue
            
            if not platform['connector']:
                logger.warning(f"{platform_name}: No connector available")
                continue
            
            try:
                # Hole Deals von dieser Plattform
                logger.info(f"📊 Fetching deals from {platform_name}: {start_time} to {end_time}")
                deals = await platform['connector'].get_deals_by_time_range(
                    start_time, end_time, offset=0, limit=5000  # Erhöht auf 5000
                )
                
                if not deals:
                    logger.info(f"{platform_name}: Keine Deals gefunden")
                    continue
                
                logger.info(f"{platform_name}: {len(deals)} raw deals received")
                
                # Füge Plattform-Info hinzu und filtere nur CLOSE-Deals
                closed_count = 0
                for deal in deals:
                    deal['platform'] = platform_name
                    deal['platform_name'] = platform['name']
                    deal['is_real'] = platform.get('is_real', False)
                    
                    # Nur geschlossene Positionen (DEAL_ENTRY_OUT)
                    entry_type = deal.get('entryType', '')
                    if entry_type in ['DEAL_ENTRY_OUT', 'DEAL_ENTRY_INOUT']:
                        all_trades.append(deal)
                        closed_count += 1
                
                logger.info(f"✅ {platform_name}: {closed_count} geschlossene Trades")
                
            except Exception as e:
                logger.error(f"Error getting closed trades from {platform_name}: {e}", exc_info=True)
                continue
        
        # Sortiere nach Zeit (neueste zuerst)
        all_trades.sort(key=lambda x: x.get('time', ''), reverse=True)
        
        logger.info(f"📊 Total: {len(all_trades)} geschlossene Trades von allen Plattformen")
        return all_trades

    async def modify_position(self, ticket: str, stop_loss: float = None, 
                             take_profit: float = None, platform: str = 'MT5_LIBERTEX_DEMO') -> bool:
        """
        Modify existing position SL/TP via MetaAPI
        
        Args:
            ticket: Position ticket ID
            stop_loss: New stop loss price
            take_profit: New take profit price
            platform: Platform name
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Handle legacy platform names
            if platform in ['MT5_LIBERTEX', 'LIBERTEX']:
                platform = 'MT5_LIBERTEX_DEMO'
            elif platform in ['MT5_ICMARKETS', 'ICMARKETS']:
                platform = 'MT5_ICMARKETS_DEMO'
            
            if platform not in self.platforms:
                logger.error(f"Unknown platform: {platform}")
                return False
            
            platform_obj = self.platforms[platform]
            
            # Connect if needed
            if not platform_obj['active'] or not platform_obj['connector']:
                logger.info(f"Connecting to {platform} for position modification...")
                await self.connect_platform(platform)
            
            if not platform_obj['connector']:
                logger.error(f"Platform {platform} not connected")
                return False
            
            # Modify via SDK
            logger.info(f"Modifying position {ticket} on {platform}: SL={stop_loss}, TP={take_profit}")
            
            result = await platform_obj['connector'].modify_position(
                position_id=ticket,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            if result:
                logger.info(f"✅ Successfully modified position {ticket} on {platform}")
                return True
            else:
                logger.error(f"❌ Failed to modify position {ticket} on {platform} - SDK returned False")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error modifying position {ticket} on {platform}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


# Global instance
multi_platform = MultiPlatformConnector()
