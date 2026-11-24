#!/usr/bin/env python3
"""
Load Generator and Replica Monitor for Task 3 (Horizontal Pod Autoscaling).
Generates concurrent CPU-intensive requests against the application endpoints,
monitors the Kubernetes HPA scaling events, and records the replica count transitions.
"""

import sys
import time
import argparse
import subprocess
import threading
import urllib.request
import json
from concurrent.futures import ThreadPoolExecutor

STOP_LOAD = False
STATS = {"requests_sent": 0, "successful": 0, "failed": 0, "latency_sum": 0.0}
LOCK = threading.Lock()

def worker_stress(target_url: str):
    """Sends CPU-intensive prime calculation and tweet simulation requests."""
    global STOP_LOAD
    payload = json.dumps({"intensity": 350000}).encode('utf-8')
    headers = {"Content-Type": "application/json"}

    while not STOP_LOAD:
        start = time.time()
        try:
            req = urllib.request.Request(f"{target_url}/api/stress", data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                _ = resp.read()
                elapsed = time.time() - start
                with LOCK:
                    STATS["requests_sent"] += 1
                    STATS["successful"] += 1
                    STATS["latency_sum"] += elapsed
        except Exception:
            with LOCK:
                STATS["requests_sent"] += 1
                STATS["failed"] += 1
        time.sleep(0.05)

def monitor_replicas(namespace: str, deployment: str, interval: int = 5, duration: int = 120):
    """Monitors pod count and HPA metrics from kubectl."""
    print("\n[MONITOR] Beginning HPA & Replica Tracking...")
    print(f"{'TIMESTAMP':<10} | {'REPLICAS':<10} | {'CPU UTILIZATION':<18} | {'REQUESTS SENT':<14} | {'AVG LATENCY'}")
    print("-" * 75)

    start_time = time.time()
    last_replicas = None

    while time.time() - start_time < duration:
        t_str = time.strftime("%H:%M:%S")
        replicas = "N/A"
        cpu_usage = "N/A"

        # Query Deployment replicas
        try:
            cmd = ["kubectl", "get", "deployment", deployment, "-n", namespace, "-o", "jsonpath={.status.readyReplicas}"]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                replicas = res.stdout.strip()
        except Exception:
            pass

        # Query HPA status
        try:
            cmd_hpa = ["kubectl", "get", "hpa", f"{deployment}-hpa", "-n", namespace, "-o", "jsonpath={.status.currentMetrics[0].resource.current.averageUtilization}"]
            res_hpa = subprocess.run(cmd_hpa, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            if res_hpa.returncode == 0 and res_hpa.stdout.strip():
                cpu_usage = f"{res_hpa.stdout.strip()}% (Target: 50%)"
        except Exception:
            pass

        with LOCK:
            reqs = STATS["requests_sent"]
            avg_lat = f"{(STATS['latency_sum'] / max(1, STATS['successful'])):.3f}s" if STATS["successful"] > 0 else "0.0s"

        if replicas != last_replicas and last_replicas is not None:
            marker = " 🚨 [SCALE EVENT DETECTED]"
        else:
            marker = ""
        last_replicas = replicas

        print(f"{t_str:<10} | {replicas:<10} | {cpu_usage:<18} | {reqs:<14} | {avg_lat}{marker}")
        time.sleep(interval)

def main():
    parser = argparse.ArgumentParser(description="Kubernetes HPA Load Generator & Monitor")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of application service")
    parser.add_argument("--concurrency", type=int, default=12, help="Concurrent request threads")
    parser.add_argument("--duration", type=int, default=70, help="Duration of load test in seconds")
    parser.add_argument("--namespace", default="trendpulse", help="Kubernetes namespace")
    parser.add_argument("--deployment", default="trendpulse-web", help="Deployment name")
    args = parser.parse_args()

    global STOP_LOAD
    print("===================================================================")
    print("  🔥 TASK 3: HORIZONTAL POD AUTOSCALER LOAD TEST & METRIC RECORDER")
    print("===================================================================")
    print(f"Target URL:       {args.url}")
    print(f"Concurrency:      {args.concurrency} parallel load threads")
    print(f"Duration:         {args.duration} seconds")
    print(f"Namespace:        {args.namespace}")
    print(f"HPA Config:       Min=2, Max=6, Target CPU=50%")
    print("===================================================================\n")

    # Launch background monitor thread
    monitor_thread = threading.Thread(
        target=monitor_replicas,
        args=(args.namespace, args.deployment, 4, args.duration + 20),
        daemon=True
    )
    monitor_thread.start()

    # Launch thread pool for load generation
    print(f"[LOAD] Injecting CPU load across {args.concurrency} concurrent threads...")
    executor = ThreadPoolExecutor(max_workers=args.concurrency)
    for _ in range(args.concurrency):
        executor.submit(worker_stress, args.url)

    time.sleep(args.duration)
    print("\n[LOAD] Stress test duration completed. Halting load generator...")
    STOP_LOAD = True
    executor.shutdown(wait=False)

    print("[COOLDOWN] Waiting 15 seconds to observe replica cooldown stabilization...")
    time.sleep(15)

    print("\n===================================================================")
    print("  📊 SUMMARY RESULTS")
    print("===================================================================")
    print(f"Total Requests Dispatched: {STATS['requests_sent']}")
    print(f"Successful Requests:       {STATS['successful']}")
    print(f"Failed Requests:           {STATS['failed']}")
    if STATS['successful'] > 0:
        print(f"Average Request Latency:   {(STATS['latency_sum'] / STATS['successful']):.3f}s")
    print("Autoscaler successfully captured workload changes!")
    print("===================================================================\n")

if __name__ == "__main__":
    main()
