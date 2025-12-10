"""
Phase 1 Test Script
Comprehensive tests for A2A Protocol and Router implementation.
"""

import sys
import os
import json
import time
import requests
import threading
import subprocess
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from backend.a2a_protocol.a2a_message import A2AMessage, MessageType, Priority
from backend.a2a_router.router import A2ARouter


class Phase1Tester:
    """Test suite for Phase 1 implementation."""
    
    def __init__(self):
        self.router = A2ARouter()
        self.test_results = []
        self.service_url = "http://localhost:8000"
        self.service_thread = None
        self.service_app = None
        self.service_process = None
    
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
    
    def test_message_creation(self):
        """Test 1: A2AMessage creation and validation."""
        print("\n=== Test 1: Message Creation ===")
        
        try:
            # Test request message
            msg = A2AMessage.create_request(
                sender_agent="test_agent_1",
                recipient_agent="test_agent_2",
                payload={"action": "get_data", "params": {"id": 123}},
                priority=Priority.HIGH
            )
            assert msg.sender_agent == "test_agent_1"
            assert msg.recipient_agent == "test_agent_2"
            assert msg.message_type == MessageType.REQUEST
            assert msg.requires_response is True
            self.log_test("Create request message", True)
        except Exception as e:
            self.log_test("Create request message", False, str(e))
        
        try:
            # Test response message
            response = A2AMessage.create_response(
                sender_agent="test_agent_2",
                recipient_agent="test_agent_1",
                payload={"data": "result"},
                correlation_id="test_correlation_id"
            )
            assert response.message_type == MessageType.RESPONSE
            assert response.correlation_id == "test_correlation_id"
            self.log_test("Create response message", True)
        except Exception as e:
            self.log_test("Create response message", False, str(e))
        
        try:
            # Test notification message
            notification = A2AMessage.create_notification(
                sender_agent="test_agent_1",
                payload={"event": "update_complete"}
            )
            assert notification.message_type == MessageType.NOTIFICATION
            assert notification.recipient_agent == ""
            self.log_test("Create notification message", True)
        except Exception as e:
            self.log_test("Create notification message", False, str(e))
        
        try:
            # Test error message
            error = A2AMessage.create_error(
                sender_agent="router",
                recipient_agent="test_agent_1",
                error_message="Test error",
                error_code="TEST_ERROR"
            )
            assert error.message_type == MessageType.ERROR
            assert "error" in error.payload
            self.log_test("Create error message", True)
        except Exception as e:
            self.log_test("Create error message", False, str(e))
        
        try:
            # Test validation - should fail without sender
            try:
                invalid_msg = A2AMessage(sender_agent="")
                self.log_test("Message validation (empty sender)", False, "Should have raised ValueError")
            except ValueError:
                self.log_test("Message validation (empty sender)", True)
        except Exception as e:
            self.log_test("Message validation (empty sender)", False, str(e))
    
    def test_message_serialization(self):
        """Test 2: Message serialization and deserialization."""
        print("\n=== Test 2: Message Serialization ===")
        
        try:
            original = A2AMessage.create_request(
                sender_agent="agent_a",
                recipient_agent="agent_b",
                payload={"test": "data"},
                metadata={"key": "value"}
            )
            
            # Test to_dict
            msg_dict = original.to_dict()
            assert isinstance(msg_dict, dict)
            assert msg_dict["sender_agent"] == "agent_a"
            self.log_test("Message to_dict", True)
        except Exception as e:
            self.log_test("Message to_dict", False, str(e))
        
        try:
            # Test to_json
            json_str = original.to_json()
            assert isinstance(json_str, str)
            parsed = json.loads(json_str)
            assert parsed["sender_agent"] == "agent_a"
            self.log_test("Message to_json", True)
        except Exception as e:
            self.log_test("Message to_json", False, str(e))
        
        try:
            # Test from_dict
            restored = A2AMessage.from_dict(msg_dict)
            assert restored.sender_agent == original.sender_agent
            assert restored.recipient_agent == original.recipient_agent
            assert restored.message_type == original.message_type
            self.log_test("Message from_dict", True)
        except Exception as e:
            self.log_test("Message from_dict", False, str(e))
        
        try:
            # Test from_json
            restored_json = A2AMessage.from_json(json_str)
            assert restored_json.sender_agent == original.sender_agent
            assert restored_json.payload == original.payload
            self.log_test("Message from_json", True)
        except Exception as e:
            self.log_test("Message from_json", False, str(e))
    
    def test_router_registration(self):
        """Test 3: Router agent registration."""
        print("\n=== Test 3: Router Registration ===")
        
        try:
            # Register agent
            self.router.register_agent(
                agent_id="test_agent_1",
                agent_url="http://localhost:8001",
                metadata={"type": "test"}
            )
            assert self.router.is_agent_registered("test_agent_1")
            self.log_test("Register agent", True)
        except Exception as e:
            self.log_test("Register agent", False, str(e))
        
        try:
            # Check agent info
            info = self.router.get_agent_info("test_agent_1")
            assert info is not None
            assert info["agent_id"] == "test_agent_1"
            self.log_test("Get agent info", True)
        except Exception as e:
            self.log_test("Get agent info", False, str(e))
        
        try:
            # List agents
            agents = self.router.list_agents()
            assert "test_agent_1" in agents
            self.log_test("List agents", True)
        except Exception as e:
            self.log_test("List agents", False, str(e))
        
        try:
            # Unregister agent
            self.router.unregister_agent("test_agent_1")
            assert not self.router.is_agent_registered("test_agent_1")
            self.log_test("Unregister agent", True)
        except Exception as e:
            self.log_test("Unregister agent", False, str(e))
    
    def test_router_message_routing(self):
        """Test 4: Router message routing."""
        print("\n=== Test 4: Message Routing ===")
        
        # Setup test handler
        received_messages = []
        
        def test_handler(message: A2AMessage) -> A2AMessage:
            received_messages.append(message)
            return A2AMessage.create_response(
                sender_agent=message.recipient_agent,
                recipient_agent=message.sender_agent,
                payload={"status": "received", "original": message.payload},
                correlation_id=message.message_id
            )
        
        try:
            # Register agent with handler
            self.router.register_agent(
                agent_id="test_agent_2",
                handler=test_handler
            )
            self.log_test("Register agent with handler", True)
        except Exception as e:
            self.log_test("Register agent with handler", False, str(e))
        
        try:
            # Send message
            request_msg = A2AMessage.create_request(
                sender_agent="test_agent_1",
                recipient_agent="test_agent_2",
                payload={"test": "message"}
            )
            response = self.router.send_message(request_msg)
            
            assert response is not None
            assert response.message_type == MessageType.RESPONSE
            assert response.correlation_id == request_msg.message_id
            assert len(received_messages) == 1
            self.log_test("Send message and receive response", True)
        except Exception as e:
            self.log_test("Send message and receive response", False, str(e))
        
        try:
            # Test error handling - unregistered recipient
            error_msg = A2AMessage.create_request(
                sender_agent="test_agent_1",
                recipient_agent="nonexistent_agent",
                payload={"test": "data"}
            )
            error_response = self.router.send_message(error_msg)
            assert error_response is not None
            assert error_response.message_type == MessageType.ERROR
            self.log_test("Error handling for unregistered agent", True)
        except Exception as e:
            self.log_test("Error handling for unregistered agent", False, str(e))
    
    def test_router_history(self):
        """Test 5: Router message history."""
        print("\n=== Test 5: Message History ===")
        
        try:
            # Get history
            history = self.router.get_message_history()
            assert isinstance(history, list)
            self.log_test("Get message history", True)
        except Exception as e:
            self.log_test("Get message history", False, str(e))
        
        try:
            # Filter by agent
            filtered = self.router.get_message_history(agent_id="test_agent_1")
            assert isinstance(filtered, list)
            self.log_test("Filter history by agent", True)
        except Exception as e:
            self.log_test("Filter history by agent", False, str(e))
        
        try:
            # Filter by message type
            filtered = self.router.get_message_history(message_type=MessageType.REQUEST)
            assert isinstance(filtered, list)
            self.log_test("Filter history by message type", True)
        except Exception as e:
            self.log_test("Filter history by message type", False, str(e))
        
        try:
            # Get stats
            stats = self.router.get_stats()
            assert "total_agents" in stats
            assert "total_messages" in stats
            self.log_test("Get router stats", True)
        except Exception as e:
            self.log_test("Get router stats", False, str(e))
    
    def start_service(self):
        """Start the A2A router service in a subprocess."""
        try:
            service_path = os.path.join(os.path.dirname(__file__), 'services', 'a2a-router-service', 'main.py')
            if not os.path.exists(service_path):
                return False
            
            # Start service in subprocess
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
            
            # If we get here, service didn't start
            if self.service_process:
                self.service_process.terminate()
                self.service_process = None
            return False
        except Exception as e:
            print(f"Warning: Could not start service: {e}")
            return False
    
    def stop_service(self):
        """Stop the A2A router service."""
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
            else:
                self.log_test("Service health check", False, "Could not start service")
                print("Skipping HTTP endpoint tests - service not available")
                return
        except Exception as e:
            self.log_test("Service health check", False, str(e))
            return
        
        # Give service a moment to be ready
        if service_started:
            time.sleep(0.5)
        
        # Cleanup function to stop service at end
        try:
            # Register agent via HTTP
            response = requests.post(
                f"{self.service_url}/register",
                json={
                    "agent_id": "http_test_agent",
                    "agent_url": "http://localhost:8001",
                    "metadata": {"test": True}
                }
            )
            assert response.status_code == 201
            self.log_test("HTTP register agent", True)
        except Exception as e:
            self.log_test("HTTP register agent", False, str(e))
        
        try:
            # List agents via HTTP
            response = requests.get(f"{self.service_url}/agents")
            assert response.status_code == 200
            data = response.json()
            assert "agents" in data
            assert "http_test_agent" in data["agents"]
            self.log_test("HTTP list agents", True)
        except Exception as e:
            self.log_test("HTTP list agents", False, str(e))
        
        try:
            # Send message via HTTP
            message = A2AMessage.create_request(
                sender_agent="http_sender",
                recipient_agent="http_test_agent",
                payload={"test": "http_message"}
            )
            response = requests.post(
                f"{self.service_url}/send",
                json=message.to_dict()
            )
            assert response.status_code == 200
            self.log_test("HTTP send message", True)
        except Exception as e:
            self.log_test("HTTP send message", False, str(e))
        
        try:
            # Get history via HTTP
            response = requests.get(f"{self.service_url}/history?limit=10")
            assert response.status_code == 200
            data = response.json()
            assert "history" in data
            self.log_test("HTTP get history", True)
        except Exception as e:
            self.log_test("HTTP get history", False, str(e))
        
        try:
            # Get stats via HTTP
            response = requests.get(f"{self.service_url}/stats")
            assert response.status_code == 200
            data = response.json()
            assert "total_agents" in data
            self.log_test("HTTP get stats", True)
        except Exception as e:
            self.log_test("HTTP get stats", False, str(e))
        
        try:
            # Unregister agent via HTTP
            response = requests.delete(f"{self.service_url}/unregister/http_test_agent")
            assert response.status_code == 200
            self.log_test("HTTP unregister agent", True)
        except Exception as e:
            self.log_test("HTTP unregister agent", False, str(e))
    
    def run_all_tests(self):
        """Run all tests."""
        print("=" * 60)
        print("Phase 1 Test Suite - A2A Protocol and Router")
        print("=" * 60)
        
        try:
            self.test_message_creation()
            self.test_message_serialization()
            self.test_router_registration()
            self.test_router_message_routing()
            self.test_router_history()
            self.test_service_endpoints()
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
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        if passed == total:
            print("\n✓ All tests passed! Phase 1 implementation is successful.")
            return True
        else:
            print("\n✗ Some tests failed. Please review the implementation.")
            return False


if __name__ == "__main__":
    tester = Phase1Tester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
