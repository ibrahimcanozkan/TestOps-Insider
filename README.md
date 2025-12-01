# Insider TestOps Project

Selenium test automation for Insider website using Docker and Kubernetes.

## Test Cases

1. Homepage verification (`useinsider.com`)
2. Careers page navigation and blocks
3. QA jobs filtering (Istanbul, Turkey + Quality Assurance)
4. Job details validation
5. Lever application redirect

## System Overview

### How Test Controller Works

Test Controller Pod executes test cases remotely on Chrome Node Pods using Selenium WebDriver protocol.

**Flow:**
1. Test Controller starts and connects to `chrome-node-service:4444/wd/hub`
2. Kubernetes service routes connection to available Chrome Node
3. Test Controller sends Selenium commands (click, type, navigate, etc.)
4. Chrome Node executes commands in headless Chrome browser
5. Results return to Test Controller for logging

### Inter-Pod Communication

Communication happens via **Kubernetes DNS Service Discovery**:

- Chrome Nodes are exposed through a ClusterIP service
- Service DNS: `chrome-node-service:4444`
- Test Controller uses this DNS to connect (no hardcoded IPs)
- Service automatically load balances across available Chrome Nodes

## Deployment Steps

### Deploy to AWS EKS

```bash
# 1. Create EKS cluster
eksctl create cluster --name insider-test-cluster --region us-east-1 --nodes 2
aws eks update-kubeconfig --name insider-test-cluster --region us-east-1

# 2. Build and push images to ECR
export AWS_ACCOUNT_ID=<your-account-id>

# Build images
docker build -f test-controller/Dockerfile -t insider-tests:controller test-controller/
docker build -f chrome-node/Dockerfile -t insider-tests:chrome-node chrome-node/

# Tag and push to ECR
ECR_REPO="$AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/insider-tests"
aws ecr create-repository --repository-name insider-tests --region us-east-1 || true
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_REPO

docker tag insider-tests:controller $ECR_REPO:controller
docker tag insider-tests:chrome-node $ECR_REPO:chrome-node
docker push $ECR_REPO:controller
docker push $ECR_REPO:chrome-node

# 3. Deploy to Kubernetes
python3 deploy.py --aws-account-id $AWS_ACCOUNT_ID --region us-east-1 --node-count 2
```
> **Note:** The `deploy.py` script automatically replaces `ACCOUNT_ID` and `REGION` placeholders in YAML files with your AWS credentials.

### Deploy Locally (Minikube/Kind)

```bash
# 1. Start local cluster
minikube start

# 2. Build images locally
docker build -f test-controller/Dockerfile -t insider-tests:controller test-controller/
docker build -f chrome-node/Dockerfile -t insider-tests:chrome-node chrome-node/

# 3. Deploy to Kubernetes
kubectl apply -f k8s/chrome-node/
kubectl apply -f k8s/test-controller/
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
│                                                              │
│  ┌──────────────────────┐                                   │
│  │  Test Controller Pod │                                   │
│  │  ┌────────────────┐  │                                   │
│  │  │ test_controller│  │                                   │
│  │  │     .py        │──┼─────┐                            │
│  │  └────────────────┘  │     │                            │
│  └──────────────────────┘     │                            │
│                               │ HTTP (Selenium WebDriver)   │
│                               │                            │
│                               ▼                            │
│  ┌──────────────────────────────────────────────────┐      │
│  │     chrome-node-service (ClusterIP)             │      │
│  │     DNS: chrome-node-service:4444               │      │
│  └──────────────────────────────────────────────────┘      │
│                               │                            │
│              ┌────────────────┼────────────────┐           │
│              │                │                │           │
│              ▼                ▼                ▼           │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐   │
│  │ Chrome Node 1 │ │ Chrome Node 2 │ │ Chrome Node N │   │
│  │  (Selenium)   │ │  (Selenium)   │ │  (Selenium)   │   │
│  │   Port 4444   │ │   Port 4444   │ │   Port 4444   │   │
│  └───────────────┘ └───────────────┘ └───────────────┘   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```
