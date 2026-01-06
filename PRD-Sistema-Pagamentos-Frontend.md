# PRD - Sistema de Pagamentos Frontend

## 1. Visão Geral

Sistema de gestão de pagamentos integrado com Asaas, permitindo gerenciamento completo de clientes, cobranças avulsas, assinaturas recorrentes e análise de métricas financeiras.

**Versão:** 1.0.0  
**Data:** Janeiro 2026  
**Responsável:** Equipe Frontend EcosysMS

---

## 2. Objetivos

- Fornecer interface intuitiva para gestão de pagamentos
- Permitir criação e acompanhamento de cobranças
- Gerenciar assinaturas recorrentes
- Visualizar métricas e KPIs financeiros
- Facilitar cadastro e sincronização de clientes

---

## 3. Estrutura de Navegação

### 3.1 Menu Sidebar

```
📁 Pagamentos (Expansível)
  ├─ 📊 Dashboard
  ├─ 👥 Clientes
  ├─ 💳 Cobranças
  ├─ 🔄 Assinaturas
  ├─ 🔗 Link de Pagamento
  ├─ 📦 Produtos/Planos
  └─ 🔄 Sincronização
```

**Ordem de prioridade:**
1. **Dashboard** - Visão geral e métricas principais
2. **Clientes** - Gestão de clientes cadastrados
3. **Cobranças** - Pagamentos avulsos e únicos
4. **Assinaturas** - Pagamentos recorrentes
5. **Link de Pagamento** - Geração rápida de links
6. **Produtos/Planos** - Catálogo de produtos
7. **Sincronização** - Importar dados do Asaas

---

## 4. Módulos e Funcionalidades

### 4.1 Dashboard 📊

#### Endpoint Base
```
GET /api/v1/asaas/dashboard
```

#### Dados Recebidos
```typescript
interface DashboardData {
  mrr: {
    current_mrr: number;           // MRR atual
    active_subscriptions: number;  // Assinaturas ativas
    growth_rate: number;           // Taxa de crescimento
  };
  
  payments: {
    total_received: number;        // Total recebido
    pending: number;               // Pendentes
    overdue: number;               // Vencidos
    confirmed_count: number;       // Quantidade confirmados
    pending_count: number;         // Quantidade pendentes
    overdue_count: number;         // Quantidade vencidos
  };
  
  customers: {
    total_customers: number;       // Total de clientes
    active_customers: number;      // Clientes ativos
    new_last_30_days: number;      // Novos últimos 30 dias
    overdue_customers: number;     // Clientes inadimplentes
  };
  
  churn: {
    churn_rate: number;            // Taxa de churn %
    canceled_subscriptions: number; // Assinaturas canceladas
    active_subscriptions: number;  // Assinaturas ativas
  };
}
```

#### Interface Recomendada

**Cards Principais (Grid 4 colunas)**
1. **MRR (Receita Recorrente)**
   - Valor em destaque
   - Badge com taxa de crescimento (verde/vermelho)
   - Quantidade de assinaturas ativas

2. **Pagamentos do Mês**
   - Total recebido
   - Mini gráfico de barras: Confirmados, Pendentes, Vencidos
   - Cores: Verde, Amarelo, Vermelho

3. **Clientes**
   - Total de clientes
   - Novos últimos 30 dias (badge verde)
   - Inadimplentes (badge vermelho)

4. **Churn Rate**
   - Percentual em destaque
   - Assinaturas canceladas vs ativas
   - Indicador visual de alerta se > 5%

**Gráficos Secundários**
- Receita por período (linha temporal)
- Top 5 clientes inadimplentes
- Distribuição de pagamentos por status (pizza)

---

### 4.2 Clientes 👥

#### Endpoints

**Listar Clientes**
```
GET /api/v1/asaas/customers?offset=0&limit=100&active=true
```

**Criar Cliente**
```
POST /api/v1/asaas/customers
```

**Detalhes do Cliente**
```
GET /api/v1/asaas/customers/{customer_id}
```

**Pagamentos do Cliente**
```
GET /api/v1/asaas/customers/{customer_id}/payments
```

**Assinaturas do Cliente**
```
GET /api/v1/asaas/customers/{customer_id}/subscriptions
```

**Estatísticas**
```
GET /api/v1/asaas/customers/stats
```

#### Modelos de Dados

**Cliente (Response)**
```typescript
interface Customer {
  id: string;
  asaas_id: string;
  name: string;
  email: string;
  cpf_cnpj: string;
  phone?: string;
  address?: {
    street?: string;
    number?: string;
    complement?: string;
    neighborhood?: string;
    city?: string;
    state?: string;
    postal_code?: string;
  };
  active: boolean;
  created_at: string;
  updated_at: string;
}
```

**Criar Cliente (Request)**
```typescript
interface CustomerCreate {
  name: string;                    // OBRIGATÓRIO
  email: string;                   // OBRIGATÓRIO
  cpf_cnpj: string;                // OBRIGATÓRIO (11 ou 14 dígitos)
  phone?: string;                  // Formato: (00) 00000-0000
  mobile_phone?: string;
  address?: string;
  address_number?: string;
  complement?: string;
  province?: string;
  postal_code?: string;
  external_reference?: string;
  notifications_disabled?: boolean;
  additional_emails?: string;
  municipal_inscription?: string;
  state_inscription?: string;
  observations?: string;
}
```

#### Interface Recomendada

**Página de Listagem**
- Tabela com paginação
- Colunas: Nome, CPF/CNPJ, Email, Telefone, Status, Ações
- Filtros: Status (Ativo/Inativo), Busca por nome/email/CPF
- Badge de status (Verde: Ativo, Cinza: Inativo)
- Ações rápidas: Ver detalhes, Editar, Criar cobrança, Criar assinatura

**Formulário de Cadastro**
- Seção 1: Dados Básicos (Nome, Email, CPF/CNPJ)
- Seção 2: Contato (Telefone, Celular)
- Seção 3: Endereço (Expansível/Opcional)
- Validação de CPF/CNPJ em tempo real
- Verificar se cliente já existe antes de criar

**Detalhes do Cliente**
- Abas: Informações, Pagamentos, Assinaturas
- Cards com métricas: Total pago, MRR, Status de pagamento
- Linha do tempo de transações

---

### 4.3 Cobranças 💳

#### Endpoints

**Listar Cobranças**
```
GET /api/v1/asaas/payments?offset=0&limit=100&status=PENDING&customer_id=xxx
```

**Criar Cobrança**
```
POST /api/v1/asaas/payments
```

**Detalhes da Cobrança**
```
GET /api/v1/asaas/payments/{payment_id}
```

**Link de Pagamento**
```
GET /api/v1/asaas/payments/{payment_id}/link
```

**Estornar Pagamento**
```
POST /api/v1/asaas/payments/{payment_id}/refund
```

#### Modelos de Dados

**Cobrança (Response)**
```typescript
interface Payment {
  id: string;
  asaas_id: string;
  cliente_id: string;
  value: number;
  status: 'PENDING' | 'RECEIVED' | 'CONFIRMED' | 'OVERDUE' | 'REFUNDED' | 'RECEIVED_IN_CASH' | 'REFUND_REQUESTED' | 'CHARGEBACK_REQUESTED' | 'CHARGEBACK_DISPUTE' | 'AWAITING_CHARGEBACK_REVERSAL' | 'DUNNING_REQUESTED' | 'DUNNING_RECEIVED' | 'AWAITING_RISK_ANALYSIS';
  due_date: string;              // YYYY-MM-DD
  payment_date?: string;
  invoice_url?: string;
  billing_type: 'BOLETO' | 'CREDIT_CARD' | 'PIX' | 'UNDEFINED';
  description?: string;
  created_at: string;
}
```

**Criar Cobrança (Request)**
```typescript
interface PaymentCreate {
  customer: string;              // ID do cliente (OBRIGATÓRIO)
  billing_type: 'BOLETO' | 'CREDIT_CARD' | 'PIX' | 'UNDEFINED'; // OBRIGATÓRIO
  value: number;                 // OBRIGATÓRIO (min: 5.00)
  due_date: string;              // OBRIGATÓRIO (YYYY-MM-DD)
  description?: string;
  external_reference?: string;
  installment_count?: number;    // Parcelas (se CREDIT_CARD)
  installment_value?: number;
  discount?: {
    value?: number;
    due_date_limit_days?: number;
    type?: 'FIXED' | 'PERCENTAGE';
  };
  interest?: {
    value: number;
    type?: 'PERCENTAGE';
  };
  fine?: {
    value: number;
    type?: 'FIXED' | 'PERCENTAGE';
  };
  postal_service?: boolean;
  split?: any[];
}
```

**Link de Pagamento (Response)**
```typescript
interface PaymentLink {
  invoice_url?: string;          // Link do boleto/fatura
  bank_slip_url?: string;        // URL específica do boleto
  pix_qr_code?: string;          // QR Code PIX (base64)
  pix_copy_paste?: string;       // Código PIX copia e cola
}
```

#### Interface Recomendada

**Página de Listagem**
- Tabela com paginação
- Colunas: Cliente, Valor, Vencimento, Status, Forma de Pagamento, Ações
- Filtros: Status, Cliente, Período, Forma de pagamento
- Badges coloridos por status:
  - 🟢 RECEIVED/CONFIRMED: Verde
  - 🟡 PENDING: Amarelo
  - 🔴 OVERDUE: Vermelho
  - 🔵 REFUNDED: Azul
- Ações: Ver detalhes, Copiar link, Estornar, Enviar lembrete

**Formulário de Criação**
- Etapa 1: Selecionar Cliente (autocomplete)
- Etapa 2: Valor e Vencimento
- Etapa 3: Forma de Pagamento
  - Boleto: Campo de vencimento
  - PIX: Vencimento e informações
  - Cartão: Número de parcelas
- Etapa 4: Opcionais (Descontos, Juros, Multa)
- Etapa 5: Confirmação e Geração

**Modal de Link de Pagamento**
- QR Code PIX (se PIX)
- Botão "Copiar código PIX"
- Link do boleto (se BOLETO)
- Botão "Copiar link"
- Botão "Enviar por email"
- Botão "Enviar por WhatsApp"

---

### 4.4 Assinaturas 🔄

#### Endpoints

**Listar Assinaturas**
```
GET /api/v1/asaas/subscriptions?offset=0&limit=100&status=ACTIVE&customer_id=xxx
```

**Criar Assinatura**
```
POST /api/v1/asaas/subscriptions
```

**Detalhes da Assinatura**
```
GET /api/v1/asaas/subscriptions/{subscription_id}
```

**Atualizar Assinatura**
```
PUT /api/v1/asaas/subscriptions/{subscription_id}
```

**Pausar Assinatura**
```
POST /api/v1/asaas/subscriptions/{subscription_id}/pause
```

**Reativar Assinatura**
```
POST /api/v1/asaas/subscriptions/{subscription_id}/resume
```

**Cancelar Assinatura**
```
DELETE /api/v1/asaas/subscriptions/{subscription_id}
```

**Métricas**
```
GET /api/v1/asaas/subscriptions/metrics
```

#### Modelos de Dados

**Assinatura (Response)**
```typescript
interface Subscription {
  id: string;
  asaas_id: string;
  cliente_id: string;
  product_id?: string;
  value: number;
  cycle: 'WEEKLY' | 'BIWEEKLY' | 'MONTHLY' | 'QUARTERLY' | 'SEMIANNUALLY' | 'YEARLY';
  status: 'ACTIVE' | 'INACTIVE' | 'EXPIRED';
  next_due_date?: string;        // YYYY-MM-DD
  billing_type: 'BOLETO' | 'CREDIT_CARD' | 'PIX' | 'UNDEFINED';
  description?: string;
  created_at: string;
}
```

**Criar Assinatura (Request)**
```typescript
interface SubscriptionCreate {
  customer: string;              // ID do cliente (OBRIGATÓRIO)
  billing_type: 'BOLETO' | 'CREDIT_CARD' | 'PIX' | 'UNDEFINED'; // OBRIGATÓRIO
  value: number;                 // OBRIGATÓRIO (min: 5.00)
  cycle: 'WEEKLY' | 'BIWEEKLY' | 'MONTHLY' | 'QUARTERLY' | 'SEMIANNUALLY' | 'YEARLY'; // OBRIGATÓRIO
  next_due_date: string;         // OBRIGATÓRIO (YYYY-MM-DD)
  description?: string;
  product_id?: string;
  discount?: {
    value: number;
    duration_type: 'REPEATS' | 'FOREVER';
    type: 'FIXED' | 'PERCENTAGE';
  };
  interest?: {
    value: number;
  };
  fine?: {
    value: number;
  };
  external_reference?: string;
}
```

**Métricas de Assinaturas**
```typescript
interface SubscriptionMetrics {
  mrr: {
    current_mrr: number;
    active_subscriptions: number;
    growth_rate: number;
  };
  churn: {
    overall_churn: number;
    churn_rate: number;
    canceled_subscriptions: number;
    active_subscriptions: number;
  };
}
```

#### Interface Recomendada

**Página de Listagem**
- Tabela com paginação
- Colunas: Cliente, Valor, Ciclo, Próximo Vencimento, Status, Ações
- Filtros: Status, Cliente, Ciclo
- Badges de status:
  - 🟢 ACTIVE: Verde
  - 🟡 INACTIVE: Amarelo
  - ⚫ EXPIRED: Cinza
- Ações: Ver detalhes, Pausar/Reativar, Editar, Cancelar

**Formulário de Criação**
- Etapa 1: Selecionar Cliente
- Etapa 2: Selecionar Produto/Plano (opcional) ou valor customizado
- Etapa 3: Ciclo de cobrança
  - Semanal, Quinzenal, Mensal, Trimestral, Semestral, Anual
- Etapa 4: Data do primeiro vencimento
- Etapa 5: Forma de pagamento
- Etapa 6: Descontos (opcional)
- Etapa 7: Confirmação

**Detalhes da Assinatura**
- Card com informações principais
- Linha do tempo de cobranças
- Gráfico de pagamentos (recebidos vs pendentes)
- Botões de ação: Pausar, Editar valor, Cancelar

**Modal de Métricas**
- MRR atual e evolução
- Taxa de churn
- Distribuição por ciclo (gráfico pizza)
- Top 5 assinaturas por valor

---

### 4.5 Link de Pagamento 🔗

#### Interface Recomendada

**Página Simplificada de Geração Rápida**

Formulário em uma única página para criar cobrança rápida e obter link imediatamente:

1. **Cliente**
   - Buscar cliente existente (autocomplete)
   - OU criar novo cliente rápido (modal)

2. **Detalhes do Pagamento**
   - Valor (destaque)
   - Descrição
   - Vencimento

3. **Forma de Pagamento**
   - Toggle buttons: PIX, Boleto, Cartão

4. **Botão de Gerar**
   - Ao clicar, cria a cobrança e exibe modal com:
     - QR Code (se PIX)
     - Link copiável
     - Botões de compartilhamento (WhatsApp, Email)

**Diferencial:** Fluxo otimizado para uso rápido, sem navegar por múltiplas páginas.

---

### 4.6 Produtos/Planos 📦

#### Endpoints

**Listar Produtos**
```
GET /api/v1/asaas/products?offset=0&limit=100&active=true
```

**Produtos Ativos**
```
GET /api/v1/asaas/products/active
```

**Criar Produto**
```
POST /api/v1/asaas/products
```

**Detalhes do Produto**
```
GET /api/v1/asaas/products/{product_id}
```

#### Modelos de Dados

**Produto (Response)**
```typescript
interface Product {
  id: string;
  name: string;
  price: number;
  cycle?: 'WEEKLY' | 'BIWEEKLY' | 'MONTHLY' | 'QUARTERLY' | 'SEMIANNUALLY' | 'YEARLY';
  active: boolean;
  created_at: string;
}
```

**Criar Produto (Request)**
```typescript
interface ProductCreate {
  name: string;                  // OBRIGATÓRIO
  price: number;                 // OBRIGATÓRIO (min: 5.00)
  cycle?: 'WEEKLY' | 'BIWEEKLY' | 'MONTHLY' | 'QUARTERLY' | 'SEMIANNUALLY' | 'YEARLY';
  description?: string;
  active?: boolean;              // default: true
}
```

#### Interface Recomendada

**Página de Listagem**
- Cards em grid (3 colunas)
- Cada card mostra:
  - Nome do produto
  - Preço em destaque
  - Ciclo de cobrança
  - Badge de status (Ativo/Inativo)
  - Botões: Editar, Ativar/Desativar, Excluir
- Filtro: Ativos, Inativos, Todos
- Botão flutuante: "+ Novo Produto"

**Formulário de Criação**
- Nome do produto
- Descrição
- Preço
- Ciclo de cobrança (opcional, para assinaturas)
- Toggle: Ativar/Desativar

---

### 4.7 Sincronização 🔄

#### Endpoints

**Sincronizar Clientes**
```
POST /api/v1/asaas/sync/customers?offset=0&limit=100
```

**Sincronizar Pagamentos**
```
POST /api/v1/asaas/sync/payments?offset=0&limit=100&status=RECEIVED
```

**Sincronizar Assinaturas**
```
POST /api/v1/asaas/sync/subscriptions?offset=0&limit=100&status=ACTIVE
```

**Sincronizar Tudo**
```
POST /api/v1/asaas/sync/all?limit=100
```

#### Modelos de Dados

**Resposta de Sincronização**
```typescript
interface SyncResponse {
  synced_count: number;
  failed_count: number;
  total_available: number;
  errors: Array<{
    id: string;
    error: string;
  }>;
}
```

**Resposta de Sincronização Completa**
```typescript
interface SyncAllResponse {
  customers: SyncResponse;
  payments: SyncResponse;
  subscriptions: SyncResponse;
  total_duration: number;        // segundos
  started_at: string;
  completed_at: string;
}
```

#### Interface Recomendada

**Página de Sincronização**

Cards para cada tipo de sincronização:

1. **Clientes**
   - Botão: "Sincronizar Clientes"
   - Mostra última sincronização
   - Progress bar durante sincronização
   - Resultado: X importados, Y falharam

2. **Pagamentos**
   - Botão: "Sincronizar Pagamentos"
   - Filtro de status (opcional)
   - Progress bar
   - Resultado com detalhes

3. **Assinaturas**
   - Botão: "Sincronizar Assinaturas"
   - Progress bar
   - Resultado com detalhes

4. **Sincronização Completa**
   - Botão destacado: "Sincronizar Tudo"
   - Warning: "Pode levar alguns minutos"
   - Progress bar geral
   - Log de progresso em tempo real
   - Resumo final com métricas

**Logs de Sincronização**
- Lista com histórico de sincronizações
- Data/hora, tipo, resultado, duração
- Filtros por tipo e resultado

---

## 5. Autenticação

**Todos os endpoints requerem Basic Auth**

```typescript
// Headers obrigatórios em todas as requisições
const headers = {
  'Authorization': 'Basic ' + btoa(username + ':' + password),
  'Content-Type': 'application/json'
}
```

**Tratamento de Erros**
```typescript
// Status 401 - Não autenticado
{
  "detail": "Credenciais inválidas"
}

// Status 500 - Erro interno
{
  "detail": "Mensagem de erro"
}
```

---

## 6. Paginação

**Padrão de Resposta Paginada**
```typescript
interface PaginatedResponse<T> {
  data: T[];
  total_count: number;
  offset: number;
  limit: number;
  has_more: boolean;
}
```

**Parâmetros de Query**
- `offset`: Número de registros a pular (default: 0)
- `limit`: Número de registros por página (default: 100, max: 500)

**Exemplo de Uso**
```typescript
// Página 1
GET /api/v1/asaas/customers?offset=0&limit=20

// Página 2
GET /api/v1/asaas/customers?offset=20&limit=20
```

---

## 7. Validações e Regras de Negócio

### 7.1 CPF/CNPJ
- Validar formato (11 ou 14 dígitos)
- Remover caracteres especiais antes de enviar
- Verificar se já existe antes de criar cliente

### 7.2 Valores
- Valor mínimo: R$ 5,00
- Usar 2 casas decimais
- Validar valores positivos

### 7.3 Datas
- Formato: YYYY-MM-DD
- Vencimento não pode ser data passada (exceto para registro histórico)
- Próximo vencimento de assinatura deve ser futuro

### 7.4 Status de Pagamento
```typescript
const statusColors = {
  'PENDING': '#FFA500',        // Laranja
  'RECEIVED': '#4CAF50',       // Verde
  'CONFIRMED': '#4CAF50',      // Verde
  'OVERDUE': '#F44336',        // Vermelho
  'REFUNDED': '#2196F3',       // Azul
  'RECEIVED_IN_CASH': '#4CAF50' // Verde
}

const statusLabels = {
  'PENDING': 'Pendente',
  'RECEIVED': 'Recebido',
  'CONFIRMED': 'Confirmado',
  'OVERDUE': 'Vencido',
  'REFUNDED': 'Estornado',
  'RECEIVED_IN_CASH': 'Recebido em Dinheiro'
}
```

---

## 8. Webhooks (Backend)

O backend já recebe webhooks do Asaas. O frontend deve estar preparado para atualizar dados em tempo real se implementar WebSocket ou polling.

**Eventos Suportados:**
- PAYMENT_RECEIVED
- PAYMENT_CONFIRMED
- PAYMENT_OVERDUE
- PAYMENT_REFUNDED
- PAYMENT_DELETED

**Recomendação:** Implementar polling a cada 30-60 segundos nas páginas de dashboard e listagens ativas.

---

## 9. Boas Práticas de UX

### 9.1 Loading States
- Skeleton loaders para tabelas e cards
- Progress bars para sincronizações
- Spinners para ações individuais

### 9.2 Feedback Visual
- Toasts para ações bem-sucedidas/falhas
- Modais de confirmação para ações destrutivas (excluir, cancelar)
- Badges coloridos para status

### 9.3 Responsividade
- Tabelas devem ter scroll horizontal em mobile
- Cards devem empilhar em telas pequenas
- Formulários devem ser single-column em mobile

### 9.4 Acessibilidade
- Labels claros em formulários
- Contraste adequado de cores
- Navegação por teclado
- ARIA labels para ícones

---

## 10. Exemplos de Fluxos Completos

### 10.1 Criar Cliente e Gerar Cobrança

```typescript
// 1. Criar cliente
const customer = await createCustomer({
  name: "João Silva",
  email: "joao@example.com",
  cpf_cnpj: "12345678901",
  phone: "(11) 98765-4321"
});

// 2. Criar cobrança
const payment = await createPayment({
  customer: customer.id,
  billing_type: "PIX",
  value: 100.00,
  due_date: "2026-02-01",
  description: "Mensalidade Janeiro"
});

// 3. Obter link
const link = await getPaymentLink(payment.id);

// 4. Copiar PIX ou enviar link
copyToClipboard(link.pix_copy_paste);
```

### 10.2 Criar Assinatura Mensal

```typescript
// 1. Selecionar cliente existente
const customer = await searchCustomer("João Silva");

// 2. Criar assinatura
const subscription = await createSubscription({
  customer: customer.id,
  billing_type: "CREDIT_CARD",
  value: 99.90,
  cycle: "MONTHLY",
  next_due_date: "2026-02-01",
  description: "Plano Premium Mensal"
});

// 3. Confirmar criação
showSuccessToast("Assinatura criada com sucesso!");
navigateTo(`/pagamentos/assinaturas/${subscription.id}`);
```

---

## 11. Métricas e Monitoramento

### 11.1 KPIs do Dashboard

**Principais Métricas:**
- MRR (Monthly Recurring Revenue)
- Churn Rate
- Total Recebido no Mês
- Clientes Inadimplentes
- Taxa de Conversão de Cobranças

**Visualizações Recomendadas:**
- Gráfico de linha: Evolução do MRR
- Gráfico de barras: Pagamentos por status
- Gráfico de pizza: Distribuição por forma de pagamento
- Lista: Top clientes inadimplentes

---

## 12. Considerações Técnicas

### 12.1 Tratamento de Erros

```typescript
try {
  const response = await apiCall();
  handleSuccess(response);
} catch (error) {
  if (error.status === 401) {
    // Redirecionar para login
    redirectToLogin();
  } else if (error.status === 400) {
    // Mostrar erros de validação
    showValidationErrors(error.detail);
  } else {
    // Erro genérico
    showErrorToast("Ocorreu um erro. Tente novamente.");
  }
}
```

### 12.2 Cache Local

Recomenda-se cachear:
- Lista de clientes (1 hora)
- Lista de produtos (1 dia)
- Métricas do dashboard (5 minutos)

Invalidar cache após:
- Criação de novos registros
- Edição de registros existentes
- Sincronização com Asaas

### 12.3 Performance

- Implementar lazy loading em listagens
- Usar debounce em buscas (300ms)
- Pré-carregar dados de navegação provável
- Otimizar imagens e ícones

---

## 13. Roadmap Futuro

### Fase 2 (Futuras Melhorias)
- [ ] Envio de lembretes por email/SMS
- [ ] Relatórios exportáveis (PDF/Excel)
- [ ] Análise preditiva de churn
- [ ] Integração com WhatsApp Business
- [ ] Automações de cobrança
- [ ] Split de pagamentos
- [ ] Cupons de desconto
- [ ] Gateway multi-fornecedor

---

## 14. Contatos e Suporte

**Equipe Backend:** [Inserir contato]  
**Documentação API:** `/docs` (Swagger)  
**Repositório:** https://github.com/danexplore/ecosysMS-Back

---

## 15. Anexos

### 15.1 Mapeamento de Status

| Status Asaas | Cor | Label PT-BR | Ação Permitida |
|-------------|-----|-------------|----------------|
| PENDING | 🟡 Amarelo | Pendente | Ver link, Cancelar |
| RECEIVED | 🟢 Verde | Recebido | Ver detalhes |
| CONFIRMED | 🟢 Verde | Confirmado | Estornar |
| OVERDUE | 🔴 Vermelho | Vencido | Enviar lembrete |
| REFUNDED | 🔵 Azul | Estornado | Ver histórico |

### 15.2 Ciclos de Cobrança

| Cycle | Label PT-BR | Descrição |
|-------|-------------|-----------|
| WEEKLY | Semanal | A cada 7 dias |
| BIWEEKLY | Quinzenal | A cada 14 dias |
| MONTHLY | Mensal | Todo mês no mesmo dia |
| QUARTERLY | Trimestral | A cada 3 meses |
| SEMIANNUALLY | Semestral | A cada 6 meses |
| YEARLY | Anual | Uma vez por ano |

### 15.3 Formas de Pagamento

| Billing Type | Label PT-BR | Ícone Sugerido |
|-------------|-------------|----------------|
| BOLETO | Boleto | 📄 |
| CREDIT_CARD | Cartão de Crédito | 💳 |
| PIX | PIX | ⚡ |
| UNDEFINED | Não Definido | ❓ |

---

**Fim do PRD**
