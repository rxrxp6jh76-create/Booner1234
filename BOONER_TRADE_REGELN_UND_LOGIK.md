# 🤖 Booner Trade v2.3.29 - Regeln & Logik Dokumentation

## Inhaltsverzeichnis
1. [Trading-Strategien](#1-trading-strategien)
2. [Portfolio-Risiko-Management](#2-portfolio-risiko-management)
3. [Lot-Größen-Berechnung](#3-lot-größen-berechnung)
4. [Position-Limits](#4-position-limits)
5. [Auto-Close Funktionen](#5-auto-close-funktionen)
6. [Peak-Profit Tracking](#6-peak-profit-tracking)
7. [Risk Circuits (Automatische Schließung)](#7-risk-circuits)
8. [Markt-Regime Erkennung](#8-markt-regime-erkennung)
9. [Filter & Checks](#9-filter--checks)
10. [Handelszeiten](#10-handelszeiten)
11. [News-Filter](#11-news-filter)
12. [Trading-Modi](#12-trading-modi)

---

## 1. Trading-Strategien

### 7 verfügbare Strategien:

| Strategie | Priorität | Kategorie | Beschreibung |
|-----------|-----------|-----------|--------------|
| **Momentum** | 100 (höchste) | Intraday | Folgt starken Kursbewegungen |
| **Swing Trading** | 95 | Multi-Day | Nutzt größere Marktbewegungen über Tage |
| **Breakout** | 80 | Multi-Day | Handelt Ausbrüche aus Ranges |
| **Day Trading** | 70 | Intraday | Klassisches Tageshandeln |
| **Mean Reversion** | 60 | Intraday | Handelt Rückkehr zum Mittelwert |
| **Scalping** | 50 | Intraday | Sehr kurze Trades, kleine Gewinne |
| **Grid** | 40 (niedrigste) | Multi-Day | Automatisches Grid-Trading |

### Strategie-Kategorien:

**Intraday-Strategien** (werden täglich vor Handelsschluss geschlossen):
- `day_trading`, `scalping`, `momentum`, `mean_reversion`

**Multi-Day-Strategien** (laufen über mehrere Tage):
- `swing_trading`, `grid`, `breakout`

---

## 2. Portfolio-Risiko-Management

### Kernregel: **MAX 20% Portfolio-Risiko**

```
MAX_PORTFOLIO_RISK = 20.0%
```

**Berechnung:**
```
Portfolio-Risiko (%) = (Margin Used / Balance) × 100
```

**Wenn Portfolio-Risiko ≥ 20%:**
- ⛔ KEINE neuen Trades werden eröffnet
- ⚠️ Warnung wird im Dashboard angezeigt
- ✅ Bestehende Trades bleiben offen

**Beispiel:**
- Balance: €1.000
- Max Margin erlaubt: €200 (20%)
- Bei 6 geplanten Positionen: €33 pro Trade (~3.3%)

---

## 3. Lot-Größen-Berechnung

### V3.3.1 Korrigierte Formel:

```python
# Schritt 1: Verfügbares Risiko berechnen
MAX_POSITIONS_PLANNED = 6
remaining_risk = MAX_PORTFOLIO_RISK - current_risk
risk_per_trade = remaining_risk / max(1, MAX_POSITIONS_PLANNED - len(positions))

# Schritt 2: Risiko-Betrag
risk_amount = balance * (risk_per_trade / 100)

# Schritt 3: Lot-Size mit Sicherheitslimits
```

### Balance-basierte Lot-Limits:

| Balance | Max Lot |
|---------|---------|
| < €500 | 0.01 |
| €500 - €1.000 | 0.02 |
| €1.000 - €2.000 | 0.05 |
| €2.000 - €5.000 | 0.10 |
| €5.000 - €10.000 | 0.20 |
| €10.000 - €50.000 | 0.50 |
| > €50.000 | 1.00 |

### Trading-Modus abhängige Risiko-Stufen:

**KONSERVATIV** (Threshold 75%+):
- Signal 75-80%: 0.5% Risiko
- Signal 80-88%: 0.75% Risiko
- Signal >88%: 1.0% Risiko (Max!)
- Max Lot: 1.5

**NEUTRAL** (Threshold 68%+):
- Signal 68-75%: 0.5% Risiko
- Signal 75-85%: 1.0% Risiko
- Signal >85%: 1.5% Risiko
- Max Lot: 2.0

**AGGRESSIV** (Threshold 60%+):
- Signal 60-68%: 1.0% Risiko
- Signal 68-78%: 1.5% Risiko
- Signal >78%: 2.0% Risiko
- Max Lot: 2.5

---

## 4. Position-Limits

### Regeln:

| Limit | Wert | Beschreibung |
|-------|------|--------------|
| **Max Positionen pro Asset** | 1 | Standard: NUR 1 offene Position pro Commodity |
| **Zeit zwischen Trades** | 15 Min | Mindestabstand für gleiches Asset (wenn >1 erlaubt) |
| **Max Gesamt-Positionen** | 50 | Alle Plattformen zusammen |

**Check-Logik:**
```
1. Hat Asset bereits offene Position? → STOP
2. Letzte Position vor <15 Min? → STOP  
3. Mehr als 50 Positionen gesamt? → STOP
4. Sonst → OK, Trade erlaubt
```

---

## 5. Auto-Close Funktionen

### 📅 Tägliches Auto-Close (Mo-Do)
- **Betrifft:** `day_trading`, `scalping`, `momentum`, `mean_reversion`
- **Wann:** 10 Minuten vor Handelsschluss
- **Bedingung:** NUR profitable Trades (Profit > 0)
- **Setting:** `auto_close_profitable_daily = true`

### 🗓️ Freitag Auto-Close (Wochenend-Schutz)
- **Betrifft:** ALLE Strategien inkl. `swing`, `grid`, `breakout`
- **Wann:** 10 Minuten vor Wochenend-Schluss (Fr 21:55 UTC)
- **Bedingung:** NUR profitable Trades
- **Setting:** `auto_close_all_friday = true`

### Logik-Tabelle:

| Strategie | Mo-Do Close | Freitag Close |
|-----------|-------------|---------------|
| day_trading | ✅ | ✅ |
| scalping | ✅ | ✅ |
| momentum | ✅ | ✅ |
| mean_reversion | ✅ | ✅ |
| swing_trading | ❌ | ✅ |
| grid | ❌ | ✅ |
| breakout | ❌ | ✅ |

---

## 6. Peak-Profit Tracking

### Funktionsweise:

```
Peak-Profit = Höchster erreichter Gewinn während der Trade-Laufzeit
```

**Regeln:**
1. Peak wird nur ERHÖHT, nie gesenkt
2. Bei negativem Profit bleibt Peak erhalten
3. Peak wird in DB gespeichert (persistent)
4. Anzeige: Aktueller Profit vs. Peak

**Beispiel:**
```
Zeit    | Profit | Peak
--------|--------|------
10:00   | €10    | €10   (Initial)
10:30   | €50    | €50   (Neuer Peak!)
11:00   | €40    | €50   (Peak bleibt)
11:30   | €20    | €50   (Peak bleibt)
12:00   | -€5    | €50   (Peak bleibt trotz Verlust!)
```

---

## 7. Risk Circuits (Automatische Schließung)

### Profit-Drawdown-Exit (20% vom Peak)

**Bedingungen für Auto-Close:**
1. Trade mindestens 30 Minuten offen
2. Peak-Profit war positiv
3. Aktueller Profit ≤ 80% vom Peak (= 20% Drawdown)

**Formel:**
```
profit_drawdown_ratio = (peak_profit - current_profit) / peak_profit

Wenn profit_drawdown_ratio >= 0.20 → AUTO-CLOSE
```

**Beispiel:**
```
Peak: €100
Aktuell: €75
Drawdown: (100-75)/100 = 25% → AUTO-CLOSE (>20%)
```

### Weitere Risk Circuits:

| Circuit | Beschreibung |
|---------|--------------|
| **Time Exit** | Schließt nach X Stunden ohne Fortschritt |
| **Breakeven** | Bewegt SL auf Entry nach X% Gewinn |
| **Trailing Stop** | Folgt dem Preis in Gewinnrichtung |

---

## 8. Markt-Regime Erkennung

### Erkannte Regimes:

| Regime | Bedingung | Empfohlene Strategie |
|--------|-----------|---------------------|
| **STRONG_TREND_UP** | Preis > EMA, RSI > 60 | Momentum, Swing |
| **STRONG_TREND_DOWN** | Preis < EMA, RSI < 40 | Momentum, Swing |
| **WEAK_TREND** | Leichte Trendrichtung | Day Trading |
| **RANGE_BOUND** | Seitwärts, <1% Std | Mean Reversion, Grid |
| **HIGH_VOLATILITY** | ATR > 2%, Volumen hoch | Breakout |
| **LOW_VOLATILITY** | ATR < 0.5% | Scalping |
| **NEWS_PHASE** | News-Fenster aktiv | KEINE TRADES |

---

## 9. Filter & Checks

### MasterFilter - Alle Checks in Reihenfolge:

```
1. SpreadFilter      → Max Spread-Kosten prüfen
2. SessionFilter     → Ist Markt offen?
3. CorrelationFilter → Korrelierte Assets prüfen
4. MTFFilter         → Multi-Timeframe Bestätigung
5. SmartEntryFilter  → Pullback-Entry prüfen
6. BTCVolatilityFilter → BTC-spezifische Volatilität
7. EURUSDFilter      → DXY-Korrelation prüfen
8. ClusterRiskFilter → Nicht zu viele ähnliche Trades
```

### Spread-Limits nach Asset-Klasse:

| Asset-Klasse | Max Spread (% vom Preis) |
|--------------|--------------------------|
| Major Forex | 0.02% |
| Minor Forex | 0.05% |
| Gold/Silber | 0.03% |
| Crypto | 0.10% |
| Indices | 0.05% |

### Cluster-Risk (Korrelation):

```
Wenn bereits Trade in korrelierter Gruppe → SKIP

Gruppen:
- EUR-Pairs: EURUSD, EURGBP, EURJPY
- USD-Pairs: USDJPY, USDCHF, USDCAD
- Metalle: XAUUSD, XAGUSD
- Crypto: BTCUSD, ETHUSD
```

---

## 10. Handelszeiten

### Market Hours nach Asset:

| Asset | Typ | Öffnung | Schluss |
|-------|-----|---------|---------|
| Forex Major | 24/5 | Mo 22:05 UTC | Fr 21:55 UTC |
| Gold (XAUUSD) | Spezial | Mo 23:00 UTC | Fr 22:00 UTC |
| Bitcoin | 24/7 | - | - |
| US Indices | Börse | 14:30 UTC | 21:00 UTC |
| EU Indices | Börse | 08:00 UTC | 16:30 UTC |

### Wochenend-Regel:

```
Freitag 21:55 UTC → Märkte schließen
Sonntag 22:00 UTC → Märkte öffnen

Kein Trading Sa-So (außer Crypto)
```

---

## 11. News-Filter

### News-Impact Klassifikation:

| Impact | Beschreibung | Aktion |
|--------|--------------|--------|
| **HIGH** | NFP, FOMC, EZB | ⛔ KEINE Trades 30min vorher/nachher |
| **MEDIUM** | CPI, PMI | ⚠️ Vorsicht, reduzierte Lot-Size |
| **LOW** | Kleine Reports | ✅ Normal handeln |

### News-Fenster:

```
News Zeit: 14:30 UTC
Sperrfenster: 14:00 - 15:00 UTC (30min vor + 30min nach)
```

---

## 12. Trading-Modi

### 3 verfügbare Modi:

| Modus | Confidence Threshold | Max Lot | Risiko/Trade |
|-------|---------------------|---------|--------------|
| **Conservative** | 75% | 1.5 | 0.5-1.0% |
| **Neutral** | 68% | 2.0 | 0.5-1.5% |
| **Aggressive** | 60% | 2.5 | 1.0-2.0% |

### Confidence-Score Berechnung (4-Säulen-Modell):

```
Confidence = (Technical + Sentiment + Volume + Pattern) / 4

- Technical: RSI, MACD, EMA Crossover
- Sentiment: News-Analyse, Market Mood
- Volume: Volumen-Bestätigung
- Pattern: Chartmuster-Erkennung
```

---

## Zusammenfassung der wichtigsten Regeln

### ⛔ TRADE WIRD BLOCKIERT wenn:

1. Portfolio-Risiko ≥ 20%
2. Asset hat bereits offene Position
3. Letzte Position vor <15 Min
4. Mehr als 50 Positionen gesamt
5. News-Phase aktiv (High Impact)
6. Markt geschlossen
7. Spread zu hoch
8. Confidence unter Threshold

### ✅ TRADE WIRD AUTOMATISCH GESCHLOSSEN wenn:

1. Profit 20% unter Peak (nach 30min)
2. Auto-Close vor Handelsschluss (Mo-Do für Intraday)
3. Freitag-Close vor Wochenende (alle Strategien)
4. Stop-Loss erreicht
5. Take-Profit erreicht
6. Time-Exit überschritten

### 📊 RISIKO-VERTEILUNG:

```
Max Portfolio-Risiko:     20%
Geplante Positionen:      6
Max Risiko pro Trade:     ~3.3%
Lot-Size pro €1.000:      0.02-0.05
```

---

*Dokumentation erstellt: 01.02.2026*
*Version: Booner Trade v2.3.29 + V3.3.2 Fixes*
