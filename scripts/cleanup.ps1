# ============================================================================
# LLM Ensemble - Cleanup Script (PowerShell Version)
# ============================================================================
# This script removes ALL AWS resources created for the deployment.
# Run this when you're done to avoid ongoing charges.
# ============================================================================

$ErrorActionPreference = "Continue"

# Configuration
$AWS_REGION = "us-east-1"
$CLUSTER_NAME = "llm-ensemble-cluster"
$NAMESPACE = "llm-ensemble"
$ECR_BACKEND = "llm-ensemble-backend"
$ECR_FRONTEND = "llm-ensemble-frontend"
$AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)

Write-Host "=============================================="
Write-Host "🧹 LLM Ensemble - Cleanup"
Write-Host "=============================================="
Write-Host ""
Write-Host "⚠️  WARNING: This will delete ALL resources including:"
Write-Host "   - EKS Cluster and all workloads"
Write-Host "   - ECR repositories and images"
Write-Host "   - Load balancers"
Write-Host "   - IAM roles and policies"
Write-Host ""

$confirm = Read-Host "Are you sure you want to continue? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "Cleanup cancelled."
    exit 0
}

Write-Host ""
Write-Host "🗑️  Starting cleanup..."

# ============================================================================
# STEP 1: Delete Kubernetes resources
# ============================================================================
Write-Host ""
Write-Host "Step 1: Deleting Kubernetes resources..."

kubectl delete ingress llm-ensemble-ingress -n $NAMESPACE 2>$null
kubectl delete deployment llm-frontend -n $NAMESPACE 2>$null
kubectl delete deployment llm-backend -n $NAMESPACE 2>$null
kubectl delete service llm-frontend-service -n $NAMESPACE 2>$null
kubectl delete service llm-backend-service -n $NAMESPACE 2>$null
kubectl delete hpa llm-backend-hpa -n $NAMESPACE 2>$null
kubectl delete hpa llm-frontend-hpa -n $NAMESPACE 2>$null
kubectl delete secret llm-api-secrets -n $NAMESPACE 2>$null
kubectl delete configmap llm-config -n $NAMESPACE 2>$null
kubectl delete namespace $NAMESPACE 2>$null

Write-Host "Waiting for load balancer to be deleted (60 seconds)..."
Start-Sleep -Seconds 60

Write-Host "✅ Kubernetes resources deleted"

# ============================================================================
# STEP 2: Delete EKS Cluster
# ============================================================================
Write-Host ""
Write-Host "Step 2: Deleting EKS cluster (this takes 10-15 minutes)..."

eksctl delete cluster --name $CLUSTER_NAME --region $AWS_REGION --wait

Write-Host "✅ EKS cluster deleted"

# ============================================================================
# STEP 3: Delete ECR Repositories
# ============================================================================
Write-Host ""
Write-Host "Step 3: Deleting ECR repositories..."

aws ecr delete-repository --repository-name $ECR_BACKEND --region $AWS_REGION --force 2>$null
aws ecr delete-repository --repository-name $ECR_FRONTEND --region $AWS_REGION --force 2>$null

Write-Host "✅ ECR repositories deleted"

# ============================================================================
# STEP 4: Delete IAM Resources
# ============================================================================
Write-Host ""
Write-Host "Step 4: Cleaning up IAM resources..."

aws iam delete-policy `
    --policy-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:policy/AWSLoadBalancerControllerIAMPolicy" 2>$null

Write-Host "✅ IAM resources cleaned up"

Write-Host ""
Write-Host "=============================================="
Write-Host "🎉 CLEANUP COMPLETE!"
Write-Host "=============================================="
Write-Host ""
Write-Host "All AWS resources have been deleted."
Write-Host "Check your AWS console to verify no orphaned resources."
Write-Host ""
Write-Host "💡 Tip: Also check these services manually:"
Write-Host "   - EC2 > Load Balancers"
Write-Host "   - VPC > NAT Gateways"
Write-Host "   - CloudWatch > Log Groups"
Write-Host "=============================================="
