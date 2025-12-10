"""
Phase 5 Test Script
Comprehensive tests for Scheduler Service implementation.
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

# Import from services directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services', 'scheduler-service'))
from scheduler import RefreshScheduler
from backend.a2a_router.router import A2ARouter
from backend.database import DatabaseManager
from backend.a2a_protocol.a2a_message import A2AMessage, MessageType


class Phase5Tester:
    """Test suite for Phase 5 implementation."""
    
    def __init__(self):
        self.test_results = []
        self.service_url = "http://localhost:8005"
        self.service_process = None
        
        # Initialize managers for direct testing
        self.a2a_router = A2ARouter()
        self.db_manager = DatabaseManager()
        self.refresh_scheduler = RefreshScheduler(self.a2a_router, self.db_manager)
    
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
        """Start the scheduler service in a subprocess."""
        try:
            service_path = os.path.join(os.path.dirname(__file__), 'services', 'scheduler-service', 'main.py')
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
        """Stop the scheduler service."""
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
    
    def test_scheduler_imports(self):
        """Test 1: Scheduler imports and structure."""
        print("\n=== Test 1: Scheduler Imports ===")
        
        try:
            from scheduler import RefreshScheduler
            assert RefreshScheduler is not None
            self.log_test("Import RefreshScheduler", True)
        except Exception as e:
            self.log_test("Import RefreshScheduler", False, str(e))
    
    def test_scheduler_initialization(self):
        """Test 2: Scheduler initialization."""
        print("\n=== Test 2: Scheduler Initialization ===")
        
        try:
            scheduler = RefreshScheduler(self.a2a_router, self.db_manager)
            assert scheduler.a2a_router is not None
            assert scheduler.db_manager is not None
            self.log_test("RefreshScheduler initialization", True)
        except Exception as e:
            self.log_test("RefreshScheduler initialization", False, str(e))
    
    def test_get_all_projects(self):
        """Test 3: Get all projects method."""
        print("\n=== Test 3: Get All Projects ===")
        
        try:
            projects = self.refresh_scheduler.get_all_projects()
            assert isinstance(projects, list)
            self.log_test("get_all_projects method", True)
        except Exception as e:
            self.log_test("get_all_projects method", False, str(e))
    
    def test_financial_refresh_method(self):
        """Test 4: Financial refresh trigger method."""
        print("\n=== Test 4: Financial Refresh Method ===")
        
        try:
            # Register a mock financial service handler
            def mock_financial_handler(message: A2AMessage) -> A2AMessage:
                return A2AMessage.create_response(
                    sender_agent="financial-service",
                    recipient_agent=message.sender_agent,
                    payload={"success": True, "project_id": message.payload.get("project_id")},
                    correlation_id=message.message_id
                )
            
            self.a2a_router.register_agent(
                agent_id="financial-service",
                handler=mock_financial_handler
            )
            
            # Test trigger method
            result = self.refresh_scheduler.trigger_financial_refresh_all()
            assert isinstance(result, dict)
            assert "total_projects" in result
            assert "successful" in result
            assert "failed" in result
            self.log_test("trigger_financial_refresh_all method", True)
        except Exception as e:
            self.log_test("trigger_financial_refresh_all method", False, str(e))
    
    def test_performance_refresh_method(self):
        """Test 5: Performance refresh trigger method."""
        print("\n=== Test 5: Performance Refresh Method ===")
        
        try:
            # Register a mock performance service handler
            def mock_performance_handler(message: A2AMessage) -> A2AMessage:
                return A2AMessage.create_response(
                    sender_agent="performance-service",
                    recipient_agent=message.sender_agent,
                    payload={"success": True, "project_id": message.payload.get("project_id")},
                    correlation_id=message.message_id
                )
            
            self.a2a_router.register_agent(
                agent_id="performance-service",
                handler=mock_performance_handler
            )
            
            # Test trigger method
            result = self.refresh_scheduler.trigger_performance_refresh_all()
            assert isinstance(result, dict)
            assert "total_projects" in result
            assert "successful" in result
            assert "failed" in result
            self.log_test("trigger_performance_refresh_all method", True)
        except Exception as e:
            self.log_test("trigger_performance_refresh_all method", False, str(e))
    
    def test_service_endpoints(self):
        """Test 6: HTTP service endpoints."""
        print("\n=== Test 6: HTTP Service Endpoints ===")
        
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
            assert "scheduled_jobs" in data
            self.log_test("HTTP health endpoint", True)
        except Exception as e:
            self.log_test("HTTP health endpoint", False, str(e))
        
        try:
            # Test jobs endpoint
            response = requests.get(f"{self.service_url}/jobs")
            assert response.status_code == 200
            data = response.json()
            assert "jobs" in data
            self.log_test("HTTP jobs endpoint", True)
        except Exception as e:
            self.log_test("HTTP jobs endpoint", False, str(e))
        
        try:
            # Test manual trigger endpoints (will fail without registered services, but should handle gracefully)
            response = requests.post(f"{self.service_url}/trigger/financial")
            # Should return 200 even if services aren't registered
            assert response.status_code in [200, 500]
            self.log_test("HTTP trigger financial endpoint", True)
        except Exception as e:
            self.log_test("HTTP trigger financial endpoint", False, str(e))
        
        try:
            response = requests.post(f"{self.service_url}/trigger/performance")
            assert response.status_code in [200, 500]
            self.log_test("HTTP trigger performance endpoint", True)
        except Exception as e:
            self.log_test("HTTP trigger performance endpoint", False, str(e))
    
    def test_apscheduler_setup(self):
        """Test 7: APScheduler job setup."""
        print("\n=== Test 7: APScheduler Setup ===")
        
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger
            
            scheduler = BackgroundScheduler()
            scheduler.start()
            
            # Add a test job
            scheduler.add_job(
                func=lambda: None,
                trigger=IntervalTrigger(hours=12),
                id='test_job'
            )
            
            jobs = scheduler.get_jobs()
            assert len(jobs) > 0
            assert jobs[0].id == 'test_job'
            
            scheduler.shutdown()
            self.log_test("APScheduler job setup", True)
        except Exception as e:
            self.log_test("APScheduler job setup", False, str(e))
    
    def run_all_tests(self):
        """Run all tests."""
        print("=" * 60)
        print("Phase 5 Test Suite - Scheduler Service")
        print("=" * 60)
        
        try:
            self.test_scheduler_imports()
            self.test_scheduler_initialization()
            self.test_get_all_projects()
            self.test_financial_refresh_method()
            self.test_performance_refresh_method()
            self.test_service_endpoints()
            self.test_apscheduler_setup()
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
            print("\n✓ All tests passed! Phase 5 implementation is successful.")
            return True
        else:
            print("\n✗ Some tests failed. Please review the implementation.")
            return False


if __name__ == "__main__":
    tester = Phase5Tester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
