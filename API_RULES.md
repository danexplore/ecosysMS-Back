# Regras de Implementação de APIs

Este documento define as regras e padrões para implementação de APIs neste projeto. Todas as APIs devem seguir estas diretrizes para garantir consistência, manutenibilidade e qualidade.

## 1. Estrutura Geral

### 1.1 Arquitetura
- Usar **FastAPI** como framework principal
- Seguir padrão **RESTful** para endpoints
- Implementar autenticação/autorização adequada
- Usar **PostgreSQL** como banco de dados principal via **psycopg2**

### 1.2 Organização de Arquivos
```
api/
├── main.py              # Ponto de entrada da aplicação
├── lib/                 # Módulos compartilhados
│   ├── models.py        # Modelos de dados (Pydantic)
│   ├── queries.py       # Consultas SQL diretas
│   └── db_connection.py # Conexão PostgreSQL global
└── scripts/             # Scripts utilitários (não endpoints)
```

## 2. Endpoints

### 2.1 Convenções de Nomenclatura
- Usar **snake_case** para nomes de endpoints
- Prefixo baseado no recurso: `/clientes`, `/vendas`, `/inadimplencia`
- Verbos HTTP padronizados:
  - `GET` - Buscar dados
  - `POST` - Criar recursos
  - `PUT` - Atualizar completamente
  - `PATCH` - Atualizar parcialmente
  - `DELETE` - Remover recursos

### 2.2 Estrutura de Resposta
Todas as respostas devem seguir este formato padrão:

```json
{
  "success": true|false,
  "data": { ... } | [...],
  "message": "Mensagem opcional",
  "errors": ["lista de erros"] | null
}
```

**Exemplos:**
- Sucesso: `{"success": true, "data": {...}}`
- Erro: `{"success": false, "message": "Erro interno", "errors": ["Detalhes do erro"]}`

### 2.3 Tratamento de Erros
- Usar códigos HTTP apropriados (200, 201, 400, 401, 403, 404, 500)
- Nunca expor detalhes internos do erro em produção
- Logar erros detalhados para debugging
- Retornar mensagens amigáveis ao usuário

## 3. Modelos de Dados

### 3.1 Pydantic Models
- Definir modelos em `api/lib/models.py`
- Usar tipos do Python para validação automática
- Campos obrigatórios vs opcionais bem definidos
- Documentar campos com `Field(description="...")`

```python
from pydantic import BaseModel, Field
from typing import Optional

class ClienteCreate(BaseModel):
    cnpj: str = Field(..., description="CNPJ do cliente")
    razao_social: str = Field(..., description="Razão social")
    vendedor_id: Optional[int] = Field(None, description="ID do vendedor responsável")
```

### 3.2 Validação
- Validar entrada de dados automaticamente com Pydantic
- Usar validadores customizados quando necessário
- Retornar erros de validação de forma clara

## 4. Banco de Dados

### 4.1 PostgreSQL
- Usar **psycopg2** para conexão direta com PostgreSQL
- Conexão global via `api/lib/db_connection.py`
- Evitar migrations manuais - usar queries SQL diretas

### 4.2 Consultas SQL
- Centralizar consultas SQL em `api/lib/queries/`
- Separe consultas por tipo de recurso: `clientes_queries.py`, `vendas_queries.py`
- Usar queries SQL nativas em vez de ORMs
- Adicionar índices apropriados via SQL DDL

### 4.3 Operações de Banco
- Criar módulos de operações em `api/lib/` ex: `clientes_db.py`, `vendas_db.py`
- Cada módulo deve ter função `get_conn()` para conexão
- Usar context managers para cursores: `with conn.cursor() as cursor:`
- Retornar dados como listas de dicionários
- Tratar transações com `conn.commit()` e `conn.rollback()`

### 4.4 Conexão
```python
import psycopg2
import os

def get_conn():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )
```

## 5. Autenticação e Autorização

### 5.1 JWT Tokens
- Implementar autenticação baseada em JWT
- Validar tokens em cada requisição protegida
- Usar claims para controle de acesso

### 5.2 Autorização
- Verificar permissões baseadas em roles
- Implementar middleware de autorização
- Proteger endpoints sensíveis

## 6. Logging

### 6.1 Níveis de Log
- `INFO`: Operações normais
- `WARNING`: Situações anômalas não críticas
- `ERROR`: Erros que precisam atenção
- `DEBUG`: Informações detalhadas para desenvolvimento

### 6.2 Estrutura
```python
import logging

logger = logging.getLogger(__name__)

logger.info("✅ Operação realizada com sucesso")
logger.error("❌ Erro ao processar: %s", str(e))
```

### 6.3 Boas Práticas
- Logar entrada/saída de funções importantes
- Não logar dados sensíveis (senhas, tokens)
- Usar emojis para facilitar leitura: ✅ ❌ ⚠️

## 9. Performance

### 9.1 Otimização
- Implementar cache quando apropriado
- Otimizar queries com índices

## 10. Documentação

### 10.1 OpenAPI
- Documentar automaticamente com FastAPI
- Adicionar descrições detalhadas
- Exemplos de request/response

### 10.2 README
- Documentar setup e uso
- Exemplos de chamadas API
- Troubleshooting
- Changelog de versões

## 11. Versionamento

### 11.1 API Versioning
- Usar header `Accept-Version` ou path `/v1/`
- Manter compatibilidade backward
- Depreciar versões antigas gradualmente

## 12. Exemplo de Implementação

## 12.1 Scripts pasta de execução
```python
from lib.db_connection import get_conn
from lib.queries.clientes_queries import BUSCAR_CLIENTES
import logging
logger = logging.getLogger(__name__)
def buscar_clientes():
    """Busca todos os clientes no banco de dados."""
    try:
        conn = get_conn()
        with conn.cursor() as cursor:
            cursor.execute(BUSCAR_CLIENTES)
            resultados = cursor.fetchall()

            clientes = []
            for row in resultados:
                cliente = {
                    "id": row[0],
                    "cnpj": row[1],
                    "razao_social": row[2],
                    "vendedor_id": row[3],
                    "data_criacao": row[4].isoformat() if row[4] else None
                }
                clientes.append(cliente)

            logger.info("✅ Clientes buscados com sucesso")
            return clientes

    except Exception as e:
        logger.error(f"❌ Erro ao buscar clientes: {e}")
        raise

    finally:
        if conn:
            conn.close()
```

### 12.2 Endpoint FastAPI
```python
from fastapi import APIRouter, HTTPException
from lib.clientes_db import buscar_clientes
from lib.models import ClienteResponse
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/clientes", response_model=ClienteResponse)
async def listar_clientes():
    """Lista todos os clientes."""
    try:
        clientes = buscar_clientes()

        return {
            "success": True,
            "data": clientes,
            "message": "Clientes encontrados com sucesso"
        }

    except Exception as e:
        logger.error(f"❌ Erro ao listar clientes: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": "Erro interno do servidor",
                "errors": [str(e)]
            }
        )
```