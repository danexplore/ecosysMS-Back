# 📊 API de Vendas - Documentação Completa

## Visão Geral

A API de Vendas fornece endpoints para gerenciamento de vendedores, clientes, comissões e métricas de performance.

**Base URL:** `/vendas`

**Autenticação:** Todos os endpoints requerem **Basic Auth**

---

## 📋 Índice

1. [Vendedores](#vendedores)
2. [Clientes](#clientes)
3. [Comissões](#comissões)
4. [Dashboard e Métricas](#dashboard-e-métricas)
5. [Configuração](#configuração)
6. [Cache](#cache)

---

## 🔐 Autenticação

Todos os endpoints requerem autenticação Basic Auth:

```bash
curl -u "usuario:senha" https://api.exemplo.com/vendas/...
```

---

## 📅 Parâmetro de Filtro por Mês

A maioria dos endpoints suporta o parâmetro `month` para filtrar por período:

| Parâmetro | Formato | Descrição |
|-----------|---------|-----------|
| `month` | `YYYY-MM` | Filtra dados **até** o final do mês especificado |

**Exemplo:** `?month=2024-12` retorna dados até 31/12/2024

**Comportamento:**
- **Sem filtro:** Retorna estado atual de todos os dados
- **Com filtro:** Retorna evolução histórica até aquele mês

---

## Vendedores

### GET `/vendas/vendedores`

Lista todos os vendedores ativos.

**Response:**
```json
[
  {
    "id": 12476067,
    "name": "Amanda Klava",
    "email": "amanda.klava@ecosysauto.com.br"
  },
  {
    "id": 13734187,
    "name": "Eduarda Oliveira",
    "email": "eduarda@ecosys.com.br"
  }
]
```

---

## Clientes

### GET `/vendas/clientes`

Retorna todos os clientes para cálculo de comissão (valor > 0).

**Query Parameters:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `month` | string | ❌ | Mês de referência (YYYY-MM) |

**Response:**
```json
[
  {
    "id": "123",
    "clientName": "Empresa ABC",
    "mrr": 299.90,
    "setupValue": 500.00,
    "date": "2024-01-15",
    "status": "ativo",
    "sellerId": "12476067",
    "sellerName": "Amanda Klava",
    "canceledAt": null,
    "month": "2024-01",
    "mesesAtivo": 11,
    "parcelasAtrasadas": 0,
    "mesesComissao": 11,
    "percentualComissao": 0.0,
    "valorComissao": 0.0
  }
]
```

**Campos:**
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | string | ID único do cliente |
| `clientName` | string | Nome do cliente |
| `mrr` | float | Valor mensal recorrente |
| `setupValue` | float | Valor do setup |
| `date` | string | Data de adesão |
| `status` | string | `ativo`, `inadimplente` ou `cancelado` |
| `sellerId` | string | ID do vendedor |
| `sellerName` | string | Nome do vendedor |
| `canceledAt` | string | Data de cancelamento (se houver) |
| `month` | string | Mês de adesão (YYYY-MM) |
| `mesesAtivo` | int | Quantidade de meses ativo |
| `parcelasAtrasadas` | int | Parcelas em atraso |
| `mesesComissao` | int | Meses para comissão (mesesAtivo - parcelasAtrasadas) |
| `percentualComissao` | float | % de comissão recorrente |
| `valorComissao` | float | Valor da comissão calculado |

---

### GET `/vendas/clientes/vendedor/{vendedor_id}`

Retorna clientes de um vendedor específico.

**Path Parameters:**
| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `vendedor_id` | int | ID do vendedor (use `99999999` para Vendas Antigas) |

**Query Parameters:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `month` | string | ❌ | Mês de referência (YYYY-MM) |

**Exemplo:**
```
GET /vendas/clientes/vendedor/12476067?month=2024-12
```

---

### GET `/vendas/clientes/inadimplentes`

Retorna clientes com status financeiro inadimplente.

**Query Parameters:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `month` | string | ❌ | Mês de referência (YYYY-MM) |

**Response:** Mesma estrutura de `/vendas/clientes`, filtrado por `status: "inadimplente"`

---

### GET `/vendas/clientes/novos`

Retorna novos clientes (adesões) do mês.

**Query Parameters:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `month` | string | ❌ | Mês de referência (YYYY-MM). Default: mês atual |

**Comportamento:**
- Retorna clientes que aderiram **até** o mês especificado
- Usado para análise de evolução histórica

---

### GET `/vendas/clientes/churns`

Retorna cancelamentos (churns) do mês.

**Query Parameters:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `month` | string | ❌ | Mês de referência (YYYY-MM). Default: mês atual |

**Response:**
```json
[
  {
    "id": "456",
    "clientName": "Empresa XYZ",
    "mrr": 199.90,
    "status": "cancelado",
    "canceledAt": "2024-12-03"
  }
]
```

---

## Comissões

### GET `/vendas/resumo-comissoes`

Retorna resumo de comissões agrupado por vendedor, incluindo **gamificação (tiers)**.

**Query Parameters:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `month` | string | ❌ | Mês de referência (YYYY-MM) |

**Response:**
```json
[
  {
    "vendedor": {
      "id": 12476067,
      "name": "Amanda Klava",
      "email": "amanda.klava@ecosysauto.com.br"
    },
    "totalClientes": 59,
    "clientesAtivos": 15,
    "clientesInadimplentes": 19,
    "clientesCancelados": 25,
    "mrrAtivo": 6085.00,
    "setupTotal": 0.00,
    "comissaoTotal": 1566.10,
    "novosMes": 3,
    "tier": "bronze",
    "percentualMrr": 5.0,
    "percentualSetup": 15.0
  }
]
```

**Campos:**
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `vendedor` | object | Dados do vendedor |
| `totalClientes` | int | Total de clientes do vendedor |
| `clientesAtivos` | int | Clientes ativos |
| `clientesInadimplentes` | int | Clientes inadimplentes |
| `clientesCancelados` | int | Clientes cancelados |
| `mrrAtivo` | float | MRR total dos clientes ativos |
| `setupTotal` | float | Setup total dos clientes ativos |
| `comissaoTotal` | float | Comissão total calculada |
| `novosMes` | int | **Vendas do mês** (novos clientes) |
| `tier` | string | **Tier de gamificação**: `bronze`, `prata` ou `ouro` |
| `percentualMrr` | float | **% de comissão MRR** baseado no tier |
| `percentualSetup` | float | **% de comissão Setup** baseado no tier |

---

### GET `/vendas/ranking`

Retorna ranking de vendedores ordenado por MRR ativo.

**Query Parameters:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `month` | string | ❌ | Mês de referência (YYYY-MM) |

**Response:**
```json
[
  {
    "vendedor": {
      "id": 12476067,
      "name": "Amanda Klava",
      "email": "amanda.klava@ecosysauto.com.br"
    },
    "mrrAtivo": 15000.00,
    "clientesAtivos": 50,
    "novosMes": 8,
    "posicao": 1,
    "comissaoTotal": 3500.00,
    "tier": "prata",
    "percentualMrr": 10.0,
    "percentualSetup": 25.0
  }
]
```

**Ordenação:** Por `mrrAtivo` decrescente

---

## Dashboard e Métricas

### GET `/vendas/dashboard`

Retorna métricas gerais consolidadas.

**Query Parameters:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `month` | string | ❌ | Mês de referência (YYYY-MM) |

**Response:**
```json
{
  "totalClientes": 200,
  "clientesAtivos": 180,
  "clientesInadimplentes": 10,
  "clientesCancelados": 10,
  "mrrTotal": 54000.00,
  "ltvTotal": 0,
  "avgMesesAtivo": 8.5,
  "novosMesAtual": 15,
  "churnsMesAtual": 3,
  "ticketMedio": 300.00,
  "comissaoTotal": 12500.00
}
```

**Campos:**
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `totalClientes` | int | Total de clientes |
| `clientesAtivos` | int | Clientes ativos |
| `clientesInadimplentes` | int | Clientes inadimplentes |
| `clientesCancelados` | int | Clientes cancelados |
| `mrrTotal` | float | MRR total dos ativos |
| `ltvTotal` | float | LTV total (setup quando filtrado por mês) |
| `avgMesesAtivo` | float | Média de meses ativo |
| `novosMesAtual` | int | Novos clientes no mês |
| `churnsMesAtual` | int | Churns no mês |
| `ticketMedio` | float | Ticket médio (MRR / ativos) |
| `comissaoTotal` | float | Total de comissões a pagar |

---

## Configuração

### GET `/vendas/commission-config`

Retorna a configuração atual de comissões e gamificação.

**Response:**
```json
{
  "id": 1,
  "sales_goal": 10,
  "mrr_tier1": 5.0,
  "mrr_tier2": 10.0,
  "mrr_tier3": 20.0,
  "setup_tier1": 15.0,
  "setup_tier2": 25.0,
  "setup_tier3": 40.0,
  "mrr_recurrence": [30.0, 20.0, 10.0, 10.0, 10.0, 10.0, 10.0],
  "updated_at": "2024-12-09T10:00:00"
}
```

**Campos:**
| Campo | Tipo | Descrição |
|-------|------|-----------|
| `sales_goal` | int | Meta de vendas para tier ouro |
| `mrr_tier1` | float | % MRR para tier bronze (1-5 vendas) |
| `mrr_tier2` | float | % MRR para tier prata (6-9 vendas) |
| `mrr_tier3` | float | % MRR para tier ouro (10+ vendas) |
| `setup_tier1` | float | % Setup para tier bronze |
| `setup_tier2` | float | % Setup para tier prata |
| `setup_tier3` | float | % Setup para tier ouro |
| `mrr_recurrence` | array | Array de % de comissão recorrente por mês |

---

### PUT `/vendas/commission-config`

Atualiza a configuração de comissões. **Apenas campos fornecidos serão atualizados.**

**Request Body:**
```json
{
  "sales_goal": 12,
  "mrr_tier3": 25.0,
  "mrr_recurrence": [35.0, 25.0, 15.0, 10.0, 10.0, 10.0, 10.0]
}
```

**Validações:**
| Campo | Regra |
|-------|-------|
| `sales_goal` | >= 1 |
| `mrr_tier*` | 0-100 |
| `setup_tier*` | 0-100 |
| `mrr_recurrence` | array de floats |

**Response:** Configuração completa atualizada (mesma estrutura do GET)

**Exemplo:**
```bash
curl -X PUT "https://api.exemplo.com/vendas/commission-config" \
  -u "usuario:senha" \
  -H "Content-Type: application/json" \
  -d '{"sales_goal": 15}'
```

---

## Cache

### POST `/vendas/cache/clear`

Limpa o cache de vendas e configurações.

**Response:**
```json
{
  "status": "success",
  "message": "Cache de vendas e configuração de comissões limpo com sucesso",
  "keys_deleted": 25
}
```

---

## 🏅 Sistema de Gamificação (Tiers)

O tier é calculado com base nas **vendas do mês** (novos clientes):

| Vendas no Mês | Tier | % MRR | % Setup |
|---------------|------|-------|---------|
| 0 - 5 | 🥉 **Bronze** | 5% | 15% |
| 6 - 9 | 🥈 **Prata** | 10% | 25% |
| 10+ | 🥇 **Ouro** | 20% | 40% |

**Nota:** Os valores são configuráveis via `/vendas/commission-config`

---

## 💰 Cálculo de Comissão Recorrente

A comissão recorrente é calculada assim:

1. **mesesComissao** = `mesesAtivo - parcelasAtrasadas` (mínimo 0)
2. **percentual** = `mrr_recurrence[mesesComissao - 1]` (do array de configuração)
3. **valorComissao** = `mrr * percentual / 100`

**Tabela de Recorrência (padrão):**
| Mês | % Comissão |
|-----|------------|
| 1º | 30% |
| 2º | 20% |
| 3º | 10% |
| 4º | 10% |
| 5º | 10% |
| 6º | 10% |
| 7º+ | 10% |
| 8º+ | 0% |

---

## 🔄 Códigos de Status HTTP

| Código | Descrição |
|--------|-----------|
| 200 | Sucesso |
| 401 | Não autorizado (Basic Auth inválido) |
| 500 | Erro interno do servidor |

---

## 📝 Exemplos de Uso

### Buscar resumo do mês atual
```bash
curl -u "user:pass" "https://api.exemplo.com/vendas/resumo-comissoes"
```

### Buscar evolução até junho/2024
```bash
curl -u "user:pass" "https://api.exemplo.com/vendas/resumo-comissoes?month=2024-06"
```

### Buscar clientes de um vendedor específico
```bash
curl -u "user:pass" "https://api.exemplo.com/vendas/clientes/vendedor/12476067?month=2024-12"
```

### Atualizar meta de vendas
```bash
curl -X PUT "https://api.exemplo.com/vendas/commission-config" \
  -u "user:pass" \
  -H "Content-Type: application/json" \
  -d '{"sales_goal": 15}'
```

### Limpar cache
```bash
curl -X POST "https://api.exemplo.com/vendas/cache/clear" -u "user:pass"
```
