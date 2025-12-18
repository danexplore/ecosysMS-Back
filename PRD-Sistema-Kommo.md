# PRD - Sistema de Produtividade e Análise de Leads Kommo
**Product Requirements Document**

---

## 📋 Sumário Executivo

Sistema de análise e acompanhamento de performance de vendas integrado ao CRM Kommo, com foco em **produtividade de vendedores**, **conversão de leads** e **análise de marketing**. O sistema fornece dashboards interativos, métricas em tempo real e insights inteligentes baseados em IA para otimização do processo comercial.

**Objetivo da Migração:** Transformar o sistema atual (Streamlit monolítico) em uma arquitetura moderna com backend FastAPI e frontend desacoplado, permitindo maior escalabilidade, performance e facilidade de manutenção.

---

## 🎯 Visão Geral do Sistema Atual

### Stack Tecnológica Atual
- **Frontend**: Streamlit (Python)
- **Backend**: Integrado no Streamlit
- **Banco de Dados**: PostgreSQL (Supabase)
- **Integrações**: 
  - Supabase (dados)
  - Google Gemini (IA/Insights)
- **Deploy**: Vercel

### Modelo de Dados Principal

#### Tabelas/Views do Supabase:
1. **kommo_leads_statistics** (view principal)
   - `id`: ID único do lead
   - `lead_name`: Nome do lead
   - `vendedor`: Vendedor responsável
   - `status_id`, `status`: Status atual do lead
   - `pipeline`: Funil do lead
   - `criado_em`: Data de criação (timestamp)
   - `data_agendamento`: Data do agendamento
   - `data_demo`: Data da demonstração
   - `data_hora_demo`: Data e hora da demo (com timezone)
   - `data_noshow`: Data do no-show
   - `data_venda`: Data da venda
   - `utm_campaign`, `utm_source`, `utm_medium`: Parâmetros UTM

2. **kommo_users**
   - `user_name`: Nome do usuário
   - `kommo_user_id`: ID do usuário no Kommo

3. **kommo_chamadas** (dados de telefonia)
   - `name`: Nome do vendedor
   - `ramal`: Ramal
   - `atendente`: Nome do atendente
   - `atendido_em`: Data/hora da chamada
   - `duration`: Duração em segundos
   - `causa_desligamento`: Resultado ("Atendida", etc)
   - `url_gravacao`: URL da gravação

#### RPCs (Stored Procedures) Otimizadas:
- `get_leads_by_period(p_data_inicio, p_data_fim)`: Busca leads por período
- `get_tempo_por_etapa()`: Calcula tempo médio por etapa do funil
- `get_chamadas_vendedores(data_inicio, data_fim)`: Dados de telefonia

---

## 🔍 Funcionalidades por Módulo

### 1. 🚨 **Módulo: Leads com Atenção**
**Objetivo:** Identificar leads que precisam de ação imediata

**Regras de Negócio:**
- Lead tem `data_hora_demo` vencida (< data/hora atual)
- `data_noshow` está vazio
- `data_venda` está vazio
- Status NÃO está em STATUS_POS_DEMO (demos realizadas ou finalizadas)

**Outputs:**
- Lista ordenada por data_demo (mais antiga primeiro)
- Colunas: Lead, Vendedor, Status Atual, Data e Hora, Link Kommo
- Contador total de leads que exigem atenção

**Endpoints FastAPI Necessários:**
```
GET /api/leads/necessitam-atencao
Query params: data_inicio, data_fim, vendedores[], pipelines[]
Response: { count: int, leads: Lead[] }
```

---

### 2. 🤖 **Módulo: Insights com IA (Google Gemini)**
**Objetivo:** Gerar análises automatizadas e recomendações estratégicas

**Funcionalidades:**
1. **Análise Automática de Performance**
   - Compara período atual com período anterior
   - Identifica tendências (positivas/negativas)
   - Calcula variações percentuais de KPIs

2. **Chat Conversacional**
   - Permite perguntas sobre os dados
   - Mantém contexto da conversa
   - Respostas baseadas nas métricas atuais

**Métricas Analisadas:**
- Total de leads
- Leads com demo
- Demos realizadas
- No-shows
- Taxa de conversão
- Leads convertidos

**Prompt Engineering:**
- System prompt: Analista sênior de vendas especializado em concessionárias
- Formato: Resumo executivo + Pontos críticos + Recomendações priorizadas
- Estilo: Objetivo, com números e percentuais específicos

**Endpoints FastAPI Necessários:**
```
POST /api/insights/gerar
Body: { metricas_atual, metricas_anterior, periodo }
Response: { insights: string, gerado_em: datetime }

POST /api/insights/chat
Body: { mensagem: string, contexto: {}, historico: [] }
Response: { resposta: string }
```

---

### 3. 📆 **Módulo: Demos de Hoje**
**Objetivo:** Acompanhamento de demonstrações agendadas para o dia atual

**Regras de Filtro:**
- `data_demo` = data de hoje
- `data_noshow` está vazio (não é no-show)
- Status NÃO está em DEMO_COMPLETED_STATUSES ou FUNNEL_CLOSED_STATUSES

**Outputs:**
- Total de demos hoje
- Vendedores ativos
- Média de demos por vendedor
- Lista ordenada por horário
- Colunas: Lead, Vendedor, Status, Horário da Demo, Link

**Cálculos:**
- Timezone: America/Sao_Paulo (GMT-3)
- Priorizar `data_hora_demo` sobre `data_demo`

**Endpoints FastAPI Necessários:**
```
GET /api/demos/hoje
Query params: vendedores[], pipelines[]
Response: { 
  total: int, 
  vendedores_ativos: int, 
  media_por_vendedor: float,
  demos: Demo[] 
}
```

---

### 4. 📅 **Módulo: Resumo Diário da Equipe**
**Objetivo:** Visão agregada de atividades por dia

**Métricas por Dia:**
- **Novos Leads**: Criados no dia (`criado_em`)
- **Agendamentos**: Demos agendadas (`data_agendamento`)
- **Demos no Dia**: Total de demos (`data_demo`)
- **No-shows**: Demos não realizadas (`data_noshow`)
- **Demos Realizadas**: Aplicando regra de negócio específica

**Regra de "Demo Realizada":**
```python
(status == 'Desqualificados' AND data_demo.notna() AND data_noshow.isna())
OR
(data_demo.notna() AND status IN DEMO_COMPLETED_STATUSES)
```

**Cálculos Adicionais:**
- % Demos Realizadas: (demos_realizadas / demos_dia * 100)
- % No-show: (noshow / demos_dia * 100)

**Outputs:**
- Tabela por dia (mais recente primeiro)
- Linha de TOTAL no final
- Tradução de dias da semana (português)

**Endpoints FastAPI Necessários:**
```
GET /api/resumo/diario
Query params: data_inicio, data_fim, vendedores[], pipelines[]
Response: { resumo_por_dia: ResumoDia[], totais: ResumoDia }
```

---

### 5. 🔍 **Módulo: Detalhes dos Leads**
**Objetivo:** Tabela completa e pesquisável de todos os leads

**Filtros:**
- Busca por nome do lead
- Período de datas
- Vendedores
- Pipelines

**Colunas Principais:**
- ID, Lead Name, Vendedor, Status
- Pipeline
- Data Criação, Data Agendamento, Data Demo, Data No-show, Data Venda
- Link Kommo

**Funcionalidades:**
- Ordenação por múltiplas colunas
- Exportação de dados (CSV/Excel)
- Links clicáveis para Kommo

**Endpoints FastAPI Necessários:**
```
GET /api/leads
Query params: 
  - busca: string
  - data_inicio, data_fim
  - vendedores[], pipelines[]
  - page, limit
  - sort_by, sort_order
Response: { 
  total: int, 
  page: int, 
  leads: Lead[] 
}

GET /api/leads/export
Query params: formato (csv/xlsx)
Response: File download
```

---

### 6. ⏱️ **Módulo: Tempo por Etapa**
**Objetivo:** Identificar gargalos no funil de vendas

**Fonte de Dados:**
- RPC: `get_tempo_por_etapa()`
- Retorna: status_id, status_name, media_tempo_horas

**Cálculos:**
- Converter horas para dias (/ 24)
- Ordenar por tempo decrescente

**Visualizações:**
1. Gráfico de barras (tempo por etapa)
2. Ranking de etapas
3. Tabela detalhada

**Filtros:**
- Seleção múltipla de etapas
- Por padrão: Top 10 etapas

**Insights:**
- Etapas com tempo elevado = gargalo
- Recomendações de ação

**Endpoints FastAPI Necessários:**
```
GET /api/analytics/tempo-por-etapa
Response: { etapas: { status: string, dias: float }[] }
```

---

### 7. 📞 **Módulo: Produtividade do Vendedor (Telefonia)**
**Objetivo:** Análise detalhada de chamadas e efetividade

**Classificações de Ligação:**
- **Discagem**: Toda tentativa de ligação
- **Atendida**: `causa_desligamento == "Atendida"`
- **Efetiva**: Atendida E `duration > 50 segundos`

**Métricas Principais:**
1. **Volume**
   - Total de discagens
   - Total atendidas
   - Total efetivas

2. **Taxas**
   - Taxa de atendimento: (atendidas / discagens * 100)
   - Taxa de efetividade: (efetivas / atendidas * 100)
   - Taxa de conversão geral: (efetivas / discagens * 100)

3. **Tempo Médio**
   - TMD Atendidas: Duração média de ligações atendidas
   - TMD Efetivas: Duração média de ligações efetivas

**Visualizações:**
1. **Evolução de Discagens por Dia** (gráfico de linhas)
   - Por vendedor
   - Identificar padrões e picos

2. **Funil de Conversão**
   - Discagens → Atendidas → Efetivas
   - Percentuais de conversão

3. **Distribuição por Vendedor**
   - Comparação de performance

4. **Análise de Horários**
   - Top 3 horários com mais efetivas
   - Recomendações de melhor período

5. **Tabelas Detalhadas**
   - Ligações efetivas (com gravação)
   - Histórico completo de discagens

**Metas de Performance:**
- Meta de conversão: 15% de ligações efetivas
- Duração mínima efetiva: 50 segundos

**Endpoints FastAPI Necessários:**
```
GET /api/chamadas/vendedor
Query params: 
  - data_inicio, data_fim
  - vendedor (opcional)
Response: { 
  metricas: {
    total_discagens, total_atendidas, total_efetivas,
    taxa_atendimento, taxa_efetividade, taxa_conversao_geral,
    tmd_atendidas, tmd_efetivas
  },
  evolucao_diaria: [],
  top_horarios: [],
  ligacoes: Chamada[]
}

GET /api/chamadas/metricas-vendedores
Query params: data_inicio, data_fim
Response: { vendedores: VendedorMetricas[] }
```

---

### 8. 💰 **Módulo: Mural de Vendas**
**Objetivo:** Análise completa de vendas e desempenho comercial

**Filtro Principal:**
- Leads com `data_venda` não nulo
- Dentro do período selecionado

**Métricas Gerais:**
1. Total de vendas
2. Tempo médio de venda (da criação até venda, em dias)
3. Taxa de conversão do período
4. Top vendedor (mais vendas)
5. Venda mais rápida (menor tempo)

**Análises por Vendedor:**
- Ranking de vendas
- Taxa de conversão individual
- Tempo médio por vendedor

**Análises por Período:**
- Vendas por dia/semana/mês
- Tendências de crescimento
- Comparação com período anterior

**Análises por Pipeline:**
- Distribuição de vendas por funil
- Performance de cada pipeline

**Ciclo de Venda:**
- Distribuição do tempo de venda (histograma)
- Quartis (25%, 50%, 75%)
- Identificação de outliers

**Tabela Detalhada:**
- Lead, Vendedor, Pipeline
- Data Criação, Data Venda
- Ciclo (dias)
- Link Kommo

**Endpoints FastAPI Necessários:**
```
GET /api/vendas/resumo
Query params: data_inicio, data_fim, vendedores[], pipelines[]
Response: { 
  metricas_gerais: {},
  por_vendedor: [],
  por_pipeline: [],
  ciclo_venda: {
    media: float,
    mediana: float,
    quartis: {}
  }
}

GET /api/vendas/detalhadas
Query params: data_inicio, data_fim, vendedores[], pipelines[]
Response: { vendas: Venda[] }

GET /api/vendas/tendencias
Query params: data_inicio, data_fim, agrupamento (dia/semana/mes)
Response: { tendencia: [] }
```

---

### 9. ✅ **Módulo: Demos Realizadas**
**Objetivo:** Análise completa das demonstrações realizadas

**Fonte de Dados:**
- RPC: `get_leads_by_data_demo()` com filtros

**Regra de "Demo Realizada":**
```python
(status == 'Desqualificados' AND data_demo.notna() AND data_noshow.isna())
OR
(data_demo.notna() AND status IN DEMO_COMPLETED_STATUSES)
```

**DEMO_COMPLETED_STATUSES:**
- "5 - Demonstração realizada"
- "6 - Lead quente"
- "5 - VISITA REALIZADA"
- "6 - EM Negociação"

**Métricas:**
1. Total demos realizadas
2. Demos convertidas (vendas)
3. Demos desqualificadas
4. Taxa de conversão demo → venda

**ROI Marketing:**
Análise por dimensão UTM (campaign/source/medium):
- Volume de demos por campanha
- Taxa de conversão por campanha
- Taxa de desqualificação
- Identificação de campanhas mais efetivas

**Visualizações:**
1. Top 10 campanhas (volume)
2. Demos x Conversões (comparativo)
3. Taxa de desqualificação por campanha
4. Tabela detalhada de ROI

**Insights Automáticos:**
- Campanhas com melhor ROI
- Campanhas com alta desqualificação (alerta)
- Recomendações de investimento

**Endpoints FastAPI Necessários:**
```
GET /api/demos/realizadas
Query params: data_inicio, data_fim, vendedores[], pipelines[]
Response: { 
  metricas: {
    total, convertidas, desqualificadas, taxa_conversao
  },
  demos: Demo[]
}

GET /api/demos/roi-marketing
Query params: 
  - data_inicio, data_fim
  - utm_dimension (campaign/source/medium)
Response: { 
  campanhas: {
    nome: string,
    total_demos: int,
    convertidos: int,
    desqualificados: int,
    taxa_conversao: float,
    taxa_desqualificacao: float
  }[]
}
```

---

### 10. 📣 **Módulo: Marketing Analytics**
**Objetivo:** Análise avançada de performance de campanhas

**Classe Principal:** `MarketingAnalyzer`

**Dimensões de Análise:**
- `UTMDimension.CAMPAIGN`: Campanhas
- `UTMDimension.SOURCE`: Fontes de tráfego
- `UTMDimension.MEDIUM`: Mídias

**Métricas Calculadas:**

#### Por Campanha:
```python
class CampaignMetrics:
    - total_leads
    - demos_agendadas
    - demos_realizadas
    - desqualificados
    - vendas
    - noshows
    - taxa_agendamento
    - taxa_conversao_lead_venda
    - taxa_desqualificacao
```

#### Resumo Geral:
- Campanhas ativas
- Fontes ativas
- % Rastreamento (leads com UTM)
- Total vendas
- Taxa de conversão geral

**Insights Automáticos:**
Tipos de insight gerados:
- `POSITIVE`: Destaque positivo
- `WARNING`: Alerta/atenção
- `CRITICAL`: Problema crítico
- `INFO`: Informativo
- `OPPORTUNITY`: Oportunidade de melhoria

**Comparação entre Períodos:**
```python
class PeriodComparison:
    - periodo_atual
    - periodo_anterior
    - variacao_leads
    - variacao_vendas
    - variacao_taxa_conversao
```

**Visualizações:**
1. Cards de métricas resumidas
2. Gráfico de performance por campanha
3. Funil de conversão
4. Análise de desqualificação
5. Ranking de campanhas
6. Tabela de métricas completas
7. Gráfico de tendências

**Endpoints FastAPI Necessários:**
```
GET /api/marketing/resumo
Query params: data_inicio, data_fim
Response: { 
  campanhas_ativas, fontes_ativas, 
  pct_rastreamento, total_vendas, 
  taxa_conversao_geral 
}

GET /api/marketing/campanhas
Query params: 
  - data_inicio, data_fim
  - dimensao (campaign/source/medium)
Response: { campanhas: CampaignMetrics[] }

GET /api/marketing/insights
Query params: data_inicio, data_fim
Response: { insights: MarketingInsight[] }

GET /api/marketing/comparacao
Query params: 
  - periodo_atual_inicio, periodo_atual_fim
  - periodo_anterior_inicio, periodo_anterior_fim
Response: { comparacao: PeriodComparison }

GET /api/marketing/funil
Query params: data_inicio, data_fim, dimensao, campanha
Response: { 
  funil: {
    leads, agendamentos, demos, vendas
  }
}
```

---

## 📊 Métricas e Cálculos Principais

### Constantes de Status

```python
# Status que indicam demo concluída
DEMO_COMPLETED_STATUSES = [
    "5 - Demonstração realizada",
    "6 - Lead quente",
    "5 - VISITA REALIZADA",
    "6 - EM Negociação",
]

# Status que indicam saída do funil
FUNNEL_CLOSED_STATUSES = [
    "Venda Ganha",
    "Desqualificados",
]

# Todos status completados
COMPLETED_STATUSES = DEMO_COMPLETED_STATUSES + FUNNEL_CLOSED_STATUSES
```

### Fórmulas de Cálculo

#### 1. Demos Realizadas
```python
def calcular_demos_realizadas(df, data_inicio, data_fim):
    mask = df['data_demo'].notna()
    
    # Filtrar por período
    mask &= (df['data_demo'] >= data_inicio) & (df['data_demo'] <= data_fim)
    
    # Lógica de negócio
    demos_mask = mask & (
        (
            (df['status'] == 'Desqualificados') &
            (df['data_noshow'].isna())
        ) |
        (
            df['status'].isin(DEMO_COMPLETED_STATUSES)
        )
    )
    
    return demos_mask.sum()
```

#### 2. No-shows
```python
def calcular_noshows(df, data_inicio, data_fim):
    mask = df['data_noshow'].notna()
    
    if data_inicio and data_fim:
        mask &= (df['data_noshow'] >= data_inicio) & (df['data_noshow'] <= data_fim)
    
    return mask.sum()
```

#### 3. Vendas
```python
def calcular_vendas(df, data_inicio, data_fim):
    mask = df['data_venda'].notna()
    
    if data_inicio and data_fim:
        mask &= (df['data_venda'] >= data_inicio) & (df['data_venda'] <= data_fim)
    
    return mask.sum()
```

#### 4. Taxa de Conversão
```python
def safe_divide(numerador, denominador, default=0):
    return (numerador / denominador * 100) if denominador > 0 else default
```

#### 5. Ligações Efetivas (Telefonia)
```python
def classificar_ligacao(row):
    if row['causa_desligamento'] == 'Atendida' and row['duration'] > 50:
        return 'Efetiva'
    elif row['causa_desligamento'] == 'Atendida':
        return 'Atendida'
    else:
        return 'Não Atendida'
```

#### 6. Meta de Conversão para Demos
```python
META_CONVERSAO_EFETIVAS = 0.15  # 15% das discagens devem ser efetivas
DURACAO_MINIMA_EFETIVA = 50     # 50 segundos
```

---

## 🔗 Integrações

### 1. Supabase (PostgreSQL)

**Configuração:**
- SUPABASE_URL
- SUPABASE_KEY

**Cache:**
- TTL Leads: 30 minutos (1800s)
- TTL Chamadas: 30 minutos
- TTL Tempo por Etapa: 30 minutos

**Otimizações:**
- Uso de RPCs (stored procedures)
- Cache em múltiplas camadas
- Pré-computação de colunas `.date()`

### 2. Google Gemini (IA)

**Modelo:** Gemini 1.5 Flash

**Configuração:**
- GEMINI_API_KEY

**Uso:**
1. Geração de insights automáticos
2. Chat conversacional sobre dados

**Limites:**
- Gratuito até 15 requisições/minuto

**Cache:**
- TTL IA: 1 hora (3600s)

### 3. Kommo CRM

**Integração:**
- Links diretos para leads: `https://ecosysauto.kommo.com/leads/detail/{lead_id}`

---

## 🎨 UI/UX - Temas e Estilos

### Paleta de Cores

```python
COLORS = {
    'primary': '#20B2AA',        # Teal
    'secondary': '#C0C0C0',      # Silver
    'background': '#1a1f2e',     # Dark blue
    'card_bg': '#2d3748',        # Card background
    'text': '#ffffff',           # White
    'text_secondary': '#CBD5E0', # Light gray
    'success': '#48BB78',        # Green
    'warning': '#FFA500',        # Orange
    'error': '#F56565',          # Red
}

CHART_COLORS = [
    '#4A9FFF',  # Blue
    '#48BB78',  # Green
    '#FFA500',  # Orange
    '#9F7AEA',  # Purple
    '#F56565',  # Red
    '#ED8936',  # Dark Orange
    '#4FD1C5',  # Cyan
    '#FC8181',  # Light Red
    '#B794F4',  # Light Purple
    '#63B3ED',  # Light Blue
]
```

### Componentes Visuais

1. **Métricas (st.metric)**
   - Fundo gradiente (teal/silver)
   - Sombra com glow
   - Valores grandes e destacados

2. **Tabelas**
   - Alternância de cores nas linhas
   - Hover com destaque
   - Cabeçalhos com fundo semi-transparente

3. **Gráficos (Plotly)**
   - Fundo transparente
   - Grid sutil
   - Cores da paleta oficial
   - Hover personalizado

4. **Cards de Insight**
   - Ícones por tipo (✅⚠️🚨ℹ️💡)
   - Priorização (1=alta, 2=média, 3=baixa)
   - Recomendações acionáveis

5. **Estado Vazio**
   - Ícone grande
   - Mensagem clara
   - Sugestão de ação

---

## 🏗️ Arquitetura Proposta (Nova Implementação)

### Backend - FastAPI

```
api/
├── main.py                    # App FastAPI principal
├── requirements.txt
├── config/
│   ├── settings.py            # Configurações (env vars)
│   └── database.py            # Conexão Supabase
├── models/
│   ├── lead.py                # Modelos Pydantic
│   ├── chamada.py
│   ├── venda.py
│   └── marketing.py
├── schemas/
│   ├── requests.py            # Schemas de request
│   └── responses.py           # Schemas de response
├── services/
│   ├── supabase_service.py    # Queries Supabase
│   ├── gemini_service.py      # Integração IA
│   └── analytics_service.py   # Cálculos e métricas
├── routers/
│   ├── leads.py               # Endpoints de leads
│   ├── demos.py               # Endpoints de demos
│   ├── vendas.py              # Endpoints de vendas
│   ├── chamadas.py            # Endpoints de telefonia
│   ├── marketing.py           # Endpoints de marketing
│   └── insights.py            # Endpoints de IA
├── core/
│   ├── metrics.py             # Funções de cálculo
│   ├── helpers.py             # Utilitários
│   └── exceptions.py          # Exceções customizadas
└── middleware/
    ├── cors.py                # CORS
    ├── cache.py               # Cache Redis
    └── auth.py                # Autenticação (futuro)
```

### Frontend - React/Next.js (Sugestão)

```
frontend/
├── src/
│   ├── components/
│   │   ├── Layout/
│   │   ├── Dashboard/
│   │   ├── Charts/
│   │   ├── Tables/
│   │   └── Cards/
│   ├── pages/
│   │   ├── leads-atencao.tsx
│   │   ├── insights-ia.tsx
│   │   ├── demos-hoje.tsx
│   │   ├── resumo-diario.tsx
│   │   ├── detalhes-leads.tsx
│   │   ├── tempo-etapa.tsx
│   │   ├── produtividade.tsx
│   │   ├── mural-vendas.tsx
│   │   ├── demos-realizadas.tsx
│   │   └── marketing-analytics.tsx
│   ├── services/
│   │   └── api.ts             # Axios/Fetch client
│   ├── hooks/
│   │   ├── useLeads.ts
│   │   ├── useVendas.ts
│   │   └── useChamadas.ts
│   ├── contexts/
│   │   └── FilterContext.tsx  # Filtros globais
│   ├── types/
│   │   └── index.ts           # TypeScript types
│   └── utils/
│       ├── formatters.ts
│       └── validators.ts
├── public/
└── package.json
```

---

## 📡 Especificação de Endpoints (API FastAPI)

### Base URL: `/api/v1`

### 1. Leads

#### `GET /leads`
**Descrição:** Lista leads com filtros e paginação

**Query Parameters:**
```typescript
{
  data_inicio?: string (ISO date),
  data_fim?: string (ISO date),
  vendedores?: string[] (array),
  pipelines?: string[] (array),
  busca?: string,
  page?: number = 1,
  limit?: number = 50,
  sort_by?: string = 'criado_em',
  sort_order?: 'asc' | 'desc' = 'desc'
}
```

**Response:**
```typescript
{
  total: number,
  page: number,
  total_pages: number,
  leads: Lead[]
}

interface Lead {
  id: number,
  lead_name: string,
  vendedor: string,
  status_id: number,
  status: string,
  pipeline: string,
  criado_em: string,
  data_agendamento?: string,
  data_demo?: string,
  data_hora_demo?: string,
  data_noshow?: string,
  data_venda?: string,
  utm_campaign?: string,
  utm_source?: string,
  utm_medium?: string,
  kommo_link: string
}
```

#### `GET /leads/necessitam-atencao`
**Descrição:** Leads que precisam de atualização urgente

**Query Parameters:**
```typescript
{
  data_inicio?: string,
  data_fim?: string,
  vendedores?: string[],
  pipelines?: string[]
}
```

**Response:**
```typescript
{
  count: number,
  leads: Lead[]
}
```

#### `GET /leads/export`
**Descrição:** Exportar leads para CSV ou Excel

**Query Parameters:**
```typescript
{
  formato: 'csv' | 'xlsx',
  ...filtros (mesmos de GET /leads)
}
```

**Response:** File download

---

### 2. Demos

#### `GET /demos/hoje`
**Descrição:** Demos agendadas para hoje

**Query Parameters:**
```typescript
{
  vendedores?: string[],
  pipelines?: string[]
}
```

**Response:**
```typescript
{
  total: number,
  vendedores_ativos: number,
  media_por_vendedor: number,
  demos: Demo[]
}

interface Demo {
  id: number,
  lead_name: string,
  vendedor: string,
  status: string,
  horario_demo: string,
  kommo_link: string
}
```

#### `GET /demos/realizadas`
**Descrição:** Demos realizadas no período

**Query Parameters:**
```typescript
{
  data_inicio: string,
  data_fim: string,
  vendedores?: string[],
  pipelines?: string[]
}
```

**Response:**
```typescript
{
  metricas: {
    total: number,
    convertidas: number,
    desqualificadas: number,
    taxa_conversao: number
  },
  demos: Demo[]
}
```

#### `GET /demos/roi-marketing`
**Descrição:** Análise de ROI por campanha

**Query Parameters:**
```typescript
{
  data_inicio: string,
  data_fim: string,
  utm_dimension: 'campaign' | 'source' | 'medium'
}
```

**Response:**
```typescript
{
  campanhas: Campanha[]
}

interface Campanha {
  nome: string,
  total_demos: number,
  convertidos: number,
  desqualificados: number,
  taxa_conversao: number,
  taxa_desqualificacao: number,
  aproveitamento: number
}
```

---

### 3. Vendas

#### `GET /vendas/resumo`
**Descrição:** Métricas gerais de vendas

**Query Parameters:**
```typescript
{
  data_inicio: string,
  data_fim: string,
  vendedores?: string[],
  pipelines?: string[]
}
```

**Response:**
```typescript
{
  metricas_gerais: {
    total_vendas: number,
    tempo_medio_venda: number,
    taxa_conversao: number,
    vendedor_top: string,
    vendas_top: number,
    venda_mais_rapida: number
  },
  por_vendedor: VendedorStats[],
  por_pipeline: PipelineStats[],
  ciclo_venda: {
    media: number,
    mediana: number,
    quartis: {
      q25: number,
      q50: number,
      q75: number
    }
  }
}

interface VendedorStats {
  vendedor: string,
  total_vendas: number,
  tempo_medio: number,
  taxa_conversao: number
}

interface PipelineStats {
  pipeline: string,
  total_vendas: number,
  percentual: number
}
```

#### `GET /vendas/detalhadas`
**Descrição:** Lista detalhada de vendas

**Response:**
```typescript
{
  vendas: Venda[]
}

interface Venda {
  id: number,
  lead_name: string,
  vendedor: string,
  pipeline: string,
  data_criacao: string,
  data_venda: string,
  tempo_venda: number,
  kommo_link: string
}
```

#### `GET /vendas/tendencias`
**Descrição:** Tendências de vendas ao longo do tempo

**Query Parameters:**
```typescript
{
  data_inicio: string,
  data_fim: string,
  agrupamento: 'dia' | 'semana' | 'mes'
}
```

**Response:**
```typescript
{
  tendencia: Tendencia[]
}

interface Tendencia {
  periodo: string,
  total_vendas: number,
  taxa_conversao: number
}
```

---

### 4. Chamadas (Telefonia)

#### `GET /chamadas/vendedor`
**Descrição:** Métricas de telefonia por vendedor

**Query Parameters:**
```typescript
{
  data_inicio: string,
  data_fim: string,
  vendedor?: string
}
```

**Response:**
```typescript
{
  metricas: {
    total_discagens: number,
    total_atendidas: number,
    total_efetivas: number,
    taxa_atendimento: number,
    taxa_efetividade: number,
    taxa_conversao_geral: number,
    tmd_atendidas: number,
    tmd_efetivas: number
  },
  evolucao_diaria: EvoluçãoDia[],
  top_horarios: TopHorario[],
  ligacoes: Chamada[]
}

interface EvoluçãoDia {
  data: string,
  vendedor: string,
  discagens: number
}

interface TopHorario {
  hora: number,
  efetivas: number
}

interface Chamada {
  name: string,
  ramal: number,
  atendente: string,
  atendido_em: string,
  duration: number,
  duration_minutos: number,
  causa_desligamento: string,
  tipo_ligacao: string,
  efetiva: boolean,
  url_gravacao?: string
}
```

#### `GET /chamadas/metricas-vendedores`
**Descrição:** Comparação de métricas entre vendedores

**Response:**
```typescript
{
  vendedores: VendedorChamadas[]
}

interface VendedorChamadas {
  vendedor: string,
  ramal: number,
  discagens: number,
  atendidas: number,
  efetivas: number,
  taxa_atendimento: number,
  taxa_efetividade: number
}
```

---

### 5. Marketing

#### `GET /marketing/resumo`
**Descrição:** Resumo de métricas de marketing

**Query Parameters:**
```typescript
{
  data_inicio: string,
  data_fim: string
}
```

**Response:**
```typescript
{
  campanhas_ativas: number,
  fontes_ativas: number,
  pct_rastreamento: number,
  total_vendas: number,
  taxa_conversao_geral: number
}
```

#### `GET /marketing/campanhas`
**Descrição:** Métricas detalhadas por campanha

**Query Parameters:**
```typescript
{
  data_inicio: string,
  data_fim: string,
  dimensao: 'campaign' | 'source' | 'medium'
}
```

**Response:**
```typescript
{
  campanhas: CampaignMetrics[]
}

interface CampaignMetrics {
  name: string,
  total_leads: number,
  demos_agendadas: number,
  demos_realizadas: number,
  desqualificados: number,
  vendas: number,
  noshows: number,
  taxa_agendamento: number,
  taxa_conversao_lead_venda: number,
  taxa_desqualificacao: number
}
```

#### `GET /marketing/insights`
**Descrição:** Insights automáticos de marketing

**Response:**
```typescript
{
  insights: MarketingInsight[]
}

interface MarketingInsight {
  type: 'positive' | 'warning' | 'critical' | 'info' | 'opportunity',
  title: string,
  description: string,
  metric_value?: number,
  metric_label?: string,
  campaign?: string,
  recommendation?: string,
  priority: 1 | 2 | 3,
  icon: string
}
```

#### `GET /marketing/comparacao`
**Descrição:** Comparação entre dois períodos

**Query Parameters:**
```typescript
{
  periodo_atual_inicio: string,
  periodo_atual_fim: string,
  periodo_anterior_inicio: string,
  periodo_anterior_fim: string
}
```

**Response:**
```typescript
{
  periodo_atual: PeriodMetrics,
  periodo_anterior: PeriodMetrics,
  variacoes: {
    leads: { absoluta: number, percentual: number },
    vendas: { absoluta: number, percentual: number },
    taxa_conversao: { absoluta: number, percentual: number }
  }
}

interface PeriodMetrics {
  total_leads: number,
  total_vendas: number,
  taxa_conversao: number
}
```

#### `GET /marketing/funil`
**Descrição:** Funil de conversão por campanha

**Query Parameters:**
```typescript
{
  data_inicio: string,
  data_fim: string,
  dimensao: 'campaign' | 'source' | 'medium',
  campanha?: string
}
```

**Response:**
```typescript
{
  funil: {
    leads: number,
    agendamentos: number,
    demos: number,
    vendas: number
  },
  taxas: {
    lead_agendamento: number,
    agendamento_demo: number,
    demo_venda: number,
    lead_venda: number
  }
}
```

---

### 6. Analytics

#### `GET /analytics/tempo-por-etapa`
**Descrição:** Tempo médio em cada etapa do funil

**Response:**
```typescript
{
  etapas: Etapa[]
}

interface Etapa {
  status_id: number,
  status: string,
  tempo_medio_horas: number,
  tempo_medio_dias: number
}
```

#### `GET /analytics/resumo-diario`
**Descrição:** Métricas agregadas por dia

**Query Parameters:**
```typescript
{
  data_inicio: string,
  data_fim: string,
  vendedores?: string[],
  pipelines?: string[]
}
```

**Response:**
```typescript
{
  resumo_por_dia: ResumoDia[],
  totais: ResumoDia
}

interface ResumoDia {
  data: string,
  dia_semana: string,
  novos_leads: number,
  agendamentos: number,
  demos_dia: number,
  noshows: number,
  demos_realizadas: number,
  percentual_demos: number,
  percentual_noshow: number
}
```

---

### 7. Insights (IA)

#### `POST /insights/gerar`
**Descrição:** Gerar insights com IA (Google Gemini)

**Request Body:**
```typescript
{
  metricas_atual: Metricas,
  metricas_anterior: Metricas,
  periodo_descricao: string
}

interface Metricas {
  total_leads: number,
  leads_com_demo: number,
  pct_com_demo: number,
  demos_realizadas: number,
  noshow_count: number,
  leads_convertidos: number,
  taxa_conversao: number
}
```

**Response:**
```typescript
{
  insights: string,  // Markdown formatado
  gerado_em: string
}
```

#### `POST /insights/chat`
**Descrição:** Chat conversacional sobre dados

**Request Body:**
```typescript
{
  mensagem: string,
  contexto: {
    metricas_atual: Metricas,
    metricas_anterior: Metricas,
    periodo_descricao: string
  },
  historico: Message[]
}

interface Message {
  role: 'user' | 'assistant',
  content: string
}
```

**Response:**
```typescript
{
  resposta: string
}
```

---

### 8. Filtros & Configurações

#### `GET /config/vendedores`
**Descrição:** Lista de vendedores disponíveis

**Response:**
```typescript
{
  vendedores: string[]
}
```

#### `GET /config/pipelines`
**Descrição:** Lista de pipelines disponíveis

**Response:**
```typescript
{
  pipelines: string[]
}
```

#### `GET /config/status`
**Descrição:** Lista de status e suas categorias

**Response:**
```typescript
{
  status: Status[]
}

interface Status {
  id: number,
  nome: string,
  categoria: 'demo_completed' | 'funnel_closed' | 'other'
}
```

---

## 🔐 Segurança & Autenticação

### Fase 1 (MVP)
- Sem autenticação (uso interno)
- API Key básica via header

### Fase 2 (Produção)
- JWT Authentication
- Roles: Admin, Manager, Vendedor
- Permissões por módulo

### Configurações de Segurança
```python
# CORS
ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Dev
    "https://seu-dominio.com" # Prod
]

# Rate Limiting
RATE_LIMIT_PER_MINUTE = 60

# API Key (temporário)
API_KEY_HEADER = "X-API-Key"
```

---

## 🚀 Performance & Otimizações

### Cache Strategy

#### Redis (Recomendado)
```python
# Keys e TTLs
CACHE_KEYS = {
    'leads:{periodo}:{filtros}': 1800,          # 30 min
    'demos_hoje:{data}': 300,                   # 5 min
    'chamadas:{periodo}:{vendedor}': 1800,      # 30 min
    'vendas_resumo:{periodo}': 3600,            # 1 hora
    'marketing:{periodo}:{dimensao}': 3600,     # 1 hora
    'tempo_etapa': 3600,                        # 1 hora
    'insights_ia:{hash}': 3600,                 # 1 hora
}
```

### Database Optimizations

1. **Indexes**
   ```sql
   CREATE INDEX idx_leads_criado_em ON kommo_leads_statistics(criado_em);
   CREATE INDEX idx_leads_data_demo ON kommo_leads_statistics(data_demo);
   CREATE INDEX idx_leads_data_venda ON kommo_leads_statistics(data_venda);
   CREATE INDEX idx_leads_vendedor ON kommo_leads_statistics(vendedor);
   CREATE INDEX idx_leads_pipeline ON kommo_leads_statistics(pipeline);
   CREATE INDEX idx_leads_status ON kommo_leads_statistics(status);
   
   CREATE INDEX idx_chamadas_atendido_em ON kommo_chamadas(atendido_em);
   CREATE INDEX idx_chamadas_name ON kommo_chamadas(name);
   ```

2. **Materialized Views** (Considerar)
   - Resumo diário pré-calculado
   - Métricas de vendedor
   - Estatísticas de campanha

### API Response Compression
```python
# Gzip compression
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### Pagination
- Default: 50 itens por página
- Max: 500 itens por página

---

## 📱 Frontend - Requisitos de UX

### Layout

1. **Sidebar de Navegação**
   - Logo/Nome do sistema
   - Links para cada módulo
   - Indicador de módulo ativo

2. **Filtros Globais (Fixos no Topo)**
   - Período (data início/fim)
   - Vendedores (multi-select)
   - Pipelines (multi-select)
   - Botão "Aplicar Filtros"
   - Botão "Resetar"

3. **Content Area**
   - Breadcrumb
   - Título do módulo
   - Métricas em cards
   - Gráficos/Tabelas
   - Ações contextuais

### Responsividade
- Desktop: Layout de 3-4 colunas
- Tablet: 2 colunas
- Mobile: 1 coluna (stack vertical)

### Componentes Reutilizáveis

1. **MetricCard**
   ```typescript
   interface MetricCardProps {
     title: string;
     value: string | number;
     delta?: {
       value: string;
       type: 'positive' | 'negative' | 'neutral';
     };
     icon?: React.ReactNode;
     help?: string;
   }
   ```

2. **DataTable**
   ```typescript
   interface DataTableProps {
     columns: Column[];
     data: any[];
     pagination?: boolean;
     sortable?: boolean;
     searchable?: boolean;
     exportable?: boolean;
   }
   ```

3. **ChartCard**
   ```typescript
   interface ChartCardProps {
     title: string;
     type: 'line' | 'bar' | 'pie' | 'funnel';
     data: any;
     config?: ChartConfig;
   }
   ```

4. **InsightCard**
   ```typescript
   interface InsightCardProps {
     type: 'positive' | 'warning' | 'critical' | 'info' | 'opportunity';
     title: string;
     description: string;
     recommendation?: string;
     priority: 1 | 2 | 3;
   }
   ```

### Bibliotecas de Gráficos
- Recharts (Recomendado para React)
- Chart.js
- Apache ECharts
- Plotly.js (melhor compatibilidade com código atual)

### State Management
- React Context API (filtros globais)
- React Query / SWR (cache e fetching)
- Zustand (estado da aplicação)

---

## 🧪 Testes

### Backend (FastAPI)

```python
# Structure
tests/
├── test_api/
│   ├── test_leads.py
│   ├── test_demos.py
│   ├── test_vendas.py
│   └── test_chamadas.py
├── test_services/
│   ├── test_supabase.py
│   └── test_gemini.py
├── test_core/
│   ├── test_metrics.py
│   └── test_helpers.py
└── conftest.py
```

**Ferramentas:**
- pytest
- httpx (async client)
- pytest-asyncio
- faker (dados de teste)

### Frontend (React)

```
tests/
├── components/
├── pages/
├── hooks/
└── utils/
```

**Ferramentas:**
- Jest
- React Testing Library
- MSW (Mock Service Worker)

### Coverage Target
- Backend: > 80%
- Frontend: > 70%

---

## 📦 Deploy

### Backend (FastAPI)

**Opções:**
1. **Vercel** (atual)
   - Serverless functions
   - Cold start issues

2. **Railway** (Recomendado)
   - Sempre on
   - Suporte a Redis
   - Fácil deploy

3. **AWS ECS / Fargate**
   - Produção escalável
   - Mais complexo

4. **DigitalOcean App Platform**
   - Simples e barato

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend (React/Next.js)

**Opções:**
1. **Vercel** (Recomendado para Next.js)
2. **Netlify**
3. **AWS Amplify**
4. **Cloudflare Pages**

### Variáveis de Ambiente

**Backend:**
```env
# Supabase
SUPABASE_URL=https://...
SUPABASE_KEY=...

# Gemini
GEMINI_API_KEY=...

# Redis (opcional)
REDIS_URL=redis://...

# Config
ENVIRONMENT=production
API_KEY=...
ALLOWED_ORIGINS=https://...
```

**Frontend:**
```env
NEXT_PUBLIC_API_URL=https://api.seu-dominio.com
```

---

## 📈 Roadmap de Migração

### Fase 1: Setup & Infraestrutura (1-2 semanas)
- [ ] Configurar projeto FastAPI
- [ ] Configurar estrutura de pastas
- [ ] Setup banco de dados (conexões, RPCs)
- [ ] Configurar Redis (cache)
- [ ] Setup ambiente de desenvolvimento

### Fase 2: API Core (2-3 semanas)
- [ ] Implementar modelos Pydantic
- [ ] Implementar serviços Supabase
- [ ] Implementar endpoints de leads
- [ ] Implementar endpoints de demos
- [ ] Implementar endpoints de vendas
- [ ] Implementar endpoints de chamadas
- [ ] Testes unitários dos serviços

### Fase 3: Analytics & Marketing (1-2 semanas)
- [ ] Implementar endpoints de analytics
- [ ] Implementar endpoints de marketing
- [ ] Implementar cálculos de métricas
- [ ] Implementar análise de campanhas
- [ ] Testes de integração

### Fase 4: IA & Insights (1 semana)
- [ ] Migrar integração com Gemini
- [ ] Implementar geração de insights
- [ ] Implementar chat conversacional
- [ ] Cache de respostas IA

### Fase 5: Frontend Base (2-3 semanas)
- [ ] Setup React/Next.js
- [ ] Criar componentes base (cards, tables, charts)
- [ ] Implementar filtros globais
- [ ] Implementar layout e navegação
- [ ] Setup React Query / SWR

### Fase 6: Módulos Frontend (3-4 semanas)
- [ ] Módulo: Leads com Atenção
- [ ] Módulo: Insights IA
- [ ] Módulo: Demos de Hoje
- [ ] Módulo: Resumo Diário
- [ ] Módulo: Detalhes dos Leads
- [ ] Módulo: Tempo por Etapa
- [ ] Módulo: Produtividade do Vendedor
- [ ] Módulo: Mural de Vendas
- [ ] Módulo: Demos Realizadas
- [ ] Módulo: Marketing Analytics

### Fase 7: Polish & Otimizações (1-2 semanas)
- [ ] Otimizações de performance
- [ ] Ajustes de UX/UI
- [ ] Testes E2E
- [ ] Documentação API (Swagger)
- [ ] Documentação do usuário

### Fase 8: Deploy & Monitoramento (1 semana)
- [ ] Deploy backend (Railway/AWS)
- [ ] Deploy frontend (Vercel)
- [ ] Setup monitoramento (Sentry)
- [ ] Setup analytics (Posthog/Mixpanel)
- [ ] Treinamento dos usuários

**Tempo Total Estimado:** 12-18 semanas (3-4 meses)

---

## 🔧 Ferramentas & Dependências

### Backend (requirements.txt)

```txt
# FastAPI & Web
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Database
supabase==2.3.0
postgrest==0.13.0

# Redis (Cache)
redis==5.0.1
aioredis==2.0.1

# IA
google-generativeai==0.3.2

# Data Processing
pandas==2.1.4
numpy==1.26.2

# Utils
python-dotenv==1.0.0
python-multipart==0.0.6
httpx==0.26.0

# Dev & Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.26.0
faker==21.0.0

# Monitoring
sentry-sdk==1.39.2
```

### Frontend (package.json)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "next": "^14.0.0",
    "@tanstack/react-query": "^5.0.0",
    "axios": "^1.6.0",
    "recharts": "^2.10.0",
    "date-fns": "^3.0.0",
    "zustand": "^4.4.0",
    "tailwindcss": "^3.4.0",
    "lucide-react": "^0.300.0",
    "@radix-ui/react-select": "^2.0.0",
    "@radix-ui/react-tabs": "^1.0.0",
    "react-hook-form": "^7.49.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "@types/react": "^18.2.0",
    "@types/node": "^20.10.0",
    "eslint": "^8.55.0",
    "jest": "^29.7.0",
    "@testing-library/react": "^14.1.0"
  }
}
```

---

## 📊 Métricas de Sucesso

### Performance
- [ ] Tempo de resposta API < 200ms (P95)
- [ ] Tempo de carregamento inicial < 2s
- [ ] Cache hit rate > 70%

### Usabilidade
- [ ] Redução de 50% no tempo para gerar relatórios
- [ ] 90% de adoção pelos vendedores
- [ ] < 3 cliques para ações principais

### Técnicas
- [ ] 95% uptime
- [ ] Cobertura de testes > 80%
- [ ] Zero bugs críticos em produção

---

## 📞 Suporte & Manutenção

### Documentação
- [ ] API: Swagger/OpenAPI
- [ ] Frontend: Storybook
- [ ] Guia do usuário
- [ ] FAQ

### Monitoramento
- **Logs**: Structured logging (JSON)
- **Errors**: Sentry
- **Performance**: DataDog / New Relic
- **Usage**: Posthog / Mixpanel

### Backup
- Supabase: Backup automático diário
- Redis: Persist to disk

---

## 🎓 Considerações Finais

### Vantagens da Nova Arquitetura
1. **Escalabilidade**: Backend e frontend podem escalar independentemente
2. **Performance**: Cache otimizado, queries eficientes
3. **Manutenibilidade**: Código modular e testável
4. **Flexibilidade**: Fácil adicionar novos módulos/integrações
5. **DX**: Melhor experiência de desenvolvimento

### Desafios & Mitigações
1. **Complexidade aumentada**
   - Mitigation: Documentação clara, arquitetura bem definida

2. **Tempo de migração**
   - Mitigation: Migração incremental, manter sistema antigo até completar

3. **Curva de aprendizado**
   - Mitigation: Treinamento da equipe, pair programming

4. **Custo de infraestrutura**
   - Mitigation: Começar com tier gratuito/barato, escalar conforme necessário

---

## 📝 Glossário

- **Lead**: Cliente potencial cadastrado no CRM
- **Demo**: Demonstração/test-drive do produto
- **No-show**: Cliente que agendou demo mas não compareceu
- **Pipeline**: Funil de vendas
- **UTM**: Parâmetros de rastreamento de marketing (utm_source, utm_campaign, etc)
- **Discagem**: Tentativa de ligação
- **Ligação Efetiva**: Chamada atendida com duração > 50s
- **TMD**: Tempo Médio de Duração
- **RPC**: Remote Procedure Call (stored procedure do banco)
- **TTL**: Time To Live (tempo de cache)

---

**Versão:** 1.0  
**Data:** 18 de dezembro de 2025  
**Autor:** Documentação gerada pela análise do codebase existente

---

## 🔄 Changelog

### v1.0 (18/12/2025)
- Documentação inicial completa
- Análise de todos os módulos do sistema
- Especificação de endpoints API
- Arquitetura proposta
- Roadmap de migração
