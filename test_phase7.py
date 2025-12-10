"""
Phase 7 Test Script
Comprehensive tests for Docker Compose setup.
"""

import sys
import os
import time
import requests
import subprocess
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))


class Phase7Tester:
    """Test suite for Phase 7 implementation."""
    
    def __init__(self):
        self.test_results = []
        self.services = {
            'api-gateway': 'http://localhost:5000',
            'financial-service': 'http://localhost:8001',
            'performance-service': 'http://localhost:8002',
            'csv-analysis-service': 'http://localhost:8003',
            'a2a-router-service': 'http://localhost:8004',
            'scheduler-service': 'http://localhost:8005'
        }
        self.docker_compose_file = os.path.join(os.path.dirname(__file__), 'docker-compose.yml')
    
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
    
    def test_docker_compose_file_exists(self):
        """Test 1: Docker Compose file exists."""
        print("\n=== Test 1: Docker Compose File ===")
        
        try:
            if os.path.exists(self.docker_compose_file):
                self.log_test("docker-compose.yml exists", True)
            else:
                self.log_test("docker-compose.yml exists", False, "File not found")
        except Exception as e:
            self.log_test("docker-compose.yml exists", False, str(e))
    
    def test_docker_compose_syntax(self):
        """Test 2: Docker Compose syntax validation."""
        print("\n=== Test 2: Docker Compose Syntax ===")
        
        try:
            result = subprocess.run(
                ['docker-compose', '-f', self.docker_compose_file, 'config'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                self.log_test("Docker Compose syntax validation", True)
            else:
                self.log_test("Docker Compose syntax validation", False, result.stderr)
        except FileNotFoundError:
            self.log_test("Docker Compose syntax validation", False, "docker-compose not installed")
        except Exception as e:
            self.log_test("Docker Compose syntax validation", False, str(e))
    
    def test_all_services_defined(self):
        """Test 3: All services are defined in docker-compose."""
        print("\n=== Test 3: Service Definitions ===")
        
        try:
            with open(self.docker_compose_file, 'r') as f:
                content = f.read()
            
            required_services = [
                'api-gateway',
                'financial-service',
                'performance-service',
                'csv-analysis-service',
                'a2a-router-service',
                'scheduler-service'
            ]
            
            all_found = True
            for service in required_services:
                if service not in content:
                    all_found = False
                    self.log_test(f"Service {service} defined", False, "Not found in docker-compose.yml")
                else:
                    self.log_test(f"Service {service} defined", True)
            
            if all_found:
                self.log_test("All services defined", True)
        except Exception as e:
            self.log_test("All services defined", False, str(e))
    
    def test_network_configuration(self):
        """Test 4: Network configuration."""
        print("\n=== Test 4: Network Configuration ===")
        
        try:
            with open(self.docker_compose_file, 'r') as f:
                content = f.read()
            
            if 'microservices-network' in content:
                self.log_test("Network microservices-network defined", True)
            else:
                self.log_test("Network microservices-network defined", False)
            
            if 'networks:' in content:
                self.log_test("Networks section present", True)
            else:
                self.log_test("Networks section present", False)
        except Exception as e:
            self.log_test("Network configuration", False, str(e))
    
    def test_volume_configuration(self):
        """Test 5: Volume mounts configuration."""
        print("\n=== Test 5: Volume Configuration ===")
        
        try:
            with open(self.docker_compose_file, 'r') as f:
                content = f.read()
            
            if 'chroma_db' in content and 'data' in content:
                self.log_test("Volume mounts configured", True)
            else:
                self.log_test("Volume mounts configured", False, "Missing chroma_db or data volumes")
        except Exception as e:
            self.log_test("Volume configuration", False, str(e))
    
    def test_environment_variables(self):
        """Test 6: Environment variables configuration."""
        print("\n=== Test 6: Environment Variables ===")
        
        try:
            with open(self.docker_compose_file, 'r') as f:
                content = f.read()
            
            # Check for service URL environment variables
            env_vars = [
                'FINANCIAL_SERVICE_URL',
                'PERFORMANCE_SERVICE_URL',
                'CSV_ANALYSIS_SERVICE_URL',
                'A2A_ROUTER_SERVICE_URL',
                'SCHEDULER_SERVICE_URL'
            ]
            
            found_vars = sum(1 for var in env_vars if var in content)
            if found_vars >= 3:  # At least some env vars are set
                self.log_test("Environment variables configured", True)
            else:
                self.log_test("Environment variables configured", False, f"Only {found_vars} env vars found")
        except Exception as e:
            self.log_test("Environment variables", False, str(e))
    
    def test_health_checks(self):
        """Test 7: Health check configurations."""
        print("\n=== Test 7: Health Checks ===")
        
        try:
            with open(self.docker_compose_file, 'r') as f:
                content = f.read()
            
            if 'healthcheck:' in content:
                self.log_test("Health checks configured", True)
            else:
                self.log_test("Health checks configured", False)
        except Exception as e:
            self.log_test("Health checks", False, str(e))
    
    def test_dockerfiles_exist(self):
        """Test 8: All Dockerfiles exist."""
        print("\n=== Test 8: Dockerfiles ===")
        
        dockerfiles = [
            'services/api-gateway/Dockerfile',
            'services/financial-service/Dockerfile',
            'services/performance-service/Dockerfile',
            'services/csv-analysis-service/Dockerfile',
            'services/a2a-router-service/Dockerfile',
            'services/scheduler-service/Dockerfile'
        ]
        
        all_exist = True
        for dockerfile in dockerfiles:
            dockerfile_path = os.path.join(os.path.dirname(__file__), dockerfile)
            if os.path.exists(dockerfile_path):
                self.log_test(f"Dockerfile {dockerfile} exists", True)
            else:
                self.log_test(f"Dockerfile {dockerfile} exists", False, "File not found")
                all_exist = False
        
        if all_exist:
            self.log_test("All Dockerfiles exist", True)
    
    def test_service_dependencies(self):
        """Test 9: Service dependencies configuration."""
        print("\n=== Test 9: Service Dependencies ===")
        
        try:
            with open(self.docker_compose_file, 'r') as f:
                content = f.read()
            
            # Check for depends_on sections
            if 'depends_on:' in content:
                self.log_test("Service dependencies configured", True)
            else:
                self.log_test("Service dependencies configured", False)
        except Exception as e:
            self.log_test("Service dependencies", False, str(e))
    
    def run_all_tests(self):
        """Run all tests."""
        print("=" * 60)
        print("Phase 7 Test Suite - Docker Compose Setup")
        print("=" * 60)
        
        self.test_docker_compose_file_exists()
        self.test_docker_compose_syntax()
        self.test_all_services_defined()
        self.test_network_configuration()
        self.test_volume_configuration()
        self.test_environment_variables()
        self.test_health_checks()
        self.test_dockerfiles_exist()
        self.test_service_dependencies()
        
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
            print("\n✓ All tests passed! Phase 7 implementation is successful.")
            print("\nNext steps:")
            print("  1. Build images: docker-compose build")
            print("  2. Start services: docker-compose up -d")
            print("  3. Check logs: docker-compose logs -f")
            print("  4. Stop services: docker-compose down")
            return True
        else:
            print("\n✗ Some tests failed. Please review the implementation.")
            return False


if __name__ == "__main__":
    tester = Phase7Tester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
