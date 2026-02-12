# Currency Converter v2.0 - Microsserviço com PostgreSQL

Microsserviço REST API para converter preços de várias moedas estrangeiras para Real brasileiro (BRL) com armazenamento histórico em PostgreSQL.

## 🌍 Moedas Suportadas

- USD - Dólar Americano
- EUR - Euro
- CAD - Dólar Canadense
- CHF - Franco Suíço
- GBP - Libra Esterlina
- JPY - Iene Japonês
- CNY - Yuan Chinês

## 🆕 Novidades v2.0

- ✅ **Banco de dados PostgreSQL** para armazenamento histórico
- ✅ **Consulta de taxas históricas** por período
- ✅ **Estatísticas diárias** com min/max/média
- ✅ **Consulta de taxa em data específica**
- ✅ **Persistência de dados** com PersistentVolume
- ✅ **Views otimizadas** para consultas rápidas

## 🏗️ Arquitetura

```
┌─────────────────────┐
│   User/Client       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Kubernetes Service │
│   (LoadBalancer)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────┐
│   Currency Converter Pods (2x)      │
│   - Flask REST API                  │
│   - Cache de taxas (30min)          │
│   - Integração com Exchange API     │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│   PostgreSQL StatefulSet            │
│   - Histórico de taxas              │
│   - Estatísticas agregadas          │
│   - PersistentVolume (5GB)          │
└─────────────────────────────────────┘
```

## 🚀 Deploy Rápido

### Opção 1: Script Automatizado

```bash
chmod +x deploy.sh
./deploy.sh
```

### Opção 2: Deploy Manual

```bash
# 1. Build da imagem
docker build -t currency-converter:v2 .

# 2. Deploy PostgreSQL
kubectl apply -f k8s-postgres.yaml

# 3. Aguardar PostgreSQL
kubectl wait --for=condition=ready pod -l app=postgres --timeout=120s

# 4. Deploy da aplicação
kubectl apply -f k8s-deployment-v2.yaml

# 5. Verificar
kubectl get pods
```

## 📡 Endpoints da API

### Endpoints Básicos

#### GET /
Informações sobre a API

```bash
curl http://localhost:8080/
```

#### GET /health
Health check do serviço

```bash
curl http://localhost:8080/health
```

#### GET /rates
Taxas atuais (do cache)

```bash
curl http://localhost:8080/rates
```

Resposta:
```json
{
  "base_currency": "BRL",
  "rates": {
    "USD": 5.45,
    "EUR": 5.92,
    "CAD": 3.98
  },
  "last_update": "2024-02-11T10:30:00",
  "supported_currencies": ["USD", "EUR", "CAD", "CHF", "GBP", "JPY", "CNY"]
}
```

#### GET /rates/latest
Taxas mais recentes do banco de dados

```bash
curl http://localhost:8080/rates/latest
```

### Conversão

#### GET /convert?from=USD&amount=100
Converte moeda estrangeira para BRL

```bash
curl "http://localhost:8080/convert?from=USD&amount=100"
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

#### GET /convert/reverse?to=USD&amount=545
Converte BRL para moeda estrangeira

```bash
curl "http://localhost:8080/convert/reverse?to=USD&amount=545"
```

### 🆕 Endpoints Históricos

#### GET /history/{currency_code}
Histórico de taxas por período

**Parâmetros:**
- `start_date` (opcional): Data inicial (YYYY-MM-DD)
- `end_date` (opcional): Data final (YYYY-MM-DD)

```bash
# Últimos 30 dias (padrão)
curl http://localhost:8080/history/USD

# Período específico
curl "http://localhost:8080/history/USD?start_date=2024-02-01&end_date=2024-02-10"
```

Resposta:
```json
{
  "currency_code": "USD",
  "base_currency": "BRL",
  "start_date": "2024-02-01T00:00:00",
  "end_date": "2024-02-10T23:59:59",
  "data_points": 45,
  "history": [
    {
      "id": 123,
      "currency_code": "USD",
      "rate_to_brl": 5.45,
      "recorded_at": "2024-02-10T14:30:00",
      "source": "exchangerate-api"
    }
  ]
}
```

#### GET /stats/{currency_code}
Estatísticas diárias agregadas

**Parâmetros:**
- `days` (opcional): Número de dias (1-365, padrão: 30)

```bash
# Últimos 30 dias
curl http://localhost:8080/stats/USD

# Últimos 7 dias
curl "http://localhost:8080/stats/USD?days=7"
```

Resposta:
```json
{
  "currency_code": "USD",
  "base_currency": "BRL",
  "days_requested": 7,
  "days_available": 7,
  "stats": [
    {
      "date": "2024-02-10",
      "min_rate": 5.42,
      "max_rate": 5.48,
      "avg_rate": 5.45,
      "sample_count": 12
    }
  ]
}
```

#### GET /rate-at-date/{currency_code}
Taxa em uma data específica

**Parâmetros:**
- `date` (obrigatório): Data desejada (YYYY-MM-DD)

```bash
curl "http://localhost:8080/rate-at-date/USD?date=2024-02-01"
```

Resposta:
```json
{
  "currency_code": "USD",
  "base_currency": "BRL",
  "requested_date": "2024-02-01",
  "rate": 5.43,
  "recorded_at": "2024-02-01T23:45:00"
}
```

## 🗄️ Estrutura do Banco de Dados

### Tabela: exchange_rates
Armazena todas as taxas de câmbio coletadas

```sql
CREATE TABLE exchange_rates (
    id SERIAL PRIMARY KEY,
    currency_code VARCHAR(3) NOT NULL,
    rate_to_brl DECIMAL(12, 6) NOT NULL,
    recorded_at TIMESTAMP NOT NULL,
    source VARCHAR(50) DEFAULT 'exchangerate-api',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Tabela: rate_updates
Log de atualizações

```sql
CREATE TABLE rate_updates (
    id SERIAL PRIMARY KEY,
    update_timestamp TIMESTAMP NOT NULL,
    currencies_updated INTEGER NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT
);
```

### View: latest_rates
Taxas mais recentes de cada moeda

```sql
SELECT DISTINCT ON (currency_code)
    currency_code,
    rate_to_brl,
    recorded_at
FROM exchange_rates
ORDER BY currency_code, recorded_at DESC;
```

### View: daily_rate_stats
Estatísticas diárias agregadas

```sql
SELECT 
    currency_code,
    DATE(recorded_at) as date,
    MIN(rate_to_brl) as min_rate,
    MAX(rate_to_brl) as max_rate,
    AVG(rate_to_brl) as avg_rate,
    COUNT(*) as sample_count
FROM exchange_rates
GROUP BY currency_code, DATE(recorded_at);
```

## 🧪 Testes

### Port Forward para testes locais

```bash
kubectl port-forward svc/currency-converter-service 8080:80
```

### Exemplos de uso

```bash
# Verificar saúde
curl http://localhost:8080/health

# Taxa atual do dólar
curl http://localhost:8080/convert?from=USD&amount=100

# Histórico do euro nos últimos 7 dias
curl "http://localhost:8080/history/EUR?start_date=$(date -d '7 days ago' +%Y-%m-%d)&end_date=$(date +%Y-%m-%d)"

# Estatísticas do iene
curl http://localhost:8080/stats/JPY?days=14

# Taxa da libra em 1º de fevereiro
curl "http://localhost:8080/rate-at-date/GBP?date=2024-02-01"
```

### Acessar PostgreSQL diretamente

```bash
kubectl exec -it postgres-0 -- psql -U currency_user -d currency_db

# Dentro do psql:
\dt                    # Listar tabelas
\d exchange_rates      # Descrever tabela
SELECT * FROM latest_rates;
SELECT * FROM daily_rate_stats WHERE currency_code = 'USD' LIMIT 10;
```

## 🔧 Configurações

### Variáveis de Ambiente - Aplicação

```yaml
PORT: 5000
DB_HOST: postgres-service
DB_PORT: 5432
DB_NAME: currency_db
DB_USER: currency_user
DB_PASSWORD: <from-secret>
EXCHANGE_API_KEY: <optional>
```

### Variáveis de Ambiente - PostgreSQL

```yaml
POSTGRES_DB: currency_db
POSTGRES_USER: currency_user
POSTGRES_PASSWORD: <from-secret>
```

### Recursos Kubernetes

**Aplicação:**
- Requests: 128Mi RAM, 100m CPU
- Limits: 256Mi RAM, 500m CPU
- Réplicas: 2

**PostgreSQL:**
- Requests: 256Mi RAM, 250m CPU
- Limits: 512Mi RAM, 500m CPU
- Storage: 5Gi PersistentVolume

## 📊 Monitoramento

### Logs

```bash
# Logs da aplicação
kubectl logs -f deployment/currency-converter

# Logs do PostgreSQL
kubectl logs -f statefulset/postgres

# Logs de um pod específico
kubectl logs -f currency-converter-xxxxx
```

### Métricas

```bash
# Uso de recursos
kubectl top pods -l app=currency-converter
kubectl top pods -l app=postgres

# Status dos pods
kubectl get pods -w
```

### Verificar dados no banco

```bash
# Contar registros
kubectl exec -it postgres-0 -- psql -U currency_user -d currency_db -c "SELECT currency_code, COUNT(*) FROM exchange_rates GROUP BY currency_code;"

# Ver últimas atualizações
kubectl exec -it postgres-0 -- psql -U currency_user -d currency_db -c "SELECT * FROM rate_updates ORDER BY update_timestamp DESC LIMIT 5;"
```

## 🔄 Atualização e Manutenção

### Atualizar a aplicação

```bash
# Rebuild da imagem
docker build -t currency-converter:v3 .

# Atualizar deployment
kubectl set image deployment/currency-converter currency-converter=currency-converter:v3

# Verificar rollout
kubectl rollout status deployment/currency-converter
```

### Backup do banco de dados

```bash
# Criar backup
kubectl exec postgres-0 -- pg_dump -U currency_user currency_db > backup.sql

# Restaurar backup
cat backup.sql | kubectl exec -i postgres-0 -- psql -U currency_user currency_db
```

### Limpeza de dados antigos

```bash
# Deletar dados com mais de 1 ano
kubectl exec -it postgres-0 -- psql -U currency_user -d currency_db -c "DELETE FROM exchange_rates WHERE recorded_at < NOW() - INTERVAL '1 year';"
```

## 🛡️ Segurança

### Trocar senha do PostgreSQL

```bash
# Deletar secret antigo
kubectl delete secret postgres-secret

# Criar novo secret
kubectl create secret generic postgres-secret \
  --from-literal=POSTGRES_PASSWORD='nova_senha_segura' \
  --from-literal=DB_PASSWORD='nova_senha_segura'

# Reiniciar pods
kubectl rollout restart statefulset/postgres
kubectl rollout restart deployment/currency-converter
```

### Adicionar API Key

```bash
kubectl create secret generic currency-converter-secret \
  --from-literal=api-key='YOUR_API_KEY_HERE'

# Descomentar as linhas no k8s-deployment-v2.yaml
```

## 📝 Notas Importantes

- O PostgreSQL usa StatefulSet para garantir identidade persistente
- Os dados são armazenados em PersistentVolume (não são perdidos ao reiniciar)
- O cache da aplicação é atualizado a cada 30 minutos
- Cada atualização salva as taxas no banco de dados
- As views são atualizadas automaticamente conforme novos dados chegam
- Para produção, considere usar managed database (RDS, CloudSQL, etc.)

## 🚧 Troubleshooting

### Aplicação não conecta ao banco

```bash
# Verificar se o PostgreSQL está rodando
kubectl get pods -l app=postgres

# Verificar logs
kubectl logs -f statefulset/postgres

# Testar conexão manualmente
kubectl run -it --rm debug --image=postgres:16-alpine --restart=Never -- psql -h postgres-service -U currency_user -d currency_db
```

### Sem espaço no PersistentVolume

```bash
# Verificar uso
kubectl exec postgres-0 -- df -h /var/lib/postgresql/data

# Aumentar PVC (se suportado pelo storage class)
kubectl patch pvc postgres-pvc -p '{"spec":{"resources":{"requests":{"storage":"10Gi"}}}}'
```

### Queries lentas

```bash
# Ver queries ativas
kubectl exec -it postgres-0 -- psql -U currency_user -d currency_db -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# Analisar plano de execução
kubectl exec -it postgres-0 -- psql -U currency_user -d currency_db -c "EXPLAIN ANALYZE SELECT * FROM exchange_rates WHERE currency_code = 'USD' AND recorded_at > NOW() - INTERVAL '7 days';"
```

## 🎯 Próximos Passos

- [ ] Adicionar autenticação JWT
- [ ] Implementar rate limiting
- [ ] Adicionar mais fontes de taxas
- [ ] Criar dashboard Grafana
- [ ] Implementar alertas
- [ ] Adicionar testes automatizados
- [ ] Configurar CI/CD
- [ ] Adicionar WebSocket para taxas em tempo real

## 📄 Licença

MIT License - Use como quiser! 🎉
