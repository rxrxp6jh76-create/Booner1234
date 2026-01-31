"""
AI Trading Bot - Vollautomatische KI-gesteuerte Trading-Plattform
Überwacht, analysiert, öffnet und schließt Positionen AUTOMATISCH

Features:
- 🆕 7 Trading-Strategien (v2.4.0) mit fortgeschrittener KI-Logik
- Multi-Strategie-Analyse (RSI, MACD, MA, Bollinger Bands, Stochastic)
- News-Integration & Sentiment-Analyse
- LLM-basierte Entscheidungsfindung (GPT-5)
- Automatisches Position-Management
- Risk Management & Portfolio-Balance
- 🆕 v2.4.0: Konfidenz-basierte SL/TP mit ATR
- 🆕 v2.4.0: Dynamisches CRV basierend auf Wahrscheinlichkeit
"""
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta, timezone
import database as db_module
import os
import uuid
from dotenv import load_dotenv
from typing import Dict, List, Optional
from collections import OrderedDict

# 🆕 v2.3.29: Import neue Trading-Strategien
from strategies import (
    MeanReversionStrategy,
    MomentumTradingStrategy,
    BreakoutTradingStrategy,
    GridTradingStrategy
)

# 🆕 v2.4.0: Import fortgeschrittene Trading-Logik
from advanced_trading_logic import advanced_trading, TradingStrategy, TradeSignal

# 🆕 v2.4.0: Import Self-Learning Trading-Journal
from self_learning_journal import trading_journal, MarketPhase, TrendDirection

# 🆕 v2.5.0: Import Autonomous Trading Intelligence
from autonomous_trading_intelligence import (
    autonomous_trading, 
    MarketState, 
    StrategyCluster,
    UniversalConfidenceScore
)

load_dotenv()

# Global per-process commodity locks (shared across AITradingBot instances)
_COMMODITY_LOCKS: Dict[str, asyncio.Lock] = {}

# Logging mit Rotation
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            os.path.join(log_dir, 'ai_bot.log'),
            maxBytes=10*1024*1024,
            backupCount=3
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AITradingBot:
    """KI-gesteuerter Trading Bot - übernimmt ALLE Trading-Entscheidungen
    
    DUAL TRADING STRATEGY:
    - Swing Trading: Langfristig, größere Positionen, 80% Balance
    - Day Trading: Kurzfristig, kleinere Positionen, 20% Balance
    """
    
    def __init__(self):
        self.running = False
        self.db = None
        self.settings = None
        self.market_data = {}
        self.market_analyzer = None
        self.llm_chat = None
        # MEMORY FIX: Begrenzte History mit deque (max 1000 Trades)
        from collections import deque
        self.trade_history = deque(maxlen=1000)  # Auto-evicts oldest
        self.last_analysis_time_swing = {}  # Pro Commodity für Swing Trading
        self.last_analysis_time_day_trading = {}  # Pro Commodity für Day Trading
        self.trades_this_hour = []  # Track Trades pro Stunde
        
        # 🆕 v2.3.29: Neue Trading-Strategien
        self.mean_reversion_strategy = None
        self.momentum_strategy = None
        self.breakout_strategy = None
        self.grid_strategy = None
        self.last_analysis_time_by_strategy = {}  # Per Strategie und Commodity
        # Concurrency protections
        # Per-commodity asyncio locks to avoid simultaneous trade openings in the same process
        # Use module-level registry so locks are shared across AITradingBot instances in the same process
        self._commodity_locks = _COMMODITY_LOCKS
        # In-memory cooldown/reservation tracker for recent or in-flight trades
        self._asset_cooldown_tracker = {}
        
    async def initialize(self):
        """Initialisiere Bot"""
        logger.info("🤖 AI Trading Bot wird mit SQLite initialisiert...")
        
        # Reload .env für API-Keys
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        # SQLite Database Connection
        await db_module.init_database()
        
        # Create DB object with collections
        self.db = type('DB', (), {
            'trading_settings': db_module.trading_settings,
            'trades': db_module.trades,
            'trade_settings': db_module.trade_settings,
            'market_data': db_module.market_data,
            'market_data_history': db_module.market_data_history
        })()
        
        # Load Settings
        self.settings = await self.db.trading_settings.find_one({"id": "trading_settings"})
        if not self.settings:
            logger.error("❌ Settings nicht gefunden!")
            return False
        
        # Market Analyzer initialisieren (mit neu geladenen ENV vars)
        from market_analysis import MarketAnalyzer
        self.market_analyzer = MarketAnalyzer()
        
        # LLM Chat für KI-Entscheidungen initialisieren (optional)
        try:
            from ai_chat_service import get_ai_chat_instance
            ai_provider = self.settings.get('ai_provider', 'emergent')
            ai_model = self.settings.get('ai_model', 'gpt-5')
            self.llm_chat = await get_ai_chat_instance(
                self.settings, 
                ai_provider, 
                ai_model, 
                session_id="ai_trading_bot"
            )
            logger.info(f"✅ LLM initialisiert: {ai_provider}/{ai_model}")
        except Exception as e:
            logger.warning(f"⚠️  LLM nicht verfügbar: {e}")
            self.llm_chat = None
        
        # 🆕 v2.3.29: Initialisiere neue Trading-Strategien
        try:
            self.mean_reversion_strategy = MeanReversionStrategy(self.settings)
            self.momentum_strategy = MomentumTradingStrategy(self.settings)
            self.breakout_strategy = BreakoutTradingStrategy(self.settings)
            self.grid_strategy = GridTradingStrategy(self.settings)
            logger.info("✅ Alle 7 Trading-Strategien initialisiert")
        except Exception as e:
            logger.warning(f"⚠️ Konnte neue Strategien nicht initialisieren: {e}")
            # Strategien bleiben None wenn Fehler - Bot läuft trotzdem
        
        logger.info(f"✅ Bot initialisiert | Auto-Trading: {self.settings.get('auto_trading', False)}")
        
        # 🎯 BEIM START: Prüfe alle offenen Trades und erstelle fehlende Settings
        await self.create_missing_trade_settings()
        
        return True
    
    async def create_missing_trade_settings(self):
        """Erstellt SL/TP Settings für alle offenen Trades ohne Settings"""
        try:
            logger.info("🔍 Prüfe offene Trades auf fehlende Settings...")
            
            from multi_platform_connector import multi_platform
            
            # Hole alle offenen Positionen von allen Plattformen
            all_positions = []
            for platform in ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO', 'MT5_LIBERTEX_REAL']:
                if platform in self.settings.get('active_platforms', []):
                    try:
                        positions = await multi_platform.get_open_positions(platform)
                        for pos in positions:
                            pos['platform'] = platform
                        all_positions.extend(positions)
                    except Exception as e:
                        logger.warning(f"Konnte Positionen von {platform} nicht holen: {e}")
            
            logger.info(f"📊 Gefunden: {len(all_positions)} offene Positionen")
            
            created_count = 0
            for pos in all_positions:
                ticket = pos.get('id') or pos.get('ticket') or pos.get('positionId')
                trade_id = f"mt5_{ticket}"
                platform = pos.get('platform', 'MT5_LIBERTEX_DEMO')
                
                # Prüfe ob Settings existieren
                existing = await self.db.trade_settings.find_one({'trade_id': trade_id})
                
                if not existing:
                    # Erstelle Settings
                    symbol = pos.get('symbol', '')
                    pos_type = pos.get('type', 'BUY')
                    entry_price = pos.get('openPrice') or pos.get('price_open') or pos.get('entry_price', 0)
                    volume = pos.get('volume', 0.01)
                    
                    # Bestimme Strategie basierend auf globalen Settings
                    # V2.3.36 FIX: Prüfe scalping_enabled statt trading_strategy
                    scalping_enabled = self.settings.get('scalping_enabled', False)
                    
                    if scalping_enabled:
                        strategy = 'scalping'
                        tp_percent = self.settings.get('scalping_take_profit_percent', 0.25)
                        sl_percent = self.settings.get('scalping_stop_loss_percent', 0.15)
                    else:
                        # Default: day_trading Strategy
                        strategy = 'day_trading'
                        tp_percent = self.settings.get('day_trading_take_profit_percent', 2.5)
                        sl_percent = self.settings.get('day_trading_stop_loss_percent', 1.5)
                    
                    # Berechne SL/TP
                    if 'BUY' in str(pos_type).upper():
                        stop_loss_price = entry_price * (1 - sl_percent / 100)
                        take_profit_price = entry_price * (1 + tp_percent / 100)
                    else:
                        stop_loss_price = entry_price * (1 + sl_percent / 100)
                        take_profit_price = entry_price * (1 - tp_percent / 100)
                    
                    # Speichere in DB
                    await self.db.trade_settings.insert_one({
                        'trade_id': trade_id,
                        'stop_loss': stop_loss_price,
                        'take_profit': take_profit_price,
                        'strategy': strategy,
                        'created_at': datetime.now(timezone.utc).isoformat(),
                        'entry_price': entry_price,
                        'platform': platform,
                        'created_by': 'AI_STARTUP_AUTO'
                    })
                    
                    logger.info(f"✅ Settings erstellt für #{ticket} ({strategy.upper()}): SL={stop_loss_price:.2f}, TP={take_profit_price:.2f}")
                    created_count += 1
            
            if created_count > 0:
                logger.info(f"🎯 {created_count} Trade Settings beim Start erstellt!")
            else:
                logger.info("✓ Alle offenen Trades haben bereits Settings")
                
        except Exception as e:
            logger.error(f"❌ Fehler beim Erstellen fehlender Settings: {e}")
    
    async def run_forever(self):
        """Hauptschleife - läuft kontinuierlich"""
        self.running = True
        logger.info("🚀 AI Trading Bot gestartet - läuft kontinuierlich!")
        
        iteration = 0
        last_market_check = 0  # Timestamp für Market-Hours Check
        
        while self.running:
            try:
                iteration += 1
                logger.info(f"\n{'='*60}")
                logger.info(f"🤖 Bot Iteration #{iteration} - {datetime.now().strftime('%H:%M:%S')}")
                logger.info(f"{'='*60}")
                
                # Reload settings (könnte sich ändern)
                self.settings = await self.db.trading_settings.find_one({"id": "trading_settings"})
                
                if not self.settings.get('auto_trading', False):
                    logger.warning("⚠️  Auto-Trading ist DEAKTIVIERT in Settings")
                    await asyncio.sleep(30)
                    continue
                
                # 🕐 MARKET HOURS CHECK (konfigurierbar über Settings)
                respect_market_hours = self.settings.get('respect_market_hours', True)
                pause_when_all_closed = self.settings.get('pause_when_all_markets_closed', True)
                check_interval_minutes = self.settings.get('market_hours_check_interval_minutes', 5)
                
                if respect_market_hours:
                    current_time = datetime.now().timestamp()
                    check_interval_seconds = check_interval_minutes * 60
                    
                    if current_time - last_market_check > check_interval_seconds:
                        last_market_check = current_time
                        
                        # Prüfe ob mindestens ein Markt offen ist
                        import commodity_processor
                        enabled_commodities = self.settings.get('enabled_commodities', [])
                        any_market_open = False
                        
                        for commodity_id in enabled_commodities:
                            if commodity_processor.is_market_open(commodity_id):
                                any_market_open = True
                                break
                        
                        if not any_market_open and pause_when_all_closed:
                            # Finde nächste Marktöffnung
                            next_opens = []
                            for commodity_id in enabled_commodities[:3]:  # Nur erste 3 prüfen
                                next_open = commodity_processor.get_next_market_open(commodity_id)
                                if next_open:
                                    next_opens.append(f"{commodity_id}: {next_open}")
                            
                            logger.warning("⏰ ALLE Märkte geschlossen - Bot pausiert (konfigurierbar in Settings)")
                            if next_opens:
                                logger.info(f"   Nächste Öffnungen: {', '.join(next_opens[:2])}")
                            
                            # Längere Pause wenn alle Märkte zu
                            await asyncio.sleep(check_interval_seconds)  # Warten basierend auf Settings
                            continue
                        elif not any_market_open:
                            logger.info("⏰ Alle Märkte geschlossen, aber Bot läuft weiter (pause_when_all_markets_closed=False)")
                        else:
                            logger.debug("✅ Mindestens ein Markt ist offen - Trading aktiv")
                else:
                    logger.debug("⏰ Market Hours Check deaktiviert - Bot läuft kontinuierlich")
                
                # 1. Marktdaten aktualisieren
                await self.fetch_market_data()
                
                # 2. ALLE offenen Positionen überwachen
                await self.monitor_open_positions()
                
                # 2b. EoD / Friday Auto-Close Checks (close profitable trades before market close / weekend)
                await self.check_auto_close_events()
                
                # V3.3.0: ARCHITEKTUR-FIX - Nur noch Positionen-Monitoring, keine direkten Analysen mehr
                # Die Signale kommen jetzt von der 4-Pillar-KI (multi_bot_system.py) die die beste Strategie dynamisch wählt
                # Das verhindert Strategie-Mismatch und nutzt alle 7 Strategien korrekt
                
                # 3. SCALPING: Ultra-schnelle Analyse (alle 15 Sekunden)
                # V2.3.36 FIX: Prüfe scalping_enabled statt trading_strategy!
                # V3.3.0: DEPRECATED - Signale kommen jetzt von 4-Pillar-KI
                # if self.settings.get('scalping_enabled', False):
                #     await self.analyze_and_open_trades(strategy="scalping")
                
                # 4. SWING TRADING: KI-Analyse für neue Swing-Trades (alle 10 Min)
                # V3.3.0: DEPRECATED - Signale kommen jetzt von 4-Pillar-KI
                # if self.settings.get('swing_trading_enabled', False):
                #     await self.analyze_and_open_trades(strategy="swing")
                
                # 5. DAY TRADING: KI-Analyse für neue Day-Trades (jede Minute)
                # V3.3.0: DEPRECATED - Signale kommen jetzt von 4-Pillar-KI
                # if self.settings.get('day_trading_enabled', True):
                #     await self.analyze_and_open_trades(strategy="day")
                
                # 🆕 v2.3.29: NEUE STRATEGIEN - Signal-Generation
                
                # 6. MEAN REVERSION: Bollinger Bands + RSI (alle 5 Minuten)
                # V3.3.0: DEPRECATED - Signale kommen jetzt von 4-Pillar-KI
                # if self.settings.get('mean_reversion_enabled', False):
                #     await self.analyze_mean_reversion_signals()
                
                # 7. MOMENTUM TRADING: Trend-Following (alle 5 Minuten)
                # V3.3.0: DEPRECATED - Signale kommen jetzt von 4-Pillar-KI
                # if self.settings.get('momentum_enabled', False):
                #     await self.analyze_momentum_signals()
                
                # 8. BREAKOUT TRADING: Ausbrüche (alle 2 Minuten)
                # V3.3.0: DEPRECATED - Signale kommen jetzt von 4-Pillar-KI
                # if self.settings.get('breakout_enabled', False):
                #     await self.analyze_breakout_signals()
                
                # 9. GRID TRADING: Grid-Struktur (kontinuierlich)
                # V3.3.0: DEPRECATED - Signale kommen jetzt von 4-Pillar-KI
                # if self.settings.get('grid_enabled', False):
                #     await self.analyze_grid_signals()
                
                # 10. Automatisches Schließen alter Positionen (Time-Based Exit)
                if self.settings.get('day_trading_enabled', True):
                    await self.close_expired_day_trades()
                
                if self.settings.get('swing_trading_enabled', False):
                    await self.close_expired_swing_trades()
                
                # Scalping: Sehr kurze Haltezeit (5 Minuten max)
                # V2.3.36 FIX: Prüfe scalping_enabled statt trading_strategy!
                if self.settings.get('scalping_enabled', False):
                    await self.close_expired_scalping_trades()
                
                # 6. Memory Management: Behalte nur essenzielle Daten für KI
                iteration_count = getattr(self, '_iteration_count', 0) + 1
                self._iteration_count = iteration_count
                
                # ROLLING WINDOW für market_data: Nur letzte 60 Datenpunkte pro Commodity
                # Das reicht für alle technischen Indikatoren (MA50, RSI14, MACD, BB20)
                if iteration_count % 5 == 0:  # Alle 50 Sekunden
                    for commodity_id in list(self.market_data.keys()):
                        if isinstance(self.market_data[commodity_id], list):
                            if len(self.market_data[commodity_id]) > 60:
                                # Behalte nur die letzten 60 Datenpunkte
                                self.market_data[commodity_id] = self.market_data[commodity_id][-60:]
                
                # Garbage Collection alle 10 Iterationen (100s)
                if iteration_count % 10 == 0:
                    logger.info(f"🧹 Memory Cleanup nach {iteration_count} Iterationen...")
                    
                    # Zähle Datenpunkte
                    total_points = sum(len(v) if isinstance(v, list) else 1 for v in self.market_data.values())
                    logger.info(f"  Market Data: {len(self.market_data)} Commodities, {total_points} Datenpunkte")
                    
                    # Force garbage collection
                    import gc
                    collected = gc.collect()
                    logger.info(f"  ✓ Cleanup: {collected} Objekte freigegeben")
                
                # Cleanup alte geschlossene Trades aus DB (alle 100 Iterationen = ~16 Min)
                if iteration_count % 100 == 0:
                    logger.info("🗑️ Bereinige alte geschlossene Trades (älter als 30 Tage)...")
                    try:
                        # BUGFIX: Removed local import that shadowed global datetime import
                        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
                        
                        # Lösche sehr alte geschlossene Trades
                        result = await self.db.trades.delete_many({
                            "status": "CLOSED",
                            "closed_at": {"$lt": cutoff_date}
                        })
                        
                        if result.deleted_count > 0:
                            logger.info(f"  ✓ {result.deleted_count} alte Trades gelöscht")
                    except Exception as e:
                        logger.error(f"  ❌ Fehler beim Löschen alter Trades: {e}")
                
                # 7. Kurze Pause (alle 10 Sekunden)
                logger.info("✅ Iteration abgeschlossen, warte 10 Sekunden...")
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"❌ Fehler in Bot-Iteration: {e}", exc_info=True)
                await asyncio.sleep(30)
    
    async def fetch_market_data(self):
        """Hole aktuelle Marktdaten + Preis-Historie für neue Strategien"""
        try:
            # Hole Marktdaten aus market_data Collection (werden von server.py gespeichert)
            cursor = await self.db.market_data.find({})
            market_docs = await cursor.to_list(100)
            
            self.market_data = {}
            for doc in market_docs:
                # Versuche beide Feldnamen
                commodity_id = doc.get('commodity_id') or doc.get('commodity')
                if commodity_id:
                    self.market_data[commodity_id] = doc
                    
                    # 🆕 v2.3.29: Lade Preis-Historie für neue Strategien
                    # Versuche aus market_data_history zu laden
                    try:
                        # Hole letzte 250 Datenpunkte (für MA(200))
                        history_cursor = await self.db.market_data_history.find(
                            {"commodity": commodity_id}
                        ).sort("timestamp", -1).limit(250)
                        
                        history_docs = await history_cursor.to_list(250)
                        
                        if history_docs:
                            # Extrahiere Preise (neueste zuerst, muss umgedreht werden)
                            prices = [h.get('price', 0) for h in reversed(history_docs)]
                            self.market_data[commodity_id]['price_history'] = prices
                        else:
                            # Fallback: Simuliere History aus aktuellem Preis
                            current_price = doc.get('current_price', 0)
                            if current_price > 0:
                                # Erstelle künstliche History mit leichten Variationen
                                import random
                                self.market_data[commodity_id]['price_history'] = [
                                    current_price * (1 + random.uniform(-0.02, 0.02))
                                    for _ in range(250)
                                ]
                    except Exception as e:
                        # Wenn market_data_history nicht existiert, nutze aktuellen Preis
                        current_price = doc.get('current_price', 0)
                        if current_price > 0:
                            self.market_data[commodity_id]['price_history'] = [current_price] * 250
            
            logger.info(f"📊 Marktdaten aktualisiert: {len(self.market_data)} Rohstoffe")
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Marktdaten: {e}")
    
    async def monitor_open_positions(self):
        """🤖 KI ÜBERWACHT SL/TP - schließt automatisch bei Ziel!
        
        🆕 v2.5.0: Erweitert um Autonomous Risk Circuits:
        - Breakeven-Automatik (bei 50% TP)
        - Time-Exit (bei stagnierendem Trade)
        - Trailing Stop (für Momentum)
        """
        logger.info("👀 KI überwacht offene Positionen und prüft SL/TP + Risk Circuits...")
        
        try:
            from multi_platform_connector import multi_platform
            
            # Strategy-spezifische Settings werden dynamisch pro Position geladen
            
            platforms = ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO']
            total_positions = 0
            closed_positions = 0
            
            for platform in platforms:
                if platform not in self.settings.get('active_platforms', []):
                    continue
                
                try:
                    positions = await multi_platform.get_open_positions(platform)
                    total_positions += len(positions)
                    
                    for pos in positions:
                        # Extrahiere Daten
                        entry_price = pos.get('price_open') or pos.get('openPrice') or pos.get('entry_price')
                        current_price = pos.get('price_current') or pos.get('currentPrice') or pos.get('price')
                        pos_type = str(pos.get('type', '')).upper()
                        symbol = pos.get('symbol', '')
                        ticket = pos.get('ticket') or pos.get('id') or pos.get('positionId')
                        profit = pos.get('profit', 0)
                        quantity = pos.get('volume', 0) or pos.get('quantity', 0) or pos.get('size', 0)
                        
                        if not entry_price or not current_price or not ticket:
                            continue
                        
                        trade_id = f"mt5_{ticket}"
                        
                        # ═══════════════════════════════════════════════════════════
                        # 🆕 v2.5.0: RISK CIRCUITS CHECK (Breakeven + Time-Exit)
                        # ═══════════════════════════════════════════════════════════
                        risk_action = {'action': 'none', 'reason': 'not_checked'}
                        try:
                            risk_action = autonomous_trading.check_risk_circuits(
                                trade_id,
                                current_price,
                                current_profit=profit
                            )

                            # Debug-Ausgabe für alle offenen Trades: aktueller Profit, Peak und verstrichene Minuten
                            state = autonomous_trading.active_risk_circuits.get(trade_id)
                            elapsed = getattr(state, 'elapsed_minutes', None) if state else None
                            peak_profit = getattr(state, 'peak_profit', None) if state else None
                            peak_progress = getattr(state, 'peak_progress_percent', None) if state else None
                            logger.info(
                                f"[PEAK] {symbol}#{ticket} action={risk_action.get('action')}, profit={profit:.2f}, peak_profit={peak_profit}, "
                                f"peak_progress={peak_progress}, elapsed_min={elapsed}"
                            )
                            
                            # 🆕 v3.1.18: PERSISTIERE PEAK IN DB (überlebt Backend-Neustart)
                            if state and (peak_profit is not None or peak_progress is not None):
                                try:
                                    await self.db.trade_settings.update_one(
                                        {'trade_id': trade_id},
                                        {'$set': {
                                            'peak_profit': peak_profit,
                                            'peak_progress_percent': peak_progress
                                        }},
                                        upsert=True
                                    )
                                except Exception as e:
                                    logger.debug(f"Peak-Persistierung fehlgeschlagen für {trade_id}: {e}")

                            if risk_action['action'] == 'move_sl_breakeven':
                                # Aktualisiere SL auf Breakeven
                                new_sl = risk_action['new_sl']
                                logger.info(f"🔐 BREAKEVEN für #{ticket}: SL → {new_sl:.4f}")
                                
                                # Update in DB
                                await self.db.trade_settings.update_one(
                                    {'trade_id': trade_id},
                                    {'$set': {'stop_loss': new_sl, 'breakeven_active': True}}
                                )
                                
                            elif risk_action['action'] == 'profit_drawdown_exit':
                                # Gewinn fällt nach 30min um >=30% vom Peak: Trade schließen
                                logger.warning(f"📉 PROFIT-DRAWDOWN EXIT für #{ticket}: {risk_action['reason']}")

                                try:
                                    close_result = await multi_platform.close_position(platform, ticket)
                                    if close_result:
                                        logger.info(f"✅ Profit-Drawdown Exit erfolgreich: #{ticket}")
                                        autonomous_trading.remove_risk_circuit(trade_id)

                                        # Update Performance Stats
                                        strategy = pos.get('strategy', 'day')
                                        autonomous_trading.update_strategy_performance(
                                            strategy, is_winner=(profit > 0), profit=profit
                                        )
                                except Exception as e:
                                    logger.error(f"Profit-Drawdown Exit fehlgeschlagen: {e}")
                                continue  # Nächste Position
                                
                            elif risk_action['action'] == 'trailing_stop':
                                # Trailing Stop nachziehen
                                new_sl = risk_action['new_sl']
                                logger.info(f"🔄 TRAILING STOP für #{ticket}: SL → {new_sl:.4f}")
                                
                                await self.db.trade_settings.update_one(
                                    {'trade_id': trade_id},
                                    {'$set': {'stop_loss': new_sl}}
                                )
                                
                        except Exception as e:
                            logger.debug(f"Risk Circuit Check fehlgeschlagen für #{ticket}: {e}")
                        
                        # ═══════════════════════════════════════════════════════════
                        
                        # Hole Strategie aus DB Trade (falls vorhanden)
                        # DEFAULT: 'day' für unbekannte/manuelle Trades (konservativer)
                        db_trade = await self.db.trades.find_one({"mt5_ticket": str(ticket), "status": "OPEN"})
                        strategy = db_trade.get('strategy', 'day') if db_trade else 'day'
                        
                        # 🎯 INDIVIDUELLE TRADE SETTINGS haben Priorität!
                        individual_settings = await self.db.trade_settings.find_one({'trade_id': trade_id})
                        
                        if individual_settings and (individual_settings.get('stop_loss') or individual_settings.get('take_profit')):
                            # Nutze individuelle Settings vom User
                            stop_loss_price = individual_settings.get('stop_loss')
                            take_profit_price = individual_settings.get('take_profit')
                            logger.info(f"🎯 Nutze individuelle Settings für #{ticket}: SL={stop_loss_price}, TP={take_profit_price}")
                        elif not individual_settings:
                            # 🚨 KEINE SETTINGS GEFUNDEN - AUTOMATISCH ERSTELLEN!
                            logger.warning(f"⚠️ Trade #{ticket} hat keine SL/TP Settings - erstelle automatisch...")
                            
                            # Berechne SL/TP basierend auf DUAL TRADING STRATEGY Settings
                            # Nutze erkannte Strategie oder Swing als Default
                            
                            # Prüfe Modus: Prozent oder Euro (strategie-abhängig)
                            if strategy == 'day_trading':
                                mode = self.settings.get('day_trading_tp_sl_mode', 'percent')
                            elif strategy == 'scalping':
                                mode = 'percent'  # Scalping nutzt immer Prozent
                            else:
                                mode = self.settings.get('swing_tp_sl_mode', 'percent')
                            
                            if mode == 'euro' and strategy == 'day_trading':
                                # EURO-MODUS für DAY TRADING
                                tp_euro = self.settings.get('day_trading_take_profit_euro', 25.0)
                                sl_euro = self.settings.get('day_trading_stop_loss_euro', 15.0)
                                
                                logger.info(f"📊 Verwende Day Trading Settings (EURO-Modus): TP=€{tp_euro}, SL=€{sl_euro}")
                                
                                volume = pos.get('volume', 0.01)
                                
                                if 'BUY' in pos_type:
                                    stop_loss_price = entry_price - (sl_euro / volume)
                                    take_profit_price = entry_price + (tp_euro / volume)
                                else:  # SELL
                                    stop_loss_price = entry_price + (sl_euro / volume)
                                    take_profit_price = entry_price - (tp_euro / volume)
                            elif mode == 'euro':
                                # EURO-MODUS: Feste Euro-Beträge
                                tp_euro = self.settings.get('swing_take_profit_euro', 50.0)
                                sl_euro = self.settings.get('swing_stop_loss_euro', 20.0)
                                
                                logger.info(f"📊 Verwende Swing Trading Settings (EURO-Modus): TP=€{tp_euro}, SL=€{sl_euro}")
                                
                                # Berechne Price basierend auf Euro-Betrag
                                # Volume und Contract Size berücksichtigen
                                volume = pos.get('volume', 0.01)
                                
                                if 'BUY' in pos_type:
                                    stop_loss_price = entry_price - (sl_euro / volume)
                                    take_profit_price = entry_price + (tp_euro / volume)
                                else:  # SELL
                                    stop_loss_price = entry_price + (sl_euro / volume)
                                    take_profit_price = entry_price - (tp_euro / volume)
                            else:
                                # PROZENT-MODUS: Prozentuale Berechnung
                                if strategy == 'day_trading':
                                    tp_percent = self.settings.get('day_trading_take_profit_percent', 2.5)
                                    sl_percent = self.settings.get('day_trading_stop_loss_percent', 1.5)
                                    logger.info(f"📊 Verwende Day Trading Settings (PROZENT-Modus): TP={tp_percent}%, SL={sl_percent}%")
                                elif strategy == 'scalping':
                                    tp_percent = 0.15  # 15 Pips
                                    sl_percent = 0.08  # 8 Pips
                                    logger.info(f"🎯 Verwende SCALPING Settings (PROZENT-Modus): TP={tp_percent}%, SL={sl_percent}%")
                                else:
                                    tp_percent = self.settings.get('swing_take_profit_percent', 4.0)
                                    sl_percent = self.settings.get('swing_stop_loss_percent', 2.0)
                                    logger.info(f"📊 Verwende Swing Trading Settings (PROZENT-Modus): TP={tp_percent}%, SL={sl_percent}%")
                                
                                if 'BUY' in pos_type:
                                    stop_loss_price = entry_price * (1 - sl_percent / 100)
                                    take_profit_price = entry_price * (1 + tp_percent / 100)
                                else:  # SELL
                                    stop_loss_price = entry_price * (1 + sl_percent / 100)
                                    take_profit_price = entry_price * (1 - tp_percent / 100)
                            
                            # V2.3.34: Alle Strategien erkennen
                            valid_strategies = ['swing', 'day_trading', 'scalping', 'mean_reversion', 'momentum', 'breakout', 'grid']
                            default_strategy = strategy if strategy in valid_strategies else 'day_trading'
                            
                            # Speichere in DB - NUR wenn noch nicht vorhanden (insert_one wirft Exception wenn existiert)
                            try:
                                result = await self.db.trade_settings.insert_one({
                                    'trade_id': trade_id,
                                    'stop_loss': stop_loss_price,
                                    'take_profit': take_profit_price,
                                    'strategy': default_strategy,  # HARD-CODED: 'day_trading'
                                    'created_at': datetime.now(timezone.utc).isoformat(),
                                    'entry_price': entry_price,
                                    'platform': platform,
                                    'created_by': 'AI_MONITOR_AUTO'
                                })
                                logger.info(f"✅ Auto-created SL/TP für #{ticket} ({strategy.upper()}): SL={stop_loss_price:.2f}, TP={take_profit_price:.2f}")
                            except Exception as e:
                                logger.error(f"❌ Fehler beim Auto-Create SL/TP: {e}")
                                # Verwende berechnete Werte trotzdem
                        else:
                            # ⚡ V2.3.34: ALLE Strategien aus Settings berechnen!
                            if strategy == 'day_trading':
                                tp_pct = self.settings.get('day_trading_take_profit_percent', 2.5)
                                sl_pct = self.settings.get('day_trading_stop_loss_percent', 1.5)
                            elif strategy == 'swing':
                                tp_pct = self.settings.get('swing_take_profit_percent', 4.0)
                                sl_pct = self.settings.get('swing_stop_loss_percent', 2.0)
                            elif strategy == 'scalping':
                                tp_pct = self.settings.get('scalping_take_profit_percent', 0.5)
                                sl_pct = self.settings.get('scalping_stop_loss_percent', 0.3)
                            elif strategy == 'mean_reversion':
                                tp_pct = self.settings.get('mean_reversion_take_profit_percent', 4.0)
                                sl_pct = self.settings.get('mean_reversion_stop_loss_percent', 2.0)
                            elif strategy == 'momentum':
                                tp_pct = self.settings.get('momentum_take_profit_percent', 5.0)
                                sl_pct = self.settings.get('momentum_stop_loss_percent', 2.5)
                            elif strategy == 'breakout':
                                tp_pct = self.settings.get('breakout_take_profit_percent', 6.0)
                                sl_pct = self.settings.get('breakout_stop_loss_percent', 3.0)
                            elif strategy == 'grid':
                                tp_pct = self.settings.get('grid_tp_per_level_percent', 2.0)
                                sl_pct = self.settings.get('grid_stop_loss_percent', 5.0)
                            else:  # Fallback zu day_trading
                                tp_pct = self.settings.get('day_trading_take_profit_percent', 2.5)
                                sl_pct = self.settings.get('day_trading_stop_loss_percent', 1.5)
                            
                            # Berechne SL/TP basierend auf Entry-Preis und Settings
                            if 'BUY' in pos_type:
                                take_profit_price = entry_price * (1 + tp_pct / 100)
                                stop_loss_price = entry_price * (1 - sl_pct / 100)
                            else:  # SELL
                                take_profit_price = entry_price * (1 - tp_pct / 100)
                                stop_loss_price = entry_price * (1 + sl_pct / 100)
                        
                        logger.debug(f"🤖 KI überwacht {symbol}: Entry={entry_price:.2f}, SL={stop_loss_price:.2f}, TP={take_profit_price:.2f}")

                        # Fallback: Wenn Risk Circuits nicht registriert (z.B. nach Neustart), jetzt nachholen
                        if trade_id not in autonomous_trading.active_risk_circuits:
                            try:
                                # Entry-Time übernehmen, damit 30-Minuten-Checks korrekt sind
                                entry_time_raw = pos.get('time') or (individual_settings.get('opened_at') if individual_settings else None)
                                if entry_time_raw and isinstance(entry_time_raw, datetime):
                                    entry_time_iso = entry_time_raw.isoformat()
                                elif entry_time_raw:
                                    entry_time_iso = str(entry_time_raw)
                                else:
                                    entry_time_iso = None

                                time_exit_minutes = {
                                    'scalping': 30,
                                    'day': 240,
                                    'day_trading': 240,
                                    'swing': 1440,
                                    'swing_trading': 1440,
                                    'momentum': 180,
                                    'breakout': 120,
                                    'mean_reversion': 60,
                                    'grid': 480
                                }.get(strategy, 240)

                                # 🆕 v3.1.18: Lade Peak aus DB falls vorhanden (überlebt Backend-Neustart)
                                db_peak_profit = None
                                db_peak_progress = None
                                try:
                                    existing_settings = await self.db.trade_settings.find_one({'trade_id': trade_id})
                                    if existing_settings:
                                        db_peak_profit = existing_settings.get('peak_profit')
                                        db_peak_progress = existing_settings.get('peak_progress_percent')
                                        if db_peak_profit is not None:
                                            logger.info(f"📈 Peak aus DB geladen für {trade_id}: peak_profit={db_peak_profit}, peak_progress={db_peak_progress}")
                                except Exception as e:
                                    logger.debug(f"Peak-Laden aus DB fehlgeschlagen für {trade_id}: {e}")
                                
                                # Verwende den höheren Wert: aktueller Profit oder gespeicherter Peak
                                effective_initial_profit = profit
                                if db_peak_profit is not None and db_peak_profit > (profit or 0):
                                    effective_initial_profit = db_peak_profit
                                
                                autonomous_trading.register_trade_for_risk_monitoring(
                                    trade_id=trade_id,
                                    entry_price=entry_price,
                                    stop_loss=stop_loss_price,
                                    take_profit=take_profit_price,
                                    strategy=strategy,
                                    time_exit_minutes=time_exit_minutes,
                                    entry_time_override=entry_time_iso,
                                    initial_profit=effective_initial_profit
                                )
                                
                                # Setze auch peak_progress_percent falls aus DB geladen
                                if db_peak_progress is not None:
                                    state = autonomous_trading.active_risk_circuits.get(trade_id)
                                    if state and db_peak_progress > state.peak_progress_percent:
                                        state.peak_progress_percent = db_peak_progress

                                # Sofortige Neubewertung nach Registrierung
                                risk_action = autonomous_trading.check_risk_circuits(
                                    trade_id,
                                    current_price,
                                    current_profit=profit
                                )

                                # Falls Auto-Register sofort eine Aktion auslöst, direkt anwenden
                                if risk_action.get('action') == 'move_sl_breakeven':
                                    new_sl = risk_action['new_sl']
                                    logger.info(f"🔐 BREAKEVEN für #{ticket}: SL → {new_sl:.4f} (Auto-Register)")
                                    await self.db.trade_settings.update_one(
                                        {'trade_id': trade_id},
                                        {'$set': {'stop_loss': new_sl, 'breakeven_active': True}}
                                    )
                                elif risk_action.get('action') == 'profit_drawdown_exit':
                                    logger.warning(f"📉 PROFIT-DRAWDOWN EXIT für #{ticket}: {risk_action['reason']} (Auto-Register)")
                                    try:
                                        close_result = await multi_platform.close_position(platform, ticket)
                                        if close_result:
                                            logger.info(f"✅ Profit-Drawdown Exit erfolgreich: #{ticket}")
                                            autonomous_trading.remove_risk_circuit(trade_id)
                                            autonomous_trading.update_strategy_performance(strategy, is_winner=(profit > 0), profit=profit)
                                            continue
                                    except Exception as e:
                                        logger.error(f"Profit-Drawdown Exit fehlgeschlagen: {e}")
                                elif risk_action.get('action') == 'trailing_stop':
                                    new_sl = risk_action['new_sl']
                                    logger.info(f"🔄 TRAILING STOP für #{ticket}: SL → {new_sl:.4f} (Auto-Register)")
                                    await self.db.trade_settings.update_one(
                                        {'trade_id': trade_id},
                                        {'$set': {'stop_loss': new_sl}}
                                    )
                            except Exception as e:
                                logger.debug(f"Risk Circuit Auto-Register fehlgeschlagen für #{ticket}: {e}")
                        
                        # Prüfe ob SL oder TP erreicht
                        if 'BUY' in pos_type:
                            tp_reached = current_price >= take_profit_price
                            sl_reached = current_price <= stop_loss_price
                        else:  # SELL
                            tp_reached = current_price <= take_profit_price
                            sl_reached = current_price >= stop_loss_price
                        
                        # 🤖 KI-ENTSCHEIDUNG: Position schließen bei SL oder TP
                        should_close = False
                        close_reason = ""
                        
                        if tp_reached:
                            should_close = True
                            close_reason = f"✅ TAKE PROFIT erreicht (Target: {take_profit_price:.2f}, Aktuell: {current_price:.2f})"
                        elif sl_reached:
                            should_close = True
                            close_reason = f"🛑 STOP LOSS erreicht (SL: {stop_loss_price:.2f}, Aktuell: {current_price:.2f})"
                        
                        # Position schließen wenn nötig
                        if should_close:
                            reason = "TAKE PROFIT" if tp_reached else "STOP LOSS"
                            profit_loss = profit if profit else (current_price - entry_price) * quantity if 'BUY' in pos_type else (entry_price - current_price) * quantity
                            
                            logger.info("")
                            logger.info("="*60)
                            logger.info(f"🤖 KI-ÜBERWACHUNG: {reason} ERREICHT!")
                            logger.info("="*60)
                            logger.info(f"📊 Symbol: {symbol} ({pos_type})")
                            logger.info(f"📍 Entry: €{entry_price:.2f}")
                            logger.info(f"📍 Aktuell: €{current_price:.2f}")
                            logger.info(f"🎯 Target: €{take_profit_price if tp_reached else stop_loss_price:.2f}")
                            logger.info(f"💰 P&L: €{profit_loss:.2f}")
                            logger.info("🚀 Aktion: Position wird bei MT5 geschlossen...")
                            logger.info("="*60)
                            
                            # SCHLIESSE POSITION!
                            success = await multi_platform.close_position(platform, str(ticket))
                            
                            if success:
                                logger.info(f"✅ Position {ticket} automatisch geschlossen!")
                                closed_positions += 1
                                
                                # WICHTIG: Speichere geschlossenen Trade in DB für Historie & Statistiken
                                try:
                                    closed_trade = {
                                        "id": f"mt5_{ticket}",
                                        "mt5_ticket": str(ticket),
                                        "commodity": symbol,
                                        "type": "BUY" if 'BUY' in pos_type else "SELL",
                                        "entry_price": entry_price,
                                        "exit_price": current_price,
                                        "quantity": quantity,
                                        "profit_loss": profit,
                                        "status": "CLOSED",
                                        "platform": platform,
                                        "opened_at": opened_at if opened_at else datetime.now(timezone.utc).isoformat(),
                                        "closed_at": datetime.now(timezone.utc).isoformat(),
                                        "close_reason": close_reason,
                                        "closed_by": "AI_BOT"
                                    }
                                    await self.db.trades.insert_one(closed_trade)
                                    logger.info(f"💾 Saved closed trade #{ticket} to DB (P/L: €{profit:.2f})")
                                except Exception as e:
                                    logger.error(f"⚠️ Failed to save closed trade to DB: {e}")
                            else:
                                logger.error(f"❌ Fehler beim Schließen von Position {ticket}")
                        
                except Exception as e:
                    logger.error(f"Fehler bei {platform}: {e}")
            
            logger.info(f"📊 Monitoring abgeschlossen: {total_positions} Positionen überwacht, {closed_positions} geschlossen")
            
        except Exception as e:
            logger.error(f"Fehler beim Monitoring: {e}", exc_info=True)
    
    async def analyze_and_open_trades(self, strategy="day_trading"):
        """KI analysiert Markt und öffnet neue Positionen - DUAL STRATEGY
        
        Args:
            strategy: "swing" für Swing Trading, "day_trading" für Day Trading
        """
        if strategy == "swing":
            strategy_name = "Swing Trading"
        elif strategy == "scalping":
            strategy_name = "Scalping"
        else:
            strategy_name = "Day Trading"
        logger.info(f"🧠 KI analysiert Markt für neue {strategy_name} Möglichkeiten...")
        
        try:
            # Strategie-spezifische Parameter laden
            if strategy == "swing":
                max_positions = self.settings.get('swing_max_positions', 5)
                min_confidence = self.settings.get('swing_min_confidence_score', 0.6) * 100
                analysis_interval = self.settings.get('swing_analysis_interval_seconds', 60)
                last_analysis_dict = self.last_analysis_time_swing
            elif strategy == "scalping":
                # V2.3.36 FIX: Lade max_positions aus Settings statt hardcoded!
                max_positions = self.settings.get('scalping_max_positions', 2)
                min_confidence = self.settings.get('scalping_min_confidence_score', 0.65) * 100
                analysis_interval = 15  # Alle 15 Sekunden analysieren
                last_analysis_dict = getattr(self, 'last_analysis_time_scalping', {})
                if not hasattr(self, 'last_analysis_time_scalping'):
                    self.last_analysis_time_scalping = {}
            else:  # day trading
                max_positions = self.settings.get('day_trading_max_positions', 10)
                min_confidence = self.settings.get('day_trading_min_confidence_score', 0.4) * 100
                analysis_interval = self.settings.get('day_trading_analysis_interval_seconds', 60)
                last_analysis_dict = self.last_analysis_time_day_trading

                # Apply confidence profile modifier (conservative/standard/aggressive)
                profile = self.settings.get('confidence_profile')
                if not profile:
                    mode = self.settings.get('trading_mode', 'neutral')
                    profile = 'aggressive' if mode == 'aggressive' else ('conservative' if mode == 'conservative' else 'standard')
                profile_map = self.settings.get('confidence_profile_map', {'conservative': 1.15, 'standard': 1.0, 'aggressive': 0.85})
                profile_factor = profile_map.get(profile, 1.0)
                # min_confidence is set per-strategy below as decimal*100; we'll apply factor after it's computed
                # store factor to apply later
                min_confidence_profile_factor = profile_factor

                # KORRIGIERT: 20% PRO PLATTFORM für BEIDE Strategien ZUSAMMEN
                combined_max_balance_percent = self.settings.get('combined_max_balance_percent_per_platform', 20.0)
            
            # Prüfe GESAMTE offene Positionen (Swing + Day zusammen)
            all_open_positions = await self.get_all_open_ai_positions()
            total_positions = len(all_open_positions)
            
            # Max Positionen Check (GESAMT, nicht pro Strategie!)
            total_max_positions = self.settings.get('swing_max_positions', 5) + self.settings.get('day_trading_max_positions', 10)
            if total_positions >= total_max_positions:
                logger.warning(f"⚠️  Max GESAMT-Positionen erreicht ({total_positions}/{total_max_positions})")
                return
            
            # Prüfe Positionen für diese spezifische Strategie
            current_positions = await self.get_strategy_positions(strategy)
            if len(current_positions) >= max_positions:
                logger.info(f"ℹ️  {strategy_name}: Max Positionen für diese Strategie erreicht ({len(current_positions)}/{max_positions})")
                return
            
            # Prüfe Max Trades pro Stunde
            max_trades_per_hour = self.settings.get('max_trades_per_hour', 10)
            now = datetime.now()
            one_hour_ago = now - timedelta(hours=1)
            # Entferne alte Trades (älter als 1 Stunde)
            self.trades_this_hour = [t for t in self.trades_this_hour if t > one_hour_ago]
            if len(self.trades_this_hour) >= max_trades_per_hour:
                logger.warning(f"⚠️  {strategy_name}: Max Trades pro Stunde erreicht ({len(self.trades_this_hour)}/{max_trades_per_hour})")
                return
            
            # Prüfe GESAMTE Balance-Auslastung (Swing + Day zusammen) PRO Plattform
            total_balance_usage = await self.calculate_combined_balance_usage_per_platform()
            if total_balance_usage >= combined_max_balance_percent:
                logger.warning(f"⚠️  {strategy_name}: GESAMT Balance-Limit erreicht ({total_balance_usage:.1f}% >= {combined_max_balance_percent}% PRO Plattform)")
                return
            
            # Hole aktivierte Commodities aus Settings
            enabled_commodities = self.settings.get('enabled_commodities', [])
            if not enabled_commodities:
                logger.info("ℹ️  Keine aktivierten Commodities in Settings")
                return
            
            # Analysiere jeden Commodity
            analyzed_count = 0
            skipped_count = 0
            for commodity_id in enabled_commodities:
                # Rate Limiting: Respektiere analysis_interval
                last_check = last_analysis_dict.get(commodity_id)
                time_since_last = (datetime.now() - last_check).seconds if last_check else 999999
                
                if last_check and time_since_last < analysis_interval:
                    skipped_count += 1
                    logger.debug(f"{strategy_name}: {commodity_id} übersprungen (erst vor {time_since_last}s analysiert, Intervall: {analysis_interval}s)")
                    continue
                
                last_analysis_dict[commodity_id] = datetime.now()
                
                # Hole Preishistorie
                price_history = await self.get_price_history(commodity_id)
                if len(price_history) < 20:
                    logger.info(f"ℹ️  {strategy_name}: {commodity_id} - Nicht genug Preisdaten ({len(price_history)}/20)")
                    continue
                
                # Vollständige Marktanalyse - V2.3.36: STRATEGIE-SPEZIFISCH!
                logger.info(f"\n{'='*80}")
                logger.info(f"🔍 STARTE ANALYSE FÜR: {commodity_id} ({strategy_name})")
                logger.info(f"{'='*80}")
                
                # V2.3.36 FIX: Jede Strategie hat eigene Signal-Logik!
                # V2.4.0: Nutze FORTGESCHRITTENE Trading-Logik mit Konfidenz und ATR
                if strategy == "scalping":
                    analysis = await self._analyze_for_scalping_v2(commodity_id, price_history)
                elif strategy == "swing":
                    analysis = await self._analyze_for_swing_v2(commodity_id, price_history)
                elif strategy == "momentum":
                    analysis = await self._analyze_for_momentum_v2(commodity_id, price_history)
                elif strategy == "mean_reversion":
                    analysis = await self._analyze_for_mean_reversion_v2(commodity_id, price_history)
                elif strategy == "breakout":
                    analysis = await self._analyze_for_breakout_v2(commodity_id, price_history)
                elif strategy == "grid":
                    analysis = await self._analyze_for_grid_v2(commodity_id, price_history)
                else:  # day trading (default)
                    analysis = await self._analyze_for_day_trading_v2(commodity_id, price_history)
                
                analyzed_count += 1
                
                signal = analysis.get('signal', 'HOLD')
                confidence = analysis.get('confidence', 0)
                total_score = analysis.get('total_score', 0)
                
                logger.info(f"\n{'='*80}")
                logger.info(f"📊 ANALYSE-ERGEBNIS FÜR {commodity_id}:")
                logger.info(f"   Signal: {signal}")
                logger.info(f"   Konfidenz: {confidence}%")
                logger.info(f"   Total Score: {total_score}")
                # Apply profile factor if available
                try:
                    min_confidence = int(min_confidence * min_confidence_profile_factor)
                except Exception:
                    pass
                logger.info(f"   Min. erforderliche Konfidenz: {min_confidence}%")
                logger.info(f"{'='*80}\n")
                
                # Nur bei hoher Konfidenz handeln
                if signal in ['BUY', 'SELL'] and confidence >= min_confidence:
                    logger.info(f"✅ {strategy_name} Signal akzeptiert: {commodity_id} {signal} (Konfidenz: {confidence}% >= {min_confidence}%)")
                    
                    # VERSCHÄRFT: Prüfe Duplicate Prevention
                    # Prüfe wie viele Trades für dieses Asset bereits offen sind
                    open_trades_for_asset = await self.count_open_positions_for_commodity(commodity_id)
                    # Es darf nur eine Position pro Asset geben, außer die zweite nach Cooldown
                    if open_trades_for_asset >= 2:
                        logger.info(f"⏭️  {commodity_id} übersprungen - bereits {open_trades_for_asset} offene Trades (Max: 2)")
                        continue
                    if open_trades_for_asset == 1:
                        # Prüfe Cooldown für zweite Position
                        cooldown_minutes = 30
                        recent_trade = await self.has_recent_trade_for_commodity(commodity_id, minutes=cooldown_minutes)
                        if recent_trade:
                            logger.info(f"⏭️  {commodity_id} übersprungen - zweite Position nur nach {cooldown_minutes} Minuten erlaubt")
                            continue
                    if open_trades_for_asset == 0:
                        # Es darf nur eine Position eröffnet werden, keine zweite
                        recent_trade = await self.has_recent_trade_for_commodity(commodity_id, minutes=1)
                        if recent_trade:
                            logger.info(f"⏭️  {commodity_id} übersprungen - Position wurde gerade erst eröffnet")
                            continue
                    
                    # Optional: LLM Final Decision
                    if self.llm_chat and self.settings.get('use_llm_confirmation', False):
                        llm_decision = await self.ask_llm_for_decision(commodity_id, analysis)
                        if not llm_decision:
                            logger.info(f"🤖 LLM lehnt Trade ab: {commodity_id}")
                            continue
                    
                    # Trade ausführen mit Strategie-Tag!
                    await self.execute_ai_trade(commodity_id, signal, analysis, strategy=strategy)
                else:
                    if signal != 'HOLD':
                        logger.info(f"ℹ️  {strategy_name}: {commodity_id} {signal} aber Konfidenz zu niedrig ({confidence:.1f}% < {min_confidence:.1f}%)")
            
            logger.info(f"📊 {strategy_name} Analyse: {analyzed_count} analysiert, {skipped_count} übersprungen (Rate Limit)")
            
        except Exception as e:
            logger.error(f"Fehler bei der {strategy_name} KI-Analyse: {e}", exc_info=True)
    
    # =========================================================================
    # V2.3.37: STRATEGIE-SPEZIFISCHE ANALYSE-METHODEN (PROFESSIONELL)
    # Basierend auf bewährten Trading-Strategien
    # =========================================================================
    
    async def _analyze_for_scalping(self, commodity_id: str, price_history: List[Dict]) -> Dict:
        """
        SCALPING-SPEZIFISCHE ANALYSE (1-5 Min Timeframe)
        
        Professionelle Scalping-Signale:
        - Stochastik-Oszillator: Kreuzung im überverkauften Bereich (<20)
        - EMA 9/21 Crossover: Signalisiert Mikrotrend
        - Spread-Check: Nur bei niedrigem Spread handeln
        """
        try:
            prices = [p.get('price', p.get('close', 0)) for p in price_history[-50:]]
            highs = [p.get('high', p.get('price', 0)) for p in price_history[-50:]]
            lows = [p.get('low', p.get('price', 0)) for p in price_history[-50:]]
            
            if len(prices) < 21:
                return {'signal': 'HOLD', 'confidence': 0, 'reason': 'Nicht genug Daten'}
            
            current_price = prices[-1]
            
            # 1. STOCHASTIK-OSZILLATOR (%K und %D)
            stoch_k, stoch_d = self._calculate_stochastic(prices, highs, lows, k_period=14, d_period=3)
            
            # 2. EMA 9/21 CROSSOVER
            ema_9 = self._calculate_ema(prices, 9)
            ema_21 = self._calculate_ema(prices, 21)
            ema_9_prev = self._calculate_ema(prices[:-1], 9) if len(prices) > 10 else ema_9
            ema_21_prev = self._calculate_ema(prices[:-1], 21) if len(prices) > 22 else ema_21
            
            # Crossover Detection
            bullish_crossover = ema_9_prev <= ema_21_prev and ema_9 > ema_21
            bearish_crossover = ema_9_prev >= ema_21_prev and ema_9 < ema_21
            
            # 3. SPREAD-CHECK (simuliert durch Volatilität)
            volatility = self._calculate_volatility(prices[-10:])
            spread_ok = volatility < 0.5  # Nur bei niedriger Volatilität/Spread
            
            # 4. Momentum (schnelle Preisbewegung)
            momentum = ((prices[-1] - prices[-3]) / prices[-3] * 100) if prices[-3] > 0 else 0
            
            # SCALPING SIGNAL LOGIK:
            signal = 'HOLD'
            confidence = 0
            reasons = []
            
            # LONG: Stochastik < 20 (überverkauft) + bullish EMA Crossover
            if stoch_k < 20 and stoch_d < 25:
                if bullish_crossover or (ema_9 > ema_21 and momentum > 0):
                    signal = 'BUY'
                    confidence = 65
                    reasons.append(f"Stochastik überverkauft (K={stoch_k:.1f}, D={stoch_d:.1f})")
                    if bullish_crossover:
                        confidence += 15
                        reasons.append("EMA 9/21 Bullish Crossover")
                    if spread_ok:
                        confidence += 10
                        reasons.append("Niedriger Spread")
            
            # SHORT: Stochastik > 80 (überkauft) + bearish EMA Crossover
            elif stoch_k > 80 and stoch_d > 75:
                if bearish_crossover or (ema_9 < ema_21 and momentum < 0):
                    signal = 'SELL'
                    confidence = 65
                    reasons.append(f"Stochastik überkauft (K={stoch_k:.1f}, D={stoch_d:.1f})")
                    if bearish_crossover:
                        confidence += 15
                        reasons.append("EMA 9/21 Bearish Crossover")
                    if spread_ok:
                        confidence += 10
                        reasons.append("Niedriger Spread")
            
            # Spread-Penalty
            if not spread_ok and signal != 'HOLD':
                confidence -= 20
                reasons.append(f"⚠️ Hoher Spread/Volatilität ({volatility:.2f}%)")
            
            confidence = max(0, min(95, confidence))
            
            logger.info(f"⚡ SCALPING {commodity_id}: Stoch K={stoch_k:.1f}/D={stoch_d:.1f}, EMA9={ema_9:.2f}/21={ema_21:.2f}")
            
            return {
                'signal': signal,
                'confidence': confidence,
                'total_score': confidence,
                'reason': ' | '.join(reasons) if reasons else 'Keine Scalping-Signale',
                'indicators': {
                    'stochastic_k': stoch_k,
                    'stochastic_d': stoch_d,
                    'ema_9': ema_9,
                    'ema_21': ema_21,
                    'ema_crossover': 'bullish' if bullish_crossover else 'bearish' if bearish_crossover else 'none',
                    'momentum': momentum,
                    'spread_ok': spread_ok
                },
                'strategy': 'scalping'
            }
            
        except Exception as e:
            logger.error(f"Scalping analysis error: {e}")
            return {'signal': 'HOLD', 'confidence': 0, 'reason': str(e)}
    
    async def _analyze_for_swing(self, commodity_id: str, price_history: List[Dict]) -> Dict:
        """
        SWING TRADING-SPEZIFISCHE ANALYSE (4 Std / 1 Tag Timeframe)
        
        Professionelle Swing-Signale:
        - Golden Cross: SMA 50 kreuzt SMA 200 nach oben
        - MACD-Histogramm: Wechsel bei Support/Resistance
        - Fibonacci-Retracements: Einstieg bei 61.8% Level
        """
        try:
            prices = [p.get('price', p.get('close', 0)) for p in price_history[-250:]]
            if len(prices) < 200:
                return {'signal': 'HOLD', 'confidence': 0, 'reason': 'Nicht genug Daten für Swing (min 200)'}
            
            current_price = prices[-1]
            
            # 1. SMA 50/200 - GOLDEN CROSS / DEATH CROSS
            sma_50 = self._calculate_sma(prices, 50)
            sma_200 = self._calculate_sma(prices, 200)
            sma_50_prev = self._calculate_sma(prices[:-5], 50)  # Vor 5 Perioden
            sma_200_prev = self._calculate_sma(prices[:-5], 200)
            
            golden_cross = sma_50_prev <= sma_200_prev and sma_50 > sma_200
            death_cross = sma_50_prev >= sma_200_prev and sma_50 < sma_200
            
            # 2. MACD-HISTOGRAMM
            macd_line, signal_line, histogram = self._calculate_macd_full(prices)
            macd_bullish = histogram > 0 and macd_line > signal_line
            macd_bearish = histogram < 0 and macd_line < signal_line
            
            # 3. FIBONACCI RETRACEMENTS
            # Finde Hoch/Tief der letzten 50 Perioden
            recent_high = max(prices[-50:])
            recent_low = min(prices[-50:])
            fib_range = recent_high - recent_low
            
            fib_382 = recent_high - (fib_range * 0.382)
            fib_500 = recent_high - (fib_range * 0.500)
            fib_618 = recent_high - (fib_range * 0.618)
            
            # Preis nahe Fibonacci-Level?
            near_fib_618 = abs(current_price - fib_618) / fib_618 < 0.02 if fib_618 > 0 else False
            near_fib_500 = abs(current_price - fib_500) / fib_500 < 0.02 if fib_500 > 0 else False
            
            # 4. TREND-STRUKTUR (Higher Highs / Lower Lows)
            trend_direction = "UP" if sma_50 > sma_200 else "DOWN"
            
            # SWING SIGNAL LOGIK:
            signal = 'HOLD'
            confidence = 0
            reasons = []
            
            # LONG: Golden Cross ODER SMA50 > SMA200 mit MACD bullish
            if golden_cross:
                signal = 'BUY'
                confidence = 80
                reasons.append("🌟 GOLDEN CROSS: SMA50 kreuzt SMA200 nach oben")
            elif sma_50 > sma_200 and macd_bullish:
                signal = 'BUY'
                confidence = 60
                reasons.append("SMA50 > SMA200 (Aufwärtstrend)")
                reasons.append("MACD bullish")
                
                # Bonus: Fibonacci-Level
                if near_fib_618 or near_fib_500:
                    confidence += 15
                    reasons.append(f"Preis bei Fibonacci-Retracement")
            
            # SHORT: Death Cross ODER SMA50 < SMA200 mit MACD bearish
            elif death_cross:
                signal = 'SELL'
                confidence = 80
                reasons.append("💀 DEATH CROSS: SMA50 kreuzt SMA200 nach unten")
            elif sma_50 < sma_200 and macd_bearish:
                signal = 'SELL'
                confidence = 60
                reasons.append("SMA50 < SMA200 (Abwärtstrend)")
                reasons.append("MACD bearish")
            
            confidence = max(0, min(90, confidence))
            
            logger.info(f"📈 SWING {commodity_id}: SMA50={sma_50:.2f}, SMA200={sma_200:.2f}, MACD={histogram:.2f}")
            
            return {
                'signal': signal,
                'confidence': confidence,
                'total_score': confidence,
                'reason': ' | '.join(reasons) if reasons else 'Keine Swing-Signale',
                'indicators': {
                    'sma_50': sma_50,
                    'sma_200': sma_200,
                    'golden_cross': golden_cross,
                    'death_cross': death_cross,
                    'macd_histogram': histogram,
                    'macd_bullish': macd_bullish,
                    'fib_618': fib_618,
                    'fib_500': fib_500,
                    'trend': trend_direction
                },
                'strategy': 'swing'
            }
            
        except Exception as e:
            logger.error(f"Swing analysis error: {e}")
            return {'signal': 'HOLD', 'confidence': 0, 'reason': str(e)}
    
    async def _analyze_for_day_trading(self, commodity_id: str, price_history: List[Dict]) -> Dict:
        """
        DAY TRADING-SPEZIFISCHE ANALYSE (5 Min / 15 Min / 1 Std Timeframe)
        
        Professionelle Day-Trading-Signale:
        - VWAP-Rebound: Preis prallt vom VWAP ab
        - RSI-Divergenz: Preis macht neues Hoch, RSI aber nicht
        - Open Range Breakout: Ausbruch aus den ersten 30-60 Min
        """
        try:
            prices = [p.get('price', p.get('close', 0)) for p in price_history[-100:]]
            volumes = [p.get('volume', 1) for p in price_history[-100:]]
            highs = [p.get('high', p.get('price', 0)) for p in price_history[-100:]]
            lows = [p.get('low', p.get('price', 0)) for p in price_history[-100:]]
            
            if len(prices) < 30:
                return {'signal': 'HOLD', 'confidence': 0, 'reason': 'Nicht genug Daten'}
            
            current_price = prices[-1]
            
            # 1. VWAP (Volume Weighted Average Price)
            vwap = self._calculate_vwap(prices, volumes)
            price_vs_vwap = (current_price - vwap) / vwap * 100 if vwap > 0 else 0
            
            # VWAP-Rebound: Preis nähert sich VWAP und prallt ab
            near_vwap = abs(price_vs_vwap) < 0.5  # Innerhalb 0.5% vom VWAP
            
            # 2. RSI mit DIVERGENZ-Check
            rsi = self._calculate_rsi(prices, period=14)
            rsi_prev = self._calculate_rsi(prices[:-10], period=14) if len(prices) > 24 else rsi
            
            # Bullish Divergenz: Preis macht tieferes Tief, RSI macht höheres Tief
            price_lower_low = prices[-1] < min(prices[-20:-10]) if len(prices) > 20 else False
            rsi_higher_low = rsi > rsi_prev
            bullish_divergence = price_lower_low and rsi_higher_low and rsi < 40
            
            # Bearish Divergenz: Preis macht höheres Hoch, RSI macht tieferes Hoch
            price_higher_high = prices[-1] > max(prices[-20:-10]) if len(prices) > 20 else False
            rsi_lower_high = rsi < rsi_prev
            bearish_divergence = price_higher_high and rsi_lower_high and rsi > 60
            
            # 3. OPEN RANGE BREAKOUT (simuliert: Hoch/Tief der ersten Perioden)
            open_range_high = max(prices[:10])  # "Morgen"-Range
            open_range_low = min(prices[:10])
            breakout_up = current_price > open_range_high * 1.005  # 0.5% über Range
            breakout_down = current_price < open_range_low * 0.995  # 0.5% unter Range
            
            # 4. VOLUMEN-Analyse (Morgensvolumen vs. aktuell)
            avg_volume = sum(volumes) / len(volumes) if volumes else 1
            current_volume = volumes[-1] if volumes else 1
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            high_volume = volume_ratio > 1.5
            
            # DAY TRADING SIGNAL LOGIK:
            signal = 'HOLD'
            confidence = 0
            reasons = []
            
            # LONG-Signale
            if bullish_divergence:
                signal = 'BUY'
                confidence = 70
                reasons.append("📊 Bullish RSI-Divergenz")
            elif near_vwap and current_price > vwap and rsi < 50:
                signal = 'BUY'
                confidence = 60
                reasons.append(f"VWAP-Rebound (Preis +{price_vs_vwap:.2f}% über VWAP)")
            elif breakout_up and high_volume:
                signal = 'BUY'
                confidence = 65
                reasons.append("Open Range Breakout nach oben")
                reasons.append(f"Volumen bestätigt ({volume_ratio:.1f}x)")
            
            # SHORT-Signale
            elif bearish_divergence:
                signal = 'SELL'
                confidence = 70
                reasons.append("📊 Bearish RSI-Divergenz")
            elif near_vwap and current_price < vwap and rsi > 50:
                signal = 'SELL'
                confidence = 60
                reasons.append(f"VWAP-Rebound (Preis {price_vs_vwap:.2f}% unter VWAP)")
            elif breakout_down and high_volume:
                signal = 'SELL'
                confidence = 65
                reasons.append("Open Range Breakout nach unten")
                reasons.append(f"Volumen bestätigt ({volume_ratio:.1f}x)")
            
            # Volumen-Bonus
            if signal != 'HOLD' and high_volume:
                confidence += 10
                if "Volumen" not in str(reasons):
                    reasons.append(f"Starkes Volumen ({volume_ratio:.1f}x)")
            
            confidence = max(0, min(90, confidence))
            
            logger.info(f"📊 DAY {commodity_id}: VWAP={vwap:.2f}, RSI={rsi:.1f}, Vol={volume_ratio:.1f}x")
            
            return {
                'signal': signal,
                'confidence': confidence,
                'total_score': confidence,
                'reason': ' | '.join(reasons) if reasons else 'Keine Day-Trading-Signale',
                'indicators': {
                    'vwap': vwap,
                    'price_vs_vwap': price_vs_vwap,
                    'rsi': rsi,
                    'bullish_divergence': bullish_divergence,
                    'bearish_divergence': bearish_divergence,
                    'open_range_high': open_range_high,
                    'open_range_low': open_range_low,
                    'breakout': 'up' if breakout_up else 'down' if breakout_down else 'none',
                    'volume_ratio': volume_ratio
                },
                'strategy': 'day_trading'
            }
            
        except Exception as e:
            logger.error(f"Day trading analysis error: {e}")
            return {'signal': 'HOLD', 'confidence': 0, 'reason': str(e)}
    
    # =========================================================================
    # HILFS-METHODEN FÜR TECHNISCHE INDIKATOREN (ERWEITERT)
    # =========================================================================
    
    def _calculate_stochastic(self, prices: List[float], highs: List[float], lows: List[float], 
                              k_period: int = 14, d_period: int = 3) -> tuple:
        """Berechnet Stochastik-Oszillator (%K und %D)"""
        if len(prices) < k_period:
            return 50.0, 50.0
        
        # %K = (Current Close - Lowest Low) / (Highest High - Lowest Low) * 100
        highest_high = max(highs[-k_period:]) if highs else max(prices[-k_period:])
        lowest_low = min(lows[-k_period:]) if lows else min(prices[-k_period:])
        
        if highest_high == lowest_low:
            stoch_k = 50.0
        else:
            stoch_k = ((prices[-1] - lowest_low) / (highest_high - lowest_low)) * 100
        
        # %D = SMA von %K (vereinfacht)
        stoch_d = stoch_k * 0.9  # Vereinfachte Glättung
        
        return stoch_k, stoch_d
    
    def _calculate_sma(self, prices: List[float], period: int) -> float:
        """Berechnet Simple Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        return sum(prices[-period:]) / period
    
    def _calculate_vwap(self, prices: List[float], volumes: List[float]) -> float:
        """Berechnet Volume Weighted Average Price"""
        if not prices or not volumes or len(prices) != len(volumes):
            return prices[-1] if prices else 0
        
        total_pv = sum(p * v for p, v in zip(prices, volumes))
        total_volume = sum(volumes)
        
        if total_volume == 0:
            return prices[-1]
        
        return total_pv / total_volume
    
    def _calculate_macd_full(self, prices: List[float]) -> tuple:
        """Berechnet MACD Line, Signal Line und Histogram"""
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        macd_line = ema_12 - ema_26
        
        # Signal Line (EMA 9 der MACD Line - vereinfacht)
        # Für echte Berechnung bräuchten wir MACD-History
        signal_line = macd_line * 0.85  # Vereinfachte Glättung
        
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Berechnet RSI"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]
        
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Berechnet EMA"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period  # SMA als Start
        
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2.0) -> tuple:
        """Berechnet Bollinger Bands"""
        if len(prices) < period:
            avg = prices[-1] if prices else 0
            return avg * 1.02, avg, avg * 0.98
        
        recent_prices = prices[-period:]
        middle = sum(recent_prices) / period
        
        variance = sum((p - middle) ** 2 for p in recent_prices) / period
        std = variance ** 0.5
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return upper, middle, lower
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Berechnet prozentuale Volatilität"""
        if len(prices) < 2:
            return 0.0
        
        returns = [(prices[i] - prices[i-1]) / prices[i-1] * 100 for i in range(1, len(prices)) if prices[i-1] > 0]
        if not returns:
            return 0.0
        
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        return variance ** 0.5
    
    def _calculate_atr(self, prices: List[float], highs: List[float], lows: List[float], period: int = 14) -> float:
        """Berechnet Average True Range"""
        if len(prices) < period + 1:
            return 0.0
        
        true_ranges = []
        for i in range(1, len(prices)):
            high = highs[i] if i < len(highs) else prices[i]
            low = lows[i] if i < len(lows) else prices[i]
            prev_close = prices[i-1]
            
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            true_ranges.append(tr)
        
        return sum(true_ranges[-period:]) / period if true_ranges else 0.0
    
    def _calculate_adx(self, prices: List[float], highs: List[float], lows: List[float], period: int = 14) -> float:
        """Berechnet ADX (Average Directional Index)"""
        # Vereinfachte ADX-Berechnung basierend auf Trend-Stärke
        if len(prices) < period:
            return 25.0  # Neutraler Wert
        
        # Berechne Trend-Stärke über price changes
        changes = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        avg_change = sum(changes[-period:]) / period if changes else 0
        price_range = max(prices[-period:]) - min(prices[-period:])
        
        if price_range == 0:
            return 10.0  # Kein Trend
        
        # ADX-ähnlicher Wert: Je größer die durchschnittliche Änderung relativ zur Range, desto stärker der Trend
        adx_like = (avg_change / price_range) * 100 * 2
        return min(100, max(0, adx_like))
    
    async def get_price_history(self, commodity_id: str, days: int = 7) -> List[Dict]:
        """Hole Preishistorie für technische Analyse - V2.4.0: SQLite kompatibel"""
        try:
            from datetime import datetime, timedelta
            import database as db_module
            
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_str = cutoff_date.isoformat()
            
            # V2.4.0: SQLite-kompatible Abfrage
            history = []
            try:
                # Versuche über das database module
                history = await db_module.market_data_history.find(
                    commodity_id=commodity_id,
                    timestamp_gte=cutoff_str
                )
            except Exception as e:
                logger.debug(f"SQLite query failed, trying fallback: {e}")
                
                # Fallback: Nutze self.market_data (in-memory Cache)
                if commodity_id in self.market_data:
                    cached = self.market_data[commodity_id]
                    if isinstance(cached, dict) and 'price_history' in cached:
                        history = cached['price_history']
                    elif isinstance(cached, list):
                        history = cached
            
            if not history:
                # V2.4.0: Wenn keine Historie, versuche von MetaAPI Candles zu holen
                try:
                    from multi_platform_connector import multi_platform
                    import commodity_processor
                    
                    commodity = commodity_processor.COMMODITIES.get(commodity_id)
                    if commodity:
                        symbol = commodity.get('mt5_libertex_symbol') or commodity.get('mt5_icmarkets_symbol')
                        if symbol:
                            # Hole aktuelle Preisdaten von MetaAPI
                            for platform in self.settings.get('active_platforms', []):
                                try:
                                    connector = multi_platform.platforms.get(platform, {}).get('connector')
                                    if connector:
                                        price_data = await connector.get_symbol_price(symbol)
                                        if price_data:
                                            current_price = price_data.get('bid', 0) or price_data.get('ask', 0)
                                            if current_price > 0:
                                                # Erstelle minimale Historie für Analyse
                                                history = [{'price': current_price, 'high': current_price * 1.001, 'low': current_price * 0.999}] * 100
                                                logger.info(f"📊 Erstelle Pseudo-Historie für {commodity_id} aus Live-Preis: {current_price}")
                                                break
                                except:
                                    continue
                except Exception as e:
                    logger.debug(f"MetaAPI fallback failed: {e}")
            
            if not history:
                logger.warning(f"Keine Preishistorie für {commodity_id}")
                return []
            
            # Konvertiere zu Format für Indikatoren
            price_data = []
            for item in history:
                if isinstance(item, dict):
                    price_data.append({
                        'timestamp': item.get('timestamp'),
                        'price': item.get('price', item.get('close', 0)),
                        'close': item.get('price', item.get('close', 0)),
                        'high': item.get('high', item.get('price', item.get('close', 0))),
                        'low': item.get('low', item.get('price', item.get('close', 0))),
                        'volume': item.get('volume', 1000)
                    })
                elif isinstance(item, (int, float)):
                    price_data.append({
                        'price': float(item),
                        'close': float(item),
                        'high': float(item) * 1.001,
                        'low': float(item) * 0.999,
                        'volume': 1000
                    })
            
            return price_data
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Preishistorie: {e}")
            return []
    
    
    async def get_strategy_positions(self, strategy: str) -> List[Dict]:
        """Hole alle offenen Positionen für eine bestimmte Strategie
        
        WICHTIG: Wir nutzen "live-from-broker" Architektur:
        - Offene Trades kommen vom Broker (multi_platform), nicht aus der DB
        - Strategy-Info steht in trade_settings Collection
        
        VERBESSERUNG: Wenn ein Trade KEINE Strategy hat, wird er als "swing" gezählt (konservativ)
        """
        try:
            from multi_platform_connector import multi_platform
            
            # Hole ALLE offenen Positionen vom Broker
            all_open_positions = []
            for platform in self.settings.get('active_platforms', []):
                try:
                    positions = await multi_platform.get_open_positions(platform)
                    if positions:
                        for pos in positions:
                            pos['platform'] = platform
                            all_open_positions.append(pos)
                except Exception as e:
                    logger.warning(f"Fehler beim Holen von Positionen von {platform}: {e}")
                    continue
            
            logger.info(f"📊 Gefunden: {len(all_open_positions)} offene Positionen gesamt")
            
            # Filtere nach Strategie aus trade_settings
            strategy_positions = []
            for pos in all_open_positions:
                ticket = pos.get('ticket') or pos.get('id')
                if not ticket:
                    continue
                
                # Hole strategy aus trade_settings
                trade_id = f"mt5_{ticket}"
                trade_setting = await self.db.trade_settings.find_one(
                    {"trade_id": trade_id}, 
                    {"_id": 0, "strategy": 1}
                )
                
                # WICHTIG: Wenn KEINE Strategy gesetzt ist, zähle als "day" (Default für unbekannte Trades)
                # Das verhindert, dass Trades ohne Strategy das Limit umgehen
                trade_strategy = trade_setting.get('strategy', 'day') if trade_setting else 'day'
                
                if trade_strategy == strategy:
                    strategy_positions.append(pos)
                    logger.debug(f"  ✓ #{ticket}: {pos.get('symbol')} → {strategy}")
            
            logger.info(f"📊 {len(strategy_positions)} davon sind {strategy.upper()} Trades")
            return strategy_positions
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der {strategy} Positionen: {e}")
            return []
    
    async def has_open_position_for_commodity(self, commodity_id: str, strategy: str) -> bool:
        """Prüft ob bereits eine offene Position für diesen Rohstoff existiert
        
        Args:
            commodity_id: Der Rohstoff (z.B. "GOLD", "WTI_CRUDE")
            strategy: Die Strategie ("swing" oder "day")
        
        Returns:
            True wenn bereits ein Trade offen ist, False sonst
        """
        try:
            from multi_platform_connector import multi_platform
            import commodity_processor
            
            # Symbol-Mapping: Unsere Commodity IDs → MT5 Symbole
            commodity = commodity_processor.COMMODITIES.get(commodity_id)
            if not commodity:
                return False
            
            # Mögliche MT5-Symbole für diesen Rohstoff
            possible_symbols = set()
            if commodity.get('mt5_libertex_symbol'):
                possible_symbols.add(commodity.get('mt5_libertex_symbol'))
            if commodity.get('mt5_icmarkets_symbol'):
                possible_symbols.add(commodity.get('mt5_icmarkets_symbol'))
            
            if not possible_symbols:
                return False
            
            # Hole ALLE offenen Positionen von allen aktiven Plattformen
            for platform in self.settings.get('active_platforms', []):
                try:
                    positions = await multi_platform.get_open_positions(platform)
                    
                    for pos in positions:
                        mt5_symbol = pos.get('symbol', '')
                        ticket = pos.get('ticket') or pos.get('id')
                        
                        # Prüfe ob Symbol übereinstimmt
                        if mt5_symbol in possible_symbols:
                            # Prüfe ob gleiche Strategie (falls trade_settings existiert)
                            trade_id = f"mt5_{ticket}"
                            trade_setting = await self.db.trade_settings.find_one(
                                {"trade_id": trade_id}, 
                                {"_id": 0, "strategy": 1}
                            )
                            
                            # Wenn keine Settings existieren ODER gleiche Strategy
                            if not trade_setting or trade_setting.get('strategy') == strategy:
                                logger.info(f"🔍 Gefunden: {commodity_id} ({mt5_symbol}) bereits offen auf {platform} (Ticket #{ticket}, Strategy: {trade_setting.get('strategy') if trade_setting else 'unknown'})")
                                return True
                    
                except Exception as e:
                    logger.warning(f"Fehler beim Prüfen von {platform}: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Fehler bei has_open_position_for_commodity: {e}")
            return False  # Im Fehlerfall erlauben wir den Trade (fail-safe)
    
    async def calculate_combined_balance_usage_per_platform(self) -> float:
        """KORRIGIERT: Berechne kombinierte Balance-Auslastung (Swing + Day) PRO Plattform
        
        Returns:
            Höchste Auslastung über alle aktiven Plattformen in Prozent
        """
        try:
            from multi_platform_connector import multi_platform
            
            max_usage_percent = 0.0
            
            # Prüfe jede aktive Plattform separat (inkl. Real Account)
            for platform in ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO', 'MT5_LIBERTEX_REAL']:
                if platform not in self.settings.get('active_platforms', []):
                    continue
                
                # Hole Balance dieser Plattform
                account_info = await multi_platform.get_account_info(platform)
                if not account_info:
                    continue
                
                platform_balance = account_info.get('balance', 0)
                if platform_balance <= 0:
                    continue
                
                # KORRIGIERT: Verwende MARGIN vom Account Info statt Nominalwert
                # Bei CFD/Forex mit Hebel ist Margin das tatsächlich genutzte Kapital
                used_margin = account_info.get('margin', 0)
                
                # Prozent dieser Plattform-Balance
                usage_percent = (used_margin / platform_balance) * 100
                
                logger.debug(f"{platform}: {usage_percent:.1f}% genutzt (Margin: €{used_margin:.2f} von Balance: €{platform_balance:.2f})")
                
                # Höchste Auslastung merken
                if usage_percent > max_usage_percent:
                    max_usage_percent = usage_percent
            
            return min(max_usage_percent, 100.0)
            
        except Exception as e:
            logger.error(f"Fehler bei kombinierten Balance-Berechnung: {e}")
            return 0.0
    
    async def close_expired_day_trades(self):
        """Schließe Day-Trading-Positionen die zu lange offen sind"""
        try:
            max_hold_time = self.settings.get('day_position_hold_time_hours', 2)
            cutoff_time = datetime.now() - timedelta(hours=max_hold_time)
            
            # Hole alle Day-Trading-Positionen
            day_trading_positions = await self.get_strategy_positions("day_trading")
            
            closed_count = 0
            for pos in day_trading_positions:
                opened_at = pos.get('opened_at')
                if not opened_at:
                    continue
                
                # Prüfe Alter
                if opened_at < cutoff_time:
                    ticket = pos.get('mt5_ticket')
                    platform = pos.get('platform')
                    
                    if ticket and platform:
                        from multi_platform_connector import multi_platform
                        
                        logger.info(f"⏰ Schließe abgelaufenen Day-Trading-Trade: {pos.get('commodity_id')} (Ticket: {ticket}, Alter: {(datetime.now() - opened_at).seconds // 60} Min)")
                        
                        success = await multi_platform.close_position(platform, str(ticket))
                        if success:
                            closed_count += 1
                            
                            # Update DB
                            await self.db.trades.update_one(
                                {"mt5_ticket": str(ticket)},
                                {"$set": {
                                    "status": "CLOSED",
                                    "closed_at": datetime.now(),
                                    "close_reason": f"Time-Based Exit: Max {max_hold_time}h erreicht",
                                    "closed_by": "AI_BOT_TIMER"
                                }}
                            )
            
            if closed_count > 0:
                logger.info(f"✅ {closed_count} abgelaufene Day-Trades geschlossen")
                
        except Exception as e:
            logger.error(f"Fehler beim Schließen abgelaufener Day-Trading-Trades: {e}")
    
    async def close_expired_swing_trades(self):
        """Schließe Swing-Trading-Positionen die zu lange offen sind"""
        try:
            max_hold_time = self.settings.get('swing_position_hold_time_hours', 168)  # Default 7 Tage
            cutoff_time = datetime.now() - timedelta(hours=max_hold_time)
            
            # Hole alle Swing-Trading-Positionen
            swing_positions = await self.get_strategy_positions("swing")
            
            closed_count = 0
            for pos in swing_positions:
                opened_at = pos.get('opened_at')
                if not opened_at:
                    continue
                
                # Prüfe Alter
                if opened_at < cutoff_time:
                    ticket = pos.get('mt5_ticket')
                    platform = pos.get('platform')
                    
                    if ticket and platform:
                        from multi_platform_connector import multi_platform
                        
                        age_hours = (datetime.now() - opened_at).total_seconds() / 3600
                        logger.info(f"⏰ Schließe abgelaufenen Swing-Trade: {pos.get('commodity_id')} (Ticket: {ticket}, Alter: {age_hours:.1f}h)")
                        
                        success = await multi_platform.close_position(platform, str(ticket))
                        if success:
                            closed_count += 1
                            
                            # Update DB
                            await self.db.trades.update_one(
                                {"mt5_ticket": str(ticket)},
                                {"$set": {
                                    "status": "CLOSED",
                                    "closed_at": datetime.now(),
                                    "close_reason": f"Time-Based Exit: Max {max_hold_time}h erreicht",
                                    "closed_by": "AI_BOT_TIMER"
                                }}
                            )
            
            if closed_count > 0:
                logger.info(f"✅ {closed_count} abgelaufene Swing-Trades geschlossen")
                
        except Exception as e:
            logger.error(f"Fehler beim Schließen abgelaufener Swing-Trades: {e}")

    async def close_expired_scalping_trades(self):
        """Schließe abgelaufene Scalping-Trades (max 5 Minuten Haltezeit)"""
        try:
            max_hold_time_minutes = 5  # 5 Minuten max für Scalping
            cutoff_time = datetime.now() - timedelta(minutes=max_hold_time_minutes)
            
            # Hole alle Scalping-Positionen
            scalping_positions = await self.get_strategy_positions("scalping")
            
            closed_count = 0
            for pos in scalping_positions:
                opened_at = pos.get('opened_at')
                if not opened_at:
                    continue
                
                # Prüfe Alter
                if opened_at < cutoff_time:
                    ticket = pos.get('mt5_ticket')
                    platform = pos.get('platform')
                    
                    if ticket and platform:
                        from multi_platform_connector import multi_platform
                        
                        age_minutes = (datetime.now() - opened_at).total_seconds() / 60
                        logger.info(f"🎯 Schließe abgelaufenen SCALPING-Trade: {pos.get('commodity_id')} (Ticket: {ticket}, Alter: {age_minutes:.1f}min)")
                        
                        success = await multi_platform.close_position(platform, str(ticket))
                        if success:
                            closed_count += 1
                            
                            # Update DB
                            await self.db.trades.update_one(
                                {"mt5_ticket": str(ticket)},
                                {"$set": {
                                    "status": "CLOSED",
                                    "closed_at": datetime.now(),
                                    "close_reason": f"Scalping Time-Based Exit: Max {max_hold_time_minutes}min erreicht",
                                    "closed_by": "AI_BOT_SCALPING_TIMER"
                                }}
                            )
            
            if closed_count > 0:
                logger.info(f"🎯 {closed_count} abgelaufene SCALPING-Trades geschlossen")
                
        except Exception as e:
            logger.error(f"Fehler beim Schließen abgelaufener Scalping-Trades: {e}")

    async def calculate_portfolio_risk(self) -> float:
        """Berechne aktuelles Portfolio-Risiko in Prozent"""
        try:
            from multi_platform_connector import multi_platform
            
            # Hole alle offenen Positionen (inkl. Real Account)
            all_positions = []
            for platform in ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO', 'MT5_LIBERTEX_REAL']:
                if platform in self.settings.get('active_platforms', []):
                    positions = await multi_platform.get_open_positions(platform)
                    all_positions.extend(positions)
            
            if not all_positions:
                return 0.0
            
            # Hole Account-Balance
            total_balance = 0.0
            for platform in ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO', 'MT5_LIBERTEX_REAL']:
                if platform in self.settings.get('active_platforms', []):
                    account_info = await multi_platform.get_account_info(platform)
                    if account_info:
                        total_balance += account_info.get('balance', 0)
            
            if total_balance <= 0:
                return 100.0  # Safety: Wenn keine Balance, maximales Risiko
            
            # Berechne offenes Risiko (basierend auf Stop Loss)
            total_risk = 0.0
            for pos in all_positions:
                volume = pos.get('volume', 0)
                entry_price = pos.get('openPrice') or pos.get('price_open') or pos.get('entry_price', 0)
                stop_loss = pos.get('stopLoss') or pos.get('sl', 0)
                
                if entry_price and stop_loss:
                    # Risiko = Differenz * Volume
                    risk_per_unit = abs(entry_price - stop_loss)
                    position_risk = risk_per_unit * volume
                    total_risk += position_risk
            
            # Risiko in Prozent der Balance
            risk_percent = (total_risk / total_balance) * 100
            
            return min(risk_percent, 100.0)
            
        except Exception as e:
            logger.error(f"Fehler bei Portfolio-Risiko-Berechnung: {e}")
            return 0.0
    
    async def ask_llm_for_decision(self, commodity_id: str, analysis: Dict) -> bool:
        """Frage LLM ob Trade ausgeführt werden soll - MIT VOLLSTÄNDIGEM KONTEXT"""
        try:
            if not self.llm_chat:
                return True  # Default: Ja, wenn LLM nicht verfügbar
            
            # Extrahiere alle verfügbaren Daten
            indicators = analysis.get('indicators', {})
            news = analysis.get('news', {})
            economic = analysis.get('economic_events', {})
            market_sentiment = analysis.get('market_sentiment', {})
            sr_levels = analysis.get('support_resistance', {})
            
            prompt = f"""
Du bist ein professioneller Commodities Trading Analyst. Analysiere folgende KOMPLETTE Marktlage für {commodity_id}:

═══════════════════════════════════════════════
TRADING SIGNAL ANFRAGE
═══════════════════════════════════════════════

📊 SIGNAL-ZUSAMMENFASSUNG:
• Signal: {analysis.get('signal')}
• Konfidenz: {analysis.get('confidence')}%
• Multi-Strategie Score: {analysis.get('total_score')}

📈 TECHNISCHE INDIKATOREN:
• RSI: {indicators.get('rsi', 0):.1f} (Überverkauft <30, Überkauft >70)
• MACD: {indicators.get('macd_diff', 0):.3f} (Positiv=Bullish, Negativ=Bearish)
• Aktueller Preis: ${indicators.get('current_price', 0):.2f}
• SMA 20: ${indicators.get('sma_20', 0):.2f}
• SMA 50: ${indicators.get('sma_50', 0):.2f}
• EMA 12: ${indicators.get('ema_12', 0):.2f}
• Bollinger Bands: ${indicators.get('bb_lower', 0):.2f} - ${indicators.get('bb_upper', 0):.2f}
• ATR (Volatilität): {indicators.get('atr', 0):.2f}
• Stochastic: {indicators.get('stoch_k', 0):.1f}

📰 NEWS & SENTIMENT:
• News-Sentiment: {news.get('sentiment', 'neutral')}
• Sentiment Score: {news.get('score', 0):.2f}
• Anzahl Artikel: {news.get('articles', 0)}
• Quelle: {news.get('source', 'none')}

📅 ECONOMIC CALENDAR (heute):
• Gesamt Events: {economic.get('total_events', 0)}
• High-Impact Events: {economic.get('high_impact', 0)}
{"• ⚠️ WICHTIGE EVENTS HEUTE - Vorsicht!" if economic.get('high_impact', 0) > 0 else "• Keine kritischen Events"}

🌍 MARKT-STIMMUNG:
• Sentiment: {market_sentiment.get('sentiment', 'neutral')}
• SPY RSI: {market_sentiment.get('rsi', 50):.1f}

📊 SUPPORT & RESISTANCE:
• Support Level: ${sr_levels.get('support', 0):.2f}
• Resistance Level: ${sr_levels.get('resistance', 0):.2f}
• Aktueller Preis: ${sr_levels.get('current_price', 0):.2f}

🎯 STRATEGIE-SIGNALE:
{chr(10).join(['• ' + sig for sig in analysis.get('signals', [])])}

═══════════════════════════════════════════════
DEINE AUFGABE
═══════════════════════════════════════════════

Analysiere ALLE oben genannten Faktoren und entscheide:
• Sind die technischen Signale stark genug?
• Unterstützt das News-Sentiment den Trade?
• Gibt es Economic Events die dagegen sprechen?
• Ist die Markt-Stimmung günstig?
• Sind wir nahe Support/Resistance Levels?

WICHTIG:
• Nur bei SEHR STARKEN und KLAREN Signalen JA sagen
• Bei Zweifeln oder gemischten Signalen NEIN sagen
• Economic Events mit hohem Impact = eher NEIN
• Konfidenz unter 70% = genau prüfen

Antworte NUR mit: JA oder NEIN
(Optional: kurze Begründung in 1 Satz)
"""
            
            from emergentintegrations.llm.chat import UserMessage
            response_obj = await self.llm_chat.send_message(UserMessage(text=prompt))
            response = response_obj.text if hasattr(response_obj, 'text') else str(response_obj)
            
            decision = 'ja' in response.lower() or 'yes' in response.lower()
            logger.info(f"🤖 LLM Entscheidung für {commodity_id}: {'✅ JA' if decision else '❌ NEIN'}")
            logger.info(f"   LLM Begründung: {response[:200]}")
            
            return decision
            
        except Exception as e:
            logger.error(f"LLM Entscheidung fehlgeschlagen: {e}")
            return True  # Default: Ja bei Fehler
    
    async def execute_ai_trade(self, commodity_id: str, direction: str, analysis: Dict, strategy="day_trading"):
        """Führe Trade aus mit Risk Management - MULTI STRATEGY AWARE
        
        Args:
            strategy: "swing", "day_trading", "scalping", "mean_reversion", "momentum", "breakout", "grid"
        """
        lock_key = None
        lock_owner = None
        lock_acquired = False
        db_reserved = False
        db_owner = None
        platform = None

        try:
            from multi_platform_connector import multi_platform
            import commodity_processor
            
            # 🆕 v2.3.29: Erweitert um neue Strategien
            strategy_names = {
                "swing": "📈 Swing Trading",
                "day": "⚡ Day Trading",
                "scalping": "⚡🎯 Scalping",
                "mean_reversion": "📊 Mean Reversion",
                "momentum": "🚀 Momentum Trading",
                "breakout": "💥 Breakout Trading",
                "grid": "🔹 Grid Trading"
            }
            strategy_name = strategy_names.get(strategy, "Day Trading")
            logger.info(f"🚀 Führe {strategy_name} Trade aus: {commodity_id} {direction}")
            
            # Distributed Lock (SQLite) pro Asset, um Parallel-Opens über Prozesse zu verhindern
            try:
                lock_owner = str(uuid.uuid4())
                lock_key = f"trade_open:{commodity_id}"
                lock_acquired = await db_module.acquire_lock(lock_key, lock_owner, ttl_seconds=180)
                if not lock_acquired:
                    logger.info(f"⏭️  {commodity_id} übersprungen - verteilte Sperre aktiv")
                    return
            except Exception as e:
                logger.warning(f"⚠️ Distributed Lock konnte nicht gesetzt werden für {commodity_id}: {e}")
                return

            # NOTE: DB reservation is now attempted AFTER the platform is selected so that
            # reservations are per-(platform,commodity) and prevent duplicates per account.
            # Reservation will be attempted later (after platform selection)
            # to ensure reservations are scoped to the specific platform/account.

            # Acquire per-commodity lock to prevent simultaneous openings (in-process)
            # Protect lock creation with a meta-lock to avoid race where two tasks create different locks
            if not hasattr(self, '_commodity_locks_meta_lock'):
                self._commodity_locks_meta_lock = asyncio.Lock()
            async with self._commodity_locks_meta_lock:
                lock = self._commodity_locks.get(commodity_id)
                if not lock:
                    lock = asyncio.Lock()
                    self._commodity_locks[commodity_id] = lock

            async with lock:
                # Nochmals prüfen, wie viele Positionen für dieses Asset offen sind (atomar!)
                open_trades_for_asset = await self.count_open_positions_for_commodity(commodity_id)
                if open_trades_for_asset >= 2:
                    logger.info(f"⏭️  {commodity_id} übersprungen - bereits {open_trades_for_asset} offene Trades (Max: 2) [ATOMAR]")
                    return
                if open_trades_for_asset == 1:
                    cooldown_minutes = 30
                    recent_trade = await self.has_recent_trade_for_commodity(commodity_id, minutes=cooldown_minutes)
                    if recent_trade:
                        logger.info(f"⏭️  {commodity_id} übersprungen - zweite Position nur nach {cooldown_minutes} Minuten erlaubt [ATOMAR]")
                        return
                if open_trades_for_asset == 0:
                    # Es darf nur eine Position eröffnet werden, keine zweite
                    recent_trade = await self.has_recent_trade_for_commodity(commodity_id, minutes=1)
                    if recent_trade:
                        logger.info(f"⏭️  {commodity_id} übersprungen - Position wurde gerade erst eröffnet [ATOMAR]")
                        return
                # Temporäre Reservierung / Cooldown setzen NUR nachdem der Lock erfolgreich erworben wurde
                if not hasattr(self, '_asset_cooldown_tracker'):
                    self._asset_cooldown_tracker = {}
                self._asset_cooldown_tracker[commodity_id] = datetime.now(timezone.utc)
                logger.info(f"🔒 Lock für {commodity_id} akquiriert, Trade wird ausgeführt")

                try:
                    # 1. Hole Preishistorie für Markt-Analyse
                    price_history = await self.get_price_history(commodity_id, days=7)
                    if price_history:
                        prices = [p.get('price', p.get('close', 0)) for p in price_history[-100:]]
                        highs = [p.get('high', p.get('price', 0)) for p in price_history[-100:]]
                        lows = [p.get('low', p.get('price', 0)) for p in price_history[-100:]]
                    else:
                        # Fallback: Verwende aktuelle Analyse-Daten
                        prices = [analysis.get('entry_price', 100)] * 50
                        highs = [p * 1.001 for p in prices]
                        lows = [p * 0.999 for p in prices]

                    # 2. Markt-Zustand erkennen
                    market_analysis = autonomous_trading.detect_market_state(prices, highs, lows)
                    
                    # 3. Prüfe ob Strategie zum Markt passt (Dynamic Strategy Selection)
                    strategy_suitable, suitability_reason = autonomous_trading.is_strategy_suitable_for_market(
                        strategy, market_analysis
                    )
                    
                    if not strategy_suitable:
                        logger.warning(f"⛔ STRATEGIE NICHT GEEIGNET: {suitability_reason}")
                        logger.info(f"   Markt-Zustand: {market_analysis.state.value}")
                        logger.info(f"   Geeignete Cluster: {[c.value for c in market_analysis.suitable_clusters]}")
                        
                        # Versuche beste alternative Strategie zu finden und wechsele zu ihr, falls sinnvoll
                        enabled_strategies = []
                        for s in ['scalping', 'day', 'swing', 'momentum', 'breakout', 'mean_reversion', 'grid']:
                            setting_key = f'{s}_enabled' if s != 'day' else 'day_trading_enabled'
                            if self.settings.get(setting_key, False):
                                enabled_strategies.append(s)
                        
                        best_alt, alt_reason = autonomous_trading.select_best_strategy(
                            market_analysis, enabled_strategies, commodity_id
                        )
                        
                        if best_alt and best_alt != strategy:
                            logger.info(f"   💡 Empfohlene Alternative: {best_alt} ({alt_reason})")
                            logger.info(f"🔁 Wechsel zu alternativer Strategie '{best_alt}' und fahre mit der Trade-Ausführung fort")
                            strategy = best_alt
                        else:
                            logger.warning("⛔ Keine geeignete alternative Strategie gefunden - Trade wird abgebrochen")
                            return
                    else:
                        logger.info(f"✅ Strategie '{strategy}' passt zu Markt: {market_analysis.state.value}")
                    
                    # 4. Hole News-Sentiment für Universal Score
                    news_sentiment = "neutral"
                    high_impact_pending = False
                    try:
                        from news_analyzer import news_analyzer
                        news_status = await news_analyzer.get_commodity_news_status(commodity_id)
                        news_sentiment = news_status.get('sentiment', 'neutral')
                        high_impact_pending = news_status.get('high_impact_pending', False)
                    except:
                        pass
                    
                    # 5. Berechne Universal Confidence Score (4-Säulen-Modell)
                    confluence_count = analysis.get('indicators', {}).get('confluence_count', 0)
                    if confluence_count == 0:
                        # Zähle aus Indicators
                        indicators = analysis.get('indicators', {})
                        confluence_count = sum([
                            1 if indicators.get('rsi', 50) < 35 or indicators.get('rsi', 50) > 65 else 0,
                            1 if indicators.get('macd_histogram', 0) != 0 else 0,
                            1 if indicators.get('adx', 0) > 25 else 0,
                            1 if indicators.get('volume_surge', False) else 0,
                            1 if indicators.get('ema_9', 0) != indicators.get('ema_21', 0) else 0,
                        ])
                    
                    universal_score = autonomous_trading.calculate_universal_confidence(
                        strategy=strategy,
                        signal=direction,
                        indicators=analysis.get('indicators', {}),
                        market_analysis=market_analysis,
                        trend_h1=market_analysis.trend_direction,  # Vereinfacht
                        trend_h4=market_analysis.trend_direction,
                        trend_d1=market_analysis.trend_direction,
                        news_sentiment=news_sentiment,
                        high_impact_news_pending=high_impact_pending,
                        confluence_count=confluence_count
                    )
                    
                    # 6. Prüfe ob Trade erlaubt (>= 80%)
                    if not universal_score.passed_threshold:
                        logger.warning(f"⛔ TRADE BLOCKIERT: Universal Score {universal_score.total_score:.1f}% < 80%")
                        logger.info(f"   Bonuses: {universal_score.bonuses}")
                        logger.info(f"   Penalties: {universal_score.penalties}")
                        return
                    
                    # Passe Positionsgröße basierend auf Score an
                    if universal_score.total_score >= 90:
                        position_size_multiplier = 1.0  # Volle Position
                    elif universal_score.total_score >= 85:
                        position_size_multiplier = 0.85
                    else:
                        position_size_multiplier = 0.75
                    
                    logger.info(f"✅ Universal Score: {universal_score.total_score:.1f}% - Trade ERLAUBT")
                    logger.info(f"   Position Size: {position_size_multiplier:.0%}")
                
                except Exception as e:
                    logger.warning(f"Autonomous Trading Intelligence fehlgeschlagen: {e}, nutze Fallback...")
                    position_size_multiplier = 1.0
                    market_analysis = None
                    universal_score = None
            
            # ═══════════════════════════════════════════════════════════════
            # 🆕 v2.4.0: SELF-LEARNING VALIDIERUNG (zusätzliche Prüfung)
            # ═══════════════════════════════════════════════════════════════
            try:
                # Validiere über Self-Learning Journal
                validation = await trading_journal.validate_trade_signal(
                    strategy=strategy,
                    commodity=commodity_id,
                    signal=direction,
                    confidence=analysis.get('confidence', 0),
                    indicators=analysis.get('indicators', {}),
                    news_sentiment=news_sentiment if 'news_sentiment' in dir() else "neutral",
                    high_impact_pending=high_impact_pending if 'high_impact_pending' in dir() else False
                )
                
                logger.info(f"🧠 Self-Learning Validierung: {commodity_id} {direction}")
                logger.info(f"   Approved: {validation['approved']}")
                logger.info(f"   Confluence: {validation['confluence']['confluence_count']}/3")
                for reason in validation['reasons']:
                    logger.info(f"   {reason}")

                # Confidence anpassen falls Self-Learning ein Re-Rank liefert
                adjusted_confidence = validation.get('adjusted_confidence', analysis.get('confidence', 0))
                analysis['confidence'] = adjusted_confidence
                logger.info(f"   Adjusted Confidence: {adjusted_confidence:.1f}%")
                
                # Blockiere Trade wenn nicht approved
                if not validation['approved']:
                    logger.warning(f"⛔ Trade BLOCKIERT durch Self-Learning System")
                    return
                
            except Exception as e:
                logger.warning(f"Self-Learning Validierung fehlgeschlagen: {e}, fahre fort...")
            
            # ═══════════════════════════════════════════════════════════════
            
            # 🐛 FIX: DUPLICATE TRADE CHECK - Verhindert mehrere identische Trades
            # Prüfe ob bereits ein offener Trade für dieses Asset + Strategy + Direction existiert
            try:
                active_platforms = self.settings.get('active_platforms', [])
                
                # Hole alle offenen Positionen
                all_open_positions = []
                for platform_name in active_platforms:
                    if 'MT5_' in platform_name:
                        try:
                            positions = await multi_platform.get_open_positions(platform_name)
                            all_open_positions.extend(positions)
                        except:
                            pass
                
                # Prüfe ob identischer Trade bereits existiert
                for pos in all_open_positions:
                    pos_symbol = pos.get('symbol', '')
                    pos_type = pos.get('type', '')
                    
                    # Hole Strategie aus trade_settings
                    ticket = pos.get('ticket') or pos.get('positionId')
                    trade_settings = await self.db.trade_settings.find_one({"trade_id": f"mt5_{ticket}"})
                    pos_strategy = trade_settings.get('strategy', 'day') if trade_settings else 'day'
                    
                    # Check: Gleiches Asset + Gleiche Strategie + Gleiche Richtung?
                    # Verwende bevorzugt DB-Feld `commodity_id` (bei von uns eröffneten Trades).
                    pos_commodity = trade_settings.get('commodity_id') if trade_settings else None
                    # Fallback: Versuche Symbol-Mapping über `commodity_processor.COMMODITIES`
                    if not pos_commodity:
                        pos_symbol_upper = (pos_symbol or '').upper()
                        for cid, cinfo in commodity_processor.COMMODITIES.items():
                            candidates = [
                                cinfo.get('mt5_libertex_symbol', '') or '',
                                cinfo.get('mt5_icmarkets_symbol', '') or '',
                                cid
                            ]
                            if any(c and c.upper() in pos_symbol_upper for c in candidates):
                                pos_commodity = cid
                                break
                    # Prüfe gleiche Commodity + gleiche Strategie
                    if pos_commodity == commodity_id and pos_strategy == strategy:
                        # Bestimme Richtung der bestehenden Position (DB -> pos -> fallback)
                        pos_direction = (trade_settings.get('type') if trade_settings and trade_settings.get('type') else pos.get('type', '')).upper() if (trade_settings or pos) else ''
                        req_direction = (direction or '').upper()

                        # Nur blockieren wenn auch die Richtung übereinstimmt (A: gleiche Direction)
                        if pos_direction == req_direction:
                            # Bei Grid ist multiple erlaubt, sonst nicht
                            if strategy != 'grid':
                                logger.warning(
                                    f"⚠️ DUPLICATE VERHINDERT: Trade blocked - bestehende Position mit gleichem Asset, Strategie und Richtung gefunden (Ticket: {ticket})"
                                )
                                logger.info(f"   ℹ️ Bestehende Position: Symbol={pos_symbol}, Direction={pos_direction}, Strategy={pos_strategy}, Price={pos.get('price_open', 0):.2f}")
                                return  # ABBRUCH - Kein Duplicate Trade!
                        else:
                            # Gleiche Asset+Strategie aber unterschiedliche Richtung => erlauben (Info-Log)
                            logger.debug(f"ℹ️ Gleiches Asset+Strategie gefunden, aber unterschiedliche Richtung ({pos_direction} != {req_direction}) - Trade wird zugelassen")
                
                logger.info(f"✅ Duplicate Check OK: Kein identischer Trade gefunden")
                
                # 🐛 FIX: MAX POSITIONS CHECK pro Strategie
                # Zähle wie viele Trades dieser Strategie bereits offen sind
                strategy_open_count = sum(1 for pos in all_open_positions 
                                         if (await self.db.trade_settings.find_one(
                                             {"trade_id": f"mt5_{pos.get('ticket') or pos.get('positionId')}"}
                                         ) or {}).get('strategy') == strategy)
                
                # Hole Max Positions für diese Strategie
                max_positions_map = {
                    'day': self.settings.get('day_max_positions', 8),
                    'swing': self.settings.get('swing_max_positions', 6),
                    'scalping': self.settings.get('scalping_max_positions', 3),
                    'mean_reversion': self.settings.get('mean_reversion_max_positions', 5),
                    'momentum': self.settings.get('momentum_max_positions', 8),
                    'breakout': self.settings.get('breakout_max_positions', 6),
                    'grid': self.settings.get('grid_max_positions', 10)
                }
                max_positions = max_positions_map.get(strategy, 5)
                
                if strategy_open_count >= max_positions:
                    logger.warning(f"⚠️ MAX POSITIONS ERREICHT: {strategy} hat bereits {strategy_open_count}/{max_positions} Positionen")
                    logger.info(f"   ℹ️ Trade wird NICHT eröffnet - warte bis bestehende Trades geschlossen werden")
                    return  # ABBRUCH - Max Positions erreicht!
                
                logger.info(f"✅ Max Positions Check OK: {strategy} hat {strategy_open_count}/{max_positions} Positionen")
                
            except Exception as e:
                logger.warning(f"⚠️ Position Checks fehlgeschlagen: {e} - Trade wird trotzdem fortgesetzt")
            
            # ⏰ WICHTIG: Prüfe Handelszeiten
            if not commodity_processor.is_market_open(commodity_id):
                next_open = commodity_processor.get_next_market_open(commodity_id)
                logger.warning(f"⏰ Markt für {commodity_id} ist geschlossen. Nächste Öffnung: {next_open}")
                return
            
            # Hole Commodity-Info aus dem COMMODITIES dict
            commodity = commodity_processor.COMMODITIES.get(commodity_id)
            if not commodity:
                logger.error(f"Commodity {commodity_id} nicht gefunden")
                return
            
            # Bestimme Platform
            active_platforms = self.settings.get('active_platforms', [])
            if not active_platforms:
                logger.error("Keine aktiven Plattformen")
                return
            
            # Wähle Platform mit verfügbarem Symbol - GLEICHMÄSSIGE VERTEILUNG
            platform = None
            symbol = None
            
            # Prüfe, auf welchen Plattformen das Symbol verfügbar ist
            available_platforms = []
            
            for p in active_platforms:
                # V2.3.34 FIX: Prüfe auf ALLE Libertex-Varianten (DEMO, REAL, etc.)
                if 'LIBERTEX' in p and commodity.get('mt5_libertex_symbol'):
                    available_platforms.append({
                        'platform': p,
                        'symbol': commodity.get('mt5_libertex_symbol'),
                        'name': 'Libertex'
                    })
                # V2.3.34 FIX: Prüfe auf ALLE ICMarkets-Varianten
                elif 'ICMARKETS' in p and commodity.get('mt5_icmarkets_symbol'):
                    available_platforms.append({
                        'platform': p,
                        'symbol': commodity.get('mt5_icmarkets_symbol'),
                        'name': 'ICMarkets'
                    })
            
            if not available_platforms:
                logger.warning(f"⚠️  {commodity_id}: Kein verfügbares Symbol auf aktiven Plattformen")
                return
            
            # INTELLIGENTE LOAD BALANCING: Balance-gewichtete Plattform-Auswahl
            from multi_platform_connector import multi_platform
            
            platform_usage = {}
            
            for plat_info in available_platforms:
                try:
                    # Hole Account Info für Balance
                    account_info = await multi_platform.get_account_info(plat_info['platform'])
                    balance = account_info.get('balance', 0) if account_info else 0
                    
                    if balance <= 0:
                        platform_usage[plat_info['platform']] = 100.0  # Vermeide Plattform ohne Balance
                        continue
                    
                    # KORREKTE Berechnung wie Libertex: Portfolio Risk = (Margin / Equity) × 100
                    # Hole alle offenen Positionen
                    positions = await multi_platform.get_open_positions(plat_info['platform'])
                    
                    # Hole Account Info für Margin und Equity
                    account_info = await multi_platform.get_account_info(plat_info['platform'])
                    margin_used = account_info.get('margin', 0) if account_info else 0
                    equity = account_info.get('equity', balance) if account_info else balance
                    
                    # Berechne Portfolio-Risiko basierend auf MARGIN / EQUITY (Libertex-Formel)
                    usage_percent = (margin_used / equity * 100) if equity > 0 else 0.0
                    positions_count = len(positions) if positions else 0
                    
                    platform_usage[plat_info['platform']] = {
                        'usage_percent': usage_percent,
                        'balance': balance,
                        'equity': equity,
                        'margin_used': margin_used,
                        'positions_count': positions_count
                    }
                    
                    logger.debug(f"📊 {plat_info['name']}: {usage_percent:.1f}% Portfolio-Risiko (Margin: €{margin_used:.2f} / Equity: €{equity:.2f}, {positions_count} Positionen)")
                    
                except Exception as e:
                    logger.error(f"Fehler beim Abrufen von {plat_info['platform']}: {e}")
                    platform_usage[plat_info['platform']] = {'usage_percent': 100.0}  # Vermeide fehlerhafte Plattform
            
            # VERSCHÄRFT: Prüfe Limit MIT dem neuen Trade
            max_balance_percent = self.settings.get('combined_max_balance_percent_per_platform', 20.0)
            
            # Sicherheitspuffer: Neuer Trade könnte ~5% hinzufügen - FESTE REGEL
            safety_buffer = 5.0
            effective_limit = max_balance_percent - safety_buffer
            
            # Filtere Plattformen die noch Kapazität haben (mit Buffer)
            available_capacity_platforms = []
            
            for plat_info in available_platforms:
                usage_data = platform_usage.get(plat_info['platform'], {'usage_percent': 100.0})
                
                # Handle both dict and float
                if isinstance(usage_data, dict):
                    usage = usage_data.get('usage_percent', 100.0)
                else:
                    usage = usage_data
                
                logger.info(f"📊 {plat_info.get('name', plat_info['platform'])}: {usage:.1f}% Portfolio-Risiko (Limit: {max_balance_percent}%, Buffer-Limit: {effective_limit}%)")
                
                # Prüfe gegen Buffer-Limit!
                if usage < effective_limit:
                    available_capacity_platforms.append(plat_info)
                else:
                    logger.warning(f"⚠️ {plat_info.get('name', plat_info['platform'])} bei {usage:.1f}% - zu nah am Limit!")
            
            # Wenn ALLE Plattformen über Buffer-Limit, ABBRUCH!
            if not available_capacity_platforms:
                logger.error(f"🚫 ALLE Plattformen über {effective_limit}% (inkl. Buffer) - KEIN TRADE!")
                return  # Kein Trade ausführen!
            
            # Log platform candidates for instrumentation
            try:
                candidates_info = []
                for p in available_platforms:
                    info = platform_usage.get(p['platform'], {})
                    usage = info.get('usage_percent', info if isinstance(info, (int, float)) else 100.0)
                    candidates_info.append(f"{p['platform']}={usage:.1f}%")
                logger.info(f"📡 Platform candidates and usage: {', '.join(candidates_info)}")
            except Exception:
                pass

            # Wähle die Plattform mit der niedrigsten Nutzung (unter dem Limit)
            selected = min(available_capacity_platforms, 
                          key=lambda x: platform_usage.get(x['platform'], {}).get('usage_percent', 100.0))
            platform = selected['platform']
            symbol = selected['symbol']
            
            usage_info = platform_usage.get(platform, {})
            logger.info(
                f"✅ {commodity_id} → {selected['name']} "
                f"(Symbol: {symbol}, "
                f"Nutzung: {usage_info.get('usage_percent', 0):.1f}% / {max_balance_percent}%, "
                f"Balance: €{usage_info.get('balance', 0):,.2f}, "
                f"Positionen: {usage_info.get('positions_count', 0)})"
            )

            # ----------------------------
            # Per-account cooldown (platform-scoped)
            # V3.3.0: INCREASED from 15 to 60 minutes
            # V3.3.0: INTELLIGENT COOLDOWN - 60 min standard, 120 min wenn Asset aktiv
            # ----------------------------
            cooldown_minutes = self.settings.get('ai_per_account_cooldown_minutes', 60)
            
            # Prüfe ob Asset bereits Position hat
            open_positions_for_asset = await self.count_open_positions_for_commodity(commodity_id)
            if open_positions_for_asset > 0:
                cooldown_minutes = 120  # Erhöhe auf 120 Min wenn Asset aktiv ist
                logger.info(f"⏱️ {commodity_id}: {open_positions_for_asset} aktive Position(en) - erhöhe Cooldown auf {cooldown_minutes} Min")
            
            try:
                recent = await self.has_recent_trade_for_commodity(commodity_id, platform=platform, minutes=cooldown_minutes)
                if recent:
                    logger.info(f"⏭️  {commodity_id} on {platform} skipped - per-account cooldown active ({cooldown_minutes}min)")
                    return
            except Exception as e:
                logger.warning(f"⚠️ Error checking per-account cooldown for {commodity_id} on {platform}: {e}")

            # DB-backed reservation (multi-process protection) - platform-scoped
            try:
                import uuid
                from database_v2 import db_manager
                db = await db_manager.get_instance()
                db_owner = f"AI_BOT_{uuid.uuid4().hex}"
                resource_id = f"{platform}:{commodity_id}"
                db_reserved = await db.trades_db.reserve_resource('commodity', resource_id, db_owner, ttl_seconds=self.settings.get('ai_db_reservation_ttl_seconds', 60))
                if not db_reserved:
                    logger.warning(f"⚠️ DB reservation for {resource_id} failed: already reserved by another process. Aborting trade.")
                    return
                else:
                    logger.debug(f"🔒 DB reservation acquired for {resource_id} by {db_owner}")
            except Exception as e:
                logger.warning(f"⚠️ DB reservation check failed for {commodity_id} on {platform}: {e} - falling back to in-memory locks")
            
            # Risk Management: Positionsgröße berechnen
            account_info = await multi_platform.get_account_info(platform)
            if not account_info:
                logger.error(f"Account-Info nicht verfügbar für {platform}")
                return
            
            balance = account_info.get('balance', 0)
            if balance <= 0:
                logger.error("Balance ist 0 oder negativ")
                return
            
            # V2.3.31: Strategie-spezifische Parameter für ALLE Strategien
            if strategy == "swing":
                risk_per_trade = self.settings.get('swing_risk_per_trade_percent', 2.0)
                atr_multiplier_sl = self.settings.get('swing_atr_multiplier_sl', 2.0)
                atr_multiplier_tp = self.settings.get('swing_atr_multiplier_tp', 3.0)
            elif strategy == "scalping":
                risk_per_trade = self.settings.get('scalping_risk_per_trade_percent', 0.5)
                atr_multiplier_sl = 1.0  # Enge SL
                atr_multiplier_tp = 1.5  # Schnelle TP
            elif strategy == "mean_reversion":
                risk_per_trade = self.settings.get('mean_reversion_risk_per_trade_percent', 1.5)
                atr_multiplier_sl = self.settings.get('mean_reversion_stop_loss_percent', 2.0) / 100 * 2
                atr_multiplier_tp = self.settings.get('mean_reversion_take_profit_percent', 4.0) / 100 * 2
            elif strategy == "momentum":
                risk_per_trade = self.settings.get('momentum_risk_per_trade_percent', 1.5)
                atr_multiplier_sl = self.settings.get('momentum_stop_loss_percent', 2.5) / 100 * 2
                atr_multiplier_tp = self.settings.get('momentum_take_profit_percent', 5.0) / 100 * 2
            elif strategy == "breakout":
                risk_per_trade = self.settings.get('breakout_risk_per_trade_percent', 2.0)
                atr_multiplier_sl = self.settings.get('breakout_stop_loss_percent', 3.0) / 100 * 2
                atr_multiplier_tp = self.settings.get('breakout_take_profit_percent', 6.0) / 100 * 2
            elif strategy == "grid":
                risk_per_trade = self.settings.get('grid_risk_per_trade_percent', 1.0)
                atr_multiplier_sl = self.settings.get('grid_stop_loss_percent', 5.0) / 100 * 2
                atr_multiplier_tp = self.settings.get('grid_tp_per_level_percent', 2.0) / 100 * 2
            else:  # day trading (default)
                risk_per_trade = self.settings.get('day_risk_per_trade_percent', 1.0)
                atr_multiplier_sl = self.settings.get('day_atr_multiplier_sl', 1.0)
                atr_multiplier_tp = self.settings.get('day_atr_multiplier_tp', 1.5)

            # Option 2: Budget-basierte Obergrenze pro Trade aus 20% Plattform-Budget
            max_budget_percent = self.settings.get('combined_max_balance_percent_per_platform', 20.0)
            budget_buffer_ratio = self.settings.get('budget_buffer_ratio', 0.20)  # 20% Puffer ⇒ 16% nutzbar
            budget_target_trades = self.settings.get('budget_target_trades', 6)
            max_risk_per_trade_cap = self.settings.get('budget_max_risk_per_trade_percent', 3.0)

            usage_percent = usage_info.get('usage_percent', 0) if isinstance(usage_info, dict) else 0
            effective_budget = max_budget_percent * (1 - budget_buffer_ratio)
            remaining_budget = max(0.0, effective_budget - usage_percent)
            remaining_slots = max(1, budget_target_trades)
            budget_based_risk = remaining_budget / remaining_slots
            risk_per_trade = min(risk_per_trade, max_risk_per_trade_cap, budget_based_risk)

            if risk_per_trade <= 0:
                logger.warning(
                    f"🛑 Kein Budget für neuen Trade: usage={usage_percent:.1f}% / "
                    f"budget={effective_budget:.1f}% (slots={remaining_slots})"
                )
                return

            logger.info(
                f"📊 Budget-Risk-Adjust: usage={usage_percent:.1f}% | "
                f"budget={max_budget_percent}% buffer={budget_buffer_ratio*100:.0f}% → eff={effective_budget:.1f}% | "
                f"slots={remaining_slots} | risk_per_trade={risk_per_trade:.2f}% (cap {max_risk_per_trade_cap}%)"
            )
            
            logger.info(f"📐 Strategy parameters for {strategy}: risk={risk_per_trade}%, sl_mult={atr_multiplier_sl}, tp_mult={atr_multiplier_tp}")
            
            risk_amount = balance * (risk_per_trade / 100)
            
            # Stop Loss und Take Profit basierend auf PROZENT-SETTINGS (wie in monitor_open_positions)
            current_price = analysis.get('indicators', {}).get('current_price', 0)
            
            if not current_price:
                logger.error("Preis nicht verfügbar")
                return
            
            # Strategie-spezifische SL/TP - prüfe Modus (Prozent oder Euro)
            # V2.4.0: Nutze dynamische SL/TP aus der Analyse wenn verfügbar!
            use_dynamic_sl_tp = analysis.get('dynamic_sl_tp', False)
            
            if use_dynamic_sl_tp and analysis.get('stop_loss') and analysis.get('take_profit'):
                # V2.4.0: DYNAMISCHE SL/TP aus der fortgeschrittenen Analyse
                stop_loss = analysis.get('stop_loss')
                take_profit = analysis.get('take_profit')
                atr_value = analysis.get('atr', 0)
                crv = analysis.get('crv', 2.0)
                
                logger.info(f"📊 V2.4.0 DYNAMISCHES SL/TP:")
                logger.info(f"   ATR: {atr_value:.4f}")
                logger.info(f"   SL: {stop_loss:.4f}")
                logger.info(f"   TP: {take_profit:.4f}")
                logger.info(f"   CRV: {crv}")
                logger.info(f"   Konfidenz: {analysis.get('confidence', 0)}%")
                
                # Trailing Stop Flag für spätere Verwendung
                trailing_stop_enabled = analysis.get('trailing_stop', False)
                if trailing_stop_enabled:
                    logger.info(f"   🔄 TRAILING STOP aktiviert!")
                
            elif strategy == "swing":
                mode = self.settings.get('swing_tp_sl_mode', 'percent')
                if mode == 'euro':
                    # EURO-MODUS
                    tp_euro = self.settings.get('swing_take_profit_euro', 50.0)
                    sl_euro = self.settings.get('swing_stop_loss_euro', 20.0)
                    # Volume noch nicht bekannt, später berechnen
                    tp_percent = None
                    sl_percent = None
                else:
                    # PROZENT-MODUS
                    tp_percent = self.settings.get('swing_take_profit_percent', 4.0)
                    sl_percent = self.settings.get('swing_stop_loss_percent', 2.0)
                    tp_euro = None
                    sl_euro = None
            elif strategy == "scalping":
                # SCALPING: Immer Prozent-Modus mit sehr engen Werten
                mode = 'percent'
                tp_percent = 0.15  # 15 Pips (0.15%)
                sl_percent = 0.08  # 8 Pips (0.08%)
                tp_euro = None
                sl_euro = None
                risk_per_trade = 0.5  # Kleineres Risiko für Scalping
                logger.info(f"🎯 SCALPING Modus: TP={tp_percent}%, SL={sl_percent}%")
            else:  # day trading
                mode = self.settings.get('day_tp_sl_mode', 'percent')
                if mode == 'euro':
                    # EURO-MODUS
                    tp_euro = self.settings.get('day_take_profit_euro', 25.0)
                    sl_euro = self.settings.get('day_stop_loss_euro', 15.0)
                    tp_percent = None
                    sl_percent = None
                else:
                    # PROZENT-MODUS
                    tp_percent = self.settings.get('day_take_profit_percent', 2.5)
                    sl_percent = self.settings.get('day_stop_loss_percent', 1.5)
                    tp_euro = None
                    sl_euro = None
            
            # Berechne SL/TP basierend auf Modus
            if tp_euro is not None and sl_euro is not None:
                # EURO-MODUS: Erst Volume schätzen, dann Price berechnen
                # Nutze Standardvolume für erste Berechnung
                volume_estimate = 0.05
                
                if direction == 'BUY':
                    stop_loss = current_price - (sl_euro / volume_estimate)
                    take_profit = current_price + (tp_euro / volume_estimate)
                else:  # SELL
                    stop_loss = current_price + (sl_euro / volume_estimate)
                    take_profit = current_price - (tp_euro / volume_estimate)
                
                logger.info(f"📊 TP/SL Modus: EURO (TP: €{tp_euro}, SL: €{sl_euro})")
            else:
                # PROZENT-MODUS
                if direction == 'BUY':
                    stop_loss = current_price * (1 - sl_percent / 100)
                    take_profit = current_price * (1 + tp_percent / 100)
                else:  # SELL
                    stop_loss = current_price * (1 + sl_percent / 100)
                    take_profit = current_price * (1 - tp_percent / 100)
                
                logger.info(f"📊 TP/SL Modus: PROZENT (TP: {tp_percent}%, SL: {sl_percent}%)")
            
            # Dynamische, risikobasierte Positionsgröße mit _calculate_lot_size_v2
            from multi_bot_system import TradeBot
            tradebot = TradeBot()
            # Ermittele symbol_info für dynamische Limits
            symbol_info = None
            try:
                symbol_info = await tradebot._get_symbol_info(symbol, platform)
            except Exception as e:
                logger.warning(f"Symbol-Info konnte nicht geladen werden: {e}")
                symbol_info = {'min_lot': 0.01, 'max_lot': 2.0, 'pip_size': 0.01, 'tick_value': 10.0}

            # Berechne Stop-Loss in Pips
            pip_size = symbol_info.get('pip_size', 0.01)
            stop_loss_pips = abs(current_price - stop_loss) / pip_size if pip_size > 0 else 20
            stop_loss_pips = max(10, stop_loss_pips)  # Sicherheitsminimum
            tick_value = symbol_info.get('tick_value', 10.0)

            # Nutze dynamische Lot-Berechnung
            volume = tradebot._calculate_lot_size_v2(
                balance=balance,
                confidence_score=analysis.get('confidence', 0),
                stop_loss_pips=stop_loss_pips,
                tick_value=tick_value,
                symbol=symbol,
                trading_mode=strategy  # strategy als trading_mode übergeben
            )

            # Symbol-spezifische Limits
            min_lot = symbol_info.get('min_lot', 0.01)
            max_lot = symbol_info.get('max_lot', 2.0)
            if volume < min_lot:
                logger.warning(f"Lot {volume} unter Minimum für Symbol! Limitiert auf {min_lot}")
                volume = min_lot
            elif volume > max_lot:
                logger.warning(f"Lot {volume} überschreitet Symbol-Maximum! Limitiert auf {max_lot}")
                volume = max_lot

            logger.info(f"📊 Trade-Parameter (Dynamisch):")
            logger.info(f"   Platform: {platform}")
            logger.info(f"   Symbol: {symbol}")
            logger.info(f"   Direction: {direction}")
            logger.info(f"   Volume: {volume}")
            logger.info(f"   Entry: {current_price:.2f}")
            logger.info(f"   Stop Loss: {stop_loss:.2f}")
            logger.info(f"   Take Profit: {take_profit:.2f}")
            logger.info(f"   Risk: €{risk_amount:.2f} ({risk_per_trade}%)")

            # ⚡ IMMER OHNE MT5 SL/TP - KI ÜBERWACHT ALLES (Swing UND Day)!
            logger.info(f"💡 Öffne {strategy_name} Trade OHNE MT5 SL/TP - KI übernimmt komplette Überwachung!")
            logger.info(f"📊 KI wird überwachen: SL={stop_loss:.2f}, TP={take_profit:.2f}")

            result = await multi_platform.execute_trade(
                platform_name=platform,
                symbol=symbol,
                action=direction,
                volume=volume,
                stop_loss=None,  # IMMER None - KI überwacht!
                take_profit=None # IMMER None - KI überwacht!
            )
            
            if result and result.get('success'):
                ticket = result.get('ticket')
                logger.info(f"✅ AI-Trade erfolgreich ausgeführt: {commodity_id} {direction}")
                logger.info(f"   Ticket: {ticket}")
                
                # V2.3.36 FIX: Setze platform-scoped Cooldown für dieses Asset
                self.mark_trade_opened(commodity_id, platform)
                await self.db.trades.insert_one({
                    "commodity_id": commodity_id,
                    "commodity_name": commodity.get('name'),
                    "platform": platform,
                    "type": direction,
                    "quantity": volume,
                    "entry_price": current_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "mt5_ticket": ticket,
                    "status": "OPEN",
                    "opened_at": datetime.now(),
                    "opened_by": "AI_BOT",
                    "strategy": strategy,  # WICHTIG: Tag für Dual-Strategy-Tracking!
                    "analysis": analysis,  # Speichere komplette Analyse
                    "confidence": analysis.get('confidence', 0)
                })
                
                # WICHTIG: Speichere SL/TP auch in trade_settings für Monitor
                # CRITICAL: trade_id MUSS "mt5_{ticket}" Format haben!
                try:
                    trade_id = f"mt5_{ticket}"
                    await self.db.trade_settings.update_one(
                        {'trade_id': trade_id},
                        {'$set': {
                            'trade_id': trade_id,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'created_at': datetime.now(timezone.utc).isoformat(),
                            'opened_at': datetime.now(timezone.utc),  # Für Time-Check!
                            'commodity_id': commodity_id,  # commodity_id statt commodity!
                            'entry_price': current_price,
                            'platform': platform,
                            'strategy': strategy,  # WICHTIG: Strategie beibehalten!
                            'status': 'OPEN',  # Für Tracking
                            'type': direction,  # BUY oder SELL
                            'created_by': 'AI_BOT'
                        }},
                        upsert=True
                    )
                    logger.info(f"💾 SL/TP Settings gespeichert für {strategy.upper()}-Trade #{trade_id}")
                except Exception as e:
                    logger.error(f"⚠️ Fehler beim Speichern der Trade Settings: {e}")
                
                # V2.3.31: TICKET-STRATEGIE MAPPING - Dauerhaft speichern!
                try:
                    from database_v2 import db_manager
                    await db_manager.trades_db.save_ticket_strategy(
                        mt5_ticket=str(ticket),
                        strategy=strategy,
                        commodity=commodity_id,
                        platform=platform
                    )
                    logger.info(f"📋 Ticket-Strategie-Mapping gespeichert: #{ticket} → {strategy}")
                except Exception as e:
                    logger.warning(f"⚠️ Ticket-Strategie-Mapping Fehler: {e}")
                
                # ═══════════════════════════════════════════════════════════════
                # 🆕 v2.5.0: RISK CIRCUITS REGISTRIEREN (Breakeven + Time-Exit)
                # ═══════════════════════════════════════════════════════════════
                try:
                    trade_id = f"mt5_{ticket}"
                    
                    # Time-Exit je nach Strategie anpassen
                    time_exit_minutes = {
                        'scalping': 30,      # 30 Minuten für Scalping
                        'day': 240,          # 4 Stunden für Day Trading
                        'swing': 1440,       # 24 Stunden für Swing
                        'momentum': 180,     # 3 Stunden für Momentum
                        'breakout': 120,     # 2 Stunden für Breakout
                        'mean_reversion': 60,# 1 Stunde für Mean Reversion
                        'grid': 480          # 8 Stunden für Grid
                    }.get(strategy, 240)
                    
                    risk_status = autonomous_trading.register_trade_for_risk_monitoring(
                        trade_id=trade_id,
                        entry_price=current_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        strategy=strategy,
                        time_exit_minutes=time_exit_minutes
                    )
                    
                    logger.info(f"🔒 Risk Circuits aktiviert:")
                    logger.info(f"   Breakeven bei 50% TP: {risk_status.entry_price + (take_profit - risk_status.entry_price) * 0.5:.4f}")
                    logger.info(f"   Time-Exit nach: {time_exit_minutes} Minuten")
                    if strategy == 'momentum':
                        logger.info(f"   🔄 Trailing Stop: AKTIV")
                        
                except Exception as e:
                    logger.warning(f"Risk Circuit Registration fehlgeschlagen: {e}")
                
                # ═══════════════════════════════════════════════════════════════
                # 🆕 v2.4.0: TRADE IM JOURNAL LOGGEN
                # ═══════════════════════════════════════════════════════════════
                try:
                    await trading_journal.log_trade_entry(
                        trade_id=trade_id,
                        strategy=strategy,
                        commodity=commodity_id,
                        direction=direction,
                        entry_price=current_price,
                        planned_sl=stop_loss,
                        planned_tp=take_profit,
                        confidence_score=analysis.get('confidence', 0),
                        indicators=analysis.get('indicators', {}),
                        news_sentiment=news_sentiment if 'news_sentiment' in dir() else "neutral",
                        high_impact_pending=high_impact_pending if 'high_impact_pending' in dir() else False
                    )
                    logger.info(f"📝 Trade im Journal geloggt")
                except Exception as e:
                    logger.warning(f"Journal Logging fehlgeschlagen: {e}")
                
                # Für Lernzwecke
                self.trade_history.append({
                    "commodity": commodity_id,
                    "direction": direction,
                    "timestamp": datetime.now(),
                    "confidence": analysis.get('confidence', 0)
                })
                
            else:
                error = result.get('error', 'Unknown error') if result else 'No result'
                logger.error(f"❌ Trade fehlgeschlagen: {error}")
            
        except Exception as e:
            logger.error(f"Fehler bei Trade-Execution: {e}", exc_info=True)
        finally:
            try:
                # Wenn kein offener Trade in DB gefunden wurde, entferne temporäre Reservierung
                try:
                    existing = await self.db.trade_settings.find_one({
                        "commodity_id": commodity_id,
                        "status": {"$in": ["OPEN", "ACTIVE"]}
                    })
                    key = f"{platform}:{commodity_id}" if platform else commodity_id
                    if not existing and key in self._asset_cooldown_tracker:
                        del self._asset_cooldown_tracker[key]
                except Exception:
                    key = f"{platform}:{commodity_id}" if platform else commodity_id
                    if key in self._asset_cooldown_tracker:
                        del self._asset_cooldown_tracker[key]
            except Exception as e:
                logger.warning(f"⚠️ Fehler beim Aufräumen der temporären Reservierung für {commodity_id}: {e}")

            # Release DB reservation if we acquired one
            try:
                if db_reserved:
                    try:
                        from database_v2 import db_manager
                        db = await db_manager.get_instance()
                        resource_id = f"{platform}:{commodity_id}" if platform else commodity_id
                        await db.trades_db.release_resource('commodity', resource_id, owner=db_owner)
                        logger.debug(f"🔓 DB reservation released for {resource_id} by {db_owner}")
                    except Exception as e:
                        logger.warning(f"⚠️ Fehler beim Freigeben der DB-Reservierung für {commodity_id}: {e}")
            except Exception:
                pass

            # Release distributed SQLite lock for this asset
            try:
                if lock_acquired and lock_key and lock_owner:
                    released = await db_module.release_lock(lock_key, lock_owner)
                    if released:
                        logger.debug(f"🔓 Distributed lock released for {lock_key} ({lock_owner})")
                    else:
                        logger.warning(f"⚠️ Konnte distributed lock {lock_key} nicht freigeben (Owner: {lock_owner})")
            except Exception as e:
                logger.warning(f"⚠️ Fehler beim Freigeben des distributed locks für {commodity_id}: {e}")
    
    
    async def count_open_positions_for_commodity(self, commodity_id: str) -> int:
        """V2.3.36 FIX: Zählt ALLE offenen Trades für ein Commodity - sowohl in DB als auch MT5"""
        try:
            count = 0
            
            # 1. Prüfe lokale DB
            db_count = await self.db.trade_settings.count_documents({
                "commodity_id": commodity_id,
                "status": {"$in": ["OPEN", "ACTIVE"]}
            })
            count += db_count
            
            # 2. Prüfe MT5 Positionen via multi_platform_connector
            try:
                from multi_platform_connector import multi_platform
                
                # Symbol-Mapping für MT5
                symbol_map = {
                    'GOLD': ['XAUUSD', 'GOLD'],
                    'SILVER': ['XAGUSD', 'SILVER'],
                    'WTI_CRUDE': ['USOUSD', 'WTIUSD', 'CL', 'OIL'],
                    'BRENT_CRUDE': ['UKOUSD', 'BRENT'],
                    'NATURAL_GAS': ['NGUSD', 'NATGAS'],
                    'BITCOIN': ['BTCUSD', 'BTC'],
                    'EURUSD': ['EURUSD'],
                    'PLATINUM': ['XPTUSD', 'PLATINUM'],
                    'PALLADIUM': ['XPDUSD', 'PALLADIUM'],
                    'COPPER': ['COPPER', 'HG'],
                    'CORN': ['CORN', 'ZC'],
                    'WHEAT': ['WHEAT', 'ZW'],
                    'SOYBEANS': ['SOYBEANS', 'ZS'],
                    'COFFEE': ['COFFEE', 'KC'],
                    'SUGAR': ['SUGAR', 'SB'],
                    'COCOA': ['COCOA', 'CC'],
                    'COTTON': ['COTTON', 'CT'],
                    'GBPUSD': ['GBPUSD'],
                    'USDJPY': ['USDJPY']
                }
                
                mt5_symbols = symbol_map.get(commodity_id, [commodity_id])
                
                for platform_name in ['MT5_LIBERTEX_DEMO', 'MT5_ICMARKETS_DEMO']:
                    try:
                        positions = await multi_platform.get_positions(platform_name)
                        for pos in positions:
                            symbol = pos.get('symbol', '')
                            if any(s in symbol for s in mt5_symbols):
                                count += 1
                    except Exception as e:
                        logger.debug(f"Could not check {platform_name}: {e}")
                        
            except ImportError:
                pass
            
            logger.debug(f"📊 {commodity_id}: {count} offene Positionen gefunden")
            return count
            
        except Exception as e:
            logger.error(f"Error counting open positions: {e}")
            return 0
    
    async def has_recent_trade_for_commodity(self, commodity_id: str, platform: str = None, minutes: int = None) -> bool:
        """Prüft ob innerhalb der letzten X Minuten ein Trade für dieses Asset eröffnet wurde.

        Wenn `platform` angegeben ist, wird die Prüfung auf (platform,commodity) scoped (per-account cooldown).
        Minuten default: 15 für platform-scoped checks, 5 für global checks.
        """
        try:
            if minutes is None:
                minutes = self.settings.get('ai_per_account_cooldown_minutes', 15) if platform else 5

            # 1. In-Memory Cooldown Tracking (schnell und zuverlässig)
            if not hasattr(self, '_asset_cooldown_tracker'):
                self._asset_cooldown_tracker = {}

            # V2.3.37 FIX: Bereinige alte Cooldowns (älter als 1 Stunde)
            now_utc = datetime.now(timezone.utc)
            old_entries = [k for k, v in self._asset_cooldown_tracker.items() 
                          if (now_utc - v).total_seconds() > 3600]
            for k in old_entries:
                del self._asset_cooldown_tracker[k]

            cutoff_time = now_utc - timedelta(minutes=minutes)
            key = f"{platform}:{commodity_id}" if platform else commodity_id
            last_trade_time = self._asset_cooldown_tracker.get(key)

            if last_trade_time and last_trade_time > cutoff_time:
                time_diff = (now_utc - last_trade_time).total_seconds()
                logger.info(f"⏱️ {key}: Cooldown aktiv - letzter Trade vor {time_diff:.0f}s (min: {minutes*60}s)")
                return True

            # 2. DB-Prüfung als Backup (platform-scoped if platform provided)
            query = {
                "commodity_id": commodity_id,
                "opened_at": {"$gte": cutoff_time}
            }
            if platform:
                query["platform"] = platform

            recent_trade = await self.db.trade_settings.find_one(query)
            # Fallback to trades collection if available
            if not recent_trade:
                recent_trade = await self.db.trades.find_one(query)

            return recent_trade is not None

        except Exception as e:
            logger.error(f"Error checking recent trades: {e}")
            return False
    
    def mark_trade_opened(self, commodity_id: str, platform: str = None):
        """Markiert dass ein Trade für dieses Asset eröffnet wurde (platform-scoped Cooldown)."""
        if not hasattr(self, '_asset_cooldown_tracker'):
            self._asset_cooldown_tracker = {}
        key = f"{platform}:{commodity_id}" if platform else commodity_id
        self._asset_cooldown_tracker[key] = datetime.now(timezone.utc)
        logger.info(f"🔒 Cooldown gesetzt für {key}")
    
    async def get_all_open_ai_positions(self) -> List:
        """V2.3.34: Holt ALLE offenen AI-Positionen (alle Strategien)"""
        try:
            positions = await self.db.trade_settings.find({
                "status": {"$in": ["OPEN", "ACTIVE"]},
                "strategy": {"$in": ["swing", "day", "scalping", "mean_reversion", "momentum", "breakout", "grid"]}
            }).to_list(1000)
            
            return positions
            
        except Exception as e:
            logger.error(f"Error getting all open positions: {e}")
            return []
    def stop(self):
        """Stoppe Bot"""
        logger.info("🛑 Bot wird gestoppt...")
        self.running = False

    async def monitor_open_positions(self):
        """Periodically monitor open AI trades and adjust or close them based on market signals and settings.

        Runs in background as long as `self.running` is True. Uses `ai_monitor_interval_seconds` setting.
        """
        interval = int(self.settings.get('ai_monitor_interval_seconds', 30))
        logger.info(f"🛰️ Starting monitor loop (interval={interval}s)")
        try:
            while self.running:
                try:
                    open_trades = await self.get_all_open_ai_positions()
                    for trade in open_trades:
                        try:
                            await self._evaluate_and_adjust_trade(trade)
                        except Exception as e:
                            logger.exception(f"Error evaluating trade {trade.get('trade_id')}: {e}")
                except Exception as e:
                    logger.exception(f"Error in monitor loop: {e}")
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("Monitor loop cancelled")
        except Exception as e:
            logger.exception(f"Monitor loop failed: {e}")

    async def check_auto_close_events(self):
        """Close profitable trades near market close (daily) or before Friday close per settings."""
        try:
            auto_daily = self.settings.get('auto_close_profitable_daily', True)
            auto_friday = self.settings.get('auto_close_all_friday', True)
            minutes_before = int(self.settings.get('auto_close_minutes_before', 10))

            # Nothing to do
            if not (auto_daily or auto_friday):
                return

            from multi_platform_connector import multi_platform
            import commodity_market_hours

            active_platforms = self.settings.get('active_platforms', [])
            positions_to_close = []

            for platform_name in active_platforms:
                try:
                    positions = await multi_platform.get_open_positions(platform_name)
                    if not positions:
                        continue

                    to_close = await commodity_market_hours.get_positions_to_close_before_market_end(
                        self.db,
                        positions,
                        close_profitable_daily=auto_daily,
                        close_all_friday=auto_friday,
                        minutes_before_close=minutes_before
                    )

                    for item in to_close:
                        item['platform'] = platform_name
                        positions_to_close.append(item)

                except Exception as e:
                    logger.debug(f"Could not fetch positions from {platform_name}: {e}")

            # Close positions via connector
            for item in positions_to_close:
                try:
                    ticket = item.get('ticket')
                    if not ticket:
                        continue

                    trade_settings = await self.db.trade_settings.find_one({'trade_id': f'mt5_{ticket}'})
                    if not trade_settings:
                        continue

                    trade = {
                        'trade_id': f"mt5_{ticket}",
                        'mt5_ticket': ticket,
                        'platform': item.get('platform'),
                        'commodity_id': item.get('commodity_id')
                    }

                    logger.info(f"📉 Auto-Close executing for {trade['trade_id']} (profit €{item.get('profit'):.2f})")
                    await self._close_trade_via_connector(trade)

                except Exception as e:
                    logger.warning(f"Error closing position {item.get('ticket')}: {e}")

        except Exception as e:
            logger.error(f"Error in check_auto_close_events: {e}", exc_info=True)

    async def _evaluate_and_adjust_trade(self, trade: dict):
        """Evaluate an open trade and decide whether to adjust SL/TP/strategy or close it."""
        try:
            commodity_id = trade.get('commodity_id')
            platform = trade.get('platform')
            strategy = trade.get('strategy')
            ticket = trade.get('mt5_ticket')

            # 1) Check market price and compute potential SL/TP adjustments
            price_history = await self.get_price_history(commodity_id, days=1)
            if not price_history:
                return
            current_price = price_history[-1].get('price') if price_history else None
            if current_price is None:
                return

            # 2) Evaluate using strategy-specific analysis to get suggested SL/TP
            suggested = await self._analyze_and_suggest_adjustments(commodity_id, strategy, price_history)
            new_sl = suggested.get('stop_loss')
            new_tp = suggested.get('take_profit')
            new_strategy = suggested.get('strategy')

            # 3) If suggested close -> close via connector
            if suggested.get('close_now'):
                logger.info(f"🔔 Closing trade {trade.get('trade_id')} due to monitor signal (close_now)")
                await self._close_trade_via_connector(trade)
                return

            # 4) If suggested strategy differs and confidence high, update DB
            if new_strategy and new_strategy != strategy and suggested.get('confidence',0) >= 70:
                logger.info(f"🔁 Updating strategy for {trade.get('trade_id')} -> {new_strategy} (confidence {suggested.get('confidence')})")
                await self.db.trade_settings.update_one({'trade_id': trade.get('trade_id')}, {'$set': {'strategy': new_strategy}})

            # 5) Apply SL/TP adjustments in DB (app-level management), and log
            updates = {}
            if new_sl and new_sl != trade.get('stop_loss'):
                updates['stop_loss'] = new_sl
            if new_tp and new_tp != trade.get('take_profit'):
                updates['take_profit'] = new_tp
            if updates:
                logger.info(f"🔧 Adjusting trade {trade.get('trade_id')}: {updates}")
                await self.db.trade_settings.update_one({'trade_id': trade.get('trade_id')}, {'$set': updates})

        except Exception as e:
            logger.exception(f"Failed to evaluate/adjust trade: {e}")

    async def _analyze_and_suggest_adjustments(self, commodity_id: str, strategy: str, price_history: List[Dict], trade_type: str = None) -> Dict:
        """Generate suggested SL/TP/strategy adjustments based on latest analysis and ATR heuristics.

        Returns a dict: {stop_loss, take_profit, strategy, confidence, close_now}
        """
        try:
            # Call strategy-specific analyzer to get current signal and indicators
            if strategy == "scalping":
                analysis = await self._analyze_for_scalping_v2(commodity_id, price_history)
            elif strategy == "swing":
                analysis = await self._analyze_for_swing_v2(commodity_id, price_history)
            elif strategy == "momentum":
                analysis = await self._analyze_for_momentum_v2(commodity_id, price_history)
            elif strategy == "mean_reversion":
                analysis = await self._analyze_for_mean_reversion_v2(commodity_id, price_history)
            elif strategy == "breakout":
                analysis = await self._analyze_for_breakout_v2(commodity_id, price_history)
            elif strategy == "grid":
                analysis = await self._analyze_for_grid_v2(commodity_id, price_history)
            else:
                analysis = await self._analyze_for_day_trading_v2(commodity_id, price_history)

            indicators = analysis.get('indicators', {})
            atr = indicators.get('atr', None) or 0
            current_price = indicators.get('current_price') or (price_history[-1].get('price') if price_history else None)
            signal = analysis.get('signal')
            confidence = analysis.get('confidence', 0)

            # Strategy multipliers (keep in sync with execute_ai_trade logic)
            if strategy == "swing":
                atr_multiplier_sl = self.settings.get('swing_atr_multiplier_sl', 2.0)
                atr_multiplier_tp = self.settings.get('swing_atr_multiplier_tp', 3.0)
            elif strategy == "scalping":
                atr_multiplier_sl = 1.0
                atr_multiplier_tp = 1.5
            elif strategy == "mean_reversion":
                atr_multiplier_sl = self.settings.get('mean_reversion_stop_loss_percent', 2.0) / 100 * 2
                atr_multiplier_tp = self.settings.get('mean_reversion_take_profit_percent', 4.0) / 100 * 2
            elif strategy == "momentum":
                atr_multiplier_sl = self.settings.get('momentum_stop_loss_percent', 2.5) / 100 * 2
                atr_multiplier_tp = self.settings.get('momentum_take_profit_percent', 5.0) / 100 * 2
            elif strategy == "breakout":
                atr_multiplier_sl = self.settings.get('breakout_stop_loss_percent', 3.0) / 100 * 2
                atr_multiplier_tp = self.settings.get('breakout_take_profit_percent', 6.0) / 100 * 2
            elif strategy == "grid":
                atr_multiplier_sl = self.settings.get('grid_stop_loss_percent', 5.0) / 100 * 2
                atr_multiplier_tp = self.settings.get('grid_tp_per_level_percent', 2.0) / 100 * 2
            else:
                atr_multiplier_sl = self.settings.get('day_atr_multiplier_sl', 1.0)
                atr_multiplier_tp = self.settings.get('day_atr_multiplier_tp', 1.5)

            # Basic heuristics
            result = {
                'stop_loss': None,
                'take_profit': None,
                'strategy': None,
                'confidence': confidence,
                'close_now': False
            }

            # If strong opposite signal, close
            if trade_type and signal and ((trade_type.upper() == 'BUY' and signal == 'SELL') or (trade_type.upper() == 'SELL' and signal == 'BUY')) and confidence >= 70:
                result['close_now'] = True
                return result

            # Calculate SL/TP using ATR multipliers when ATR available
            if atr and current_price:
                if trade_type and trade_type.upper() == 'BUY':
                    sl = current_price - (atr * atr_multiplier_sl)
                    tp = current_price + (atr * atr_multiplier_tp)
                else:
                    sl = current_price + (atr * atr_multiplier_sl)
                    tp = current_price - (atr * atr_multiplier_tp)

                result['stop_loss'] = round(sl, 4)
                result['take_profit'] = round(tp, 4)

            # Strategy nudges: if signal strongly favors a different strategy, suggest change
            if analysis.get('recommended_strategy') and analysis.get('confidence', 0) >= 70:
                result['strategy'] = analysis.get('recommended_strategy')

            return result
        except Exception as e:
            logger.exception(f"Error in suggest adjustments: {e}")
            return {'stop_loss': None, 'take_profit': None, 'strategy': None, 'confidence': 0, 'close_now': False}

    async def _close_trade_via_connector(self, trade: dict):
        """Close trade via multi_platform connector and update DB documents."""
        try:
            from multi_platform_connector import multi_platform
            platform = trade.get('platform')
            ticket = trade.get('mt5_ticket')
            if not platform or not ticket:
                logger.error("Cannot close trade: missing platform or ticket")
                return False

            success = await multi_platform.close_position(platform, str(ticket))
            if success:
                # Update DB records
                await self.db.trades.update_one({'mt5_ticket': ticket}, {'$set': {'status': 'CLOSED', 'closed_at': datetime.now(), 'closed_by': 'AI_BOT'}})
                await self.db.trade_settings.update_one({'trade_id': trade.get('trade_id')}, {'$set': {'status': 'CLOSED', 'closed_at': datetime.now()}})
                logger.info(f"✅ Trade {trade.get('trade_id')} closed via connector")
                return True
            else:
                logger.warning(f"⚠️ Failed to close trade {trade.get('trade_id')} via connector")
                return False
        except Exception as e:
            logger.exception(f"Error closing trade via connector: {e}")
            return False

async def main():
    """Hauptfunktion"""
    bot = AITradingBot()
    
    if await bot.initialize():
        try:
            await bot.run_forever()
        except KeyboardInterrupt:
            logger.info("\n⚠️  Bot manuell gestoppt (Ctrl+C)")
        finally:
            bot.stop()
    else:
        logger.error("❌ Bot konnte nicht initialisiert werden")

# Bot Manager für FastAPI Integration

    # 🆕 v2.3.29: NEUE STRATEGIEN - Signal-Generation Methoden
    
    async def analyze_mean_reversion_signals(self):
        """
        📊 Mean Reversion Strategy - Signal-Generation
        Analysiert Märkte mit Bollinger Bands + RSI
        """
        try:
            if not self.mean_reversion_strategy or not self.mean_reversion_strategy.enabled:
                return
            
            enabled_commodities = self.settings.get('enabled_commodities', [])
            cooldown_minutes = 5  # Analyse alle 5 Minuten
            
            for commodity_id in enabled_commodities:
                # Cooldown Check
                last_check = self.last_analysis_time_by_strategy.get(f"mean_reversion_{commodity_id}", 0)
                if (datetime.now().timestamp() - last_check) < (cooldown_minutes * 60):
                    continue
                
                self.last_analysis_time_by_strategy[f"mean_reversion_{commodity_id}"] = datetime.now().timestamp()
                
                # Market Data vorbereiten
                market_data = self.market_data.get(commodity_id, {})
                if not market_data:
                    continue
                
                # Hole Preis-Historie (letzte 100 Datenpunkte)
                # TODO: Aus market_data_history laden
                price_history = market_data.get('price_history', [])
                if len(price_history) < 20:  # Min für BB
                    continue
                
                market_data_for_strategy = {
                    'price_history': price_history[-100:],  # Letzte 100
                    'current_price': market_data.get('current_price', 0),
                    'symbol': commodity_id
                }
                
                # Signal generieren
                signal = await self.mean_reversion_strategy.analyze_signal(market_data_for_strategy)
                
                if signal and signal['confidence'] >= self.mean_reversion_strategy.min_confidence:
                    logger.info(f"📊 Mean Reversion Signal: {signal['signal']} {commodity_id} @ {signal['entry_price']:.2f} (Confidence: {signal['confidence']:.2%})")
                    
                    # Trade ausführen
                    await self.execute_ai_trade(
                        commodity_id=commodity_id,
                        direction=signal['signal'],
                        analysis=signal,
                        strategy="mean_reversion"
                    )
        
        except Exception as e:
            logger.error(f"❌ Error in Mean Reversion analysis: {e}", exc_info=True)
    
    async def analyze_momentum_signals(self):
        """
        🚀 Momentum Trading Strategy - Signal-Generation
        Analysiert Trends mit Momentum + MA Crossovers
        """
        try:
            if not self.momentum_strategy or not self.momentum_strategy.enabled:
                return
            
            enabled_commodities = self.settings.get('enabled_commodities', [])
            cooldown_minutes = 5  # Analyse alle 5 Minuten
            
            for commodity_id in enabled_commodities:
                # Cooldown Check
                last_check = self.last_analysis_time_by_strategy.get(f"momentum_{commodity_id}", 0)
                if (datetime.now().timestamp() - last_check) < (cooldown_minutes * 60):
                    continue
                
                self.last_analysis_time_by_strategy[f"momentum_{commodity_id}"] = datetime.now().timestamp()
                
                # Market Data vorbereiten
                market_data = self.market_data.get(commodity_id, {})
                if not market_data:
                    continue
                
                # Braucht mindestens 200 Datenpunkte für MA(200)
                price_history = market_data.get('price_history', [])
                if len(price_history) < 200:
                    continue
                
                market_data_for_strategy = {
                    'price_history': price_history[-250:],  # Letzte 250
                    'current_price': market_data.get('current_price', 0),
                    'symbol': commodity_id
                }
                
                # Signal generieren
                signal = await self.momentum_strategy.analyze_signal(market_data_for_strategy)
                
                if signal and signal['confidence'] >= self.momentum_strategy.min_confidence:
                    logger.info(f"🚀 Momentum Signal: {signal['signal']} {commodity_id} @ {signal['entry_price']:.2f} (Confidence: {signal['confidence']:.2%})")
                    
                    # Trade ausführen
                    await self.execute_ai_trade(
                        commodity_id=commodity_id,
                        direction=signal['signal'],
                        analysis=signal,
                        strategy="momentum"
                    )
        
        except Exception as e:
            logger.error(f"❌ Error in Momentum analysis: {e}", exc_info=True)
    
    async def analyze_breakout_signals(self):
        """
        💥 Breakout Trading Strategy - Signal-Generation
        Analysiert Ausbrüche aus Ranges mit Volume
        """
        try:
            if not self.breakout_strategy or not self.breakout_strategy.enabled:
                return
            
            enabled_commodities = self.settings.get('enabled_commodities', [])
            cooldown_minutes = 2  # Analyse alle 2 Minuten (schneller für Breakouts)
            
            for commodity_id in enabled_commodities:
                # Cooldown Check
                last_check = self.last_analysis_time_by_strategy.get(f"breakout_{commodity_id}", 0)
                if (datetime.now().timestamp() - last_check) < (cooldown_minutes * 60):
                    continue
                
                self.last_analysis_time_by_strategy[f"breakout_{commodity_id}"] = datetime.now().timestamp()
                
                # Market Data vorbereiten
                market_data = self.market_data.get(commodity_id, {})
                if not market_data:
                    continue
                
                price_history = market_data.get('price_history', [])
                if len(price_history) < 25:  # Lookback + Confirmation
                    continue
                
                market_data_for_strategy = {
                    'price_history': price_history[-50:],
                    'current_price': market_data.get('current_price', 0),
                    'symbol': commodity_id,
                    'volume_history': [],  # TODO: Volume-Daten laden
                    'current_volume': 0
                }
                
                # Signal generieren
                signal = await self.breakout_strategy.analyze_signal(market_data_for_strategy)
                
                if signal and signal['confidence'] >= self.breakout_strategy.min_confidence:
                    logger.info(f"💥 Breakout Signal: {signal['signal']} {commodity_id} @ {signal['entry_price']:.2f} (Confidence: {signal['confidence']:.2%})")
                    
                    # Trade ausführen
                    await self.execute_ai_trade(
                        commodity_id=commodity_id,
                        direction=signal['signal'],
                        analysis=signal,
                        strategy="breakout"
                    )
        
        except Exception as e:
            logger.error(f"❌ Error in Breakout analysis: {e}", exc_info=True)
    
    async def analyze_grid_signals(self):
        """
        🔹 Grid Trading Strategy - Signal-Generation
        Platziert Trades basierend auf Grid-Levels
        """
        try:
            if not self.grid_strategy or not self.grid_strategy.enabled:
                return
            
            enabled_commodities = self.settings.get('enabled_commodities', [])
            cooldown_seconds = 30  # Sehr kurz für Grid (alle 30 Sek)
            
            # Hole alle offenen Grid-Positionen
            from multi_platform_connector import multi_platform
            all_positions = []
            for platform in self.settings.get('active_platforms', []):
                try:
                    positions = await multi_platform.get_open_positions(platform)
                    all_positions.extend(positions)
                except:
                    pass
            
            for commodity_id in enabled_commodities:
                # Cooldown Check
                last_check = self.last_analysis_time_by_strategy.get(f"grid_{commodity_id}", 0)
                if (datetime.now().timestamp() - last_check) < cooldown_seconds:
                    continue
                
                self.last_analysis_time_by_strategy[f"grid_{commodity_id}"] = datetime.now().timestamp()
                
                # Market Data vorbereiten
                market_data = self.market_data.get(commodity_id, {})
                if not market_data:
                    continue
                
                # Filter Grid-Positionen für dieses Commodity
                grid_positions = [p for p in all_positions if p.get('symbol') == commodity_id]
                
                market_data_for_strategy = {
                    'price_history': market_data.get('price_history', [])[-50:],
                    'current_price': market_data.get('current_price', 0),
                    'symbol': commodity_id,
                    'open_positions': grid_positions
                }
                
                # Signal generieren
                signal = await self.grid_strategy.analyze_signal(market_data_for_strategy)
                
                if signal:
                    logger.info(f"🔹 Grid Signal: {signal['signal']} {commodity_id} @ {signal['entry_price']:.2f} (Level: {signal['indicators']['target_level']:.2f})")
                    
                    # Trade ausführen
                    await self.execute_ai_trade(
                        commodity_id=commodity_id,
                        direction=signal['signal'],
                        analysis=signal,
                        strategy="grid"
                    )
        
        except Exception as e:
            logger.error(f"❌ Error in Grid analysis: {e}", exc_info=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # V2.4.0: FORTGESCHRITTENE ANALYSE-METHODEN MIT KONFIDENZ UND ATR
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def _analyze_for_scalping_v2(self, commodity_id: str, price_history: List[Dict]) -> Dict:
        """V2.4.0: Fortgeschrittene Scalping-Analyse mit Order Flow und Micro-Momentum"""
        try:
            prices = [p.get('price', p.get('close', 0)) for p in price_history[-100:]]
            highs = [p.get('high', p.get('price', 0)) for p in price_history[-100:]]
            lows = [p.get('low', p.get('price', 0)) for p in price_history[-100:]]
            
            if len(prices) < 20:
                return {'signal': 'HOLD', 'confidence': 0, 'reason': 'Nicht genug Daten'}
            
            current_price = prices[-1]
            
            # Nutze fortgeschrittene Trading-Logik
            # News/Sentiment aus externer Quelle holen (hier als Beispiel leer)
            news = {}
            sentiment = {}
            signal = advanced_trading.analyze_for_strategy(
                strategy=TradingStrategy.SCALPING,
                current_price=current_price,
                prices=prices,
                highs=highs,
                lows=lows,
                news=news,
                sentiment=sentiment
            )
            
            logger.info(f"⚡ SCALPING V2 {commodity_id}: Signal={signal.signal}, Konfidenz={signal.confidence}%, ATR={signal.atr:.4f}")
            logger.info(f"   SL={signal.stop_loss:.4f}, TP={signal.take_profit:.4f}, CRV={signal.crv}")
            
            return self._signal_to_dict(signal)
            
        except Exception as e:
            logger.error(f"Scalping V2 analysis error: {e}", exc_info=True)
            return {'signal': 'HOLD', 'confidence': 0, 'reason': str(e)}
    
    async def _analyze_for_day_trading_v2(self, commodity_id: str, price_history: List[Dict]) -> Dict:
        """V2.4.0: Fortgeschrittene Day Trading-Analyse mit VWAP"""
        try:
            prices = [p.get('price', p.get('close', 0)) for p in price_history[-100:]]
            highs = [p.get('high', p.get('price', 0)) for p in price_history[-100:]]
            lows = [p.get('low', p.get('price', 0)) for p in price_history[-100:]]
            volumes = [p.get('volume', 1000) for p in price_history[-100:]]
            
            if len(prices) < 50:
                return {'signal': 'HOLD', 'confidence': 0, 'reason': 'Nicht genug Daten'}
            
            current_price = prices[-1]
            
            news = {}
            sentiment = {}
            signal = advanced_trading.analyze_for_strategy(
                strategy=TradingStrategy.DAY_TRADING,
                current_price=current_price,
                prices=prices,
                highs=highs,
                lows=lows,
                volumes=volumes,
                news=news,
                sentiment=sentiment
            )
            
            logger.info(f"📈 DAY TRADING V2 {commodity_id}: Signal={signal.signal}, Konfidenz={signal.confidence}%, ATR={signal.atr:.4f}")
            logger.info(f"   SL={signal.stop_loss:.4f}, TP={signal.take_profit:.4f}, CRV={signal.crv}")
            
            return self._signal_to_dict(signal)
            
        except Exception as e:
            logger.error(f"Day Trading V2 analysis error: {e}", exc_info=True)
            return {'signal': 'HOLD', 'confidence': 0, 'reason': str(e)}
    
    async def _analyze_for_swing_v2(self, commodity_id: str, price_history: List[Dict]) -> Dict:
        """V2.4.0: Fortgeschrittene Swing Trading-Analyse mit Fibonacci Extensions"""
        try:
            prices = [p.get('price', p.get('close', 0)) for p in price_history[-250:]]
            highs = [p.get('high', p.get('price', 0)) for p in price_history[-250:]]
            lows = [p.get('low', p.get('price', 0)) for p in price_history[-250:]]
            volumes = [p.get('volume', 1000) for p in price_history[-250:]]
            
            if len(prices) < 100:
                return {'signal': 'HOLD', 'confidence': 0, 'reason': 'Nicht genug Daten (min 100)'}
            
            current_price = prices[-1]
            
            news = {}
            sentiment = {}
            signal = advanced_trading.analyze_for_strategy(
                strategy=TradingStrategy.SWING,
                current_price=current_price,
                prices=prices,
                highs=highs,
                lows=lows,
                volumes=volumes,
                news=news,
                sentiment=sentiment
            )
            
            logger.info(f"🔄 SWING V2 {commodity_id}: Signal={signal.signal}, Konfidenz={signal.confidence}%, ATR={signal.atr:.4f}")
            logger.info(f"   SL={signal.stop_loss:.4f}, TP={signal.take_profit:.4f}, CRV={signal.crv}")
            
            return self._signal_to_dict(signal)
            
        except Exception as e:
            logger.error(f"Swing V2 analysis error: {e}", exc_info=True)
            return {'signal': 'HOLD', 'confidence': 0, 'reason': str(e)}
    
    async def _analyze_for_momentum_v2(self, commodity_id: str, price_history: List[Dict]) -> Dict:
        """V2.4.0: Fortgeschrittene Momentum-Analyse mit Trailing Stop"""
        try:
            prices = [p.get('price', p.get('close', 0)) for p in price_history[-100:]]
            highs = [p.get('high', p.get('price', 0)) for p in price_history[-100:]]
            lows = [p.get('low', p.get('price', 0)) for p in price_history[-100:]]
            volumes = [p.get('volume', 1000) for p in price_history[-100:]]
            
            if len(prices) < 50:
                return {'signal': 'HOLD', 'confidence': 0, 'reason': 'Nicht genug Daten'}
            
            current_price = prices[-1]
            
            news = {}
            sentiment = {}
            signal = advanced_trading.analyze_for_strategy(
                strategy=TradingStrategy.MOMENTUM,
                current_price=current_price,
                prices=prices,
                highs=highs,
                lows=lows,
                volumes=volumes,
                news=news,
                sentiment=sentiment
            )
            
            logger.info(f"🚀 MOMENTUM V2 {commodity_id}: Signal={signal.signal}, Konfidenz={signal.confidence}%, Trailing={signal.trailing_stop}")
            logger.info(f"   SL={signal.stop_loss:.4f}, TP={signal.take_profit:.4f}, CRV={signal.crv}")
            
            return self._signal_to_dict(signal)
            
        except Exception as e:
            logger.error(f"Momentum V2 analysis error: {e}", exc_info=True)
            return {'signal': 'HOLD', 'confidence': 0, 'reason': str(e)}
    
    async def _analyze_for_breakout_v2(self, commodity_id: str, price_history: List[Dict]) -> Dict:
        """V2.4.0: Fortgeschrittene Breakout-Analyse mit Range-Erkennung"""
        try:
            prices = [p.get('price', p.get('close', 0)) for p in price_history[-100:]]
            highs = [p.get('high', p.get('price', 0)) for p in price_history[-100:]]
            lows = [p.get('low', p.get('price', 0)) for p in price_history[-100:]]
            
            if len(prices) < 50:
                return {'signal': 'HOLD', 'confidence': 0, 'reason': 'Nicht genug Daten'}
            
            current_price = prices[-1]
            
            news = {}
            sentiment = {}
            signal = advanced_trading.analyze_for_strategy(
                strategy=TradingStrategy.BREAKOUT,
                current_price=current_price,
                prices=prices,
                highs=highs,
                lows=lows,
                news=news,
                sentiment=sentiment
            )
            
            logger.info(f"💥 BREAKOUT V2 {commodity_id}: Signal={signal.signal}, Konfidenz={signal.confidence}%")
            logger.info(f"   SL={signal.stop_loss:.4f}, TP={signal.take_profit:.4f} (200% Range)")
            
            return self._signal_to_dict(signal)
            
        except Exception as e:
            logger.error(f"Breakout V2 analysis error: {e}", exc_info=True)
            return {'signal': 'HOLD', 'confidence': 0, 'reason': str(e)}
    
    async def _analyze_for_mean_reversion_v2(self, commodity_id: str, price_history: List[Dict]) -> Dict:
        """V2.4.0: Fortgeschrittene Mean Reversion-Analyse mit Bollinger Bands"""
        try:
            prices = [p.get('price', p.get('close', 0)) for p in price_history[-100:]]
            highs = [p.get('high', p.get('price', 0)) for p in price_history[-100:]]
            lows = [p.get('low', p.get('price', 0)) for p in price_history[-100:]]
            
            if len(prices) < 30:
                return {'signal': 'HOLD', 'confidence': 0, 'reason': 'Nicht genug Daten'}
            
            current_price = prices[-1]
            
            news = {}
            sentiment = {}
            signal = advanced_trading.analyze_for_strategy(
                strategy=TradingStrategy.MEAN_REVERSION,
                current_price=current_price,
                prices=prices,
                highs=highs,
                lows=lows,
                news=news,
                sentiment=sentiment
            )
            
            logger.info(f"📉 MEAN REVERSION V2 {commodity_id}: Signal={signal.signal}, Konfidenz={signal.confidence}%")
            logger.info(f"   StdDev Distance: {signal.indicators.get('distance_from_mean', 0):.2f}")
            
            return self._signal_to_dict(signal)
            
        except Exception as e:
            logger.error(f"Mean Reversion V2 analysis error: {e}", exc_info=True)
            return {'signal': 'HOLD', 'confidence': 0, 'reason': str(e)}
    
    async def _analyze_for_grid_v2(self, commodity_id: str, price_history: List[Dict]) -> Dict:
        """V2.4.0: Fortgeschrittene Grid Trading-Analyse mit ADR"""
        try:
            prices = [p.get('price', p.get('close', 0)) for p in price_history[-100:]]
            highs = [p.get('high', p.get('price', 0)) for p in price_history[-100:]]
            lows = [p.get('low', p.get('price', 0)) for p in price_history[-100:]]
            
            if len(prices) < 30:
                return {'signal': 'HOLD', 'confidence': 0, 'reason': 'Nicht genug Daten'}
            
            current_price = prices[-1]
            
            news = {}
            sentiment = {}
            signal = advanced_trading.analyze_for_strategy(
                strategy=TradingStrategy.GRID,
                current_price=current_price,
                prices=prices,
                highs=highs,
                lows=lows,
                news=news,
                sentiment=sentiment
            )
            
            logger.info(f"🔲 GRID V2 {commodity_id}: Signal={signal.signal}, Konfidenz={signal.confidence}%")
            logger.info(f"   Grid Type: {signal.indicators.get('grid_type', 'normal')}, Spacing: {signal.indicators.get('grid_spacing', 0):.4f}")
            
            return self._signal_to_dict(signal)
            
        except Exception as e:
            logger.error(f"Grid V2 analysis error: {e}", exc_info=True)
            return {'signal': 'HOLD', 'confidence': 0, 'reason': str(e)}
    
    def _signal_to_dict(self, signal: TradeSignal) -> Dict:
        """Konvertiert TradeSignal zu Dictionary für Kompatibilität"""
        return {
            'signal': signal.signal,
            'confidence': signal.confidence,
            'total_score': signal.confidence,
            'reason': ' | '.join(signal.reasons),
            'entry_price': signal.entry_price,
            'stop_loss': signal.stop_loss,
            'take_profit': signal.take_profit,
            'trailing_stop': signal.trailing_stop,
            'crv': signal.crv,
            'atr': signal.atr,
            'volatility': signal.volatility,
            'indicators': signal.indicators,
            'strategy': signal.strategy.value,
            'dynamic_sl_tp': True  # Flag dass SL/TP dynamisch berechnet wurden
        }


class BotManager:
    def __init__(self):
        self.bot = None
        self.bot_task = None
        
    def is_running(self):
        return self.bot is not None and self.bot.running
    
    async def start(self):
        if self.is_running():
            logger.warning("Bot läuft bereits")
            return False
        
        self.bot = AITradingBot()
        if await self.bot.initialize():
            self.bot_task = asyncio.create_task(self.bot.run_forever())
            logger.info("✅ Bot Manager gestartet")
            return True
        return False
    
    async def stop(self):
        if self.bot:
            self.bot.stop()
            if self.bot_task:
                self.bot_task.cancel()
            self.bot = None
            self.bot_task = None
            logger.info("✅ Bot Manager gestoppt")

# Global bot manager instance
bot_manager = BotManager()

if __name__ == "__main__":
    asyncio.run(main())
