#!/usr/bin/env python3
"""
Python verification script to test and simulate Hybrid Cloud Failover logic.
Can run standalone or against the live docker-compose / k8s environment.
"""

import time
import json
import urllib.request
import urllib.error

def test_endpoint(url: str, description: str):
    print(f"\n[TEST] {description} -> {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HybridFailoverTester/1.0"})
        start = time.time()
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = resp.read().decode('utf-8')
            elapsed = round((time.time() - start) * 1000, 2)
            try:
                parsed = json.loads(data)
                print(f"  Status: HTTP 200 OK ({elapsed}ms)")
                print(f"  Cluster Env: {parsed.get('cluster_env', 'N/A')}")
                print(f"  Tier:        {parsed.get('deployment_tier', 'N/A')}")
                print(f"  Pod Host:    {parsed.get('pod_name', 'N/A')}")
                return parsed
            except json.JSONDecodeError:
                print(f"  Status: HTTP 200 OK (Non-JSON response, length: {len(data)})")
                return {"raw": data}
    except urllib.error.HTTPError as e:
        print(f"  HTTP Error {e.code}: {e.reason}")
        return None
    except Exception as e:
        print(f"  Connection Error: {e}")
        return None

if __name__ == "__main__":
    print("===================================================================")
    print("  🌐 HYBRID CLOUD ROUTER & CLUSTERS HEALTH VERIFIER")
    print("===================================================================")
    test_endpoint("http://localhost:8000/api/system-info", "Direct Web App (Standalone / Port 8000)")
    test_endpoint("http://localhost:8080/api/system-info", "Hybrid Router Gateway (Port 8080)")
    test_endpoint("http://localhost:30080/api/system-info", "Kubernetes NodePort Primary (Port 30080)")
    test_endpoint("http://localhost:30090/api/system-info", "Kubernetes NodePort Hybrid Router (Port 30090)")
    print("\nHealth checks complete.")
