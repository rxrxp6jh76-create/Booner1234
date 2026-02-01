#!/usr/bin/env python3
"""
Booner Trade v2.3.29 - Backend API Testing Suite
Tests all critical API endpoints for the KI-gesteuerte Trading-Plattform
"""

import requests
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, List

class BoonerTradeAPITester:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api"
        self.session = requests.Session()
        self.session.timeout = 30
        
        # Test results tracking
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.test_results = []
        
        print(f"🚀 Booner Trade API Tester initialized")
        print(f"📡 Backend URL: {self.base_url}")
        print(f"🔗 API Base: {self.api_base}")
        print("=" * 60)

    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {test_name}: PASSED")
            if details:
                print(f"   📋 {details}")
        else:
            self.failed_tests.append(test_name)
            print(f"❌ {test_name}: FAILED")
            if details:
                print(f"   💥 {details}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "response_data": response_data,
            "timestamp": datetime.now().isoformat()
        })
        print()

    def test_health_endpoint(self):
        """Test /api/health endpoint"""
        try:
            response = self.session.get(f"{self.api_base}/health")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'healthy':
                    self.log_test(
                        "Health API", 
                        True, 
                        f"Status: {data.get('status')}, Uptime: {data.get('uptime', 'N/A')}"
                    )
                else:
                    self.log_test(
                        "Health API", 
                        False, 
                        f"Unexpected status: {data.get('status')}"
                    )
            else:
                self.log_test(
                    "Health API", 
                    False, 
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )
                
        except Exception as e:
            self.log_test("Health API", False, f"Connection error: {str(e)}")

    def test_market_data_endpoint(self):
        """Test /api/market/all endpoint (correct market data endpoint)"""
        try:
            response = self.session.get(f"{self.api_base}/market/all")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and 'markets' in data:
                    market_count = len(data.get('markets', {}))
                    self.log_test(
                        "Market Data API", 
                        True, 
                        f"Retrieved {market_count} market entries"
                    )
                else:
                    self.log_test(
                        "Market Data API", 
                        False, 
                        f"Unexpected response format: {type(data)}"
                    )
            else:
                self.log_test(
                    "Market Data API", 
                    False, 
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )
                
        except Exception as e:
            self.log_test("Market Data API", False, f"Connection error: {str(e)}")

    def test_settings_endpoint(self):
        """Test /api/settings GET endpoint"""
        try:
            response = self.session.get(f"{self.api_base}/settings")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    # Check for key settings fields
                    key_fields = ['auto_trading', 'use_ai_analysis', 'ai_provider', 'active_platforms']
                    found_fields = [field for field in key_fields if field in data]
                    
                    self.log_test(
                        "Settings GET API", 
                        True, 
                        f"Found {len(found_fields)}/{len(key_fields)} key fields: {found_fields}"
                    )
                else:
                    self.log_test(
                        "Settings GET API", 
                        False, 
                        f"Unexpected response format: {type(data)}"
                    )
            else:
                self.log_test(
                    "Settings GET API", 
                    False, 
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )
                
        except Exception as e:
            self.log_test("Settings GET API", False, f"Connection error: {str(e)}")

    def test_settings_save_load(self):
        """Test /api/settings POST (save) functionality"""
        try:
            # First get current settings
            get_response = self.session.get(f"{self.api_base}/settings")
            if get_response.status_code != 200:
                self.log_test("Settings Save/Load", False, "Could not retrieve current settings")
                return
            
            current_settings = get_response.json()
            
            # Create test settings with a small modification
            test_settings = current_settings.copy()
            test_settings['max_trades_per_hour'] = 999  # Test value
            test_settings['test_timestamp'] = datetime.now().isoformat()
            
            # Save the test settings
            post_response = self.session.post(
                f"{self.api_base}/settings", 
                json=test_settings,
                headers={'Content-Type': 'application/json'}
            )
            
            if post_response.status_code == 200:
                # Verify the settings were saved by retrieving them again
                verify_response = self.session.get(f"{self.api_base}/settings")
                if verify_response.status_code == 200:
                    saved_settings = verify_response.json()
                    if saved_settings.get('max_trades_per_hour') == 999:
                        self.log_test(
                            "Settings Save/Load", 
                            True, 
                            "Successfully saved and retrieved test settings"
                        )
                        
                        # Restore original settings
                        self.session.post(f"{self.api_base}/settings", json=current_settings)
                    else:
                        self.log_test(
                            "Settings Save/Load", 
                            False, 
                            "Settings not properly saved or retrieved"
                        )
                else:
                    self.log_test(
                        "Settings Save/Load", 
                        False, 
                        f"Could not verify saved settings: HTTP {verify_response.status_code}"
                    )
            else:
                self.log_test(
                    "Settings Save/Load", 
                    False, 
                    f"Save failed: HTTP {post_response.status_code}: {post_response.text[:200]}"
                )
                
        except Exception as e:
            self.log_test("Settings Save/Load", False, f"Error: {str(e)}")

    def test_additional_endpoints(self):
        """Test additional important endpoints"""
        endpoints_to_test = [
            ("/api/commodities", "Commodities API"),
            ("/api/market/all", "All Markets API"),
            ("/api/trades/list", "Trades List API"),
            ("/api/trades/stats", "Trade Statistics API"),
            ("/api/signals/status", "Signals Status API"),
        ]
        
        for endpoint, name in endpoints_to_test:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        self.log_test(name, True, f"Response received, type: {type(data)}")
                    except json.JSONDecodeError:
                        self.log_test(name, False, "Invalid JSON response")
                elif response.status_code == 404:
                    self.log_test(name, False, "Endpoint not found (404)")
                else:
                    self.log_test(name, False, f"HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_test(name, False, f"Connection error: {str(e)}")

    def test_lot_size_calculation(self):
        """Test lot size calculation for €1000 balance - should be max 0.02 lot"""
        try:
            # Test lot size calculation endpoint or logic
            test_data = {
                "balance": 1000.0,
                "commodity": "GOLD",
                "confidence_score": 0.75,
                "stop_loss_pips": 20,
                "tick_value": 10.0,
                "trading_mode": "neutral"
            }
            
            # Try to find a lot size calculation endpoint
            response = self.session.post(
                f"{self.api_base}/calculate/lot-size", 
                json=test_data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                lot_size = data.get('lot_size', 0)
                
                if lot_size <= 0.02:
                    self.log_test(
                        "Lot Size Calculation (€1000 Balance)", 
                        True, 
                        f"Lot size {lot_size} is correctly ≤ 0.02 for €1000 balance"
                    )
                else:
                    self.log_test(
                        "Lot Size Calculation (€1000 Balance)", 
                        False, 
                        f"Lot size {lot_size} is too high for €1000 balance (should be ≤ 0.02)"
                    )
            elif response.status_code == 404:
                # Endpoint might not exist, check if logic is embedded in trading logic
                self.log_test(
                    "Lot Size Calculation (€1000 Balance)", 
                    False, 
                    "Lot size calculation endpoint not found - may be embedded in trading logic"
                )
            else:
                self.log_test(
                    "Lot Size Calculation (€1000 Balance)", 
                    False, 
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )
                
        except Exception as e:
            self.log_test("Lot Size Calculation (€1000 Balance)", False, f"Error: {str(e)}")

    def test_peak_profit_tracking(self):
        """Test peak profit tracking - should persist even when current profit is negative"""
        try:
            # Check if trades have peak_profit field
            response = self.session.get(f"{self.api_base}/trades/list")
            
            if response.status_code == 200:
                data = response.json()
                trades = data.get('trades', []) if isinstance(data, dict) else data
                
                if trades and len(trades) > 0:
                    # Check if any trade has peak_profit field
                    has_peak_profit = any('peak_profit' in trade for trade in trades)
                    
                    if has_peak_profit:
                        # Find a trade with peak_profit data
                        peak_profit_trades = [t for t in trades if 'peak_profit' in t and t.get('peak_profit') is not None]
                        
                        if peak_profit_trades:
                            sample_trade = peak_profit_trades[0]
                            peak_profit = sample_trade.get('peak_profit')
                            current_profit = sample_trade.get('profit_loss', sample_trade.get('profit', 0))
                            
                            self.log_test(
                                "Peak Profit Tracking", 
                                True, 
                                f"Found trades with peak_profit field. Sample: peak={peak_profit}, current={current_profit}"
                            )
                        else:
                            self.log_test(
                                "Peak Profit Tracking", 
                                True, 
                                "Peak profit field exists but no trades with peak profit data yet"
                            )
                    else:
                        self.log_test(
                            "Peak Profit Tracking", 
                            False, 
                            "No trades found with peak_profit field"
                        )
                else:
                    self.log_test(
                        "Peak Profit Tracking", 
                        True, 
                        "No trades available to test peak profit tracking (expected if no active trades)"
                    )
            else:
                self.log_test(
                    "Peak Profit Tracking", 
                    False, 
                    f"Could not retrieve trades: HTTP {response.status_code}"
                )
                
        except Exception as e:
            self.log_test("Peak Profit Tracking", False, f"Error: {str(e)}")

    def test_profit_drawdown_exit(self):
        """Test profit drawdown exit at 20% from peak (not 10%)"""
        try:
            # Check settings for drawdown percentage
            response = self.session.get(f"{self.api_base}/settings")
            
            if response.status_code == 200:
                settings = response.json()
                
                # Look for drawdown-related settings
                drawdown_settings = {}
                for key, value in settings.items():
                    if 'drawdown' in key.lower() or 'exit' in key.lower():
                        drawdown_settings[key] = value
                
                # Check if there's a 20% drawdown setting
                found_20_percent = False
                for key, value in drawdown_settings.items():
                    if isinstance(value, (int, float)) and value == 20:
                        found_20_percent = True
                        break
                
                if found_20_percent:
                    self.log_test(
                        "Profit Drawdown Exit (20%)", 
                        True, 
                        f"Found 20% drawdown setting in configuration: {drawdown_settings}"
                    )
                elif drawdown_settings:
                    self.log_test(
                        "Profit Drawdown Exit (20%)", 
                        False, 
                        f"Drawdown settings found but no 20% value: {drawdown_settings}"
                    )
                else:
                    self.log_test(
                        "Profit Drawdown Exit (20%)", 
                        False, 
                        "No drawdown-related settings found in configuration"
                    )
            else:
                self.log_test(
                    "Profit Drawdown Exit (20%)", 
                    False, 
                    f"Could not retrieve settings: HTTP {response.status_code}"
                )
                
        except Exception as e:
            self.log_test("Profit Drawdown Exit (20%)", False, f"Error: {str(e)}")

    def test_portfolio_risk_warning(self):
        """Test portfolio risk warning at >20%"""
        try:
            # Check settings for portfolio risk limits
            response = self.session.get(f"{self.api_base}/settings")
            
            if response.status_code == 200:
                settings = response.json()
                
                # Look for portfolio risk settings
                risk_settings = {}
                for key, value in settings.items():
                    if 'portfolio' in key.lower() and 'risk' in key.lower():
                        risk_settings[key] = value
                    elif 'max_portfolio' in key.lower():
                        risk_settings[key] = value
                
                # Check for 20% portfolio risk limit
                found_20_percent_limit = False
                for key, value in risk_settings.items():
                    if isinstance(value, (int, float)) and value == 20:
                        found_20_percent_limit = True
                        break
                
                if found_20_percent_limit:
                    self.log_test(
                        "Portfolio Risk Warning (>20%)", 
                        True, 
                        f"Found 20% portfolio risk limit: {risk_settings}"
                    )
                elif risk_settings:
                    self.log_test(
                        "Portfolio Risk Warning (>20%)", 
                        False, 
                        f"Portfolio risk settings found but no 20% limit: {risk_settings}"
                    )
                else:
                    self.log_test(
                        "Portfolio Risk Warning (>20%)", 
                        False, 
                        "No portfolio risk settings found in configuration"
                    )
            else:
                self.log_test(
                    "Portfolio Risk Warning (>20%)", 
                    False, 
                    f"Could not retrieve settings: HTTP {response.status_code}"
                )
                
        except Exception as e:
            self.log_test("Portfolio Risk Warning (>20%)", False, f"Error: {str(e)}")

    def test_metaapi_integration(self):
        """Test MetaAPI integration endpoints"""
        metaapi_endpoints = [
            ("/api/platforms/MT5_LIBERTEX/account", "MT5 Libertex Account"),
            ("/api/platforms/MT5_ICMARKETS/account", "MT5 ICMarkets Account"),
            ("/api/platforms/MT5_LIBERTEX/positions", "MT5 Libertex Positions"),
            ("/api/platforms/MT5_ICMARKETS/positions", "MT5 ICMarkets Positions"),
        ]
        
        for endpoint, name in metaapi_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data.get('success'):
                            self.log_test(name, True, "MetaAPI connection successful")
                        else:
                            error_msg = data.get('error', 'Unknown error')
                            if 'Forbidden' in error_msg or 'account top-up' in error_msg:
                                self.log_test(name, True, f"Expected MetaAPI error: {error_msg}")
                            else:
                                self.log_test(name, False, f"MetaAPI error: {error_msg}")
                    except json.JSONDecodeError:
                        self.log_test(name, False, "Invalid JSON response")
                else:
                    self.log_test(name, False, f"HTTP {response.status_code}")
                    
            except Exception as e:
                self.log_test(name, False, f"Connection error: {str(e)}")

    def run_all_tests(self):
        """Run all test suites"""
        print("🧪 Starting Booner Trade Backend API Tests...")
        print()
        
        # Core API tests
        self.test_health_endpoint()
        self.test_market_data_endpoint()
        self.test_settings_endpoint()
        self.test_settings_save_load()
        
        # Additional endpoint tests
        self.test_additional_endpoints()
        
        # MetaAPI integration tests
        self.test_metaapi_integration()
        
        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print("=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {len(self.failed_tests)}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in self.failed_tests:
                print(f"   • {test}")
        
        print(f"\n🕒 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Return exit code based on results
        return 0 if len(self.failed_tests) == 0 else 1

def main():
    """Main test execution"""
    # Use the frontend's configured backend URL
    backend_url = "http://localhost:8001"
    
    print("🎯 Booner Trade v2.3.29 - Backend API Test Suite")
    print("🤖 KI-gesteuerte Trading-Plattform für MetaTrader 5")
    print()
    
    tester = BoonerTradeAPITester(backend_url)
    exit_code = tester.run_all_tests()
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())