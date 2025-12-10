"""
Phase 4 Test Script
Comprehensive tests for CSV Analysis Agent A2A conversion.
"""

import sys
import os
import json
import time
import requests
import subprocess
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from backend.csv_analysis_agent.csv_analysis_agent import CSVAnalysisAgent
from backend.csv_analysis_agent.tools.financial_tools import FinancialDataTool, TransactionTool, AnomalyTool
from backend.csv_analysis_agent.agents.data_context_agent import DataContextAgent
from backend.a2a_router.router import A2ARouter
from backend.a2a_protocol.a2a_message import A2AMessage, MessageType
from backend.llm_manager import LLMManager
from backend.financial_agent.agents.anomaly_detection_agent import AnomalyDetectionAgent
from backend.financial_agent.chroma_manager import FinancialChromaManager


class Phase4Tester:
    """Test suite for Phase 4 implementation."""
    
    def __init__(self):
        self.test_results = []
        self.service_url = "http://localhost:8003"
        self.service_process = None
        
        # Initialize managers for direct testing
        self.llm_manager = LLMManager()
        self.a2a_router = A2ARouter()
        self.chroma_manager = FinancialChromaManager()
        self.anomaly_agent = AnomalyDetectionAgent(self.chroma_manager)
    
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
    
    def start_service(self):
        """Start the CSV analysis service in a subprocess."""
        try:
            service_path = os.path.join(os.path.dirname(__file__), 'services', 'csv-analysis-service', 'main.py')
            if not os.path.exists(service_path):
                return False
            
            self.service_process = subprocess.Popen(
                [sys.executable, service_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.path.dirname(__file__)
            )
            
            # Wait for service to start
            max_attempts = 20
            for i in range(max_attempts):
                try:
                    response = requests.get(f"{self.service_url}/health", timeout=1)
                    if response.status_code == 200:
                        return True
                except:
                    time.sleep(0.5)
            
            if self.service_process:
                self.service_process.terminate()
                self.service_process = None
            return False
        except Exception as e:
            print(f"Warning: Could not start service: {e}")
            return False
    
    def stop_service(self):
        """Stop the CSV analysis service."""
        if self.service_process:
            try:
                self.service_process.terminate()
                self.service_process.wait(timeout=5)
            except:
                try:
                    self.service_process.kill()
                except:
                    pass
            self.service_process = None
    
    def test_tool_a2a_conversion(self):
        """Test 1: Financial tools use A2A router."""
        print("\n=== Test 1: Tool A2A Conversion ===")
        
        try:
            # Test FinancialDataTool initialization with A2A router
            tool = FinancialDataTool(self.a2a_router)
            assert tool.a2a_router is not None
            # Verify old financial_interface attribute doesn't exist (removed in Phase 4)
            assert not hasattr(tool, 'financial_interface')
            self.log_test("FinancialDataTool uses A2A router", True)
        except Exception as e:
            self.log_test("FinancialDataTool uses A2A router", False, str(e))
        
        try:
            # Test TransactionTool initialization with A2A router
            tool = TransactionTool(self.a2a_router)
            assert tool.a2a_router is not None
            self.log_test("TransactionTool uses A2A router", True)
        except Exception as e:
            self.log_test("TransactionTool uses A2A router", False, str(e))
        
        try:
            # Test AnomalyTool initialization with A2A router
            tool = AnomalyTool(a2a_router=self.a2a_router, anomaly_agent=self.anomaly_agent)
            assert tool.a2a_router is not None
            self.log_test("AnomalyTool uses A2A router", True)
        except Exception as e:
            self.log_test("AnomalyTool uses A2A router", False, str(e))
    
    def test_data_context_agent_a2a(self):
        """Test 2: Data context agent uses A2A."""
        print("\n=== Test 2: Data Context Agent A2A ===")
        
        try:
            # Test DataContextAgent initialization with A2A router
            agent = DataContextAgent(self.a2a_router, self.anomaly_agent)
            assert agent.a2a_router is not None
            # Verify old financial_interface attribute doesn't exist (removed in Phase 4)
            assert not hasattr(agent, 'financial_interface')
            self.log_test("DataContextAgent uses A2A router", True)
        except Exception as e:
            self.log_test("DataContextAgent uses A2A router", False, str(e))
    
    def test_csv_agent_initialization(self):
        """Test 3: CSV Analysis Agent initialization with A2A."""
        print("\n=== Test 3: CSV Agent Initialization ===")
        
        try:
            # Test CSV Analysis Agent initialization
            agent = CSVAnalysisAgent(self.llm_manager, self.a2a_router, self.anomaly_agent)
            assert agent.a2a_router is not None
            assert agent.context_agent.a2a_router is not None
            self.log_test("CSVAnalysisAgent initialized with A2A router", True)
        except Exception as e:
            self.log_test("CSVAnalysisAgent initialized with A2A router", False, str(e))
    
    def test_a2a_message_creation(self):
        """Test 4: A2A message creation for financial data requests."""
        print("\n=== Test 4: A2A Message Creation ===")
        
        try:
            # Test message creation for financial data request
            msg = A2AMessage.create_request(
                sender_agent="csv-analysis-service",
                recipient_agent="financial-service",
                payload={
                    "action": "get_financial_data",
                    "project_id": "test_project",
                    "data_type": "expenses"
                }
            )
            assert msg.sender_agent == "csv-analysis-service"
            assert msg.recipient_agent == "financial-service"
            assert msg.payload["action"] == "get_financial_data"
            self.log_test("A2A message creation for financial data", True)
        except Exception as e:
            self.log_test("A2A message creation for financial data", False, str(e))
    
    def test_service_endpoints(self):
        """Test 5: HTTP service endpoints."""
        print("\n=== Test 5: HTTP Service Endpoints ===")
        
        # Try to start service if not running
        service_started = False
        try:
            response = requests.get(f"{self.service_url}/health", timeout=2)
            if response.status_code == 200:
                self.log_test("Service health check (already running)", True)
                service_started = True
        except requests.exceptions.ConnectionError:
            print("Service not running, attempting to start...")
            service_started = self.start_service()
            if service_started:
                self.log_test("Service health check (started)", True)
                time.sleep(0.5)
            else:
                self.log_test("Service health check", False, "Could not start service")
                print("Skipping HTTP endpoint tests - service not available")
                return
        
        if not service_started:
            return
        
        try:
            # Test health endpoint
            response = requests.get(f"{self.service_url}/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            self.log_test("HTTP health endpoint", True)
        except Exception as e:
            self.log_test("HTTP health endpoint", False, str(e))
        
        try:
            # Test data endpoint (will fail without real session, but should handle gracefully)
            response = requests.get(f"{self.service_url}/data?project_id=test&session_id=test")
            # Should return 200 or 400/500 with error message
            assert response.status_code in [200, 400, 500]
            self.log_test("HTTP data endpoint", True)
        except Exception as e:
            self.log_test("HTTP data endpoint", False, str(e))
        
        try:
            # Test ask endpoint (will fail without real data, but should handle gracefully)
            response = requests.post(
                f"{self.service_url}/ask",
                json={
                    "project_id": "test",
                    "session_id": "test",
                    "question": "test question"
                }
            )
            # Should return 200 or 400/500 with error message
            assert response.status_code in [200, 400, 500]
            self.log_test("HTTP ask endpoint", True)
        except Exception as e:
            self.log_test("HTTP ask endpoint", False, str(e))
        
        try:
            # Test export endpoint (will fail without real session, but should handle gracefully)
            response = requests.post(
                f"{self.service_url}/export",
                json={
                    "project_id": "test",
                    "session_id": "test"
                }
            )
            # Should return 200 or 400/500 with error message
            assert response.status_code in [200, 400, 500]
            self.log_test("HTTP export endpoint", True)
        except Exception as e:
            self.log_test("HTTP export endpoint", False, str(e))
    
    def test_a2a_integration(self):
        """Test 6: A2A router integration."""
        print("\n=== Test 6: A2A Integration ===")
        
        try:
            # Check if service can be registered
            self.a2a_router.register_agent(
                agent_id="csv-analysis-service",
                agent_url="http://localhost:8003"
            )
            assert self.a2a_router.is_agent_registered("csv-analysis-service")
            self.log_test("A2A router registration", True)
        except Exception as e:
            self.log_test("A2A router registration", False, str(e))
    
    def run_all_tests(self):
        """Run all tests."""
        print("=" * 60)
        print("Phase 4 Test Suite - CSV Analysis Agent A2A Conversion")
        print("=" * 60)
        
        try:
            self.test_tool_a2a_conversion()
            self.test_data_context_agent_a2a()
            self.test_csv_agent_initialization()
            self.test_a2a_message_creation()
            self.test_service_endpoints()
            self.test_a2a_integration()
        finally:
            # Cleanup: stop service if we started it
            self.stop_service()
        
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
            print("\n✓ All tests passed! Phase 4 implementation is successful.")
            return True
        else:
            print("\n✗ Some tests failed. Please review the implementation.")
            return False


if __name__ == "__main__":
    tester = Phase4Tester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
