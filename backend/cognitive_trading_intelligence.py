"""
🧠 COGNITIVE TRADING INTELLIGENCE V4.2
=======================================

Transformiert Booner Trade von reaktivem zu proaktivem System.

Komponenten:
1. Historical Feasibility Analyzer - Prüft ob Ziel erreichbar
2. Strategic Reasoning Engine (Advocatus Diaboli) - Interne Debatte
3. Asset-Specific Context Intelligence - Nuanciertes Wissen
4. Cognitive Validation Pipeline - Dreistufige Analyse

Autor: Booner Trade AI Team
Version: 4.2
"""

import logging
import asyncio
import json
import aiohttp
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CognitiveDecision:
    """Ergebnis der kognitiven Validierung"""
    decision: str  # "GO" oder "VETO"
    confidence: int  # 0-100
    reasoning: str
    historical_feasibility: float  # 0-100
    pro_arguments: List[str]
    contra_arguments: List[str]
    risk_assessment: str
    adjusted_tp: Optional[float] = None
    adjusted_sl: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class HistoricalContext:
    """Historische Daten für 48h-Analyse"""
    asset: str
    last_48h_high: float
    last_48h_low: float
    last_48h_avg: float
    atr: float
    atr_percentage: float
    volatility_std: float
    price_range: float
    current_price: float
    target_in_range: bool
    statistical_anomaly: bool


@dataclass
class AssetIntelligence:
    """Asset-spezifisches Kontextwissen"""
    asset: str
    category: str
    key_correlations: List[str]
    session_notes: str
    geopolitical_factors: List[str]
    typical_volatility: str
    best_trading_hours: str
    avoid_conditions: List[str]


# ═══════════════════════════════════════════════════════════════════════════
# ASSET KNOWLEDGE BASE
# ═══════════════════════════════════════════════════════════════════════════

ASSET_INTELLIGENCE_DB = {
    # EDELMETALLE
    "GOLD": AssetIntelligence(
        asset="GOLD",
        category="Edelmetalle",
        key_correlations=["DXY (invers)", "USDJPY", "US-Realzinsen (invers)", "VIX"],
        session_notes="Höchste Liquidität in London/NY Overlap (14:00-17:00 CET). Vorsicht bei FOMC.",
        geopolitical_factors=["Geopolitische Krisen", "Inflation", "Zentralbank-Gold-Käufe", "USD-Stärke"],
        typical_volatility="Mittel (ATR 1.5-2.5%)",
        best_trading_hours="14:00-20:00 CET",
        avoid_conditions=["FOMC-Tage", "NFP-Release", "Extreme DXY-Bewegungen"]
    ),
    "SILVER": AssetIntelligence(
        asset="SILVER",
        category="Edelmetalle",
        key_correlations=["GOLD", "DXY (invers)", "Industrienachfrage"],
        session_notes="Volatiler als Gold. Oft Übertreibungen, dann Mean Reversion.",
        geopolitical_factors=["Industrielle Nachfrage", "Solar-Sektor", "Inflation"],
        typical_volatility="Hoch (ATR 2.5-4%)",
        best_trading_hours="14:00-20:00 CET",
        avoid_conditions=["Dünne Märkte", "Holiday-Trading"]
    ),
    
    # ENERGIE
    "WTI_CRUDE": AssetIntelligence(
        asset="WTI_CRUDE",
        category="Energie",
        key_correlations=["BRENT_CRUDE", "DXY (invers)", "CAD-Pairs", "US-Lagerbestände"],
        session_notes="EIA-Report Mittwoch 16:30 CET verursacht heftige Moves.",
        geopolitical_factors=["OPEC-Entscheidungen", "US-Schieferöl", "Geopolitik Nahost", "China-Nachfrage"],
        typical_volatility="Sehr hoch (ATR 3-5%)",
        best_trading_hours="15:00-21:00 CET",
        avoid_conditions=["EIA-Report Tag ohne Absicherung", "OPEC-Meetings"]
    ),
    "BRENT_CRUDE": AssetIntelligence(
        asset="BRENT_CRUDE",
        category="Energie",
        key_correlations=["WTI_CRUDE", "DXY (invers)", "EUR-Wirtschaft"],
        session_notes="Brent/WTI Spread beachten. Spread > $5 = Anomalie.",
        geopolitical_factors=["Nordseevolatilität", "EU-Nachfrage", "Russland-Sanktionen"],
        typical_volatility="Hoch (ATR 2.5-4%)",
        best_trading_hours="09:00-20:00 CET",
        avoid_conditions=["Extrem niedriger Spread zu WTI"]
    ),
    "NATURAL_GAS": AssetIntelligence(
        asset="NATURAL_GAS",
        category="Energie",
        key_correlations=["Wetter-Forecasts", "US-Lagerbestände", "LNG-Export"],
        session_notes="Extremst volatil! Nur mit engen SL handeln.",
        geopolitical_factors=["Wetter USA", "LNG-Nachfrage EU", "Russland-Gasfluss"],
        typical_volatility="Extrem (ATR 5-10%)",
        best_trading_hours="15:00-20:00 CET",
        avoid_conditions=["Winter-Stürme", "Extrem-Wetter-Events"]
    ),
    
    # FOREX - MAJORS
    "EURUSD": AssetIntelligence(
        asset="EURUSD",
        category="Forex",
        key_correlations=["DXY (invers)", "EUR/GBP", "DE-US Zinsdifferenz"],
        session_notes="Liquideste Pair. London-Session (09:00-17:00) optimal.",
        geopolitical_factors=["EZB-Politik", "Fed-Politik", "EU-Wirtschaft", "US-Daten"],
        typical_volatility="Niedrig-Mittel (ATR 0.5-1%)",
        best_trading_hours="09:00-17:00 CET",
        avoid_conditions=["Gleichzeitige EZB+Fed Events", "NFP ohne Absicherung"]
    ),
    "USDJPY": AssetIntelligence(
        asset="USDJPY",
        category="Forex",
        key_correlations=["US-Renditen", "Nikkei225", "Risk-On/Off Sentiment", "BOJ-Politik"],
        session_notes="Safe-Haven Pair! Fällt bei Risk-Off. BOJ-Interventionen beachten.",
        geopolitical_factors=["BOJ Yield Curve Control", "US-Renditen", "Japan CPI"],
        typical_volatility="Mittel (ATR 0.7-1.2%)",
        best_trading_hours="01:00-09:00 CET (Asien), 14:00-17:00 CET",
        avoid_conditions=["BOJ-Meetings", "Potenzielle Interventionen über 150"]
    ),
    "GBPUSD": AssetIntelligence(
        asset="GBPUSD",
        category="Forex",
        key_correlations=["EURUSD", "UK-Wirtschaftsdaten", "BOE-Politik"],
        session_notes="London-Session dominant. Kann bei UK-News sehr volatil sein.",
        geopolitical_factors=["BOE-Zinsen", "UK-Inflation", "Brexit-Nachwirkungen"],
        typical_volatility="Mittel-Hoch (ATR 0.8-1.5%)",
        best_trading_hours="09:00-17:00 CET",
        avoid_conditions=["BOE Super Thursday", "UK GDP/CPI Release"]
    ),
    
    # INDIZES
    "SP500": AssetIntelligence(
        asset="SP500",
        category="Indizes",
        key_correlations=["VIX (invers)", "NASDAQ100", "US-Renditen", "Fed-Politik"],
        session_notes="US-Session (15:30-22:00 CET). Futures handeln fast 24h.",
        geopolitical_factors=["Fed-Politik", "US-Earnings", "Makro-Daten", "Geopolitik"],
        typical_volatility="Mittel (ATR 1-2%)",
        best_trading_hours="15:30-20:00 CET",
        avoid_conditions=["FOMC-Tag", "Große Tech-Earnings"]
    ),
    "DAX40": AssetIntelligence(
        asset="DAX40",
        category="Indizes",
        key_correlations=["EUROSTOXX50", "US-Futures", "EUR/USD"],
        session_notes="EU-Session (09:00-17:30). Oft Gap-Close nach US-Bewegung.",
        geopolitical_factors=["EZB-Politik", "DE-Wirtschaft", "China-Export"],
        typical_volatility="Mittel-Hoch (ATR 1.5-2.5%)",
        best_trading_hours="09:00-17:30 CET",
        avoid_conditions=["17:00 CET (künstliche Volatilität)", "US-Session-Start"]
    ),
    "NASDAQ100": AssetIntelligence(
        asset="NASDAQ100",
        category="Indizes",
        key_correlations=["SP500", "US-Renditen (invers bei Tech)", "VIX"],
        session_notes="Tech-Heavy. Reagiert stark auf Zinsen und Big-Tech-News.",
        geopolitical_factors=["Tech-Regulierung", "Zinsen", "AI-Hype/Crash"],
        typical_volatility="Hoch (ATR 1.5-3%)",
        best_trading_hours="15:30-20:00 CET",
        avoid_conditions=["Big Tech Earnings", "Fed Hawkish Überraschungen"]
    ),
    
    # CRYPTO
    "BITCOIN": AssetIntelligence(
        asset="BITCOIN",
        category="Crypto",
        key_correlations=["ETHEREUM", "Nasdaq100 (seit 2020)", "Risk-On Sentiment", "DXY (invers)"],
        session_notes="24/7 aber höchste Liquidität in US-Session. Weekend-Dumps möglich!",
        geopolitical_factors=["Regulierung", "ETF-Flows", "Halving-Cycle", "Whale-Movements"],
        typical_volatility="Sehr hoch (ATR 3-8%)",
        best_trading_hours="15:00-22:00 CET (US-Session)",
        avoid_conditions=["Weekend ohne SL", "Kurz vor Halving", "Regulatory FUD"]
    ),
    "ETHEREUM": AssetIntelligence(
        asset="ETHEREUM",
        category="Crypto",
        key_correlations=["BITCOIN", "DeFi-Sentiment", "Gas-Fees"],
        session_notes="Folgt meist BTC, kann aber bei ETH-spezifischen News abweichen.",
        geopolitical_factors=["Ethereum Upgrades", "DeFi-Markt", "NFT-Hype", "Staking-Yields"],
        typical_volatility="Extrem (ATR 4-10%)",
        best_trading_hours="15:00-22:00 CET",
        avoid_conditions=["Major Upgrade Days", "BTC-Dump ohne ETH-News"]
    ),
    
    # AGRAR
    "WHEAT": AssetIntelligence(
        asset="WHEAT",
        category="Agrar",
        key_correlations=["CORN", "Wetter Midwest USA", "Ukraine-Export"],
        session_notes="CBOT-Session (15:30-20:00 CET). USDA-Reports beachten!",
        geopolitical_factors=["Ukraine-Krieg", "Wetter", "USDA WASDE Report", "Export-Bans"],
        typical_volatility="Hoch (ATR 2-4%)",
        best_trading_hours="15:30-19:00 CET",
        avoid_conditions=["USDA Report Tag", "Extrem-Wetter Events"]
    ),
    "COFFEE": AssetIntelligence(
        asset="COFFEE",
        category="Agrar",
        key_correlations=["BRL (Brasilien)", "Wetter Brasilien/Vietnam"],
        session_notes="ICE-Session. Frost in Brasilien = massive Spikes!",
        geopolitical_factors=["Brasilien Wetter", "Vietnam Ernte", "BRL-Kurs"],
        typical_volatility="Sehr hoch (ATR 3-6%)",
        best_trading_hours="15:00-19:00 CET",
        avoid_conditions=["Brasilien Frost-Saison ohne Hedge"]
    )
}

# Default für nicht-spezifizierte Assets
DEFAULT_ASSET_INTELLIGENCE = AssetIntelligence(
    asset="DEFAULT",
    category="Unknown",
    key_correlations=["DXY", "Risk Sentiment"],
    session_notes="Keine spezifischen Informationen verfügbar.",
    geopolitical_factors=["Allgemeine Marktbedingungen"],
    typical_volatility="Unbekannt",
    best_trading_hours="Haupthandelszeiten",
    avoid_conditions=["Major News Events"]
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. HISTORICAL FEASIBILITY ANALYZER
# ═══════════════════════════════════════════════════════════════════════════

class HistoricalFeasibilityAnalyzer:
    """
    Analysiert ob ein Trade-Ziel historisch machbar ist.
    Prüft die letzten 48h Daten gegen das geplante TP.
    """
    
    def __init__(self):
        self.anomaly_threshold = 2.0  # Standardabweichungen für Anomalie
    
    def analyze(
        self,
        asset: str,
        current_price: float,
        target_price: float,
        historical_data: List[Dict],  # OHLCV Daten
        direction: str = "BUY"  # BUY oder SELL
    ) -> HistoricalContext:
        """
        Analysiert die historische Machbarkeit eines Trade-Ziels.
        
        Args:
            asset: Asset-ID (z.B. "GOLD")
            current_price: Aktueller Preis
            target_price: Geplantes Take-Profit
            historical_data: Liste von OHLCV Daten (mind. 48h)
            direction: Trade-Richtung
            
        Returns:
            HistoricalContext mit Analyse-Ergebnissen
        """
        if not historical_data or len(historical_data) < 10:
            logger.warning(f"Nicht genug historische Daten für {asset}")
            return self._create_default_context(asset, current_price, target_price)
        
        # Extrahiere Preisdaten
        highs = [d.get('high', d.get('close', 0)) for d in historical_data]
        lows = [d.get('low', d.get('close', 0)) for d in historical_data]
        closes = [d.get('close', 0) for d in historical_data]
        
        # Berechne Statistiken
        last_48h_high = max(highs) if highs else current_price
        last_48h_low = min(lows) if lows else current_price
        last_48h_avg = np.mean(closes) if closes else current_price
        
        # ATR Berechnung (True Range)
        true_ranges = []
        for i in range(1, len(historical_data)):
            high = highs[i]
            low = lows[i]
            prev_close = closes[i-1]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            true_ranges.append(tr)
        
        atr = np.mean(true_ranges) if true_ranges else 0
        atr_percentage = (atr / current_price * 100) if current_price > 0 else 0
        
        # Volatilität
        volatility_std = np.std(closes) if closes else 0
        price_range = last_48h_high - last_48h_low
        
        # Ist das Ziel im 48h-Bereich?
        if direction == "BUY":
            target_in_range = target_price <= last_48h_high
        else:  # SELL
            target_in_range = target_price >= last_48h_low
        
        # Statistische Anomalie prüfen
        price_distance = abs(target_price - current_price)
        expected_move = atr * 2  # 2x ATR als erwartete Bewegung
        statistical_anomaly = price_distance > (expected_move * self.anomaly_threshold)
        
        return HistoricalContext(
            asset=asset,
            last_48h_high=last_48h_high,
            last_48h_low=last_48h_low,
            last_48h_avg=last_48h_avg,
            atr=atr,
            atr_percentage=atr_percentage,
            volatility_std=volatility_std,
            price_range=price_range,
            current_price=current_price,
            target_in_range=target_in_range,
            statistical_anomaly=statistical_anomaly
        )
    
    def _create_default_context(self, asset: str, current_price: float, target_price: float) -> HistoricalContext:
        """Erstellt Default-Kontext wenn keine Daten verfügbar"""
        return HistoricalContext(
            asset=asset,
            last_48h_high=current_price * 1.02,
            last_48h_low=current_price * 0.98,
            last_48h_avg=current_price,
            atr=current_price * 0.01,
            atr_percentage=1.0,
            volatility_std=current_price * 0.005,
            price_range=current_price * 0.04,
            current_price=current_price,
            target_in_range=True,
            statistical_anomaly=False
        )
    
    def calculate_feasibility_score(self, context: HistoricalContext, target_price: float, direction: str) -> float:
        """
        Berechnet einen Machbarkeits-Score von 0-100.
        
        100 = Ziel sehr wahrscheinlich erreichbar
        0 = Ziel praktisch unmöglich
        """
        score = 100.0
        
        # Abzug wenn Ziel außerhalb des 48h-Bereichs
        if not context.target_in_range:
            score -= 30
        
        # Abzug für statistische Anomalie
        if context.statistical_anomaly:
            score -= 40
        
        # Bonus wenn Ziel nah am aktuellen Preis
        distance_pct = abs(target_price - context.current_price) / context.current_price * 100
        if distance_pct < context.atr_percentage:
            score += 10
        elif distance_pct > context.atr_percentage * 3:
            score -= 20
        
        # Volatilitäts-Anpassung
        if context.atr_percentage < 0.5:
            score -= 10  # Niedrige Volatilität = schwer TP zu erreichen
        elif context.atr_percentage > 3:
            score -= 15  # Zu hohe Volatilität = Risiko
        
        return max(0, min(100, score))


# ═══════════════════════════════════════════════════════════════════════════
# 2. STRATEGIC REASONING ENGINE (ADVOCATUS DIABOLI)
# ═══════════════════════════════════════════════════════════════════════════

class StrategicReasoningEngine:
    """
    Führt eine interne Debatte: Pro vs. Contra.
    Der Trade wird nur freigegeben wenn Pro-Argumente gewinnen.
    """
    
    def __init__(self, ollama_base_url: str = "http://127.0.0.1:11434", model: str = "llama3:latest"):
        self.ollama_base_url = ollama_base_url
        self.model = model
        self.timeout = aiohttp.ClientTimeout(total=30)
    
    async def _call_ollama(self, prompt: str) -> Optional[str]:
        """Ruft Ollama API auf"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {
                        "temperature": 0.4,
                        "num_predict": 800
                    }
                }
                
                async with session.post(
                    f"{self.ollama_base_url}/api/chat",
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('message', {}).get('content', '')
                    else:
                        logger.warning(f"Ollama Status {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Ollama Fehler: {e}")
            return None
    
    async def generate_contra_arguments(
        self,
        signal_data: Dict,
        historical_context: HistoricalContext,
        asset_intel: AssetIntelligence
    ) -> List[str]:
        """
        Generiert 3 Contra-Argumente (Advocatus Diaboli).
        """
        prompt = f"""Du bist ein skeptischer Trading-Analyst (Advocatus Diaboli).
Deine Aufgabe: Finde 3 GRÜNDE warum dieser Trade SCHEITERN könnte.

TRADE-SIGNAL:
- Asset: {signal_data.get('asset', 'Unknown')}
- Richtung: {signal_data.get('direction', 'BUY')}
- Einstieg: {signal_data.get('entry_price', 0)}
- Take Profit: {signal_data.get('take_profit', 0)}
- Stop Loss: {signal_data.get('stop_loss', 0)}
- Strategie: {signal_data.get('strategy', 'Unknown')}
- Confidence: {signal_data.get('confidence', 0)}%

HISTORISCHE DATEN (48h):
- Hoch: {historical_context.last_48h_high}
- Tief: {historical_context.last_48h_low}
- ATR: {historical_context.atr_percentage:.2f}%
- Ziel im Bereich: {'Ja' if historical_context.target_in_range else 'NEIN - AUSSERHALB!'}
- Statistische Anomalie: {'JA - WARNUNG!' if historical_context.statistical_anomaly else 'Nein'}

ASSET-KONTEXT:
- Kategorie: {asset_intel.category}
- Korrelationen: {', '.join(asset_intel.key_correlations)}
- Zu vermeiden: {', '.join(asset_intel.avoid_conditions)}

Antworte mit GENAU 3 kurzen Contra-Argumenten im Format:
1. [Argument 1]
2. [Argument 2]
3. [Argument 3]
"""
        
        response = await self._call_ollama(prompt)
        
        if response:
            # Parse Argumente
            lines = [l.strip() for l in response.split('\n') if l.strip()]
            arguments = []
            for line in lines:
                if line[0].isdigit() and '.' in line[:3]:
                    arg = line.split('.', 1)[-1].strip()
                    if arg:
                        arguments.append(arg)
            return arguments[:3] if arguments else self._fallback_contra(signal_data, historical_context)
        
        return self._fallback_contra(signal_data, historical_context)
    
    def _fallback_contra(self, signal_data: Dict, context: HistoricalContext) -> List[str]:
        """Fallback Contra-Argumente ohne Ollama"""
        contras = []
        
        if not context.target_in_range:
            contras.append(f"TP liegt außerhalb des 48h-Bereichs (Max: {context.last_48h_high:.2f})")
        
        if context.statistical_anomaly:
            contras.append("Ziel ist eine statistische Anomalie (>2 Std-Abweichungen)")
        
        if context.atr_percentage > 3:
            contras.append(f"Hohe Volatilität ({context.atr_percentage:.1f}% ATR) erhöht SL-Risiko")
        
        if signal_data.get('confidence', 0) < 70:
            contras.append(f"Signal-Confidence nur {signal_data.get('confidence', 0)}% (unter 70%)")
        
        # Fülle auf 3 Argumente
        while len(contras) < 3:
            contras.append("Allgemeines Marktrisiko und unvorhergesehene Events")
        
        return contras[:3]
    
    async def generate_pro_arguments(
        self,
        signal_data: Dict,
        historical_context: HistoricalContext,
        asset_intel: AssetIntelligence
    ) -> List[str]:
        """
        Generiert Pro-Argumente für den Trade.
        """
        prompt = f"""Du bist ein optimistischer Trading-Analyst.
Deine Aufgabe: Finde 3 GRÜNDE warum dieser Trade ERFOLGREICH sein könnte.

TRADE-SIGNAL:
- Asset: {signal_data.get('asset', 'Unknown')}
- Richtung: {signal_data.get('direction', 'BUY')}
- Einstieg: {signal_data.get('entry_price', 0)}
- Take Profit: {signal_data.get('take_profit', 0)}
- Strategie: {signal_data.get('strategy', 'Unknown')}
- Confidence: {signal_data.get('confidence', 0)}%

HISTORISCHE DATEN:
- ATR: {historical_context.atr_percentage:.2f}%
- Preis-Range: {historical_context.price_range:.2f}

ASSET-STÄRKEN:
- Beste Handelszeiten: {asset_intel.best_trading_hours}
- Typische Volatilität: {asset_intel.typical_volatility}

Antworte mit GENAU 3 kurzen Pro-Argumenten im Format:
1. [Argument 1]
2. [Argument 2]
3. [Argument 3]
"""
        
        response = await self._call_ollama(prompt)
        
        if response:
            lines = [l.strip() for l in response.split('\n') if l.strip()]
            arguments = []
            for line in lines:
                if line[0].isdigit() and '.' in line[:3]:
                    arg = line.split('.', 1)[-1].strip()
                    if arg:
                        arguments.append(arg)
            return arguments[:3] if arguments else self._fallback_pro(signal_data, historical_context)
        
        return self._fallback_pro(signal_data, historical_context)
    
    def _fallback_pro(self, signal_data: Dict, context: HistoricalContext) -> List[str]:
        """Fallback Pro-Argumente ohne Ollama"""
        pros = []
        
        if context.target_in_range:
            pros.append("Ziel liegt innerhalb des 48h-Preisbereichs")
        
        if signal_data.get('confidence', 0) >= 75:
            pros.append(f"Starkes Signal mit {signal_data.get('confidence', 0)}% Confidence")
        
        if not context.statistical_anomaly:
            pros.append("Ziel ist statistisch realistisch (keine Anomalie)")
        
        if context.atr_percentage < 2.5:
            pros.append(f"Moderate Volatilität ({context.atr_percentage:.1f}%) für kontrolliertes Risiko")
        
        while len(pros) < 3:
            pros.append("Technische Indikatoren unterstützen die Richtung")
        
        return pros[:3]
    
    def weigh_arguments(
        self,
        pro_arguments: List[str],
        contra_arguments: List[str],
        historical_context: HistoricalContext,
        signal_confidence: float
    ) -> Tuple[bool, str, int]:
        """
        Gewichtet Pro vs. Contra Argumente.
        
        Returns:
            (approved, reasoning, confidence)
        """
        # Basis-Gewichtung
        pro_weight = len(pro_arguments) * 10 + signal_confidence * 0.5
        contra_weight = len(contra_arguments) * 10
        
        # Kritische Faktoren
        if not historical_context.target_in_range:
            contra_weight += 30
        
        if historical_context.statistical_anomaly:
            contra_weight += 40
        
        if signal_confidence >= 80:
            pro_weight += 20
        elif signal_confidence < 65:
            contra_weight += 15
        
        # Entscheidung
        net_score = pro_weight - contra_weight
        approved = net_score > 0
        
        confidence = min(100, max(0, int(50 + net_score)))
        
        reasoning = f"Pro-Gewicht: {pro_weight:.0f}, Contra-Gewicht: {contra_weight:.0f}, Netto: {net_score:.0f}"
        
        return approved, reasoning, confidence


# ═══════════════════════════════════════════════════════════════════════════
# 3. COGNITIVE VALIDATION PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

class CognitiveValidationPipeline:
    """
    Dreistufige kognitive Validierung:
    1. Sicherheits-Check (hart)
    2. Historische Machbarkeits-Analyse
    3. Strategisches Reasoning (Ollama)
    """
    
    def __init__(self, ollama_base_url: str = "http://127.0.0.1:11434", model: str = "llama3:latest"):
        self.feasibility_analyzer = HistoricalFeasibilityAnalyzer()
        self.reasoning_engine = StrategicReasoningEngine(ollama_base_url, model)
        self.ollama_base_url = ollama_base_url
        self.model = model
    
    def get_asset_intelligence(self, asset: str) -> AssetIntelligence:
        """Holt Asset-spezifisches Wissen"""
        return ASSET_INTELLIGENCE_DB.get(asset, DEFAULT_ASSET_INTELLIGENCE)
    
    async def validate_trade(
        self,
        signal_data: Dict,
        historical_data: List[Dict],
        current_portfolio_risk: float = 0.0,
        max_portfolio_risk: float = 20.0
    ) -> CognitiveDecision:
        """
        Führt die vollständige kognitive Validierung durch.
        
        Args:
            signal_data: {asset, direction, entry_price, take_profit, stop_loss, strategy, confidence}
            historical_data: OHLCV Daten der letzten 48h
            current_portfolio_risk: Aktuelles Portfolio-Risiko in %
            max_portfolio_risk: Maximales erlaubtes Risiko
            
        Returns:
            CognitiveDecision mit GO/VETO und Begründung
        """
        asset = signal_data.get('asset', 'Unknown')
        direction = signal_data.get('direction', 'BUY')
        entry_price = signal_data.get('entry_price', 0)
        target_price = signal_data.get('take_profit', 0)
        confidence = signal_data.get('confidence', 0)
        
        logger.info(f"🧠 Kognitive Validierung für {asset} {direction}...")
        
        # ═══════════════════════════════════════════════════════════════════
        # STUFE 1: SICHERHEITS-CHECK (HART)
        # ═══════════════════════════════════════════════════════════════════
        if current_portfolio_risk >= max_portfolio_risk:
            logger.warning(f"⛔ VETO: Portfolio-Risiko {current_portfolio_risk:.1f}% >= {max_portfolio_risk}%")
            return CognitiveDecision(
                decision="VETO",
                confidence=100,
                reasoning=f"Portfolio-Risiko zu hoch: {current_portfolio_risk:.1f}% >= {max_portfolio_risk}%",
                historical_feasibility=0,
                pro_arguments=[],
                contra_arguments=["Portfolio-Risiko-Limit erreicht"],
                risk_assessment="KRITISCH - Keine neuen Trades erlaubt"
            )
        
        # ═══════════════════════════════════════════════════════════════════
        # STUFE 2: HISTORISCHE MACHBARKEITS-ANALYSE
        # ═══════════════════════════════════════════════════════════════════
        hist_context = self.feasibility_analyzer.analyze(
            asset=asset,
            current_price=entry_price,
            target_price=target_price,
            historical_data=historical_data,
            direction=direction
        )
        
        feasibility_score = self.feasibility_analyzer.calculate_feasibility_score(
            hist_context, target_price, direction
        )
        
        logger.info(f"📊 Historische Machbarkeit: {feasibility_score:.0f}%")
        logger.info(f"   48h-Range: {hist_context.last_48h_low:.2f} - {hist_context.last_48h_high:.2f}")
        logger.info(f"   Ziel im Bereich: {hist_context.target_in_range}")
        logger.info(f"   Anomalie: {hist_context.statistical_anomaly}")
        
        # Sofortiges VETO bei sehr niedriger Machbarkeit
        if feasibility_score < 30:
            logger.warning(f"⛔ VETO: Machbarkeit nur {feasibility_score:.0f}%")
            return CognitiveDecision(
                decision="VETO",
                confidence=int(100 - feasibility_score),
                reasoning=f"Historische Machbarkeit zu niedrig: {feasibility_score:.0f}%",
                historical_feasibility=feasibility_score,
                pro_arguments=[],
                contra_arguments=[
                    "Ziel liegt außerhalb des historischen Bereichs",
                    "Statistische Anomalie erkannt",
                    "Unwahrscheinliche Kursbewegung erforderlich"
                ],
                risk_assessment="HOCH - Ziel nicht realistisch"
            )
        
        # ═══════════════════════════════════════════════════════════════════
        # STUFE 3: STRATEGISCHES REASONING (OLLAMA)
        # ═══════════════════════════════════════════════════════════════════
        asset_intel = self.get_asset_intelligence(asset)
        
        # Generiere Pro und Contra parallel
        contra_task = self.reasoning_engine.generate_contra_arguments(
            signal_data, hist_context, asset_intel
        )
        pro_task = self.reasoning_engine.generate_pro_arguments(
            signal_data, hist_context, asset_intel
        )
        
        contra_arguments, pro_arguments = await asyncio.gather(contra_task, pro_task)
        
        logger.info(f"✅ Pro-Argumente: {pro_arguments}")
        logger.info(f"❌ Contra-Argumente: {contra_arguments}")
        
        # Gewichtung
        approved, reasoning, final_confidence = self.reasoning_engine.weigh_arguments(
            pro_arguments, contra_arguments, hist_context, confidence
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # FINALE ENTSCHEIDUNG
        # ═══════════════════════════════════════════════════════════════════
        decision = "GO" if approved else "VETO"
        
        # Risiko-Bewertung
        if feasibility_score >= 70 and approved:
            risk_assessment = "NIEDRIG - Trade empfohlen"
        elif feasibility_score >= 50 and approved:
            risk_assessment = "MITTEL - Trade mit Vorsicht"
        elif approved:
            risk_assessment = "ERHÖHT - Enges Risiko-Management erforderlich"
        else:
            risk_assessment = "HOCH - Trade nicht empfohlen"
        
        # Ziel-Korrektur wenn nötig
        adjusted_tp = None
        if not hist_context.target_in_range and approved:
            if direction == "BUY":
                adjusted_tp = hist_context.last_48h_high * 0.99  # 1% unter Max
            else:
                adjusted_tp = hist_context.last_48h_low * 1.01  # 1% über Min
            logger.info(f"📐 TP korrigiert: {target_price} → {adjusted_tp:.2f}")
        
        result = CognitiveDecision(
            decision=decision,
            confidence=final_confidence,
            reasoning=reasoning,
            historical_feasibility=feasibility_score,
            pro_arguments=pro_arguments,
            contra_arguments=contra_arguments,
            risk_assessment=risk_assessment,
            adjusted_tp=adjusted_tp
        )
        
        logger.info(f"🧠 ENTSCHEIDUNG: {decision} (Confidence: {final_confidence}%)")
        logger.info(f"   Begründung: {reasoning}")
        
        return result
    
    async def quick_validate(
        self,
        signal_data: Dict,
        current_price: float,
        target_price: float,
        direction: str = "BUY"
    ) -> Dict:
        """
        Schnelle Validierung ohne vollständige Ollama-Analyse.
        Für hohe Frequenz oder wenn Ollama nicht verfügbar.
        """
        # Einfache Machbarkeits-Prüfung
        asset = signal_data.get('asset', 'Unknown')
        confidence = signal_data.get('confidence', 0)
        
        # Basis-Checks
        price_distance_pct = abs(target_price - current_price) / current_price * 100
        
        if price_distance_pct > 5:
            return {
                "decision": "VETO",
                "reason": f"Ziel-Distanz zu groß: {price_distance_pct:.1f}%"
            }
        
        if confidence < 60:
            return {
                "decision": "VETO",
                "reason": f"Confidence zu niedrig: {confidence}%"
            }
        
        return {
            "decision": "GO",
            "reason": f"Basis-Checks bestanden (Confidence: {confidence}%)"
        }


# ═══════════════════════════════════════════════════════════════════════════
# 4. TRADE INTELLIGENCE VALIDATOR (HAUPTFUNKTION)
# ═══════════════════════════════════════════════════════════════════════════

async def validate_trade_with_intelligence(
    signal_data: Dict,
    historical_df_or_list,
    portfolio_risk: float = 0.0,
    ollama_url: str = "http://127.0.0.1:11434",
    ollama_model: str = "llama3:latest"
) -> Dict:
    """
    Hauptfunktion für kognitive Trade-Validierung.
    
    Diese Funktion bereitet die Daten für Ollama vor, damit die KI 
    einen historischen und logischen Abgleich machen kann.
    
    Args:
        signal_data: Dict mit {asset, direction, entry_price, take_profit, stop_loss, strategy, confidence}
        historical_df_or_list: Pandas DataFrame oder Liste von OHLCV Dicts
        portfolio_risk: Aktuelles Portfolio-Risiko in %
        ollama_url: Ollama Server URL
        ollama_model: Ollama Modell Name
        
    Returns:
        Dict mit {decision, reasoning, confidence, ...}
    """
    # Konvertiere DataFrame zu Liste falls nötig
    if hasattr(historical_df_or_list, 'to_dict'):
        historical_data = historical_df_or_list.to_dict('records')
    elif isinstance(historical_df_or_list, list):
        historical_data = historical_df_or_list
    else:
        historical_data = []
    
    # Pipeline initialisieren
    pipeline = CognitiveValidationPipeline(ollama_url, ollama_model)
    
    # Validierung durchführen
    result = await pipeline.validate_trade(
        signal_data=signal_data,
        historical_data=historical_data,
        current_portfolio_risk=portfolio_risk
    )
    
    # Als Dict zurückgeben
    return {
        "decision": result.decision,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
        "historical_feasibility": result.historical_feasibility,
        "pro_arguments": result.pro_arguments,
        "contra_arguments": result.contra_arguments,
        "risk_assessment": result.risk_assessment,
        "adjusted_tp": result.adjusted_tp,
        "adjusted_sl": result.adjusted_sl,
        "timestamp": result.timestamp
    }


# ═══════════════════════════════════════════════════════════════════════════
# 5. LOGGING & FEEDBACK
# ═══════════════════════════════════════════════════════════════════════════

async def log_cognitive_decision(decision_result: Dict, log_file: str = "/app/backend/trade_logic_log.md"):
    """
    Loggt die kognitive Entscheidung für Nachverfolgbarkeit.
    """
    import os
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry = f"""
## {timestamp} - {decision_result.get('decision', 'UNKNOWN')}

**Asset:** {decision_result.get('asset', 'N/A')}
**Confidence:** {decision_result.get('confidence', 0)}%
**Historische Machbarkeit:** {decision_result.get('historical_feasibility', 0)}%

### Begründung
{decision_result.get('reasoning', 'Keine Begründung')}

### Risk Assessment
{decision_result.get('risk_assessment', 'N/A')}

### Pro-Argumente
{chr(10).join(['- ' + a for a in decision_result.get('pro_arguments', [])])}

### Contra-Argumente
{chr(10).join(['- ' + a for a in decision_result.get('contra_arguments', [])])}

---
"""
    
    try:
        mode = 'a' if os.path.exists(log_file) else 'w'
        with open(log_file, mode) as f:
            if mode == 'w':
                f.write("# Trade Logic Log - Cognitive Decisions\n\n")
            f.write(log_entry)
        logger.info(f"📝 Decision logged to {log_file}")
    except Exception as e:
        logger.error(f"Failed to log decision: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════

__all__ = [
    'CognitiveValidationPipeline',
    'HistoricalFeasibilityAnalyzer',
    'StrategicReasoningEngine',
    'CognitiveDecision',
    'HistoricalContext',
    'AssetIntelligence',
    'ASSET_INTELLIGENCE_DB',
    'validate_trade_with_intelligence',
    'log_cognitive_decision'
]
