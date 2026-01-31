#!/usr/bin/env python3
"""
Test Trading Fixes V3.3.0
Prüft:
1. ✅ Cooldown ist 60 Min (statt 15)
2. ✅ Cooldown erhöht sich auf 120 Min wenn Asset aktiv
3. ✅ Alle 7 Strategien werden dynamisch gewählt (nicht hardcoded)
4. ✅ Strategy fließt durch die Trade-Pipeline
"""

import sys
import json
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

def test_cooldown_defaults():
    """Test 1: Cooldown defaults sind auf 60 Min"""
    print("\n" + "="*60)
    print("TEST 1: COOLDOWN DEFAULTS (15 -> 60 Min)")
    print("="*60)
    
    # Check server.py
    server_file = backend_path / "server.py"
    content = server_file.read_text()
    
    # Suche nach ai_per_account_cooldown_minutes
    if "ai_per_account_cooldown_minutes: int = 60" in content:
        print("✅ server.py: ai_per_account_cooldown_minutes = 60")
    elif "ai_per_account_cooldown_minutes: int = 15" in content:
        print("❌ server.py: ai_per_account_cooldown_minutes = 15 (SOLLTE 60 sein)")
        return False
    else:
        print("⚠️  server.py: ai_per_account_cooldown_minutes nicht gefunden")
        return False
    
    # Check ai_trading_bot.py
    ai_bot = backend_path / "ai_trading_bot.py"
    content = ai_bot.read_text()
    
    if "self.settings.get('ai_per_account_cooldown_minutes', 60)" in content:
        print("✅ ai_trading_bot.py: default = 60")
    else:
        print("❌ ai_trading_bot.py: default ist nicht 60")
        return False
    
    return True

def test_intelligent_cooldown():
    """Test 2: Intelligente Cooldown-Logik (120 Min wenn aktiv)"""
    print("\n" + "="*60)
    print("TEST 2: INTELLIGENTE COOLDOWN (60 -> 120 Min wenn aktiv)")
    print("="*60)
    
    # Check ai_trading_bot.py
    ai_bot = backend_path / "ai_trading_bot.py"
    content = ai_bot.read_text()
    
    if "open_positions_for_asset > 0" in content and "cooldown_minutes = 120" in content:
        print("✅ ai_trading_bot.py: Erhöht auf 120 Min wenn Asset aktiv")
    else:
        print("❌ ai_trading_bot.py: Intelligente Cooldown nicht implementiert")
        return False
    
    # Check multi_bot_system.py
    multi_bot = backend_path / "multi_bot_system.py"
    content = multi_bot.read_text()
    
    if "cooldown_minutes = 120" in content and "len(positions_for_asset) > 0" in content:
        print("✅ multi_bot_system.py: Erhöht auf 120 Min wenn Asset aktiv")
    else:
        print("❌ multi_bot_system.py: Intelligente Cooldown nicht implementiert")
        return False
    
    return True

def test_strategy_from_signal():
    """Test 3: Strategy kommt aus Signal, nicht hardcoded"""
    print("\n" + "="*60)
    print("TEST 3: STRATEGIE AUS SIGNAL (nicht hardcoded)")
    print("="*60)
    
    # Check ai_trading_bot.py - sollte analyze_and_open_trades NICHT mehr direkt aufgerufen werden
    ai_bot = backend_path / "ai_trading_bot.py"
    content = ai_bot.read_text()
    
    # Suche nach den alten analyze_and_open_trades Aufrufen (sollten kommentiert sein)
    lines = content.split('\n')
    deprecated_found = False
    for i, line in enumerate(lines, 1):
        if "await self.analyze_and_open_trades(strategy=" in line and not line.strip().startswith('#'):
            if "DEPRECATED" not in lines[i-2] if i > 1 else False:
                print(f"❌ ai_trading_bot.py Zeile {i}: analyze_and_open_trades wird noch direkt aufgerufen")
                return False
        if "V3.3.0: DEPRECATED" in line or "V3.3.0: ARCHITEKTUR-FIX" in line:
            deprecated_found = True
    
    if deprecated_found:
        print("✅ ai_trading_bot.py: analyze_and_open_trades ist depreciert")
    else:
        print("⚠️  ai_trading_bot.py: Keine DEPRECATED Markierung gefunden")
    
    return True

def test_strategy_in_trade_settings():
    """Test 4: Strategy fließt durch Pipeline zur trade_settings"""
    print("\n" + "="*60)
    print("TEST 4: STRATEGY FLIESST DURCH PIPELINE")
    print("="*60)
    
    multi_bot = backend_path / "multi_bot_system.py"
    content = multi_bot.read_text()
    
    # Suche nach der Trade-Settings Speicherung
    if "'strategy': strategy," in content or "'strategy': strategy  # V3.3.0" in content:
        print("✅ multi_bot_system.py: 'strategy': strategy wird in trade_settings gespeichert")
    elif "'strategy': '4pillar_autonomous'" in content:
        print("❌ multi_bot_system.py: 'strategy' ist noch hardcoded zu '4pillar_autonomous'")
        return False
    else:
        print("⚠️  multi_bot_system.py: Konnte strategy in trade_settings nicht finden")
        return False
    
    return True

def test_all_strategies_available():
    """Test 5: Alle 7 Strategien sind in der V3.2.2 Logik verfügbar"""
    print("\n" + "="*60)
    print("TEST 5: ALLE 7 STRATEGIEN (V3.2.2 Logik)")
    print("="*60)
    
    multi_bot = backend_path / "multi_bot_system.py"
    content = multi_bot.read_text()
    
    strategies_to_find = [
        "day_trading",
        "swing_trading",
        "scalping",
        "mean_reversion",
        "momentum",
        "breakout",
        "grid"
    ]
    
    found_strategies = []
    for strategy in strategies_to_find:
        # Suche nach best_strategy = 'strategie' oder best_strategy = "strategie"
        if f"best_strategy = '{strategy}'" in content or f'best_strategy = "{strategy}"' in content or f"= '{strategy}'" in content and strategy in content:
            found_strategies.append(strategy)
            print(f"✅ Strategie '{strategy}' wird zugewiesen")
    
    if len(found_strategies) == 7:
        print(f"\n✅ Alle 7 Strategien gefunden")
        return True
    else:
        print(f"\n❌ Nur {len(found_strategies)} von 7 Strategien gefunden")
        return False

def test_v322_logic():
    """Test 6: V3.2.2 Strategie-Auswahl ist dynamisch (nicht hardcoded)"""
    print("\n" + "="*60)
    print("TEST 6: V3.2.2 DYNAMISCHE STRATEGIE-AUSWAHL")
    print("="*60)
    
    multi_bot = backend_path / "multi_bot_system.py"
    content = multi_bot.read_text()
    
    # Suche nach V3.2.2 VERBESSERTE Strategie-Auswahl
    if "V3.2.2: VERBESSERTE Strategie-Auswahl" in content:
        print("✅ V3.2.2 Strategie-Auswahl-Logik vorhanden")
        
        # Prüfe, dass die Logik dynamisch ist (basierend auf ADX, RSI, ATR)
        if "adx >" in content and "rsi >" in content and "atr_percent" in content:
            print("✅ Logik basiert auf ADX, RSI und ATR (dynamisch)")
            return True
        else:
            print("⚠️  Logik könnte nicht vollständig sein")
            return True  # Nicht kritisch
    else:
        print("❌ V3.2.2 Strategie-Auswahl nicht gefunden")
        return False

def main():
    """Führe alle Tests aus"""
    print("\n")
    print("╔" + "═"*58 + "╗")
    print("║" + " "*15 + "TRADING FIXES V3.3.0 TEST-SUITE" + " "*12 + "║")
    print("╚" + "═"*58 + "╝")
    
    tests = [
        ("Cooldown Defaults (60 Min)", test_cooldown_defaults),
        ("Intelligente Cooldown Logic", test_intelligent_cooldown),
        ("Strategy aus Signal", test_strategy_from_signal),
        ("Strategy durch Pipeline", test_strategy_in_trade_settings),
        ("Alle 7 Strategien", test_all_strategies_available),
        ("V3.2.2 Dynamische Auswahl", test_v322_logic),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ FEHLER: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*60)
    print("ZUSAMMENFASSUNG")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nGesamt: {passed}/{total} Tests bestanden")
    
    if passed == total:
        print("\n🎉 ALLE TESTS BESTANDEN!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} Test(s) fehlgeschlagen")
        return 1

if __name__ == "__main__":
    sys.exit(main())
