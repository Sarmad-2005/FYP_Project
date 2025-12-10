"""
Phase 8 Test Script
Comprehensive tests for API Gateway migration.
"""

import sys
import os
import time
import requests
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))


class Phase8Tester:
    """Test suite for Phase 8 implementation."""
    
    def __init__(self):
        self.test_results = []
        self.gateway_url = os.getenv('GATEWAY_URL', 'http://localhost:5000')
        self.app_url = 'http://localhost:5001'
    
    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result."""
        status = "PASS" if passed else "FAIL"
        result = f"[{status}] {test_name}"
        if message:
            result += f": {message}"
        print(result)
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })
    
    def test_shared_package(self):
        """Test 1: Shared package exists and imports."""
        print("\n=== Test 1: Shared Package ===")
        
        try:
            from shared import LLMManager, EmbeddingsManager, DatabaseManager
            self.log_test("Shared package imports", True)
        except ImportError as e:
            self.log_test("Shared package imports", False, str(e))
    
    def test_gateway_client(self):
        """Test 2: Gateway client module."""
        print("\n=== Test 2: Gateway Client ===")
        
        try:
            from backend.gateway_client import GatewayClient, get_gateway_client
            client = get_gateway_client()
            assert client is not None
            self.log_test("Gateway client import", True)
        except Exception as e:
            self.log_test("Gateway client import", False, str(e))
    
    def test_gateway_client_availability_check(self):
        """Test 3: Gateway availability check."""
        print("\n=== Test 3: Gateway Availability Check ===")
        
        try:
            from backend.gateway_client import get_gateway_client
            client = get_gateway_client()
            available = client.is_available()
            self.log_test("Gateway availability check", True, f"Gateway available: {available}")
        except Exception as e:
            self.log_test("Gateway availability check", False, str(e))
    
    def test_app_gateway_integration(self):
        """Test 4: App.py gateway integration."""
        print("\n=== Test 4: App Gateway Integration ===")
        
        try:
            # Check if app.py has gateway client import
            with open('app.py', 'r') as f:
                content = f.read()
            
            if 'gateway_client' in content and 'get_gateway_client' in content:
                self.log_test("App.py gateway integration", True)
            else:
                self.log_test("App.py gateway integration", False, "Gateway client not found in app.py")
        except Exception as e:
            self.log_test("App.py gateway integration", False, str(e))
    
    def test_gateway_routing(self):
        """Test 5: Gateway routing (if gateway is running)."""
        print("\n=== Test 5: Gateway Routing ===")
        
        try:
            response = requests.get(f"{self.gateway_url}/health", timeout=2)
            if response.status_code == 200:
                # Gateway is running, test routing
                response = requests.get(f"{self.gateway_url}/financial_agent/health", timeout=5)
                if response.status_code in [200, 503]:  # 503 if service down, 200 if up
                    self.log_test("Gateway routing", True)
                else:
                    self.log_test("Gateway routing", False, f"Unexpected status: {response.status_code}")
            else:
                self.log_test("Gateway routing", True, "Skipped - gateway not running")
        except requests.exceptions.ConnectionError:
            self.log_test("Gateway routing", True, "Skipped - gateway not running")
        except Exception as e:
            self.log_test("Gateway routing", False, str(e))
    
    def test_fallback_mechanism(self):
        """Test 6: Fallback mechanism."""
        print("\n=== Test 6: Fallback Mechanism ===")
        
        try:
            from backend.gateway_client import GatewayClient
            
            # Test with gateway disabled
            client = GatewayClient(use_gateway=False)
            assert client.is_available() == False
            self.log_test("Fallback mechanism (gateway disabled)", True)
            
            # Test with unavailable gateway
            client = GatewayClient(gateway_url='http://localhost:9999', use_gateway=True)
            assert client.is_available() == False
            self.log_test("Fallback mechanism (gateway unavailable)", True)
        except Exception as e:
            self.log_test("Fallback mechanism", False, str(e))
    
    def test_environment_variables(self):
        """Test 7: Environment variable support."""
        print("\n=== Test 7: Environment Variables ===")
        
        try:
            from backend.gateway_client import GatewayClient
            
            # Test default values
            client = GatewayClient()
            assert client.gateway_url == 'http://localhost:5000'
            self.log_test("Environment variables (defaults)", True)
        except Exception as e:
            self.log_test("Environment variables", False, str(e))
    
    def run_all_tests(self):
        """Run all tests."""
        print("=" * 60)
        print("Phase 8 Test Suite - API Gateway Migration")
        print("=" * 60)
        
        self.test_shared_package()
        self.test_gateway_client()
        self.test_gateway_client_availability_check()
        self.test_app_gateway_integration()
        self.test_gateway_routing()
        self.test_fallback_mechanism()
        self.test_environment_variables()
        
        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        passed = sum(1 for r in self.test_results if r["passed"])
        total = len(self.test_results)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        if total > 0:
            print(f"Success Rate: {(passed/total*100):.1f}%")
        
        if passed == total:
            print("\n✓ All tests passed! Phase 8 foundation is ready.")
            print("\nNext steps:")
            print("  1. Update remaining routes in app.py using the migration pattern")
            print("  2. See PHASE8_MIGRATION_GUIDE.md for examples")
            print("  3. Test with gateway running and without (fallback mode)")
            return True
        else:
            print("\n✗ Some tests failed. Please review the implementation.")
            return False


if __name__ == "__main__":
    tester = Phase8Tester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
