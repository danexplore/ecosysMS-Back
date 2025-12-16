from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.encoders import jsonable_encoder
from upstash_redis import Redis
from .scripts.clientes import (
    fetch_tenant_logins, 
    metricas_clientes,
    fetch_cs_users
)
from .scripts.health_scores import merge_dataframes
from .scripts.dashboard import calculate_dashboard_kpis, data_ultima_atualizacao_inadimplentes
from .scripts.credere import (
    process_clients,
    check_existing_clients, 
    fetch_existing_clientes, 
    process_client,
    clear_credere_cache
)
from .scripts.vendas import (
    fetch_resumo_comissoes_por_vendedor,
    fetch_dashboard_metrics,
    fetch_ranking_vendedores,
    get_all_clientes_as_dicts,
    get_vendedores_as_dicts,
    get_clientes_by_vendedor_as_dicts,
    get_inadimplentes_as_dicts,
    get_novos_clientes_as_dicts,
    get_churns_as_dicts,
    fetch_commission_config,
    update_commission_config,
    clear_commission_config_cache,
    CommissionConfig,
    fetch_comissoes_por_historico,
    fetch_parcelas_pagas_por_vendedor,
)
from .scripts.inadimplencia import (
    processar_snapshot_inadimplencia,
    buscar_comissoes_pendentes,
    buscar_comissoes_liberadas,
    buscar_resumo_comissoes,
    marcar_comissao_perdida,
    atualizar_comissoes_cliente_regularizado,
    ClienteInadimplente,
    ComissaoPendente,
    ResumoComissoesPendentes,
    ResultadoProcessamento
)
import os
import warnings
import json
from decimal import Decimal
from dotenv import load_dotenv
import secrets
import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from functools import lru_cache
import asyncio
import threading
import time

from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Any, Callable
from pydantic import BaseModel, Field

# ============================================================================
# CONFIGURAÇÕES E CONSTANTES
# ============================================================================

load_dotenv()

# Logging estruturado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

# Configurações de cache
class CacheConfig:
    CLIENTES = 60 * 60 * 24      # 1 dia
    HEALTH_SCORES = 60 * 60 * 24 # 1 dia
    DASHBOARD = 60 * 60 * 24     # 1 dia
    LOGINS = 60 * 60             # 1 hora
    METRICAS = 60 * 60 * 24      # 1 dia
    EVOLUTION = 60 * 60 * 24     # 1 dia
    VENDAS = 60 * 60 * 12        # 12 horas
    VENDEDORES = 60 * 60 * 24    # 1 dia

# Thread pool otimizado
MAX_WORKERS = min(32, (os.cpu_count() or 1) + 4)
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="api_worker")

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class LoginRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1, description="ID do tenant")

class ClientCredere(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    cnpj: str = Field(..., min_length=10, max_length=18)

class ClientsCredereRequest(BaseModel):
    clients: List[ClientCredere]

class CNPJCheckRequest(BaseModel):
    cnpjs: List[str]

class CacheResponse(BaseModel):
    status: str
    message: str
    keys_deleted: int


class CommissionConfigUpdate(BaseModel):
    """Modelo para atualização de configuração de comissões"""
    sales_goal: Optional[int] = Field(None, ge=1, description="Meta de vendas para tier máximo")
    mrr_tier1: Optional[float] = Field(None, ge=0, le=100, description="% MRR para 1-5 vendas")
    mrr_tier2: Optional[float] = Field(None, ge=0, le=100, description="% MRR para 6-9 vendas")
    mrr_tier3: Optional[float] = Field(None, ge=0, le=100, description="% MRR para 10+ vendas")
    setup_tier1: Optional[float] = Field(None, ge=0, le=100, description="% Setup para 1-5 vendas")
    setup_tier2: Optional[float] = Field(None, ge=0, le=100, description="% Setup para 6-9 vendas")
    setup_tier3: Optional[float] = Field(None, ge=0, le=100, description="% Setup para 10+ vendas")
    mrr_recurrence: Optional[List[float]] = Field(None, description="Array de % de comissão recorrente por mês")


# ============================================================================
# MODELOS PYDANTIC - INADIMPLÊNCIA
# ============================================================================

class ClienteInadimplenteRequest(BaseModel):
    """Cliente inadimplente do snapshot semanal"""
    cnpj: str = Field(..., min_length=11, max_length=20, description="CNPJ do cliente")
    razao_social: str = Field(..., min_length=1, max_length=255, description="Razão social")
    parcelas_atrasadas: int = Field(..., ge=1, description="Quantidade de parcelas atrasadas")
    vendedor_id: Optional[int] = Field(None, description="ID do vendedor responsável")
    vendedor_nome: Optional[str] = Field(None, description="Nome do vendedor responsável")
    valor_mrr: float = Field(0.0, ge=0, description="Valor do MRR do cliente")
    percentual_comissao: float = Field(0.0, ge=0, le=100, description="Percentual de comissão aplicável")


class SnapshotInadimplenciaRequest(BaseModel):
    """Request para processar snapshot semanal de inadimplência"""
    clientes: List[ClienteInadimplenteRequest] = Field(..., min_length=1, description="Lista de clientes inadimplentes")


class RegularizarClienteRequest(BaseModel):
    """Request para regularizar manualmente um cliente"""
    cnpj: str = Field(..., min_length=11, max_length=20, description="CNPJ do cliente")
    parcelas_pagas: int = Field(..., ge=1, description="Quantidade de parcelas regularizadas")


class MarcarPerdidaRequest(BaseModel):
    """Request para marcar comissões como perdidas"""
    cnpj: str = Field(..., min_length=11, max_length=20, description="CNPJ do cliente")
    motivo: str = Field("cancelamento", description="Motivo da perda")

# ============================================================================
# AUTENTICAÇÃO
# ============================================================================

security = HTTPBasic()

@lru_cache(maxsize=1)
def get_users() -> Dict[str, str]:
    """Carrega usuários do .env com cache"""
    users = {}
    users_env = os.getenv("BASIC_AUTH_USERS")
    if users_env:
        for pair in users_env.split(","):
            if ":" in pair:
                user, pwd = pair.split(":", 1)
                users[user.strip()] = pwd.strip()
    return users

def verify_basic_auth(credentials: HTTPBasicCredentials = Depends(security)):
    """Valida credenciais Basic Auth"""
    users = get_users()
    password = users.get(credentials.username)
    
    if not password or not secrets.compare_digest(credentials.password, password):
        raise HTTPException(
            status_code=401, 
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Basic"}
        )
    return credentials

# ============================================================================
# GERENCIAMENTO DE CACHE E LOCKS
# ============================================================================

class CacheManager:
    """Gerenciador centralizado de cache com locks thread-safe"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self._locks: Dict[str, threading.Lock] = {}
        self._locks_lock = threading.Lock()
    
    def get_lock(self, cache_key: str) -> threading.Lock:
        """Obtém ou cria um lock para uma chave específica"""
        with self._locks_lock:
            if cache_key not in self._locks:
                self._locks[cache_key] = threading.Lock()
            return self._locks[cache_key]
    
    def get(self, key: str) -> Optional[Any]:
        """Busca valor do cache com tratamento de erros"""
        try:
            cached = self.redis.get(key)
            if cached:
                return json.loads(cached) if isinstance(cached, str) else cached
        except Exception as e:
            logger.warning(f"⚠️ Erro ao buscar cache {key}: {e}")
        return None
    
    def set(self, key: str, value: Any, ttl: int) -> bool:
        """Salva valor no cache com tratamento de erros"""
        try:
            # Encoder customizado para tipos não serializáveis
            def json_encoder(obj):
                if isinstance(obj, Decimal):
                    return float(obj)
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
            
            cache_data = json.dumps(value, ensure_ascii=False, default=json_encoder)
            self.redis.set(key, cache_data, ex=ttl)
            return True
        except Exception as e:
            logger.warning(f"⚠️ Erro ao salvar cache {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Deleta chaves que correspondem ao padrão"""
        try:
            keys = self.redis.keys(pattern)
            deleted = 0
            for key in keys:
                self.redis.delete(key)
                deleted += 1
            return deleted
        except Exception as e:
            logger.error(f"❌ Erro ao deletar cache {pattern}: {e}")
            return 0
    
    async def get_or_compute(
        self,
        cache_key: str,
        compute_func: Callable,
        ttl: int,
        *args,
        use_lock: bool = False,
        **kwargs
    ) -> Any:
        """Busca no cache ou calcula o valor. Suporta locks para evitar processamento duplicado."""
        # Tentar buscar do cache
        cached = self.get(cache_key)
        if cached:
            logger.info(f"✅ Cache hit: {cache_key}")
            return cached
        
        logger.info(f"❌ Cache miss: {cache_key}")
        
        # Se usar lock, garantir processamento único
        if use_lock:
            lock = self.get_lock(cache_key)
            
            if not lock.acquire(blocking=False):
                logger.info(f"⏳ Aguardando processamento: {cache_key}")
                return await self._wait_for_cache(cache_key, lock, timeout=60)
            
            try:
                # Verificar cache novamente após adquirir lock
                cached = self.get(cache_key)
                if cached:
                    logger.info(f"✅ Cache disponível após lock: {cache_key}")
                    return cached
                
                # Calcular valor
                result = await self._execute_compute(compute_func, *args, **kwargs)
                self.set(cache_key, result, ttl)
                logger.info(f"💾 Cache salvo: {cache_key} (TTL: {ttl}s)")
                return result
            finally:
                lock.release()
                logger.debug(f"🔓 Lock liberado: {cache_key}")
        else:
            # Sem lock, apenas calcular
            result = await self._execute_compute(compute_func, *args, **kwargs)
            self.set(cache_key, result, ttl)
            logger.info(f"💾 Cache salvo: {cache_key} (TTL: {ttl}s)")
            return result
    
    async def _wait_for_cache(self, cache_key: str, lock: threading.Lock, timeout: int = 60) -> Any:
        """Aguarda cache ficar disponível"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            await asyncio.sleep(2)
            cached = self.get(cache_key)
            if cached:
                elapsed = int(time.time() - start_time)
                logger.info(f"✅ Cache disponível após {elapsed}s: {cache_key}")
                return cached
        
        logger.warning(f"⏰ Timeout aguardando cache: {cache_key}")
        lock.acquire(blocking=True)
        return None
    
    async def _execute_compute(self, func: Callable, *args, **kwargs) -> Any:
        """Executa função de forma assíncrona se necessário"""
        loop = asyncio.get_event_loop()
        
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return await loop.run_in_executor(executor, lambda: func(*args, **kwargs))

# ============================================================================
# INICIALIZAÇÃO DA APLICAÇÃO
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia lifecycle da aplicação"""
    try:
        logger.info("🚀 Iniciando aplicação...")
        
        # Validar variáveis de ambiente
        required_vars = [
            "UPSTASH_REDIS_REST_URL",
            "UPSTASH_REDIS_REST_TOKEN",
            "BASIC_AUTH_USERS"
        ]
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            raise RuntimeError(f"Variáveis obrigatórias ausentes: {missing}")
        
        # Testar Redis
        app.state.redis.ping()
        logger.info("✅ Redis conectado")
        
        # Inicializar cache manager
        app.state.cache = CacheManager(app.state.redis)
        logger.info(f"✅ Cache manager inicializado")
        
        logger.info(f"✅ Thread pool: {MAX_WORKERS} workers")
        logger.info("✅ Aplicação pronta!")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Erro na inicialização: {e}")
        raise
    finally:
        logger.info("🔴 Encerrando aplicação...")
        executor.shutdown(wait=True)
        logger.info("✅ Aplicação encerrada")

# Criar app FastAPI
app = FastAPI(
    title="EcosysMS API",
    description="API de Gestão de Clientes e Health Scores",
    version="2.0.0",
    lifespan=lifespan
)

# Inicializar Redis antes do lifespan
try:
    redis = Redis.from_env()
    app.state.redis = redis
    logger.info("✅ Redis configurado")
except Exception as e:
    logger.error(f"❌ Erro ao configurar Redis: {e}")
    raise

# ============================================================================
# MIDDLEWARES
# ============================================================================

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Adiciona tempo de processamento nos headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.3f}s"
    return response

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "message": "EcosysMS API",
        "version": "2.0.0",
        "status": "online",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check(request: Request):
    """Health check detalhado"""
    try:
        redis = request.app.state.redis
        redis.ping()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": os.getenv("ENVIRONMENT", "production"),
            "redis": "connected",
            "workers": MAX_WORKERS,
            "version": "2.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")
    
@app.get("/clientes", dependencies=[Depends(verify_basic_auth)])
async def get_clientes(
    request: Request,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
):
    """
    Retorna lista de clientes com filtros opcionais.
    
    - **data_inicio**: Data inicial (YYYY-MM-DD)
    - **data_fim**: Data final (YYYY-MM-DD)
    """
    cache_key = f"clientes:{data_inicio or 'all'}:{data_fim or 'all'}"
    cache: CacheManager = request.app.state.cache
    
    try:
        from .scripts.clientes import fetch_clientes
        
        def compute_clientes():
            clientes_list = fetch_clientes(data_inicio, data_fim)
            # Converter para formato indexado já na computação
            return {str(c['client_id']): c for c in clientes_list}
        
        result = await cache.get_or_compute(
            cache_key,
            compute_clientes,
            CacheConfig.CLIENTES
        )
        
        return jsonable_encoder(result)
        
    except Exception as e:
        logger.error(f"Erro em /clientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/clientes/evolution", dependencies=[Depends(verify_basic_auth)])
async def get_clientes_evolution(
    request: Request,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
):
    """Retorna evolução mensal de clientes"""
    cache_key = f"evolution:{data_inicio or 'all'}:{data_fim or 'all'}"
    cache: CacheManager = request.app.state.cache
    
    try:
        from .scripts.clientes import calculate_clientes_evolution
        
        return await cache.get_or_compute(
            cache_key,
            lambda: calculate_clientes_evolution(data_inicio, data_fim),
            CacheConfig.EVOLUTION
        )
    except Exception as e:
        logger.error(f"Erro em /clientes/evolution: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/clientes/data-atualizacao-inadimplentes", dependencies=[Depends(verify_basic_auth)])
async def get_data_ultima_atualizacao_inadimplentes(request: Request):
    """Retorna data da última atualização de inadimplentes"""
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            data_ultima_atualizacao_inadimplentes
        )
        return result or {"data_atualizacao": None}
    except Exception as e:
        logger.error(f"Erro em /data-atualizacao-inadimplentes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health-scores", dependencies=[Depends(verify_basic_auth)])
async def get_health_scores(
    request: Request,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
):
    """Retorna health scores dos clientes com métricas detalhadas incluindo porte da loja"""
    cache_key = f"health-scores:{data_inicio or 'all'}:{data_fim or 'all'}"
    cache: CacheManager = request.app.state.cache
    
    try:
        result = await cache.get_or_compute(
            cache_key,
            lambda: merge_dataframes(data_inicio, data_fim),
            CacheConfig.HEALTH_SCORES,
            use_lock=True  # Lock para evitar cálculo duplicado
        )
        return jsonable_encoder(result)
    except Exception as e:
        logger.error(f"Erro em /health-scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard", dependencies=[Depends(verify_basic_auth)])
async def get_dashboard(
    request: Request,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
):
    """Retorna KPIs do dashboard"""
    cache_key = f"dashboard:{data_inicio or 'all'}:{data_fim or 'all'}"
    cache: CacheManager = request.app.state.cache
    
    try:
        result = await cache.get_or_compute(
            cache_key,
            lambda: calculate_dashboard_kpis(data_inicio, data_fim),
            CacheConfig.DASHBOARD
        )
        return jsonable_encoder(result)
    except Exception as e:
        logger.error(f"Erro em /dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cache/clear", dependencies=[Depends(verify_basic_auth)], response_model=CacheResponse)
async def clear_cache(request: Request):
    """Limpa todo o cache da aplicação"""
    try:
        cache: CacheManager = request.app.state.cache
        
        patterns = [
            'clientes:*',
            'health-scores:*',
            'dashboard:*',
            'evolution:*',
            'metricas-clientes',
            'logins:*'
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = cache.delete_pattern(pattern)
            total_deleted += deleted
            logger.info(f"🗑️ Deletadas {deleted} chaves: {pattern}")
        
        return CacheResponse(
            status="success",
            message="Cache limpo com sucesso",
            keys_deleted=total_deleted
        )
    except Exception as e:
        logger.error(f"Erro ao limpar cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cache/stats", dependencies=[Depends(verify_basic_auth)])
async def cache_stats(request: Request):
    """Estatísticas do cache"""
    try:
        cache: CacheManager = request.app.state.cache
        
        patterns = {
            'clientes': 'clientes:*',
            'health_scores': 'health-scores:*',
            'dashboard': 'dashboard:*',
            'evolution': 'evolution:*',
            'metricas': 'metricas-clientes',
            'logins': 'logins:*'
        }
        
        stats = {}
        for name, pattern in patterns.items():
            keys = cache.redis.keys(pattern)
            stats[name] = len(keys)
        
        return {
            "total_keys": sum(stats.values()),
            "by_type": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Erro ao obter stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logins", dependencies=[Depends(verify_basic_auth)])
async def get_logins(request: Request, tenant_id: str):
    """Retorna logins de um tenant"""
    cache_key = f"logins:{tenant_id}"
    cache: CacheManager = request.app.state.cache
    
    try:
        result = await cache.get_or_compute(
            cache_key,
            lambda: fetch_tenant_logins(tenant_id),
            CacheConfig.LOGINS
        )
        return jsonable_encoder(result)
    except Exception as e:
        logger.error(f"Erro em /logins: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metricas-clientes", dependencies=[Depends(verify_basic_auth)])
async def get_metricas_clientes(request: Request):
    """Retorna métricas agregadas dos clientes"""
    cache_key = "metricas-clientes"
    cache: CacheManager = request.app.state.cache
    
    try:
        result = await cache.get_or_compute(
            cache_key,
            metricas_clientes,
            CacheConfig.METRICAS
        )
        return jsonable_encoder(result)
    except Exception as e:
        logger.error(f"Erro em /metricas-clientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cs-users", dependencies=[Depends(verify_basic_auth)])
async def get_cs_users():
    """
    Retorna lista de usuários CS com seus e-mails.
    
    **Response:**
    ```json
    [
        {
            "id": 13090515,
            "name": "Nome do CS",
            "email": "cs@ecosysauto.com.br"
        }
    ]
    ```
    """
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            fetch_cs_users
        )
        return jsonable_encoder(result)
    except Exception as e:
        logger.error(f"Erro em /cs-users: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ENDPOINTS CREDERE
# ============================================================================

@app.post("/add-client-credere", dependencies=[Depends(verify_basic_auth)])
async def add_client_credere(client: ClientCredere):
    """
    Adiciona um único cliente no sistema Credere.
    
    **Request:**
    ```json
    {
        "name": "Empresa ABC Ltda",
        "cnpj": "44.285.354/0001-03"  // Aceita formatado ou não
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
    """
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            lambda: process_client(client.dict())
        )
        return result
    except Exception as e:
        logger.error(f"Erro ao adicionar cliente: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add-clients-credere", dependencies=[Depends(verify_basic_auth)])
async def add_clients_credere(request: ClientsCredereRequest):
    """
    Adiciona múltiplos clientes no Credere em lote.
    
    **Request:**
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
            {...}
        ]
    }
    ```
    
    **Nota:** Clientes já existentes são automaticamente filtrados.
    """
    try:
        clients_dicts = [c.dict() for c in request.clients]
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            executor,
            lambda: process_clients(clients_dicts)
        )
        return {"results": results}
    except Exception as e:
        logger.error(f"Erro ao processar clientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/all-clients-credere", dependencies=[Depends(verify_basic_auth)])
async def get_all_clients_credere():
    """
    Retorna lista de CNPJs de todos os clientes cadastrados no Credere.
    
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
    
    **Nota:** CNPJs retornados estão normalizados (sem formatação).
    Os dados são cacheados - use `/credere/cache/clear` para atualizar.
    """
    try:
        loop = asyncio.get_event_loop()
        existing = await loop.run_in_executor(executor, fetch_existing_clientes)
        return {"all_clients": list(existing.keys())}
    except Exception as e:
        logger.error(f"Erro ao buscar clientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/check-existing-clients-credere", dependencies=[Depends(verify_basic_auth)])
async def check_existing_clients_credere(request: CNPJCheckRequest):
    """
    Verifica quais CNPJs já existem no Credere.
    
    **Input:**
    ```json
    {
        "cnpjs": ["08098404000171", "44.285.354/0001-03", "49.796.764/0001-24"]
    }
    ```
    
    **Output:**
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
            ...
        ]
    }
    ```
    """
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            executor,
            lambda: check_existing_clients(request.cnpjs)
        )
        
        # Estatísticas
        total = len(results)
        existing = sum(1 for r in results if r['exists'])
        not_found = sum(1 for r in results if r['valid'] and not r['exists'])
        invalid = sum(1 for r in results if not r['valid'])
        
        return {
            "total": total,
            "existing": existing,
            "not_found": not_found,
            "invalid": invalid,
            "results": results
        }
    except Exception as e:
        logger.error(f"Erro ao verificar clientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/credere/cache/clear", dependencies=[Depends(verify_basic_auth)])
async def clear_credere_cache_endpoint():
    """Limpa o cache de clientes do Credere (força nova busca na API)"""
    try:
        clear_credere_cache()
        return {
            "status": "success",
            "message": "Cache do Credere limpo com sucesso",
            "note": "A próxima requisição buscará dados atualizados da API"
        }
    except Exception as e:
        logger.error(f"Erro ao limpar cache Credere: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ENDPOINTS DE VENDAS E COMISSÕES
# ============================================================================

@app.get("/vendas/vendedores", dependencies=[Depends(verify_basic_auth)])
async def get_vendedores(request: Request):
    """
    Retorna lista de vendedores ativos.
    
    **Response:**
    ```json
    [
        {"id": 12476067, "name": "Amanda Klava", "email": "amanda@email.com"},
        ...
    ]
    ```
    """
    cache_key = "vendedores:all"
    cache: CacheManager = request.app.state.cache
    
    try:
        result = await cache.get_or_compute(
            cache_key,
            get_vendedores_as_dicts,
            CacheConfig.VENDEDORES
        )
        return jsonable_encoder(result)
    except Exception as e:
        logger.error(f"Erro em /vendas/vendedores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vendas/clientes", dependencies=[Depends(verify_basic_auth)])
async def get_clientes_comissao(request: Request, month: Optional[str] = None):
    """
    Retorna todos os clientes para cálculo de comissão.
    Considera apenas clientes com valor > 0.
    
    **Query Parameters:**
    - **month**: (opcional) Mês de referência no formato YYYY-MM (ex: 2024-01)
    
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
        },
        ...
    ]
    ```
    """
    cache_key = f"vendas:clientes:all:{month or 'all'}"
    cache: CacheManager = request.app.state.cache
    
    try:
        result = await cache.get_or_compute(
            cache_key,
            lambda: get_all_clientes_as_dicts(month),
            CacheConfig.VENDAS
        )
        return jsonable_encoder(result)
    except Exception as e:
        logger.error(f"Erro em /vendas/clientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vendas/clientes/vendedor/{vendedor_id}", dependencies=[Depends(verify_basic_auth)])
async def get_clientes_by_vendedor(request: Request, vendedor_id: int, month: Optional[str] = None):
    """
    Retorna clientes de um vendedor específico.
    
    **Path Parameters:**
    - **vendedor_id**: ID do vendedor (use 99999999 para Vendas Antigas)
    
    **Query Parameters:**
    - **month**: (opcional) Mês de referência no formato YYYY-MM (ex: 2024-01)
    
    **Response:**
    ```json
    [
        {
            "id": "123",
            "clientName": "Empresa ABC",
            "mrr": 299.90,
            "status": "ativo",
            ...
        },
        ...
    ]
    ```
    """
    cache_key = f"vendas:clientes:vendedor:{vendedor_id}:{month or 'all'}"
    cache: CacheManager = request.app.state.cache
    
    try:
        result = await cache.get_or_compute(
            cache_key,
            lambda: get_clientes_by_vendedor_as_dicts(vendedor_id, month),
            CacheConfig.VENDAS
        )
        return jsonable_encoder(result)
    except Exception as e:
        logger.error(f"Erro em /vendas/clientes/vendedor/{vendedor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vendas/clientes/inadimplentes", dependencies=[Depends(verify_basic_auth)])
async def get_clientes_inadimplentes_endpoint(request: Request, month: Optional[str] = None):
    """
    Retorna clientes inadimplentes.
    Considera apenas clientes com valor > 0.
    
    **Query Parameters:**
    - **month**: (opcional) Mês de referência no formato YYYY-MM (ex: 2024-01)
    
    **Response:**
    ```json
    [
        {
            "id": "123",
            "clientName": "Empresa ABC",
            "mrr": 299.90,
            "status": "inadimplente",
            ...
        },
        ...
    ]
    ```
    """
    cache_key = f"vendas:inadimplentes:{month or 'all'}"
    cache: CacheManager = request.app.state.cache
    
    try:
        result = await cache.get_or_compute(
            cache_key,
            lambda: get_inadimplentes_as_dicts(month),
            CacheConfig.VENDAS
        )
        return jsonable_encoder(result)
    except Exception as e:
        logger.error(f"Erro em /vendas/clientes/inadimplentes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vendas/clientes/novos", dependencies=[Depends(verify_basic_auth)])
async def get_novos_clientes_endpoint(request: Request, month: Optional[str] = None):
    """
    Retorna novos clientes do mês.
    Considera apenas clientes com valor > 0.
    
    **Query Parameters:**
    - **month**: (opcional) Mês de referência no formato YYYY-MM (ex: 2024-01). Se não informado, retorna do mês atual.
    
    **Response:**
    ```json
    [
        {
            "id": "123",
            "clientName": "Empresa ABC",
            "mrr": 299.90,
            "date": "2024-12-05",
            ...
        },
        ...
    ]
    ```
    """
    cache_key = f"vendas:novos-mes:{month or 'current'}"
    cache: CacheManager = request.app.state.cache
    
    try:
        result = await cache.get_or_compute(
            cache_key,
            lambda: get_novos_clientes_as_dicts(month),
            CacheConfig.VENDAS
        )
        return jsonable_encoder(result)
    except Exception as e:
        logger.error(f"Erro em /vendas/clientes/novos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vendas/clientes/churns", dependencies=[Depends(verify_basic_auth)])
async def get_churns_endpoint(request: Request, month: Optional[str] = None):
    """
    Retorna churns do mês.
    Considera apenas clientes com valor > 0.
    
    **Query Parameters:**
    - **month**: (opcional) Mês de referência no formato YYYY-MM (ex: 2024-01). Se não informado, retorna do mês atual.
    
    **Response:**
    ```json
    [
        {
            "id": "123",
            "clientName": "Empresa ABC",
            "mrr": 299.90,
            "canceledAt": "2024-12-03",
            ...
        },
        ...
    ]
    ```
    """
    cache_key = f"vendas:churns-mes:{month or 'current'}"
    cache: CacheManager = request.app.state.cache
    
    try:
        result = await cache.get_or_compute(
            cache_key,
            lambda: get_churns_as_dicts(month),
            CacheConfig.VENDAS
        )
        return jsonable_encoder(result)
    except Exception as e:
        logger.error(f"Erro em /vendas/clientes/churns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vendas/comissoes-historico", dependencies=[Depends(verify_basic_auth)])
async def get_comissoes_por_historico(request: Request, month: str):
    """
    Retorna comissões calculadas com base no histórico REAL de pagamentos.
    
    Esta é a nova lógica que consulta a tabela historico_pagamentos para 
    determinar quais parcelas foram efetivamente pagas.
    
    **Lógica:**
    1. Consulta parcelas pagas na tabela historico_pagamentos
    2. Mês de comissão = mês SEGUINTE ao vencimento da parcela paga
    3. Se houve churn, só paga comissão das parcelas que foram pagas até o mês do churn
    
    **Query Parameters:**
    - **month**: Mês de referência para comissão no formato YYYY-MM (ex: 2025-07)
    
    **Response:**
    ```json
    [
        {
            "vendedor": "Amanda Klava",
            "cliente_id": 123,
            "cliente_nome": "Loja XYZ",
            "mrr": 399.00,
            "posicao_ciclo": 0,
            "percentual_comissao": 0.30,
            "valor_comissao": 119.70,
            "vencimento_parcela": "2025-06-15",
            "mes_comissao": "2025-07"
        },
        ...
    ]
    ```
    """
    cache_key = f"vendas:comissoes-historico:{month}"
    cache: CacheManager = request.app.state.cache
    
    try:
        result = await cache.get_or_compute(
            cache_key,
            lambda: fetch_comissoes_por_historico(month),
            CacheConfig.VENDAS
        )
        return jsonable_encoder(result)
    except Exception as e:
        logger.error(f"Erro em /vendas/comissoes-historico: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vendas/resumo-comissoes", dependencies=[Depends(verify_basic_auth)])
async def get_resumo_comissoes(request: Request, month: Optional[str] = None):
    """
    Retorna resumo de comissões por vendedor.
    
    **Query Parameters:**
    - **month**: (opcional) Mês de referência no formato YYYY-MM (ex: 2024-01)
    
    **Response:**
    ```json
    [
        {
            "vendedor": {"id": 12476067, "name": "Amanda Klava", "email": "..."},
            "totalClientes": 50,
            "clientesAtivos": 45,
            "clientesInadimplentes": 3,
            "clientesCancelados": 2,
            "mrrAtivo": 13500.00,
            "setupTotal": 25000.00
        },
        ...
    ]
    ```
    """
    cache_key = f"vendas:resumo-comissoes:{month or 'all'}"
    cache: CacheManager = request.app.state.cache
    
    try:
        result = await cache.get_or_compute(
            cache_key,
            lambda: fetch_resumo_comissoes_por_vendedor(month),
            CacheConfig.VENDAS
        )
        return jsonable_encoder(result)
    except Exception as e:
        logger.error(f"Erro em /vendas/resumo-comissoes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vendas/dashboard", dependencies=[Depends(verify_basic_auth)])
async def get_vendas_dashboard(request: Request, month: Optional[str] = None):
    """
    Retorna métricas gerais do dashboard de vendas.
    
    **Query Parameters:**
    - **month**: (opcional) Mês de referência no formato YYYY-MM (ex: 2024-01)
    
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
    """
    cache_key = f"vendas:dashboard-metrics:{month or 'all'}"
    cache: CacheManager = request.app.state.cache
    
    try:
        result = await cache.get_or_compute(
            cache_key,
            lambda: fetch_dashboard_metrics(month),
            CacheConfig.VENDAS
        )
        return jsonable_encoder(result)
    except Exception as e:
        logger.error(f"Erro em /vendas/dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vendas/ranking", dependencies=[Depends(verify_basic_auth)])
async def get_ranking_vendedores_endpoint(request: Request, month: Optional[str] = None):
    """
    Retorna ranking de vendedores por MRR ativo.
    
    **Query Parameters:**
    - **month**: (opcional) Mês de referência no formato YYYY-MM (ex: 2024-01)
    
    **Response:**
    ```json
    [
        {
            "vendedor": {"id": 12476067, "name": "Amanda Klava", "email": "..."},
            "mrrAtivo": 15000.00,
            "clientesAtivos": 50,
            "novosMes": 8,
            "posicao": 1
        },
        ...
    ]
    ```
    """
    cache_key = f"vendas:ranking:{month or 'all'}"
    cache: CacheManager = request.app.state.cache
    
    try:
        result = await cache.get_or_compute(
            cache_key,
            lambda: fetch_ranking_vendedores(month),
            CacheConfig.VENDAS
        )
        return jsonable_encoder(result)
    except Exception as e:
        logger.error(f"Erro em /vendas/ranking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vendas/commission-config", dependencies=[Depends(verify_basic_auth)])
async def get_commission_config():
    """
    Retorna a configuração atual de comissões.
    
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
    """
    try:
        config = fetch_commission_config()
        return jsonable_encoder({
            "id": config.id,
            "sales_goal": config.sales_goal,
            "mrr_tier1": config.mrr_tier1,
            "mrr_tier2": config.mrr_tier2,
            "mrr_tier3": config.mrr_tier3,
            "setup_tier1": config.setup_tier1,
            "setup_tier2": config.setup_tier2,
            "setup_tier3": config.setup_tier3,
            "mrr_recurrence": config.mrr_recurrence,
            "updated_at": config.updated_at
        })
    except Exception as e:
        logger.error(f"Erro em /vendas/commission-config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/vendas/commission-config", dependencies=[Depends(verify_basic_auth)])
async def put_commission_config(config_update: CommissionConfigUpdate):
    """
    Atualiza a configuração de comissões.
    
    Apenas os campos fornecidos serão atualizados (PATCH semântico).
    
    **Request Body:**
    ```json
    {
        "sales_goal": 10,
        "mrr_tier1": 5.0,
        "mrr_tier2": 10.0,
        "mrr_tier3": 20.0,
        "setup_tier1": 15.0,
        "setup_tier2": 25.0,
        "setup_tier3": 40.0,
        "mrr_recurrence": [30.0, 20.0, 10.0, 10.0, 10.0, 10.0, 10.0]
    }
    ```
    
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
    """
    try:
        config = update_commission_config(
            sales_goal=config_update.sales_goal,
            mrr_tier1=config_update.mrr_tier1,
            mrr_tier2=config_update.mrr_tier2,
            mrr_tier3=config_update.mrr_tier3,
            setup_tier1=config_update.setup_tier1,
            setup_tier2=config_update.setup_tier2,
            setup_tier3=config_update.setup_tier3,
            mrr_recurrence=config_update.mrr_recurrence
        )
        return jsonable_encoder({
            "id": config.id,
            "sales_goal": config.sales_goal,
            "mrr_tier1": config.mrr_tier1,
            "mrr_tier2": config.mrr_tier2,
            "mrr_tier3": config.mrr_tier3,
            "setup_tier1": config.setup_tier1,
            "setup_tier2": config.setup_tier2,
            "setup_tier3": config.setup_tier3,
            "mrr_recurrence": config.mrr_recurrence,
            "updated_at": config.updated_at
        })
    except Exception as e:
        logger.error(f"Erro em PUT /vendas/commission-config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/vendas/cache/clear", dependencies=[Depends(verify_basic_auth)], response_model=CacheResponse)
async def clear_vendas_cache(request: Request):
    """Limpa o cache de vendas e configuração de comissões"""
    try:
        cache: CacheManager = request.app.state.cache
        
        patterns = [
            'vendedores:*',
            'vendas:*'
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = cache.delete_pattern(pattern)
            total_deleted += deleted
            logger.info(f"🗑️ Deletadas {deleted} chaves: {pattern}")
        
        # Limpar cache de configuração de comissões
        clear_commission_config_cache()
        
        return CacheResponse(
            status="success",
            message="Cache de vendas e configuração de comissões limpo com sucesso",
            keys_deleted=total_deleted
        )
    except Exception as e:
        logger.error(f"Erro ao limpar cache de vendas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS DE INADIMPLÊNCIA E COMISSÕES PENDENTES
# ============================================================================

@app.post("/vendas/processar-snapshot-inadimplencia", dependencies=[Depends(verify_basic_auth)])
async def post_processar_snapshot_inadimplencia(request_data: SnapshotInadimplenciaRequest):
    """
    Processa o snapshot semanal de inadimplência.
    
    Para cada cliente inadimplente, cria registros de comissão bloqueada
    na tabela comissoes_pendentes, um para cada parcela atrasada.
    
    A função é idempotente: registros existentes são ignorados devido
    ao constraint UNIQUE(cnpj, mes_referencia).
    
    **Request Body:**
    ```json
    {
        "clientes": [
            {
                "cnpj": "54776425000116",
                "razao_social": "Empresa XYZ Ltda",
                "parcelas_atrasadas": 3,
                "vendedor_id": 12476067,
                "vendedor_nome": "Amanda Klava",
                "valor_mrr": 250.00,
                "percentual_comissao": 10.0
            }
        ]
    }
    ```
    
    **Response:**
    ```json
    {
        "status": "success",
        "total_processados": 1,
        "total_criados": 3,
        "total_existentes": 0,
        "resultados": [
            {
                "cnpj": "54776425000116",
                "razao_social": "Empresa XYZ Ltda",
                "registros_criados": 3,
                "registros_existentes": 0,
                "sucesso": true,
                "erro": null
            }
        ]
    }
    ```
    """
    try:
        # Converter request para lista de ClienteInadimplente
        clientes = [
            ClienteInadimplente(
                cnpj=c.cnpj,
                razao_social=c.razao_social,
                parcelas_atrasadas=c.parcelas_atrasadas,
                vendedor_id=c.vendedor_id,
                vendedor_nome=c.vendedor_nome,
                valor_mrr=c.valor_mrr,
                percentual_comissao=c.percentual_comissao
            )
            for c in request_data.clientes
        ]
        
        # Processar snapshot
        resultados = processar_snapshot_inadimplencia(clientes)
        
        # Calcular totais
        total_criados = sum(r.registros_criados for r in resultados)
        total_existentes = sum(r.registros_existentes for r in resultados)
        
        return jsonable_encoder({
            "status": "success",
            "total_processados": len(resultados),
            "total_criados": total_criados,
            "total_existentes": total_existentes,
            "resultados": [
                {
                    "cnpj": r.cnpj,
                    "razao_social": r.razao_social,
                    "registros_criados": r.registros_criados,
                    "registros_existentes": r.registros_existentes,
                    "sucesso": r.sucesso,
                    "erro": r.erro
                }
                for r in resultados
            ]
        })
        
    except Exception as e:
        logger.error(f"Erro em POST /vendas/processar-snapshot-inadimplencia: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vendas/comissoes-pendentes", dependencies=[Depends(verify_basic_auth)])
async def get_comissoes_pendentes(
    vendedor_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100
):
    """
    Busca comissões pendentes (bloqueadas por inadimplência).
    
    **Query Parameters:**
    - `vendedor_id`: ID do vendedor para filtrar (opcional)
    - `status`: Status para filtrar: bloqueada, paga, perdida (opcional)
    - `limit`: Limite de registros (default 100)
    
    **Response:**
    ```json
    {
        "status": "success",
        "total": 5,
        "comissoes": [
            {
                "id": "uuid-...",
                "cnpj": "54776425000116",
                "razao_social": "Empresa XYZ Ltda",
                "vendedor_id": 12476067,
                "vendedor_nome": "Amanda Klava",
                "mes_referencia": "2025-09-01",
                "competencia": "09/2025",
                "parcela_numero": 1,
                "valor_mrr": 250.00,
                "percentual_aplicado": 10.0,
                "valor_comissao": 25.00,
                "status": "bloqueada",
                "motivo_bloqueio": "inadimplencia",
                "data_bloqueio": "2025-12-10T10:00:00",
                "data_liberacao": null,
                "dias_bloqueada": 15,
                "recem_liberada": false
            }
        ]
    }
    ```
    """
    try:
        comissoes = buscar_comissoes_pendentes(
            vendedor_id=vendedor_id,
            status=status,
            limit=limit
        )
        
        return jsonable_encoder({
            "status": "success",
            "total": len(comissoes),
            "comissoes": [
                {
                    "id": c.id,
                    "cnpj": c.cnpj,
                    "razao_social": c.razao_social,
                    "vendedor_id": c.vendedor_id,
                    "vendedor_nome": c.vendedor_nome,
                    "mes_referencia": c.mes_referencia,
                    "competencia": c.competencia,
                    "parcela_numero": c.parcela_numero,
                    "valor_mrr": c.valor_mrr,
                    "percentual_aplicado": c.percentual_aplicado,
                    "valor_comissao": c.valor_comissao,
                    "status": c.status,
                    "motivo_bloqueio": c.motivo_bloqueio,
                    "data_bloqueio": c.data_bloqueio,
                    "data_liberacao": c.data_liberacao,
                    "dias_bloqueada": c.dias_bloqueada,
                    "recem_liberada": c.recem_liberada
                }
                for c in comissoes
            ]
        })
        
    except Exception as e:
        logger.error(f"Erro em GET /vendas/comissoes-pendentes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vendas/comissoes-liberadas", dependencies=[Depends(verify_basic_auth)])
async def get_comissoes_liberadas(
    vendedor_id: Optional[int] = None,
    mes_liberacao: Optional[str] = None,
    limit: int = 100
):
    """
    Busca comissões liberadas (pagas via FIFO após regularização).
    
    **Query Parameters:**
    - `vendedor_id`: ID do vendedor para filtrar (opcional)
    - `mes_liberacao`: Mês de liberação no formato YYYY-MM (opcional)
    - `limit`: Limite de registros (default 100)
    
    **Response:**
    ```json
    {
        "status": "success",
        "total": 2,
        "comissoes": [
            {
                "id": "uuid-...",
                "cnpj": "54776425000116",
                "razao_social": "Empresa XYZ Ltda",
                "vendedor_id": 12476067,
                "vendedor_nome": "Amanda Klava",
                "mes_referencia": "2025-06-01",
                "competencia": "06/2025",
                "parcela_numero": 1,
                "valor_mrr": 250.00,
                "percentual_aplicado": 10.0,
                "valor_comissao": 25.00,
                "status": "paga",
                "motivo_bloqueio": "inadimplencia",
                "data_bloqueio": "2025-09-10T10:00:00",
                "data_liberacao": "10/12/2025",
                "dias_bloqueada": 0,
                "recem_liberada": true
            }
        ]
    }
    ```
    """
    try:
        comissoes = buscar_comissoes_liberadas(
            vendedor_id=vendedor_id,
            mes_liberacao=mes_liberacao,
            limit=limit
        )
        
        return jsonable_encoder({
            "status": "success",
            "total": len(comissoes),
            "comissoes": [
                {
                    "id": c.id,
                    "cnpj": c.cnpj,
                    "razao_social": c.razao_social,
                    "vendedor_id": c.vendedor_id,
                    "vendedor_nome": c.vendedor_nome,
                    "mes_referencia": c.mes_referencia,
                    "competencia": c.competencia,
                    "parcela_numero": c.parcela_numero,
                    "valor_mrr": c.valor_mrr,
                    "percentual_aplicado": c.percentual_aplicado,
                    "valor_comissao": c.valor_comissao,
                    "status": c.status,
                    "motivo_bloqueio": c.motivo_bloqueio,
                    "data_bloqueio": c.data_bloqueio,
                    "data_liberacao": c.data_liberacao,
                    "dias_bloqueada": c.dias_bloqueada,
                    "recem_liberada": c.recem_liberada
                }
                for c in comissoes
            ]
        })
        
    except Exception as e:
        logger.error(f"Erro em GET /vendas/comissoes-liberadas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vendas/comissoes-resumo", dependencies=[Depends(verify_basic_auth)])
async def get_comissoes_resumo(vendedor_id: Optional[int] = None):
    """
    Busca resumo consolidado de comissões pendentes por vendedor.
    
    **Query Parameters:**
    - `vendedor_id`: ID do vendedor para filtrar (opcional)
    
    **Response:**
    ```json
    {
        "status": "success",
        "total": 3,
        "resumos": [
            {
                "vendedor_id": 12476067,
                "vendedor_nome": "Amanda Klava",
                "qtd_bloqueadas": 5,
                "qtd_pagas": 10,
                "qtd_perdidas": 2,
                "total_bloqueado": 125.00,
                "total_pago": 250.00,
                "pago_mes_atual": 50.00
            }
        ]
    }
    ```
    """
    try:
        resumos = buscar_resumo_comissoes(vendedor_id=vendedor_id)
        
        return jsonable_encoder({
            "status": "success",
            "total": len(resumos),
            "resumos": [
                {
                    "vendedor_id": r.vendedor_id,
                    "vendedor_nome": r.vendedor_nome,
                    "qtd_bloqueadas": r.qtd_bloqueadas,
                    "qtd_pagas": r.qtd_pagas,
                    "qtd_perdidas": r.qtd_perdidas,
                    "total_bloqueado": r.total_bloqueado,
                    "total_pago": r.total_pago,
                    "pago_mes_atual": r.pago_mes_atual
                }
                for r in resumos
            ]
        })
        
    except Exception as e:
        logger.error(f"Erro em GET /vendas/comissoes-resumo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/vendas/regularizar-cliente", dependencies=[Depends(verify_basic_auth)])
async def post_regularizar_cliente(request_data: RegularizarClienteRequest):
    """
    Regulariza manualmente um cliente, liberando comissões FIFO.
    
    Usar em casos onde o webhook de pagamento não disparou automaticamente.
    
    **Request Body:**
    ```json
    {
        "cnpj": "54776425000116",
        "parcelas_pagas": 2
    }
    ```
    
    **Response:**
    ```json
    {
        "status": "success",
        "cnpj": "54776425000116",
        "comissoes_liberadas": 2
    }
    ```
    """
    try:
        liberadas = atualizar_comissoes_cliente_regularizado(
            cnpj=request_data.cnpj,
            parcelas_pagas=request_data.parcelas_pagas
        )
        
        return jsonable_encoder({
            "status": "success",
            "cnpj": request_data.cnpj,
            "comissoes_liberadas": liberadas
        })
        
    except Exception as e:
        logger.error(f"Erro em POST /vendas/regularizar-cliente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/vendas/marcar-comissao-perdida", dependencies=[Depends(verify_basic_auth)])
async def post_marcar_comissao_perdida(request_data: MarcarPerdidaRequest):
    """
    Marca todas as comissões bloqueadas de um cliente como perdidas.
    
    Usar quando o cliente for cancelado definitivamente.
    
    **Request Body:**
    ```json
    {
        "cnpj": "54776425000116",
        "motivo": "cancelamento"
    }
    ```
    
    **Response:**
    ```json
    {
        "status": "success",
        "cnpj": "54776425000116",
        "sucesso": true
    }
    ```
    """
    try:
        sucesso = marcar_comissao_perdida(
            cnpj=request_data.cnpj,
            motivo=request_data.motivo
        )
        
        return jsonable_encoder({
            "status": "success" if sucesso else "error",
            "cnpj": request_data.cnpj,
            "sucesso": sucesso
        })
        
    except Exception as e:
        logger.error(f"Erro em POST /vendas/marcar-comissao-perdida: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ADMINISTRAÇÃO
# ============================================================================