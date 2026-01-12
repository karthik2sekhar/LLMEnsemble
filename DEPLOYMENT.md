# 🚀 LLM Ensemble - AWS EKS Deployment Guide

## Complete Production Deployment to AWS Kubernetes

This guide walks you through deploying your LLM Ensemble application to AWS EKS (Elastic Kubernetes Service) with CI/CD, monitoring, and auto-scaling.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Cost Breakdown](#cost-breakdown)
3. [Step-by-Step Deployment](#step-by-step-deployment)
4. [GitHub Actions CI/CD Setup](#github-actions-cicd-setup)
5. [Monitoring & Logging](#monitoring--logging)
6. [Troubleshooting](#troubleshooting)
7. [Cleanup Instructions](#cleanup-instructions)
8. [Resume/LinkedIn Update](#resumelinkedin-update)

---

## Prerequisites

### Required Tools
Make sure you have these installed:

```powershell
# Check all prerequisites
aws --version          # AWS CLI v2.x
eksctl version         # eksctl 0.160+
kubectl version        # kubectl 1.28+
docker --version       # Docker 24+
helm version           # Helm 3.x
```

### Installation Commands (if needed)

```powershell
# Install AWS CLI (Windows)
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi

# Install eksctl (Windows - using Chocolatey)
choco install eksctl

# Install kubectl (Windows - using Chocolatey)
choco install kubernetes-cli

# Install Helm (Windows - using Chocolatey)
choco install kubernetes-helm
```

### AWS Configuration

```powershell
# Configure AWS credentials
aws configure

# Enter when prompted:
# AWS Access Key ID: <your-access-key>
# AWS Secret Access Key: <your-secret-key>
# Default region: us-east-1
# Default output format: json

# Verify configuration
aws sts get-caller-identity
```

---

## Cost Breakdown

### Estimated Costs (Running for 24 hours)

| Resource | Type | Hourly Cost | 24h Cost |
|----------|------|-------------|----------|
| EKS Control Plane | Managed | $0.10/hr | $2.40 |
| EC2 Nodes (2x t3.medium spot) | Compute | ~$0.02/hr each | ~$0.96 |
| NAT Gateway | Network | $0.045/hr | $1.08 |
| Application Load Balancer | Network | $0.0225/hr | $0.54 |
| ECR Storage | Storage | ~$0.10/GB | ~$0.20 |
| **Total** | | | **~$5-7** |

### Cost Optimization Tips
- Using **spot instances** saves 60-70% on EC2
- Single NAT gateway (vs one per AZ) saves ~$2/day
- Delete resources promptly after demo

---

## Step-by-Step Deployment

### Step 1: Set Environment Variables

```powershell
# Set your configuration (run in PowerShell)
$env:AWS_REGION = "us-east-1"
$env:CLUSTER_NAME = "llm-ensemble-cluster"
$env:AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)

# Verify
Write-Host "Account: $env:AWS_ACCOUNT_ID, Region: $env:AWS_REGION"
```

### Step 2: Create ECR Repositories

```powershell
# Create repository for backend
aws ecr create-repository `
    --repository-name llm-ensemble-backend `
    --region $env:AWS_REGION `
    --image-scanning-configuration scanOnPush=true

# Create repository for frontend
aws ecr create-repository `
    --repository-name llm-ensemble-frontend `
    --region $env:AWS_REGION `
    --image-scanning-configuration scanOnPush=true

# Verify repositories exist
aws ecr describe-repositories --region $env:AWS_REGION
```

### Step 3: Build and Push Docker Images

```powershell
# Login to ECR
aws ecr get-login-password --region $env:AWS_REGION | docker login --username AWS --password-stdin "$env:AWS_ACCOUNT_ID.dkr.ecr.$env:AWS_REGION.amazonaws.com"

# Build and push backend
cd backend
docker build -t llm-ensemble-backend:latest .
docker tag llm-ensemble-backend:latest "$env:AWS_ACCOUNT_ID.dkr.ecr.$env:AWS_REGION.amazonaws.com/llm-ensemble-backend:latest"
docker push "$env:AWS_ACCOUNT_ID.dkr.ecr.$env:AWS_REGION.amazonaws.com/llm-ensemble-backend:latest"

# Build and push frontend
cd ../frontend
docker build --build-arg NEXT_PUBLIC_API_URL=http://llm-backend-service:8000 -t llm-ensemble-frontend:latest .
docker tag llm-ensemble-frontend:latest "$env:AWS_ACCOUNT_ID.dkr.ecr.$env:AWS_REGION.amazonaws.com/llm-ensemble-frontend:latest"
docker push "$env:AWS_ACCOUNT_ID.dkr.ecr.$env:AWS_REGION.amazonaws.com/llm-ensemble-frontend:latest"

cd ..
```

### Step 4: Create EKS Cluster

⏱️ **This takes 15-20 minutes**

```powershell
# Create the cluster using the config file
eksctl create cluster -f k8s/cluster-config.yaml

# Verify cluster is running
kubectl get nodes
kubectl cluster-info
```

### Step 5: Install AWS Load Balancer Controller

```powershell
# Associate IAM OIDC provider
eksctl utils associate-iam-oidc-provider `
    --cluster $env:CLUSTER_NAME `
    --region $env:AWS_REGION `
    --approve

# Download and create IAM policy
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.6.1/docs/install/iam_policy.json" -OutFile "iam-policy.json"

aws iam create-policy `
    --policy-name AWSLoadBalancerControllerIAMPolicy `
    --policy-document file://iam-policy.json

# Create service account
eksctl create iamserviceaccount `
    --cluster=$env:CLUSTER_NAME `
    --namespace=kube-system `
    --name=aws-load-balancer-controller `
    --attach-policy-arn="arn:aws:iam::$($env:AWS_ACCOUNT_ID):policy/AWSLoadBalancerControllerIAMPolicy" `
    --override-existing-serviceaccounts `
    --region $env:AWS_REGION `
    --approve

# Install using Helm
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm install aws-load-balancer-controller eks/aws-load-balancer-controller `
    -n kube-system `
    --set clusterName=$env:CLUSTER_NAME `
    --set serviceAccount.create=false `
    --set serviceAccount.name=aws-load-balancer-controller

# Verify controller is running
kubectl get deployment -n kube-system aws-load-balancer-controller
```

### Step 6: Update Kubernetes Manifests

```powershell
# Update backend deployment with your ECR image
(Get-Content k8s/backend-deployment.yaml) `
    -replace '\$\{AWS_ACCOUNT_ID\}', $env:AWS_ACCOUNT_ID `
    -replace '\$\{AWS_REGION\}', $env:AWS_REGION | `
    Set-Content k8s/backend-deployment.yaml

# Update frontend deployment with your ECR image
(Get-Content k8s/frontend-deployment.yaml) `
    -replace '\$\{AWS_ACCOUNT_ID\}', $env:AWS_ACCOUNT_ID `
    -replace '\$\{AWS_REGION\}', $env:AWS_REGION | `
    Set-Content k8s/frontend-deployment.yaml
```

### Step 7: Configure API Secrets

**⚠️ IMPORTANT: Update your API keys before deploying!**

```powershell
# Edit k8s/secrets.yaml and replace:
# - "your-openai-api-key-here" with your actual OpenAI API key
# - "your-perplexity-api-key-here" with your actual Perplexity API key

notepad k8s/secrets.yaml
```

### Step 8: Deploy the Application

```powershell
# Apply all Kubernetes manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml

# Watch deployment progress
kubectl get pods -n llm-ensemble -w

# Wait for rollout to complete
kubectl rollout status deployment/llm-backend -n llm-ensemble --timeout=300s
kubectl rollout status deployment/llm-frontend -n llm-ensemble --timeout=300s
```

### Step 9: Get Your Application URL

```powershell
# Wait 60 seconds for ALB to provision
Start-Sleep -Seconds 60

# Get the ALB URL
$ALB_URL = kubectl get ingress llm-ensemble-ingress -n llm-ensemble -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

Write-Host ""
Write-Host "=============================================="
Write-Host "🎉 DEPLOYMENT COMPLETE!"
Write-Host "=============================================="
Write-Host ""
Write-Host "🌐 Application URL: http://$ALB_URL"
Write-Host "🔧 API Health: http://$ALB_URL/api/health"
Write-Host "📊 API Docs: http://$ALB_URL/api/docs"
Write-Host "=============================================="
```

---

## GitHub Actions CI/CD Setup

### Step 1: Add GitHub Secrets

Go to your repository → Settings → Secrets and variables → Actions → New repository secret

Add these secrets:
- `AWS_ACCESS_KEY_ID` - Your AWS access key
- `AWS_SECRET_ACCESS_KEY` - Your AWS secret key
- `OPENAI_API_KEY` - Your OpenAI API key
- `PERPLEXITY_API_KEY` - Your Perplexity API key

### Step 2: Push Changes to Trigger Deployment

```powershell
git add .
git commit -m "Add AWS EKS deployment configuration"
git push origin main
```

The GitHub Action will automatically:
1. Build Docker images
2. Push to ECR
3. Deploy to EKS
4. Output the application URL

---

## Monitoring & Logging

### View Pod Logs

```powershell
# Backend logs
kubectl logs -f deployment/llm-backend -n llm-ensemble

# Frontend logs
kubectl logs -f deployment/llm-frontend -n llm-ensemble

# All pods
kubectl logs -l app=llm-ensemble -n llm-ensemble --all-containers
```

### Check Pod Status

```powershell
# View all pods
kubectl get pods -n llm-ensemble

# Describe a specific pod (for debugging)
kubectl describe pod <pod-name> -n llm-ensemble

# View resource usage
kubectl top pods -n llm-ensemble
```

### CloudWatch Integration

EKS automatically sends logs to CloudWatch. View them:
1. Go to AWS Console → CloudWatch → Log Groups
2. Find `/aws/eks/llm-ensemble-cluster/cluster`

### View HPA Status

```powershell
# Check autoscaling status
kubectl get hpa -n llm-ensemble

# Watch autoscaling events
kubectl describe hpa llm-backend-hpa -n llm-ensemble
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Pods stuck in `Pending` state
```powershell
# Check node resources
kubectl describe nodes

# Check pod events
kubectl describe pod <pod-name> -n llm-ensemble
```
**Solution**: Usually means nodes don't have enough resources. Check HPA and node capacity.

#### 2. Pods in `CrashLoopBackOff`
```powershell
# Check logs
kubectl logs <pod-name> -n llm-ensemble --previous
```
**Solution**: Usually an application error. Check environment variables and secrets.

#### 3. Ingress not getting ALB URL
```powershell
# Check ALB controller logs
kubectl logs -n kube-system deployment/aws-load-balancer-controller
```
**Solution**: Verify IAM permissions and controller installation.

#### 4. Cannot pull images from ECR
```powershell
# Verify ECR repository exists
aws ecr describe-repositories --region $env:AWS_REGION
```
**Solution**: Check IAM role has ECR pull permissions.

#### 5. API returns 502 Bad Gateway
**Solution**: 
- Check backend pods are running
- Verify health check endpoints are working
- Check security group rules

### Useful Debug Commands

```powershell
# Get all resources in namespace
kubectl get all -n llm-ensemble

# Get events (sorted by time)
kubectl get events -n llm-ensemble --sort-by='.lastTimestamp'

# Execute into a pod for debugging
kubectl exec -it <pod-name> -n llm-ensemble -- /bin/sh

# Port forward for local testing
kubectl port-forward service/llm-backend-service 8000:8000 -n llm-ensemble
```

---

## Cleanup Instructions

### ⚠️ IMPORTANT: Delete everything to avoid charges!

```powershell
# Option 1: Use the cleanup script
.\scripts\cleanup.ps1

# Option 2: Manual cleanup

# Step 1: Delete Kubernetes resources (this removes the ALB)
kubectl delete -f k8s/ingress.yaml
kubectl delete -f k8s/hpa.yaml
kubectl delete -f k8s/frontend-deployment.yaml
kubectl delete -f k8s/backend-deployment.yaml
kubectl delete -f k8s/secrets.yaml
kubectl delete -f k8s/namespace.yaml

# Wait for ALB to be deleted
Start-Sleep -Seconds 60

# Step 2: Delete EKS cluster (takes 10-15 minutes)
eksctl delete cluster --name llm-ensemble-cluster --region us-east-1 --wait

# Step 3: Delete ECR repositories
aws ecr delete-repository --repository-name llm-ensemble-backend --region us-east-1 --force
aws ecr delete-repository --repository-name llm-ensemble-frontend --region us-east-1 --force

# Step 4: Delete IAM policy
aws iam delete-policy --policy-arn "arn:aws:iam::$($env:AWS_ACCOUNT_ID):policy/AWSLoadBalancerControllerIAMPolicy"
```

### Verify Cleanup

Check these AWS services manually to ensure no orphaned resources:
- EC2 → Load Balancers
- VPC → NAT Gateways
- CloudWatch → Log Groups
- IAM → Roles (eksctl creates several)

---

## Resume/LinkedIn Update

### LinkedIn Post Template

```
🚀 Just deployed my LLM Ensemble application to AWS EKS!

Built a full-stack intelligent LLM routing system that:
✅ Routes queries between GPT-4, GPT-4o-mini & Perplexity based on complexity
✅ Features "Time-Travel Answers" showing how AI responses evolved over time
✅ Achieves 40-60% cost savings through smart model selection
✅ Auto-scales based on demand

Tech Stack:
• Backend: FastAPI (Python) with async processing
• Frontend: Next.js 15 + React 19 + TypeScript
• Infrastructure: AWS EKS, ECR, ALB, CloudWatch
• CI/CD: GitHub Actions with automated deployments
• Container: Docker with multi-stage builds

Key learnings:
• Kubernetes deployment patterns for microservices
• AWS ALB Ingress Controller configuration
• Cost optimization with spot instances
• Production-ready container security

#AWS #Kubernetes #EKS #DevOps #Python #React #AI #LLM #OpenAI
```

### Resume Bullets

**LLM Ensemble Platform** | Full-Stack Developer
*Personal Project | [Month Year]*

• Designed and deployed an intelligent LLM routing platform to AWS EKS, achieving 40-60% cost reduction through dynamic model selection between GPT-4o, GPT-4o-mini, and Perplexity based on query complexity

• Implemented "Time-Travel Answers" feature using temporal synthesis to show how AI responses evolved across different time periods, demonstrating advanced prompt engineering techniques

• Built production Kubernetes infrastructure with auto-scaling (1-5 pods), Application Load Balancer, and CloudWatch monitoring using eksctl and Helm

• Established CI/CD pipeline with GitHub Actions for automated Docker builds to ECR and rolling deployments to EKS on every push to main branch

• Tech: Python/FastAPI, Next.js 15/React 19, Docker, Kubernetes, AWS (EKS, ECR, ALB, CloudWatch), GitHub Actions

### Skills to Highlight

**Cloud & DevOps:**
- AWS EKS, ECR, ALB, CloudWatch, IAM
- Kubernetes (Deployments, Services, Ingress, HPA, ConfigMaps, Secrets)
- Docker (multi-stage builds, security best practices)
- CI/CD with GitHub Actions
- Infrastructure as Code (eksctl, Helm)

**Backend:**
- Python, FastAPI, async/await
- OpenAI API integration
- Cost optimization strategies

**Frontend:**
- Next.js 15, React 19, TypeScript
- Tailwind CSS
- Real-time streaming responses

---

## Quick Reference Commands

```powershell
# View cluster info
kubectl cluster-info
kubectl get nodes

# View application status
kubectl get pods -n llm-ensemble
kubectl get services -n llm-ensemble
kubectl get ingress -n llm-ensemble

# View logs
kubectl logs -f deployment/llm-backend -n llm-ensemble
kubectl logs -f deployment/llm-frontend -n llm-ensemble

# Scale manually
kubectl scale deployment llm-backend --replicas=3 -n llm-ensemble

# Get application URL
kubectl get ingress llm-ensemble-ingress -n llm-ensemble -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'

# Port forward for local testing
kubectl port-forward service/llm-backend-service 8000:8000 -n llm-ensemble

# Check HPA status
kubectl get hpa -n llm-ensemble
```

---

## Estimated Timeline

| Step | Duration |
|------|----------|
| Prerequisites check | 5 min |
| Create ECR repos | 2 min |
| Build & push images | 5-10 min |
| Create EKS cluster | **15-20 min** |
| Install ALB controller | 5 min |
| Deploy application | 5 min |
| Wait for ALB | 2 min |
| **Total** | **~40-50 min** |

---

## 🎉 Congratulations!

You now have a production-grade Kubernetes deployment that demonstrates:

1. **Container orchestration** with Kubernetes
2. **Cloud infrastructure** on AWS
3. **CI/CD automation** with GitHub Actions
4. **Auto-scaling** based on demand
5. **Production best practices** (health checks, resource limits, security)

This is a significant accomplishment that showcases real-world DevOps skills!
