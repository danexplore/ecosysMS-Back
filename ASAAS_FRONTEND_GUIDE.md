# Guia de Integração - Asaas API Proxy (Frontend)

Este guia explica como consumir a API do Asaas através do proxy Python no frontend.

## 📋 Sumário

- [Configuração Inicial](#configuração-inicial)
- [Rotas Disponíveis](#rotas-disponíveis)
- [Exemplos de Implementação](#exemplos-de-implementação)
- [React Query](#react-query)
- [Tratamento de Erros](#tratamento-de-erros)

---

## Configuração Inicial

### URL Base da API

```typescript
// Para desenvolvimento local
const ASAAS_API_BASE = 'http://127.0.0.1:8000/api/v1';

// Para produção (Vercel ou seu domínio)
// const ASAAS_API_BASE = 'https://seu-dominio.com/api/v1';
```

### Importante ⚠️

- **Não é necessário** configurar `ASAAS_API_KEY` no frontend
- A API key fica segura no backend (arquivo `.env`)
- Todas as requisições passam pelo proxy Python
- CORS já está configurado no backend

---

## Rotas Disponíveis

### 🧑 Clientes

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/v1/asaas/customers` | Lista todos os clientes |
| `GET` | `/api/v1/asaas/customers/{id}` | Busca cliente por ID |
| `POST` | `/api/v1/asaas/customers` | Cria novo cliente |
| `PUT` | `/api/v1/asaas/customers/{id}` | Atualiza cliente |
| `DELETE` | `/api/v1/asaas/customers/{id}` | Remove cliente |
| `GET` | `/api/v1/asaas/customers/{id}/payments` | Pagamentos do cliente |
| `GET` | `/api/v1/asaas/customers/{id}/subscriptions` | Assinaturas do cliente |

**Query Parameters (Listar Clientes):**
- `offset`: número (default: 0)
- `limit`: número (default: 10, max: 100)
- `name`: string (filtro por nome)
- `email`: string (filtro por email)
- `cpfCnpj`: string (filtro por documento)

**Exemplo de Body (Criar Cliente):**
```json
{
  "name": "João Silva",
  "cpfCnpj": "12345678901",
  "email": "joao@email.com",
  "phone": "11999999999",
  "mobilePhone": "11888888888",
  "address": "Rua Exemplo",
  "addressNumber": "123",
  "province": "Centro",
  "postalCode": "01234567"
}
```

---

### 💳 Cobranças (Payments)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/v1/asaas/payments` | Lista todas as cobranças |
| `GET` | `/api/v1/asaas/payments/{id}` | Busca cobrança por ID |
| `POST` | `/api/v1/asaas/payments` | Cria nova cobrança |
| `PUT` | `/api/v1/asaas/payments/{id}` | Atualiza cobrança |
| `DELETE` | `/api/v1/asaas/payments/{id}` | Remove cobrança |
| `GET` | `/api/v1/asaas/payments/{id}/pixQrCode` | QR Code Pix da cobrança |
| `GET` | `/api/v1/asaas/payments/{id}/identificationField` | Linha digitável do boleto |
| `POST` | `/api/v1/asaas/payments/{id}/refund` | Estorna cobrança |

**Query Parameters (Listar Cobranças):**
- `offset`: número
- `limit`: número
- `customer`: string (ID do cliente)
- `status`: PENDING | RECEIVED | CONFIRMED | OVERDUE | REFUNDED | CANCELLED
- `billingType`: BOLETO | CREDIT_CARD | PIX | DEBIT_CARD
- `dateCreated_ge`: YYYY-MM-DD (data inicial)
- `dateCreated_le`: YYYY-MM-DD (data final)
- `dueDate_ge`: YYYY-MM-DD (vencimento inicial)
- `dueDate_le`: YYYY-MM-DD (vencimento final)

**Exemplo de Body (Criar Cobrança):**
```json
{
  "customer": "cus_000012345678",
  "billingType": "PIX",
  "value": 100.50,
  "dueDate": "2026-01-15",
  "description": "Mensalidade Janeiro/2026",
  "externalReference": "REF-001"
}
```

**Tipos de Cobrança (`billingType`):**
- `BOLETO`: Boleto bancário
- `CREDIT_CARD`: Cartão de crédito
- `PIX`: Pagamento via Pix
- `DEBIT_CARD`: Cartão de débito (não disponível em sandbox)

---

### 📅 Assinaturas (Subscriptions)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/v1/asaas/subscriptions` | Lista todas as assinaturas |
| `GET` | `/api/v1/asaas/subscriptions/{id}` | Busca assinatura por ID |
| `POST` | `/api/v1/asaas/subscriptions` | Cria nova assinatura |
| `PUT` | `/api/v1/asaas/subscriptions/{id}` | Atualiza assinatura |
| `DELETE` | `/api/v1/asaas/subscriptions/{id}` | Remove assinatura |
| `GET` | `/api/v1/asaas/subscriptions/{id}/payments` | Cobranças da assinatura |

**Query Parameters (Listar Assinaturas):**
- `offset`: número
- `limit`: número
- `customer`: string (ID do cliente)
- `status`: ACTIVE | INACTIVE | EXPIRED

**Exemplo de Body (Criar Assinatura):**
```json
{
  "customer": "cus_000012345678",
  "billingType": "BOLETO",
  "value": 299.90,
  "nextDueDate": "2026-02-01",
  "cycle": "MONTHLY",
  "description": "Plano Premium",
  "maxPayments": 12
}
```

**Ciclos de Cobrança (`cycle`):**
- `WEEKLY`: Semanal
- `BIWEEKLY`: Quinzenal
- `MONTHLY`: Mensal
- `QUARTERLY`: Trimestral
- `SEMIANNUALLY`: Semestral
- `YEARLY`: Anual

---

### 📊 Dashboard & Métricas

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/v1/asaas/dashboard` | Dashboard completo (MRR, pagamentos, churn) |
| `GET` | `/api/v1/asaas/dashboard/mrr` | MRR (Monthly Recurring Revenue) |
| `GET` | `/api/v1/asaas/dashboard/payments` | Resumo de pagamentos por status |
| `GET` | `/api/v1/asaas/dashboard/overdue` | Lista de inadimplentes |
| `GET` | `/api/v1/asaas/dashboard/churn` | Taxa de churn |
| `GET` | `/api/v1/asaas/dashboard/revenue` | Receita total por status |
| `GET` | `/api/v1/asaas/subscriptions/metrics` | Métricas de assinaturas (total, ativas, inativas, MRR) |
| `GET` | `/api/v1/asaas/customers/stats` | Estatísticas de clientes |

**Estrutura de Resposta - Métricas de Assinaturas (`/subscriptions/metrics`):**

Este endpoint retorna um resumo completo das assinaturas, incluindo o MRR calculado automaticamente:

```typescript
interface SubscriptionMetrics {
  total: number;        // Total de assinaturas (ativas + inativas + expiradas)
  active: number;       // Número de assinaturas ativas
  inactive: number;     // Número de assinaturas inativas
  expired: number;      // Número de assinaturas expiradas
  mrr: number;         // Monthly Recurring Revenue (receita recorrente mensal)
}
```

**Exemplo de Resposta:**
```json
{
  "total": 53,
  "active": 50,
  "inactive": 3,
  "expired": 0,
  "mrr": 15000.00
}
```

**Como o MRR é calculado:**

O backend converte automaticamente o valor de cada assinatura ativa para mensal, baseado no ciclo de cobrança:

| Ciclo | Conversão |
|-------|-----------|
| `WEEKLY` | valor × 4 |
| `BIWEEKLY` | valor × 2 |
| `MONTHLY` | valor × 1 |
| `QUARTERLY` | valor ÷ 3 |
| `SEMIANNUALLY` | valor ÷ 6 |
| `YEARLY` | valor ÷ 12 |

**Exemplo de Cálculo:**
- Assinatura 1: R$ 100,00 (MONTHLY) = R$ 100,00 MRR
- Assinatura 2: R$ 50,00 (WEEKLY) = R$ 200,00 MRR (50 × 4)
- Assinatura 3: R$ 300,00 (YEARLY) = R$ 25,00 MRR (300 ÷ 12)
- **Total MRR**: R$ 325,00

---

**Exemplo de Resposta (Dashboard Completo):**
```json
{
  "mrr": {
    "current": 15000.00,
    "active_subscriptions": 50,
    "avg_ticket": 300.00
  },
  "payments": {
    "total_count": 150,
    "received_count": 100,
    "pending_count": 30,
    "overdue_count": 20,
    "received_value": 30000.00,
    "pending_value": 9000.00,
    "overdue_value": 6000.00
  },
  "overdue": [
    {
      "customer_id": "cus_123",
      "customer_name": "Cliente Exemplo",
      "total_overdue": 1500.00,
      "overdue_payments": 3,
      "oldest_due_date": "2025-12-01"
    }
  ],
  "churn": {
    "churn_rate": 5.5,
    "canceled_subscriptions": 3,
    "active_subscriptions": 50
  }
}
```

---

## Exemplos de Implementação

### Serviço TypeScript Completo

```typescript
// services/asaasApi.ts
const ASAAS_API_BASE = 'http://127.0.0.1:8000/api/v1';

interface PaginationParams {
  offset?: number;
  limit?: number;
}

interface CustomerCreateData {
  name: string;
  cpfCnpj: string;
  email?: string;
  phone?: string;
  mobilePhone?: string;
  address?: string;
  addressNumber?: string;
  province?: string;
  postalCode?: string;
}

interface PaymentCreateData {
  customer: string;
  billingType: 'BOLETO' | 'CREDIT_CARD' | 'PIX';
  value: number;
  dueDate: string;
  description?: string;
}

interface SubscriptionCreateData {
  customer: string;
  billingType: 'BOLETO' | 'CREDIT_CARD' | 'PIX';
  value: number;
  nextDueDate: string;
  cycle: 'MONTHLY' | 'WEEKLY' | 'YEARLY';
  description?: string;
  maxPayments?: number;
}

export const asaasApi = {
  // ===== CLIENTES =====
  customers: {
    list: async (params?: PaginationParams & { name?: string; email?: string }) => {
      const query = new URLSearchParams(params as any);
      const response = await fetch(`${ASAAS_API_BASE}/asaas/customers?${query}`);
      return response.json();
    },

    get: async (id: string) => {
      const response = await fetch(`${ASAAS_API_BASE}/asaas/customers/${id}`);
      return response.json();
    },

    create: async (data: CustomerCreateData) => {
      const response = await fetch(`${ASAAS_API_BASE}/asaas/customers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      return response.json();
    },

    update: async (id: string, data: Partial<CustomerCreateData>) => {
      const response = await fetch(`${ASAAS_API_BASE}/asaas/customers/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      return response.json();
    },

    delete: async (id: string) => {
      const response = await fetch(`${ASAAS_API_BASE}/asaas/customers/${id}`, {
        method: 'DELETE',
      });
      return response.json();
    },

    payments: async (customerId: string) => {
      const response = await fetch(`${ASAAS_API_BASE}/asaas/customers/${customerId}/payments`);
      return response.json();
    },

    subscriptions: async (customerId: string) => {
      const response = await fetch(`${ASAAS_API_BASE}/asaas/customers/${customerId}/subscriptions`);
      return response.json();
    },
  },

  // ===== PAGAMENTOS =====
  payments: {
    list: async (params?: PaginationParams & { status?: string; customer?: string }) => {
      const query = new URLSearchParams(params as any);
      const response = await fetch(`${ASAAS_API_BASE}/asaas/payments?${query}`);
      return response.json();
    },

    get: async (id: string) => {
      const response = await fetch(`${ASAAS_API_BASE}/asaas/payments/${id}`);
      return response.json();
    },

    create: async (data: PaymentCreateData) => {
      const response = await fetch(`${ASAAS_API_BASE}/asaas/payments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      return response.json();
    },

    getPixQrCode: async (id: string) => {
      const response = await fetch(`${ASAAS_API_BASE}/asaas/payments/${id}/pixQrCode`);
      return response.json();
    },

    refund: async (id: string, value?: number) => {
      const response = await fetch(`${ASAAS_API_BASE}/asaas/payments/${id}/refund`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value }),
      });
      return response.json();
    },
  },

  // ===== ASSINATURAS =====
  subscriptions: {
    list: async (params?: PaginationParams & { status?: string; customer?: string }) => {
      const query = new URLSearchParams(params as any);
      const response = await fetch(`${ASAAS_API_BASE}/asaas/subscriptions?${query}`);
      return response.json();
    },

    get: async (id: string) => {
      const response = await fetch(`${ASAAS_API_BASE}/asaas/subscriptions/${id}`);
      return response.json();
    },

    create: async (data: SubscriptionCreateData) => {
      const response = await fetch(`${ASAAS_API_BASE}/asaas/subscriptions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      return response.json();
    },

    metrics: async () => {
      const response = await fetch(`${ASAAS_API_BASE}/asaas/subscriptions/metrics`);
      return response.json();
    },
  },

  // ===== DASHBOARD =====
  dashboard: {
    overview: async () => {
      const response = await fetch(`${ASAAS_API_BASE}/asaas/dashboard`);
      return response.json();
    },

    mrr: async () => {
      const response = await fetch(`${ASAAS_API_BASE}/asaas/dashboard/mrr`);
      return response.json();
    },

    payments: async () => {
      const response = await fetch(`${ASAAS_API_BASE}/asaas/dashboard/payments`);
      return response.json();
    },

    overdue: async () => {
      const response = await fetch(`${ASAAS_API_BASE}/asaas/dashboard/overdue`);
      return response.json();
    },

    churn: async () => {
      const response = await fetch(`${ASAAS_API_BASE}/asaas/dashboard/churn`);
      return response.json();
    },

    revenue: async () => {
      const response = await fetch(`${ASAAS_API_BASE}/asaas/dashboard/revenue`);
      return response.json();
    },
  },
};
```

---

## React Query

### Hooks Personalizados

```typescript
// hooks/useAsaas.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { asaasApi } from '../services/asaasApi';

// ===== DASHBOARD =====
export function useDashboard() {
  return useQuery({
    queryKey: ['asaas', 'dashboard'],
    queryFn: asaasApi.dashboard.overview,
    staleTime: 1000 * 60 * 5, // 5 minutos
  });
}

export function useSubscriptionMetrics() {
  return useQuery({
    queryKey: ['asaas', 'subscriptions', 'metrics'],
    queryFn: asaasApi.subscriptions.metrics,
    staleTime: 1000 * 60 * 5,
  });
}

export function useMRR() {
  return useQuery({
    queryKey: ['asaas', 'dashboard', 'mrr'],
    queryFn: asaasApi.dashboard.mrr,
    staleTime: 1000 * 60 * 5,
  });
}

// ===== CLIENTES =====
export function useCustomers(params?: { offset?: number; limit?: number }) {
  return useQuery({
    queryKey: ['asaas', 'customers', params],
    queryFn: () => asaasApi.customers.list(params),
  });
}

export function useCustomer(id: string) {
  return useQuery({
    queryKey: ['asaas', 'customers', id],
    queryFn: () => asaasApi.customers.get(id),
    enabled: !!id,
  });
}

export function useCreateCustomer() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: asaasApi.customers.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['asaas', 'customers'] });
    },
  });
}

// ===== PAGAMENTOS =====
export function usePayments(params?: { status?: string; customer?: string }) {
  return useQuery({
    queryKey: ['asaas', 'payments', params],
    queryFn: () => asaasApi.payments.list(params),
  });
}

export function useCreatePayment() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: asaasApi.payments.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['asaas', 'payments'] });
      queryClient.invalidateQueries({ queryKey: ['asaas', 'dashboard'] });
    },
  });
}

// ===== ASSINATURAS =====
export function useSubscriptions(params?: { status?: string }) {
  return useQuery({
    queryKey: ['asaas', 'subscriptions', params],
    queryFn: () => asaasApi.subscriptions.list(params),
  });
}

export function useCreateSubscription() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: asaasApi.subscriptions.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['asaas', 'subscriptions'] });
      queryClient.invalidateQueries({ queryKey: ['asaas', 'dashboard'] });
    },
  });
}
```

### Uso em Componentes

```tsx
// components/Dashboard.tsx
import { useDashboard, useMRR, useSubscriptionMetrics } from '../hooks/useAsaas';

export function Dashboard() {
  const { data: dashboard, isLoading } = useDashboard();
  const { data: mrr } = useMRR();
  const { data: metrics } = useSubscriptionMetrics();

  if (isLoading) return <div>Carregando...</div>;

  return (
    <div>
      <h1>Dashboard</h1>
      
      <div className="metrics">
        <div className="card">
          <h2>MRR</h2>
          <p>R$ {mrr?.current?.toFixed(2)}</p>
          <small>{mrr?.active_subscriptions} assinaturas ativas</small>
        </div>

        <div className="card">
          <h2>Pagamentos</h2>
          <p>Recebidos: {dashboard?.payments?.received_count}</p>
          <p>Pendentes: {dashboard?.payments?.pending_count}</p>
          <p>Vencidos: {dashboard?.payments?.overdue_count}</p>
        </div>

        <div className="card">
          <h2>Churn</h2>
          <p>{dashboard?.churn?.churn_rate?.toFixed(2)}%</p>
          <small>{dashboard?.churn?.canceled_subscriptions} cancelamentos</small>
        </div>
      </div>
    </div>
  );
}
```

```tsx
// components/CreatePayment.tsx
import { useCreatePayment } from '../hooks/useAsaas';

export function CreatePayment() {
  const createPayment = useCreatePayment();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);

    try {
      const result = await createPayment.mutateAsync({
        customer: formData.get('customer') as string,
        billingType: formData.get('billingType') as any,
        value: Number(formData.get('value')),
        dueDate: formData.get('dueDate') as string,
        description: formData.get('description') as string,
      });

      alert('Cobrança criada com sucesso!');
      console.log(result);
    } catch (error) {
      alert('Erro ao criar cobrança');
      console.error(error);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input name="customer" placeholder="ID do Cliente" required />
      
      <select name="billingType" required>
        <option value="">Selecione o tipo</option>
        <option value="BOLETO">Boleto</option>
        <option value="PIX">Pix</option>
        <option value="CREDIT_CARD">Cartão de Crédito</option>
      </select>

      <input name="value" type="number" step="0.01" placeholder="Valor" required />
      <input name="dueDate" type="date" required />
      <input name="description" placeholder="Descrição" />

      <button type="submit" disabled={createPayment.isPending}>
        {createPayment.isPending ? 'Criando...' : 'Criar Cobrança'}
      </button>
    </form>
  );
}
```

---

## Tratamento de Erros

### Estrutura de Resposta de Erro

Quando ocorre um erro, a API retorna:

```json
{
  "detail": {
    "message": "Descrição do erro",
    "code": "error_code"
  }
}
```

### Exemplo de Tratamento

```typescript
try {
  const customer = await asaasApi.customers.create({
    name: 'João Silva',
    cpfCnpj: '12345678901',
    email: 'joao@email.com',
  });
  
  console.log('Cliente criado:', customer);
} catch (error) {
  if (error instanceof Response) {
    const errorData = await error.json();
    console.error('Erro da API:', errorData.detail);
  } else {
    console.error('Erro desconhecido:', error);
  }
}
```

### Com React Query

```typescript
export function useCreateCustomer() {
  return useMutation({
    mutationFn: asaasApi.customers.create,
    onError: (error: any) => {
      console.error('Erro ao criar cliente:', error);
      // Exibir toast de erro, etc
    },
    onSuccess: (data) => {
      console.log('Cliente criado com sucesso:', data);
      // Exibir toast de sucesso, etc
    },
  });
}
```

---

## Rotas de Compatibilidade

O proxy suporta rotas com e sem o prefixo `/asaas/`:

```typescript
// Ambas as rotas funcionam:
GET /api/v1/asaas/customers/{id}      ✅ Recomendado
GET /api/v1/customers/{id}             ✅ Compatibilidade (legado)

GET /api/v1/asaas/subscriptions/metrics  ✅ Recomendado
GET /api/v1/subscriptions/metrics         ✅ Compatibilidade (legado)
```

**Recomendação:** Use sempre as rotas com `/asaas/` para deixar claro que são do Asaas.

---

## Verificação de Saúde

Para verificar se o proxy está funcionando:

```typescript
const response = await fetch('http://127.0.0.1:8000/api/v1/asaas/health');
const data = await response.json();
console.log(data);
// {
//   "status": "ok",
//   "timestamp": "2026-01-06T14:00:00",
//   "environment": "sandbox",
//   "asaas_url": "https://api-sandbox.asaas.com/v3",
//   "api_key_configured": true
// }
```

---

## Ambiente de Produção

Quando for para produção, certifique-se de:

1. **Mudar a URL base** para o domínio de produção
2. **Configurar variáveis de ambiente** no backend:
   ```env
   ASAAS_API_KEY="sua_chave_de_producao"
   ASAAS_SANDBOX=false
   ```
3. **Testar todas as integrações** antes de ir para produção

---

## Suporte e Documentação

- **Documentação oficial do Asaas:** https://docs.asaas.com/
- **Status da API:** https://status.asaas.com/
- **Sandbox Asaas:** https://sandbox.asaas.com/

---

**🚀 Pronto! Agora você pode integrar o Asaas no seu frontend de forma segura e eficiente.**
