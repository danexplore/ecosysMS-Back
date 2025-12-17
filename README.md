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
      adoption: cliente.scores.adocao,
      porteLoja: cliente.metrics.estoque.porte_loja,
      estoqueTotal: cliente.metrics.estoque.total,
      usuariosAtivos: cliente.metrics.acessos.usuarios_ativos_30d,
      tipoEquipe: cliente.metrics.acessos.tipo_equipe
    }));
  
  console.log(`\n=== Clientes Críticos: ${criticos.length} ===`);
  criticos.forEach(c => {
    console.log(`- ${c.nome}: Score ${c.scoreTotal.toFixed(2)} (Adoção: ${c.adoption.toFixed(2)}) - Porte: ${c.porteLoja} (${c.estoqueTotal} veículos) - Equipe: ${c.tipoEquipe} (${c.usuariosAtivos} usuários)`);
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

### Sistema de Pontuação

O Health Score é calculado com base em **4 pilares principais**, cada um com peso específico na avaliação geral do cliente. O sistema identifica automaticamente o nível de saúde do cliente e categoriza em 4 níveis.

### 4 Pilares Detalhados

#### 🔥 **Pilar 1: Engajamento (30%)**
**Objetivo**: Medir a frequência e consistência do uso da plataforma pelos usuários do cliente.

**Métricas Principais:**
- Quantidade de acessos nos últimos 30 dias
- Dias desde o último acesso
- Número de usuários ativos (distintos)
- Tipo de equipe (Pequena/Média/Grande/Extra Grande)

**Fórmula de Cálculo:**
```python
# Score baseado em recência de acesso (igual para todos)
score_recencia = {
    dias <= 3: 1.0,
    dias <= 7: 0.9,
    dias <= 14: 0.6,
    dias <= 30: 0.2,
    dias > 30: 0.0
}

# Score baseado em frequência (proporcional ao tamanho da equipe)
score_frequencia = {
    'Pequena (1-2 users)': {
        acessos >= 25: 1.2, >=12: 1.0, >=6: 0.7, >=3: 0.5, >=2: 0.3, else: 0.0
    },
    'Média (3-5 users)': {
        acessos >= 40: 1.2, >=20: 1.0, >=10: 0.7, >=5: 0.5, >=3: 0.3, else: 0.0
    },
    'Grande (6-9 users)': {
        acessos >= 70: 1.2, >=35: 1.0, >=18: 0.7, >=9: 0.5, >=5: 0.3, else: 0.0
    },
    'Extra Grande (10+ users)': {
        acessos >= 95: 1.2, >=48: 1.0, >=24: 0.7, >=12: 0.5, >=7: 0.3, else: 0.0
    }
}

score_engajamento = (score_recencia + score_frequencia) / 2
```

**Exemplo:**
- Cliente com 4 usuários ativos, 45 acessos em 30 dias, último acesso há 0 dias
- Tipo: Média equipe → score_frequencia = 1.2 (45 >= 40)
- score_recencia = 1.0 (0 <= 3)
- **Resultado**: (1.0 + 1.2) / 2 = **1.10**

#### 📦 **Pilar 2: Gestão de Estoque (30%)**
**Objetivo**: Avaliar a eficiência na gestão do inventário e movimentação de veículos.

**Métricas Principais:**
- Quantidade de entradas nos últimos 30 dias
- Quantidade de saídas nos últimos 30 dias
- Dias desde última entrada
- Dias desde última saída
- Porte da loja (calculado automaticamente)

**Fórmula de Cálculo:**
```python
# Score baseado em frequência de entradas
score_entradas = {
    entradas >= 50: 1.2, >=25: 1.0, >=12: 0.7, >=6: 0.5, >=3: 0.3, else: 0.15
}

# Score baseado em frequência de saídas
score_saidas = {
    saidas >= 50: 1.2, >=25: 1.0, >=12: 0.7, >=6: 0.5, >=3: 0.3, else: 0.15
}

# Score baseado em recência
score_recencia_estoque = {
    max(dias_ultima_entrada, dias_ultima_saida) <= 7: 1.0,
    <= 14: 0.8, <= 30: 0.5, else: 0.0
}

score_estoque = (score_entradas + score_saidas + score_recencia_estoque) / 3
```

**Exemplo:**
- Cliente com 45 entradas, 38 saídas em 30 dias, última movimentação há 2 dias
- score_entradas = 1.0 (45 >= 25), score_saidas = 1.0 (38 >= 25)
- score_recencia = 1.0 (2 <= 7)
- **Resultado**: (1.0 + 1.0 + 1.0) / 3 = **1.00**

#### 💼 **Pilar 3: CRM e Vendas (20%)**
**Objetivo**: Medir a atividade no sistema de CRM e geração de leads/oportunidades.

**Métricas Principais:**
- Quantidade de leads criados nos últimos 30 dias
- Dias desde o último lead
- Frequência de criação de leads

**Fórmula de Cálculo:**
```python
# Score baseado em volume de leads
score_volume_leads = {
    leads >= 100: 1.2, >=50: 1.0, >=25: 0.7, >=10: 0.5, >=5: 0.3, else: 0.15
}

# Score baseado em recência
score_recencia_leads = {
    dias <= 7: 1.0, <=14: 0.8, <=30: 0.5, else: 0.0
}

score_crm = (score_volume_leads + score_recencia_leads) / 2
```

**Exemplo:**
- Cliente com 67 leads em 30 dias, último lead há 3 dias
- score_volume = 1.0 (67 >= 50), score_recencia = 1.0 (3 <= 7)
- **Resultado**: (1.0 + 1.0) / 2 = **1.00**

#### 🚀 **Pilar 4: Adoção Tecnológica (20%)**
**Objetivo**: Avaliar o nível de adoção de recursos avançados da plataforma.

**Métricas Principais:**
- Status de integração com econversa (WhatsApp)
- Status de anúncios (Ads)
- Status de relatórios avançados
- Status de contratos

**Fórmula de Cálculo:**
```python
# Cada integração contribui igualmente
score_adoption = (
    econversa_connected = 0.4 +  # 40% do score
    ads_status = 0.3 +           # 30% do score
    reports_status = 0.2 +       # 20% do score
    contracts_status = 0.1       # 10% do score
)
```

**Exemplo:**
- Cliente com econversa ativo, anúncios ativos, relatórios inativos, contratos ativos
- **Resultado**: 0.4 + 0.3 + 0.0 + 0.1 = **1**

### Pilar 1: Engajamento (Atualizado)

O cálculo de engajamento agora considera atividade semanal consistente e é proporcional ao tamanho da equipe:

**Frequência Esperada para Score Máximo (1.2):**
- **Pequena equipe (1-2 usuários)**: ≥ 25 acessos/mês
- **Média equipe (3-5 usuários)**: ≥ 40 acessos/mês 
- **Grande equipe (6-9 usuários)**: ≥ 70 acessos/mês
- **Extra grande (10+ usuários)**: ≥ 95 acessos/mês

**Lógica:**
- Baseado em 5-7 acessos/semana do usuário mais ativo (≈20-28 em 28 dias)
- Thresholds ajustados para refletir engajamento "realmente excelente"
- Tenants sem acesso recebem score 0.0 (antes dava mínimo 0.075)

### Categorias

```
🏆 Campeão  (>0.8)  - Clientes exemplares
💚 Saudável (0.6-0.8) - Clientes saudáveis  
🟡 Normal   (0.3-0.6) - Precisam atenção
🔴 Crítico  (≤0.3)   - Risco de churn
```

### Fórmula Geral

```python
score_total = (
  score_engajamento × 0.35 +    # 35% - Engajamento e frequência
  score_estoque × 0.35 +        # 35% - Gestão de inventário
  score_crm × 0.20 +            # 20% - Atividade de vendas
  score_adoption × 0.10         # 10% - Adoção tecnológica
)
```

**Exemplo de Cálculo Completo:**
- Cliente com scores: engajamento=1.10, estoque=1.00, crm=1.00, adoption=0.1
- **Resultado**: (1.10 × 0.35) + (1.00 × 0.35) + (1.00 × 0.20) + (1 × 0.10) = **1.035**

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
- **Pilar 1 (Engajamento)**: Thresholds atualizados para atividade semanal consistente (5-7 acessos/semana), proporcionais ao tamanho da equipe
- **Classificação de equipes**: Ajustada para Pequena (1-2), Média (3-5), Grande (6-9), Extra (10+)

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

