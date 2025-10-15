# 📝 Changelog - Mudança no Sistema de Filtros

## Data: 2025-01-XX

### 🎯 Objetivo da Mudança
Implementar filtro unificado que captura tanto **novos clientes** (data de adesão) quanto **churns** (data de cancelamento) no mesmo período.

---

## ✅ Mudanças Implementadas

### 1. **Parâmetros de Query Atualizados**

#### Antes:
```
data_adesao_inicio (YYYY-MM-DD)
data_adesao_fim (YYYY-MM-DD)
```

#### Depois:
```
data_inicio (YYYY-MM-DD)
data_fim (YYYY-MM-DD)
```

**Razão**: Nomes mais genéricos, pois agora filtramos por múltiplos campos de data.

---

### 2. **Lógica de Filtragem Modificada**

#### Antes:
```python
# Filtrava apenas por data_adesao
if data_adesao_inicio and cliente.data_adesao < data_adesao_inicio:
    skip_cliente = True
if data_adesao_fim and cliente.data_adesao > data_adesao_fim:
    skip_cliente = True
```

#### Depois:
```python
# Filtra por data_adesao OU data_cancelamento (lógica OR)
incluir_cliente = False

# Verificar se aderiu no período
if data_adesao in range(data_inicio, data_fim):
    incluir_cliente = True

# Verificar se deu churn no período
if data_cancelamento in range(data_inicio, data_fim):
    incluir_cliente = True
```

**Razão**: Permite capturar o **movimento completo de clientes** em um período:
- Novos clientes que entraram
- Clientes que saíram (churn)

---

### 3. **Novos KPIs no Dashboard**

Adicionado ao endpoint `/dashboard`:

```json
{
  "novos_clientes": 45,        // Quantidade de clientes que aderiram no período
  "clientes_churn": 12,         // Quantidade de clientes que cancelaram no período
  "clientes_ativos": 230,
  "clientes_pagantes": 225,
  "mrr_value": 337500.00,
  "churn_value": 18000.00,
  ...
}
```

**Cálculo**:
- `novos_clientes`: COUNT de clientes onde `data_adesao` está no intervalo [data_inicio, data_fim]
- `clientes_churn`: COUNT de clientes onde `data_cancelamento` está no intervalo [data_inicio, data_fim]

---

### 4. **Arquivos Modificados**

#### ✅ `api/scripts/clientes.py`
- Função `fetch_clientes(data_inicio, data_fim)`:
  - Renomeados parâmetros
  - Implementada lógica OR para incluir cliente se qualquer data estiver no range
  - Converte ambas as datas (`data_adesao` e `data_cancelamento`) para datetime

- Função `clientes_to_dataframe(data_inicio, data_fim)`:
  - Renomeados parâmetros
  - Atualizada docstring

#### ✅ `api/scripts/health_scores.py`
- Função `filter_active_clients(df, data_inicio, data_fim)`:
  - Renomeados parâmetros
  
- Função `merge_dataframes(data_inicio, data_fim)`:
  - Renomeados parâmetros
  - Atualizada docstring para refletir filtro duplo

#### ✅ `api/scripts/dashboard.py`
- Função `calculate_dashboard_kpis(data_inicio, data_fim)`:
  - Renomeados parâmetros
  - Adicionada lógica para contar `novos_clientes` e `clientes_churn` separadamente
  - Converte datas de filtro para comparação
  - Atualizado retorno incluindo novos KPIs

#### ✅ `api/main.py`
- Endpoint `GET /clientes`:
  - Parâmetros: `data_inicio`, `data_fim`
  - Cache key: `clientes:{data_inicio}:{data_fim}`
  - Docstring atualizada explicando lógica OR

- Endpoint `GET /health-scores`:
  - Parâmetros: `data_inicio`, `data_fim`
  - Cache key: `health-scores:{data_inicio}:{data_fim}`
  - Docstring atualizada

- Endpoint `GET /dashboard`:
  - Parâmetros: `data_inicio`, `data_fim`
  - Cache key: `dashboard:{data_inicio}:{data_fim}`
  - Docstring atualizada incluindo novos KPIs no retorno

---

## 📊 Impacto nas Integrações

### URLs de Exemplo

#### Antes:
```bash
GET /clientes?data_adesao_inicio=2024-01-01&data_adesao_fim=2024-12-31
GET /health-scores?data_adesao_inicio=2024-06-01&data_adesao_fim=2024-09-30
GET /dashboard?data_adesao_inicio=2024-01-01
```

#### Depois:
```bash
GET /clientes?data_inicio=2024-01-01&data_fim=2024-12-31
GET /health-scores?data_inicio=2024-06-01&data_fim=2024-09-30
GET /dashboard?data_inicio=2024-01-01
```

### Resposta do Dashboard

#### Antes:
```json
{
  "clientes_ativos": 230,
  "clientes_pagantes": 225,
  "clientes_onboarding": 15,
  "clientes_churn": 150,    // Total histórico
  "mrr_value": 337500.00,
  "churn_value": 225000.00,  // Total histórico
  "tmo_dias": 36,
  "clientes_health": {...}
}
```

#### Depois:
```json
{
  "clientes_ativos": 230,
  "clientes_pagantes": 225,
  "clientes_onboarding": 15,
  "novos_clientes": 45,      // Novos no período selecionado
  "clientes_churn": 12,      // Churns no período selecionado
  "mrr_value": 337500.00,
  "churn_value": 18000.00,   // Valor perdido no período
  "tmo_dias": 36,
  "clientes_health": {...}
}
```

---

## 🔄 Compatibilidade

### ⚠️ BREAKING CHANGE

Esta é uma **mudança incompatível** (breaking change) que requer atualização de:

1. **Frontend/Clientes da API**:
   - Atualizar todos os parâmetros de query de `data_adesao_inicio/fim` para `data_inicio/fim`
   - Atualizar parsing do response do `/dashboard` para incluir `novos_clientes`

2. **Documentação**:
   - ✅ Atualizar API_DOCUMENTATION.md (pendente)
   - ✅ Atualizar QUICK_START.md (pendente)
   - ✅ Atualizar Postman Collection (pendente)

3. **Testes**:
   - Criar testes para validar lógica OR
   - Testar contadores de `novos_clientes` e `clientes_churn`

---

## 🧪 Casos de Teste

### Cenário 1: Cliente que aderiu no período
```python
cliente = {
    "data_adesao": "2024-06-15",
    "data_cancelamento": None
}
filtro = {"data_inicio": "2024-06-01", "data_fim": "2024-06-30"}

# Resultado: incluir_cliente = True
# Motivo: data_adesao está no range
```

### Cenário 2: Cliente que deu churn no período
```python
cliente = {
    "data_adesao": "2023-01-10",
    "data_cancelamento": "2024-06-20"
}
filtro = {"data_inicio": "2024-06-01", "data_fim": "2024-06-30"}

# Resultado: incluir_cliente = True
# Motivo: data_cancelamento está no range
```

### Cenário 3: Cliente que aderiu E deu churn no período
```python
cliente = {
    "data_adesao": "2024-06-05",
    "data_cancelamento": "2024-06-25"
}
filtro = {"data_inicio": "2024-06-01", "data_fim": "2024-06-30"}

# Resultado: incluir_cliente = True
# Motivo: ambas as datas estão no range
# Dashboard conta:
#   - novos_clientes += 1
#   - clientes_churn += 1
```

### Cenário 4: Cliente fora do período
```python
cliente = {
    "data_adesao": "2023-01-10",
    "data_cancelamento": "2023-12-20"
}
filtro = {"data_inicio": "2024-06-01", "data_fim": "2024-06-30"}

# Resultado: incluir_cliente = False
# Motivo: nenhuma data está no range
```

---

## 📈 Benefícios

1. **Análise Temporal Completa**: Visualizar movimento completo de clientes (entrada + saída) em um período
2. **Simplicidade**: Um único filtro de datas para múltiplos casos de uso
3. **Métricas Mais Precisas**: Separação clara entre churns totais vs churns do período
4. **Flexibilidade**: Lógica OR permite análises mais ricas

---

## 🔮 Próximos Passos

- [ ] Atualizar API_DOCUMENTATION.md
- [ ] Atualizar QUICK_START.md
- [ ] Atualizar EcoSys_API.postman_collection.json
- [ ] Criar testes unitários para nova lógica
- [ ] Notificar equipe de frontend sobre mudanças
- [ ] Atualizar versão da API para v1.1.0

---

## 📞 Contato

Para dúvidas sobre esta mudança, contatar a equipe de desenvolvimento.
