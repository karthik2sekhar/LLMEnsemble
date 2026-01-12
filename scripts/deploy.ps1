# ============================================================================
# LLM Ensemble - AWS EKS Deployment Script (PowerShell Version)
# ============================================================================
# Run this script from the project root directory on Windows.
# Prerequisites: AWS CLI, eksctl, kubectl, Docker Desktop
# ============================================================================

$ErrorActionPreference = "Stop"

# Configuration - CUSTOMIZE THESE VALUES
$AWS_REGION = "us-east-1"
$AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
$CLUSTER_NAME = "llm-ensemble-cluster"
$NAMESPACE = "llm-ensemble"
$ECR_BACKEND = "llm-ensemble-backend"
$ECR_FRONTEND = "llm-ensemble-frontend"

Write-Host "=============================================="
Write-Host "🚀 LLM Ensemble - AWS EKS Deployment"
Write-Host "=============================================="
Write-Host "AWS Account: $AWS_ACCOUNT_ID"
Write-Host "Region: $AWS_REGION"
Write-Host "Cluster: $CLUSTER_NAME"
Write-Host ""

# ============================================================================
# STEP 1: Create ECR Repositories
# ============================================================================
Write-Host "📦 Step 1: Creating ECR repositories..."

try {
    aws ecr create-repository `
        --repository-name $ECR_BACKEND `
        --region $AWS_REGION `
        --image-scanning-configuration scanOnPush=true 2>$null
} catch { Write-Host "Backend repository already exists" }

try {
    aws ecr create-repository `
        --repository-name $ECR_FRONTEND `
        --region $AWS_REGION `
        --image-scanning-configuration scanOnPush=true 2>$null
} catch { Write-Host "Frontend repository already exists" }

Write-Host "✅ ECR repositories ready"

# ============================================================================
# STEP 2: Login to ECR
# ============================================================================
Write-Host ""
Write-Host "🔐 Step 2: Logging into ECR..."

$ECR_PASSWORD = aws ecr get-login-password --region $AWS_REGION
docker login --username AWS --password $ECR_PASSWORD "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

Write-Host "✅ ECR login successful"

# ============================================================================
# STEP 3: Build and Push Docker Images
# ============================================================================
Write-Host ""
Write-Host "🐳 Step 3: Building and pushing Docker images..."

# Backend
Write-Host "Building backend..."
docker build -t "${ECR_BACKEND}:latest" ./backend
docker tag "${ECR_BACKEND}:latest" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/${ECR_BACKEND}:latest"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/${ECR_BACKEND}:latest"

# Frontend
Write-Host "Building frontend..."
docker build `
    --build-arg NEXT_PUBLIC_API_URL=http://llm-backend-service:8000 `
    -t "${ECR_FRONTEND}:latest" ./frontend
docker tag "${ECR_FRONTEND}:latest" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/${ECR_FRONTEND}:latest"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/${ECR_FRONTEND}:latest"

Write-Host "✅ Docker images pushed to ECR"

# ============================================================================
# STEP 4: Create EKS Cluster
# ============================================================================
Write-Host ""
Write-Host "☸️  Step 4: Creating EKS cluster (this takes 15-20 minutes)..."

eksctl create cluster -f k8s/cluster-config.yaml

Write-Host "✅ EKS cluster created"

# ============================================================================
# STEP 5: Install AWS Load Balancer Controller
# ============================================================================
Write-Host ""
Write-Host "🔧 Step 5: Installing AWS Load Balancer Controller..."

# Create IAM OIDC provider
eksctl utils associate-iam-oidc-provider --cluster $CLUSTER_NAME --region $AWS_REGION --approve

# Download IAM policy
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.6.1/docs/install/iam_policy.json" -OutFile "iam-policy.json"

# Create IAM policy
try {
    aws iam create-policy `
        --policy-name AWSLoadBalancerControllerIAMPolicy `
        --policy-document file://iam-policy.json 2>$null
} catch { Write-Host "IAM policy already exists" }

# Create service account
eksctl create iamserviceaccount `
    --cluster=$CLUSTER_NAME `
    --namespace=kube-system `
    --name=aws-load-balancer-controller `
    --attach-policy-arn="arn:aws:iam::${AWS_ACCOUNT_ID}:policy/AWSLoadBalancerControllerIAMPolicy" `
    --override-existing-serviceaccounts `
    --region $AWS_REGION `
    --approve

# Install the controller using Helm
helm repo add eks https://aws.github.io/eks-charts
helm repo update
helm install aws-load-balancer-controller eks/aws-load-balancer-controller `
    -n kube-system `
    --set clusterName=$CLUSTER_NAME `
    --set serviceAccount.create=false `
    --set serviceAccount.name=aws-load-balancer-controller

# Clean up temp file
Remove-Item -Path "iam-policy.json" -ErrorAction SilentlyContinue

Write-Host "✅ AWS Load Balancer Controller installed"

# ============================================================================
# STEP 6: Deploy Application
# ============================================================================
Write-Host ""
Write-Host "🚀 Step 6: Deploying application..."

# Update manifests with actual values
$backendYaml = Get-Content "k8s/backend-deployment.yaml" -Raw
$backendYaml = $backendYaml -replace '\$\{AWS_ACCOUNT_ID\}', $AWS_ACCOUNT_ID
$backendYaml = $backendYaml -replace '\$\{AWS_REGION\}', $AWS_REGION
$backendYaml | Set-Content "k8s/backend-deployment.yaml"

$frontendYaml = Get-Content "k8s/frontend-deployment.yaml" -Raw
$frontendYaml = $frontendYaml -replace '\$\{AWS_ACCOUNT_ID\}', $AWS_ACCOUNT_ID
$frontendYaml = $frontendYaml -replace '\$\{AWS_REGION\}', $AWS_REGION
$frontendYaml | Set-Content "k8s/frontend-deployment.yaml"

# Create namespace
kubectl apply -f k8s/namespace.yaml

Write-Host ""
Write-Host "⚠️  IMPORTANT: Update API keys in k8s/secrets.yaml before continuing!"
Write-Host "   Edit the file and replace placeholder values."
Read-Host "Press Enter when ready..."

# Apply Kubernetes manifests
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml

# Wait for deployments
Write-Host "Waiting for deployments to be ready..."
kubectl rollout status deployment/llm-backend -n $NAMESPACE --timeout=300s
kubectl rollout status deployment/llm-frontend -n $NAMESPACE --timeout=300s

Write-Host "✅ Application deployed"

# ============================================================================
# STEP 7: Get Application URL
# ============================================================================
Write-Host ""
Write-Host "🌐 Step 7: Getting application URL..."

Write-Host "Waiting for ALB to be provisioned (60 seconds)..."
Start-Sleep -Seconds 60

$ALB_URL = kubectl get ingress llm-ensemble-ingress -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

Write-Host ""
Write-Host "=============================================="
Write-Host "🎉 DEPLOYMENT COMPLETE!"
Write-Host "=============================================="
Write-Host ""
Write-Host "🌐 Application URL: http://$ALB_URL"
Write-Host "🔧 API Health: http://$ALB_URL/api/health"
Write-Host "📊 API Docs: http://$ALB_URL/api/docs"
Write-Host ""
Write-Host "📋 Useful commands:"
Write-Host "   kubectl get pods -n $NAMESPACE"
Write-Host "   kubectl logs -f deployment/llm-backend -n $NAMESPACE"
Write-Host "   kubectl logs -f deployment/llm-frontend -n $NAMESPACE"
Write-Host ""
Write-Host "⚠️  To delete everything when done, run:"
Write-Host "   .\scripts\cleanup.ps1"
Write-Host "=============================================="
