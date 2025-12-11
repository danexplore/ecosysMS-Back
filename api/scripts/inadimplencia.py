"""
Módulo de gestão de inadimplência e comissões pendentes.

Implementa funcionalidades para:
- Processamento de snapshot de inadimplência
- Consulta de comissões pendentes (bloqueadas)
- Consulta de comissões liberadas (pagas via FIFO)
- Integração com tabela historico_pagamentos
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass, asdict
import logging
from decimal import Decimal

from supabase import create_client, Client

load_dotenv = __import__('dotenv', fromlist=['load_dotenv']).load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class ClienteInadimplente:
    """Estrutura do cliente inadimplente do snapshot semanal."""
    cnpj: str
    razao_social: str
    parcelas_atrasadas: int
    vendedor_id: Optional[int] = None
    vendedor_nome: Optional[str] = None
    valor_mrr: float = 0.0
    percentual_comissao: float = 0.0


@dataclass
class ComissaoPendente:
    """Estrutura de uma comissão pendente (bloqueada ou paga)."""
    id: str
    cnpj: str
    razao_social: str
    vendedor_id: int
    vendedor_nome: str
    mes_referencia: str
    competencia: str  # Formato MM/YYYY
    parcela_numero: int
    valor_mrr: float
    percentual_aplicado: float
    valor_comissao: float
    status: Literal['bloqueada', 'paga', 'perdida']
    motivo_bloqueio: str
    data_bloqueio: str
    data_liberacao: Optional[str] = None
    dias_bloqueada: int = 0
    recem_liberada: bool = False


@dataclass 
class ResumoComissoesPendentes:
    """Resumo de comissões pendentes por vendedor."""
    vendedor_id: int
    vendedor_nome: str
    qtd_bloqueadas: int
    qtd_pagas: int
    qtd_perdidas: int
    total_bloqueado: float
    total_pago: float
    pago_mes_atual: float


@dataclass
class ResultadoProcessamento:
    """Resultado do processamento de snapshot de inadimplência."""
    cnpj: str
    razao_social: str
    registros_criados: int
    registros_existentes: int
    sucesso: bool
    erro: Optional[str] = None


# ============================================================================
# CONEXÃO SUPABASE
# ============================================================================

_supabase_client: Optional[Client] = None


def get_supabase() -> Client:
    """Obtém cliente Supabase singleton."""
    global _supabase_client
    
    if _supabase_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL e SUPABASE_SERVICE_KEY devem estar configurados no .env")
        
        _supabase_client = create_client(supabase_url, supabase_key)
        logger.info("✅ Cliente Supabase inicializado")
    
    return _supabase_client


# ============================================================================
# FUNÇÕES DE PROCESSAMENTO DE INADIMPLÊNCIA
# ============================================================================

def processar_snapshot_inadimplencia(
    clientes: List[ClienteInadimplente]
) -> List[ResultadoProcessamento]:
    """
    Processa o snapshot semanal de inadimplência.
    
    Para cada cliente inadimplente, cria registros de comissão bloqueada
    na tabela comissoes_pendentes, um para cada parcela atrasada.
    
    A função é idempotente: registros existentes são ignorados devido
    ao constraint UNIQUE(cnpj, mes_referencia).
    
    Args:
        clientes: Lista de clientes inadimplentes do snapshot
    
    Returns:
        Lista de resultados do processamento
    """
    supabase = get_supabase()
    resultados = []
    
    for cliente in clientes:
        try:
            # Para cada parcela atrasada, criar registro retroativo
            registros_criados = 0
            registros_existentes = 0
            
            for parcela in range(1, cliente.parcelas_atrasadas + 1):
                # Calcula o mês de referência retroativamente
                # Se tem 3 parcelas atrasadas, cria para: mês-3, mês-2, mês-1
                hoje = datetime.now()
                mes_referencia = datetime(
                    hoje.year, 
                    hoje.month, 
                    1
                )
                # Subtrair meses
                for _ in range(parcela):
                    mes_referencia = mes_referencia.replace(day=1)
                    if mes_referencia.month == 1:
                        mes_referencia = mes_referencia.replace(
                            year=mes_referencia.year - 1,
                            month=12
                        )
                    else:
                        mes_referencia = mes_referencia.replace(
                            month=mes_referencia.month - 1
                        )
                
                # Calcular valor da comissão
                valor_comissao = cliente.valor_mrr * (cliente.percentual_comissao / 100)
                
                # Preparar dados para inserção
                dados = {
                    "cnpj": cliente.cnpj,
                    "razao_social": cliente.razao_social,
                    "vendedor_id": cliente.vendedor_id,
                    "vendedor_nome": cliente.vendedor_nome,
                    "mes_referencia": mes_referencia.strftime('%Y-%m-%d'),
                    "parcela_numero": parcela,
                    "valor_mrr": float(cliente.valor_mrr),
                    "percentual_aplicado": float(cliente.percentual_comissao),
                    "valor_comissao": float(valor_comissao),
                    "status": "bloqueada",
                    "motivo_bloqueio": "inadimplencia",
                    "data_bloqueio": datetime.now().isoformat()
                }
                
                # Tentar inserir (ignora se já existir)
                try:
                    result = supabase.table("comissoes_pendentes").upsert(
                        dados,
                        on_conflict="cnpj,mes_referencia",
                        ignore_duplicates=True
                    ).execute()
                    
                    if result.data:
                        registros_criados += 1
                    else:
                        registros_existentes += 1
                        
                except Exception as e:
                    if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                        registros_existentes += 1
                    else:
                        raise e
            
            resultados.append(ResultadoProcessamento(
                cnpj=cliente.cnpj,
                razao_social=cliente.razao_social,
                registros_criados=registros_criados,
                registros_existentes=registros_existentes,
                sucesso=True
            ))
            
            logger.info(
                f"✅ Processado {cliente.cnpj}: "
                f"{registros_criados} criados, {registros_existentes} existentes"
            )
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar {cliente.cnpj}: {e}")
            resultados.append(ResultadoProcessamento(
                cnpj=cliente.cnpj,
                razao_social=cliente.razao_social,
                registros_criados=0,
                registros_existentes=0,
                sucesso=False,
                erro=str(e)
            ))
    
    return resultados


# ============================================================================
# FUNÇÕES DE CONSULTA
# ============================================================================

def buscar_comissoes_pendentes(
    vendedor_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100
) -> List[ComissaoPendente]:
    """
    Busca comissões pendentes com filtros opcionais.
    
    Args:
        vendedor_id: ID do vendedor para filtrar (opcional)
        status: Status para filtrar (bloqueada/paga/perdida) (opcional)
        limit: Limite de registros (default 100)
    
    Returns:
        Lista de comissões pendentes
    """
    supabase = get_supabase()
    
    query = supabase.table("vw_comissoes_pendentes_detalhado").select("*")
    
    if vendedor_id:
        query = query.eq("vendedor_id", vendedor_id)
    
    if status:
        query = query.eq("status", status)
    
    query = query.order("mes_referencia", desc=False).limit(limit)
    
    result = query.execute()
    
    comissoes = []
    for row in result.data:
        comissoes.append(ComissaoPendente(
            id=row.get("id", ""),
            cnpj=row.get("cnpj", ""),
            razao_social=row.get("razao_social", ""),
            vendedor_id=row.get("vendedor_id", 0),
            vendedor_nome=row.get("vendedor_nome", ""),
            mes_referencia=row.get("mes_referencia", ""),
            competencia=row.get("competencia", ""),
            parcela_numero=row.get("parcela_numero", 0),
            valor_mrr=float(row.get("valor_mrr", 0)),
            percentual_aplicado=float(row.get("percentual_aplicado", 0)),
            valor_comissao=float(row.get("valor_comissao", 0)),
            status=row.get("status", "bloqueada"),
            motivo_bloqueio=row.get("motivo_bloqueio", ""),
            data_bloqueio=row.get("data_bloqueio", ""),
            data_liberacao=row.get("data_liberacao_formatada"),
            dias_bloqueada=row.get("dias_bloqueada", 0),
            recem_liberada=row.get("recem_liberada", False)
        ))
    
    logger.info(f"✅ Encontradas {len(comissoes)} comissões pendentes")
    return comissoes


def buscar_comissoes_liberadas(
    vendedor_id: Optional[int] = None,
    mes_liberacao: Optional[str] = None,
    limit: int = 100
) -> List[ComissaoPendente]:
    """
    Busca comissões que foram liberadas (pagas via FIFO).
    
    Args:
        vendedor_id: ID do vendedor para filtrar (opcional)
        mes_liberacao: Mês de liberação no formato YYYY-MM (opcional)
        limit: Limite de registros (default 100)
    
    Returns:
        Lista de comissões liberadas
    """
    supabase = get_supabase()
    
    query = supabase.table("vw_comissoes_pendentes_detalhado") \
        .select("*") \
        .eq("status", "paga")
    
    if vendedor_id:
        query = query.eq("vendedor_id", vendedor_id)
    
    # Ordenar por data de liberação mais recente primeiro
    query = query.order("data_liberacao", desc=True).limit(limit)
    
    result = query.execute()
    
    comissoes = []
    for row in result.data:
        # Filtrar por mês de liberação se especificado
        if mes_liberacao:
            data_lib = row.get("data_liberacao", "")
            if data_lib and not data_lib.startswith(mes_liberacao):
                continue
        
        comissoes.append(ComissaoPendente(
            id=row.get("id", ""),
            cnpj=row.get("cnpj", ""),
            razao_social=row.get("razao_social", ""),
            vendedor_id=row.get("vendedor_id", 0),
            vendedor_nome=row.get("vendedor_nome", ""),
            mes_referencia=row.get("mes_referencia", ""),
            competencia=row.get("competencia", ""),
            parcela_numero=row.get("parcela_numero", 0),
            valor_mrr=float(row.get("valor_mrr", 0)),
            percentual_aplicado=float(row.get("percentual_aplicado", 0)),
            valor_comissao=float(row.get("valor_comissao", 0)),
            status=row.get("status", "paga"),
            motivo_bloqueio=row.get("motivo_bloqueio", ""),
            data_bloqueio=row.get("data_bloqueio", ""),
            data_liberacao=row.get("data_liberacao_formatada"),
            dias_bloqueada=row.get("dias_bloqueada", 0),
            recem_liberada=row.get("recem_liberada", False)
        ))
    
    logger.info(f"✅ Encontradas {len(comissoes)} comissões liberadas")
    return comissoes


def buscar_resumo_comissoes(
    vendedor_id: Optional[int] = None
) -> List[ResumoComissoesPendentes]:
    """
    Busca resumo consolidado de comissões por vendedor.
    
    Args:
        vendedor_id: ID do vendedor para filtrar (opcional)
    
    Returns:
        Lista de resumos por vendedor
    """
    supabase = get_supabase()
    
    query = supabase.table("vw_comissoes_fifo_resumo").select("*")
    
    if vendedor_id:
        query = query.eq("vendedor_id", vendedor_id)
    
    result = query.execute()
    
    resumos = []
    for row in result.data:
        resumos.append(ResumoComissoesPendentes(
            vendedor_id=row.get("vendedor_id", 0),
            vendedor_nome=row.get("vendedor_nome", ""),
            qtd_bloqueadas=row.get("qtd_bloqueadas", 0),
            qtd_pagas=row.get("qtd_pagas", 0),
            qtd_perdidas=row.get("qtd_perdidas", 0),
            total_bloqueado=float(row.get("total_bloqueado", 0)),
            total_pago=float(row.get("total_pago", 0)),
            pago_mes_atual=float(row.get("pago_mes_atual", 0))
        ))
    
    logger.info(f"✅ Encontrados {len(resumos)} resumos de comissões")
    return resumos


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def marcar_comissao_perdida(cnpj: str, motivo: str = "cancelamento") -> bool:
    """
    Marca todas as comissões bloqueadas de um cliente como perdidas.
    
    Usar quando o cliente for cancelado definitivamente.
    
    Args:
        cnpj: CNPJ do cliente
        motivo: Motivo da perda (default: cancelamento)
    
    Returns:
        True se sucesso, False caso contrário
    """
    supabase = get_supabase()
    
    try:
        result = supabase.table("comissoes_pendentes") \
            .update({
                "status": "perdida",
                "motivo_bloqueio": motivo,
                "updated_at": datetime.now().isoformat()
            }) \
            .eq("cnpj", cnpj) \
            .eq("status", "bloqueada") \
            .execute()
        
        logger.info(f"✅ Comissões marcadas como perdidas para CNPJ {cnpj}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao marcar comissões como perdidas: {e}")
        return False


def atualizar_comissoes_cliente_regularizado(cnpj: str, parcelas_pagas: int) -> int:
    """
    Libera comissões manualmente para um cliente que regularizou parcelas.
    
    Usar em casos onde o webhook não disparou automaticamente.
    
    Args:
        cnpj: CNPJ do cliente
        parcelas_pagas: Quantidade de parcelas pagas
    
    Returns:
        Quantidade de comissões liberadas
    """
    supabase = get_supabase()
    
    try:
        # Buscar comissões bloqueadas mais antigas
        result = supabase.table("comissoes_pendentes") \
            .select("id") \
            .eq("cnpj", cnpj) \
            .eq("status", "bloqueada") \
            .order("mes_referencia", desc=False) \
            .limit(parcelas_pagas) \
            .execute()
        
        if not result.data:
            logger.info(f"Nenhuma comissão bloqueada encontrada para CNPJ {cnpj}")
            return 0
        
        # Atualizar cada uma para 'paga'
        liberadas = 0
        for row in result.data:
            supabase.table("comissoes_pendentes") \
                .update({
                    "status": "paga",
                    "data_liberacao": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }) \
                .eq("id", row["id"]) \
                .execute()
            liberadas += 1
        
        logger.info(f"✅ {liberadas} comissões liberadas para CNPJ {cnpj}")
        return liberadas
        
    except Exception as e:
        logger.error(f"❌ Erro ao liberar comissões: {e}")
        return 0
