# 📚 Documentação de Endpoints - EcosysMS API

> **Versão:** 2.0.0  
> **Base URL:** `https://your-api-url.com`  
> **Autenticação:** HTTP Basic Auth (exceto endpoints públicos)

---

## 📋 Índice

- [Endpoints Públicos](#-endpoints-públicos)
- [Clientes](#-clientes)
- [Health Scores](#-health-scores)
- [Dashboard](#-dashboard)
- [Logins](#-logins)
- [Credere](#-credere)
- [Vendas e Comissões](#-vendas-e-comissões)
- [Cache](#-cache)

---

## 🌐 Endpoints Públicos

### `GET /`
**Descrição:** Endpoint raiz da API

**Response:**
```json
{
    "message": "EcosysMS API",
    "version": "2.0.0",
    "status": "online",
    "docs": "/docs"
}
```

---

### `GET /health`
**Descrição:** Health check detalhado da aplicação

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2024-12-09T10:30:00.000Z",
    "environment": "production",
    "redis": "connected",
    "workers": 8,
    "version": "2.0.0"
}
```

---

## 👥 Clientes

### `GET /clientes`
**Descrição:** Retorna lista de clientes com filtros opcionais

**🔒 Autenticação:** Basic Auth

**Query Parameters:**
| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `data_inicio` | string | Data inicial (YYYY-MM-DD) |
| `data_fim` | string | Data final (YYYY-MM-DD) |

**Response:**
```json
{
    "123": {
        "client_id": 123,
        "nome": "Empresa ABC Ltda",
        "vendedor": "Amanda Klava",
        "valor": 299.90,
        "status": "ativo",
        "pipeline": "Clientes Ativos",
        "data_adesao": "2024-01-15",
        "data_cancelamento": null,
        "meses_ativo": 11
    }
}
```

---

### `GET /clientes/evolution`
**Descrição:** Retorna evolução mensal de clientes (novos, churns, ativos)

**🔒 Autenticação:** Basic Auth

**Query Parameters:**
| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `data_inicio` | string | Data inicial (YYYY-MM-DD) |
| `data_fim` | string | Data final (YYYY-MM-DD) |

**Response:**
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
    }
]
```

---

### `GET /clientes/data-atualizacao-inadimplentes`
**Descrição:** Retorna data da última atualização de inadimplentes

**🔒 Autenticação:** Basic Auth

**Response:**
```json
{
    "data_atualizacao": "2024-12-09T08:00:00.000Z"
}
```

---

## 📊 Health Scores

### `GET /health-scores`
**Descrição:** Retorna health scores dos clientes baseados em 4 pilares

**🔒 Autenticação:** Basic Auth

**Query Parameters:**
| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `data_inicio` | string | Data inicial (YYYY-MM-DD) |
| `data_fim` | string | Data final (YYYY-MM-DD) |

**Response:**
```json
{
    "123": {
        "tenant_id": 123,
        "client_id": 123,
        "nome": "Empresa ABC",
        "score_engajamento": 0.85,
        "score_movimentacao_estoque": 0.72,
        "score_crm": 0.90,
        "score_adoption": 0.65,
        "score_total": 0.78,
        "categoria": "Saudável",
        "qntd_acessos_30d": 45,
        "dias_desde_ultimo_acesso": 2
    }
}
```

**Categorias de Score:**
| Categoria | Score |
|-----------|-------|
| Crítico | 0 - 0.25 |
| Normal | 0.26 - 0.50 |
| Saudável | 0.51 - 0.75 |
| Campeão | 0.76 - 1.00 |

---

## 📈 Dashboard

### `GET /dashboard`
**Descrição:** Retorna KPIs do dashboard de gestão

**🔒 Autenticação:** Basic Auth

**Query Parameters:**
| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `data_inicio` | string | Data inicial (YYYY-MM-DD) |
| `data_fim` | string | Data final (YYYY-MM-DD) |

**Response:**
```json
{
    "total_clientes": 350,
    "clientes_ativos": 280,
    "clientes_inadimplentes": 25,
    "clientes_cancelados": 45,
    "mrr_total": 84000.00,
    "ticket_medio": 300.00,
    "tmo_medio": 15,
    "novos_mes": 28,
    "churns_mes": 8,
    "distribuicao_health": {
        "critico": 15,
        "normal": 45,
        "saudavel": 120,
        "campeao": 100
    }
}
```

---

## 🔐 Logins

### `GET /logins`
**Descrição:** Retorna logins de um tenant específico nos últimos 30 dias

**🔒 Autenticação:** Basic Auth

**Query Parameters:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| `tenant_id` | string | Sim | ID do tenant |

**Response:**
```json
{
    "tenant_id": "123",
    "periodo": "30 dias",
    "total_logins": 156,
    "dias_com_login": 22,
    "ultimo_login": {
        "usuario_nome": "João Silva",
        "usuario_email": "joao@empresa.com",
        "data_login": "2024-12-09T14:30:00",
        "data": "2024-12-09",
        "hora": "14:30:00"
    },
    "logins": [
        {
            "usuario_nome": "João Silva",
            "usuario_email": "joao@empresa.com",
            "data_login": "2024-12-09T14:30:00",
            "data": "2024-12-09",
            "hora": "14:30:00"
        }
    ]
}
```

---

## 📊 Métricas

### `GET /metricas-clientes`
**Descrição:** Retorna métricas agregadas mensais dos clientes

**🔒 Autenticação:** Basic Auth

**Response:**
```json
[
    {
        "mes_referencia": "01/2024",
        "novos_clientes": 45,
        "clientes_churned": 12,
        "total_ativos_final_mes": 230,
        "total_ativos_inicio_mes": 197,
        "churns_rate": 5.23,
        "growth_rate": 16.75
    }
]
```

---

## 🏦 Credere

### `POST /add-client-credere`
**Descrição:** Adiciona um único cliente no sistema Credere

**🔒 Autenticação:** Basic Auth

**Request Body:**
```json
{
    "name": "Empresa ABC Ltda",
    "cnpj": "44.285.354/0001-03"
}
```

**Response:**
```json
{
    "success": true,
    "client_name": "Empresa ABC Ltda",
    "cnpj": "44285354000103",
    "store_id": 12345,
    "insert_message": "✅ Cliente inserido com sucesso",
    "persist_success": true,
    "persist_message": "✅ Credenciais persistidas",
    "already_exists": false
}
```

---

### `POST /add-clients-credere`
**Descrição:** Adiciona múltiplos clientes no Credere em lote

**🔒 Autenticação:** Basic Auth

**Request Body:**
```json
{
    "clients": [
        {"name": "Empresa A", "cnpj": "12345678000190"},
        {"name": "Empresa B", "cnpj": "98.765.432/0001-10"}
    ]
}
```

**Response:**
```json
{
    "results": [
        {
            "success": true,
            "client_name": "Empresa A",
            "store_id": 123,
            "already_exists": false
        },
        {
            "success": true,
            "client_name": "Empresa B",
            "store_id": 124,
            "already_exists": false
        }
    ]
}
```

---

### `GET /all-clients-credere`
**Descrição:** Retorna lista de CNPJs de todos os clientes cadastrados no Credere

**🔒 Autenticação:** Basic Auth

**Response:**
```json
{
    "all_clients": [
        "12345678000190",
        "98765432000110",
        "44285354000103"
    ]
}
```

---

### `POST /check-existing-clients-credere`
**Descrição:** Verifica quais CNPJs já existem no Credere

**🔒 Autenticação:** Basic Auth

**Request Body:**
```json
{
    "cnpjs": ["08098404000171", "44.285.354/0001-03", "49.796.764/0001-24"]
}
```

**Response:**
```json
{
    "total": 3,
    "existing": 2,
    "not_found": 1,
    "invalid": 0,
    "results": [
        {
            "cnpj_original": "08098404000171",
            "cnpj_normalized": "08098404000171",
            "exists": true,
            "client_name": "Empresa ABC",
            "status": "✅ Cliente existe no Credere"
        },
        {
            "cnpj_original": "44.285.354/0001-03",
            "cnpj_normalized": "44285354000103",
            "exists": true,
            "client_name": "Empresa XYZ",
            "status": "✅ Cliente existe no Credere"
        },
        {
            "cnpj_original": "49.796.764/0001-24",
            "cnpj_normalized": "49796764000124",
            "exists": false,
            "client_name": null,
            "status": "❌ Cliente não encontrado"
        }
    ]
}
```

---

### `POST /credere/cache/clear`
**Descrição:** Limpa o cache de clientes do Credere

**🔒 Autenticação:** Basic Auth

**Response:**
```json
{
    "status": "success",
    "message": "Cache do Credere limpo com sucesso",
    "note": "A próxima requisição buscará dados atualizados da API"
}
```

---

## 💰 Vendas e Comissões

### `GET /vendas/vendedores`
**Descrição:** Retorna lista de vendedores ativos

**🔒 Autenticação:** Basic Auth

**Response:**
```json
[
    {
        "id": 12476067,
        "name": "Amanda Klava",
        "email": "amanda@ecosys.com.br"
    },
    {
        "id": 13734187,
        "name": "Eduarda Oliveira",
        "email": "eduarda@ecosys.com.br"
    }
]
```

---

### `GET /vendas/clientes`
**Descrição:** Retorna todos os clientes para cálculo de comissão (valor > 0)

**🔒 Autenticação:** Basic Auth

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
        "month": "2024-01"
    }
]
```

---

### `GET /vendas/clientes/vendedor/{vendedor_id}`
**Descrição:** Retorna clientes de um vendedor específico

**🔒 Autenticação:** Basic Auth

**Path Parameters:**
| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `vendedor_id` | integer | ID do vendedor (use 99999999 para Vendas Antigas) |

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
        "month": "2024-01"
    }
]
```

---

### `GET /vendas/clientes/inadimplentes`
**Descrição:** Retorna clientes inadimplentes (valor > 0)

**🔒 Autenticação:** Basic Auth

**Response:**
```json
[
    {
        "id": "456",
        "clientName": "Empresa XYZ",
        "mrr": 199.90,
        "setupValue": 300.00,
        "date": "2024-03-10",
        "status": "inadimplente",
        "sellerId": "13734187",
        "sellerName": "Eduarda Oliveira",
        "month": "2024-03"
    }
]
```

---

### `GET /vendas/clientes/novos`
**Descrição:** Retorna novos clientes do mês atual (valor > 0)

**🔒 Autenticação:** Basic Auth

**Response:**
```json
[
    {
        "id": "789",
        "clientName": "Empresa Nova",
        "mrr": 399.90,
        "setupValue": 800.00,
        "date": "2024-12-05",
        "status": "ativo",
        "sellerId": "12476067",
        "sellerName": "Amanda Klava",
        "month": "2024-12"
    }
]
```

---

### `GET /vendas/clientes/churns`
**Descrição:** Retorna churns do mês atual (valor > 0)

**🔒 Autenticação:** Basic Auth

**Response:**
```json
[
    {
        "id": "321",
        "clientName": "Empresa Cancelada",
        "mrr": 299.90,
        "setupValue": 500.00,
        "date": "2024-06-15",
        "status": "cancelado",
        "sellerId": "12985247",
        "sellerName": "Fabiana Lima",
        "canceledAt": "2024-12-03",
        "month": "2024-06"
    }
]
```

---

### `GET /vendas/resumo-comissoes`
**Descrição:** Retorna resumo de comissões por vendedor

**🔒 Autenticação:** Basic Auth

**Response:**
```json
[
    {
        "vendedor": {
            "id": 12476067,
            "name": "Amanda Klava",
            "email": "amanda@ecosys.com.br"
        },
        "totalClientes": 50,
        "clientesAtivos": 45,
        "clientesInadimplentes": 3,
        "clientesCancelados": 2,
        "mrrAtivo": 13500.00,
        "setupTotal": 25000.00
    }
]
```

---

### `GET /vendas/dashboard`
**Descrição:** Retorna métricas gerais do dashboard de vendas

**🔒 Autenticação:** Basic Auth

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
    "ticketMedio": 300.00
}
```

---

### `GET /vendas/ranking`
**Descrição:** Retorna ranking de vendedores por MRR ativo

**🔒 Autenticação:** Basic Auth

**Response:**
```json
[
    {
        "vendedor": {
            "id": 12476067,
            "name": "Amanda Klava",
            "email": "amanda@ecosys.com.br"
        },
        "mrrAtivo": 15000.00,
        "clientesAtivos": 50,
        "novosMes": 8,
        "posicao": 1
    },
    {
        "vendedor": {
            "id": 13734187,
            "name": "Eduarda Oliveira",
            "email": "eduarda@ecosys.com.br"
        },
        "mrrAtivo": 12500.00,
        "clientesAtivos": 42,
        "novosMes": 5,
        "posicao": 2
    }
]
```

---

### `POST /vendas/cache/clear`
**Descrição:** Limpa o cache de vendas

**🔒 Autenticação:** Basic Auth

**Response:**
```json
{
    "status": "success",
    "message": "Cache de vendas limpo com sucesso",
    "keys_deleted": 15
}
```

---

## 🗑️ Cache

### `POST /cache/clear`
**Descrição:** Limpa todo o cache da aplicação

**🔒 Autenticação:** Basic Auth

**Response:**
```json
{
    "status": "success",
    "message": "Cache limpo com sucesso",
    "keys_deleted": 42
}
```

---

### `GET /cache/stats`
**Descrição:** Retorna estatísticas do cache

**🔒 Autenticação:** Basic Auth

**Response:**
```json
{
    "total_keys": 42,
    "by_type": {
        "clientes": 5,
        "health_scores": 5,
        "dashboard": 5,
        "evolution": 5,
        "metricas": 1,
        "logins": 21
    },
    "timestamp": "2024-12-09T10:30:00.000Z"
}
```

---

## 📝 Códigos de Status HTTP

| Código | Descrição |
|--------|-----------|
| `200` | Sucesso |
| `401` | Não autorizado (credenciais inválidas) |
| `500` | Erro interno do servidor |
| `503` | Serviço indisponível |

---

## 🔧 Headers de Resposta

| Header | Descrição |
|--------|-----------|
| `X-Process-Time` | Tempo de processamento da requisição |
| `Content-Encoding` | `gzip` quando compressão ativa |

---

## 📌 Mapeamento de Vendedores

| Nome | ID |
|------|------|
| Amanda Klava | 12476067 |
| Eduarda Oliveira | 13734187 |
| Fabiana Lima | 12985247 |
| Marcos Roberto | 12466499 |
| Lindolfo Silva | 14164344 |
| Jaqueline Matos | 14164336 |
| Gabriela Lima | 14164332 |
| Venda Antiga | 99999999 |

---

## ⏱️ Configuração de Cache (TTL)

| Recurso | TTL |
|---------|-----|
| Clientes | 24 horas |
| Health Scores | 24 horas |
| Dashboard | 24 horas |
| Evolution | 24 horas |
| Métricas | 24 horas |
| Logins | 1 hora |
| Vendas | 12 horas |
| Vendedores | 24 horas |
