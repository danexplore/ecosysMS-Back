from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.encoders import jsonable_encoder
from upstash_redis import Redis
from .scripts.clientes import clientes_to_json
import os
import warnings
from dotenv import load_dotenv
import secrets
import logging
from datetime import datetime

# Carregar variáveis de ambiente primeiro
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

async def lifespan(app: FastAPI):
    try:
        logger.info("Iniciando aplicação...")
        
        # Verificar variáveis de ambiente críticas
        required_env_vars = ["UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"Variáveis de ambiente obrigatórias não encontradas: {missing_vars}")
            raise RuntimeError(f"Variáveis de ambiente obrigatórias não encontradas: {missing_vars}")
        
        # Inicializa os usuários do Supabase
        # global users
        # logger.info("Buscando usuários do Supabase...")
        # users = await fetch_users_from_supabase()
        # if not users:
        #     logger.error("Erro ao buscar usuários do Supabase")
        #     raise RuntimeError("Erro ao buscar usuários do Supabase")

        logger.info("Aplicação iniciada com sucesso!")
        yield
        
    except Exception as e:
        logger.error(f"Erro durante a inicialização: {str(e)}")
        raise
    
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
if os.getenv("ENVIRONMENT") == "development":
    load_dotenv()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todas as origens
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
            "timestamp": datetime.now(datetime.timezone.utc).isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Health check falhou: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check falhou: {str(e)}")
    
@app.get("/clientes", dependencies=[Depends(verify_basic_auth)])
async def get_clientes():
    """Retorna a lista de clientes em JSON, indexada por client_id."""
    try:
        clientes_json = clientes_to_json()
        return jsonable_encoder(clientes_json)
    except Exception as e:
        logger.error(f"Erro ao obter clientes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter clientes: {str(e)}")