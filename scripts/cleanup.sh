#!/bin/bash
# ============================================================================
# LLM Ensemble - Cleanup Script
# ============================================================================
# This script removes ALL AWS resources created for the deployment.
# Run this when you're done to avoid ongoing charges.
# ============================================================================

set -e

# Configuration
export AWS_REGION="us-east-1"
export CLUSTER_NAME="llm-ensemble-cluster"
export NAMESPACE="llm-ensemble"
export ECR_BACKEND="llm-ensemble-backend"
export ECR_FRONTEND="llm-ensemble-frontend"

echo "=============================================="
echo "🧹 LLM Ensemble - Cleanup"
echo "=============================================="
echo ""
echo "⚠️  WARNING: This will delete ALL resources including:"
echo "   - EKS Cluster and all workloads"
echo "   - ECR repositories and images"
echo "   - Load balancers"
echo "   - IAM roles and policies"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "🗑️  Starting cleanup..."

# ============================================================================
# STEP 1: Delete Kubernetes resources
# ============================================================================
echo ""
echo "Step 1: Deleting Kubernetes resources..."

kubectl delete ingress llm-ensemble-ingress -n $NAMESPACE 2>/dev/null || true
kubectl delete deployment llm-frontend -n $NAMESPACE 2>/dev/null || true
kubectl delete deployment llm-backend -n $NAMESPACE 2>/dev/null || true
kubectl delete service llm-frontend-service -n $NAMESPACE 2>/dev/null || true
kubectl delete service llm-backend-service -n $NAMESPACE 2>/dev/null || true
kubectl delete hpa llm-backend-hpa -n $NAMESPACE 2>/dev/null || true
kubectl delete hpa llm-frontend-hpa -n $NAMESPACE 2>/dev/null || true
kubectl delete secret llm-api-secrets -n $NAMESPACE 2>/dev/null || true
kubectl delete configmap llm-config -n $NAMESPACE 2>/dev/null || true
kubectl delete namespace $NAMESPACE 2>/dev/null || true

echo "Waiting for load balancer to be deleted (60 seconds)..."
sleep 60

echo "✅ Kubernetes resources deleted"

# ============================================================================
# STEP 2: Delete EKS Cluster
# ============================================================================
echo ""
echo "Step 2: Deleting EKS cluster (this takes 10-15 minutes)..."

eksctl delete cluster --name $CLUSTER_NAME --region $AWS_REGION --wait

echo "✅ EKS cluster deleted"

# ============================================================================
# STEP 3: Delete ECR Repositories
# ============================================================================
echo ""
echo "Step 3: Deleting ECR repositories..."

aws ecr delete-repository --repository-name $ECR_BACKEND --region $AWS_REGION --force 2>/dev/null || true
aws ecr delete-repository --repository-name $ECR_FRONTEND --region $AWS_REGION --force 2>/dev/null || true

echo "✅ ECR repositories deleted"

# ============================================================================
# STEP 4: Delete IAM Resources
# ============================================================================
echo ""
echo "Step 4: Cleaning up IAM resources..."

# Delete the load balancer controller policy
aws iam delete-policy \
    --policy-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/AWSLoadBalancerControllerIAMPolicy \
    2>/dev/null || true

echo "✅ IAM resources cleaned up"

echo ""
echo "=============================================="
echo "🎉 CLEANUP COMPLETE!"
echo "=============================================="
echo ""
echo "All AWS resources have been deleted."
echo "Check your AWS console to verify no orphaned resources."
echo ""
echo "💡 Tip: Also check these services manually:"
echo "   - EC2 > Load Balancers"
echo "   - VPC > NAT Gateways"
echo "   - CloudWatch > Log Groups"
echo "=============================================="
