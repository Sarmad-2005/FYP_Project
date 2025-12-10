import requests

BASE = "http://localhost:5000"

def check_health():
    r = requests.get(f"{BASE}/health", timeout=5)
    print("/health", r.status_code, r.text[:200])

def post_expect_400(path):
    r = requests.post(f"{BASE}{path}", json={}, timeout=5)
    print(path, r.status_code, r.text[:200])

def main():
    check_health()
    post_expect_400("/performance_agent/extract_requirements")
    post_expect_400("/performance_agent/extract_actors")

if __name__ == "__main__":
    main()
