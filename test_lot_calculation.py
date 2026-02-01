#!/usr/bin/env python3
"""
Test script to verify lot size calculation for €1000 balance
Tests the specific bug fix: Lot size should be much smaller than 0.5 for €1000 balance
"""

def calculate_lot_size_v2(balance, confidence_score, stop_loss_pips=20, tick_value=10.0, trading_mode="neutral"):
    """
    Replicated lot size calculation logic from multi_bot_system.py
    """
    # Normalize confidence to 0-100 if needed
    if confidence_score <= 1.0:
        confidence_percent = confidence_score * 100
    else:
        confidence_percent = confidence_score
    
    # Risk levels configuration (from multi_bot_system.py)
    RISK_LEVELS = {
        'conservative': {
            'min_confidence': 75,
            'low_risk_max': 80,
            'medium_risk_max': 88,
            'low_risk': 0.005,         # 0.5%
            'medium_risk': 0.0075,     # 0.75%
            'high_risk': 0.01,         # 1.0%
            'max_lot': 1.5
        },
        'neutral': {
            'min_confidence': 68,
            'low_risk_max': 75,
            'medium_risk_max': 85,
            'low_risk': 0.005,         # 0.5%
            'medium_risk': 0.01,       # 1.0%
            'high_risk': 0.015,        # 1.5%
            'max_lot': 2.0
        },
        'aggressive': {
            'min_confidence': 60,
            'low_risk_max': 68,
            'medium_risk_max': 78,
            'low_risk': 0.01,          # 1.0%
            'medium_risk': 0.015,      # 1.5%
            'high_risk': 0.02,         # 2.0%
            'max_lot': 2.5
        }
    }
    
    mode_config = RISK_LEVELS.get(trading_mode.lower(), RISK_LEVELS['neutral'])
    
    # Risk level determination
    min_conf = mode_config['min_confidence']
    low_max = mode_config['low_risk_max']
    med_max = mode_config['medium_risk_max']
    
    if confidence_percent < min_conf:
        print(f"⛔ Signal {confidence_percent:.1f}% < {min_conf}% minimum - No trade")
        return 0.0
    elif confidence_percent < low_max:
        risk_percent = mode_config['low_risk']
        risk_level = "LOW"
    elif confidence_percent <= med_max:
        risk_percent = mode_config['medium_risk']
        risk_level = "MEDIUM"
    else:
        risk_percent = mode_config['high_risk']
        risk_level = "HIGH"
    
    # Safety checks
    if balance <= 0:
        print("⚠️ Balance is 0 or negative!")
        return 0.01
    
    if stop_loss_pips <= 0:
        print("⚠️ Stop loss pips must be > 0")
        return 0.01
    
    if tick_value <= 0:
        print("⚠️ Tick value must be > 0")
        return 0.01
    
    # LOT CALCULATION
    # Formula: Lots = (Balance * Risk%) / (Stop_Loss_Pips * Tick_Value)
    risk_amount = balance * risk_percent
    lot_size = risk_amount / (stop_loss_pips * tick_value)
    
    # Apply limits
    max_lot = mode_config['max_lot']
    if lot_size > max_lot:
        lot_size = max_lot
    
    # Minimum lot size
    if lot_size < 0.01:
        lot_size = 0.01
    
    print(f"📊 Lot Calculation [{trading_mode.upper()}]:")
    print(f"   Balance: €{balance:.2f}")
    print(f"   Confidence: {confidence_percent:.1f}% ({risk_level} risk)")
    print(f"   Risk %: {risk_percent*100:.2f}%")
    print(f"   Risk Amount: €{risk_amount:.2f}")
    print(f"   Stop Loss Pips: {stop_loss_pips}")
    print(f"   Tick Value: {tick_value}")
    print(f"   Calculated Lot: {lot_size:.4f}")
    print(f"   Max Lot Limit: {max_lot}")
    
    return round(lot_size, 4)

def test_lot_size_for_1000_euro():
    """Test lot size calculation for €1000 balance"""
    print("🧪 Testing Lot Size Calculation for €1000 Balance")
    print("=" * 60)
    
    balance = 1000.0
    test_cases = [
        # (confidence, trading_mode, expected_max)
        (75, "neutral", 0.025),      # 75% confidence, neutral mode
        (80, "neutral", 0.05),       # 80% confidence, neutral mode  
        (90, "neutral", 0.075),      # 90% confidence, neutral mode
        (75, "conservative", 0.025), # 75% confidence, conservative mode
        (85, "conservative", 0.0375),# 85% confidence, conservative mode
        (70, "aggressive", 0.05),    # 70% confidence, aggressive mode
        (80, "aggressive", 0.075),   # 80% confidence, aggressive mode
    ]
    
    all_passed = True
    
    for confidence, mode, expected_max in test_cases:
        print(f"\n🔍 Test Case: {confidence}% confidence, {mode} mode")
        lot_size = calculate_lot_size_v2(
            balance=balance,
            confidence_score=confidence,
            stop_loss_pips=20,
            tick_value=10.0,
            trading_mode=mode
        )
        
        if lot_size <= expected_max:
            print(f"✅ PASSED: Lot size {lot_size:.4f} ≤ {expected_max:.4f}")
        else:
            print(f"❌ FAILED: Lot size {lot_size:.4f} > {expected_max:.4f}")
            all_passed = False
        
        # Check if lot size is much smaller than 0.5 (the original bug)
        if lot_size < 0.5:
            print(f"✅ Bug Fix Verified: Lot size {lot_size:.4f} << 0.5")
        else:
            print(f"❌ Bug Still Present: Lot size {lot_size:.4f} not much smaller than 0.5")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED - Lot size calculation is working correctly!")
        print("✅ Bug Fix Confirmed: For €1000 balance, lot sizes are much smaller than 0.5")
    else:
        print("❌ SOME TESTS FAILED - Lot size calculation needs review")
    
    return all_passed

if __name__ == "__main__":
    test_lot_size_for_1000_euro()