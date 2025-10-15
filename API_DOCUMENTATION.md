# 📚 Documentação Completa da API - EcoSys MS

## 📖 Índice

1. [Visão Geral](#visão-geral)
2. [Arquitetura](#arquitetura)
3. [Autenticação](#autenticação)
4. [Endpoints](#endpoints)
5. [Modelos de Dados](#modelos-de-dados)
6. [Sistema de Cache](#sistema-de-cache)
7. [Health Scores](#health-scores)
8. [Configuração](#configuração)
9. [Exemplos de Uso](#exemplos-de-uso)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Visão Geral

### Propósito
API RESTful para gestão e análise de clientes do sistema EcoSys, fornecendo:
- Dados de clientes e suas configurações
- Cálculo de Health Scores (4 pilares)
- KPIs e métricas de negócio
- Histórico de acessos e atividades

### Tecnologias
- **Framework**: FastAPI 
- **Linguagem**: Python 3.9+
- **Cache**: Redis (Upstash)
- **Bancos de Dados**: 
  - PostgreSQL (clientes Kommo)
  - MySQL (dados EcoSys)
- **Autenticação**: HTTP Basic Auth
- **Compressão**: GZIP
- **Async**: ThreadPoolExecutor para operações bloqueantes

### URL Base
```
Production: https://your-domain.com
Development: http://localhost:8000
```

### Versão da API
**v1.0.0** (Outubro 2025)

---

## 🏗️ Arquitetura

### Estrutura de Diretórios

```
api/
├── main.py                 # Aplicação FastAPI principal
├── lib/
│   ├── models.py          # Modelos Pydantic
│   └── queries.py         # Queries SQL
├── scripts/
│   ├── clientes.py        # Gestão de clientes
│   ├── health_scores.py   # Cálculo de health scores
│   └── dashboard.py       # KPIs do dashboard
└── utils/                 # Utilidades (futuro)
```

### Fluxo de Dados

```
Cliente HTTP
    ↓
FastAPI Middleware (CORS, GZIP, Auth)
    ↓
Endpoint Handler
    ↓
Verificação de Cache (Redis)
    ↓
[Cache Hit] → Retorna dados cached
    ↓
[Cache Miss] → Busca dados
    ↓
Scripts de Negócio (clientes.py, health_scores.py, dashboard.py)
    ↓
Bancos de Dados (PostgreSQL, MySQL)
    ↓
Processamento de Dados (Pandas)
    ↓
Salvar no Cache
    ↓
Retornar JSON ao Cliente
```

### Componentes Principais

#### 1. **Main Application** (`main.py`)
- Configuração do FastAPI
- Middlewares (CORS, GZIP)
- Autenticação HTTP Basic
- Sistema de cache distribuído
- Rotas principais

#### 2. **Business Logic** (`scripts/`)
- **clientes.py**: Busca e formatação de dados de clientes
- **health_scores.py**: Cálculo complexo de health scores (4 pilares)
- **dashboard.py**: Agregação de KPIs

#### 3. **Data Layer** (`lib/`)
- **models.py**: Validação de dados com Pydantic
- **queries.py**: Queries SQL otimizadas

---

## 🔐 Autenticação

### Método: HTTP Basic Authentication

Todos os endpoints (exceto `/` e `/health`) requerem autenticação.

### Headers Necessários
```http
Authorization: Basic base64(username:password)
```

### Configuração
Usuários são configurados via variável de ambiente:
```bash
BASIC_AUTH_USERS="user1:pass1,user2:pass2,admin:secret123"
```

### Exemplo com cURL
```bash
curl -u username:password https://api.ecosys.com/clientes
```

### Exemplo com Python
```python
import requests
from requests.auth import HTTPBasicAuth

response = requests.get(
    'https://api.ecosys.com/clientes',
    auth=HTTPBasicAuth('username', 'password')
)
```

### Resposta de Erro (401 Unauthorized)
```json
{
  "detail": "Acesso negado."
}
```

---

## 🔌 Endpoints

### 1. GET `/`

**Descrição**: Endpoint raiz, verifica se a API está online.

**Autenticação**: ❌ Não requerida

**Resposta**:
```json
{
  "message": "API de Gestão de Clientes está no ar!"
}
```

---

### 2. GET `/health`

**Descrição**: Health check completo da aplicação.

**Autenticação**: ❌ Não requerida

**Resposta de Sucesso (200)**:
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
  "timestamp": "2025-10-15T14:30:00.000Z"
}
```

**Resposta de Erro (500)**:
```json
{
  "detail": "Health check falhou: Redis connection failed"
}
```

**Uso**:
```bash
curl https://api.ecosys.com/health
```

---

### 3. GET `/clientes`

**Descrição**: Retorna lista completa de clientes com dados do Kommo CRM.

**Autenticação**: ✅ Requerida

**Query Parameters**:

| Parâmetro | Tipo | Obrigatório | Formato | Descrição |
|-----------|------|-------------|---------|-----------|
| `data_adesao_inicio` | string | Não | YYYY-MM-DD | Data inicial para filtro por data de adesão |
| `data_adesao_fim` | string | Não | YYYY-MM-DD | Data final para filtro por data de adesão |

**Cache**: 
- ✅ Sim 
- TTL: 300 segundos (5 minutos)
- Key: `clientes:{inicio}:{fim}`

**Resposta de Sucesso (200)**:
```json
{
  "1234": {
    "client_id": 1234,
    "nome": "Empresa XYZ Ltda",
    "razao_social": "XYZ Comércio e Serviços LTDA",
    "cnpj": 12345678000190,
    "valor": 1500.00,
    "vendedor": "João Silva",
    "cs": "Maria Santos",
    "status": "Ativo",
    "pipeline": "CS | ONGOING",
    "data_adesao": "2024-03-15T00:00:00",
    "data_start_onboarding": "2024-03-20T00:00:00",
    "data_end_onboarding": "2024-04-25T00:00:00",
    "data_cancelamento": null,
    "motivos_churn": null,
    "descricao_cancelamento": null,
    "criado_em": "2024-03-10T10:30:00",
    "atualizado_em": "2024-10-01T15:45:00"
  },
  "5678": {
    "client_id": 5678,
    "nome": "ABC Indústria",
    ...
  }
}
```

**Exemplos de Uso**:

```bash
# Todos os clientes
curl -u user:pass https://api.ecosys.com/clientes

# Clientes que aderiram em 2024
curl -u user:pass "https://api.ecosys.com/clientes?data_adesao_inicio=2024-01-01&data_adesao_fim=2024-12-31"

# Clientes desde junho de 2024
curl -u user:pass "https://api.ecosys.com/clientes?data_adesao_inicio=2024-06-01"
```

**Campos Retornados**:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `client_id` | int | ID único do cliente |
| `nome` | string | Nome fantasia |
| `razao_social` | string | Razão social completa |
| `cnpj` | int | CNPJ sem formatação |
| `valor` | float | Valor do contrato (MRR) |
| `vendedor` | string | Nome do vendedor responsável |
| `cs` | string | Customer Success responsável |
| `status` | string | Status atual no pipeline |
| `pipeline` | string | Pipeline do Kommo |
| `data_adesao` | datetime | Data de adesão ao sistema |
| `data_start_onboarding` | datetime | Início do onboarding |
| `data_end_onboarding` | datetime | Fim do onboarding |
| `data_cancelamento` | datetime | Data de cancelamento (se houver) |
| `motivos_churn` | string | Motivos do churn |
| `descricao_cancelamento` | string | Descrição do cancelamento |
| `criado_em` | datetime | Data de criação do registro |
| `atualizado_em` | datetime | Data de última atualização |

**Pipelines Possíveis**:
- `CS | ONBOARDING` - Cliente em processo de onboarding
- `CS | ONGOING` - Cliente ativo em operação
- `CS | BRADESCO` - Cliente Bradesco específico
- `Churns & Cancelamentos` - Cliente cancelado

---

### 4. GET `/health-scores`

**Descrição**: Retorna health scores calculados para todos os clientes ativos, baseado em 4 pilares.

**Autenticação**: ✅ Requerida

**Query Parameters**:

| Parâmetro | Tipo | Obrigatório | Formato | Descrição |
|-----------|------|-------------|---------|-----------|
| `data_adesao_inicio` | string | Não | YYYY-MM-DD | Data inicial para filtro |
| `data_adesao_fim` | string | Não | YYYY-MM-DD | Data final para filtro |

**Cache**: 
- ✅ Sim 
- TTL: 600 segundos (10 minutos)
- Key: `health-scores:{inicio}:{fim}`

**Resposta de Sucesso (200)**:
```json
{
  "12345": {
    "tenant_id": 12345,
    "slug": "empresa-xyz",
    "name": "Empresa XYZ Ltda",
    "cnpj": 12345678000190,
    "qntd_acessos_30d": 45,
    "dias_desde_ultimo_acesso": 2,
    "score_engajamento": 0.85,
    "qntd_entradas_30d": 120,
    "dias_desde_ultima_entrada": 1,
    "qntd_saidas_30d": 110,
    "dias_desde_ultima_saida": 1,
    "score_movimentacao_estoque": 0.92,
    "qntd_leads_30d": 25,
    "dias_desde_ultimo_lead": 3,
    "score_crm": 0.78,
    "econversa_ativo": true,
    "integradores_conectados": 2,
    "score_adoption": 0.88,
    "score_total": 0.86,
    "categoria": "Campeão"
  },
  "67890": {
    ...
  }
}
```

**Cálculo de Health Score**:

O score total é calculado com base em 4 pilares ponderados:

```
Score Total = (
  score_engajamento × 0.30 +
  score_movimentacao_estoque × 0.30 +
  score_crm × 0.20 +
  score_adoption × 0.20
)
```

**Categorias de Health**:

| Categoria | Score Range | Descrição |
|-----------|-------------|-----------|
| 🏆 **Campeão** | > 0.8 | Clientes exemplares |
| 💚 **Saudável** | 0.6 - 0.8 | Clientes em bom estado |
| 🟡 **Normal** | 0.3 - 0.6 | Clientes que precisam atenção |
| 🔴 **Crítico** | ≤ 0.3 | Clientes em risco |

**Exemplos de Uso**:

```bash
# Todos os health scores
curl -u user:pass https://api.ecosys.com/health-scores

# Health scores de clientes de 2024
curl -u user:pass "https://api.ecosys.com/health-scores?data_adesao_inicio=2024-01-01&data_adesao_fim=2024-12-31"
```

---

### 5. GET `/dashboard`

**Descrição**: Retorna KPIs principais do sistema em formato agregado.

**Autenticação**: ✅ Requerida

**Query Parameters**:

| Parâmetro | Tipo | Obrigatório | Formato | Descrição |
|-----------|------|-------------|---------|-----------|
| `data_adesao_inicio` | string | Não | YYYY-MM-DD | Data inicial para filtro |
| `data_adesao_fim` | string | Não | YYYY-MM-DD | Data final para filtro |

**Cache**: 
- ✅ Sim 
- TTL: 600 segundos (10 minutos)
- Key: `dashboard:{inicio}:{fim}`

**Resposta de Sucesso (200)**:
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

**KPIs Retornados**:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `clientes_ativos` | int | Total de clientes nas pipelines CS (ONBOARDING, ONGOING, BRADESCO) |
| `clientes_pagantes` | int | Clientes ativos com valor > 0 |
| `clientes_onboarding` | int | Clientes em onboarding sem data de finalização |
| `mrr_value` | float | Monthly Recurring Revenue (soma dos valores ativos) |
| `churn_value` | float | Valor total dos clientes em churn |
| `tmo_dias` | float | Tempo Médio de Onboarding em dias |
| `clientes_health` | object | Distribuição de clientes por categoria de health |

**Cálculo do TMO**:
```python
TMO = média((data_end_onboarding - data_start_onboarding).days)
```
- Considera apenas clientes com ambas as datas preenchidas
- Ignora tempos negativos ou zero
- Retorna 0.0 se não houver dados válidos

**Exemplos de Uso**:

```bash
# Dashboard completo
curl -u user:pass https://api.ecosys.com/dashboard

# Dashboard de clientes de 2024
curl -u user:pass "https://api.ecosys.com/dashboard?data_adesao_inicio=2024-01-01&data_adesao_fim=2024-12-31"

# Dashboard até março de 2024
curl -u user:pass "https://api.ecosys.com/dashboard?data_adesao_fim=2024-03-31"
```

---

### 6. POST `/cache/clear`

**Descrição**: Limpa o cache da aplicação.

**Autenticação**: ✅ Requerida

**Body**: Nenhum

**Resposta de Sucesso (200)**:
```json
{
  "status": "success",
  "message": "Cache será limpo automaticamente no próximo TTL",
  "note": "Para forçar atualização, aguarde o TTL expirar ou reinicie a aplicação"
}
```

**Exemplo de Uso**:
```bash
curl -X POST -u user:pass https://api.ecosys.com/cache/clear
```

**Nota**: O cache é distribuído no Redis, então limpar cache força o sistema a recalcular todos os dados nas próximas requisições.

---

### 7. GET `/logins`

**Descrição**: Retorna histórico de logins de um tenant específico nos últimos 30 dias.

**Autenticação**: ✅ Requerida

**Body (JSON)**:
```json
{
  "tenant_id": "12345"
}
```

**Resposta de Sucesso (200)**:
```json
{
  "tenant_id": 12345,
  "periodo": "últimos 30 dias",
  "total_logins": 45,
  "logins": [
    {
      "id": 98765,
      "usuario_nome": "João Silva",
      "usuario_email": "joao@empresa.com",
      "data_login": "2024-10-15T14:30:00",
      "data": "2024-10-15",
      "hora": "14:30:00"
    },
    {
      "id": 98764,
      "usuario_nome": "Maria Santos",
      "usuario_email": "maria@empresa.com",
      "data_login": "2024-10-15T09:15:00",
      "data": "2024-10-15",
      "hora": "09:15:00"
    }
  ],
  "usuarios_unicos": 8,
  "dias_com_acesso": 22
}
```

**Exemplo de Uso**:
```bash
curl -X GET -u user:pass \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"12345"}' \
  https://api.ecosys.com/logins
```

---

## 📦 Modelos de Dados

### Cliente

```python
class Cliente(BaseModel):
    client_id: int                        # ID único
    nome: Optional[str]                   # Nome fantasia
    razao_social: Optional[str]           # Razão social
    cnpj: Optional[int]                   # CNPJ sem formatação
    valor: float = 0.0                    # Valor do contrato
    vendedor: Optional[str]               # Nome do vendedor
    cs: Optional[str]                     # Customer Success
    status: Optional[str]                 # Status no pipeline
    pipeline: Optional[str]               # Pipeline do Kommo
    data_adesao: Optional[str]            # Data de adesão
    data_start_onboarding: Optional[str]  # Início do onboarding
    data_end_onboarding: Optional[str]    # Fim do onboarding
    tmo: Optional[int]                    # Tempo de onboarding
    data_cancelamento: Optional[str]      # Data de cancelamento
    motivos_churn: Optional[str]          # Motivos do churn
    descricao_cancelamento: Optional[str] # Descrição do cancelamento
    criado_em: Optional[str]              # Data de criação
    atualizado_em: Optional[str]          # Última atualização
```

### ClientScoreHealth

```python
class ClientScoreHealth(BaseModel):
    tenant_id: int                        # ID do tenant
    cnpj: Optional[int]                   # CNPJ
    
    # Pilar 1: Engajamento
    qntd_acessos_30d: int = 0             # Quantidade de acessos
    dias_desde_ultimo_acesso: int = 9999  # Dias sem acessar
    score_engajamento: float = 0.0        # Score (0-1)
    
    # Pilar 2: Movimentação de Estoque
    qntd_entradas_30d: int = 0            # Entradas no estoque
    dias_desde_ultima_entrada: int = 9999 # Dias sem entrada
    qntd_saidas_30d: int = 0              # Saídas do estoque
    dias_desde_ultima_saida: int = 9999   # Dias sem saída
    score_movimentacao_estoque: float = 0.0 # Score (0-1)
    
    # Pilar 3: CRM
    qntd_leads_30d: int = 0               # Leads criados
    dias_desde_ultimo_lead: int = 9999    # Dias sem lead
    score_crm: float = 0.0                # Score (0-1)
    
    # Pilar 4: Adoção
    score_adoption: float = 0.0           # Score (0-1)
    
    # Score Final
    score_total: float = 0.0              # Score total (0-1)
    categoria: Optional[str]              # Crítico/Normal/Saudável/Campeão
```

### LoginRequest

```python
class LoginRequest(BaseModel):
    tenant_id: str  # ID do tenant para buscar logins
```

---

## 💾 Sistema de Cache

### Estratégia de Cache

A API utiliza **cache distribuído** com Redis (Upstash) para otimizar performance.

### Configuração de TTL

| Endpoint | TTL | Descrição |
|----------|-----|-----------|
| `/clientes` | 300s (5 min) | Dados mudam com menos frequência |
| `/health-scores` | 600s (10 min) | Cálculos complexos, cache mais longo |
| `/dashboard` | 600s (10 min) | KPIs agregados |

### Chaves de Cache Dinâmicas

O sistema gera chaves únicas baseadas nos filtros:

```python
# Formato
"{endpoint}:{data_inicio}:{data_fim}"

# Exemplos
"clientes:all:all"                    # Sem filtros
"clientes:2024-01-01:all"            # Apenas início
"health-scores:all:2024-12-31"       # Apenas fim
"dashboard:2024-01-01:2024-12-31"    # Ambos os filtros
```

### Benefícios

- ✅ **Performance**: Respostas instantâneas para dados já processados
- ✅ **Redução de Carga**: Menos queries nos bancos de dados
- ✅ **Escalabilidade**: Cache distribuído entre instâncias
- ✅ **Granularidade**: Cada combinação de filtros tem seu cache

### Logs de Cache

```log
# Cache Hit (dados encontrados)
✅ Cache hit para clientes:2024-01-01:all

# Cache Miss (dados não encontrados, buscando)
❌ Cache miss para dashboard:all:all, buscando dados...
💾 Dados salvos no cache: dashboard:all:all (TTL: 600s)
```

### Limpeza Manual

```bash
# Limpar cache via API
curl -X POST -u user:pass https://api.ecosys.com/cache/clear

# Cache será regenerado na próxima requisição
```

---

## 📊 Health Scores

### Conceito

O **Health Score** é uma métrica composta que avalia a "saúde" de cada cliente baseado em 4 pilares de comportamento no sistema.

### Pilares e Pesos

| Pilar | Peso | Descrição |
|-------|------|-----------|
| **1. Engajamento** | 30% | Frequência de acessos ao sistema |
| **2. Movimentação de Estoque** | 30% | Uso ativo do módulo de estoque |
| **3. CRM** | 20% | Gestão de leads e oportunidades |
| **4. Adoção** | 20% | Uso de integrações e features avançadas |

### Pilar 1: Engajamento (30%)

**Métrica**: Frequência de login no sistema

**Componentes**:
- **Quantidade de acessos** nos últimos 30 dias
- **Dias desde o último acesso**

**Fórmula**:
```python
score_engajamento = (score_ultimo_acesso + score_qntd_acessos) / 2

# Score por último acesso
- ≤ 3 dias: 1.0
- ≤ 7 dias: 0.9
- ≤ 14 dias: 0.6
- ≤ 30 dias: 0.2
- > 30 dias: 0.0

# Score por quantidade de acessos
- > 75 acessos: 1.2
- > 40 acessos: 1.0
- > 25 acessos: 0.7
- > 11 acessos: 0.5
- > 6 acessos: 0.3
- > 1 acesso: 0.15
- 0 acessos: 0.0
```

**Exemplo**:
- Cliente com 45 acessos nos últimos 30 dias
- Último acesso há 2 dias
- Score: (1.0 + 1.0) / 2 = **1.0** (100%)

### Pilar 2: Movimentação de Estoque (30%)

**Métrica**: Uso do módulo de gestão de estoque

**Componentes**:
- **Quantidade de entradas** nos últimos 30 dias
- **Dias desde a última entrada**
- **Quantidade de saídas** nos últimos 30 dias
- **Dias desde a última saída**

**Fórmula**:
```python
score_movimentacao = (
  score_ultima_entrada + 
  score_qntd_entradas + 
  score_ultima_saida + 
  score_qntd_saidas
) / 4

# Scores de entrada (similar para saída)
- ≤ 3 dias: 1.0
- ≤ 7 dias: 0.8
- ≤ 14 dias: 0.5
- ≤ 30 dias: 0.2
- > 30 dias: 0.0

# Quantidade de movimentações
- > 50: 1.0
- > 30: 0.8
- > 15: 0.6
- > 5: 0.4
- > 1: 0.2
- 0: 0.0
```

**Exemplo**:
- 120 entradas, última há 1 dia: (1.0 + 1.0) = 2.0
- 110 saídas, última há 1 dia: (1.0 + 1.0) = 2.0
- Score: (2.0 + 2.0) / 4 = **1.0** (100%)

### Pilar 3: CRM (20%)

**Métrica**: Gestão de leads e oportunidades

**Componentes**:
- **Quantidade de leads criados** nos últimos 30 dias
- **Dias desde o último lead criado**

**Fórmula**:
```python
score_crm = (score_ultimo_lead + score_qntd_leads) / 2

# Score por último lead
- ≤ 3 dias: 1.0
- ≤ 7 dias: 0.8
- ≤ 14 dias: 0.5
- ≤ 30 dias: 0.2
- > 30 dias: 0.0

# Score por quantidade de leads
- > 30: 1.0
- > 20: 0.8
- > 10: 0.6
- > 5: 0.4
- > 1: 0.2
- 0: 0.0
```

**Exemplo**:
- 25 leads criados nos últimos 30 dias
- Último lead há 3 dias
- Score: (1.0 + 0.8) / 2 = **0.9** (90%)

### Pilar 4: Adoção (20%)

**Métrica**: Uso de features avançadas e integrações

**Componentes**:
- **eConversa ativo** (chat interno)
- **Integradores conectados** (APIs, ERPs, etc)

**Fórmula**:
```python
score_adoption = (econversa_score + integradores_score) / 2

# eConversa
- Ativo: 1.0
- Inativo: 0.0

# Integradores
- ≥ 2 integradores: 1.0
- 1 integrador: 0.5
- 0 integradores: 0.0
```

**Exemplo**:
- eConversa ativo: 1.0
- 2 integradores conectados: 1.0
- Score: (1.0 + 1.0) / 2 = **1.0** (100%)

### Score Total

```python
score_total = (
  score_engajamento × 0.30 +
  score_movimentacao_estoque × 0.30 +
  score_crm × 0.20 +
  score_adoption × 0.20
)
```

**Exemplo Completo**:
```python
score_total = (
  1.0 × 0.30 +  # Engajamento
  1.0 × 0.30 +  # Estoque
  0.9 × 0.20 +  # CRM
  1.0 × 0.20    # Adoção
) = 0.98
```

### Categorização

Após calcular o score total, o cliente é categorizado:

```python
if score_total > 0.8:
    categoria = "Campeão"  # 🏆
elif score_total > 0.6:
    categoria = "Saudável"  # 💚
elif score_total > 0.3:
    categoria = "Normal"    # 🟡
else:
    categoria = "Crítico"   # 🔴
```

### Distribuição Típica

```
🏆 Campeão (>0.8):   15-20% dos clientes
💚 Saudável (0.6-0.8): 40-45% dos clientes
🟡 Normal (0.3-0.6):   30-35% dos clientes
🔴 Crítico (≤0.3):     5-10% dos clientes
```

### Ações Recomendadas por Categoria

| Categoria | Ação | Prioridade |
|-----------|------|------------|
| 🏆 Campeão | Manter engajamento, buscar upsell | Baixa |
| 💚 Saudável | Monitorar, incentivar uso de features | Média |
| 🟡 Normal | Reunião de alinhamento, treinar time | Alta |
| 🔴 Crítico | Ação imediata, risco de churn | Crítica |

---

## ⚙️ Configuração

### Variáveis de Ambiente Obrigatórias

```bash
# Redis Cache (Upstash)
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-token-here

# Autenticação
BASIC_AUTH_USERS=user1:pass1,user2:pass2,admin:secret

# PostgreSQL (Kommo CRM)
DB_NAME=kommo_db
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432

# MySQL (EcoSys Data)
DB_HOST_ECOSYS=localhost
DB_NAME_ECOSYS=ecosys_db
DB_USER_ECOSYS=root
DB_PASSWORD_ECOSYS=yourpassword

# Ambiente
ENVIRONMENT=production  # ou 'development'
```

### Arquivo `.env` de Exemplo

```bash
# .env
ENVIRONMENT=development

# Redis
UPSTASH_REDIS_REST_URL=https://your-project.upstash.io
UPSTASH_REDIS_REST_TOKEN=AXvxAAIjcDxxxxxxxxxxxxxxxxxxxxxxx

# Auth
BASIC_AUTH_USERS=admin:admin123,user:pass123

# PostgreSQL
DB_NAME=kommo_production
DB_USER=kommo_user
DB_PASSWORD=K0mm0P@ssw0rd!
DB_HOST=postgres.server.com
DB_PORT=5432

# MySQL
DB_HOST_ECOSYS=mysql.server.com
DB_NAME_ECOSYS=ecosys_production
DB_USER_ECOSYS=ecosys_user
DB_PASSWORD_ECOSYS=Ec0Sys@2024!
```

### Instalação de Dependências

```bash
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente (Windows)
.\venv\Scripts\activate

# Ativar ambiente (Linux/Mac)
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### `requirements.txt`

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-dotenv==1.0.0
psycopg2-binary==2.9.9
mysql-connector-python==8.2.0
pandas==2.1.3
upstash-redis==0.15.0
pydantic==2.5.0
python-multipart==0.0.6
```

### Executar Aplicação

```bash
# Desenvolvimento (com reload)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Produção
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker (Opcional)

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: unless-stopped
```

---

## 📝 Exemplos de Uso

### Python

```python
import requests
from requests.auth import HTTPBasicAuth

# Configuração
BASE_URL = "https://api.ecosys.com"
AUTH = HTTPBasicAuth('username', 'password')

# 1. Verificar saúde da API
response = requests.get(f"{BASE_URL}/health")
print(response.json())

# 2. Buscar todos os clientes
response = requests.get(
    f"{BASE_URL}/clientes",
    auth=AUTH
)
clientes = response.json()
print(f"Total de clientes: {len(clientes)}")

# 3. Buscar clientes de 2024
response = requests.get(
    f"{BASE_URL}/clientes",
    params={
        'data_adesao_inicio': '2024-01-01',
        'data_adesao_fim': '2024-12-31'
    },
    auth=AUTH
)
clientes_2024 = response.json()

# 4. Buscar health scores
response = requests.get(
    f"{BASE_URL}/health-scores",
    auth=AUTH
)
health_scores = response.json()

# Filtrar clientes críticos
criticos = {
    k: v for k, v in health_scores.items() 
    if v['categoria'] == 'Crítico'
}
print(f"Clientes críticos: {len(criticos)}")

# 5. Buscar KPIs do dashboard
response = requests.get(
    f"{BASE_URL}/dashboard",
    auth=AUTH
)
dashboard = response.json()
print(f"MRR: R$ {dashboard['mrr_value']:,.2f}")
print(f"TMO: {dashboard['tmo_dias']} dias")

# 6. Limpar cache
response = requests.post(
    f"{BASE_URL}/cache/clear",
    auth=AUTH
)
print(response.json())
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');

const BASE_URL = 'https://api.ecosys.com';
const AUTH = {
  username: 'username',
  password: 'password'
};

// 1. Buscar clientes
async function getClientes() {
  try {
    const response = await axios.get(`${BASE_URL}/clientes`, { auth: AUTH });
    console.log(`Total de clientes: ${Object.keys(response.data).length}`);
    return response.data;
  } catch (error) {
    console.error('Erro:', error.response.data);
  }
}

// 2. Buscar dashboard com filtros
async function getDashboard(dataInicio, dataFim) {
  try {
    const response = await axios.get(`${BASE_URL}/dashboard`, {
      auth: AUTH,
      params: {
        data_adesao_inicio: dataInicio,
        data_adesao_fim: dataFim
      }
    });
    return response.data;
  } catch (error) {
    console.error('Erro:', error.response.data);
  }
}

// 3. Buscar health scores e filtrar por categoria
async function getClientesCriticos() {
  try {
    const response = await axios.get(`${BASE_URL}/health-scores`, { auth: AUTH });
    const healthScores = response.data;
    
    const criticos = Object.entries(healthScores)
      .filter(([_, cliente]) => cliente.categoria === 'Crítico')
      .map(([tenantId, cliente]) => ({
        tenantId,
        nome: cliente.name,
        score: cliente.score_total
      }));
    
    console.log('Clientes críticos:', criticos);
    return criticos;
  } catch (error) {
    console.error('Erro:', error.response.data);
  }
}

// Executar
(async () => {
  await getClientes();
  const dashboard = await getDashboard('2024-01-01', '2024-12-31');
  console.log('Dashboard 2024:', dashboard);
  await getClientesCriticos();
})();
```

### cURL

```bash
# 1. Health check
curl https://api.ecosys.com/health

# 2. Buscar todos os clientes
curl -u username:password https://api.ecosys.com/clientes

# 3. Buscar clientes de 2024
curl -u username:password \
  "https://api.ecosys.com/clientes?data_adesao_inicio=2024-01-01&data_adesao_fim=2024-12-31"

# 4. Buscar health scores
curl -u username:password https://api.ecosys.com/health-scores

# 5. Buscar dashboard
curl -u username:password https://api.ecosys.com/dashboard

# 6. Buscar dashboard filtrado
curl -u username:password \
  "https://api.ecosys.com/dashboard?data_adesao_inicio=2024-06-01"

# 7. Limpar cache
curl -X POST -u username:password https://api.ecosys.com/cache/clear

# 8. Salvar resposta em arquivo
curl -u username:password https://api.ecosys.com/clientes > clientes.json
```

### Postman Collection

```json
{
  "info": {
    "name": "EcoSys API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "auth": {
    "type": "basic",
    "basic": [
      {"key": "username", "value": "{{username}}"},
      {"key": "password", "value": "{{password}}"}
    ]
  },
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/health"
      }
    },
    {
      "name": "Get Clientes",
      "request": {
        "method": "GET",
        "url": {
          "raw": "{{base_url}}/clientes?data_adesao_inicio=&data_adesao_fim=",
          "query": [
            {"key": "data_adesao_inicio", "value": ""},
            {"key": "data_adesao_fim", "value": ""}
          ]
        }
      }
    },
    {
      "name": "Get Health Scores",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/health-scores"
      }
    },
    {
      "name": "Get Dashboard",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/dashboard"
      }
    },
    {
      "name": "Clear Cache",
      "request": {
        "method": "POST",
        "url": "{{base_url}}/cache/clear"
      }
    }
  ],
  "variable": [
    {"key": "base_url", "value": "https://api.ecosys.com"},
    {"key": "username", "value": "your_username"},
    {"key": "password", "value": "your_password"}
  ]
}
```

---

## 🔍 Troubleshooting

### Problema: Erro 401 Unauthorized

**Sintoma**:
```json
{
  "detail": "Acesso negado."
}
```

**Causas**:
- Usuário ou senha incorretos
- Credenciais não configuradas no `.env`
- Header `Authorization` ausente

**Solução**:
```bash
# Verificar variável de ambiente
echo $BASIC_AUTH_USERS

# Testar com cURL
curl -u username:password https://api.ecosys.com/clientes

# Verificar se o usuário existe
# .env deve ter: BASIC_AUTH_USERS=username:password
```

---

### Problema: Erro 500 Internal Server Error

**Sintoma**:
```json
{
  "detail": "Erro ao obter clientes: connection refused"
}
```

**Causas**:
- Banco de dados offline
- Credenciais de banco incorretas
- Redis não conectado

**Solução**:
```bash
# 1. Verificar health check
curl https://api.ecosys.com/health

# 2. Verificar logs
tail -f logs/api.log

# 3. Testar conexão com banco
psql -h $DB_HOST -U $DB_USER -d $DB_NAME

# 4. Verificar Redis
redis-cli -h redis.upstash.io ping
```

---

### Problema: Cache Não Está Funcionando

**Sintoma**:
Todas as requisições demoram o mesmo tempo (não há cache hit)

**Logs Esperados**:
```
❌ Cache miss para clientes:all:all, buscando dados...
💾 Dados salvos no cache: clientes:all:all (TTL: 300s)
```

**Causas**:
- Redis offline
- Credenciais Redis incorretas
- TTL muito baixo

**Solução**:
```bash
# 1. Verificar conexão Redis
curl -X GET \
  -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" \
  $UPSTASH_REDIS_REST_URL/ping

# 2. Verificar variáveis de ambiente
echo $UPSTASH_REDIS_REST_URL
echo $UPSTASH_REDIS_REST_TOKEN

# 3. Verificar logs da aplicação
# Deve mostrar: "✅ Cache hit" nas requisições subsequentes
```

---

### Problema: Timeout nas Requisições

**Sintoma**:
Requisições demoram muito ou dão timeout

**Causas**:
- Queries SQL lentas
- Banco de dados sobrecarregado
- Cache expirado

**Solução**:
```bash
# 1. Verificar tempo de resposta sem cache
time curl -u user:pass https://api.ecosys.com/health-scores

# 2. Aumentar TTL do cache (em main.py)
CACHE_TTL_HEALTH_SCORES = 1200  # 20 minutos

# 3. Otimizar queries (adicionar índices)
# No PostgreSQL:
CREATE INDEX idx_clientes_data_adesao ON clientes_kommo(data_adesao);

# No MySQL:
CREATE INDEX idx_tenant_id ON tenants(id);
CREATE INDEX idx_activity_log_tenant ON activity_log(tenant_id, created_at);
```

---

### Problema: TMO Retorna 0.0

**Sintoma**:
```json
{
  "tmo_dias": 0.0
}
```

**Causas**:
- Nenhum cliente tem `data_start_onboarding` e `data_end_onboarding`
- Datas inválidas
- Todos os tempos são negativos

**Solução**:
```sql
-- Verificar quantos clientes têm ambas as datas
SELECT COUNT(*) 
FROM clientes_kommo 
WHERE data_start_onboarding IS NOT NULL 
  AND data_end_onboarding IS NOT NULL;

-- Verificar se as datas são válidas
SELECT 
  client_id,
  data_start_onboarding,
  data_end_onboarding,
  DATEDIFF(data_end_onboarding, data_start_onboarding) as dias
FROM clientes_kommo 
WHERE data_start_onboarding IS NOT NULL 
  AND data_end_onboarding IS NOT NULL
  AND DATEDIFF(data_end_onboarding, data_start_onboarding) > 0;
```

**Verificar Logs**:
```
INFO: TMO: 0.0 dias (baseado em 0 clientes)  <- Nenhum cliente válido
INFO: TMO: 42.5 dias (baseado em 35 clientes)  <- OK
```

---

### Problema: Filtro por Data Não Funciona

**Sintoma**:
Filtrar por data retorna os mesmos resultados que sem filtro

**Causas**:
- Formato de data incorreto
- Campo `data_adesao` nulo nos clientes
- Cache com dados antigos

**Solução**:
```bash
# 1. Usar formato correto YYYY-MM-DD
curl -u user:pass \
  "https://api.ecosys.com/clientes?data_adesao_inicio=2024-01-01&data_adesao_fim=2024-12-31"

# 2. Limpar cache
curl -X POST -u user:pass https://api.ecosys.com/cache/clear

# 3. Verificar se clientes têm data_adesao
SELECT COUNT(*), 
       COUNT(data_adesao) as com_data,
       COUNT(*) - COUNT(data_adesao) as sem_data
FROM clientes_kommo;
```

---

### Problema: Health Scores Muito Baixos

**Sintoma**:
Todos os clientes aparecem como "Crítico"

**Causas**:
- Dados de atividade ausentes
- Queries não retornam resultados
- Cálculo incorreto

**Solução**:
```bash
# 1. Verificar dados de atividade
SELECT COUNT(*) FROM activity_log WHERE event = 'login' AND created_at >= CURDATE() - INTERVAL 30 DAY;
SELECT COUNT(*) FROM inventory_entries WHERE created_at >= CURDATE() - INTERVAL 30 DAY;

# 2. Verificar logs do cálculo
# Deve mostrar:
# "Pilar 1: score_engajamento calculado para X tenants"
# "Pilar 2: score_estoque calculado para X tenants"

# 3. Testar query individual
# Executar PRIMEIRO_PILAR, SEGUNDO_PILAR, etc. manualmente
```

---

### Problema: Memory Leak ou Alto Consumo de Memória

**Sintoma**:
Aplicação consome cada vez mais memória

**Causas**:
- Connection pooling inadequado
- DataFrames não sendo liberados
- Cache crescendo indefinidamente

**Solução**:
```python
# 1. Limitar tamanho do pool de conexões (em health_scores.py)
connection_pool = pooling.MySQLConnectionPool(
    pool_name="ecosys_pool",
    pool_size=3,  # Reduzir de 5 para 3
    # ...
)

# 2. Adicionar garbage collection
import gc

@app.middleware("http")
async def cleanup_middleware(request, call_next):
    response = await call_next(request)
    gc.collect()
    return response

# 3. Monitorar memória
import psutil
process = psutil.Process()
logger.info(f"Memória: {process.memory_info().rss / 1024 / 1024:.2f} MB")
```

---

## 📚 Recursos Adicionais

### Documentação Relacionada

- [DASHBOARD_DOCS.md](./DASHBOARD_DOCS.md) - Documentação específica do dashboard
- [REFACTORING_HEALTH_SCORES.md](./REFACTORING_HEALTH_SCORES.md) - Refatoração dos health scores
- [FILTROS_E_TMO_DOCS.md](./FILTROS_E_TMO_DOCS.md) - Filtros por data e TMO

### Links Úteis

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Upstash Redis](https://docs.upstash.com/redis)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [MySQL Documentation](https://dev.mysql.com/doc/)

### Equipe

- **Desenvolvimento**: EcoSys Team
- **Manutenção**: CS Team
- **Contato**: support@ecosys.com

---

## ✅ Checklist de Deployment

### Pré-Deploy

- [ ] Todas as variáveis de ambiente configuradas
- [ ] Credenciais de banco de dados testadas
- [ ] Redis conectado e funcionando
- [ ] Testes de autenticação passando
- [ ] Cache funcionando corretamente

### Deploy

- [ ] Build da aplicação sem erros
- [ ] Migrations de banco executadas
- [ ] Índices criados nas tabelas
- [ ] Health check respondendo
- [ ] Logs configurados

### Pós-Deploy

- [ ] Testar todos os endpoints
- [ ] Verificar performance do cache
- [ ] Monitorar logs de erro
- [ ] Validar cálculo de health scores
- [ ] Confirmar TMO calculando corretamente

---

## 📊 Métricas e Monitoramento

### KPIs da API

| Métrica | Target | Como Medir |
|---------|--------|------------|
| Uptime | > 99.9% | Health check endpoint |
| Response Time (sem cache) | < 2s | Logs de performance |
| Response Time (com cache) | < 100ms | Cache hit rate |
| Cache Hit Rate | > 80% | Logs de cache |
| Error Rate | < 0.1% | Logs de erro |

### Logs Importantes

```log
# Sucesso
INFO: ✅ Cache hit para clientes:all:all
INFO: Clientes ativos: 45
INFO: TMO: 42.5 dias (baseado em 35 clientes)

# Atenção
WARNING: ⚠️ Erro ao acessar cache: Connection timeout
WARNING: Formato inválido para data_adesao_inicio: 2024/01/01

# Erro
ERROR: Erro ao obter clientes: connection refused
ERROR: Health check falhou: Redis connection failed
```

---

## 🎉 Conclusão

Esta API fornece uma solução completa para:
- ✅ Gestão de dados de clientes
- ✅ Análise de saúde dos clientes (4 pilares)
- ✅ KPIs de negócio em tempo real
- ✅ Sistema de cache otimizado
- ✅ Autenticação segura
- ✅ Filtros flexíveis por data

**Performance**:
- Respostas < 100ms com cache
- Cache hit rate > 80%
- Suporta milhares de clientes simultaneamente

**Escalabilidade**:
- Cache distribuído (Redis)
- Thread pool para operações bloqueantes
- Connection pooling nos bancos

**Manutenibilidade**:
- Código bem documentado
- Separação clara de responsabilidades
- Logs detalhados
- Tratamento robusto de erros

---

**Última atualização**: 15 de Outubro de 2025  
**Versão da Documentação**: 1.0.0  
**Autor**: EcoSys Development Team
