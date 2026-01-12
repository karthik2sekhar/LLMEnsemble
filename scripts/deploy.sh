#!/bin/bash
# ============================================================================
# LLM Ensemble - AWS EKS Deployment Script
# ============================================================================
# This script automates the entire deployment process to AWS EKS.
# Run this script from the project root directory.
#
# Prerequisites:
# - AWS CLI configured with appropriate credentials
# - eksctl installed
# - kubectl installed
# - Docker installed and running
# ============================================================================

set -e  # Exit on any error

# Configuration - CUSTOMIZE THESE VALUES
export AWS_REGION="us-east-1"
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export CLUSTER_NAME="llm-ensemble-cluster"
export NAMESPACE="llm-ensemble"

# ECR Repository names
export ECR_BACKEND="llm-ensemble-backend"
export ECR_FRONTEND="llm-ensemble-frontend"

echo "=============================================="
echo "🚀 LLM Ensemble - AWS EKS Deployment"
echo "=============================================="
echo "AWS Account: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo "Cluster: $CLUSTER_NAME"
echo ""

# ============================================================================
# STEP 1: Create ECR Repositories
# ============================================================================
echo "📦 Step 1: Creating ECR repositories..."

aws ecr create-repository \
    --repository-name $ECR_BACKEND \
    --region $AWS_REGION \
    --image-scanning-configuration scanOnPush=true \
    2>/dev/null || echo "Backend repository already exists"

aws ecr create-repository \
    --repository-name $ECR_FRONTEND \
    --region $AWS_REGION \
    --image-scanning-configuration scanOnPush=true \
    2>/dev/null || echo "Frontend repository already exists"

echo "✅ ECR repositories ready"

# ============================================================================
# STEP 2: Login to ECR
# ============================================================================
echo ""
echo "🔐 Step 2: Logging into ECR..."

aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

echo "✅ ECR login successful"

# ============================================================================
# STEP 3: Build and Push Docker Images
# ============================================================================
echo ""
echo "🐳 Step 3: Building and pushing Docker images..."

# Backend
echo "Building backend..."
docker build -t $ECR_BACKEND:latest ./backend
docker tag $ECR_BACKEND:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_BACKEND:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_BACKEND:latest

# Frontend
echo "Building frontend..."
docker build \
    --build-arg NEXT_PUBLIC_API_URL=http://llm-backend-service:8000 \
    -t $ECR_FRONTEND:latest ./frontend
docker tag $ECR_FRONTEND:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_FRONTEND:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_FRONTEND:latest

echo "✅ Docker images pushed to ECR"

# ============================================================================
# STEP 4: Create EKS Cluster
# ============================================================================
echo ""
echo "☸️  Step 4: Creating EKS cluster (this takes 15-20 minutes)..."

eksctl create cluster -f k8s/cluster-config.yaml

echo "✅ EKS cluster created"

# ============================================================================
# STEP 5: Install AWS Load Balancer Controller
# ============================================================================
echo ""
echo "🔧 Step 5: Installing AWS Load Balancer Controller..."

# Create IAM OIDC provider
eksctl utils associate-iam-oidc-provider --cluster $CLUSTER_NAME --region $AWS_REGION --approve

# Download IAM policy
curl -o iam-policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.6.1/docs/install/iam_policy.json

# Create IAM policy
aws iam create-policy \
    --policy-name AWSLoadBalancerControllerIAMPolicy \
    --policy-document file://iam-policy.json \
    2>/dev/null || echo "IAM policy already exists"

# Create service account
eksctl create iamserviceaccount \
    --cluster=$CLUSTER_NAME \
    --namespace=kube-system \
    --name=aws-load-balancer-controller \
    --attach-policy-arn=arn:aws:iam::$AWS_ACCOUNT_ID:policy/AWSLoadBalancerControllerIAMPolicy \
    --override-existing-serviceaccounts \
    --region $AWS_REGION \
    --approve

# Install the controller using Helm
helm repo add eks https://aws.github.io/eks-charts
helm repo update
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
    -n kube-system \
    --set clusterName=$CLUSTER_NAME \
    --set serviceAccount.create=false \
    --set serviceAccount.name=aws-load-balancer-controller

# Clean up temp file
rm -f iam-policy.json

echo "✅ AWS Load Balancer Controller installed"

# ============================================================================
# STEP 6: Deploy Application
# ============================================================================
echo ""
echo "🚀 Step 6: Deploying application..."

# Update manifests with actual values
sed -i.bak "s|\${AWS_ACCOUNT_ID}|$AWS_ACCOUNT_ID|g" k8s/backend-deployment.yaml
sed -i.bak "s|\${AWS_REGION}|$AWS_REGION|g" k8s/backend-deployment.yaml
sed -i.bak "s|\${AWS_ACCOUNT_ID}|$AWS_ACCOUNT_ID|g" k8s/frontend-deployment.yaml
sed -i.bak "s|\${AWS_REGION}|$AWS_REGION|g" k8s/frontend-deployment.yaml

# Create namespace
kubectl apply -f k8s/namespace.yaml

# IMPORTANT: Update secrets with your actual API keys
echo ""
echo "⚠️  IMPORTANT: You need to update the API keys in k8s/secrets.yaml"
echo "   Edit the file and replace placeholder values, then run:"
echo "   kubectl apply -f k8s/secrets.yaml"
echo ""

# Apply Kubernetes manifests
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml

# Wait for deployments
echo "Waiting for deployments to be ready..."
kubectl rollout status deployment/llm-backend -n $NAMESPACE --timeout=300s
kubectl rollout status deployment/llm-frontend -n $NAMESPACE --timeout=300s

echo "✅ Application deployed"

# ============================================================================
# STEP 7: Get Application URL
# ============================================================================
echo ""
echo "🌐 Step 7: Getting application URL..."

echo "Waiting for ALB to be provisioned (60 seconds)..."
sleep 60

ALB_URL=$(kubectl get ingress llm-ensemble-ingress -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

echo ""
echo "=============================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo "=============================================="
echo ""
echo "🌐 Application URL: http://$ALB_URL"
echo "🔧 API Health: http://$ALB_URL/api/health"
echo "📊 API Docs: http://$ALB_URL/api/docs"
echo ""
echo "📋 Useful commands:"
echo "   kubectl get pods -n $NAMESPACE"
echo "   kubectl logs -f deployment/llm-backend -n $NAMESPACE"
echo "   kubectl logs -f deployment/llm-frontend -n $NAMESPACE"
echo ""
echo "⚠️  To delete everything when done, run:"
echo "   ./scripts/cleanup.sh"
echo "=============================================="
