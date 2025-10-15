# 🚀 Guia Rápido da API - EcoSys MS

## 📌 Visão Geral

Esta é uma referência rápida para uso da API. Para documentação completa, consulte [API_DOCUMENTATION.md](./API_DOCUMENTATION.md).

---

## 🔗 Base URL

```
Development: http://localhost:8000
Production:  https://api.ecosys.com
```

---

## 🔐 Autenticação

Todos os endpoints (exceto `/` e `/health`) usam **HTTP Basic Auth**.

### Headers
```http
Authorization: Basic base64(username:password)
```

### Exemplo
```bash
curl -u admin:password https://api.ecosys.com/clientes
```

---

## 📍 Endpoints

### 1. Status da API

```bash
GET /
```

**Resposta**:
```json
{
  "message": "API de Gestão de Clientes está no ar!"
}
```

---

### 2. Health Check

```bash
GET /health
```

**Resposta**:
```json
{
  "status": "healthy",
  "environment": "production",
  "redis_connection": "ok",
  "timestamp": "2025-10-15T14:30:00Z"
}
```

---

### 3. Listar Clientes

```bash
GET /clientes
GET /clientes?data_adesao_inicio=2024-01-01
GET /clientes?data_adesao_inicio=2024-01-01&data_adesao_fim=2024-12-31
```

**Parâmetros**:
- `data_adesao_inicio` (opcional): Data inicial (YYYY-MM-DD)
- `data_adesao_fim` (opcional): Data final (YYYY-MM-DD)

**Cache**: 5 minutos

**Resposta**:
```json
{
  "1234": {
    "client_id": 1234,
    "nome": "Empresa XYZ",
    "cnpj": 12345678000190,
    "valor": 1500.00,
    "pipeline": "CS | ONGOING",
    "data_adesao": "2024-03-15T00:00:00",
    ...
  }
}
```

---

### 4. Health Scores

```bash
GET /health-scores
GET /health-scores?data_adesao_inicio=2024-01-01
```

**Parâmetros**:
- `data_adesao_inicio` (opcional): Data inicial (YYYY-MM-DD)
- `data_adesao_fim` (opcional): Data final (YYYY-MM-DD)

**Cache**: 10 minutos

**Resposta**:
```json
{
  "12345": {
    "tenant_id": 12345,
    "slug": "empresa-xyz",
    "name": "Empresa XYZ",
    "score_engajamento": 0.85,
    "score_movimentacao_estoque": 0.92,
    "score_crm": 0.78,
    "score_adoption": 0.88,
    "score_total": 0.86,
    "categoria": "Campeão"
  }
}
```

**Categorias**:
- 🏆 **Campeão**: score > 0.8
- 💚 **Saudável**: 0.6 < score ≤ 0.8
- 🟡 **Normal**: 0.3 < score ≤ 0.6
- 🔴 **Crítico**: score ≤ 0.3

---

### 5. Dashboard (KPIs)

```bash
GET /dashboard
GET /dashboard?data_adesao_inicio=2024-01-01&data_adesao_fim=2024-12-31
```

**Parâmetros**:
- `data_adesao_inicio` (opcional): Data inicial (YYYY-MM-DD)
- `data_adesao_fim` (opcional): Data final (YYYY-MM-DD)

**Cache**: 10 minutos

**Resposta**:
```json
{
  "clientes_ativos": 45,
  "clientes_pagantes": 38,
  "clientes_onboarding": 7,
  "mrr_value": 125000.50,
  "churn_value": 8500.00,
  "tmo_dias": 42.5,
  "clientes_health": {
    "Crítico": 2,
    "Normal": 10,
    "Saudável": 20,
    "Campeão": 13
  }
}
```

**KPIs**:
- `clientes_ativos`: Clientes nas pipelines CS
- `clientes_pagantes`: Clientes ativos com valor > 0
- `clientes_onboarding`: Clientes em onboarding
- `mrr_value`: Monthly Recurring Revenue
- `churn_value`: Valor de clientes em churn
- `tmo_dias`: Tempo Médio de Onboarding (dias)
- `clientes_health`: Distribuição por categoria

---

### 6. Limpar Cache

```bash
POST /cache/clear
```

**Resposta**:
```json
{
  "status": "success",
  "message": "Cache será limpo automaticamente no próximo TTL"
}
```

---

### 7. Histórico de Logins

```bash
GET /logins
Body: {"tenant_id": "12345"}
```

**Body (JSON)**:
```json
{
  "tenant_id": "12345"
}
```

**Resposta**:
```json
{
  "tenant_id": 12345,
  "total_logins": 45,
  "logins": [
    {
      "usuario_nome": "João Silva",
      "usuario_email": "joao@empresa.com",
      "data_login": "2024-10-15T14:30:00"
    }
  ]
}
```

---

## 💻 Exemplos de Código

### Python

```python
import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
AUTH = HTTPBasicAuth('admin', 'password')

# Dashboard
response = requests.get(f"{BASE_URL}/dashboard", auth=AUTH)
data = response.json()
print(f"MRR: R$ {data['mrr_value']:,.2f}")
print(f"TMO: {data['tmo_dias']} dias")

# Clientes de 2024
response = requests.get(
    f"{BASE_URL}/clientes",
    params={'data_adesao_inicio': '2024-01-01', 'data_adesao_fim': '2024-12-31'},
    auth=AUTH
)
clientes = response.json()
print(f"Clientes 2024: {len(clientes)}")

# Health Scores - Clientes Críticos
response = requests.get(f"{BASE_URL}/health-scores", auth=AUTH)
health = response.json()
criticos = [c for c in health.values() if c['categoria'] == 'Crítico']
print(f"Clientes Críticos: {len(criticos)}")
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:8000';
const AUTH = { username: 'admin', password: 'password' };

// Dashboard
async function getDashboard() {
  const response = await axios.get(`${BASE_URL}/dashboard`, { auth: AUTH });
  console.log('MRR:', response.data.mrr_value);
  console.log('TMO:', response.data.tmo_dias, 'dias');
}

// Clientes filtrados
async function getClientesFiltrados() {
  const response = await axios.get(`${BASE_URL}/clientes`, {
    auth: AUTH,
    params: {
      data_adesao_inicio: '2024-01-01',
      data_adesao_fim: '2024-12-31'
    }
  });
  console.log('Total:', Object.keys(response.data).length);
}

getDashboard();
getClientesFiltrados();
```

### cURL

```bash
# Dashboard
curl -u admin:password http://localhost:8000/dashboard

# Dashboard filtrado (2024)
curl -u admin:password \
  "http://localhost:8000/dashboard?data_adesao_inicio=2024-01-01&data_adesao_fim=2024-12-31"

# Clientes
curl -u admin:password http://localhost:8000/clientes

# Health Scores
curl -u admin:password http://localhost:8000/health-scores

# Limpar cache
curl -X POST -u admin:password http://localhost:8000/cache/clear

# Salvar resposta em arquivo
curl -u admin:password http://localhost:8000/clientes > clientes.json

# Com jq (filtrar JSON)
curl -u admin:password http://localhost:8000/dashboard | jq '.mrr_value'
```

---

## 📊 Health Score (Resumo)

### Cálculo

```
Score Total = (
  Engajamento × 30% +
  Estoque × 30% +
  CRM × 20% +
  Adoção × 20%
)
```

### Pilares

| Pilar | Peso | O que mede |
|-------|------|------------|
| 🔥 Engajamento | 30% | Acessos ao sistema |
| 📦 Estoque | 30% | Movimentações de estoque |
| 💼 CRM | 20% | Gestão de leads |
| 🚀 Adoção | 20% | Uso de features avançadas |

---

## ⚡ Performance

### Cache

| Endpoint | TTL | Key Format |
|----------|-----|------------|
| `/clientes` | 5 min | `clientes:{inicio}:{fim}` |
| `/health-scores` | 10 min | `health-scores:{inicio}:{fim}` |
| `/dashboard` | 10 min | `dashboard:{inicio}:{fim}` |

### Response Times

| Operação | Com Cache | Sem Cache |
|----------|-----------|-----------|
| `/clientes` | ~80ms | ~800ms |
| `/health-scores` | ~100ms | ~2.5s |
| `/dashboard` | ~90ms | ~1.2s |

---

## 🐛 Erros Comuns

### 401 Unauthorized

```json
{"detail": "Acesso negado."}
```

**Solução**: Verificar usuário e senha no `.env`

### 500 Internal Server Error

```json
{"detail": "Erro ao obter clientes: connection refused"}
```

**Solução**: Verificar conexão com bancos de dados

### Cache não funciona

**Solução**: 
```bash
# Verificar Redis
curl -X GET \
  -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" \
  $UPSTASH_REDIS_REST_URL/ping
```

---

## 📚 Mais Informações

- **Documentação Completa**: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
- **Dashboard**: [DASHBOARD_DOCS.md](./DASHBOARD_DOCS.md)
- **Health Scores**: [REFACTORING_HEALTH_SCORES.md](./REFACTORING_HEALTH_SCORES.md)
- **Filtros**: [FILTROS_E_TMO_DOCS.md](./FILTROS_E_TMO_DOCS.md)

---

## 🚀 Deploy Rápido

```bash
# 1. Clone e configure
git clone https://github.com/danexplore/ecosysMS-Back.git
cd ecosysMS-Back
cp .env.example .env
# Edite o .env

# 2. Instale dependências
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt

# 3. Execute
uvicorn api.main:app --reload --port 8000

# 4. Teste
curl http://localhost:8000/health
```

---

## 📞 Suporte

- Email: support@ecosys.com
- Issues: [GitHub](https://github.com/danexplore/ecosysMS-Back/issues)

---

**Última atualização**: 15 de Outubro de 2025
