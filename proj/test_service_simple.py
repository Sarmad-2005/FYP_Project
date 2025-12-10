"""Simple test to verify service can start."""
import sys
import os
import time
import requests
import subprocess

sys.path.insert(0, os.path.dirname(__file__))

print("Testing service startup...")

service_path = os.path.join(os.path.dirname(__file__), 'services', 'a2a-router-service', 'main.py')
print(f"Service path: {service_path}")
print(f"Exists: {os.path.exists(service_path)}")

if os.path.exists(service_path):
    print("Starting service...")
    process = subprocess.Popen(
        [sys.executable, service_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(__file__)
    )
    
    print("Waiting for service to start...")
    max_attempts = 10
    started = False
    for i in range(max_attempts):
        try:
            response = requests.get("http://localhost:8000/health", timeout=1)
            if response.status_code == 200:
                print("✓ Service started successfully!")
                print(f"Response: {response.json()}")
                started = True
                break
        except:
            time.sleep(0.5)
            print(f"Attempt {i+1}/{max_attempts}...")
    
    if started:
        print("✓ HTTP endpoint test passed!")
        process.terminate()
        process.wait(timeout=5)
        print("✓ Service stopped cleanly")
    else:
        print("✗ Service failed to start")
        process.terminate()
        if process.poll() is None:
            process.kill()
else:
    print("✗ Service file not found")
