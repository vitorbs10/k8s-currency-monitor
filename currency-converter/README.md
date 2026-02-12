# Currency Converter - Microsserviço de Conversão de Moedas

Microsserviço REST API para converter preços de várias moedas estrangeiras para Real brasileiro (BRL).

## 🌍 Moedas Suportadas

- USD - Dólar Americano
- EUR - Euro
- CAD - Dólar Canadense
- CHF - Franco Suíço
- GBP - Libra Esterlina
- JPY - Iene Japonês
- CNY - Yuan Chinês

## 🚀 Deploy no Kubernetes

### 1. Build da Imagem Docker

```bash
cd currency-converter
docker build -t currency-converter:latest .
```

### 2. Deploy no Kubernetes

```bash
kubectl apply -f k8s-deployment.yaml
```

### 3. Verificar Pods

```bash
kubectl get pods -l app=currency-converter
kubectl logs -l app=currency-converter
```

### 4. Verificar Service

```bash
kubectl get svc currency-converter-service
```

## 📡 Endpoints da API

### GET /health
Health check do serviço (para liveness probe)

```bash
curl http://<SERVICE_IP>/health
```

### GET /ready
Readiness check (verifica se as taxas foram carregadas)

```bash
curl http://<SERVICE_IP>/ready
```

### GET /rates
Retorna todas as taxas de câmbio atuais

```bash
curl http://<SERVICE_IP>/rates
```

Resposta:
```json
{
  "base_currency": "BRL",
  "rates": {
    "USD": 5.45,
    "EUR": 5.92,
    "CAD": 3.98,
    "CHF": 6.23,
    "GBP": 6.89,
    "JPY": 0.037,
    "CNY": 0.75
  },
  "last_update": "2024-02-11T10:30:00",
  "supported_currencies": ["USD", "EUR", "CAD", "CHF", "GBP", "JPY", "CNY"]
}
```

### GET /convert?from=USD&amount=100
Converte de moeda estrangeira para BRL

```bash
curl "http://<SERVICE_IP>/convert?from=USD&amount=100"
```

Resposta:
```json
{
  "from_currency": "USD",
  "to_currency": "BRL",
  "original_amount": 100,
  "converted_amount": 545.0,
  "exchange_rate": 5.45,
  "timestamp": "2024-02-11T10:35:00"
}
```

### GET /convert/reverse?to=USD&amount=545
Converte de BRL para moeda estrangeira

```bash
curl "http://<SERVICE_IP>/convert/reverse?to=USD&amount=545"
```

Resposta:
```json
{
  "from_currency": "BRL",
  "to_currency": "USD",
  "original_amount": 545,
  "converted_amount": 100.0,
  "exchange_rate": 0.1835,
  "timestamp": "2024-02-11T10:35:00"
}
```

## 🧪 Testar Localmente

### Rodar com Docker

```bash
docker run -p 5000:5000 currency-converter:latest
curl http://localhost:5000/rates
```

### Rodar com Python direto

```bash
pip install -r requirements.txt
python app.py
```

## 🔧 Configurações

### Recursos do Pod
- Requests: 128Mi RAM, 100m CPU
- Limits: 256Mi RAM, 500m CPU

### Réplicas
- Padrão: 2 réplicas para alta disponibilidade

### Cache
- As taxas são atualizadas a cada 30 minutos automaticamente
- Usa API gratuita de taxas de câmbio

### API Key (Opcional)
Se quiser usar uma API paga com mais requisições, crie um Secret:

```bash
kubectl create secret generic currency-converter-secret \
  --from-literal=api-key=YOUR_API_KEY
```

E descomente as linhas no deployment para usar o secret.

## 📊 Monitoramento

### Logs
```bash
kubectl logs -f deployment/currency-converter
```

### Métricas
```bash
kubectl top pods -l app=currency-converter
```

### Port Forward para Teste Local
```bash
kubectl port-forward svc/currency-converter-service 8080:80
curl http://localhost:8080/rates
```

## 🔄 Atualizar a Aplicação

```bash
# Rebuild da imagem
docker build -t currency-converter:v2 .

# Atualizar deployment
kubectl set image deployment/currency-converter currency-converter=currency-converter:v2

# Verificar rollout
kubectl rollout status deployment/currency-converter
```

## 🛡️ Segurança

- Usa imagem Python slim (menor superfície de ataque)
- Health checks configurados
- Resource limits definidos
- Readiness probe para evitar tráfego antes de estar pronto

## 📝 Notas

- O serviço é do tipo ClusterIP (acesso interno ao cluster)
- Para expor externamente, mude para LoadBalancer ou crie um Ingress
- As taxas vêm de API pública e podem ter pequenas variações
- Cache de 30 minutos reduz chamadas à API externa
