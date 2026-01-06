# PRD - ecosys Payments API
## Backend de Gestão de Pagamentos com Asaas

**Versão:** 2.0  
**Data:** 02 de Janeiro de 2026  
**Produto:** ecosys Payments API  
**Repositório:** [ecosysMS-Back](https://github.com/danexplore/ecosysMS-Back)

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Objetivos e Metas](#objetivos-e-metas)
3. [Arquitetura do Sistema](#arquitetura-do-sistema)
4. [Módulos e Endpoints](#módulos-e-endpoints)
5. [Níveis de Usuários e Permissões](#níveis-de-usuários-e-permissões)
6. [Integração com Asaas](#integração-com-asaas)
7. [Especificações Técnicas](#especificações-técnicas)
8. [Modelos de Dados](#modelos-de-dados)
9. [Fluxos do Sistema](#fluxos-do-sistema)
10. [Roadmap de Desenvolvimento](#roadmap-de-desenvolvimento)
11. [Métricas de Sucesso](#métricas-de-sucesso)
12. [Riscos e Mitigações](#riscos-e-mitigações)
13. [Anexos](#anexos)
14. [Conclusão](#conclusão)

---

## 1. Visão Geral

### 1.1 Propósito do Produto

O **ecosys Payments API** é o backend responsável pela gestão de pagamentos utilizando o Asaas como gateway. A API permite gerenciar todo o ciclo de recebimentos, desde a criação de cobranças até o acompanhamento de clientes e assinaturas, fornecendo endpoints RESTful para consumo por aplicações frontend.

### 1.2 Proposta de Valor

- **Extensão do Sistema Atual:** Reutiliza módulos existentes de clientes e pagamentos
- **Integração Asaas:** Gateway de pagamento brasileiro
- **Cache Eficiente:** Aproveita Upstash Redis já configurado
- **Deploy Simplificado:** Serverless na Vercel (já em uso)

---

## 2. Objetivos e Metas

### 2.1 Objetivos

- Adicionar integração com Asaas ao sistema existente
- Reutilizar estrutura de clientes e pagamentos (`lib/clientes_queries.py`, `lib/pagamentos_queries.py`)
- Criar endpoints mínimos para operações essenciais
- Manter compatibilidade total com o ecosysMS-Back

### 2.2 Metas (2 meses)

- ✅ Integração Asaas funcionando
- ✅ CRUD de pagamentos e assinaturas
- ✅ Sincronização de clientes
- ✅ Dashboard com MRR

---

## 3. Arquitetura do Sistema

### 3.1 Diagrama de Alto Nível

```
┌─────────────────────────────────────────────────────────┐
│                  ecosys Payments API                     │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Vercel     │  │   FastAPI    │  │  PostgreSQL  │  │
│  │  Serverless  │◄─┤   Backend    │◄─┤   (Supabase) │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         │                  │                  │         │
│         │                  ▼                  │         │
│         │         ┌──────────────┐            │         │
│         │         │ Upstash Redis│            │         │
│         │         │   (Cache)    │            │         │
│         │         └──────────────┘            │         │
│         │                  │                  │         │
│         └──────────────────┼──────────────────┘         │
│                            ▼                             │
│                   ┌─────────────────┐                    │
│                   │   Asaas API     │                    │
│                   │   (Gateway)     │                    │
│                   └─────────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Tecnologias Core

**Backend (Python)**
- Python 3.11+
- FastAPI
- Pydantic (validação de dados)
- psycopg2 (PostgreSQL driver)
- Upstash Redis (cache)
- python-dotenv

**Database**
- PostgreSQL 15+ (Supabase)
- Upstash Redis (cache/sessões)

**Infraestrutura**
- Vercel (Serverless Functions)
- Supabase (Database)
- Asaas API (Pagamentos)

---

## 4. Módulos e Endpoints

### 4.1 Módulo - Checkout (Cobranças)

**Descrição:** Endpoints para criação e gestão de links de pagamento

**Endpoints:**

```
POST   /api/v1/payments                 # Criar cobrança
GET    /api/v1/payments                 # Listar cobranças
GET    /api/v1/payments/{id}            # Detalhes da cobrança
PUT    /api/v1/payments/{id}            # Atualizar cobrança
DELETE /api/v1/payments/{id}            # Cancelar cobrança
GET    /api/v1/payments/{id}/link       # Obter link de pagamento
POST   /api/v1/payments/{id}/refund     # Estornar pagamento
```

**Funcionalidades:**
- ✅ Criação de cobranças avulsas
- ✅ Seleção de produto/plano do banco
- ✅ Configuração de valores e parcelamento
- ✅ Geração de link de pagamento único
- ✅ Suporte a PIX, Boleto, Cartão
- ✅ Histórico de cobranças por cliente

**Integração Asaas:**
- `POST /v3/payments` - Criar cobrança
- `GET /v3/payments/{id}` - Consultar cobrança

---

### 4.2 Módulo - Gestão de Clientes

**Descrição:** Gerenciamento completo da base de clientes

**Endpoints:**

```
GET    /api/v1/customers                # Listar clientes
POST   /api/v1/customers                # Criar cliente
GET    /api/v1/customers/{id}           # Detalhes do cliente
PUT    /api/v1/customers/{id}           # Atualizar cliente
DELETE /api/v1/customers/{id}           # Remover cliente
GET    /api/v1/customers/{id}/payments  # Pagamentos do cliente
GET    /api/v1/customers/{id}/subscriptions  # Assinaturas do cliente
GET    /api/v1/customers/stats          # Estatísticas de clientes
```

**Funcionalidades:**
- ✅ CRUD completo de clientes
- ✅ Filtros: Ativos, Inativos, Inadimplentes
- ✅ Histórico de pagamentos por cliente
- ✅ Sincronização automática com Asaas
- ✅ Validação de CPF/CNPJ
- ✅ Busca avançada

**Integração Asaas:**
- `GET /v3/customers` - Listar clientes
- `GET /v3/customers/{id}` - Detalhes do cliente
- `POST /v3/customers` - Criar cliente
- `PUT /v3/customers/{id}` - Atualizar cliente
- `DELETE /v3/customers/{id}` - Remover cliente

---

### 4.3 Módulo - Gestão de Assinaturas

**Descrição:** Controle de assinaturas recorrentes

**Endpoints:**

```
GET    /api/v1/subscriptions            # Listar assinaturas
POST   /api/v1/subscriptions            # Criar assinatura
GET    /api/v1/subscriptions/{id}       # Detalhes da assinatura
PUT    /api/v1/subscriptions/{id}       # Atualizar assinatura
DELETE /api/v1/subscriptions/{id}       # Cancelar assinatura
POST   /api/v1/subscriptions/{id}/pause # Pausar assinatura
POST   /api/v1/subscriptions/{id}/resume # Reativar assinatura
GET    /api/v1/subscriptions/{id}/payments # Cobranças da assinatura
GET    /api/v1/subscriptions/metrics    # Métricas (MRR, Churn)
```

**Funcionalidades:**
- ✅ Lista de assinaturas ativas
- ✅ Detalhes da assinatura (plano, valor, ciclo)
- ✅ Histórico de cobranças da assinatura
- ✅ Pausar/Reativar assinatura
- ✅ Cancelar assinatura
- ✅ Alterar plano (upgrade/downgrade)
- ✅ Cálculo de MRR

**Integração Asaas:**
- `GET /v3/subscriptions` - Listar assinaturas
- `GET /v3/subscriptions/{id}` - Detalhes da assinatura
- `POST /v3/subscriptions` - Criar assinatura
- `PUT /v3/subscriptions/{id}` - Atualizar assinatura
- `DELETE /v3/subscriptions/{id}` - Cancelar assinatura

---

### 4.4 Módulo - Produtos e Planos

**Descrição:** Gestão de produtos e planos disponíveis para checkout

**Endpoints:**

```
GET    /api/v1/products                 # Listar produtos
POST   /api/v1/products                 # Criar produto
GET    /api/v1/products/{id}            # Detalhes do produto
PUT    /api/v1/products/{id}            # Atualizar produto
DELETE /api/v1/products/{id}            # Remover produto
GET    /api/v1/products/active          # Produtos ativos
```

**Funcionalidades:**
- ✅ Cadastro de produtos/planos
- ✅ Configuração de preços
- ✅ Definição de ciclos de cobrança
- ✅ Métodos de pagamento aceitos
- ✅ Ativar/Desativar produtos

---

### 4.5 Módulo - Dashboard e Métricas

**Descrição:** Endpoints para métricas e KPIs

**Endpoints:**

```
GET    /api/v1/dashboard                # Métricas gerais
GET    /api/v1/dashboard/mrr            # MRR mensal
GET    /api/v1/dashboard/churn          # Taxa de churn
GET    /api/v1/dashboard/payments       # Resumo de pagamentos
GET    /api/v1/dashboard/overdue        # Clientes inadimplentes
GET    /api/v1/dashboard/revenue        # Receita por período
```

**Funcionalidades:**
- ✅ MRR (Monthly Recurring Revenue)
- ✅ Taxa de churn
- ✅ Conversão de checkouts
- ✅ Clientes inadimplentes
- ✅ Filtros por período

---



## 5. Níveis de Usuários e Permissões

### 5.1 Controle de Acesso

**Nota:** A API não implementa camada própria de autenticação. O controle de acesso e permissões é gerenciado pela aplicação frontend/principal que consome esta API.

A API fornece endpoints RESTful públicos (dentro da rede/infraestrutura) para operações CRUD em:
- Pagamentos
- Clientes
- Assinaturas
- Produtos
- Dashboard/Métricas

### 5.2 Matriz de Permissões por Endpoint

**Nota:** O controle de permissões será gerenciado pela aplicação frontend. A API implementará os endpoints sem camada de autenticação própria.

| Módulo | Endpoint Base |
|--------|---------------|
| **Payments** | `/api/v1/asaas/payments` |
| **Customers** | `/api/v1/asaas/customers` |
| **Subscriptions** | `/api/v1/asaas/subscriptions` |
| **Products** | `/api/v1/asaas/products` |
| **Dashboard** | `/api/v1/asaas/dashboard` |
| **Webhooks** | `/api/v1/webhooks/asaas` |

---

## 6. Integração com Asaas

### 6.1 Fluxo de Integração

```
┌─────────────────────────────────────────────────────┐
│  1. Frontend chama endpoint da API                  │
│     POST /api/v1/payments                           │
│                                                      │
│  2. API valida dados e autenticação                 │
│                                                      │
│  3. API envia requisição para Asaas                 │
│     POST /v3/payments                               │
│                                                      │
│  4. Asaas retorna dados da cobrança                 │
│                                                      │
│  5. API salva no banco local (PostgreSQL)           │
│                                                      │
│  6. API invalida cache (Upstash Redis)              │
│                                                      │
│  7. Retorna resposta ao frontend                    │
│                                                      │
│  8. Webhook externo atualiza status posteriormente  │
└─────────────────────────────────────────────────────┘
```

### 6.2 Endpoints Asaas Utilizados

**Customers (Clientes)**
```
GET    /v3/customers
POST   /v3/customers
GET    /v3/customers/{id}
PUT    /v3/customers/{id}
DELETE /v3/customers/{id}
```

**Payments (Cobranças)**
```
GET    /v3/payments
POST   /v3/payments
GET    /v3/payments/{id}
PUT    /v3/payments/{id}
DELETE /v3/payments/{id}
```

**Subscriptions (Assinaturas)**
```
GET    /v3/subscriptions
POST   /v3/subscriptions
GET    /v3/subscriptions/{id}
PUT    /v3/subscriptions/{id}
DELETE /v3/subscriptions/{id}
```

**Payment Links (Links de Pagamento)**
```
GET    /v3/paymentLinks
POST   /v3/paymentLinks
GET    /v3/paymentLinks/{id}
PUT    /v3/paymentLinks/{id}
DELETE /v3/paymentLinks/{id}
```

### 6.3 Autenticação Asaas

```python
import os
import httpx
from typing import Optional

ASAAS_API_KEY = os.getenv("ASAAS_API_KEY")
ASAAS_SANDBOX = os.getenv("ASAAS_SANDBOX", "false").lower() == "true"

ASAAS_BASE_URL = (
    "https://sandbox.asaas.com/api/v3" 
    if ASAAS_SANDBOX 
    else "https://api.asaas.com/v3"
)

def get_asaas_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "access_token": ASAAS_API_KEY
    }

async def asaas_request(
    method: str, 
    endpoint: str, 
    data: Optional[dict] = None
) -> dict:
    """Faz requisição para a API do Asaas"""
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=method,
            url=f"{ASAAS_BASE_URL}{endpoint}",
            headers=get_asaas_headers(),
            json=data
        )
        response.raise_for_status()
        return response.json()
```

### 6.4 Status de Pagamento

| Status Asaas | Status ecosys | Descrição |
|--------------|---------------|-----------|
| `PENDING` | Pendente | Aguardando pagamento |
| `RECEIVED` | Pago | Pagamento confirmado |
| `CONFIRMED` | Confirmado | Em análise (PIX) |
| `OVERDUE` | Vencido | Pagamento não realizado |
| `REFUNDED` | Estornado | Pagamento devolvido |
| `RECEIVED_IN_CASH` | Pago em Dinheiro | Pago fora do sistema |
| `REFUND_REQUESTED` | Estorno Solicitado | Aguardando estorno |
| `CHARGEBACK_REQUESTED` | Contestado | Cliente contestou |
| `CHARGEBACK_DISPUTE` | Em Disputa | Disputa em andamento |
| `AWAITING_CHARGEBACK_REVERSAL` | Aguardando Reversão | - |

### 6.5 Webhooks (Gerenciado Externamente)

**Nota:** O sistema de webhooks do Asaas é gerenciado por outra aplicação.

A API receberá eventos via endpoint interno:

```python
from pydantic import BaseModel
from typing import Literal
from datetime import datetime

class PaymentEvent(BaseModel):
    event: Literal[
        'PAYMENT_CREATED', 
        'PAYMENT_UPDATED',
        'PAYMENT_CONFIRMED', 
        'PAYMENT_RECEIVED',
        'PAYMENT_OVERDUE', 
        'PAYMENT_REFUNDED'
    ]
    payment: dict  # Dados do pagamento do Asaas
    received_at: datetime
```

**Endpoint interno:**
```
POST /api/v1/webhooks/asaas  # Recebe eventos do sistema externo
```

---

## 7. Especificações Técnicas

### 7.1 Stack Tecnológica

```txt
# requirements.txt (adicionar às dependências existentes)
pydantic>=2.0
pandas
fastapi
upstash-redis
psycopg2-binary
python-dotenv
requests
httpx
uvicorn
python-multipart           # Form data
```

### 7.2 Estrutura Simplificada (Integração com Projeto Atual)

```
ecosysMS-Back/
├── api/
│   ├── main.py                    # FastAPI app (existente)
│   │
│   ├── lib/
│   │   ├── db_connection.py       # ✅ REUTILIZAR (existente)
│   │   ├── models.py              # ✅ REUTILIZAR + estender (existente)
│   │   ├── clientes_queries.py    # ✅ REUTILIZAR (existente)
│   │   ├── pagamentos_queries.py  # ✅ REUTILIZAR + estender (existente)
│   │   │
│   │   └── asaas_client.py        # 🆕 NOVO - Cliente HTTP Asaas simples
│   │
│   └── scripts/
│       ├── clientes.py            # ✅ REUTILIZAR (existente)
│       ├── dashboard.py           # ✅ REUTILIZAR (existente)
│       ├── vendas.py              # ✅ REUTILIZAR (existente)
│       │
│       └── payments.py            # 🆕 NOVO - Endpoints de pagamentos Asaas
│
├── vercel.json                    # Deploy config (existente)
├── requirements.txt               # Dependências (existente)
└── README.md
```

### 7.3 Configuração de Cache (Upstash Redis)

```python
from upstash_redis import Redis
import os
import json
from functools import wraps
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)

# Inicializar cliente Redis
redis = Redis(
    url=os.getenv("UPSTASH_REDIS_URL"),
    token=os.getenv("UPSTASH_REDIS_TOKEN")
)

class CacheConfig:
    """Configurações de TTL para cache"""
    CUSTOMERS = 60 * 60 * 24       # 24 horas
    PAYMENTS = 60 * 60             # 1 hora
    SUBSCRIPTIONS = 60 * 60 * 12   # 12 horas
    PRODUCTS = 60 * 60 * 24        # 24 horas
    DASHBOARD = 60 * 60            # 1 hora

def cached(prefix: str, ttl: int):
    """Decorator para cache de funções"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{prefix}:{hash(str(args) + str(kwargs))}"
            
            # Tentar obter do cache
            cached_value = redis.get(cache_key)
            if cached_value:
                return json.loads(cached_value)
            
            # Executar função e cachear
            result = await func(*args, **kwargs)
            redis.setex(cache_key, ttl, json.dumps(result))
            
            return result
        return wrapper
    return decorator
```

### 7.4 Segurança

**Autenticação:**
- Gerenciada pelo frontend/aplicação principal
- API confia em headers/tokens validados externamente

**Proteção:**
- HTTPS obrigatório (via Vercel)
- CORS configurado (já existente no projeto)
- Rate limiting
- Validação de dados com Pydantic
- Sanitização de inputs

**Compliance:**
- LGPD (Lei Geral de Proteção de Dados)
- PCI DSS (via Asaas)

---

## 8. Modelos de Dados

### 8.1 Reutilização de Estrutura Existente

**Tabelas Existentes (Reutilizar):**
- ✅ `clientes_atual` / `clientes_kommo` - Base de clientes
- ✅ `companies_kommo` - Empresas com CNPJ
- ✅ `historico_pagamentos` - Histórico de pagamentos

**Novas Tabelas (Criar via Supabase Dashboard):**

#### Tabela: `asaas_customers`
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | UUID (PK) | ID único |
| asaas_id | VARCHAR UNIQUE | ID no Asaas |
| name | VARCHAR | Nome/Razão Social |
| email | VARCHAR UNIQUE | Email |
| cpf_cnpj | VARCHAR UNIQUE | CPF ou CNPJ |
| phone | VARCHAR | Telefone |
| address | JSONB | Endereço completo |
| active | BOOLEAN | Status ativo |
| created_at | TIMESTAMP | Data de criação |
| updated_at | TIMESTAMP | Data de atualização |

#### Tabela: `asaas_products`
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | UUID (PK) | ID único |
| name | VARCHAR | Nome do produto |
| price | DECIMAL(10,2) | Preço |
| cycle | VARCHAR | MONTHLY, QUARTERLY, YEARLY |
| active | BOOLEAN | Status ativo |
| created_at | TIMESTAMP | Data de criação |

#### Tabela: `asaas_payments`
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | UUID (PK) | ID único |
| asaas_id | VARCHAR UNIQUE | ID no Asaas |
| cliente_id | INTEGER | FK para clientes_atual |
| value | DECIMAL(10,2) | Valor |
| status | VARCHAR | Status do pagamento |
| due_date | DATE | Data de vencimento |
| payment_date | TIMESTAMP | Data do pagamento |
| invoice_url | VARCHAR | URL da fatura |
| created_at | TIMESTAMP | Data de criação |

#### Tabela: `asaas_subscriptions`
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | UUID (PK) | ID único |
| asaas_id | VARCHAR UNIQUE | ID no Asaas |
| cliente_id | INTEGER | FK para clientes_atual |
| product_id | UUID | FK para asaas_products |
| value | DECIMAL(10,2) | Valor |
| cycle | VARCHAR | MONTHLY, QUARTERLY, YEARLY |
| status | VARCHAR | ACTIVE, INACTIVE |
| next_due_date | DATE | Próximo vencimento |
| created_at | TIMESTAMP | Data de criação |

### 8.2 Modelos Pydantic (Estender os Existentes)

**Reutilizar de `api/lib/models.py`:**
- ✅ `Cliente` - Modelo de cliente já existente

**Novos modelos para Asaas:**

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from decimal import Decimal
from enum import Enum

# ============================================================================
# ENUMS
# ============================================================================

class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
    CONFIRMED = "CONFIRMED"
    OVERDUE = "OVERDUE"
    REFUNDED = "REFUNDED"

class BillingType(str, Enum):
    BOLETO = "BOLETO"
    CREDIT_CARD = "CREDIT_CARD"
    PIX = "PIX"
    UNDEFINED = "UNDEFINED"

class SubscriptionCycle(str, Enum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"
    ONE_TIME = "ONE_TIME"

class SubscriptionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    EXPIRED = "EXPIRED"

# ============================================================================
# CUSTOMER MODELS
# ============================================================================

class Address(BaseModel):
    street: Optional[str] = None
    number: Optional[str] = None
    complement: Optional[str] = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None

class CustomerBase(BaseModel):
    name: str
    email: EmailStr
    cpf_cnpj: str
    phone: Optional[str] = None
    address: Optional[Address] = None

class CustomerCreate(CustomerBase):
    pass

class Customer(CustomerBase):
    id: str
    asaas_id: str
    active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# PRODUCT MODELS
# ============================================================================

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Decimal
    billing_type: BillingType = BillingType.UNDEFINED
    cycle: Optional[SubscriptionCycle] = None
    installments: int = 1
    features: Optional[List[str]] = None
    metadata: Optional[dict] = None

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: str
    active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# PAYMENT MODELS
# ============================================================================

class PaymentBase(BaseModel):
    customer_id: str
    product_id: Optional[str] = None
    value: Decimal
    billing_type: BillingType
    due_date: date
    description: Optional[str] = None

class PaymentCreate(PaymentBase):
    pass

class Payment(PaymentBase):
    id: str
    asaas_id: str
    status: PaymentStatus = PaymentStatus.PENDING
    payment_date: Optional[datetime] = None
    invoice_url: Optional[str] = None
    bank_slip_url: Optional[str] = None
    pix_qr_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# SUBSCRIPTION MODELS
# ============================================================================

class SubscriptionBase(BaseModel):
    customer_id: str
    product_id: str
    value: Decimal
    cycle: SubscriptionCycle

class SubscriptionCreate(SubscriptionBase):
    billing_type: BillingType = BillingType.CREDIT_CARD

class Subscription(SubscriptionBase):
    id: str
    asaas_id: str
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    next_due_date: date
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# DASHBOARD MODELS
# ============================================================================

class DashboardMetrics(BaseModel):
    mrr: Decimal
    total_customers: int
    active_subscriptions: int
    pending_payments: int
    overdue_payments: int
    churn_rate: float
    revenue_this_month: Decimal
    revenue_last_month: Decimal
```

---

## 9. Fluxos do Sistema

### 9.1 Fluxo de Criação de Cobrança

```
┌──────────────────────────────────────────────────┐
│ 1. Frontend chama POST /api/v1/payments          │
│    com dados do cliente e produto                │
│                                                   │
│ 2. API valida dados com Pydantic                 │
│                                                   │
│ 4. API verifica se cliente existe no banco       │
│    - Se não existe, cria no Asaas primeiro       │
│                                                   │
│ 5. API chama Asaas: POST /v3/payments            │
│                                                   │
│ 6. Asaas retorna dados da cobrança + link        │
│                                                   │
│ 7. API salva transação no PostgreSQL             │
│                                                   │
│ 8. API invalida cache relacionado (Redis)        │
│                                                   │
│ 9. API retorna resposta com link de pagamento    │
└──────────────────────────────────────────────────┘
```

### 9.2 Fluxo de Criação de Cliente

```
┌──────────────────────────────────────────────────┐
│ 1. Frontend chama POST /api/v1/customers         │
│    com dados do cliente                          │
│                                                   │
│ 2. API valida CPF/CNPJ                           │
│                                                   │
│ 4. API verifica duplicidade no banco             │
│                                                   │
│ 5. API chama Asaas: POST /v3/customers           │
│                                                   │
│ 6. Asaas retorna ID do cliente                   │
│                                                   │
│ 7. API salva cliente com asaas_id no PostgreSQL  │
│                                                   │
│ 8. API invalida cache de clientes                │
│                                                   │
│ 9. API retorna cliente criado                    │
└──────────────────────────────────────────────────┘
```

### 9.3 Fluxo de Criação de Assinatura

```
┌──────────────────────────────────────────────────┐
│ 1. Frontend chama POST /api/v1/subscriptions     │
│                                                   │
│ 2. API valida produto e cliente existentes       │
│                                                   │
│ 4. API monta payload para Asaas                  │
│    - customer: asaas_id do cliente               │
│    - value: valor do produto                     │
│    - cycle: MONTHLY, QUARTERLY, YEARLY           │
│    - billingType: forma de pagamento             │
│                                                   │
│ 5. API chama Asaas: POST /v3/subscriptions       │
│                                                   │
│ 6. Asaas retorna dados da assinatura             │
│                                                   │
│ 7. API salva assinatura no PostgreSQL            │
│                                                   │
│ 8. API invalida caches relacionados              │
│                                                   │
│ 9. API retorna assinatura criada                 │
└──────────────────────────────────────────────────┘
```

### 9.4 Fluxo de Recebimento de Webhook

```
┌──────────────────────────────────────────────────┐
│ 1. Sistema externo chama                         │
│    POST /api/v1/webhooks/asaas                   │
│    com evento do Asaas                           │
│                                                   │
│ 2. API valida origem da requisição               │
│                                                   │
│ 3. API identifica tipo de evento:                │
│    - PAYMENT_RECEIVED → Atualiza status          │
│    - PAYMENT_OVERDUE → Marca como vencido        │
│    - PAYMENT_REFUNDED → Marca como estornado     │
│                                                   │
│ 4. API busca transação pelo asaas_id             │
│                                                   │
│ 5. API atualiza status no PostgreSQL             │
│                                                   │
│ 6. API invalida caches relacionados              │
│                                                   │
│ 7. API retorna 200 OK                            │
└──────────────────────────────────────────────────┘
```

---

## 10. Roadmap Simplificado (4 Semanas)

### 10.1 Semana 1 - Setup e Cliente Asaas

**Tarefas:**
- [ ] Criar `api/lib/asaas_client.py` (cliente HTTP simples)
- [ ] Criar tabelas no Supabase (`asaas_customers`, `asaas_payments`, `asaas_subscriptions`)
- [ ] Adicionar `httpx` ao requirements.txt
- [ ] Testar conexão com Asaas sandbox

**Entregável:** Cliente Asaas funcionando

---

### 10.2 Semana 2 - Integração de Clientes

**Tarefas:**
- [ ] Endpoint: POST `/api/v1/asaas/customers` (criar no Asaas)
- [ ] Endpoint: GET `/api/v1/asaas/customers/{id}` (consultar)
- [ ] Sincronizar `clientes_atual` → Asaas
- [ ] Salvar mapeamento em `asaas_customers`

**Entregável:** Clientes sincronizados com Asaas

---

### 10.3 Semana 3 - Pagamentos e Assinaturas

**Tarefas:**
- [ ] Endpoint: POST `/api/v1/asaas/payments` (criar cobrança)
- [ ] Endpoint: GET `/api/v1/asaas/payments` (listar)
- [ ] Endpoint: POST `/api/v1/asaas/subscriptions` (criar assinatura)
- [ ] Endpoint: GET `/api/v1/asaas/subscriptions` (listar)
- [ ] Salvar dados em `asaas_payments` e `asaas_subscriptions`

**Entregável:** CRUD de pagamentos e assinaturas

---

### 10.4 Semana 4 - Dashboard e Webhooks

**Tarefas:**
- [ ] Endpoint: GET `/api/v1/asaas/dashboard` (MRR, total clientes)
- [ ] Endpoint: POST `/api/v1/webhooks/asaas` (receber eventos)
- [ ] Atualizar status de pagamentos via webhook
- [ ] Integrar com `scripts/dashboard.py` existente

**Entregável:** Sistema completo em produção

---

### Roadmap Visual

```
Semana 1        Semana 2         Semana 3         Semana 4
│               │                │                │
├─ Setup        ├─ Clientes      ├─ Payments      ├─ Dashboard
│  Asaas        │  Sync Asaas    │  Subscriptions │  Webhooks
│  Tabelas      │                │                │
▼               ▼                ▼                ▼
Infra           Integração       Core Features    Go Live
```

---

## 11. Métricas de Sucesso

### 11.1 KPIs Técnicos

**Performance da API:**
- [ ] **Uptime:** > 99.5%
- [ ] **Tempo de Resposta:** < 500ms (p95)
- [ ] **Taxa de Erro:** < 1%
- [ ] **Cache Hit Rate:** > 80%

**Integração Asaas:**
- [ ] **Sincronização:** 100% dos clientes sincronizados
- [ ] **Webhooks Processados:** 100% sem falhas
- [ ] **Latência Asaas:** Monitoramento ativo

### 11.2 KPIs de Negócio

**Pagamentos:**
- [ ] **Taxa de Conversão:** > 60% dos checkouts pagos
- [ ] **MRR:** Visível e crescente
- [ ] **Churn Rate:** < 5% ao mês
- [ ] **Redução de Inadimplência:** -15%

### 11.3 Métricas por Endpoint

```python
# Exemplo de métricas a serem coletadas
METRICS = {
    "payments": {
        "created_per_day": 0,
        "success_rate": 0.0,
        "avg_response_time_ms": 0,
    },
    "customers": {
        "total_active": 0,
        "created_per_day": 0,
        "sync_errors": 0,
    },
    "subscriptions": {
        "total_active": 0,
        "mrr_total": 0.0,
        "churn_rate": 0.0,
    }
}
```

---

## 12. Riscos e Mitigações

### 12.1 Riscos Técnicos

#### **RISCO 1: Instabilidade da API Asaas**
**Probabilidade:** Média  
**Impacto:** Alto  
**Mitigação:**
- Implementar retry logic com exponential backoff
- Cache de dados não-críticos no Upstash Redis
- Circuit breaker pattern
- Monitoramento ativo da API
- Logs detalhados de falhas

```python
# Exemplo de retry logic
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def asaas_request_with_retry(method: str, endpoint: str, data: dict = None):
    async with httpx.AsyncClient() as client:
        response = await client.request(method, f"{ASAAS_BASE_URL}{endpoint}", json=data)
        response.raise_for_status()
        return response.json()
```

#### **RISCO 2: Performance em Serverless**
**Probabilidade:** Média  
**Impacto:** Médio  
**Mitigação:**
- Cache agressivo com Upstash Redis
- Connection pooling para PostgreSQL
- Otimização de cold starts
- Queries otimizadas

#### **RISCO 3: Segurança de Dados**
**Probabilidade:** Baixa  
**Impacto:** Crítico  
**Mitigação:**
- API acessível apenas internamente (não pública)
- Rate limiting por IP
- Validação rigorosa com Pydantic
- HTTPS via Vercel
- CORS restrito

---

### 12.2 Riscos de Integração

#### **RISCO 4: Mudanças na API do Asaas**
**Probabilidade:** Baixa  
**Impacto:** Médio  
**Mitigação:**
- Camada de abstração (api/lib/asaas/)
- Versionamento do cliente HTTP
- Monitorar changelog do Asaas
- Testes de integração automatizados

#### **RISCO 5: Falha na Sincronização**
**Probabilidade:** Média  
**Impacto:** Alto  
**Mitigação:**
- Retry automático em falhas
- Fila de sincronização pendente
- Logs detalhados
- Alertas em falhas críticas

---

### 12.3 Matriz de Riscos

| # | Risco | Probabilidade | Impacto | Prioridade | Mitigação |
|---|-------|---------------|---------|------------|-----------|
| 1 | Instabilidade API Asaas | Média | Alto | 🔴 Alta | Retry + Cache |
| 2 | Performance Serverless | Média | Médio | 🟡 Média | Cache + Pool |
| 3 | Segurança | Baixa | Crítico | 🔴 Alta | JWT + Rate Limit |
| 4 | Mudanças API | Baixa | Médio | 🟡 Média | Abstração |
| 5 | Falha Sincronização | Média | Alto | 🔴 Alta | Retry + Queue |

---

## 13. Anexos

### 13.1 Glossário

- **Asaas:** Gateway de pagamento brasileiro
- **Checkout:** Link/cobrança de pagamento gerado
- **MRR:** Monthly Recurring Revenue (Receita Recorrente Mensal)
- **Churn:** Taxa de cancelamento de clientes
- **LGPD:** Lei Geral de Proteção de Dados

### 13.2 Variáveis de Ambiente

```bash
# Adicionar ao .env
# Asaas
ASAAS_API_KEY=your_api_key_here
ASAAS_SANDBOX=true  # false para produção

# Database (já existentes)
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=your_db_host
DB_PORT=5432

# Redis (já existentes)
UPSTASH_REDIS_URL=your_redis_url
UPSTASH_REDIS_TOKEN=your_redis_token
```

### 13.3 Referências

- [Documentação Asaas API](https://docs.asaas.com/reference/comece-por-aqui)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Pydantic Documentation](https://docs.pydantic.dev)
- [Upstash Redis](https://upstash.com/docs/redis/overall/getstarted)
- [Vercel Python Runtime](https://vercel.com/docs/functions/runtimes/python)

---

## 14. Conclusão

O **ecosys Payments API** é uma extensão do backend existente (ecosysMS-Back) para gestão de pagamentos. Utilizando a mesma stack (FastAPI, PostgreSQL, Upstash Redis, Vercel), o módulo será integrado ao projeto atual mantendo consistência e reaproveitando infraestrutura.

**Principais entregas:**

✅ **API RESTful:** Endpoints padronizados para pagamentos, clientes e assinaturas  
✅ **Integração Asaas:** Sincronização completa com gateway de pagamento  
✅ **Cache Eficiente:** Upstash Redis para performance otimizada  
✅ **Validação Robusta:** Pydantic para validação de dados  
✅ **Escalabilidade:** Serverless na Vercel, pronto para crescimento  

Com um roadmap de 8 semanas e integração ao projeto existente, o módulo de pagamentos estará operacional rapidamente.

---

**Documento aprovado para desenvolvimento**  
**Versão:** 2.0  
**Data:** 02 de Janeiro de 2026  
**Próximos Passos:** Iniciar Fase 1 - Fundação