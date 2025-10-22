# 📚 Documentação Completa - EcoSys MS API

> **Versão**: 1.1.0  
> **Última Atualização**: 22 de Outubro de 2025  
> **Status**: ✅ Produção

---

## 📖 Índice

1. [Visão Geral](#-visão-geral)
2. [Arquitetura](#-arquitetura)
3. [Instalação e Configuração](#-instalação-e-configuração)
4. [Endpoints da API](#-endpoints-da-api)
5. [Modelos de Dados](#-modelos-de-dados)
6. [Health Scores](#-health-scores)
7. [Sistema de Cache](#-sistema-de-cache)
8. [Filtros e Parâmetros](#-filtros-e-parâmetros)
9. [Autenticação](#-autenticação)
10. [Exemplos de Uso](#-exemplos-de-uso)
11. [Troubleshooting](#-troubleshooting)
12. [Changelog](#-changelog)

---

## 🎯 Visão Geral

### Propósito

API RESTful completa para análise e gestão de clientes do sistema EcoSys, fornecendo:

- 📊 **Health Scores**: Cálculo automatizado baseado em 4 pilares
- 📈 **Dashboard KPIs**: Métricas agregadas (MRR, Churn, TMO, Evolução)
- 👥 **Gestão de Clientes**: Dados completos do CRM Kommo
- 🔍 **Filtros Avançados**: Por período de adesão e churn
- 📱 **Histórico de Acessos**: Tracking de login dos usuários

### Stack Tecnológico

| Componente | Tecnologia | Versão | Propósito |
|------------|-----------|--------|-----------|
| **Framework** | FastAPI | 0.104+ | API REST assíncrona |
| **Linguagem** | Python | 3.9+ | Backend |
| **Cache** | Redis (Upstash) | - | Cache distribuído |
| **BD Principal** | PostgreSQL | 15+ | Dados de clientes (Kommo) |
| **BD Métricas** | MySQL | 8.0+ | Dados operacionais (EcoSys) |
| **Processamento** | Pandas | 2.0+ | Análise de dados |
| **Auth** | HTTP Basic | - | Autenticação |
| **Compressão** | GZIP | - | Otimização de resposta |

### Características

✅ **Alta Performance**
- Cache distribuído com TTL de 24 horas
- Queries paralelas com connection pooling
- Compressão GZIP (redução de 70%)
- Thread pool para operações bloqueantes

✅ **Segurança**
- HTTP Basic Authentication
- CORS configurável
- Validação de dados com Pydantic
- Sanitização de queries SQL

✅ **Escalabilidade**
- Arquitetura assíncrona
- Pool de conexões MySQL (5 conexões)
- Cache em múltiplas camadas
- Processamento paralelo

---

## 🏗️ Arquitetura

### Estrutura de Diretórios

```
ecosysMS Back/
├── api/
│   ├── main.py                    # 🚀 Aplicação FastAPI principal
│   ├── lib/
│   │   ├── models.py             # 📦 Modelos Pydantic
│   │   └── queries.py            # 🗄️ Queries SQL otimizadas
│   └── scripts/
│       ├── clientes.py           # 👥 Gestão de clientes
│       ├── health_scores.py      # 💚 Cálculo de health scores
│       └── dashboard.py          # 📊 KPIs e métricas
├── .env                          # 🔐 Variáveis de ambiente
├── requirements.txt              # 📋 Dependências Python
└── README.md                     # 📖 Documentação rápida
```

### Fluxo de Requisição

```
┌─────────────┐
│   Cliente   │
│  (Frontend) │
└──────┬──────┘
       │ HTTP Request
       ↓
┌─────────────────────────────┐
│    FastAPI Middleware       │
│  • CORS                     │
│  • GZIP Compression         │
│  • Basic Auth               │
└──────────┬──────────────────┘
           │
           ↓
┌─────────────────────────────┐
│    Endpoint Handler         │
│  • Validação Pydantic       │
│  • Parsing de parâmetros    │
└──────────┬──────────────────┘
           │
           ↓
    ┌──────┴──────┐
    │             │
    ↓             ↓
┌────────┐   ┌────────────┐
│ Redis  │   │  Database  │
│ Cache  │   │   Query    │
└───┬────┘   └─────┬──────┘
    │              │
    │ Hit          │ Miss
    │              ↓
    │    ┌──────────────────┐
    │    │  PostgreSQL      │
    │    │  MySQL           │
    │    │  (Paralelo)      │
    │    └────────┬─────────┘
    │             │
    │             ↓
    │    ┌──────────────────┐
    │    │  Processamento   │
    │    │  • Pandas        │
    │    │  • Cálculos      │
    │    │  • Agregações    │
    │    └────────┬─────────┘
    │             │
    ↓             ↓
┌──────────────────────────┐
│   Salvar no Cache +      │
│   Retornar JSON          │
└────────────┬─────────────┘
             │
             ↓
      ┌──────────┐
      │ Cliente  │
      └──────────┘
```

### Componentes Principais

#### 1. **FastAPI Application** (`main.py`)
- Gerenciamento de rotas
- Middlewares (CORS, GZIP, Auth)
- Sistema de cache com Redis
- Thread pool executor
- Tratamento de erros

#### 2. **Scripts de Negócio**

**`clientes.py`**
- Conexão com PostgreSQL (Kommo CRM)
- Busca de clientes com filtros
- Histórico de logins
- Métricas de clientes
- Evolução mensal de clientes

**`health_scores.py`**
- Conexão com MySQL (EcoSys)
- Connection pooling (5 conexões)
- Queries paralelas (4 pilares)
- Cálculo de scores ponderados
- Categorização de clientes

**`dashboard.py`**
- Agregação de KPIs
- Cálculo de MRR e Churn
- TMO (Tempo Médio de Onboarding)
- Distribuição de health scores
- Contadores de novos clientes e churns

#### 3. **Modelos e Queries** (`lib/`)
- Modelos Pydantic para validação
- Queries SQL otimizadas
- Constantes e configurações

---

## 🛠️ Instalação e Configuração

### Pré-requisitos

```bash
# Sistema
- Python 3.9+
- PostgreSQL 15+
- MySQL 8.0+
- Redis (ou conta Upstash)

# Ferramentas
- pip (gerenciador de pacotes Python)
- virtualenv (recomendado)
```

### Instalação

1. **Clone o repositório**
```bash
git clone https://github.com/seu-usuario/ecosysMS-Back.git
cd ecosysMS-Back
```

2. **Crie ambiente virtual**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Instale dependências**
```bash
pip install -r requirements.txt
```

4. **Configure variáveis de ambiente**

Crie um arquivo `.env` na raiz do projeto:

```env
# ═══════════════════════════════════════
# 🔐 AUTENTICAÇÃO
# ═══════════════════════════════════════
BASIC_AUTH_USERS=admin:senha123,user:senha456

# ═══════════════════════════════════════
# 🗄️ BANCO DE DADOS - POSTGRESQL (Kommo)
# ═══════════════════════════════════════
DB_HOST=localhost
DB_PORT=5432
DB_NAME=kommo_db
DB_USER=postgres
DB_PASSWORD=sua_senha

# ═══════════════════════════════════════
# 🗄️ BANCO DE DADOS - MYSQL (EcoSys)
# ═══════════════════════════════════════
DB_HOST_ECOSYS=localhost
DB_NAME_ECOSYS=ecosys_db
DB_USER_ECOSYS=root
DB_PASSWORD_ECOSYS=sua_senha

# ═══════════════════════════════════════
# 🔴 REDIS (Upstash)
# ═══════════════════════════════════════
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-token-here

# ═══════════════════════════════════════
# ⚙️ CONFIGURAÇÕES DA APLICAÇÃO
# ═══════════════════════════════════════
ENVIRONMENT=production  # ou development
```

5. **Execute a aplicação**

```bash
# Desenvolvimento (com reload automático)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Produção
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

6. **Acesse a documentação interativa**
```
http://localhost:8000/docs
```

---

## 🌐 Endpoints da API

### Base URL
```
http://localhost:8000
```

### 1. **GET /** 
Endpoint raiz - Verificação básica

**Resposta**:
```json
{
  "message": "API de Gestão de Clientes está no ar!"
}
```

---

### 2. **GET /health**
Health check da aplicação

**Resposta**:
```json
{
  "status": "healthy",
  "environment": "production",
  "redis_connection": "ok",
  "env_variables": {
    "UPSTASH_REDIS_REST_URL": true,
    "UPSTASH_REDIS_REST_TOKEN": true,
    "BASIC_AUTH_USERS": true
  },
  "timestamp": "2025-10-22T10:30:00Z"
}
```

---

### 3. **GET /clientes** 🔒
Retorna lista completa de clientes

**Autenticação**: ✅ Requerida

**Query Parameters**:
| Parâmetro | Tipo | Obrigatório | Formato | Descrição |
|-----------|------|-------------|---------|-----------|
| `data_inicio` | string | Não | YYYY-MM-DD | Data inicial para filtro |
| `data_fim` | string | Não | YYYY-MM-DD | Data final para filtro |

**Lógica de Filtro**:
Retorna clientes que **aderiram OU deram churn** no período especificado.

**Cache**: ✅ Sim (24 horas)

**Exemplo de Request**:
```bash
curl -u admin:senha123 \
  "http://localhost:8000/clientes?data_inicio=2024-01-01&data_fim=2024-12-31"
```

**Resposta** (indexada por `client_id`):
```json
{
  "379092": {
    "client_id": 379092,
    "nome": "GT AUTOBROKER",
    "razao_social": "GT AUTOBROKER LTDA",
    "cnpj": 37482160000124,
    "valor": 399.0,
    "vendedor": "João Silva",
    "cs": "Jefferson Xavier",
    "status": "Ativo",
    "pipeline": "CS | ONGOING",
    "data_adesao": "2024-06-15",
    "data_start_onboarding": "2024-06-20",
    "data_end_onboarding": "2024-07-25",
    "data_cancelamento": null,
    "motivos_churn": null,
    "descricao_cancelamento": null,
    "criado_em": "2024-06-10T14:30:00",
    "atualizado_em": "2025-10-20T10:15:00"
  }
}
```

---

### 4. **GET /clientes/evolution** 🔒
Retorna evolução mensal de clientes pagantes

**Autenticação**: ✅ Requerida

**Query Parameters**: Mesmos de `/clientes`

**Cache**: ✅ Sim (24 horas)

**Exemplo de Request**:
```bash
curl -u admin:senha123 \
  "http://localhost:8000/clientes/evolution?data_inicio=2024-01-01"
```

**Resposta**:
```json
[
  {
    "mes": "jan/2024",
    "novos_clientes": 45,
    "churns": 12,
    "clientes_ativos": 230
  },
  {
    "mes": "fev/2024",
    "novos_clientes": 38,
    "churns": 8,
    "clientes_ativos": 260
  },
  {
    "mes": "mar/2024",
    "novos_clientes": 52,
    "churns": 15,
    "clientes_ativos": 297
  }
]
```

**Campos**:
- `mes`: Mês no formato "mmm/yyyy"
- `novos_clientes`: Clientes pagantes que aderiram no mês
- `churns`: Clientes pagantes que cancelaram no mês
- `clientes_ativos`: Total acumulado de clientes ativos

---

### 5. **GET /health-scores** 🔒
Retorna health scores de todos os clientes

**Autenticação**: ✅ Requerida

**Query Parameters**: Mesmos de `/clientes`

**Cache**: ✅ Sim (24 horas)

**Exemplo de Request**:
```bash
curl -u admin:senha123 \
  "http://localhost:8000/health-scores"
```

**Resposta** (indexada por `slug`):
```json
{
  "gt-autobroker": {
    "tenant_id": "2d516def-3da6-4479-807e-ac095fa68cd1",
    "name": "GT AUTOBROKER",
    "cnpj": 37482160000124,
    "slug": "gt-autobroker",
    "scores": {
      "engajamento": 1.10,
      "adocao": 0.60,
      "estoque": 0.88,
      "crm": 1.10,
      "total": 0.93
    },
    "adoption": {
      "econversa_status": 0.0,
      "ads_status": 0.4,
      "reports_status": 0.0,
      "contracts_status": 0.2
    },
    "integrations": {
      "econversa_status": false,
      "integrators_connected": ["WEBMOTORS", "OLX"]
    },
    "metrics": {
      "acessos": {
        "quantidade_30d": 88,
        "dias_ultimo_acesso": 0
      },
      "entradas": {
        "quantidade_30d": 29,
        "dias_ultima_entrada": 0
      },
      "saidas": {
        "quantidade_30d": 4,
        "dias_ultima_saida": 0
      },
      "leads": {
        "quantidade_30d": 224,
        "dias_ultimo_lead": 1
      }
    },
    "categoria": "Campeão"
  }
}
```

---

### 6. **GET /dashboard** 🔒
Retorna KPIs agregados do sistema

**Autenticação**: ✅ Requerida

**Query Parameters**: Mesmos de `/clientes`

**Cache**: ✅ Sim (24 horas)

**Exemplo de Request**:
```bash
curl -u admin:senha123 \
  "http://localhost:8000/dashboard"
```

**Resposta**:
```json
{
  "clientes_ativos": 93,
  "clientes_pagantes": 83,
  "clientes_onboarding": 30,
  "novos_clientes": 189,
  "clientes_churn": 63,
  "mrr_value": 32262.00,
  "churn_value": 25911.00,
  "tmo_dias": 36.5,
  "clientes_health": {
    "Crítico": 15,
    "Normal": 25,
    "Saudável": 30,
    "Campeão": 13
  }
}
```

**Campos**:
- `clientes_ativos`: Total de clientes nas pipelines CS ativas
- `clientes_pagantes`: Clientes ativos com valor > 0
- `clientes_onboarding`: Clientes em onboarding (sem data de finalização)
- `novos_clientes`: Clientes que aderiram no período filtrado
- `clientes_churn`: Clientes que cancelaram no período filtrado
- `mrr_value`: Receita Mensal Recorrente (soma dos valores ativos)
- `churn_value`: Valor perdido com churns no período
- `tmo_dias`: Tempo Médio de Onboarding em dias
- `clientes_health`: Distribuição por categoria de health (apenas pagantes ativos)

---

### 7. **POST /cache/clear** 🔒
Limpa todos os caches da aplicação

**Autenticação**: ✅ Requerida

**Resposta**:
```json
{
  "status": "success",
  "message": "Cache será limpo automaticamente no próximo TTL",
  "note": "Para forçar a atualização, aguarde o TTL expirar ou reinicie a aplicação"
}
```

---

### 8. **GET /logins** 🔒
Retorna histórico de logins de um tenant

**Autenticação**: ✅ Requerida

**Query Parameters**:
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `tenant_id` | string | Sim | ID do tenant (UUID) |

**Exemplo de Request**:
```bash
curl -u admin:senha123 \
  "http://localhost:8000/logins?tenant_id=2d516def-3da6-4479-807e-ac095fa68cd1"
```

**Resposta**:
```json
{
  "tenant_id": "2d516def-3da6-4479-807e-ac095fa68cd1",
  "periodo": "30 dias",
  "total_logins": 156,
  "dias_com_login": 22,
  "ultimo_login": {
    "data": "2025-10-21",
    "hora": "14:30:25",
    "usuario": "admin",
    "ip": "192.168.1.100"
  },
  "logins": [...]
}
```

---

### 9. **GET /metricas-clientes** 🔒
Retorna métricas agregadas dos clientes

**Autenticação**: ✅ Requerida

**Exemplo de Request**:
```bash
curl -u admin:senha123 \
  "http://localhost:8000/metricas-clientes"
```

**Resposta**:
```json
{
  "total_clientes": 352,
  "clientes_ativos": 93,
  "clientes_churn": 150,
  "taxa_churn": 42.6,
  "mrr_total": 32262.00,
  "ticket_medio": 388.70
}
```

---

## 📦 Modelos de Dados

### Cliente (Kommo CRM)

```python
{
  "client_id": int,              # ID único do cliente
  "nome": str,                   # Nome fantasia
  "razao_social": str,           # Razão social
  "cnpj": int,                   # CNPJ (apenas números)
  "valor": float,                # Valor mensal do contrato
  "vendedor": str | null,        # Nome do vendedor
  "cs": str | null,              # Customer Success responsável
  "status": str,                 # Status do cliente
  "pipeline": str,               # Pipeline atual
  "data_adesao": str,            # Data de adesão (YYYY-MM-DD)
  "data_start_onboarding": str,  # Início do onboarding
  "data_end_onboarding": str,    # Fim do onboarding
  "data_cancelamento": str,      # Data de cancelamento
  "motivos_churn": str,          # Motivos do churn
  "descricao_cancelamento": str, # Descrição do cancelamento
  "criado_em": str,              # Timestamp de criação
  "atualizado_em": str           # Timestamp de atualização
}
```

### Health Score

```python
{
  "tenant_id": str,      # UUID do tenant
  "name": str,           # Nome do cliente
  "cnpj": int,           # CNPJ
  "slug": str,           # Slug único
  "scores": {
    "engajamento": float,  # Score de engajamento (0-1+)
    "adocao": float,       # Score de adoção (0-1)
    "estoque": float,      # Score de estoque (0-1+)
    "crm": float,          # Score de CRM (0-1+)
    "total": float         # Score total ponderado
  },
  "adoption": {
    "econversa_status": float,  # 0.0 ou 0.3
    "ads_status": float,        # 0.0 ou 0.4
    "reports_status": float,    # 0.0 ou 0.2
    "contracts_status": float   # 0.0 ou 0.1
  },
  "integrations": {
    "econversa_status": bool,
    "integrators_connected": list[str]
  },
  "metrics": {
    "acessos": {
      "quantidade_30d": int,
      "dias_ultimo_acesso": int
    },
    "entradas": {...},
    "saidas": {...},
    "leads": {...}
  },
  "categoria": str  # Crítico, Normal, Saudável, Campeão
}
```

---

## 💚 Health Scores

### Metodologia de Cálculo

O Health Score é calculado baseado em **4 pilares** com pesos diferentes:

```python
WEIGHTS = {
    'score_engajamento': 0.30,            # 30%
    'score_movimentacao_estoque': 0.30,   # 30%
    'score_crm': 0.20,                    # 20%
    'score_adoption': 0.20                # 20%
}

score_total = sum(score_pilar * peso for cada pilar)
```

### Pilar 1: Engajamento (30%)

Mede o **uso ativo do sistema** pelos usuários.

**Métricas**:
- Quantidade de acessos nos últimos 30 dias
- Dias desde o último acesso

**Fórmula**:
```python
if qntd_acessos >= 20 and dias_ultimo_acesso <= 1:
    score = 1.0
elif qntd_acessos >= 10:
    score = 0.7
elif qntd_acessos >= 5:
    score = 0.4
else:
    score = 0.1
```

### Pilar 2: Movimentação de Estoque (30%)

Mede a **gestão de inventário** do cliente.

**Métricas**:
- Entradas de estoque nos últimos 30 dias
- Saídas de estoque nos últimos 30 dias
- Dias desde última movimentação

**Fórmula**:
```python
movimentacao = entradas + saidas

if movimentacao >= 50 and dias_ultima_mov <= 2:
    score = 1.0
elif movimentacao >= 20:
    score = 0.7
elif movimentacao >= 10:
    score = 0.4
else:
    score = 0.1
```

### Pilar 3: CRM (20%)

Mede o **uso do CRM** para gestão de leads.

**Métricas**:
- Quantidade de leads criados nos últimos 30 dias
- Dias desde último lead criado

**Fórmula**:
```python
if qntd_leads >= 50 and dias_ultimo_lead <= 1:
    score = 1.0
elif qntd_leads >= 20:
    score = 0.7
elif qntd_leads >= 10:
    score = 0.4
else:
    score = 0.1
```

### Pilar 4: Adoção (20%)

Mede a **utilização de funcionalidades extras** do sistema.

**Funcionalidades Principais**:
- 🚗 **Integração com Portais**: 0.4 (40% do score)
- 💬 **eConversa**: 0.3 (30% do score)

**Funcionalidades Extras**:
- 📊 **Relatórios**: 0.2 (20% do score)
- 📄 **Contratos**: 0.1 (10% do score)

**Critérios**:
- **Anúncios**: Tem veículos anunciados nos últimos 30 dias
- **eConversa**: Conectado e recebeu mensagens nos últimos 15 dias
- **Relatórios**: Emitiu pelo menos 1 relatório nos últimos 30 dias
- **Contratos**: Emitiu 2+ contratos nos últimos 30 dias

**Score máximo**: 1.0 (100%)

### Categorização de Clientes

Baseado no **score_total**:

| Categoria | Score | Descrição |
|-----------|-------|-----------|
| 🏆 **Campeão** | ≥ 0.8 | Cliente engajado, usa todas as funcionalidades |
| 💚 **Saudável** | 0.6 - 0.79 | Cliente saudável, bom uso do sistema |
| ⚠️ **Normal** | 0.3 - 0.59 | Cliente com uso moderado, precisa de atenção |
| 🔴 **Crítico** | < 0.3 | Cliente em risco, baixo engajamento |

---

## 💾 Sistema de Cache

### Configuração

```python
# TTL (Time To Live)
CACHE_TTL_CLIENTES = 60 * 60 * 24      # 24 horas
CACHE_TTL_HEALTH_SCORES = 60 * 60 * 24 # 24 horas
CACHE_TTL_DASHBOARD = 60 * 60 * 24     # 24 horas
```

### Estrutura de Chaves

```
clientes:{data_inicio}:{data_fim}
health-scores:{data_inicio}:{data_fim}
dashboard:{data_inicio}:{data_fim}
evolution:{data_inicio}:{data_fim}
```

**Exemplos**:
```
clientes:all:all                    # Todos os clientes
clientes:2024-01-01:2024-12-31     # Clientes do ano 2024
health-scores:2024-06-01:2024-06-30 # Health scores de junho
```

### Estratégia de Cache

1. **Verificar Cache**: Ao receber requisição, verificar se dados existem no Redis
2. **Cache Hit**: Retornar dados imediatamente (latência ~50ms)
3. **Cache Miss**: Buscar dados nos bancos, processar e salvar no cache
4. **TTL**: Dados expiram após 24 horas automaticamente

### Limpeza de Cache

**Manual**:
```bash
curl -X POST -u admin:senha123 \
  http://localhost:8000/cache/clear
```

**Automática**:
- Cache expira após TTL (24 horas)
- Reiniciar aplicação não afeta cache (Redis externo)

---

## 🔍 Filtros e Parâmetros

### Sistema de Filtros Unificado

**Versão Atual**: v1.1.0

#### Mudança Importante (Out/2025)

**❌ Antes** (v1.0.0):
```
?data_adesao_inicio=2024-01-01
?data_adesao_fim=2024-12-31
```
Filtrava apenas por **data de adesão**.

**✅ Agora** (v1.1.0):
```
?data_inicio=2024-01-01
?data_fim=2024-12-31
```
Filtra por **data de adesão OU data de cancelamento**.

### Lógica OR

```python
incluir_cliente = False

# Verificar se aderiu no período
if data_adesao >= data_inicio and data_adesao <= data_fim:
    incluir_cliente = True

# Verificar se deu churn no período
if data_cancelamento >= data_inicio and data_cancelamento <= data_fim:
    incluir_cliente = True

return incluir_cliente
```

### Casos de Uso

#### Cenário 1: Cliente que aderiu no período
```python
cliente = {
    "data_adesao": "2024-06-15",
    "data_cancelamento": null
}
filtro = {
    "data_inicio": "2024-06-01",
    "data_fim": "2024-06-30"
}
# ✅ Incluído (data_adesao no range)
```

#### Cenário 2: Cliente que deu churn no período
```python
cliente = {
    "data_adesao": "2023-01-10",
    "data_cancelamento": "2024-06-20"
}
filtro = {
    "data_inicio": "2024-06-01",
    "data_fim": "2024-06-30"
}
# ✅ Incluído (data_cancelamento no range)
```

#### Cenário 3: Cliente que aderiu E deu churn no período
```python
cliente = {
    "data_adesao": "2024-06-05",
    "data_cancelamento": "2024-06-25"
}
filtro = {
    "data_inicio": "2024-06-01",
    "data_fim": "2024-06-30"
}
# ✅ Incluído (ambas as datas no range)
# Dashboard conta em ambos: novos_clientes += 1, clientes_churn += 1
```

#### Cenário 4: Cliente fora do período
```python
cliente = {
    "data_adesao": "2023-01-10",
    "data_cancelamento": "2023-12-20"
}
filtro = {
    "data_inicio": "2024-06-01",
    "data_fim": "2024-06-30"
}
# ❌ Excluído (nenhuma data no range)
```

---

## 🔐 Autenticação

### HTTP Basic Authentication

Todos os endpoints protegidos requerem autenticação.

### Configuração

No arquivo `.env`:
```env
BASIC_AUTH_USERS=admin:senha123,user1:senha456,user2:senha789
```

Formato: `usuario:senha,usuario:senha,...`

### Uso

**cURL**:
```bash
curl -u admin:senha123 http://localhost:8000/clientes
```

**JavaScript (Fetch)**:
```javascript
const headers = new Headers();
headers.append('Authorization', 'Basic ' + btoa('admin:senha123'));

fetch('http://localhost:8000/clientes', {
  headers: headers
})
.then(response => response.json())
.then(data => console.log(data));
```

**Python (requests)**:
```python
import requests

response = requests.get(
    'http://localhost:8000/clientes',
    auth=('admin', 'senha123')
)
data = response.json()
```

### Segurança

- ✅ Senhas nunca são logadas
- ✅ Comparação de senhas usa `secrets.compare_digest()` (timing-safe)
- ✅ HTTPS recomendado em produção
- ⚠️ Não use Basic Auth sem HTTPS em produção

---

## 💡 Exemplos de Uso

### Python

```python
import requests
from datetime import datetime, timedelta

# Configuração
BASE_URL = "http://localhost:8000"
AUTH = ("admin", "senha123")

# 1. Buscar clientes do último mês
hoje = datetime.now()
mes_passado = hoje - timedelta(days=30)

response = requests.get(
    f"{BASE_URL}/clientes",
    auth=AUTH,
    params={
        "data_inicio": mes_passado.strftime("%Y-%m-%d"),
        "data_fim": hoje.strftime("%Y-%m-%d")
    }
)
clientes = response.json()
print(f"Total de clientes: {len(clientes)}")

# 2. Buscar health scores
response = requests.get(
    f"{BASE_URL}/health-scores",
    auth=AUTH
)
health_scores = response.json()

# Filtrar clientes críticos
criticos = [
    cliente for slug, cliente in health_scores.items()
    if cliente['categoria'] == 'Crítico'
]
print(f"Clientes críticos: {len(criticos)}")

# 3. Buscar KPIs do dashboard
response = requests.get(
    f"{BASE_URL}/dashboard",
    auth=AUTH
)
dashboard = response.json()

print(f"""
Dashboard KPIs:
- MRR: R$ {dashboard['mrr_value']:,.2f}
- Clientes Ativos: {dashboard['clientes_ativos']}
- Novos Clientes: {dashboard['novos_clientes']}
- Churns: {dashboard['clientes_churn']}
- TMO: {dashboard['tmo_dias']} dias
""")

# 4. Evolução mensal
response = requests.get(
    f"{BASE_URL}/clientes/evolution",
    auth=AUTH,
    params={
        "data_inicio": "2024-01-01"
    }
)
evolution = response.json()

for mes in evolution:
    print(f"{mes['mes']}: +{mes['novos_clientes']} / -{mes['churns']} = {mes['clientes_ativos']}")
```

### JavaScript/TypeScript

```typescript
const API_BASE_URL = "http://localhost:8000";
const USERNAME = "admin";
const PASSWORD = "senha123";

// Configurar autenticação
const headers = new Headers();
headers.append(
  'Authorization',
  'Basic ' + btoa(`${USERNAME}:${PASSWORD}`)
);

// 1. Buscar clientes
async function fetchClientes(dataInicio?: string, dataFim?: string) {
  const params = new URLSearchParams();
  if (dataInicio) params.append('data_inicio', dataInicio);
  if (dataFim) params.append('data_fim', dataFim);
  
  const url = params.toString()
    ? `${API_BASE_URL}/clientes?${params.toString()}`
    : `${API_BASE_URL}/clientes`;
  
  const response = await fetch(url, { headers });
  const clientes = await response.json();
  
  return clientes;
}

// 2. Buscar health scores
async function fetchHealthScores() {
  const response = await fetch(
    `${API_BASE_URL}/health-scores`,
    { headers }
  );
  return await response.json();
}

// 3. Buscar dashboard
async function fetchDashboard() {
  const response = await fetch(
    `${API_BASE_URL}/dashboard`,
    { headers }
  );
  return await response.json();
}

// 4. Buscar evolução
async function fetchEvolution(dataInicio?: string, dataFim?: string) {
  const params = new URLSearchParams();
  if (dataInicio) params.append('data_inicio', dataInicio);
  if (dataFim) params.append('data_fim', dataFim);
  
  const url = `${API_BASE_URL}/clientes/evolution?${params.toString()}`;
  
  const response = await fetch(url, { headers });
  return await response.json();
}

// Uso
(async () => {
  // Buscar dados do último trimestre
  const dataInicio = '2024-07-01';
  const dataFim = '2024-09-30';
  
  const clientes = await fetchClientes(dataInicio, dataFim);
  const dashboard = await fetchDashboard();
  const evolution = await fetchEvolution(dataInicio);
  
  console.log('Total de clientes:', Object.keys(clientes).length);
  console.log('MRR:', dashboard.mrr_value);
  console.log('Evolução:', evolution);
})();
```

---

## 🔧 Troubleshooting

### Problemas Comuns

#### 1. Erro de Autenticação (401)

**Sintoma**:
```json
{
  "detail": "Acesso negado."
}
```

**Soluções**:
- Verificar se credenciais estão corretas
- Verificar se `BASIC_AUTH_USERS` está configurado no `.env`
- Verificar se header `Authorization` está sendo enviado

#### 2. Erro de Conexão com Redis

**Sintoma**:
```
Erro ao conectar com Redis: ...
```

**Soluções**:
- Verificar se `UPSTASH_REDIS_REST_URL` e `UPSTASH_REDIS_REST_TOKEN` estão corretos
- Testar conexão com Redis manualmente
- Verificar firewall/network

#### 3. Erro de Conexão com Banco de Dados

**Sintoma**:
```
Erro ao executar query: connection refused
```

**Soluções**:
- Verificar se PostgreSQL/MySQL estão rodando
- Verificar credenciais no `.env`
- Verificar se IP/porta estão corretos
- Testar conexão com `psql` ou `mysql` cli

#### 4. Cache Desatualizado

**Sintoma**: Dados antigos sendo retornados

**Soluções**:
- Limpar cache: `POST /cache/clear`
- Aguardar TTL de 24 horas
- Reiniciar aplicação
- Verificar TTL configurado

#### 5. Performance Lenta

**Sintoma**: Requisições demoradas (>5s)

**Soluções**:
- Verificar se cache está funcionando
- Verificar logs para identificar queries lentas
- Verificar conexão com bancos de dados
- Aumentar pool de conexões MySQL
- Adicionar índices nos bancos de dados

#### 6. Memória Alta

**Sintoma**: Aplicação consumindo muita RAM

**Soluções**:
- Verificar tamanho do cache
- Reduzir TTL do cache
- Limitar número de workers do uvicorn
- Otimizar queries que retornam muitos dados

---

## 📋 Changelog

### v1.1.0 (22/10/2025)

#### 🆕 Novidades
- **Endpoint `/clientes/evolution`**: Evolução mensal de clientes pagantes
- **Endpoint `/metricas-clientes`**: Métricas agregadas
- **Novos KPIs no dashboard**: `novos_clientes` e `clientes_churn` separados
- **Adoption scores**: Valores numéricos (0.0-1.0) ao invés de booleanos

#### 🔄 Mudanças
- **BREAKING**: Parâmetros renomeados de `data_adesao_inicio/fim` para `data_inicio/fim`
- **BREAKING**: Lógica de filtro mudou para OR (adesão OU churn)
- **TTL de cache aumentado**: 5min → 24h
- **Health distribution**: Agora exclui clientes em churn da contagem

#### 🐛 Correções
- Corrigido matching de clientes por CNPJ (antes usava client_id)
- Corrigido sobrescrita de valores no mapeamento de clientes
- Corrigido adoption status para retornar valores numéricos corretos

#### 📚 Documentação
- Documentação completa consolidada em `DOCUMENTACAO_COMPLETA.md`
- Exemplos de código atualizados
- Diagramas de fluxo adicionados

### v1.0.0 (15/10/2025)

#### 🎉 Release Inicial
- Endpoints básicos: `/clientes`, `/health-scores`, `/dashboard`
- Sistema de cache com Redis
- Health scores com 4 pilares
- Dashboard KPIs
- Autenticação HTTP Basic
- Documentação inicial

---

## 📞 Suporte

### Contatos
- **Equipe de Desenvolvimento**: dev@ecosys.com
- **Suporte Técnico**: support@ecosys.com

### Links Úteis
- 📖 [Documentação Interativa](http://localhost:8000/docs)
- 🔗 [Repositório GitHub](https://github.com/danexplore/ecosysMS-Back)
- 📊 [Postman Collection](./EcoSys_API.postman_collection.json)

### Reportar Bugs
Abra uma issue no GitHub com:
- Descrição do problema
- Steps para reproduzir
- Logs relevantes
- Versão da API

---

## 📄 Licença

Este projeto é propriedade da EcoSys e seu uso é restrito à empresa e parceiros autorizados.

---

**Última atualização**: 22 de Outubro de 2025  
**Versão**: 1.1.0  
**Maintainers**: ecosys AUTO - Claude Sonnet 4.5 (Daniel Moreira Prompter)
