#!/bin/bash

# Script de deploy completo para Currency Converter com PostgreSQL

set -e

echo "=== Currency Converter - Deploy Script ==="
echo ""

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para imprimir mensagens
print_step() {
    echo -e "${GREEN}>>> $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}>>> $1${NC}"
}

# 1. Build da imagem Docker
print_step "1. Building Docker image..."
docker build -t currency-converter:v2 .
echo ""

# 2. Deploy do PostgreSQL
print_step "2. Deploying PostgreSQL..."
kubectl apply -f k8s-postgres.yaml

# Aguarda o PostgreSQL estar pronto
print_step "3. Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres --timeout=120s
echo ""

# 4. Deploy da aplicação
print_step "4. Deploying Currency Converter application..."
kubectl apply -f k8s-deployment-v2.yaml

# Aguarda os pods estarem prontos
print_step "5. Waiting for application pods to be ready..."
kubectl wait --for=condition=ready pod -l app=currency-converter --timeout=120s
echo ""

# 6. Verificações
print_step "6. Deployment verification..."
echo ""
echo "PostgreSQL Status:"
kubectl get pods -l app=postgres
echo ""
echo "Application Status:"
kubectl get pods -l app=currency-converter
echo ""
echo "Services:"
kubectl get svc -l app=currency-converter
kubectl get svc -l app=postgres
echo ""

# 7. Instruções de teste
print_step "7. Testing instructions:"
echo ""
echo "To test the API, run:"
echo "  kubectl port-forward svc/currency-converter-service 8080:80"
echo ""
echo "Then in another terminal:"
echo "  curl http://localhost:8080/"
echo "  curl http://localhost:8080/rates"
echo "  curl http://localhost:8080/history/USD?start_date=2024-02-01"
echo "  curl http://localhost:8080/stats/USD?days=7"
echo ""

print_step "Deployment completed successfully! ✓"
