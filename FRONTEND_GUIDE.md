# Guia de Adaptação do Front-end para a Nova API de Vendas

## 📊 Novos Campos nos Endpoints

Os endpoints `/vendas/resumo` e `/vendas/ranking` agora retornam campos adicionais de **gamificação**:

```typescript
// Antes
interface ResumoVendedor {
  vendedor: { id: number; name: string; email: string };
  totalClientes: number;
  clientesAtivos: number;
  clientesInadimplentes: number;
  clientesCancelados: number;
  mrrAtivo: number;
  setupTotal: number;
  comissaoTotal: number;
}

// Depois ✨
interface ResumoVendedor {
  vendedor: { id: number; name: string; email: string };
  totalClientes: number;
  clientesAtivos: number;
  clientesInadimplentes: number;
  clientesCancelados: number;
  mrrAtivo: number;
  setupTotal: number;
  comissaoTotal: number;
  // NOVOS CAMPOS 👇
  novosMes: number;        // Vendas no mês (para gamificação)
  tier: 'bronze' | 'prata' | 'ouro';  // Medalha baseada nas vendas
  percentualMrr: number;   // % comissão MRR do tier (5, 10 ou 20)
  percentualSetup: number; // % comissão Setup do tier (15, 25 ou 40)
}
```

---

## 🏅 Lógica de Gamificação (Tiers)

O tier é calculado com base nas **vendas do mês** (não mais nos clientes ativos):

| Vendas no Mês | Tier | Cor Sugerida | Ícone |
|---------------|------|--------------|-------|
| 0 - 5 | `bronze` | `#CD7F32` | 🥉 |
| 6 - 9 | `prata` | `#C0C0C0` | 🥈 |
| 10+ | `ouro` | `#FFD700` | 🥇 |

---

## 🎨 Exemplo de Componente React

```tsx
// Badge de Tier
const TierBadge = ({ tier }: { tier: 'bronze' | 'prata' | 'ouro' }) => {
  const config = {
    bronze: { color: '#CD7F32', icon: '🥉', label: 'Bronze' },
    prata:  { color: '#C0C0C0', icon: '🥈', label: 'Prata' },
    ouro:   { color: '#FFD700', icon: '🥇', label: 'Ouro' }
  };
  
  const { color, icon, label } = config[tier];
  
  return (
    <span style={{ 
      backgroundColor: color, 
      padding: '4px 8px', 
      borderRadius: '4px',
      fontWeight: 'bold'
    }}>
      {icon} {label}
    </span>
  );
};

// Card do Vendedor
const VendedorCard = ({ vendedor }: { vendedor: ResumoVendedor }) => (
  <div className="card">
    <h3>{vendedor.vendedor.name}</h3>
    <TierBadge tier={vendedor.tier} />
    
    <p>Vendas no mês: <strong>{vendedor.novosMes}</strong></p>
    <p>Comissão MRR: <strong>{vendedor.percentualMrr}%</strong></p>
    <p>Comissão Setup: <strong>{vendedor.percentualSetup}%</strong></p>
    
    <p>MRR Ativo: R$ {vendedor.mrrAtivo.toFixed(2)}</p>
    <p>Comissão Total: R$ {vendedor.comissaoTotal.toFixed(2)}</p>
  </div>
);
```

---

## 📅 Filtro por Mês

O filtro `month` agora funciona de forma diferente:

| Parâmetro | O que retorna |
|-----------|---------------|
| Sem filtro | Estado **atual** de todos os clientes |
| `?month=2024-06` | Estado dos clientes **até junho/2024** (evolução histórica) |

**Importante:** O tier é sempre calculado com base nas vendas **daquele mês específico**.

```typescript
// Exemplo de chamada
const response = await fetch('/vendas/resumo?month=2024-12');
const data = await response.json();

// data[0].novosMes = vendas de dezembro/2024 (não acumulado)
// data[0].tier = tier baseado nas vendas de dezembro/2024
```

---

## 🔄 Resumo das Mudanças

| Campo | Antes | Agora |
|-------|-------|-------|
| `novosMes` | ❌ Não existia | ✅ Vendas do mês |
| `tier` | ❌ Não existia | ✅ bronze/prata/ouro |
| `percentualMrr` | ❌ Não existia | ✅ % baseado no tier |
| `percentualSetup` | ❌ Não existia | ✅ % baseado no tier |
| Filtro `month` | ❌ Clientes DO mês | ✅ Clientes ATÉ o mês |

---

## ⚙️ Configuração dos Tiers

Os valores dos tiers podem ser consultados e alterados via:

- **GET** `/vendas/commission-config` - Ver configuração atual
- **PUT** `/vendas/commission-config` - Alterar configuração

```json
{
  "sales_goal": 10,
  "mrr_tier1": 5.0,
  "mrr_tier2": 10.0,
  "mrr_tier3": 20.0,
  "setup_tier1": 15.0,
  "setup_tier2": 25.0,
  "setup_tier3": 40.0
}
```

### Descrição dos campos:

| Campo | Descrição |
|-------|-----------|
| `sales_goal` | Meta de vendas para atingir tier ouro |
| `mrr_tier1` | % MRR para bronze (1-5 vendas) |
| `mrr_tier2` | % MRR para prata (6-9 vendas) |
| `mrr_tier3` | % MRR para ouro (10+ vendas) |
| `setup_tier1` | % Setup para bronze |
| `setup_tier2` | % Setup para prata |
| `setup_tier3` | % Setup para ouro |

---

## 📝 Exemplo de Response Completo

### GET `/vendas/resumo?month=2024-12`

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
    "mrrAtivo": 6085.0,
    "setupTotal": 0.0,
    "comissaoTotal": 1566.1,
    "novosMes": 3,
    "tier": "bronze",
    "percentualMrr": 5.0,
    "percentualSetup": 15.0
  }
]
```

### GET `/vendas/ranking?month=2024-12`

```json
[
  {
    "vendedor": {
      "id": 12476067,
      "name": "Amanda Klava",
      "email": "amanda.klava@ecosysauto.com.br"
    },
    "mrrAtivo": 6085.0,
    "clientesAtivos": 15,
    "novosMes": 3,
    "posicao": 1,
    "comissaoTotal": 1566.1,
    "tier": "bronze",
    "percentualMrr": 5.0,
    "percentualSetup": 15.0
  }
]
```
