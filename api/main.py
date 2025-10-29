# api/main.py - OPTIMIZED
from fastapi import FastAPI, HTTPException, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.encoders import jsonable_encoder
from upstash_redis import Redis
from .scripts.clientes import fetch_tenant_logins, metricas_clientes
from .scripts.health_scores import merge_dataframes
from .scripts.dashboard import calculate_dashboard_kpis, data_ultima_atualizacao_inadimplentes
import os
import warnings
import json
from dotenv import load_dotenv
import secrets
import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from functools import wraps
import hashlib
import asyncio
import threading

from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional
from pydantic import BaseModel

# Carregar variáveis de ambiente primeiro
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Modelos Pydantic
class LoginRequest(BaseModel):
    tenant_id: str

# Parse users from env
USERS = {}
users_env = os.getenv("BASIC_AUTH_USERS")
if users_env:
    for pair in users_env.split(","):
        if ":" in pair:
            user, pwd = pair.split(":", 1)
            USERS[user.strip()] = pwd.strip()

security = HTTPBasic()

def verify_basic_auth(credentials: HTTPBasicCredentials = Depends(security)):
    password = USERS.get(credentials.username)
    if not password or not secrets.compare_digest(credentials.password, password):
        raise HTTPException(status_code=401, detail="Acesso negado.", headers={"WWW-Authenticate": "Basic"})
    return credentials

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logger.info("Iniciando aplicação...")
        
        # Verificar variáveis de ambiente críticas
        required_env_vars = ["UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"Variáveis de ambiente obrigatórias não encontradas: {missing_vars}")
            raise RuntimeError(f"Variáveis de ambiente obrigatórias não encontradas: {missing_vars}")

        logger.info("Aplicação iniciada com sucesso!")
        yield
        
    except Exception as e:
        logger.error(f"Erro durante a inicialização: {str(e)}")
        raise
    finally:
        logger.info("Encerrando aplicação...")
    
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
if os.getenv("ENVIRONMENT") == "development":
    load_dotenv()

app = FastAPI(lifespan=lifespan)

# Adicionar middleware de compressão GZIP
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Verificar conexão com Redis
try:
    redis = Redis.from_env()
    logger.info("Conexão com Redis estabelecida com sucesso")
except Exception as e:
    logger.error(f"Erro ao conectar com Redis: {str(e)}")
    raise

# Thread pool para operações bloqueantes
executor = ThreadPoolExecutor(max_workers=4)

# Locks para evitar execuções duplicadas simultâneas
cache_locks = {}
locks_lock = threading.Lock()

def get_cache_lock(cache_key: str) -> threading.Lock:
    """Obtém ou cria um lock para uma chave de cache específica"""
    with locks_lock:
        if cache_key not in cache_locks:
            cache_locks[cache_key] = threading.Lock()
        return cache_locks[cache_key]

# Configurações de cache
CACHE_TTL_CLIENTES = 60 * 60 * 24  # 1 dia
CACHE_TTL_HEALTH_SCORES = 60 * 60 * 24  # 1 dia
CACHE_TTL_DASHBOARD = 60 * 60 * 24  # 1 dia

def cache_key_generator(*args, **kwargs) -> str:
    """Gera uma chave de cache única baseada nos argumentos"""
    key_data = str(args) + str(sorted(kwargs.items()))
    return hashlib.md5(key_data.encode()).hexdigest()

def with_cache(cache_key_prefix: str, ttl: int):
    """Decorator para adicionar cache a funções assíncronas"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Gerar chave de cache simples
            cache_key = f"{cache_key_prefix}:default"
            
            # Tentar obter do cache
            try:
                cached = redis.get(cache_key)
                if cached:
                    logger.info(f"✅ Cache hit para {cache_key_prefix}")
                    if isinstance(cached, str):
                        return json.loads(cached)
                    return cached
            except Exception as e:
                logger.warning(f"⚠️ Erro ao acessar cache: {e}")
            
            # Executar função original de forma assíncrona
            logger.info(f"⏳ Cache miss para {cache_key_prefix}, executando função...")
            
            # Se a função for síncrona, executar em thread separada
            loop = asyncio.get_event_loop()
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                # Extrair a função interna real se for um wrapper
                inner_func = func
                result = await loop.run_in_executor(
                    executor, 
                    lambda: inner_func(*args, **kwargs)
                )
            
            # Salvar no cache
            try:
                cache_data = json.dumps(result, ensure_ascii=False)
                redis.set(cache_key, cache_data, ex=ttl)
                logger.info(f"💾 Cache atualizado para {cache_key_prefix}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao salvar cache: {e}")
            
            return result
        return wrapper
    return decorator

@app.get("/")
async def root():
    return {"message": "API de Gestão de Clientes está no ar!"}

@app.get("/health")
async def health_check():
    """Endpoint de verificação de saúde da aplicação"""
    try:
        # Verificar conexão com Redis
        redis.ping()
        
        # Verificar variáveis de ambiente
        env_status = {
            "UPSTASH_REDIS_REST_URL": bool(os.getenv("UPSTASH_REDIS_REST_URL")),
            "UPSTASH_REDIS_REST_TOKEN": bool(os.getenv("UPSTASH_REDIS_REST_TOKEN")),
            "BASIC_AUTH_USERS": bool(os.getenv("BASIC_AUTH_USERS"))
        }
        
        return {
            "status": "healthy",
            "environment": os.getenv("ENVIRONMENT", "production"),
            "redis_connection": "ok",
            "env_variables": env_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Health check falhou: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check falhou: {str(e)}")
    
@app.get("/clientes", dependencies=[Depends(verify_basic_auth)])
async def get_clientes(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
):
    """
    Retorna a lista de clientes em JSON, indexada por client_id.
    
    Filtra por data de adesão OU data de cancelamento, permitindo capturar tanto
    novos clientes quanto churns no mesmo período.
    
    Args:
        data_inicio: Data inicial para filtro (formato: YYYY-MM-DD)
        data_fim: Data final para filtro (formato: YYYY-MM-DD)
    """
    try:
        # Gerar chave de cache dinâmica baseada nos filtros
        cache_key = f"clientes:{data_inicio or 'all'}:{data_fim or 'all'}"
        
        # Verificar cache
        cached = redis.get(cache_key)
        if cached:
            logger.info(f"✅ Cache hit para {cache_key}")
            return json.loads(cached)
        
        # Se não há cache, buscar dados
        logger.info(f"❌ Cache miss para {cache_key}, buscando dados...")
        from .scripts.clientes import fetch_clientes
        clientes_list = fetch_clientes(data_inicio, data_fim)
        
        # Converter para formato JSON indexado por client_id
        clientes_json = {str(c['client_id']): c for c in clientes_list}
        
        # Salvar no cache
        redis.set(cache_key, json.dumps(jsonable_encoder(clientes_json)), ex=CACHE_TTL_CLIENTES)
        logger.info(f"💾 Dados salvos no cache: {cache_key} (TTL: {CACHE_TTL_CLIENTES}s)")
        
        return jsonable_encoder(clientes_json)
    except Exception as e:
        logger.error(f"Erro ao obter clientes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter clientes: {str(e)}")

@app.get("/clientes/evolution", dependencies=[Depends(verify_basic_auth)])
async def get_clientes_evolution(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
):
    """
    Retorna a evolução mensal de clientes pagantes (novos, churns e ativos acumulados).
    
    Considera apenas clientes com valor > 0 (pagantes).
    
    Args:
        data_inicio: Data inicial para filtro (formato: YYYY-MM-DD)
        data_fim: Data final para filtro (formato: YYYY-MM-DD)
    
    Returns:
        Lista com evolução mensal:
        - mes: string (formato: "jan/2024")
        - novos_clientes: int (clientes pagantes que aderiram no mês)
        - churns: int (clientes pagantes que cancelaram no mês)
        - clientes_ativos: int (total acumulado de clientes pagantes ativos)
    """
    try:
        # Gerar chave de cache dinâmica
        cache_key = f"evolution:{data_inicio or 'all'}:{data_fim or 'all'}"
        
        # Verificar cache
        cached = redis.get(cache_key)
        if cached:
            logger.info(f"✅ Cache hit para {cache_key}")
            return json.loads(cached)
        
        # Calcular evolução
        logger.info(f"❌ Cache miss para {cache_key}, calculando evolução...")
        from .scripts.clientes import calculate_clientes_evolution
        
        loop = asyncio.get_event_loop()
        evolution = await loop.run_in_executor(
            executor, 
            lambda: calculate_clientes_evolution(data_inicio, data_fim)
        )
        
        # Salvar no cache
        redis.set(cache_key, json.dumps(evolution), ex=CACHE_TTL_CLIENTES)
        logger.info(f"💾 Evolução calculada e salva no cache: {len(evolution)} meses")
        
        return evolution
        
    except Exception as e:
        logger.error(f"Erro ao calcular evolução de clientes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao calcular evolução de clientes: {str(e)}")
    
@app.get("/clientes/data-atualizacao-inadimplentes", dependencies=[Depends(verify_basic_auth)])
async def get_data_ultima_atualizacao_inadimplentes() -> Optional[str]:
    """
    Retorna a data da última atualização dos clientes inadimplentes.
    
    Returns:
        Data da última atualização no formato string (YYYY-MM-DD) ou None se não disponível.
    """
    try:
        loop = asyncio.get_event_loop()
        data_atualizacao = await loop.run_in_executor(
            executor,
            lambda: data_ultima_atualizacao_inadimplentes()
        )
        return data_atualizacao
    except Exception as e:
        logger.error(f"Erro ao obter data de última atualização dos inadimplentes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter data de última atualização dos inadimplentes: {str(e)}")

@app.get("/health-scores", dependencies=[Depends(verify_basic_auth)])
async def get_health_scores(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    credentials: HTTPBasicCredentials = Depends(verify_basic_auth)
):
    """
    Retorna os health scores dos clientes em JSON, indexados por tenant_id.
    
    Filtra por data de adesão OU data de cancelamento, permitindo capturar tanto
    novos clientes quanto churns no mesmo período.
    
    Args:
        data_inicio: Data inicial para filtro (formato: YYYY-MM-DD)
        data_fim: Data final para filtro (formato: YYYY-MM-DD)
    """
    try:
        # Gerar chave de cache dinâmica baseada nos filtros
        cache_key = f"health-scores:{data_inicio or 'all'}:{data_fim or 'all'}"
        
        # Verificar cache
        cached = redis.get(cache_key)
        if cached:
            logger.info(f"✅ Cache hit para {cache_key}")
            return json.loads(cached)
        
        # Usar lock para evitar múltiplas execuções simultâneas
        cache_lock = get_cache_lock(cache_key)
        
        # Tentar adquirir o lock sem bloquear
        lock_acquired = cache_lock.acquire(blocking=False)
        
        if not lock_acquired:
            # Outra thread está processando, aguardar e verificar cache novamente
            logger.info(f"⏳ Aguardando processamento em andamento para {cache_key}...")
            
            # Aguardar até 60 segundos verificando o cache periodicamente
            max_wait = 60
            wait_interval = 2
            elapsed = 0
            
            while elapsed < max_wait:
                await asyncio.sleep(wait_interval)
                elapsed += wait_interval
                
                cached = redis.get(cache_key)
                if cached:
                    logger.info(f"✅ Cache disponível após aguardar {elapsed}s: {cache_key}")
                    return json.loads(cached)
                
                logger.info(f"⏳ Ainda aguardando... ({elapsed}s/{max_wait}s)")
            
            # Após timeout, tentar adquirir o lock bloqueante
            logger.info(f"⏰ Timeout de espera, tentando adquirir lock...")
            cache_lock.acquire(blocking=True)
            logger.info(f"🔐 Lock adquirido após timeout")
        
        try:
            # Verificar cache novamente após adquirir lock
            cached = redis.get(cache_key)
            if cached:
                logger.info(f"✅ Cache hit dentro do lock para {cache_key}")
                return json.loads(cached)
            
            # Se não há cache, buscar dados
            logger.info(f"❌ Cache miss para {cache_key}, buscando dados...")
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(executor, lambda: merge_dataframes(data_inicio, data_fim))
            
            # Salvar no cache
            redis.set(cache_key, json.dumps(jsonable_encoder(result)), ex=CACHE_TTL_HEALTH_SCORES)
            logger.info(f"💾 Dados salvos no cache: {cache_key} (TTL: {CACHE_TTL_HEALTH_SCORES}s)")
            logger.info(f"🔓 Liberando lock para {cache_key}")
            
            return result
        finally:
            # Liberar o lock
            if cache_lock.locked():
                cache_lock.release()
                logger.info(f"✅ Lock liberado com sucesso para {cache_key}")
            
    except Exception as e:
        logger.error(f"Erro ao obter health scores: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter health scores: {str(e)}")

@app.get("/dashboard", dependencies=[Depends(verify_basic_auth)])
async def get_dashboard(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    credentials: HTTPBasicCredentials = Depends(verify_basic_auth)
):
    """
    Retorna os principais KPIs do sistema.
    
    Filtra por data de adesão OU data de cancelamento, permitindo analisar tanto
    novos clientes quanto churns no mesmo período.
    
    Args:
        data_inicio: Data inicial para filtro (formato: YYYY-MM-DD)
        data_fim: Data final para filtro (formato: YYYY-MM-DD)
    
    Returns:
        - clientes_ativos: Total de clientes nas pipelines CS
        - clientes_pagantes: Clientes ativos com valor > 0
        - clientes_onboarding: Clientes em onboarding sem data de finalização
        - novos_clientes: Clientes que aderiram no período (data_adesao)
        - clientes_churn: Clientes que cancelaram no período (data_cancelamento)
        - mrr_value: Receita mensal recorrente
        - churn_value: Valor total de clientes em churn
        - tmo_dias: Tempo médio de onboarding em dias
        - clientes_health: Distribuição por categoria de health score
    """
    try:
        # Gerar chave de cache dinâmica baseada nos filtros
        cache_key = f"dashboard:{data_inicio or 'all'}:{data_fim or 'all'}"
        
        # Verificar cache do dashboard
        cached = redis.get(cache_key)
        if cached:
            logger.info(f"✅ Cache hit para {cache_key}")
            return json.loads(cached)
        
        # Se não há cache, buscar dados
        logger.info(f"❌ Cache miss para {cache_key}, buscando dados...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor, 
            lambda: calculate_dashboard_kpis(data_inicio, data_fim)
        )
        
        # Salvar dashboard no cache
        redis.set(cache_key, json.dumps(jsonable_encoder(result)), ex=CACHE_TTL_DASHBOARD)
        logger.info(f"💾 Dashboard salvo no cache: {cache_key} (TTL: {CACHE_TTL_DASHBOARD}s)")

        return result
    except Exception as e:
        logger.error(f"Erro ao obter dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter dashboard: {str(e)}")

@app.post("/cache/clear", dependencies=[Depends(verify_basic_auth)])
async def clear_cache():
    """Limpa todos os caches da aplicação"""
    try:      
        # Buscar todas as chaves de cache
        clientes = redis.keys('clientes:*')
        health_scores = redis.keys('health-scores:*')
        dashboard = redis.keys('dashboard:*')
        evolution = redis.keys('evolution*')
        metricas = redis.keys('metricas-clientes')

        keys = [*clientes, *health_scores, *dashboard, *evolution, *metricas]
        logger.info(f"Limpando {len(keys)} chaves de cache...")
        print(keys)
        for key in keys:
            redis.delete(key)
            pass
        
        logger.info("Cache limpo com sucesso")
        return {
            "status": "success",
            "message": "Cache será limpo automaticamente no próximo TTL",
            "note": "Para forçar a atualização, aguarde o TTL expirar ou reinicie a aplicação"
        }
    except Exception as e:
        logger.error(f"Erro ao limpar cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao limpar cache: {str(e)}")

@app.get("/logins", dependencies=[Depends(verify_basic_auth)])
async def get_logins(tenant_id: str):
    """
    Retorna todos os registros de login de um tenant nos últimos 30 dias.
    
    Args:
        tenant_id: ID do tenant para buscar os logins
    
    Returns:
        JSON com lista de logins e estatísticas
    """
    try:
        logger.info(f"Buscando logins para tenant_id: {tenant_id}")
        
        # Gerar chave de cache baseada no tenant_id
        cache_key = f"logins:{tenant_id}"
        
        # Verificar cache
        cached = redis.get(cache_key)
        if cached:
            logger.info(f"✅ Cache hit para {cache_key}")
            return json.loads(cached)
        
        # Se não há cache, buscar dados
        logger.info(f"❌ Cache miss para {cache_key}, buscando dados...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            lambda: fetch_tenant_logins(tenant_id)
        )
        
        # Salvar no cache (TTL de 1 hora - 3600 segundos)
        CACHE_TTL_LOGINS = 60 * 60  # 1 hora
        redis.set(cache_key, json.dumps(jsonable_encoder(result)), ex=CACHE_TTL_LOGINS)
        logger.info(f"💾 Dados salvos no cache: {cache_key} (TTL: {CACHE_TTL_LOGINS}s)")
        
        return result
        
    except Exception as e:
        logger.error(f"Erro ao buscar logins: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar logins: {str(e)}")
    
@app.get("/metricas-clientes", dependencies=[Depends(verify_basic_auth)])
async def get_metricas_clientes():
    """
    Retorna todas as métricas dos clientes atuais do banco de dados.
    
    Returns:
        Lista de dicionários com as métricas dos clientes.
    """
    try:
        logger.info("Buscando métricas dos clientes atuais")
        
        # Gerar chave de cache
        cache_key = "metricas-clientes"
        
        # Verificar cache
        cached = redis.get(cache_key)
        if cached:
            logger.info(f"✅ Cache hit para {cache_key}")
            return json.loads(cached)
        
        # Se não há cache, buscar dados
        logger.info(f"❌ Cache miss para {cache_key}, buscando dados...")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            lambda: metricas_clientes()
        )
        
        # Salvar no cache
        CACHE_TTL_METRICAS = 60 * 60 * 24  # 1 dia
        redis.set(cache_key, json.dumps(jsonable_encoder(result)), ex=CACHE_TTL_METRICAS)
        logger.info(f"💾 Dados salvos no cache: {cache_key} (TTL: {CACHE_TTL_METRICAS}s)")
        
        return result
        
    except Exception as e:
        logger.error(f"Erro ao buscar métricas dos clientes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar métricas dos clientes: {str(e)}")