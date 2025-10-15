# 📚 Índice da Documentação - EcoSys MS API

## 🎯 Visão Geral

Este repositório contém toda a documentação da API EcoSys MS, organizada por tipo de conteúdo e nível de profundidade.

---

## 📖 Documentos Principais

### 1. 🚀 **[README.md](./README.md)**
**Para**: Desenvolvedores iniciantes, overview do projeto

**Conteúdo**:
- Visão geral do projeto
- Features principais
- Quick start e instalação
- Stack tecnológico
- Exemplos básicos
- Links para documentação detalhada

**Quando usar**: Primeira leitura, setup inicial do projeto

---

### 2. ⚡ **[QUICK_START.md](./QUICK_START.md)**
**Para**: Desenvolvedores que querem usar a API rapidamente

**Conteúdo**:
- Referência rápida de todos os endpoints
- Exemplos prontos de código (Python, JavaScript, cURL)
- Parâmetros e respostas resumidos
- Troubleshooting comum
- Deploy rápido

**Quando usar**: Consulta rápida durante desenvolvimento

---

### 3. 📚 **[API_DOCUMENTATION.md](./API_DOCUMENTATION.md)**
**Para**: Desenvolvedores que precisam de documentação técnica completa

**Conteúdo**:
- Documentação detalhada de TODOS os endpoints
- Arquitetura completa do sistema
- Modelos de dados (Pydantic)
- Sistema de cache explicado em profundidade
- Health Scores - cálculo completo dos 4 pilares
- Queries SQL documentadas
- Exemplos avançados
- Troubleshooting detalhado
- Métricas e monitoramento

**Quando usar**: Implementação completa, debugging avançado, manutenção

---

### 4. 📊 **[DASHBOARD_DOCS.md](./DASHBOARD_DOCS.md)**
**Para**: Product Owners, analistas, desenvolvedores do dashboard

**Conteúdo**:
- Detalhes do endpoint `/dashboard`
- Explicação de cada KPI
- Fórmulas de cálculo (MRR, Churn, etc)
- Distribuição de health scores
- Exemplos de uso
- Casos de uso de negócio

**Quando usar**: Desenvolvimento do frontend do dashboard, análise de KPIs

---

### 5. 🔧 **[REFACTORING_HEALTH_SCORES.md](./REFACTORING_HEALTH_SCORES.md)**
**Para**: Desenvolvedores mantendo o código de health scores

**Conteúdo**:
- Histórico da refatoração
- Arquitetura antes vs depois
- Explicação de cada função
- Padrões de design utilizados
- Benefícios da refatoração
- Como adicionar novos pilares

**Quando usar**: Manutenção do código de health scores, adicionar features

---

### 6. 📅 **[FILTROS_E_TMO_DOCS.md](./FILTROS_E_TMO_DOCS.md)**
**Para**: Desenvolvedores trabalhando com filtros e métricas temporais

**Conteúdo**:
- Sistema de filtros por data
- Cálculo do TMO (Tempo Médio de Onboarding)
- Cache dinâmico baseado em filtros
- Exemplos de filtros
- Alterações técnicas nos arquivos
- Troubleshooting específico

**Quando usar**: Implementar filtros, debugar TMO, trabalhar com cache dinâmico

---

## 🔧 Arquivos de Configuração

### 7. ⚙️ **[.env.example](./.env.example)**
**Para**: DevOps, desenvolvedores fazendo setup

**Conteúdo**:
- Template de variáveis de ambiente
- Descrição de cada variável
- Valores de exemplo
- Notas de segurança

**Quando usar**: Configurar novo ambiente (dev, staging, prod)

---

### 8. 📦 **[requirements.txt](./requirements.txt)**
**Para**: Desenvolvedores instalando dependências

**Conteúdo**:
- Lista completa de dependências Python
- Versões específicas
- Compatibilidade testada

**Quando usar**: `pip install -r requirements.txt`

---

### 9. 📮 **[EcoSys_API.postman_collection.json](./EcoSys_API.postman_collection.json)**
**Para**: Desenvolvedores testando a API

**Conteúdo**:
- Coleção completa do Postman
- Todos os endpoints configurados
- Variáveis de ambiente
- Exemplos de body/params

**Quando usar**: Importar no Postman para testar endpoints

---

## 📋 Documentos Legados

### 10. 📝 **[CORRECAO_PERMISSOES.md](./CORRECAO_PERMISSOES.md)**
**Para**: Referência histórica

**Conteúdo**:
- Correção de estrutura do Supabase
- SQL de permissões

---

## 🗺️ Mapa de Navegação

### Você quer...

#### ✅ Começar do zero?
1. Leia: [README.md](./README.md)
2. Configure: [.env.example](./.env.example)
3. Execute: `pip install -r requirements.txt`
4. Consulte: [QUICK_START.md](./QUICK_START.md)

#### ✅ Usar a API rapidamente?
1. Vá direto para: [QUICK_START.md](./QUICK_START.md)
2. Importe: [EcoSys_API.postman_collection.json](./EcoSys_API.postman_collection.json)

#### ✅ Entender a fundo como funciona?
1. Leia: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
2. Aprofunde em tópicos específicos:
   - Dashboard: [DASHBOARD_DOCS.md](./DASHBOARD_DOCS.md)
   - Health Scores: [REFACTORING_HEALTH_SCORES.md](./REFACTORING_HEALTH_SCORES.md)
   - Filtros: [FILTROS_E_TMO_DOCS.md](./FILTROS_E_TMO_DOCS.md)

#### ✅ Manter/expandir o código?
1. [REFACTORING_HEALTH_SCORES.md](./REFACTORING_HEALTH_SCORES.md) - Arquitetura
2. [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) - Referência técnica
3. [FILTROS_E_TMO_DOCS.md](./FILTROS_E_TMO_DOCS.md) - Features recentes

#### ✅ Desenvolver frontend/dashboard?
1. [DASHBOARD_DOCS.md](./DASHBOARD_DOCS.md) - KPIs e métricas
2. [QUICK_START.md](./QUICK_START.md) - Exemplos de código
3. [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) - Endpoints detalhados

#### ✅ Fazer deploy em produção?
1. [.env.example](./.env.example) - Configuração
2. [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) - Seção "Deployment"
3. [README.md](./README.md) - Checklist de deployment

---

## 📊 Comparação dos Documentos

| Documento | Tamanho | Profundidade | Público | Atualização |
|-----------|---------|--------------|---------|-------------|
| README.md | Médio | Média | Geral | Sempre |
| QUICK_START.md | Pequeno | Baixa | Desenvolvedores | A cada endpoint novo |
| API_DOCUMENTATION.md | Grande | Alta | Desenvolvedores | A cada mudança |
| DASHBOARD_DOCS.md | Médio | Média | PO/Devs | A cada KPI novo |
| REFACTORING_HEALTH_SCORES.md | Médio | Alta | Maintainers | Na refatoração |
| FILTROS_E_TMO_DOCS.md | Médio | Média | Desenvolvedores | Com novas features |

---

## 🔄 Fluxo de Leitura Recomendado

### Para Novos Desenvolvedores

```
1. README.md (15 min)
   ↓
2. QUICK_START.md (10 min)
   ↓
3. Importar Postman Collection (5 min)
   ↓
4. Testar endpoints (30 min)
   ↓
5. API_DOCUMENTATION.md (conforme necessário)
```

### Para Desenvolvedores Experientes

```
1. QUICK_START.md (5 min)
   ↓
2. API_DOCUMENTATION.md - seções relevantes (20 min)
   ↓
3. Documentos específicos conforme necessário
```

### Para Manutenção do Código

```
1. REFACTORING_HEALTH_SCORES.md (30 min)
   ↓
2. API_DOCUMENTATION.md - Arquitetura (20 min)
   ↓
3. Código fonte com contexto
```

---

## 🎯 Mantendo a Documentação

### Quando adicionar um novo endpoint:

1. ✅ Atualizar `QUICK_START.md` com exemplo rápido
2. ✅ Atualizar `API_DOCUMENTATION.md` com documentação completa
3. ✅ Adicionar à coleção do Postman
4. ✅ Atualizar README.md se for feature major

### Quando modificar um cálculo:

1. ✅ Atualizar documentação específica (ex: `DASHBOARD_DOCS.md`)
2. ✅ Atualizar `API_DOCUMENTATION.md`
3. ✅ Atualizar exemplos se necessário

### Quando refatorar código:

1. ✅ Criar/atualizar documento específico (ex: `REFACTORING_*.md`)
2. ✅ Atualizar `API_DOCUMENTATION.md` se houver mudanças de interface
3. ✅ Manter histórico de decisões

---

## 📞 Suporte

Se você não encontrou o que procurava:

1. **Busque** nos documentos usando Ctrl+F
2. **Consulte** o [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) - seção Troubleshooting
3. **Abra uma issue** no GitHub
4. **Entre em contato**: support@ecosys.com

---

## ✨ Contribuindo com a Documentação

1. Mantenha o estilo consistente
2. Use emojis para facilitar navegação
3. Inclua exemplos práticos
4. Atualize este índice ao adicionar novos documentos
5. Revise por typos e erros

---

**Última atualização**: 15 de Outubro de 2025  
**Versão**: 1.0.0  
**Mantido por**: EcoSys Development Team
