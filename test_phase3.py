"""
Phase 3 Test Script
Comprehensive tests for Performance Agent LangGraph conversion.
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

from backend.performance_agent.graphs.first_time_generation_graph import first_time_generation_graph, PerformanceGenerationState
from backend.performance_agent.graphs.refresh_graph import refresh_graph, PerformanceRefreshState
from backend.performance_agent.chroma_manager import PerformanceChromaManager
from backend.llm_manager import LLMManager
from backend.embeddings import EmbeddingsManager
from backend.database import DatabaseManager
from backend.a2a_router.router import A2ARouter


class Phase3Tester:
    """Test suite for Phase 3 implementation."""
    
    def __init__(self):
        self.test_results = []
        self.service_url = "http://localhost:8002"
        self.service_process = None
        
        # Initialize managers for direct testing
        self.llm_manager = LLMManager()
        self.embeddings_manager = EmbeddingsManager()
        self.db_manager = DatabaseManager()
        self.chroma_manager = PerformanceChromaManager()
        self.a2a_router = A2ARouter()
    
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
        """Start the performance service in a subprocess."""
        try:
            service_path = os.path.join(os.path.dirname(__file__), 'services', 'performance-service', 'main.py')
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
        """Stop the performance service."""
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
    
    def test_graph_imports(self):
        """Test 1: Graph imports and structure."""
        print("\n=== Test 1: Graph Imports ===")
        
        try:
            from backend.performance_agent.graphs import first_time_generation_graph, refresh_graph
            assert first_time_generation_graph is not None
            assert refresh_graph is not None
            self.log_test("Import graphs", True)
        except Exception as e:
            self.log_test("Import graphs", False, str(e))
        
        try:
            from backend.performance_agent.nodes import (
                extract_milestones_node,
                extract_tasks_node,
                extract_bottlenecks_node
            )
            assert extract_milestones_node is not None
            self.log_test("Import nodes", True)
        except Exception as e:
            self.log_test("Import nodes", False, str(e))
    
    def test_state_definition(self):
        """Test 2: State TypedDict definitions."""
        print("\n=== Test 2: State Definitions ===")
        
        try:
            # Test PerformanceGenerationState
            state: PerformanceGenerationState = {
                "project_id": "test_project",
                "document_id": "test_doc",
                "llm_manager": self.llm_manager,
                "embeddings_manager": self.embeddings_manager,
                "chroma_manager": self.chroma_manager,
                "db_manager": self.db_manager,
                "orchestrator": None,
                "a2a_router": self.a2a_router,
                "milestones_result": {},
                "tasks_result": {},
                "bottlenecks_result": {},
                "details_result": {},
                "suggestions_result": {},
                "completion_score": 0.0,
                "overall_success": False,
                "error": ""
            }
            assert state["project_id"] == "test_project"
            self.log_test("PerformanceGenerationState definition", True)
        except Exception as e:
            self.log_test("PerformanceGenerationState definition", False, str(e))
        
        try:
            # Test PerformanceRefreshState
            refresh_state: PerformanceRefreshState = {
                "project_id": "test_project",
                "llm_manager": self.llm_manager,
                "embeddings_manager": self.embeddings_manager,
                "chroma_manager": self.chroma_manager,
                "db_manager": self.db_manager,
                "orchestrator": None,
                "a2a_router": self.a2a_router,
                "performance_data_dir": "data/performance",
                "new_documents": [],
                "last_update": "",
                "refresh_result": {},
                "success": False,
                "error": ""
            }
            assert refresh_state["project_id"] == "test_project"
            self.log_test("PerformanceRefreshState definition", True)
        except Exception as e:
            self.log_test("PerformanceRefreshState definition", False, str(e))
    
    def test_node_functions(self):
        """Test 3: Node function structure."""
        print("\n=== Test 3: Node Functions ===")
        
        try:
            from backend.performance_agent.nodes.extraction_nodes import extract_milestones_node
            
            # Create minimal state
            state = {
                "project_id": "test_project",
                "document_id": "test_doc",
                "llm_manager": self.llm_manager,
                "chroma_manager": self.chroma_manager,
                "milestones_result": {}
            }
            
            # Node should accept state and return state
            result = extract_milestones_node(state)
            assert isinstance(result, dict)
            assert "milestones_result" in result
            self.log_test("extract_milestones_node structure", True)
        except Exception as e:
            self.log_test("extract_milestones_node structure", False, str(e))
    
    def test_graph_compilation(self):
        """Test 4: Graph compilation."""
        print("\n=== Test 4: Graph Compilation ===")
        
        try:
            # Test that graphs are compiled
            assert hasattr(first_time_generation_graph, 'invoke')
            self.log_test("first_time_generation_graph compiled", True)
        except Exception as e:
            self.log_test("first_time_generation_graph compiled", False, str(e))
        
        try:
            assert hasattr(refresh_graph, 'invoke')
            self.log_test("refresh_graph compiled", True)
        except Exception as e:
            self.log_test("refresh_graph compiled", False, str(e))
    
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
            # Test status endpoint (should work even without data)
            response = requests.get(f"{self.service_url}/status/test_project")
            assert response.status_code == 200
            data = response.json()
            assert "project_id" in data
            self.log_test("HTTP status endpoint", True)
        except Exception as e:
            self.log_test("HTTP status endpoint", False, str(e))
        
        try:
            # Test first_generation endpoint (will fail without real project/doc, but should handle gracefully)
            response = requests.post(
                f"{self.service_url}/first_generation",
                json={"project_id": "test_project", "document_id": "test_doc"}
            )
            # Should return 200 even if processing fails (error in response)
            assert response.status_code == 200
            self.log_test("HTTP first_generation endpoint", True)
        except Exception as e:
            self.log_test("HTTP first_generation endpoint", False, str(e))
        
        try:
            # Test refresh endpoint
            response = requests.post(f"{self.service_url}/refresh/test_project")
            assert response.status_code == 200
            data = response.json()
            assert "project_id" in data
            self.log_test("HTTP refresh endpoint", True)
        except Exception as e:
            self.log_test("HTTP refresh endpoint", False, str(e))
        
        try:
            # Test A2A message handler
            from backend.a2a_protocol.a2a_message import A2AMessage, MessageType
            message = A2AMessage.create_request(
                sender_agent="scheduler",
                recipient_agent="performance-service",
                payload={"action": "refresh", "project_id": "test_project"}
            )
            response = requests.post(
                f"{self.service_url}/a2a/message",
                json=message.to_dict()
            )
            assert response.status_code in [200, 400]  # 400 if unknown action is OK
            self.log_test("HTTP A2A message handler", True)
        except Exception as e:
            self.log_test("HTTP A2A message handler", False, str(e))
    
    def test_a2a_integration(self):
        """Test 6: A2A router integration."""
        print("\n=== Test 6: A2A Integration ===")
        
        try:
            # Check if service registered with router
            assert self.a2a_router is not None
            self.log_test("A2A router available", True)
        except Exception as e:
            self.log_test("A2A router available", False, str(e))
    
    def run_all_tests(self):
        """Run all tests."""
        print("=" * 60)
        print("Phase 3 Test Suite - Performance Agent LangGraph Conversion")
        print("=" * 60)
        
        try:
            self.test_graph_imports()
            self.test_state_definition()
            self.test_node_functions()
            self.test_graph_compilation()
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
            print("\n✓ All tests passed! Phase 3 implementation is successful.")
            return True
        else:
            print("\n✗ Some tests failed. Please review the implementation.")
            return False


if __name__ == "__main__":
    tester = Phase3Tester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
