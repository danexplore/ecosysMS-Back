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
    SELECT_CLIENTES_INADIMPLENTES,
    SELECT_NOVOS_CLIENTES_MES,
    SELECT_CHURNS_MES,
    DASHBOARD_VENDAS_METRICS
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


@dataclass
class ResumoVendedor:
    vendedor: Vendedor
    totalClientes: int
    clientesAtivos: int
    clientesInadimplentes: int
    clientesCancelados: int
    mrrAtivo: float
    setupTotal: float


@dataclass
class RankingVendedor:
    vendedor: Vendedor
    mrrAtivo: float
    clientesAtivos: int
    novosMes: int
    posicao: int


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


def get_vendedor_id(vendedor_name: Optional[str]) -> int:
    """Retorna o ID do vendedor baseado no nome. Retorna VENDA_ANTIGA_ID se não encontrado."""
    if not vendedor_name:
        return VENDA_ANTIGA_ID
    normalized = vendedor_name.lower().strip()
    return VENDEDOR_MAPPING.get(normalized, VENDA_ANTIGA_ID)


# ============================================================================
# MAPEAMENTO DE STATUS
# ============================================================================

def map_status(cliente: Dict) -> Literal['ativo', 'inadimplente', 'cancelado']:
    """Mapeia o status do cliente para ativo, inadimplente ou cancelado."""
    status = cliente.get('status', '') or ''
    pipeline = cliente.get('pipeline', '') or ''
    status_financeiro = cliente.get('status_financeiro', '') or ''
    
    # Status cancelado: CHURNS, CANCELADOS, Solicitar cancelamento ou pipeline de cancelamentos
    status_cancelado = ['churns', 'cancelados', 'solicitar cancelamento']
    if (
        status.lower() in status_cancelado or
        'churns' in pipeline.lower() and 'cancelamentos' in pipeline.lower()
    ):
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


def map_cliente_to_comissao(cliente: Dict) -> ClienteComissao:
    """
    Mapeia um cliente do banco de dados para o formato de comissão.
    
    Args:
        cliente: Dicionário com dados do cliente
    
    Returns:
        Objeto ClienteComissao
    """
    vendedor_id = get_vendedor_id(cliente.get('vendedor'))
    status = map_status(cliente)
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
    
    return ClienteComissao(
        id=str(cliente.get('client_id', '')),
        clientName=cliente.get('nome') or 'Cliente sem nome',
        mrr=float(cliente.get('valor') or 0),
        setupValue=float(cliente.get('taxa_setup') or 0),
        date=data_adesao,
        status=status,
        sellerId=str(vendedor_id),
        sellerName=cliente.get('vendedor') or 'Venda Antiga',
        canceledAt=data_cancelamento,
        month=data_adesao[:7] if data_adesao else None  # YYYY-MM
    )


def fetch_all_clientes_comissao() -> List[ClienteComissao]:
    """
    Busca todos os clientes para cálculo de comissão.
    Considera apenas clientes com valor > 0.
    
    Returns:
        Lista de objetos ClienteComissao
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(SELECT_CLIENTES_COMISSAO)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        cur.close()
        
        clientes = []
        for row in rows:
            cliente_dict = dict(zip(columns, row))
            clientes.append(map_cliente_to_comissao(cliente_dict))
        
        logger.info(f"✅ Encontrados {len(clientes)} clientes para comissão")
        return clientes
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar clientes: {e}")
        return []
    finally:
        conn.close()


def fetch_clientes_by_vendedor(vendedor_id: int) -> List[ClienteComissao]:
    """
    Busca clientes de um vendedor específico.
    
    Args:
        vendedor_id: ID do vendedor
    
    Returns:
        Lista de objetos ClienteComissao do vendedor
    """
    all_clientes = fetch_all_clientes_comissao()
    
    # Se for "Venda Antiga", retornar clientes que não têm vendedor mapeado
    if vendedor_id == VENDA_ANTIGA_ID:
        return [c for c in all_clientes if c.sellerId == str(VENDA_ANTIGA_ID)]
    
    # Filtrar por vendedor específico
    return [c for c in all_clientes if c.sellerId == str(vendedor_id)]


def fetch_clientes_inadimplentes() -> List[ClienteComissao]:
    """
    Busca clientes inadimplentes.
    Considera apenas clientes com valor > 0.
    
    Returns:
        Lista de objetos ClienteComissao inadimplentes
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(SELECT_CLIENTES_INADIMPLENTES)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        cur.close()
        
        clientes = []
        for row in rows:
            cliente_dict = dict(zip(columns, row))
            clientes.append(map_cliente_to_comissao(cliente_dict))
        
        logger.info(f"✅ Encontrados {len(clientes)} clientes inadimplentes")
        return clientes
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar inadimplentes: {e}")
        return []
    finally:
        conn.close()


def fetch_novos_clientes_mes() -> List[ClienteComissao]:
    """
    Busca novos clientes do mês atual.
    Considera apenas clientes com valor > 0.
    
    Returns:
        Lista de objetos ClienteComissao novos do mês
    """
    conn = get_conn()
    try:
        now = datetime.now()
        primeiro_dia_mes = f"{now.year}-{str(now.month).zfill(2)}-01"
        
        cur = conn.cursor()
        cur.execute(SELECT_NOVOS_CLIENTES_MES, (primeiro_dia_mes,))
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        cur.close()
        
        clientes = []
        for row in rows:
            cliente_dict = dict(zip(columns, row))
            clientes.append(map_cliente_to_comissao(cliente_dict))
        
        logger.info(f"✅ Encontrados {len(clientes)} novos clientes no mês")
        return clientes
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar novos clientes: {e}")
        return []
    finally:
        conn.close()


def fetch_churns_mes() -> List[ClienteComissao]:
    """
    Busca churns do mês atual.
    Considera apenas clientes com valor > 0.
    
    Returns:
        Lista de objetos ClienteComissao que deram churn no mês
    """
    conn = get_conn()
    try:
        now = datetime.now()
        primeiro_dia_mes = f"{now.year}-{str(now.month).zfill(2)}-01"
        
        cur = conn.cursor()
        cur.execute(SELECT_CHURNS_MES, (primeiro_dia_mes,))
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        cur.close()
        
        clientes = []
        for row in rows:
            cliente_dict = dict(zip(columns, row))
            clientes.append(map_cliente_to_comissao(cliente_dict))
        
        logger.info(f"✅ Encontrados {len(clientes)} churns no mês")
        return clientes
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar churns: {e}")
        return []
    finally:
        conn.close()


def fetch_resumo_comissoes_por_vendedor() -> List[Dict]:
    """
    Busca resumo de comissões por vendedor.
    
    Returns:
        Lista de dicionários com resumo por vendedor
    """
    vendedores = fetch_vendedores()
    all_clientes = fetch_all_clientes_comissao()
    
    resumos = []
    for vendedor in vendedores:
        clientes_vendedor = [c for c in all_clientes if c.sellerId == str(vendedor.id)]
        
        ativos = [c for c in clientes_vendedor if c.status == 'ativo']
        inadimplentes = [c for c in clientes_vendedor if c.status == 'inadimplente']
        cancelados = [c for c in clientes_vendedor if c.status == 'cancelado']
        
        resumo = ResumoVendedor(
            vendedor=vendedor,
            totalClientes=len(clientes_vendedor),
            clientesAtivos=len(ativos),
            clientesInadimplentes=len(inadimplentes),
            clientesCancelados=len(cancelados),
            mrrAtivo=sum(c.mrr for c in ativos),
            setupTotal=sum(c.setupValue for c in ativos)
        )
        resumos.append(asdict(resumo))
    
    logger.info(f"✅ Resumo calculado para {len(resumos)} vendedores")
    return resumos


def fetch_dashboard_metrics() -> Dict:
    """
    Busca métricas gerais do dashboard de vendas.
    
    Returns:
        Dicionário com métricas do dashboard
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(DASHBOARD_VENDAS_METRICS)
        row = cur.fetchone()
        columns = [desc[0] for desc in cur.description]
        cur.close()
        
        if row:
            result = dict(zip(columns, row))
            metrics = DashboardMetrics(
                totalClientes=int(result.get('total_clientes', 0) or 0),
                clientesAtivos=int(result.get('clientes_ativos', 0) or 0),
                clientesInadimplentes=int(result.get('clientes_inadimplentes', 0) or 0),
                clientesCancelados=int(result.get('clientes_cancelados', 0) or 0),
                mrrTotal=float(result.get('mrr_total', 0) or 0),
                ltvTotal=0,  # Calculado separadamente se necessário
                avgMesesAtivo=float(result.get('avg_meses_ativo', 0) or 0),
                novosMesAtual=int(result.get('novos_mes_atual', 0) or 0),
                churnsMesAtual=int(result.get('churns_mes_atual', 0) or 0),
                ticketMedio=float(result.get('ticket_medio', 0) or 0)
            )
            logger.info("✅ Métricas do dashboard calculadas com sucesso")
            return asdict(metrics)
        
        # Fallback: calcular manualmente
        logger.warning("⚠️ Query de métricas falhou, calculando manualmente...")
        return _calculate_metrics_fallback()
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar métricas: {e}")
        return _calculate_metrics_fallback()
    finally:
        conn.close()


def _calculate_metrics_fallback() -> Dict:
    """Calcula métricas manualmente como fallback."""
    all_clientes = fetch_all_clientes_comissao()
    
    ativos = [c for c in all_clientes if c.status == 'ativo']
    inadimplentes = [c for c in all_clientes if c.status == 'inadimplente']
    cancelados = [c for c in all_clientes if c.status == 'cancelado']
    mrr_total = sum(c.mrr for c in ativos)
    
    now = datetime.now()
    mes_atual = f"{now.year}-{str(now.month).zfill(2)}"
    novos_mes = [c for c in all_clientes if c.month == mes_atual and c.status == 'ativo']
    churns_mes = [c for c in cancelados if c.canceledAt and c.canceledAt.startswith(mes_atual)]
    
    metrics = DashboardMetrics(
        totalClientes=len(all_clientes),
        clientesAtivos=len(ativos),
        clientesInadimplentes=len(inadimplentes),
        clientesCancelados=len(cancelados),
        mrrTotal=mrr_total,
        ltvTotal=0,
        avgMesesAtivo=0,
        novosMesAtual=len(novos_mes),
        churnsMesAtual=len(churns_mes),
        ticketMedio=mrr_total / len(ativos) if ativos else 0
    )
    return asdict(metrics)


def fetch_ranking_vendedores() -> List[Dict]:
    """
    Busca ranking de vendedores por MRR.
    
    Returns:
        Lista de dicionários com ranking de vendedores
    """
    vendedores = fetch_vendedores()
    all_clientes = fetch_all_clientes_comissao()
    novos_clientes = fetch_novos_clientes_mes()
    
    ranking_data = []
    for vendedor in vendedores:
        # Filtrar vendedores válidos (excluir "Venda Antiga")
        if vendedor.name == 'Venda Antiga':
            continue
            
        clientes_vendedor = [c for c in all_clientes if c.sellerId == str(vendedor.id)]
        ativos = [c for c in clientes_vendedor if c.status == 'ativo']
        novos = [c for c in novos_clientes if c.sellerId == str(vendedor.id)]
        
        ranking_data.append({
            'vendedor': asdict(vendedor),
            'mrrAtivo': sum(c.mrr for c in ativos),
            'clientesAtivos': len(ativos),
            'novosMes': len(novos),
            'posicao': 0
        })
    
    # Ordenar por MRR (maior para menor)
    ranking_data.sort(key=lambda x: x['mrrAtivo'], reverse=True)
    
    # Atribuir posições
    for i, item in enumerate(ranking_data):
        item['posicao'] = i + 1
    
    logger.info(f"✅ Ranking calculado para {len(ranking_data)} vendedores")
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


def get_all_clientes_as_dicts() -> List[Dict]:
    """Retorna todos os clientes como lista de dicionários."""
    clientes = fetch_all_clientes_comissao()
    return [asdict(c) for c in clientes]


def get_vendedores_as_dicts() -> List[Dict]:
    """Retorna todos os vendedores como lista de dicionários."""
    vendedores = fetch_vendedores()
    return [asdict(v) for v in vendedores]


def get_clientes_by_vendedor_as_dicts(vendedor_id: int) -> List[Dict]:
    """Retorna clientes do vendedor como lista de dicionários."""
    clientes = fetch_clientes_by_vendedor(vendedor_id)
    return [asdict(c) for c in clientes]


def get_inadimplentes_as_dicts() -> List[Dict]:
    """Retorna clientes inadimplentes como lista de dicionários."""
    clientes = fetch_clientes_inadimplentes()
    return [asdict(c) for c in clientes]


def get_novos_clientes_as_dicts() -> List[Dict]:
    """Retorna novos clientes do mês como lista de dicionários."""
    clientes = fetch_novos_clientes_mes()
    return [asdict(c) for c in clientes]


def get_churns_as_dicts() -> List[Dict]:
    """Retorna churns do mês como lista de dicionários."""
    clientes = fetch_churns_mes()
    return [asdict(c) for c in clientes]
