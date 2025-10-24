# 🚀 Deploy no Vercel - Guia Completo

## 📋 Pré-requisitos

- ✅ Conta no [Vercel](https://vercel.com)
- ✅ Repositório Git configurado (GitHub, GitLab ou Bitbucket)
- ✅ Variáveis de ambiente configuradas

---

## 🔧 Configuração

### 1. Arquivos Necessários

Os seguintes arquivos já estão configurados:

- ✅ `vercel.json` - Configuração do Vercel
- ✅ `requirements.txt` - Dependências Python
- ✅ `.vercelignore` - Arquivos a ignorar no deploy
- ✅ `api/main.py` - Aplicação FastAPI

### 2. Estrutura do Projeto

```
ecosysMS Back/
├── api/
│   ├── main.py              # ✅ Entry point
│   ├── lib/
│   │   ├── models.py
│   │   └── queries.py
│   └── scripts/
│       ├── clientes.py
│       ├── health_scores.py
│       └── dashboard.py
├── vercel.json              # ✅ Config do Vercel
├── requirements.txt         # ✅ Dependências
├── .vercelignore           # ✅ Ignore files
└── .env                    # ❌ NÃO commitar (local only)
```

---

## 🚀 Deploy via Vercel CLI

### Instalação do Vercel CLI

```bash
# Instalar globalmente
npm i -g vercel

# Ou usar npx (sem instalar)
npx vercel
```

### Login

```bash
vercel login
```

### Deploy

```bash
# Deploy de preview
vercel

# Deploy em produção
vercel --prod
```

---

## 🌐 Deploy via Dashboard do Vercel

### Passo 1: Importar Projeto

1. Acesse [vercel.com/new](https://vercel.com/new)
2. Conecte seu repositório Git
3. Selecione o repositório `ecosysMS-Back`
4. Clique em **Import**

### Passo 2: Configurar Build

O Vercel detectará automaticamente o Python e o `vercel.json`.

**Framework Preset**: Other

**Build Settings** (já configurado no vercel.json):
- Build Command: (vazio - não necessário)
- Output Directory: (vazio - não necessário)
- Install Command: `pip install -r requirements.txt`

### Passo 3: Configurar Variáveis de Ambiente

Adicione todas as variáveis do `.env`:

#### Redis
```
UPSTASH_REDIS_REST_URL = https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN = your-token-here
```

#### Autenticação
```
BASIC_AUTH_USERS = admin:senha123,user:senha456
```

#### PostgreSQL (Kommo)
```
DB_HOST = seu-host-postgres.com
DB_PORT = 5432
DB_NAME = kommo_db
DB_USER = postgres
DB_PASSWORD = sua-senha
```

#### MySQL (EcoSys)
```
DB_HOST_ECOSYS = seu-host-mysql.com
DB_NAME_ECOSYS = ecosys_db
DB_USER_ECOSYS = root
DB_PASSWORD_ECOSYS = sua-senha
```

#### Ambiente
```
ENVIRONMENT = production
```

### Passo 4: Deploy

Clique em **Deploy** e aguarde!

---

## ⚙️ Configurações do vercel.json

```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/main.py"
    }
  ],
  "env": {
    "PYTHON_VERSION": "3.9"
  },
  "functions": {
    "api/main.py": {
      "maxDuration": 60,
      "memory": 1024
    }
  }
}
```

### Explicação:

- **version**: Versão da plataforma Vercel (2 é a atual)
- **builds**: Define que `api/main.py` será o entry point usando Python
- **routes**: Roteia todas as requisições para `api/main.py`
- **env.PYTHON_VERSION**: Especifica Python 3.9+
- **functions.maxDuration**: Timeout de 60 segundos (máximo no plano free)
- **functions.memory**: 1GB de RAM (recomendado para Pandas)

---

## 🔐 Segurança

### Variáveis de Ambiente

⚠️ **NUNCA** commite o arquivo `.env` no Git!

Adicione no `.gitignore`:
```
.env
.env.local
.env.*.local
```

### Configurar no Vercel

1. Dashboard → Seu Projeto → Settings → Environment Variables
2. Adicione cada variável individualmente
3. Escolha o ambiente: Production, Preview, Development (ou todos)

---

## 🧪 Testar o Deploy

### 1. Health Check

```bash
curl https://seu-projeto.vercel.app/health
```

**Resposta esperada**:
```json
{
  "status": "healthy",
  "environment": "production",
  "redis_connection": "ok"
}
```

### 2. Endpoint Protegido

```bash
curl -u admin:senha123 https://seu-projeto.vercel.app/dashboard
```

### 3. Documentação Interativa

Acesse: `https://seu-projeto.vercel.app/docs`

---

## 🐛 Troubleshooting

### Erro: "Module not found"

**Causa**: Dependência faltando no `requirements.txt`

**Solução**:
```bash
# Gerar requirements.txt atualizado
pip freeze > requirements.txt

# Fazer commit e redeploy
git add requirements.txt
git commit -m "Update requirements"
git push
```

### Erro: "Function exceeded timeout"

**Causa**: Função demorando mais de 60s (limite do plano Free)

**Solução**:
1. Otimizar queries SQL
2. Verificar cache Redis
3. Atualizar para plano Pro (timeout de 300s)

### Erro: "Database connection failed"

**Causa**: Variáveis de ambiente não configuradas

**Solução**:
1. Verificar todas as variáveis em Settings → Environment Variables
2. Verificar se o banco permite conexões externas
3. Adicionar IP do Vercel na whitelist do banco

### Cache não funciona

**Causa**: Redis não configurado corretamente

**Solução**:
1. Verificar `UPSTASH_REDIS_REST_URL` e `UPSTASH_REDIS_REST_TOKEN`
2. Testar conexão:
```bash
curl -X GET \
  -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" \
  $UPSTASH_REDIS_REST_URL/ping
```

### Logs

Ver logs em tempo real:
```bash
vercel logs https://seu-projeto.vercel.app
```

Ou no Dashboard: Seu Projeto → Deployments → [Clique no deploy] → View Function Logs

---

## 📊 Monitoramento

### Vercel Analytics

1. Dashboard → Seu Projeto → Analytics
2. Monitore:
   - Requests por endpoint
   - Tempo de resposta
   - Erros (4xx, 5xx)
   - Uso de banda

### Alertas

Configure alertas para:
- Taxa de erro > 5%
- Tempo de resposta > 2s
- Uso de memória > 80%

---

## 🔄 Atualizações

### Deploy Automático

O Vercel faz deploy automático quando você faz push para:
- **main/master**: Deploy de produção
- **Outras branches**: Deploy de preview

### Deploy Manual

```bash
# Via CLI
vercel --prod

# Via Dashboard
Dashboard → Deployments → Redeploy
```

---

## 📈 Otimizações

### Cache

O Redis cache já está configurado com TTL de 24h:
- `/clientes`: ~50ms (com cache)
- `/health-scores`: ~80ms (com cache)
- `/dashboard`: ~60ms (com cache)

### Limites do Plano Free

| Recurso | Limite |
|---------|--------|
| Bandwidth | 100GB/mês |
| Invocações | 100GB-Hrs |
| Timeout | 60s |
| Memória | 1024MB |
| Concurrent Builds | 1 |

Para aumentar, considere upgrade para Pro.

---

## 🔗 Links Úteis

- 📖 [Documentação Vercel](https://vercel.com/docs)
- 🐍 [Vercel + Python](https://vercel.com/docs/functions/serverless-functions/runtimes/python)
- 🚀 [FastAPI no Vercel](https://vercel.com/guides/deploying-fastapi-with-vercel)
- 💬 [Suporte Vercel](https://vercel.com/support)

---

## ✅ Checklist de Deploy

Antes de fazer deploy, verifique:

- [ ] `vercel.json` configurado
- [ ] `requirements.txt` atualizado
- [ ] `.env` NÃO está no Git
- [ ] Variáveis de ambiente configuradas no Vercel
- [ ] Bancos de dados permitem conexões externas
- [ ] Redis Upstash configurado
- [ ] Testes locais passando
- [ ] Documentação atualizada

---

## 🎉 Deploy com Sucesso!

Após o deploy:

1. ✅ Teste o health check
2. ✅ Teste autenticação
3. ✅ Verifique logs
4. ✅ Configure domínio customizado (opcional)
5. ✅ Configure alertas
6. ✅ Compartilhe a URL!

**URL do Projeto**: `https://ecosysms-back.vercel.app`

---

**Última atualização**: 24 de Outubro de 2025  
**Versão**: 1.1.0
