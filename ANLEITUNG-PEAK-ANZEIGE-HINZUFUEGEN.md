# 📋 Anleitung: Peak-Anzeige in der offenen Trade-Liste hinzufügen

**Booner Trade V3.2.9**
**Letzte Aktualisierung:** 6. Januar 2026

---

## Was ist der "Peak"?

Der Peak zeigt den besten Preis, den ein Trade seit der Eröffnung erreicht hat:
- **BUY Trade**: Höchster Preis seit Eröffnung (maximaler Gewinn-Punkt)
- **SELL Trade**: Niedrigster Preis seit Eröffnung (maximaler Gewinn-Punkt)

Dies hilft zu sehen, wie viel Gewinn "verpasst" wurde oder wie nah man am besten Punkt war.

---

## Übersicht der Änderungen

Es sind **2 Dateien** zu ändern:

1. **Backend** (`server.py`) - Peak-Daten berechnen und speichern
2. **Frontend** (`Dashboard.jsx`) - Peak-Spalte in der Tabelle anzeigen

---

## TEIL 1: Backend ändern (Peak-Tracking)

### Datei öffnen:
```
/pfad/zu/Version_3.0.0/backend/server.py
```

### Schritt 1.1: Peak-Speicher hinzufügen

Suchen Sie nach `# Global variables` oder `ai_trading_bot_instance = None` (ca. Zeile 180-200).

Fügen Sie darunter hinzu:

```python
# V3.2.9: Peak-Tracking für offene Trades
# Speichert den höchsten/niedrigsten Preis für jeden Trade
trade_peaks = {}  # Format: {"ticket": {"high": 123.45, "low": 120.00}}
```

### Schritt 1.2: Peak-Update Funktion hinzufügen

Suchen Sie nach `async def update_market_data()` (ca. Zeile 950).

Fügen Sie DAVOR eine neue Funktion ein:

```python
# V3.2.9: Peak-Tracking für offene Trades
async def update_trade_peaks():
    """
    Aktualisiert die Peak-Werte (Hoch/Tief) für alle offenen Trades.
    Wird bei jedem Market-Data-Update aufgerufen.
    """
    global trade_peaks
    
    try:
        from multi_platform_connector import multi_platform
        
        # Hole alle offenen Positionen
        positions = await multi_platform.get_positions()
        
        if not positions:
            return
        
        for pos in positions:
            ticket = str(pos.get('ticket') or pos.get('id', ''))
            current_price = pos.get('currentPrice', 0)
            
            if not ticket or not current_price:
                continue
            
            # Initialisiere Peak wenn nicht vorhanden
            if ticket not in trade_peaks:
                trade_peaks[ticket] = {
                    'high': current_price,
                    'low': current_price,
                    'entry_price': pos.get('openPrice', current_price)
                }
            else:
                # Update High/Low
                if current_price > trade_peaks[ticket]['high']:
                    trade_peaks[ticket]['high'] = current_price
                if current_price < trade_peaks[ticket]['low']:
                    trade_peaks[ticket]['low'] = current_price
        
        # Bereinige alte Tickets (die nicht mehr offen sind)
        open_tickets = {str(pos.get('ticket') or pos.get('id', '')) for pos in positions}
        closed_tickets = [t for t in trade_peaks.keys() if t not in open_tickets]
        for t in closed_tickets:
            del trade_peaks[t]
            
    except Exception as e:
        logger.debug(f"Peak update error: {e}")
```

### Schritt 1.3: Peak-Update aufrufen

Suchen Sie innerhalb der Funktion `update_market_data()` nach der Zeile:
```python
logger.info("Market data processing complete")
```

Fügen Sie DAVOR ein:

```python
        # V3.2.9: Update Peak-Tracking
        await update_trade_peaks()
```

### Schritt 1.4: Peak-Daten im Trade-Endpoint zurückgeben

Suchen Sie nach dem Endpoint `@api_router.get("/trades/list")` (ca. Zeile 2500-2700).

Finden Sie die Stelle wo die Trades zurückgegeben werden. Suchen Sie nach:
```python
return {"trades": trades_response}
```

Ändern Sie die Trade-Verarbeitung so, dass Peak-Daten hinzugefügt werden.

Suchen Sie die Schleife die Trades verarbeitet und fügen Sie hinzu:

```python
# V3.2.9: Peak-Daten hinzufügen
ticket = str(trade.get('mt5_ticket') or trade.get('ticket', ''))
if ticket in trade_peaks:
    trade['peak_high'] = trade_peaks[ticket].get('high')
    trade['peak_low'] = trade_peaks[ticket].get('low')
```

---

## TEIL 2: Frontend ändern (Peak-Spalte anzeigen)

### Datei öffnen:
```
/pfad/zu/Version_3.0.0/frontend/src/pages/Dashboard.jsx
```

### Schritt 2.1: Spaltenüberschrift hinzufügen

Suchen Sie nach der Tabellen-Header-Zeile (ca. Zeile 2070-2085):

```jsx
<th className="px-4 py-3 text-right text-slate-300">Aktuell</th>
```

Fügen Sie DANACH eine neue Spalte ein:

```jsx
<th className="px-4 py-3 text-right text-purple-400">Peak</th>
```

Die Header-Reihenfolge sollte dann sein:
- Rohstoff
- Typ
- Strategie
- Einstieg
- Aktuell
- **Peak** (NEU)
- Menge
- SL
- TP
- P&L
- Fortschritt
- Plattform
- Aktion

### Schritt 2.2: Peak-Wert in der Trade-Zeile anzeigen

Suchen Sie nach der Zeile die den aktuellen Preis anzeigt (ca. Zeile 2178):

```jsx
<td className="px-4 py-3 text-right text-slate-200">${currentPrice?.toFixed(2)}</td>
```

Fügen Sie DANACH die Peak-Spalte ein:

```jsx
<td className="px-4 py-3 text-right">
  {(() => {
    // V3.2.9: Peak-Anzeige
    const peakHigh = trade.peak_high;
    const peakLow = trade.peak_low;
    const entryPrice = trade.entry_price;
    
    if (!peakHigh && !peakLow) {
      return <span className="text-slate-600 text-xs">-</span>;
    }
    
    // Bei BUY: Peak ist das Hoch
    // Bei SELL: Peak ist das Tief
    const peak = trade.type === 'BUY' ? peakHigh : peakLow;
    
    if (!peak) {
      return <span className="text-slate-600 text-xs">-</span>;
    }
    
    // Berechne wie viel vom Peak "verpasst" wurde
    const peakProfit = trade.type === 'BUY' 
      ? peak - entryPrice 
      : entryPrice - peak;
    
    const currentProfit = trade.type === 'BUY'
      ? (currentPrice || entryPrice) - entryPrice
      : entryPrice - (currentPrice || entryPrice);
    
    const missedProfit = peakProfit - currentProfit;
    const missedPercent = peakProfit > 0 ? (missedProfit / peakProfit) * 100 : 0;
    
    return (
      <div className="text-xs">
        <span className="text-purple-400 font-medium">${peak.toFixed(2)}</span>
        {missedProfit > 0.01 && (
          <div className="text-amber-400 text-xs">
            -{missedPercent.toFixed(0)}% vom Peak
          </div>
        )}
      </div>
    );
  })()}
</td>
```

---

## TEIL 3: Änderungen speichern und testen

### Auf dem Mac:

1. **Speichern** Sie beide Dateien

2. **Backend neu starten:**
```bash
cd /pfad/zu/Version_3.0.0/backend
pkill -f "python.*server.py"
python3 server.py &
```

3. **Frontend neu starten (wenn nötig):**
```bash
cd /pfad/zu/Version_3.0.0/frontend
npm run build
# oder für Development:
npm start
```

4. **Browser aktualisieren** (Cmd+Shift+R für Hard Refresh)

---

## Vollständiges Code-Beispiel

### Backend - server.py (komplette Peak-Funktion):

```python
# Am Anfang der Datei, nach den Imports (ca. Zeile 180-200):
trade_peaks = {}  # Peak-Tracking

# Neue Funktion (vor update_market_data):
async def update_trade_peaks():
    """Aktualisiert Peak-Werte für alle offenen Trades"""
    global trade_peaks
    
    try:
        from multi_platform_connector import multi_platform
        positions = await multi_platform.get_positions()
        
        if not positions:
            return
        
        for pos in positions:
            ticket = str(pos.get('ticket') or pos.get('id', ''))
            current_price = pos.get('currentPrice', 0)
            
            if not ticket or not current_price:
                continue
            
            if ticket not in trade_peaks:
                trade_peaks[ticket] = {
                    'high': current_price,
                    'low': current_price,
                    'entry_price': pos.get('openPrice', current_price)
                }
            else:
                if current_price > trade_peaks[ticket]['high']:
                    trade_peaks[ticket]['high'] = current_price
                if current_price < trade_peaks[ticket]['low']:
                    trade_peaks[ticket]['low'] = current_price
        
        # Cleanup
        open_tickets = {str(pos.get('ticket') or pos.get('id', '')) for pos in positions}
        for t in list(trade_peaks.keys()):
            if t not in open_tickets:
                del trade_peaks[t]
                
    except Exception as e:
        logger.debug(f"Peak update error: {e}")
```

### Frontend - Dashboard.jsx (Peak-Spalte):

```jsx
{/* Header (nach "Aktuell" Spalte): */}
<th className="px-4 py-3 text-right text-purple-400">Peak</th>

{/* Body (nach currentPrice Zeile): */}
<td className="px-4 py-3 text-right">
  {(() => {
    const peak = trade.type === 'BUY' ? trade.peak_high : trade.peak_low;
    if (!peak) return <span className="text-slate-600">-</span>;
    
    const peakProfit = trade.type === 'BUY' 
      ? peak - trade.entry_price 
      : trade.entry_price - peak;
    const currentProfit = trade.type === 'BUY'
      ? (currentPrice || trade.entry_price) - trade.entry_price
      : trade.entry_price - (currentPrice || trade.entry_price);
    const missedPercent = peakProfit > 0 ? ((peakProfit - currentProfit) / peakProfit) * 100 : 0;
    
    return (
      <div className="text-xs">
        <span className="text-purple-400">${peak.toFixed(2)}</span>
        {missedPercent > 5 && (
          <div className="text-amber-400">-{missedPercent.toFixed(0)}%</div>
        )}
      </div>
    );
  })()}
</td>
```

---

## Fehlerbehebung

### Peak zeigt "-" an:
- Die Peak-Daten werden erst nach dem nächsten Market-Update verfügbar
- Warten Sie 10-30 Sekunden nach dem Öffnen des Dashboards

### Spalte erscheint nicht:
- Prüfen Sie ob beide Änderungen (Header UND Body) eingefügt wurden
- Hard Refresh im Browser (Cmd+Shift+R)

### Backend startet nicht:
- Prüfen Sie die Python-Syntax mit: `python3 -c "import server"`
- Schauen Sie in die Logs: `tail -f /var/log/supervisor/backend.err.log`

### TypeError bei Peak-Berechnung:
- Stellen Sie sicher, dass `trade.peak_high` und `trade.peak_low` existieren
- Fügen Sie Null-Checks hinzu wie im Beispiel gezeigt

---

## Anzeige-Beispiel

Nach der Änderung sieht die Trade-Zeile so aus:

| Rohstoff | Typ | ... | Aktuell | Peak | ... |
|----------|-----|-----|---------|------|-----|
| Gold | BUY | ... | $2050.00 | $2065.00 -15% vom Peak | ... |
| WTI | SELL | ... | $72.50 | $71.80 -8% vom Peak | ... |

Die Peak-Spalte zeigt:
- **Lila**: Der Peak-Preis
- **Amber/Gelb**: Wie viel % vom Peak-Gewinn "verpasst" wurde

---

## Alternative: Einfachere Version (nur Peak-Preis ohne Prozent)

Wenn Sie nur den Peak-Preis ohne die Prozent-Berechnung möchten:

```jsx
<td className="px-4 py-3 text-right text-purple-400">
  {trade.type === 'BUY' 
    ? (trade.peak_high ? `$${trade.peak_high.toFixed(2)}` : '-')
    : (trade.peak_low ? `$${trade.peak_low.toFixed(2)}` : '-')
  }
</td>
```

---

**Ende der Anleitung**
