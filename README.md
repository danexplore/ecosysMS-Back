# 🚀 EcoSys MS - API de Gestão de Clientes

API RESTful completa para análise e gestão de clientes do sistema EcoSys, com cálculo de Health Scores, KPIs e métricas de negócio.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Redis](https://img.shields.io/badge/Redis-Cache-red.svg)](https://redis.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange.svg)](https://www.mysql.com/)

---

## 📋 Índice

- [Features](#-features)
- [Quick Start](#-quick-start)
- [Endpoints](#-endpoints)
- [Documentação](#-documentação)
- [Arquitetura](#-arquitetura)
- [Configuração](#️-configuração)
- [Exemplos](#-exemplos)

---

## ✨ Features

### 🎯 Core
- **Health Scores**: Cálculo automatizado baseado em 4 pilares (Engajamento, Estoque, CRM, Adoção)
- **Dashboard KPIs**: Métricas agregadas em tempo real (MRR, Churn, TMO, etc)
- **Gestão de Clientes**: CRUD completo com dados do Kommo CRM
- **Filtros Avançados**: Filtrar por data de adesão em todos os endpoints

### ⚡ Performance
- **Cache Distribuído**: Redis com TTL configurável (5-10 minutos)
- **Queries Otimizadas**: Connection pooling e queries paralelas
- **Compressão GZIP**: Redução de até 70% no tamanho das respostas
- **Async Processing**: ThreadPoolExecutor para operações bloqueantes

### 🔒 Segurança
- **HTTP Basic Auth**: Autenticação em todos os endpoints protegidos
- **CORS Configurável**: Controle de origens permitidas
- **Validação de Dados**: Pydantic models para tipo-safe

### 📊 Métricas
- **TMO (Tempo Médio de Onboarding)**: Análise automática do processo
- **Categorização de Clientes**: Crítico, Normal, Saudável, Campeão
- **Distribuição de Health**: Visão geral da saúde da base

---

## 🚀 Quick Start

### Pré-requisitos

```bash
Python 3.9+
PostgreSQL 15+
MySQL 8.0+
Redis (Upstash)
```

### Instalação

```bash
# Clone o repositório
git clone https://github.com/danexplore/ecosysMS-Back.git
cd ecosysMS-Back

# Crie o ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais
```

### Configurar `.env`

```bash
# Redis Cache
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-token

# Autenticação
BASIC_AUTH_USERS=admin:admin123,user:pass123

# PostgreSQL (Kommo)
DB_NAME=kommo_db
DB_USER=postgres
DB_PASSWORD=yourpass
DB_HOST=localhost
DB_PORT=5432

# MySQL (EcoSys)
DB_HOST_ECOSYS=localhost
DB_NAME_ECOSYS=ecosys_db
DB_USER_ECOSYS=root
DB_PASSWORD_ECOSYS=yourpass

# Ambiente
ENVIRONMENT=development
```

### Executar

```bash
# Desenvolvimento (com reload)
uvicorn api.main:app --reload --port 8000

# Produção
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Testar

```bash
# Health check
curl http://localhost:8000/health

# Endpoint protegido
curl -u admin:admin123 http://localhost:8000/dashboard
```

---

## 🔌 Endpoints

| Endpoint | Método | Auth | Descrição |
|----------|--------|------|-----------|
| `/` | GET | ❌ | Status da API |
| `/health` | GET | ❌ | Health check completo |
| `/clientes` | GET | ✅ | Lista de clientes com filtros |
| `/health-scores` | GET | ✅ | Health scores de todos os clientes |
| `/dashboard` | GET | ✅ | KPIs agregados do sistema |
| `/cache/clear` | POST | ✅ | Limpar cache |
| `/logins` | GET | ✅ | Histórico de logins por tenant |

### Query Parameters (Filtros)

Disponíveis em: `/clientes`, `/health-scores`, `/dashboard`

| Parâmetro | Tipo | Formato | Exemplo |
|-----------|------|---------|---------|
| `data_adesao_inicio` | string | YYYY-MM-DD | 2024-01-01 |
| `data_adesao_fim` | string | YYYY-MM-DD | 2024-12-31 |

---

## 📚 Documentação

### Documentação Completa

📖 **[API_DOCUMENTATION.md](./API_DOCUMENTATION.md)** - Documentação técnica completa
- Todos os endpoints detalhados
- Modelos de dados
- Sistema de Health Scores (4 pilares)
- Sistema de cache
- Exemplos em Python, JavaScript, cURL
- Troubleshooting completo

### Documentos Específicos

- 📊 **[DASHBOARD_DOCS.md](./DASHBOARD_DOCS.md)** - Dashboard e KPIs
- 🔧 **[REFACTORING_HEALTH_SCORES.md](./REFACTORING_HEALTH_SCORES.md)** - Refatoração do health scores
- 📅 **[FILTROS_E_TMO_DOCS.md](./FILTROS_E_TMO_DOCS.md)** - Filtros por data e TMO

---

## 🏗️ Arquitetura

### Estrutura do Projeto

```
ecosysMS-Back/
├── api/
│   ├── main.py              # FastAPI app principal
│   ├── lib/
│   │   ├── models.py        # Modelos Pydantic
│   │   └── queries.py       # Queries SQL
│   └── scripts/
│       ├── clientes.py      # Gestão de clientes
│       ├── health_scores.py # Cálculo de health scores
│       └── dashboard.py     # KPIs do dashboard
├── requirements.txt         # Dependências Python
├── .env.example            # Template de variáveis
└── README.md               # Este arquivo
```

### Stack Tecnológico

```
┌─────────────────┐
│   FastAPI App   │ ← API REST
└────────┬────────┘
         │
    ┌────┴────┐
    │  Redis  │ ← Cache (5-10 min TTL)
    └────┬────┘
         │
    ┌────┴────────────┐
    │   PostgreSQL    │ ← Clientes (Kommo CRM)
    │   MySQL         │ ← Dados EcoSys (Activity, Inventory)
    └─────────────────┘
```

### Fluxo de Requisição

```
Cliente HTTP
    ↓
[Auth Middleware] → Valida credenciais
    ↓
[Cache Check] → Redis
    ↓
[Cache Hit?]
    ├─ Sim → Retorna dados (< 100ms)
    └─ Não → Busca no banco
              ↓
          [Processa dados] → Pandas
              ↓
          [Salva cache] → Redis
              ↓
          [Retorna JSON] → Cliente
```

---

## 🛠️ Configuração

### Variáveis de Ambiente

| Variável | Descrição | Obrigatório |
|----------|-----------|-------------|
| `UPSTASH_REDIS_REST_URL` | URL do Redis Upstash | ✅ |
| `UPSTASH_REDIS_REST_TOKEN` | Token do Redis | ✅ |
| `BASIC_AUTH_USERS` | Usuários (formato: user:pass,user2:pass2) | ✅ |
| `DB_NAME` | Nome do banco PostgreSQL | ✅ |
| `DB_USER` | Usuário PostgreSQL | ✅ |
| `DB_PASSWORD` | Senha PostgreSQL | ✅ |
| `DB_HOST` | Host PostgreSQL | ✅ |
| `DB_PORT` | Porta PostgreSQL | ✅ |
| `DB_HOST_ECOSYS` | Host MySQL | ✅ |
| `DB_NAME_ECOSYS` | Nome do banco MySQL | ✅ |
| `DB_USER_ECOSYS` | Usuário MySQL | ✅ |
| `DB_PASSWORD_ECOSYS` | Senha MySQL | ✅ |
| `ENVIRONMENT` | Ambiente (development/production) | ❌ |

### Cache TTL

Configurável em `api/main.py`:

```python
CACHE_TTL_CLIENTES = 300       # 5 minutos
CACHE_TTL_HEALTH_SCORES = 600  # 10 minutos
```

---

## 💡 Exemplos

### Dashboard com Python

```python
import requests
from requests.auth import HTTPBasicAuth

# Configuração
BASE_URL = "http://localhost:8000"
AUTH = HTTPBasicAuth('admin', 'admin123')

# Buscar KPIs gerais
response = requests.get(f"{BASE_URL}/dashboard", auth=AUTH)
dashboard = response.json()

print(f"Clientes Ativos: {dashboard['clientes_ativos']}")
print(f"MRR: R$ {dashboard['mrr_value']:,.2f}")
print(f"TMO: {dashboard['tmo_dias']} dias")
print(f"Health Distribution: {dashboard['clientes_health']}")

# Buscar KPIs de 2024
response = requests.get(
    f"{BASE_URL}/dashboard",
    params={
        'data_adesao_inicio': '2024-01-01',
        'data_adesao_fim': '2024-12-31'
    },
    auth=AUTH
)
dashboard_2024 = response.json()
print(f"Clientes 2024: {dashboard_2024['clientes_ativos']}")
```

### Health Scores com JavaScript

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:8000';
const AUTH = { username: 'admin', password: 'admin123' };

async function getClientesCriticos() {
  const response = await axios.get(`${BASE_URL}/health-scores`, { auth: AUTH });
  const healthScores = response.data;
  
  const criticos = Object.entries(healthScores)
    .filter(([_, cliente]) => cliente.categoria === 'Crítico')
    .map(([tenantId, cliente]) => ({
      tenantId,
      nome: cliente.name,
      score: cliente.score_total,
      ultimoAcesso: cliente.dias_desde_ultimo_acesso
    }));
  
  console.log(`Clientes Críticos: ${criticos.length}`);
  criticos.forEach(c => {
    console.log(`- ${c.nome}: Score ${c.score}, ${c.ultimoAcesso} dias sem acesso`);
  });
}

getClientesCriticos();
```

### cURL - Clientes de 2024

```bash
curl -u admin:admin123 \
  "http://localhost:8000/clientes?data_adesao_inicio=2024-01-01&data_adesao_fim=2024-12-31" \
  | jq 'length'
```

---

## 📊 Health Scores

### 4 Pilares

| Pilar | Peso | Métricas |
|-------|------|----------|
| 🔥 **Engajamento** | 30% | Acessos nos últimos 30 dias, dias desde último acesso |
| 📦 **Estoque** | 30% | Entradas/saídas nos últimos 30 dias, frequência |
| 💼 **CRM** | 20% | Leads criados, oportunidades, frequência |
| 🚀 **Adoção** | 20% | Integrações ativas, features avançadas |

### Categorias

```
🏆 Campeão  (>0.8)  - Clientes exemplares
💚 Saudável (0.6-0.8) - Clientes saudáveis  
🟡 Normal   (0.3-0.6) - Precisam atenção
🔴 Crítico  (≤0.3)   - Risco de churn
```

### Fórmula

```python
score_total = (
  score_engajamento × 0.30 +
  score_estoque × 0.30 +
  score_crm × 0.20 +
  score_adoption × 0.20
)
```

---

## 🔧 Troubleshooting

### API não inicia

```bash
# Verificar variáveis de ambiente
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Redis:', bool(os.getenv('UPSTASH_REDIS_REST_URL')))"

# Testar conexão com bancos
psql -h $DB_HOST -U $DB_USER -d $DB_NAME
mysql -h $DB_HOST_ECOSYS -u $DB_USER_ECOSYS -p
```

### Cache não funciona

```bash
# Verificar Redis
curl -X GET \
  -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" \
  $UPSTASH_REDIS_REST_URL/ping

# Limpar cache manualmente
curl -X POST -u admin:admin123 http://localhost:8000/cache/clear
```

### Erro 401 Unauthorized

```bash
# Verificar formato do BASIC_AUTH_USERS
echo $BASIC_AUTH_USERS
# Deve ser: user1:pass1,user2:pass2

# Testar autenticação
curl -u admin:admin123 http://localhost:8000/clientes
```

---

## 🧪 Testes

```bash
# Executar todos os testes
pytest

# Testar endpoint específico
pytest tests/test_clientes.py

# Com cobertura
pytest --cov=api tests/
```

---

## 📈 Performance

### Benchmarks

| Operação | Sem Cache | Com Cache | Melhoria |
|----------|-----------|-----------|----------|
| `/clientes` | ~800ms | ~80ms | **10x** |
| `/health-scores` | ~2.5s | ~100ms | **25x** |
| `/dashboard` | ~1.2s | ~90ms | **13x** |

### Cache Hit Rate

```
Target: > 80%
Atual: ~85% em produção
```

---

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Add: nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

---

## 📝 Changelog

### v1.0.0 (2025-10-15)
- ✨ Adicionado TMO (Tempo Médio de Onboarding)
- ✨ Filtros por data de adesão em todos os endpoints
- ✨ Cache dinâmico baseado em filtros
- 🔧 Refatoração completa do health_scores.py
- 📚 Documentação completa da API

### v0.9.0 (2025-09)
- ✨ Dashboard com KPIs principais
- ✨ Sistema de Health Scores (4 pilares)
- ✨ Cache com Redis
- 🔒 Autenticação HTTP Basic

---

## 📞 Suporte

- **Email**: support@ecosys.com
- **Issues**: [GitHub Issues](https://github.com/danexplore/ecosysMS-Back/issues)
- **Documentação**: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)

---

## 📄 Licença

Este projeto é propriedade da EcoSys. Todos os direitos reservados.

---

## 👥 Equipe

- **Development**: EcoSys Dev Team
- **Maintenance**: CS Team
- **Owner**: [@danexplore](https://github.com/danexplore)

---

**Última atualização**: 15 de Outubro de 2025  
**Versão**: 1.0.0

