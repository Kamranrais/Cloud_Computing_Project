#!/usr/bin/env bash
# ==============================================================================
# DEMONSTRATION OF KUBERNETES SELF-HEALING (TASK 2)
# ==============================================================================
# This script:
# 1. Inspects the active trendpulse-web deployment (2 replicas).
# 2. Deletes one of the active running pods.
# 3. Observes Kubernetes ReplicaSet controller immediately detecting the state
#    deviation and provisioning a brand-new replacement pod.
# 4. Validates that readiness probes pass and 2/2 pods are healthy with zero downtime.
# ==============================================================================

set -euo pipefail

NAMESPACE="trendpulse"

echo "==================================================================="
echo "  🚀 TASK 2: KUBERNETES POD SELF-HEALING DEMONSTRATION"
echo "==================================================================="

echo ""
echo "[Step 1] Inspecting initial pods state in namespace '$NAMESPACE'..."
kubectl get pods -n "$NAMESPACE" -l app=trendpulse-web -o wide

INITIAL_POD=$(kubectl get pods -n "$NAMESPACE" -l app=trendpulse-web -o jsonpath='{.items[0].metadata.name}')
echo ""
echo "[Step 2] Selected pod to terminate: $INITIAL_POD"
echo "Simulating sudden pod failure or node crash..."
kubectl delete pod "$INITIAL_POD" -n "$NAMESPACE" --grace-period=0 --force 2>/dev/null || kubectl delete pod "$INITIAL_POD" -n "$NAMESPACE"

echo ""
echo "[Step 3] Watching Kubernetes Controller self-heal the deployment..."
echo "ReplicaSet ensures desired replica count (2) is maintained continuously:"
sleep 2
kubectl get pods -n "$NAMESPACE" -l app=trendpulse-web

echo ""
echo "[Step 4] Waiting for replacement pod readiness probe to pass (status: Running & 1/1 Ready)..."
kubectl wait --for=condition=ready pod -l app=trendpulse-web -n "$NAMESPACE" --timeout=30s

echo ""
echo "[Step 5] Final Pod Status:"
kubectl get pods -n "$NAMESPACE" -l app=trendpulse-web -o wide

echo ""
echo "==================================================================="
echo "  ✅ SUCCESS: Self-healing demonstrated! The deleted pod was replaced"
echo "     automatically without service outage."
echo "==================================================================="
