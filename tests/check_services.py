"""Check service availability."""
import urllib.request
import time
import sys

def check(name, url):
    try:
        r = urllib.request.urlopen(url, timeout=5)
        print(f"  {name}: {r.status} OK")
        return True
    except Exception as e:
        print(f"  {name}: NOT READY ({e})")
        return False

print("Waiting 12s for services to start...")
time.sleep(12)

print("\nChecking services:")
web_ok = check("WEB 3000", "http://localhost:3000/api/kb/catalog")
backend_ok = check("BACKEND 8001", "http://localhost:8001/api/v1/health")

if web_ok and backend_ok:
    print("\nAll services UP!")
    sys.exit(0)
else:
    print("\nSome services not ready, waiting 10s more...")
    time.sleep(10)
    web_ok = check("WEB 3000", "http://localhost:3000/api/kb/catalog")
    backend_ok = check("BACKEND 8001", "http://localhost:8001/api/v1/health")
    if web_ok and backend_ok:
        print("\nAll services UP!")
        sys.exit(0)
    else:
        print("\nServices still not ready")
        sys.exit(1)
