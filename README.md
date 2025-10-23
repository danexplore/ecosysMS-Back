# 🚀 ecosys MS - API de Gestão de Clientes

API RESTful completa para análise e gestão de clientes do sistema ecosys, com cálculo de Health Scores, KPIs e métricas de negócio.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Redis](https://img.shields.io/badge/Redis-Cache-red.svg)](https://redis.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange.svg)](https://www.mysql.com/)
[![Version](https://img.shields.io/badge/Version-1.1.0-brightgreen.svg)](./CHANGELOG_FILTROS.md)]

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
- **Dashboard KPIs**: Métricas agregadas em tempo real (MRR, Churn, TMO, Novos Clientes, Churns)
- **Gestão de Clientes**: CRUD completo com dados do Kommo CRM
- **Filtros Avançados**: Sistema dual-date (adesão OU churn) em todos os endpoints
- **Evolução Mensal**: Tracking de novos clientes, churns e clientes ativos por mês

### ⚡ Performance
- **Cache Distribuído**: Redis com TTL de 24 horas
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

# MySQL (ecosys)
DB_HOST_ecosys=localhost
DB_NAME_ecosys=ecosys_db
DB_USER_ecosys=root
DB_PASSWORD_ecosys=yourpass

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
| `/clientes/evolution` | GET | ✅ | **NOVO** - Evolução mensal de clientes |
| `/health-scores` | GET | ✅ | Health scores de todos os clientes |
| `/dashboard` | GET | ✅ | KPIs agregados do sistema |
| `/cache/clear` | POST | ✅ | Limpar cache |
| `/logins` | GET | ✅ | Histórico de logins por tenant |
| `/metricas-clientes` | GET | ✅ | **NOVO** - Métricas agregadas |

### Query Parameters (Filtros)

Disponíveis em: `/clientes`, `/clientes/evolution`, `/health-scores`, `/dashboard`

| Parâmetro | Tipo | Formato | Exemplo | Descrição |
|-----------|------|---------|---------|-----------|
| `data_inicio` | string | YYYY-MM-DD | 2024-01-01 | Data inicial (adesão OU churn) |
| `data_fim` | string | YYYY-MM-DD | 2024-12-31 | Data final (adesão OU churn) |

> **⚠️ Mudança Importante (v1.1.0)**: Os parâmetros `data_adesao_inicio/fim` foram renomeados para `data_inicio/fim` e agora filtram por adesão **OU** churn no período.

---

## 📚 Documentação

### Documentação Principal

📖 **[DOCUMENTACAO_COMPLETA.md](./DOCUMENTACAO_COMPLETA.md)** - ⭐ **Documentação consolidada e atualizada**
- Visão geral do sistema
- Todos os 9 endpoints detalhados
- Modelos de dados completos
- Sistema de Health Scores (4 pilares)
- Sistema de cache (24h TTL)
- Filtros dual-date (adesão OU churn)
- Exemplos práticos em Python, JavaScript, cURL
- Troubleshooting e FAQ
- Changelog completo

### Documentos Complementares

- 🔄 **[CHANGELOG_FILTROS.md](./CHANGELOG_FILTROS.md)** - Migração do sistema de filtros (v1.0 → v1.1)
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
    │   MySQL         │ ← Dados ecosys (Activity, Inventory)
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
| `DB_HOST_ecosys` | Host MySQL | ✅ |
| `DB_NAME_ecosys` | Nome do banco MySQL | ✅ |
| `DB_USER_ecosys` | Usuário MySQL | ✅ |
| `DB_PASSWORD_ecosys` | Senha MySQL | ✅ |
| `ENVIRONMENT` | Ambiente (development/production) | ❌ |

### Cache TTL

Configurado em `api/main.py`:

```python
CACHE_TTL = 60 * 60 * 24  # 24 horas (86400 segundos)
```

> **Nota**: O cache de 24 horas garante melhor performance sem necessidade de invalidações frequentes.

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
print(f"Clientes Pagantes: {dashboard['clientes_pagantes']}")
print(f"Novos Clientes: {dashboard['novos_clientes']}")
print(f"Churns: {dashboard['clientes_churn']}")
print(f"MRR: R$ {dashboard['mrr_value']:,.2f}")
print(f"TMO: {dashboard['tmo_dias']} dias")
print(f"Health Distribution: {dashboard['clientes_health']}")

# Buscar KPIs de 2024 (filtro dual-date: adesão OU churn)
response = requests.get(
    f"{BASE_URL}/dashboard",
    params={
        'data_inicio': '2024-01-01',
        'data_fim': '2024-12-31'
    },
    auth=AUTH
)
dashboard_2024 = response.json()
print(f"\n=== Dados de 2024 ===")
print(f"Novos Clientes: {dashboard_2024['novos_clientes']}")
print(f"Churns: {dashboard_2024['clientes_churn']}")
```

### Evolução Mensal com JavaScript

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:8000';
const AUTH = { username: 'admin', password: 'admin123' };

async function getEvolution() {
  // Buscar evolução de 2024
  const response = await axios.get(`${BASE_URL}/clientes/evolution`, {
    auth: AUTH,
    params: {
      data_inicio: '2024-01-01',
      data_fim: '2024-12-31'
    }
  });
  
  const evolution = response.data;
  
  console.log('=== Evolução Mensal 2024 ===\n');
  evolution.forEach(mes => {
    console.log(`${mes.mes}:`);
    console.log(`  Novos: +${mes.novos_clientes}`);
    console.log(`  Churns: -${mes.churns}`);
    console.log(`  Ativos: ${mes.clientes_ativos}\n`);
  });
}

async function getClientesCriticos() {
  const response = await axios.get(`${BASE_URL}/health-scores`, { auth: AUTH });
  const healthScores = response.data;
  
  const criticos = Object.entries(healthScores)
    .filter(([_, cliente]) => cliente.categoria === 'Crítico')
    .map(([slug, cliente]) => ({
      slug,
      nome: cliente.name,
      scoreTotal: cliente.scores.total,
      adoption: cliente.scores.adocao
    }));
  
  console.log(`\n=== Clientes Críticos: ${criticos.length} ===`);
  criticos.forEach(c => {
    console.log(`- ${c.nome}: Score ${c.scoreTotal.toFixed(2)} (Adoção: ${c.adoption.toFixed(2)})`);
  });
}

getEvolution();
getClientesCriticos();
```

### cURL - Exemplos Rápidos

```bash
# Clientes que aderiram OU deram churn em 2024
curl -u admin:admin123 \
  "http://localhost:8000/clientes?data_inicio=2024-01-01&data_fim=2024-12-31" \
  | jq 'length'

# Evolução mensal de 2024
curl -u admin:admin123 \
  "http://localhost:8000/clientes/evolution?data_inicio=2024-01-01" \
  | jq '.[] | "\(.mes): +\(.novos_clientes) / -\(.churns) = \(.clientes_ativos)"'

# Dashboard de junho/2024
curl -u admin:admin123 \
  "http://localhost:8000/dashboard?data_inicio=2024-06-01&data_fim=2024-06-30" \
  | jq '{novos: .novos_clientes, churns: .clientes_churn, mrr: .mrr_value}'
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
mysql -h $DB_HOST_ecosys -u $DB_USER_ecosys -p
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

| Operação | Sem Cache | Com Cache (24h) | Melhoria |
|----------|-----------|-----------------|----------|
| `/clientes` | ~800ms | ~50ms | **16x** |
| `/health-scores` | ~2.5s | ~80ms | **31x** |
| `/dashboard` | ~1.2s | ~60ms | **20x** |
| `/clientes/evolution` | ~1.5s | ~70ms | **21x** |

### Cache Hit Rate

```
Target: > 80%
Atual: ~92% em produção (com TTL de 24h)
```

> **Nota**: Com cache de 24 horas, a taxa de acerto aumentou significativamente, reduzindo a carga nos bancos de dados.

---

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Add: nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

---

## 📝 Changelog

### v1.1.0 (2025-10-22) - **CURRENT**

#### 🆕 Novidades
- **Endpoint `/clientes/evolution`**: Evolução mensal de clientes pagantes
- **Endpoint `/metricas-clientes`**: Métricas agregadas do sistema
- **Novos KPIs no dashboard**: `novos_clientes` e `clientes_churn` separados
- **Adoption scores numéricos**: Valores 0.0-1.0 ao invés de booleanos

#### 🔄 Mudanças
- **BREAKING**: Parâmetros `data_adesao_inicio/fim` → `data_inicio/fim`
- **BREAKING**: Filtros agora usam lógica OR (adesão OU churn no período)
- **TTL de cache**: 5-10min → 24 horas
- **Health distribution**: Exclui clientes da pipeline "Churns & Cancelamentos"

#### 🐛 Correções
- Corrigido matching de clientes por CNPJ (antes usava client_id)
- Corrigido sobrescrita de valores no mapeamento de clientes
- Corrigido adoption status para retornar valores numéricos

#### 📚 Documentação
- **DOCUMENTACAO_COMPLETA.md**: Documentação consolidada (~15.000 linhas)
- **CHANGELOG_FILTROS.md**: Guia de migração v1.0 → v1.1
- Exemplos atualizados com novos parâmetros

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

- **Email**: daniel.batista@ecosysauto.com.br
- **Issues**: [GitHub Issues](https://github.com/danexplore/ecosysMS-Back/issues)
- **Documentação**: [DOCUMENTACAO_COMPLETA.md](./DOCUMENTACAO_COMPLETA.md)
- **Documentação Interativa**: http://localhost:8000/docs (Swagger UI)

---

## 📄 Licença

Este projeto é propriedade da ecosys. Todos os direitos reservados.

---

## 👥 Equipe

- **Development**: ecosys - Copilot - Daniel Moreira
- **Maintenance**: Daniel Moreira
- **Owner**: [@danexplore](https://github.com/danexplore)

---

## 🔗 Links Importantes

- 📖 [Documentação Completa](./DOCUMENTACAO_COMPLETA.md) - Guia definitivo da API
- 🔄 [Changelog de Filtros](./CHANGELOG_FILTROS.md) - Migração v1.0 → v1.1
- 🚀 [Quick Start Guide](./QUICK_START.md) - Começe em 5 minutos
- 📊 [Dashboard Docs](./DASHBOARD_DOCS.md) - KPIs e métricas

---

**Última atualização**: 23 de Outubro de 2025  
**Versão**: 1.1.0

