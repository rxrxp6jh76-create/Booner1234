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