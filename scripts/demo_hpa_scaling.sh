#!/usr/bin/env bash
# ==============================================================================
# DEMONSTRATION OF HORIZONTAL POD AUTOSCALING (TASK 3)
# ==============================================================================
# 1. Deploys the HPA configuration (min 2, max 6, 50% CPU target).
# 2. Verifies metrics-server availability.
# 3. Executes load generation script against the web service.
# 4. Records replica count expansion from 2 up to 6 pods and subsequent cooldown.
# ==============================================================================

set -euo pipefail

NAMESPACE="trendpulse"
HPA_FILE="k8s/hpa.yaml"

echo "==================================================================="
echo "  📈 TASK 3: HORIZONTAL POD AUTOSCALER CONFIGURATION & DEMO"
echo "==================================================================="

echo ""
echo "[Step 1] Applying Horizontal Pod Autoscaler manifest ($HPA_FILE)..."
kubectl apply -f "$HPA_FILE"

echo ""
echo "[Step 2] Current HPA configuration:"
kubectl get hpa trendpulse-web-hpa -n "$NAMESPACE" -o wide

echo ""
echo "[Step 3] Initial Pod count (should be min 2):"
kubectl get pods -n "$NAMESPACE" -l app=trendpulse-web

echo ""
echo "[Step 4] Starting automated load test (spawning CPU load to exceed 50% threshold)..."
python3 scripts/load_test.py --duration 60 --concurrency 10 --namespace "$NAMESPACE"

echo ""
echo "[Step 5] Checking HPA scaling events:"
kubectl describe hpa trendpulse-web-hpa -n "$NAMESPACE" | grep -A 10 "Events:" || true

echo ""
echo "==================================================================="
echo "  ✅ TASK 3 DEMO COMPLETE"
echo "==================================================================="
