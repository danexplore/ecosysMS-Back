"""
Módulo de vendas e comissões.

Implementa funcionalidades para:
- Gestão de vendedores
- Cálculo de comissões
- Dashboard de vendas
- Ranking de vendedores
"""

import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, Optional, List, Literal
from dataclasses import dataclass, asdict
import logging

from ..lib.db_connection import get_conn, release_conn
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
    DASHBOARD_VENDAS_METRICS_BY_MONTH,
    SELECT_PARCELAS_PAGAS_POR_MES_COMISSAO,
    SELECT_PARCELAS_PAGAS_POR_VENDEDOR,
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
        release_conn(conn)


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


def get_setup_rate_for_tier(tier: str, config: CommissionConfig) -> float:
    """
    Retorna a taxa de setup (em decimal, ex: 0.15 para 15%) baseada no tier do vendedor.
    
    Args:
        tier: Tier do vendedor ('bronze', 'prata', 'ouro')
        config: Configuração de comissões
    
    Returns:
        Taxa de setup em decimal (ex: 0.15 para 15%)
    """
    tier_lower = (tier or 'bronze').lower()
    if tier_lower == 'ouro':
        return config.setup_tier3 / 100.0
    elif tier_lower == 'prata':
        return config.setup_tier2 / 100.0
    else:  # bronze ou default
        return config.setup_tier1 / 100.0


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
        release_conn(conn)


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
    - Se o cliente estava inadimplente naquele mês (baseado em parcelas_atrasadas), retorna inadimplente
    
    Lógica de inadimplência histórica:
    - meses_ativo = meses desde adesão até HOJE
    - parcelas_atrasadas = parcelas não pagas HOJE
    - meses_ate_referencia = meses desde adesão até o mês de referência
    - Se parcelas_atrasadas >= (meses_ativo - meses_ate_referencia + 1), estava inadimplente naquele mês
    
    Exemplo: Adesão 2025-08, hoje 2025-12, parcelas_atrasadas=2
    - meses_ativo = 5 (ago, set, out, nov, dez)
    - referência 2025-10: meses_ate_ref = 3, parcelas_nao_pagas_ate_ref = 2 - (5 - 3) = 0 → ativo
    - referência 2025-11: meses_ate_ref = 4, parcelas_nao_pagas_ate_ref = 2 - (5 - 4) = 1 → inadimplente
    - referência 2025-12: meses_ate_ref = 5, parcelas_nao_pagas_ate_ref = 2 - (5 - 5) = 2 → inadimplente
    
    Args:
        cliente: Dicionário com dados do cliente
        reference_month: Mês de referência no formato YYYY-MM (opcional)
    
    Returns:
        Status do cliente: 'ativo', 'inadimplente' ou 'cancelado'
    """
    status = cliente.get('status', '') or ''
    pipeline = cliente.get('pipeline', '') or ''
    data_cancelamento = cliente.get('data_cancelamento')
    data_adesao = cliente.get('data_adesao')
    meses_ativo = int(cliente.get('meses_ativo') or 0)
    parcelas_atrasadas = int(cliente.get('parcelas_atrasadas') or 0)
    
    # Status cancelado: CHURNS, CANCELADOS, Solicitar cancelamento ou pipeline de cancelamentos
    status_cancelado = ['churns', 'cancelados', 'solicitar cancelamento']
    is_cancelado = (
        status.lower() in status_cancelado or
        'churns & cancelamentos' in pipeline.lower()
    )
    
    # Função auxiliar para calcular meses entre duas datas YYYY-MM
    def calcular_meses_entre(data_inicio: str, data_fim: str) -> int:
        """
        Calcula quantidade de meses de COMISSÃO entre duas datas.
        O primeiro mês de comissão é o mês SEGUINTE ao mês de início.
        
        Exemplo: início nov/2025, fim dez/2025
        - Diferença: 1 mês
        - Isso significa que dezembro é o 1º mês de comissão
        
        IMPORTANTE: Não usa +1 pois a comissão começa no mês seguinte.
        """
        try:
            ano_ini, mes_ini = int(data_inicio[:4]), int(data_inicio[5:7])
            ano_fim, mes_fim = int(data_fim[:4]), int(data_fim[5:7])
            # Sem +1: mês de adesão não conta, comissão começa mês seguinte
            return (ano_fim - ano_ini) * 12 + (mes_fim - mes_ini)
        except:
            return 0
    
    # Função para verificar inadimplência histórica
    def estava_inadimplente_no_mes(ref_month: str) -> bool:
        """
        Verifica se o cliente estava inadimplente no mês de referência.
        
        Lógica: Se hoje temos X parcelas atrasadas e Y meses desde a adesão,
        no mês de referência (Z meses desde adesão) tínhamos:
        parcelas_atrasadas_no_mes = parcelas_atrasadas - (meses_ativo - meses_ate_referencia)
        
        Se parcelas_atrasadas_no_mes > 0, estava inadimplente.
        """
        if not data_adesao or meses_ativo <= 0:
            return False
        
        # Converter data_adesao para YYYY-MM
        if hasattr(data_adesao, 'strftime'):
            adesao_month = data_adesao.strftime('%Y-%m')
        else:
            adesao_month = str(data_adesao)[:7]
        
        # Calcular meses desde adesão até o mês de referência
        meses_ate_referencia = calcular_meses_entre(adesao_month, ref_month)
        
        # Se o mês de referência é antes da adesão, não estava inadimplente (nem existia)
        if meses_ate_referencia <= 0:
            return False
        
        # Calcular parcelas atrasadas naquele mês
        # parcelas_atrasadas_no_mes = parcelas_atrasadas_hoje - meses_que_passaram_depois
        meses_depois_da_referencia = meses_ativo - meses_ate_referencia
        parcelas_atrasadas_no_mes = parcelas_atrasadas - meses_depois_da_referencia
        
        return parcelas_atrasadas_no_mes > 0
    
    # Se temos um mês de referência e o cliente está cancelado, verificar se o cancelamento
    # ocorreu APÓS o mês de referência (nesse caso, era ativo ou inadimplente naquele mês)
    if reference_month and is_cancelado and data_cancelamento:
        # Converter data_cancelamento para string YYYY-MM
        if hasattr(data_cancelamento, 'strftime'):
            cancelamento_month = data_cancelamento.strftime('%Y-%m')
        else:
            cancelamento_month = str(data_cancelamento)[:7]
        
        # Se cancelou DEPOIS do mês de referência, verificar inadimplência histórica
        if cancelamento_month > reference_month:
            if estava_inadimplente_no_mes(reference_month):
                return 'inadimplente'
            return 'ativo'
    
    if is_cancelado:
        return 'cancelado'
    
    # Se temos mês de referência, verificar inadimplência histórica
    if reference_month:
        if estava_inadimplente_no_mes(reference_month):
            return 'inadimplente'
        return 'ativo'
    
    # Sem mês de referência: usar status atual baseado em parcelas_atrasadas
    if parcelas_atrasadas > 0:
        return 'inadimplente'
    
    # Todos os outros casos: ativo
    return 'ativo'


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
        release_conn(conn)


def map_cliente_to_comissao(cliente: Dict, reference_month: Optional[str] = None, vendedor_tier: str = 'bronze') -> ClienteComissao:
    """
    Mapeia um cliente do banco de dados para o formato de comissão.
    Calcula automaticamente mesesComissao, percentualComissao e valorComissao.
    
    A comissão é calculada com base na posição do mês de referência no ciclo de 7 meses
    a partir da data de adesão do cliente.
    
    Lógica:
    1. Gera os 7 meses do ciclo de comissão (mês adesão + 6 meses seguintes)
    2. Verifica se o mês de referência está dentro do ciclo
    3. Se sim, usa a taxa correspondente à posição no ciclo
    4. Verifica se o cliente estava em dia naquele mês (sem parcelas atrasadas)
    
    IMPORTANTE: O setup usa a taxa do tier do vendedor, não a taxa de recorrência MRR.
    
    Args:
        cliente: Dicionário com dados do cliente
        reference_month: Mês de referência no formato YYYY-MM (opcional).
                        Se fornecido, a comissão é calculada para esse mês.
        vendedor_tier: Tier do vendedor ('bronze', 'prata', 'ouro') para cálculo de setup.
    
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
    
    # Obter meses_ativo ATUAL (até hoje) e parcelas_atrasadas ATUAL
    meses_ativo = int(cliente.get('meses_ativo') or 0)
    parcelas_atrasadas = int(cliente.get('parcelas_atrasadas') or 0)
    
    # Calcular MRR e mês de adesão
    mrr = float(cliente.get('valor') or 0)
    setup_value = float(cliente.get('taxa_setup') or 0)
    mes_adesao = data_adesao[:7] if data_adesao else None  # YYYY-MM
    
    # Calcular comissão baseada no mês de referência
    valor_comissao = 0.0
    percentual = 0.0
    meses_comissao = 0
    
    if reference_month and mes_adesao:
        # NOVA LÓGICA: Usar histórico de pagamentos reais
        config = fetch_commission_config()
        percentual_real, valor_real, posicao = calcular_comissao_por_historico_pagamentos(
            cliente, reference_month, config
        )
        
        if posicao >= 0:
            # Comissão baseada em pagamento real encontrado
            percentual = percentual_real
            valor_comissao = valor_real
            meses_comissao = posicao + 1
        else:
            # Fallback: usar lógica estimada (sem pagamento real encontrado)
            commission_months = _get_commission_months(mes_adesao)
            
            if reference_month in commission_months:
                month_index = commission_months.index(reference_month)
                
                is_canceled_before = False
                if data_cancelamento:
                    cancel_month = data_cancelamento[:7]
                    is_canceled_before = reference_month > cancel_month
                
                if not is_canceled_before:
                    # Com base 1: meses_ativo_referencia indica quantos meses já passaram (incluindo atual)
                    meses_ativo_referencia = int(cliente.get('meses_ativo_referencia') or (month_index + 1))
                    meses_depois = meses_ativo - meses_ativo_referencia
                    parcelas_atrasadas_no_mes = max(0, parcelas_atrasadas - meses_depois)
                    meses_comissao = max(0, meses_ativo_referencia - parcelas_atrasadas_no_mes)
                    
                    # Cliente precisa ter chegado ao mês de comissão (month_index + 1 pois é base 1)
                    if meses_comissao >= month_index + 1:
                        percentual = config.mrr_recurrence[month_index] / 100.0 if month_index < len(config.mrr_recurrence) else 0.0
                        valor_comissao = mrr * percentual
                        
                        # Setup usa taxa do tier, não taxa de recorrência
                        if month_index == 0 and setup_value > 0:
                            setup_rate = get_setup_rate_for_tier(vendedor_tier, config)
                            valor_comissao += setup_value * setup_rate
    else:
        # Sem mês de referência: usar cálculo atual (meses_ativo - parcelas_atrasadas)
        meses_comissao = max(0, meses_ativo - parcelas_atrasadas)
        percentual, valor_comissao = calcular_comissao(mrr, meses_comissao)
    
    return ClienteComissao(
        id=str(cliente.get('client_id', '')),
        clientName=cliente.get('nome') or 'Cliente sem nome',
        mrr=mrr,
        setupValue=setup_value,
        date=data_adesao,
        status=status,
        sellerId=str(vendedor_id),
        sellerName=cliente.get('vendedor') or 'Venda Antiga',
        canceledAt=data_cancelamento,
        month=mes_adesao,
        mesesAtivo=meses_ativo,
        parcelasAtrasadas=parcelas_atrasadas,
        mesesComissao=meses_comissao,
        percentualComissao=percentual,
        valorComissao=valor_comissao
    )


def _get_commission_months(start_month: str) -> list:
    """
    Gera lista dos 7 meses do ciclo de comissão.
    O ciclo começa no MÊS SEGUINTE à adesão (primeira comissão é paga no mês seguinte).
    
    Exemplo: Se adesão foi em maio/2025, o ciclo é:
    - junho/2025 (30%) - primeiro mês
    - julho/2025 (20%) - segundo mês
    - agosto/2025 (10%) - terceiro mês
    - ... até dezembro/2025 (10%) - sétimo mês
    
    Args:
        start_month: Mês de adesão no formato YYYY-MM
    
    Returns:
        Lista de 7 meses no formato YYYY-MM (começando no mês SEGUINTE à adesão)
    """
    year, month = int(start_month[:4]), int(start_month[5:7])
    months = []
    
    for i in range(7):
        # Começar do mês seguinte (i + 1 ao invés de i)
        new_month = month + i + 1
        new_year = year + (new_month - 1) // 12
        new_month = ((new_month - 1) % 12) + 1
        months.append(f"{new_year}-{str(new_month).zfill(2)}")
    
    return months


# ============================================================================
# FUNÇÕES DE HISTÓRICO DE PAGAMENTOS - BASE PARA CÁLCULO DE COMISSÕES
# ============================================================================

def fetch_parcelas_pagas_por_vendedor() -> Dict[str, Dict]:
    """
    Busca todas as parcelas pagas agrupadas por vendedor.
    Retorna um dicionário com dados de pagamentos por cliente.
    
    Returns:
        Dict com cnpj como chave contendo dados de parcelas pagas
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(SELECT_PARCELAS_PAGAS_POR_VENDEDOR)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        cur.close()
        
        resultado = {}
        for row in rows:
            data = dict(zip(columns, row))
            cnpj = str(data.get('cnpj', ''))
            resultado[cnpj] = data
        
        logger.info(f"✅ Encontrados {len(resultado)} clientes com dados de pagamento")
        return resultado
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar parcelas pagas: {e}")
        return {}
    finally:
        release_conn(conn)


def fetch_parcelas_pagas_mes_comissao(mes_comissao: str) -> List[Dict]:
    """
    Busca parcelas pagas que geram comissão para um mês específico.
    O mês de comissão é o mês SEGUINTE ao vencimento da parcela paga.
    
    Lógica:
    - Cliente aderiu em maio/2025
    - Pagou parcela com vencimento junho/2025
    - Comissão cai em julho/2025 (mês seguinte ao vencimento)
    
    Args:
        mes_comissao: Mês de referência para comissão no formato YYYY-MM
    
    Returns:
        Lista de dicionários com dados das parcelas que geram comissão
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(SELECT_PARCELAS_PAGAS_POR_MES_COMISSAO, (mes_comissao,))
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        cur.close()
        
        resultado = []
        for row in rows:
            data = dict(zip(columns, row))
            resultado.append(data)
        
        logger.info(f"✅ Encontradas {len(resultado)} parcelas pagas para comissão em {mes_comissao}")
        return resultado
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar parcelas por mês de comissão: {e}")
        return []
    finally:
        release_conn(conn)


def calcular_comissao_por_historico_pagamentos(
    cliente: Dict,
    mes_referencia: str,
    config: Optional['CommissionConfig'] = None,
    vendedor_tier: str = 'bronze'
) -> tuple[float, float, int]:
    """
    Calcula comissão de um cliente baseado no histórico REAL de pagamentos.
    
    Lógica:
    1. Busca parcelas pagas do cliente na tabela historico_pagamentos
    2. Para cada parcela paga, calcula qual o mês de comissão (mês seguinte ao vencimento)
    3. Se o mes_referencia corresponde a uma parcela paga, calcula a comissão
    4. Usa a posição no ciclo (0-6) para determinar a taxa (30%, 20%, 10%...)
    
    Regra de Churn:
    - Se cliente cancelou, só paga comissão das parcelas que FORAM PAGAS
    - Se a última parcela foi paga no mês do churn, aquela comissão é paga
    - Senão, contabiliza como churn sem pagamento
    
    IMPORTANTE: O setup usa a taxa do tier do vendedor, não a taxa de recorrência MRR.
    
    Args:
        cliente: Dict com dados do cliente incluindo cnpj, data_adesao, data_cancelamento
        mes_referencia: Mês de referência para comissão (YYYY-MM)
        config: Configuração de comissões (opcional)
        vendedor_tier: Tier do vendedor para cálculo da taxa de setup
    
    Returns:
        Tupla (percentual, valor_comissao, posicao_ciclo)
    """
    if config is None:
        config = fetch_commission_config()
    
    cnpj = str(cliente.get('cnpj') or cliente.get('company_cnpj', ''))
    data_adesao = cliente.get('data_adesao')
    data_cancelamento = cliente.get('data_cancelamento')
    mrr = float(cliente.get('mrr') or cliente.get('valor') or 0)
    setup_value = float(cliente.get('taxa_setup') or 0)
    
    if not data_adesao or not cnpj:
        return (0.0, 0.0, -1)
    
    # Converter data_adesao para string se necessário
    if hasattr(data_adesao, 'strftime'):
        mes_adesao = data_adesao.strftime('%Y-%m')
    else:
        mes_adesao = str(data_adesao)[:7]
    
    # Gerar meses do ciclo de comissão (começa no mês seguinte à adesão)
    commission_months = _get_commission_months(mes_adesao)
    
    # Verificar se o mês de referência está no ciclo
    if mes_referencia not in commission_months:
        return (0.0, 0.0, -1)
    
    posicao_ciclo = commission_months.index(mes_referencia)
    
    # Buscar parcelas pagas deste cliente
    conn = get_conn()
    try:
        cur = conn.cursor()
        
        # Buscar parcela paga cujo vencimento gera comissão no mes_referencia
        # Mês de comissão = mês seguinte ao vencimento
        # Então: vencimento deve ser no mês ANTERIOR ao mes_referencia
        query = """
        SELECT 
            hp.vencimento,
            hp.data_pagamento,
            hp.parcela
        FROM historico_pagamentos hp
        WHERE hp.cnpj = %s
          AND hp.data_pagamento IS NOT NULL
          AND TO_CHAR(hp.vencimento + INTERVAL '1 month', 'YYYY-MM') = %s
        ORDER BY hp.vencimento
        LIMIT 1
        """
        cur.execute(query, (cnpj, mes_referencia))
        parcela_row = cur.fetchone()
        cur.close()
        
        if not parcela_row:
            # Não há parcela paga que gere comissão neste mês
            return (0.0, 0.0, posicao_ciclo)
        
        vencimento, data_pagamento, numero_parcela = parcela_row
        
        # Verificar regra de churn
        if data_cancelamento:
            if hasattr(data_cancelamento, 'strftime'):
                mes_cancelamento = data_cancelamento.strftime('%Y-%m')
            else:
                mes_cancelamento = str(data_cancelamento)[:7]
            
            # Se o vencimento da parcela é DEPOIS do mês de cancelamento, não paga
            if hasattr(vencimento, 'strftime'):
                mes_vencimento = vencimento.strftime('%Y-%m')
            else:
                mes_vencimento = str(vencimento)[:7]
            
            # Regra: se vencimento > mes_cancelamento, não paga comissão
            # (parcela posterior ao churn)
            if mes_vencimento > mes_cancelamento:
                return (0.0, 0.0, posicao_ciclo)
        
        # Calcular comissão
        percentual = config.mrr_recurrence[posicao_ciclo] / 100.0 if posicao_ciclo < len(config.mrr_recurrence) else 0.0
        valor_comissao = mrr * percentual
        
        # Setup só no primeiro mês do ciclo (posição 0) - usa taxa do tier
        if posicao_ciclo == 0 and setup_value > 0:
            setup_rate = get_setup_rate_for_tier(vendedor_tier, config)
            valor_comissao += setup_value * setup_rate
        
        return (percentual, valor_comissao, posicao_ciclo)
        
    except Exception as e:
        logger.error(f"❌ Erro ao calcular comissão por histórico: {e}")
        return (0.0, 0.0, -1)
    finally:
        release_conn(conn)


def fetch_comissoes_por_historico(mes_referencia: str) -> List[Dict]:
    """
    Busca todas as comissões de um mês baseado no histórico real de pagamentos.
    
    Essa função substitui o cálculo estimado por um baseado em pagamentos reais.
    
    Args:
        mes_referencia: Mês de referência para comissão (YYYY-MM)
    
    Returns:
        Lista de dicionários com dados de comissão por cliente
    """
    config = fetch_commission_config()
    parcelas = fetch_parcelas_pagas_mes_comissao(mes_referencia)
    
    comissoes = []
    for parcela in parcelas:
        posicao_ciclo = int(parcela.get('posicao_ciclo', 0))
        
        # Validar posição no ciclo (0-6)
        if posicao_ciclo < 0 or posicao_ciclo >= 7:
            continue
        
        mrr = float(parcela.get('mrr') or 0)
        setup_value = float(parcela.get('taxa_setup') or 0)
        data_cancelamento = parcela.get('data_cancelamento')
        vencimento = parcela.get('vencimento')
        
        # Verificar regra de churn
        if data_cancelamento and vencimento:
            if hasattr(data_cancelamento, 'strftime'):
                mes_cancelamento = data_cancelamento.strftime('%Y-%m')
            else:
                mes_cancelamento = str(data_cancelamento)[:7]
            
            if hasattr(vencimento, 'strftime'):
                mes_vencimento = vencimento.strftime('%Y-%m')
            else:
                mes_vencimento = str(vencimento)[:7]
            
            # Se vencimento > mês de cancelamento, não paga comissão
            if mes_vencimento > mes_cancelamento:
                continue
        
        # Calcular comissão
        percentual = config.mrr_recurrence[posicao_ciclo] / 100.0 if posicao_ciclo < len(config.mrr_recurrence) else 0.0
        valor_comissao = mrr * percentual
        
        # Setup só no primeiro mês do ciclo - usa taxa bronze como default
        # TODO: Buscar tier real do vendedor para cálculo correto
        if posicao_ciclo == 0 and setup_value > 0:
            setup_rate = config.setup_tier1 / 100.0  # Taxa bronze como padrão
            valor_comissao += setup_value * setup_rate
        
        comissoes.append({
            'vendedor': parcela.get('vendedor'),
            'cliente_id': parcela.get('cliente_id'),
            'cliente_nome': parcela.get('cliente_nome'),
            'cnpj': parcela.get('cnpj'),
            'data_adesao': parcela.get('data_adesao'),
            'data_cancelamento': data_cancelamento,
            'mrr': mrr,
            'taxa_setup': setup_value,
            'posicao_ciclo': posicao_ciclo,
            'percentual_comissao': percentual,
            'valor_comissao': valor_comissao,
            'vencimento_parcela': vencimento,
            'mes_comissao': mes_referencia,
        })
    
    logger.info(f"✅ Calculadas {len(comissoes)} comissões para {mes_referencia} baseado em pagamentos reais")
    return comissoes


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
        release_conn(conn)


def fetch_clientes_by_vendedor(vendedor_id: int, month: Optional[str] = None, vendedor_tier: str = 'bronze') -> List[ClienteComissao]:
    """
    Busca clientes de um vendedor específico.
    
    Args:
        vendedor_id: ID do vendedor
        month: Mês de referência no formato YYYY-MM (opcional)
        vendedor_tier: Tier do vendedor para cálculo de setup (default: bronze)
    
    Returns:
        Lista de objetos ClienteComissao do vendedor
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        
        if month:
            cur.execute(SELECT_CLIENTES_COMISSAO_BY_MONTH, (month, month, month))
        else:
            cur.execute(SELECT_CLIENTES_COMISSAO)
            
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        cur.close()
        
        clientes = []
        for row in rows:
            cliente_dict = dict(zip(columns, row))
            # Filtrar por vendedor
            cliente_vendedor_id = get_vendedor_id(cliente_dict.get('vendedor'))
            
            # Se for "Venda Antiga", verificar se é o cliente certo
            if vendedor_id == VENDA_ANTIGA_ID:
                if cliente_vendedor_id == VENDA_ANTIGA_ID:
                    clientes.append(map_cliente_to_comissao(cliente_dict, month, vendedor_tier))
            elif cliente_vendedor_id == vendedor_id:
                clientes.append(map_cliente_to_comissao(cliente_dict, month, vendedor_tier))
        
        logger.info(f"✅ Encontrados {len(clientes)} clientes para vendedor {vendedor_id}" + (f" (mês: {month})" if month else ""))
        return clientes
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar clientes do vendedor {vendedor_id}: {e}")
        return []
    finally:
        release_conn(conn)


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
        release_conn(conn)


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
        release_conn(conn)


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
        release_conn(conn)


def fetch_churns_mes_especifico(month: Optional[str] = None) -> List[ClienteComissao]:
    """
    Busca churns APENAS do mês específico (não histórico).
    Considera apenas clientes cancelados NAQUELE mês exato.
    
    Args:
        month: Mês de referência no formato YYYY-MM (opcional, default: mês atual)
    
    Returns:
        Lista de objetos ClienteComissao que deram churn no mês específico
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        
        if month:
            # Filtra churns onde data_cancelamento está DENTRO do mês específico
            query = """
            SELECT
                client_id,
                nome,
                vendedor,
                valor,
                taxa_setup,
                status,
                status_financeiro,
                parcelas_atrasadas,
                data_adesao,
                data_cancelamento,
                pipeline,
                GREATEST(
                    1,
                    (EXTRACT(YEAR FROM TO_DATE(%s, 'YYYY-MM')) - EXTRACT(YEAR FROM data_adesao)) * 12 +
                    (EXTRACT(MONTH FROM TO_DATE(%s, 'YYYY-MM')) - EXTRACT(MONTH FROM data_adesao)) + 1
                )::int AS meses_ativo
            FROM clientes_atual
            WHERE TO_CHAR(data_cancelamento, 'YYYY-MM') = %s
              AND valor > 0
            ORDER BY data_cancelamento DESC
            """
            cur.execute(query, (month, month, month))
        else:
            # Buscar do mês atual
            now = datetime.now()
            mes_atual = f"{now.year}-{str(now.month).zfill(2)}"
            query = """
            SELECT
                client_id,
                nome,
                vendedor,
                valor,
                taxa_setup,
                status,
                status_financeiro,
                parcelas_atrasadas,
                data_adesao,
                data_cancelamento,
                pipeline,
                GREATEST(
                    1,
                    (EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM data_adesao)) * 12 +
                    (EXTRACT(MONTH FROM CURRENT_DATE) - EXTRACT(MONTH FROM data_adesao)) + 1
                )::int AS meses_ativo
            FROM clientes_atual
            WHERE TO_CHAR(data_cancelamento, 'YYYY-MM') = %s
              AND valor > 0
            ORDER BY data_cancelamento DESC
            """
            cur.execute(query, (mes_atual,))
        
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        cur.close()
        
        clientes = []
        for row in rows:
            cliente_dict = dict(zip(columns, row))
            clientes.append(map_cliente_to_comissao(cliente_dict, month))
        
        logger.info(f"✅ Encontrados {len(clientes)} churns específicos do mês" + (f" ({month})" if month else " (atual)"))
        return clientes
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar churns específicos: {e}")
        return []
    finally:
        release_conn(conn)


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
        release_conn(conn)


def fetch_resumo_comissoes_por_vendedor(month: Optional[str] = None) -> List[Dict]:
    """
    Busca resumo de comissões por vendedor.
    
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
    
    # Buscar churns específicos do mês selecionado
    churns_do_mes = fetch_churns_mes_especifico(month)
    
    resumos = []
    for vendedor in vendedores:
        # Excluir "Venda Antiga" do resumo
        if vendedor.name == 'Venda Antiga' or vendedor.id == VENDA_ANTIGA_ID:
            continue
            
        clientes_vendedor = [c for c in all_clientes if c.sellerId == str(vendedor.id)]
        
        ativos = [c for c in clientes_vendedor if c.status == 'ativo']
        inadimplentes = [c for c in clientes_vendedor if c.status == 'inadimplente']
        # Churns apenas do mês selecionado (não histórico completo)
        cancelados_mes = [c for c in churns_do_mes if c.sellerId == str(vendedor.id)]
        
        # Vendas do mês (gamificação) - clientes que aderiram NAQUELE mês
        vendas_vendedor = [c for c in vendas_do_mes if c.sellerId == str(vendedor.id)]
        vendas_mes = len(vendas_vendedor)
        
        # Calcular tier baseado nas vendas do mês
        tier_info = get_tier_info(vendas_mes, config)
        
        # Calcular comissão total com a MESMA LÓGICA do VendedorDetails.tsx
        setup_rate = get_setup_rate_for_tier(tier_info['tier'], config)
        mrr_rates = config.mrr_recurrence if config.mrr_recurrence else [30, 20, 10, 10, 10, 10, 10]
        comissao_total = 0.0
        
        for c in ativos:
            # Verificar se cancelou antes deste mês
            if c.canceledAt:
                cancel_month = c.canceledAt[:7]
                if month and month > cancel_month:
                    continue
            
            # Verificar se o mês selecionado está no ciclo de comissão do cliente
            mes_adesao = c.month
            if not month or not mes_adesao:
                continue
                
            commission_months = _get_commission_months(mes_adesao)
            
            if month not in commission_months:
                continue
                
            month_index = commission_months.index(month)
            
            # Verificar se cliente já pagou até este mês
            # mesesComissao = meses efetivamente pagos
            meses_ativo = c.mesesAtivo or 0
            parcelas_atrasadas = c.parcelasAtrasadas or 0
            meses_comissao = max(0, meses_ativo - parcelas_atrasadas)
            
            # Só conta se já pagou este mês: mesesComissao >= monthIndex + 1
            if meses_comissao >= month_index + 1:
                # Taxa MRR baseada na posição no ciclo
                mrr_rate = mrr_rates[month_index] if month_index < len(mrr_rates) else 0
                mrr_comissao = c.mrr * mrr_rate / 100
                
                # Setup: só no primeiro mês de comissão (monthIndex == 0)
                setup_comissao = 0.0
                if month_index == 0 and c.setupValue > 0:
                    setup_comissao = c.setupValue * setup_rate
                
                comissao_total += mrr_comissao + setup_comissao
        
        resumo_dict = asdict(ResumoVendedor(
            vendedor=vendedor,
            totalClientes=len(clientes_vendedor),
            clientesAtivos=len(ativos),
            clientesInadimplentes=len(inadimplentes),
            clientesCancelados=len(cancelados_mes),
            mrrAtivo=sum(c.mrr for c in ativos),
            setupTotal=sum(c.setupValue for c in ativos),
            comissaoTotal=comissao_total,
            novosMes=vendas_mes,
            tier=tier_info['tier'],
            percentualMrr=tier_info['percentualMrr'],
            percentualSetup=tier_info['percentualSetup']
        ))
        resumo_dict['source'] = 'estimated'  # Flag para identificar fonte
        resumos.append(resumo_dict)
    
    logger.info(f"✅ Resumo estimado calculado para {len(resumos)} vendedores" + (f" (mês: {month})" if month else ""))
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
    """Calcula métricas com comissões (modo estimado)."""
    all_clientes = fetch_all_clientes_comissao(month)
    
    ativos = [c for c in all_clientes if c.status == 'ativo']
    inadimplentes = [c for c in all_clientes if c.status == 'inadimplente']
    cancelados = [c for c in all_clientes if c.status == 'cancelado']
    mrr_total = sum(c.mrr for c in ativos)
    setup_total = sum(c.setupValue for c in ativos)
    
    # Calcular comissão total (APENAS ATIVOS - clientes que vão efetivamente pagar)
    comissao_estimada = sum(c.valorComissao for c in ativos)
    
    # Calcular comissão real se month fornecido
    comissao_real = 0.0
    if month:
        try:
            comissoes_reais = fetch_comissoes_por_historico(month)
            comissao_real = sum(c.get('valor_comissao', 0) for c in comissoes_reais)
        except Exception as e:
            logger.warning(f"Não foi possível calcular comissão real: {e}")
    
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
        comissaoTotal=comissao_estimada
    )
    result = asdict(metrics)
    result['comissaoEstimada'] = comissao_estimada
    result['comissaoReal'] = comissao_real
    result['source'] = 'estimated'
    return result


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
    
    # Buscar churns específicos do mês
    churns_do_mes = fetch_churns_mes_especifico(month)
    
    # Carregar config uma vez para todas as iterações
    config = fetch_commission_config()
    
    ranking_data = []
    for vendedor in vendedores:
        # Filtrar vendedores válidos (excluir "Venda Antiga")
        if vendedor.name == 'Venda Antiga' or vendedor.id == VENDA_ANTIGA_ID:
            continue
            
        clientes_vendedor = [c for c in all_clientes if c.sellerId == str(vendedor.id)]
        ativos = [c for c in clientes_vendedor if c.status == 'ativo']
        inadimplentes = [c for c in clientes_vendedor if c.status == 'inadimplente']
        
        # Churns apenas do mês selecionado (não histórico completo)
        churns_vendedor_mes = [c for c in churns_do_mes if c.sellerId == str(vendedor.id)]
        
        # Vendas do mês (gamificação) - clientes que aderiram NAQUELE mês
        vendas_vendedor = [c for c in vendas_do_mes if c.sellerId == str(vendedor.id)]
        vendas_mes = len(vendas_vendedor)
        tier_info = get_tier_info(vendas_mes, config)
        tier = tier_info['tier']
        
        # Calcular comissão total do vendedor (APENAS ATIVOS)
        # MESMA LÓGICA DO FRONTEND (VendedorDetails.tsx)
        comissao_total = 0.0
        setup_rate = get_setup_rate_for_tier(tier, config)
        mrr_rates = config.mrr_recurrence if config.mrr_recurrence else [30, 20, 10, 10, 10, 10, 10]
        
        for cliente in ativos:
            # Verificar se cancelou antes deste mês
            if cliente.canceledAt:
                cancel_month = cliente.canceledAt[:7]
                if month and month > cancel_month:
                    continue
            
            # Verificar se o mês selecionado está no ciclo de comissão do cliente
            mes_adesao = cliente.month
            if not month or not mes_adesao:
                continue
                
            commission_months = _get_commission_months(mes_adesao)
            
            if month not in commission_months:
                continue
                
            month_index = commission_months.index(month)
            
            # Verificar se cliente já pagou até este mês
            # mesesComissao = meses efetivamente pagos
            meses_ativo = cliente.mesesAtivo or 0
            parcelas_atrasadas = cliente.parcelasAtrasadas or 0
            meses_comissao = max(0, meses_ativo - parcelas_atrasadas)
            
            # Só conta se já pagou este mês: mesesComissao >= monthIndex + 1
            if meses_comissao >= month_index + 1:
                # Taxa MRR baseada na posição no ciclo
                mrr_rate = mrr_rates[month_index] if month_index < len(mrr_rates) else 0
                mrr_comissao = cliente.mrr * mrr_rate / 100
                
                # Setup: só no primeiro mês de comissão (monthIndex == 0)
                setup_comissao = 0.0
                if month_index == 0 and cliente.setupValue > 0:
                    setup_comissao = cliente.setupValue * setup_rate
                
                comissao_total += mrr_comissao + setup_comissao
        
        ranking_data.append({
            'vendedor': asdict(vendedor),
            'mrrAtivo': sum(c.mrr for c in ativos),
            'clientesAtivos': len(ativos),
            'novosMes': vendas_mes,
            'churnsMes': len(churns_vendedor_mes),
            'posicao': 0,
            'comissaoTotal': comissao_total,
            'tier': tier,
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
    Calcula o tier do vendedor baseado nas vendas do mês para cálculo correto de setup.
    
    Args:
        vendedor_id: ID do vendedor
        month: Mês de referência no formato YYYY-MM (opcional)
    """
    # Calcular tier do vendedor baseado nas vendas do mês
    config = fetch_commission_config()
    vendas_do_mes = fetch_vendas_do_mes(month)
    vendas_vendedor = [v for v in vendas_do_mes if v.sellerId == str(vendedor_id)]
    tier_info = get_tier_info(len(vendas_vendedor), config)
    
    clientes = fetch_clientes_by_vendedor(vendedor_id, month, tier_info['tier'])
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
