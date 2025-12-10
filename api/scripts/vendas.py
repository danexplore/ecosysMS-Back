"""
Módulo de vendas e comissões.

Implementa funcionalidades para:
- Gestão de vendedores
- Cálculo de comissões
- Dashboard de vendas
- Ranking de vendedores
"""

import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, Optional, List, Literal
from dataclasses import dataclass, asdict
import logging

from ..lib.queries import (
    SELECT_VENDEDORES,
    SELECT_CLIENTES_COMISSAO,
    SELECT_CLIENTES_COMISSAO_BY_MONTH,
    SELECT_CLIENTES_INADIMPLENTES,
    SELECT_CLIENTES_INADIMPLENTES_BY_MONTH,
    SELECT_NOVOS_CLIENTES_MES,
    SELECT_NOVOS_CLIENTES_BY_MONTH,
    SELECT_VENDAS_DO_MES,
    SELECT_CHURNS_MES,
    SELECT_CHURNS_BY_MONTH,
    DASHBOARD_VENDAS_METRICS,
    DASHBOARD_VENDAS_METRICS_BY_MONTH
)

load_dotenv()
logger = logging.getLogger(__name__)

# ============================================================================
# TIPOS E DATACLASSES
# ============================================================================

@dataclass
class Vendedor:
    id: int
    name: str
    email: str


@dataclass
class ClienteComissao:
    id: str
    clientName: str
    mrr: float
    setupValue: float
    date: str
    status: Literal['ativo', 'inadimplente', 'cancelado']
    sellerId: str
    sellerName: str
    canceledAt: Optional[str] = None
    month: Optional[str] = None
    mesesAtivo: int = 0
    parcelasAtrasadas: int = 0
    mesesComissao: int = 0  # mesesAtivo - parcelasAtrasadas (mínimo 0)
    percentualComissao: float = 0.0  # Percentual de comissão baseado na tabela
    valorComissao: float = 0.0  # Valor calculado da comissão


@dataclass
class ResumoVendedor:
    vendedor: Vendedor
    totalClientes: int
    clientesAtivos: int
    clientesInadimplentes: int
    clientesCancelados: int
    mrrAtivo: float
    setupTotal: float
    comissaoTotal: float = 0.0  # Soma das comissões de todos os clientes
    novosMes: int = 0  # Novos clientes no mês (vendas)
    tier: str = 'bronze'  # bronze, prata, ouro
    percentualMrr: float = 0.0  # % de comissão MRR baseado no tier
    percentualSetup: float = 0.0  # % de comissão Setup baseado no tier


@dataclass
class RankingVendedor:
    vendedor: Vendedor
    mrrAtivo: float
    clientesAtivos: int
    novosMes: int
    posicao: int
    comissaoTotal: float = 0.0  # Comissão total do vendedor
    tier: str = 'bronze'  # bronze, prata, ouro
    percentualMrr: float = 0.0  # % de comissão MRR baseado no tier
    percentualSetup: float = 0.0  # % de comissão Setup baseado no tier


@dataclass
class DashboardMetrics:
    totalClientes: int
    clientesAtivos: int
    clientesInadimplentes: int
    clientesCancelados: int
    mrrTotal: float
    ltvTotal: float
    avgMesesAtivo: float
    novosMesAtual: int
    churnsMesAtual: int
    ticketMedio: float
    comissaoTotal: float = 0.0  # Total de comissões a pagar


# ============================================================================
# MAPEAMENTO DE VENDEDORES
# ============================================================================

# Mapeamento de nomes de vendedores em clientes_atual para IDs da tabela vendedores
VENDEDOR_MAPPING: Dict[str, int] = {
    'amanda klava': 12476067,
    'amanda Klava': 12476067,
    'eduarda': 13734187,
    'eduarda oliveira': 13734187,
    'fabiana lima': 12985247,
    'marcos roberto': 12466499,
    'lindolfo silva': 14164344,
    'lindolfo pedro': 14164344,
    'jaque': 14164336,
    'jaqueline matos': 14164336,
    'gabriela lima': 14164332,
}

VENDA_ANTIGA_ID = 99999999

# ============================================================================
# CONFIGURAÇÃO DE COMISSÕES (CARREGADA DO BANCO)
# ============================================================================

@dataclass
class CommissionConfig:
    """Configuração de comissões carregada do banco de dados."""
    id: int
    sales_goal: int  # Meta de vendas para tier máximo
    mrr_tier1: float  # % MRR para 1-5 vendas
    mrr_tier2: float  # % MRR para 6-9 vendas
    mrr_tier3: float  # % MRR para 10+ vendas
    setup_tier1: float  # % Setup para 1-5 vendas
    setup_tier2: float  # % Setup para 6-9 vendas
    setup_tier3: float  # % Setup para 10+ vendas
    mrr_recurrence: List[float]  # Array de % recorrência por mês [30, 20, 10, 10, 10, 10, 10]
    updated_at: Optional[str] = None


# Cache da configuração de comissões
_commission_config_cache: Optional[CommissionConfig] = None
_commission_config_cache_time: Optional[datetime] = None
COMMISSION_CONFIG_CACHE_TTL = 3600  # 1 hora em segundos


def fetch_commission_config() -> CommissionConfig:
    """
    Busca configuração de comissões do banco de dados.
    Usa cache de 1 hora para evitar consultas frequentes.
    
    Returns:
        Objeto CommissionConfig com as configurações
    """
    global _commission_config_cache, _commission_config_cache_time
    
    # Verificar cache
    if _commission_config_cache and _commission_config_cache_time:
        elapsed = (datetime.now() - _commission_config_cache_time).total_seconds()
        if elapsed < COMMISSION_CONFIG_CACHE_TTL:
            return _commission_config_cache
    
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                id,
                sales_goal,
                mrr_tier1,
                mrr_tier2,
                mrr_tier3,
                setup_tier1,
                setup_tier2,
                setup_tier3,
                mrr_recurrence,
                updated_at
            FROM commission_config
            ORDER BY id DESC
            LIMIT 1
        """)
        row = cur.fetchone()
        cur.close()
        
        if row:
            # Converter array do PostgreSQL para lista Python
            mrr_recurrence = row[8] if row[8] else [30, 20, 10, 10, 10, 10, 10]
            if isinstance(mrr_recurrence, str):
                # Se vier como string '{30,20,10}', converter
                mrr_recurrence = [float(x) for x in mrr_recurrence.strip('{}').split(',')]
            
            config = CommissionConfig(
                id=row[0],
                sales_goal=row[1] or 10,
                mrr_tier1=float(row[2] or 5),
                mrr_tier2=float(row[3] or 10),
                mrr_tier3=float(row[4] or 20),
                setup_tier1=float(row[5] or 15),
                setup_tier2=float(row[6] or 25),
                setup_tier3=float(row[7] or 40),
                mrr_recurrence=[float(x) for x in mrr_recurrence],
                updated_at=str(row[9]) if row[9] else None
            )
            
            # Atualizar cache
            _commission_config_cache = config
            _commission_config_cache_time = datetime.now()
            
            logger.info(f"✅ Configuração de comissões carregada: {config}")
            return config
        
        # Fallback: valores padrão se não houver configuração
        logger.warning("⚠️ Nenhuma configuração de comissões encontrada, usando valores padrão")
        return _get_default_commission_config()
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar configuração de comissões: {e}")
        return _get_default_commission_config()
    finally:
        conn.close()


def _get_default_commission_config() -> CommissionConfig:
    """Retorna configuração padrão de comissões."""
    return CommissionConfig(
        id=0,
        sales_goal=10,
        mrr_tier1=5.0,
        mrr_tier2=10.0,
        mrr_tier3=20.0,
        setup_tier1=15.0,
        setup_tier2=25.0,
        setup_tier3=40.0,
        mrr_recurrence=[30.0, 20.0, 10.0, 10.0, 10.0, 10.0, 10.0]
    )


def clear_commission_config_cache():
    """Limpa o cache de configuração de comissões."""
    global _commission_config_cache, _commission_config_cache_time
    _commission_config_cache = None
    _commission_config_cache_time = None
    logger.info("🗑️ Cache de configuração de comissões limpo")


def update_commission_config(
    sales_goal: Optional[int] = None,
    mrr_tier1: Optional[float] = None,
    mrr_tier2: Optional[float] = None,
    mrr_tier3: Optional[float] = None,
    setup_tier1: Optional[float] = None,
    setup_tier2: Optional[float] = None,
    setup_tier3: Optional[float] = None,
    mrr_recurrence: Optional[List[float]] = None
) -> CommissionConfig:
    """
    Atualiza a configuração de comissões no banco de dados.
    Apenas os campos fornecidos serão atualizados.
    
    Args:
        sales_goal: Meta de vendas para tier máximo
        mrr_tier1: % MRR para 1-5 vendas
        mrr_tier2: % MRR para 6-9 vendas
        mrr_tier3: % MRR para 10+ vendas
        setup_tier1: % Setup para 1-5 vendas
        setup_tier2: % Setup para 6-9 vendas
        setup_tier3: % Setup para 10+ vendas
        mrr_recurrence: Array de % de comissão recorrente por mês
    
    Returns:
        Objeto CommissionConfig atualizado
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        
        # Construir query dinamicamente com apenas os campos fornecidos
        updates = []
        params = []
        
        if sales_goal is not None:
            updates.append("sales_goal = %s")
            params.append(sales_goal)
        
        if mrr_tier1 is not None:
            updates.append("mrr_tier1 = %s")
            params.append(mrr_tier1)
        
        if mrr_tier2 is not None:
            updates.append("mrr_tier2 = %s")
            params.append(mrr_tier2)
        
        if mrr_tier3 is not None:
            updates.append("mrr_tier3 = %s")
            params.append(mrr_tier3)
        
        if setup_tier1 is not None:
            updates.append("setup_tier1 = %s")
            params.append(setup_tier1)
        
        if setup_tier2 is not None:
            updates.append("setup_tier2 = %s")
            params.append(setup_tier2)
        
        if setup_tier3 is not None:
            updates.append("setup_tier3 = %s")
            params.append(setup_tier3)
        
        if mrr_recurrence is not None:
            # Converter lista para formato PostgreSQL array
            updates.append("mrr_recurrence = %s")
            params.append(mrr_recurrence)
        
        if not updates:
            logger.warning("⚠️ Nenhum campo para atualizar")
            return fetch_commission_config()
        
        # Adicionar updated_at
        updates.append("updated_at = NOW()")
        
        # Executar UPDATE
        query = f"""
            UPDATE commission_config 
            SET {', '.join(updates)}
            WHERE id = (SELECT id FROM commission_config ORDER BY id DESC LIMIT 1)
            RETURNING id, sales_goal, mrr_tier1, mrr_tier2, mrr_tier3,
                      setup_tier1, setup_tier2, setup_tier3, mrr_recurrence, updated_at
        """
        
        cur.execute(query, params)
        row = cur.fetchone()
        conn.commit()
        cur.close()
        
        if row:
            # Converter array do PostgreSQL para lista Python
            mrr_rec = row[8] if row[8] else [30, 20, 10, 10, 10, 10, 10]
            if isinstance(mrr_rec, str):
                mrr_rec = [float(x) for x in mrr_rec.strip('{}').split(',')]
            
            config = CommissionConfig(
                id=row[0],
                sales_goal=row[1] or 10,
                mrr_tier1=float(row[2] or 5),
                mrr_tier2=float(row[3] or 10),
                mrr_tier3=float(row[4] or 20),
                setup_tier1=float(row[5] or 15),
                setup_tier2=float(row[6] or 25),
                setup_tier3=float(row[7] or 40),
                mrr_recurrence=[float(x) for x in mrr_rec],
                updated_at=str(row[9]) if row[9] else None
            )
            
            # Limpar cache para forçar recarga
            clear_commission_config_cache()
            
            logger.info(f"✅ Configuração de comissões atualizada: {config}")
            return config
        
        raise Exception("Falha ao atualizar configuração")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Erro ao atualizar configuração de comissões: {e}")
        raise e
    finally:
        conn.close()


def get_percentual_comissao_recorrente(meses_comissao: int, config: Optional[CommissionConfig] = None) -> float:
    """
    Retorna o percentual de comissão recorrente baseado no mês.
    
    Args:
        meses_comissao: Número de meses para comissão (meses_ativo - parcelas_atrasadas)
        config: Configuração de comissões (opcional, busca do banco se não fornecida)
    
    Returns:
        Percentual de comissão (0.0 a 100.0)
    """
    if meses_comissao <= 0:
        return 0.0
    
    if config is None:
        config = fetch_commission_config()
    
    # Array é 0-indexed, meses_comissao é 1-indexed
    index = meses_comissao - 1
    
    if index < len(config.mrr_recurrence):
        return config.mrr_recurrence[index]
    
    return 0.0  # Após o período de recorrência, não há mais comissão


def get_tier_info(vendas_mes: int, config: Optional[CommissionConfig] = None) -> dict:
    """
    Retorna informações do tier (gamificação) baseado nas vendas do mês.
    
    Tiers:
    - Bronze: 1-5 vendas no mês
    - Prata: 6-9 vendas no mês  
    - Ouro: 10+ vendas no mês (ou >= sales_goal)
    
    Args:
        vendas_mes: Número de vendas (novos clientes) no mês
        config: Configuração de comissões (opcional, busca do banco se não fornecida)
    
    Returns:
        Dict com tier, percentualMrr e percentualSetup
    """
    if config is None:
        config = fetch_commission_config()
    
    sales_goal = config.sales_goal  # Meta para tier máximo (default 10)
    
    # Determinar tier baseado nas vendas do mês
    if vendas_mes >= sales_goal:
        # Ouro: atingiu ou superou a meta
        return {
            'tier': 'ouro',
            'percentualMrr': config.mrr_tier3,
            'percentualSetup': config.setup_tier3
        }
    elif vendas_mes >= 6:
        # Prata: 6-9 vendas (ou 6 até sales_goal-1)
        return {
            'tier': 'prata',
            'percentualMrr': config.mrr_tier2,
            'percentualSetup': config.setup_tier2
        }
    else:
        # Bronze: 1-5 vendas (ou 0-5)
        return {
            'tier': 'bronze',
            'percentualMrr': config.mrr_tier1,
            'percentualSetup': config.setup_tier1
        }


def calcular_comissao(mrr: float, meses_comissao: int, config: Optional[CommissionConfig] = None) -> tuple[float, float]:
    """
    Calcula a comissão recorrente baseada no MRR e meses de comissão.
    
    Args:
        mrr: Valor do MRR do cliente
        meses_comissao: Número de meses para comissão (meses_ativo - parcelas_atrasadas)
        config: Configuração de comissões (opcional)
    
    Returns:
        Tupla (percentual em decimal, valor_comissao)
    """
    percentual = get_percentual_comissao_recorrente(meses_comissao, config)
    # Converter de porcentagem (30) para decimal (0.30)
    percentual_decimal = percentual / 100.0
    valor = mrr * percentual_decimal
    return (percentual_decimal, valor)


def get_vendedor_id(vendedor_name: Optional[str]) -> int:
    """Retorna o ID do vendedor baseado no nome. Retorna VENDA_ANTIGA_ID se não encontrado."""
    if not vendedor_name:
        return VENDA_ANTIGA_ID
    normalized = vendedor_name.lower().strip()
    return VENDEDOR_MAPPING.get(normalized, VENDA_ANTIGA_ID)


# ============================================================================
# MAPEAMENTO DE STATUS
# ============================================================================

def map_status(cliente: Dict, reference_month: Optional[str] = None) -> Literal['ativo', 'inadimplente', 'cancelado']:
    """
    Mapeia o status do cliente para ativo, inadimplente ou cancelado.
    
    Se reference_month for fornecido, considera o status DO CLIENTE NAQUELE MÊS:
    - Se o cliente cancelou DEPOIS do mês de referência, é considerado ATIVO naquele mês
    
    Args:
        cliente: Dicionário com dados do cliente
        reference_month: Mês de referência no formato YYYY-MM (opcional)
    
    Returns:
        Status do cliente: 'ativo', 'inadimplente' ou 'cancelado'
    """
    status = cliente.get('status', '') or ''
    pipeline = cliente.get('pipeline', '') or ''
    status_financeiro = cliente.get('status_financeiro', '') or ''
    data_cancelamento = cliente.get('data_cancelamento')
    
    # Status cancelado: CHURNS, CANCELADOS, Solicitar cancelamento ou pipeline de cancelamentos
    status_cancelado = ['churns', 'cancelados', 'solicitar cancelamento']
    is_cancelado = (
        status.lower() in status_cancelado or
        'churns' in pipeline.lower() and 'cancelamentos' in pipeline.lower()
    )
    
    # Se temos um mês de referência e o cliente está cancelado, verificar se o cancelamento
    # ocorreu APÓS o mês de referência (nesse caso, era ativo naquele mês)
    if reference_month and is_cancelado and data_cancelamento:
        # Converter data_cancelamento para string YYYY-MM
        if hasattr(data_cancelamento, 'strftime'):
            cancelamento_month = data_cancelamento.strftime('%Y-%m')
        else:
            cancelamento_month = str(data_cancelamento)[:7]
        
        # Se cancelou DEPOIS do mês de referência, era ativo naquele mês
        if cancelamento_month > reference_month:
            # Verificar se era inadimplente naquele mês
            if status_financeiro.lower() == 'inadimplente':
                return 'inadimplente'
            return 'ativo'
    
    if is_cancelado:
        return 'cancelado'
    
    # Status inadimplente: status_financeiro = 'inadimplente'
    if status_financeiro.lower() == 'inadimplente':
        return 'inadimplente'
    
    # Todos os outros casos: ativo
    return 'ativo'


# ============================================================================
# CONEXÃO COM BANCO DE DADOS
# ============================================================================

def get_conn():
    """Cria conexão com o banco PostgreSQL."""
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )
    return conn


# ============================================================================
# FUNÇÕES DE SERVIÇO
# ============================================================================

def fetch_vendedores() -> List[Vendedor]:
    """
    Busca lista de vendedores ativos do banco de dados.
    
    Returns:
        Lista de objetos Vendedor
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(SELECT_VENDEDORES)
        rows = cur.fetchall()
        cur.close()
        
        vendedores = []
        for row in rows:
            vendedores.append(Vendedor(
                id=row[0],
                name=row[1],
                email=row[2]
            ))
        
        logger.info(f"✅ Encontrados {len(vendedores)} vendedores")
        return vendedores
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar vendedores: {e}")
        return []
    finally:
        conn.close()


def map_cliente_to_comissao(cliente: Dict, reference_month: Optional[str] = None) -> ClienteComissao:
    """
    Mapeia um cliente do banco de dados para o formato de comissão.
    Calcula automaticamente mesesComissao, percentualComissao e valorComissao.
    
    Args:
        cliente: Dicionário com dados do cliente
        reference_month: Mês de referência no formato YYYY-MM (opcional).
                        Se fornecido, o status é calculado considerando esse mês.
    
    Returns:
        Objeto ClienteComissao com comissão calculada
    """
    vendedor_id = get_vendedor_id(cliente.get('vendedor'))
    status = map_status(cliente, reference_month)
    data_adesao = cliente.get('data_adesao')
    
    # Converter data_adesao para string se necessário
    if data_adesao:
        if isinstance(data_adesao, datetime):
            data_adesao = data_adesao.strftime('%Y-%m-%d')
        elif hasattr(data_adesao, 'isoformat'):
            data_adesao = data_adesao.isoformat()[:10]
        else:
            data_adesao = str(data_adesao)[:10]
    else:
        data_adesao = datetime.now().strftime('%Y-%m-%d')
    
    # Converter data_cancelamento se existir
    data_cancelamento = cliente.get('data_cancelamento')
    if data_cancelamento:
        if isinstance(data_cancelamento, datetime):
            data_cancelamento = data_cancelamento.strftime('%Y-%m-%d')
        elif hasattr(data_cancelamento, 'isoformat'):
            data_cancelamento = data_cancelamento.isoformat()[:10]
        else:
            data_cancelamento = str(data_cancelamento)[:10]
    
    # Obter meses_ativo e parcelas_atrasadas
    meses_ativo = int(cliente.get('meses_ativo') or 0)
    parcelas_atrasadas = int(cliente.get('parcelas_atrasadas') or 0)
    
    # Calcular meses de comissão: meses_ativo - parcelas_atrasadas (mínimo 0)
    meses_comissao = max(0, meses_ativo - parcelas_atrasadas)
    
    # Calcular comissão baseada na tabela progressiva
    mrr = float(cliente.get('valor') or 0)
    percentual, valor_comissao = calcular_comissao(mrr, meses_comissao)
    
    return ClienteComissao(
        id=str(cliente.get('client_id', '')),
        clientName=cliente.get('nome') or 'Cliente sem nome',
        mrr=mrr,
        setupValue=float(cliente.get('taxa_setup') or 0),
        date=data_adesao,
        status=status,
        sellerId=str(vendedor_id),
        sellerName=cliente.get('vendedor') or 'Venda Antiga',
        canceledAt=data_cancelamento,
        month=data_adesao[:7] if data_adesao else None,  # YYYY-MM
        mesesAtivo=meses_ativo,
        parcelasAtrasadas=parcelas_atrasadas,
        mesesComissao=meses_comissao,
        percentualComissao=percentual,
        valorComissao=valor_comissao
    )


def fetch_all_clientes_comissao(month: Optional[str] = None) -> List[ClienteComissao]:
    """
    Busca todos os clientes para cálculo de comissão.
    Considera apenas clientes com valor > 0.
    
    Args:
        month: Mês de referência no formato YYYY-MM (opcional)
    
    Returns:
        Lista de objetos ClienteComissao
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        
        if month:
            # Passa o mês 3 vezes: 2x para cálculo de meses_ativo, 1x para filtro de data
            cur.execute(SELECT_CLIENTES_COMISSAO_BY_MONTH, (month, month, month))
        else:
            cur.execute(SELECT_CLIENTES_COMISSAO)
            
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        cur.close()
        
        clientes = []
        for row in rows:
            cliente_dict = dict(zip(columns, row))
            clientes.append(map_cliente_to_comissao(cliente_dict, month))
        
        logger.info(f"✅ Encontrados {len(clientes)} clientes para comissão" + (f" (até mês: {month})" if month else ""))
        return clientes
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar clientes: {e}")
        return []
    finally:
        conn.close()


def fetch_clientes_by_vendedor(vendedor_id: int, month: Optional[str] = None) -> List[ClienteComissao]:
    """
    Busca clientes de um vendedor específico.
    
    Args:
        vendedor_id: ID do vendedor
        month: Mês de referência no formato YYYY-MM (opcional)
    
    Returns:
        Lista de objetos ClienteComissao do vendedor
    """
    all_clientes = fetch_all_clientes_comissao(month)
    
    # Se for "Venda Antiga", retornar clientes que não têm vendedor mapeado
    if vendedor_id == VENDA_ANTIGA_ID:
        return [c for c in all_clientes if c.sellerId == str(VENDA_ANTIGA_ID)]
    
    # Filtrar por vendedor específico
    return [c for c in all_clientes if c.sellerId == str(vendedor_id)]


def fetch_clientes_inadimplentes(month: Optional[str] = None) -> List[ClienteComissao]:
    """
    Busca clientes inadimplentes.
    Considera apenas clientes com valor > 0.
    
    Args:
        month: Mês de referência no formato YYYY-MM (opcional)
    
    Returns:
        Lista de objetos ClienteComissao inadimplentes
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        
        if month:
            # Passa o mês 3 vezes: 2x para cálculo de meses_ativo, 1x para filtro de data
            cur.execute(SELECT_CLIENTES_INADIMPLENTES_BY_MONTH, (month, month, month))
        else:
            cur.execute(SELECT_CLIENTES_INADIMPLENTES)
            
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        cur.close()
        
        clientes = []
        for row in rows:
            cliente_dict = dict(zip(columns, row))
            clientes.append(map_cliente_to_comissao(cliente_dict, month))
        
        logger.info(f"✅ Encontrados {len(clientes)} clientes inadimplentes" + (f" (até mês: {month})" if month else ""))
        return clientes
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar inadimplentes: {e}")
        return []
    finally:
        conn.close()


def fetch_novos_clientes_mes(month: Optional[str] = None) -> List[ClienteComissao]:
    """
    Busca novos clientes do mês.
    Considera apenas clientes com valor > 0.
    
    Args:
        month: Mês de referência no formato YYYY-MM (opcional, default: mês atual)
    
    Returns:
        Lista de objetos ClienteComissao novos do mês
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        
        if month:
            # Passa o mês 3 vezes: 2x para cálculo de meses_ativo, 1x para filtro de data
            cur.execute(SELECT_NOVOS_CLIENTES_BY_MONTH, (month, month, month))
        else:
            # Buscar do mês atual (comportamento original)
            now = datetime.now()
            primeiro_dia_mes = f"{now.year}-{str(now.month).zfill(2)}-01"
            cur.execute(SELECT_NOVOS_CLIENTES_MES, (primeiro_dia_mes,))
        
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        cur.close()
        
        clientes = []
        for row in rows:
            cliente_dict = dict(zip(columns, row))
            clientes.append(map_cliente_to_comissao(cliente_dict, month))
        
        logger.info(f"✅ Encontrados {len(clientes)} novos clientes" + (f" (até mês: {month})" if month else " no mês atual"))
        return clientes
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar novos clientes: {e}")
        return []
    finally:
        conn.close()


def fetch_vendas_do_mes(month: Optional[str] = None) -> List[ClienteComissao]:
    """
    Busca vendas (novos clientes) de um mês específico para cálculo de gamificação.
    Diferente de fetch_novos_clientes_mes, esta função sempre retorna apenas os clientes
    que aderiram NAQUELE mês específico (não "até" o mês).
    
    Args:
        month: Mês de referência no formato YYYY-MM (opcional, default: mês atual)
    
    Returns:
        Lista de objetos ClienteComissao que aderiram naquele mês
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        
        # Determinar mês de referência
        if not month:
            now = datetime.now()
            month = f"{now.year}-{str(now.month).zfill(2)}"
        
        # Buscar clientes que aderiram NAQUELE mês específico
        cur.execute(SELECT_VENDAS_DO_MES, (month,))
        
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        cur.close()
        
        clientes = []
        for row in rows:
            cliente_dict = dict(zip(columns, row))
            clientes.append(map_cliente_to_comissao(cliente_dict, month))
        
        logger.info(f"✅ Encontradas {len(clientes)} vendas no mês {month}")
        return clientes
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar vendas do mês: {e}")
        return []
    finally:
        conn.close()


def fetch_churns_mes(month: Optional[str] = None) -> List[ClienteComissao]:
    """
    Busca churns do mês.
    Considera apenas clientes com valor > 0.
    
    Args:
        month: Mês de referência no formato YYYY-MM (opcional, default: mês atual)
    
    Returns:
        Lista de objetos ClienteComissao que deram churn no mês
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        
        if month:
            # Passa o mês 3 vezes: 2x para cálculo de meses_ativo, 1x para filtro de data
            cur.execute(SELECT_CHURNS_BY_MONTH, (month, month, month))
        else:
            # Buscar do mês atual (comportamento original)
            now = datetime.now()
            primeiro_dia_mes = f"{now.year}-{str(now.month).zfill(2)}-01"
            cur.execute(SELECT_CHURNS_MES, (primeiro_dia_mes,))
        
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        cur.close()
        
        clientes = []
        for row in rows:
            cliente_dict = dict(zip(columns, row))
            clientes.append(map_cliente_to_comissao(cliente_dict, month))
        
        logger.info(f"✅ Encontrados {len(clientes)} churns" + (f" (até mês: {month})" if month else " no mês atual"))
        return clientes
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar churns: {e}")
        return []
    finally:
        conn.close()


def fetch_resumo_comissoes_por_vendedor(month: Optional[str] = None) -> List[Dict]:
    """
    Busca resumo de comissões por vendedor.
    O filtro por mês afeta apenas a listagem de clientes que aderiram naquele mês,
    mas o cálculo de comissão considera meses_ativo e parcelas_atrasadas do banco.
    
    Args:
        month: Mês de referência no formato YYYY-MM (opcional)
    
    Returns:
        Lista de dicionários com resumo por vendedor
    """
    vendedores = fetch_vendedores()
    all_clientes = fetch_all_clientes_comissao(month)
    
    # Buscar vendas do mês específico para calcular tier (gamificação)
    # Usa fetch_vendas_do_mes que retorna apenas clientes daquele mês específico
    vendas_do_mes = fetch_vendas_do_mes(month)
    
    # Carregar config uma vez para todas as iterações
    config = fetch_commission_config()
    
    resumos = []
    for vendedor in vendedores:
        clientes_vendedor = [c for c in all_clientes if c.sellerId == str(vendedor.id)]
        
        ativos = [c for c in clientes_vendedor if c.status == 'ativo']
        inadimplentes = [c for c in clientes_vendedor if c.status == 'inadimplente']
        cancelados = [c for c in clientes_vendedor if c.status == 'cancelado']
        
        # Vendas do mês (gamificação) - clientes que aderiram NAQUELE mês
        vendas_vendedor = [c for c in vendas_do_mes if c.sellerId == str(vendedor.id)]
        vendas_mes = len(vendas_vendedor)
        
        # Calcular tier baseado nas vendas do mês
        tier_info = get_tier_info(vendas_mes, config)
        
        # Calcular comissão total de todos os clientes elegíveis (ativos e inadimplentes)
        # Inadimplentes também geram comissão, mas com meses_comissao ajustado
        clientes_comissao = ativos + inadimplentes
        comissao_total = sum(c.valorComissao for c in clientes_comissao)
        
        resumo = ResumoVendedor(
            vendedor=vendedor,
            totalClientes=len(clientes_vendedor),
            clientesAtivos=len(ativos),
            clientesInadimplentes=len(inadimplentes),
            clientesCancelados=len(cancelados),
            mrrAtivo=sum(c.mrr for c in ativos),
            setupTotal=sum(c.setupValue for c in ativos),
            comissaoTotal=comissao_total,
            novosMes=vendas_mes,
            tier=tier_info['tier'],
            percentualMrr=tier_info['percentualMrr'],
            percentualSetup=tier_info['percentualSetup']
        )
        resumos.append(asdict(resumo))
    
    logger.info(f"✅ Resumo calculado para {len(resumos)} vendedores" + (f" (mês: {month})" if month else ""))
    return resumos


def fetch_dashboard_metrics(month: Optional[str] = None) -> Dict:
    """
    Busca métricas gerais do dashboard de vendas.
    Inclui o total de comissões a pagar baseado na tabela progressiva.
    
    Args:
        month: Mês de referência no formato YYYY-MM (opcional)
    
    Returns:
        Dicionário com métricas do dashboard
    """
    # Sempre calcular via fallback para incluir comissões corretamente
    return _calculate_metrics_fallback(month)


def _calculate_metrics_fallback(month: Optional[str] = None) -> Dict:
    """Calcula métricas com comissões."""
    all_clientes = fetch_all_clientes_comissao(month)
    
    ativos = [c for c in all_clientes if c.status == 'ativo']
    inadimplentes = [c for c in all_clientes if c.status == 'inadimplente']
    cancelados = [c for c in all_clientes if c.status == 'cancelado']
    mrr_total = sum(c.mrr for c in ativos)
    setup_total = sum(c.setupValue for c in ativos)
    
    # Calcular comissão total (ativos + inadimplentes, já calculada no mapeamento)
    clientes_comissao = ativos + inadimplentes
    comissao_total = sum(c.valorComissao for c in clientes_comissao)
    
    if month:
        # Se filtrado por mês, novos = todos do mês, churns = cancelados do mês
        novos_mes = all_clientes
        churns_mes = fetch_churns_mes(month)
    else:
        now = datetime.now()
        mes_atual = f"{now.year}-{str(now.month).zfill(2)}"
        novos_mes = [c for c in all_clientes if c.month == mes_atual and c.status == 'ativo']
        churns_mes = [c for c in cancelados if c.canceledAt and c.canceledAt.startswith(mes_atual)]
    
    # Calcular média de meses ativos
    avg_meses = sum(c.mesesAtivo for c in ativos) / len(ativos) if ativos else 0
    
    metrics = DashboardMetrics(
        totalClientes=len(all_clientes),
        clientesAtivos=len(ativos),
        clientesInadimplentes=len(inadimplentes),
        clientesCancelados=len(cancelados),
        mrrTotal=mrr_total,
        ltvTotal=setup_total if month else 0,
        avgMesesAtivo=round(avg_meses, 2),
        novosMesAtual=len(novos_mes),
        churnsMesAtual=len(churns_mes) if isinstance(churns_mes, list) else 0,
        ticketMedio=mrr_total / len(ativos) if ativos else 0,
        comissaoTotal=comissao_total
    )
    return asdict(metrics)


def fetch_ranking_vendedores(month: Optional[str] = None) -> List[Dict]:
    """
    Busca ranking de vendedores por MRR.
    Inclui comissão total por vendedor e tier de gamificação.
    
    Args:
        month: Mês de referência no formato YYYY-MM (opcional)
    
    Returns:
        Lista de dicionários com ranking de vendedores
    """
    vendedores = fetch_vendedores()
    all_clientes = fetch_all_clientes_comissao(month)
    
    # Buscar vendas do mês específico para calcular tier (gamificação)
    vendas_do_mes = fetch_vendas_do_mes(month)
    
    # Carregar config uma vez para todas as iterações
    config = fetch_commission_config()
    
    ranking_data = []
    for vendedor in vendedores:
        # Filtrar vendedores válidos (excluir "Venda Antiga")
        if vendedor.name == 'Venda Antiga':
            continue
            
        clientes_vendedor = [c for c in all_clientes if c.sellerId == str(vendedor.id)]
        ativos = [c for c in clientes_vendedor if c.status == 'ativo']
        inadimplentes = [c for c in clientes_vendedor if c.status == 'inadimplente']
        
        # Vendas do mês (gamificação) - clientes que aderiram NAQUELE mês
        vendas_vendedor = [c for c in vendas_do_mes if c.sellerId == str(vendedor.id)]
        vendas_mes = len(vendas_vendedor)
        tier_info = get_tier_info(vendas_mes, config)
        
        # Calcular comissão total do vendedor
        clientes_comissao = ativos + inadimplentes
        comissao_total = sum(c.valorComissao for c in clientes_comissao)
        
        ranking_data.append({
            'vendedor': asdict(vendedor),
            'mrrAtivo': sum(c.mrr for c in ativos),
            'clientesAtivos': len(ativos),
            'novosMes': vendas_mes,
            'posicao': 0,
            'comissaoTotal': comissao_total,
            'tier': tier_info['tier'],
            'percentualMrr': tier_info['percentualMrr'],
            'percentualSetup': tier_info['percentualSetup']
        })
    
    # Ordenar por MRR (maior para menor)
    ranking_data.sort(key=lambda x: x['mrrAtivo'], reverse=True)
    
    # Atribuir posições
    for i, item in enumerate(ranking_data):
        item['posicao'] = i + 1
    
    logger.info(f"✅ Ranking calculado para {len(ranking_data)} vendedores" + (f" (mês: {month})" if month else ""))
    return ranking_data

# ============================================================================
# FUNÇÕES AUXILIARES PARA SERIALIZAÇÃO
# ============================================================================

def cliente_comissao_to_dict(cliente: ClienteComissao) -> Dict:
    """Converte ClienteComissao para dicionário."""
    return asdict(cliente)


def vendedor_to_dict(vendedor: Vendedor) -> Dict:
    """Converte Vendedor para dicionário."""
    return asdict(vendedor)


def get_all_clientes_as_dicts(month: Optional[str] = None) -> List[Dict]:
    """
    Retorna todos os clientes como lista de dicionários.
    
    Args:
        month: Mês de referência no formato YYYY-MM (opcional)
    """
    clientes = fetch_all_clientes_comissao(month)
    return [asdict(c) for c in clientes]


def get_vendedores_as_dicts() -> List[Dict]:
    """Retorna todos os vendedores como lista de dicionários."""
    vendedores = fetch_vendedores()
    return [asdict(v) for v in vendedores]


def get_clientes_by_vendedor_as_dicts(vendedor_id: int, month: Optional[str] = None) -> List[Dict]:
    """
    Retorna clientes do vendedor como lista de dicionários.
    
    Args:
        vendedor_id: ID do vendedor
        month: Mês de referência no formato YYYY-MM (opcional)
    """
    clientes = fetch_clientes_by_vendedor(vendedor_id, month)
    return [asdict(c) for c in clientes]


def get_inadimplentes_as_dicts(month: Optional[str] = None) -> List[Dict]:
    """
    Retorna clientes inadimplentes como lista de dicionários.
    
    Args:
        month: Mês de referência no formato YYYY-MM (opcional)
    """
    clientes = fetch_clientes_inadimplentes(month)
    return [asdict(c) for c in clientes]


def get_novos_clientes_as_dicts(month: Optional[str] = None) -> List[Dict]:
    """
    Retorna novos clientes do mês como lista de dicionários.
    
    Args:
        month: Mês de referência no formato YYYY-MM (opcional)
    """
    clientes = fetch_novos_clientes_mes(month)
    return [asdict(c) for c in clientes]


def get_churns_as_dicts(month: Optional[str] = None) -> List[Dict]:
    """
    Retorna churns do mês como lista de dicionários.
    
    Args:
        month: Mês de referência no formato YYYY-MM (opcional)
    """
    clientes = fetch_churns_mes(month)
    return [asdict(c) for c in clientes]
