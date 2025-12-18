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

from ..lib.db_connection import get_conn, release_conn
from ..lib.inadimplencia_queries import (
    BUSCAR_COMISSOES_PENDENTES,
    BUSCAR_RESUMO_COMISSOES,
    INSERIR_COMISSAO_PENDENTE,
    ATUALIZAR_COMISSOES_STATUS,
    BUSCAR_COMISSOES_BLOQUEADAS_POR_CNPJ,
    ATUALIZAR_COMISSAO_PARA_PAGA,
    BUSCAR_COMISSOES_LIBERADAS,
    MARCAR_COMISSOES_PERDIDAS,
    LIBERAR_COMISSOES_FIFO
)

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
# FUNÇÕES DE BANCO DE DADOS - ENCAPSULAMENTO
# ============================================================================

def _buscar_comissoes_pendentes_dados(
    vendedor_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100
) -> List[dict]:
    """Busca dados brutos de comissões pendentes."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(BUSCAR_COMISSOES_PENDENTES, (
                vendedor_id, vendedor_id, status, status, limit
            ))
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"❌ Erro ao buscar comissões pendentes: {e}")
        return []
    finally:
        release_conn(conn)


def _buscar_resumo_comissoes_dados(vendedor_id: Optional[int] = None) -> List[dict]:
    """Busca dados brutos do resumo de comissões."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(BUSCAR_RESUMO_COMISSOES, (vendedor_id, vendedor_id))
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"❌ Erro ao buscar resumo de comissões: {e}")
        return []
    finally:
        release_conn(conn)


def _inserir_comissao_pendente(dados: dict) -> bool:
    """Insere uma comissão pendente."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(INSERIR_COMISSAO_PENDENTE, (
                dados["cnpj"], dados["razao_social"], dados["vendedor_id"],
                dados["vendedor_nome"], dados["mes_referencia"], dados["parcela_numero"],
                dados["valor_mrr"], dados["percentual_aplicado"], dados["valor_comissao"],
                dados["status"], dados["motivo_bloqueio"], dados["data_bloqueio"]
            ))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"❌ Erro ao inserir comissão pendente: {e}")
        conn.rollback()
        return False
    finally:
        release_conn(conn)


def _atualizar_comissoes_status(cnpj: str, status: str, motivo: str = "") -> bool:
    """Atualiza status de comissões de um cliente."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(ATUALIZAR_COMISSOES_STATUS, (
                status, motivo, datetime.now().isoformat(), cnpj
            ))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar status de comissões: {e}")
        conn.rollback()
        return False
    finally:
        release_conn(conn)


def _buscar_comissoes_bloqueadas_por_cnpj(cnpj: str, limit: int = None) -> List[dict]:
    """Busca comissões bloqueadas de um cliente."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            params = [cnpj]
            query = BUSCAR_COMISSOES_BLOQUEADAS_POR_CNPJ
            if limit:
                query += " LIMIT %s"
                params.append(limit)

            cur.execute(query, params)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"❌ Erro ao buscar comissões bloqueadas por CNPJ: {e}")
        return []
    finally:
        release_conn(conn)


def _atualizar_comissao_para_paga(comissao_id: str) -> bool:
    """Atualiza uma comissão específica para paga."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(ATUALIZAR_COMISSAO_PARA_PAGA, (
                datetime.now().isoformat(), datetime.now().isoformat(), comissao_id
            ))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar comissão para paga: {e}")
        conn.rollback()
        return False
    finally:
        release_conn(conn)


def _buscar_comissoes_liberadas_dados(
    vendedor_id: Optional[int] = None,
    limit: int = 100
) -> List[dict]:
    """
    Busca dados brutos das comissões liberadas.

    Args:
        vendedor_id: ID do vendedor para filtrar (opcional)
        limit: Limite de registros (default 100)

    Returns:
        Lista de dicionários com dados das comissões
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(BUSCAR_COMISSOES_LIBERADAS, (vendedor_id, vendedor_id, limit))
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"❌ Erro ao buscar comissões liberadas: {e}")
        return []
    finally:
        release_conn(conn)


def _marcar_comissao_perdida(cnpj: str, motivo: str = "cancelamento") -> bool:
    """
    Marca todas as comissões bloqueadas de um cliente como perdidas.

    Args:
        cnpj: CNPJ do cliente
        motivo: Motivo da perda (default "cancelamento")

    Returns:
        True se sucesso, False caso contrário
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(MARCAR_COMISSOES_PERDIDAS, (
                motivo, datetime.now().isoformat(), cnpj
            ))
            conn.commit()
            logger.info(f"✅ Comissões marcadas como perdidas para CNPJ {cnpj}")
            return True
    except Exception as e:
        logger.error(f"❌ Erro ao marcar comissões como perdidas: {e}")
        conn.rollback()
        return False
    finally:
        release_conn(conn)


def _atualizar_comissoes_cliente_regularizado(cnpj: str, parcelas_pagas: int) -> int:
    """
    Libera comissões manualmente para um cliente que regularizou parcelas.

    Args:
        cnpj: CNPJ do cliente
        parcelas_pagas: Número de parcelas pagas

    Returns:
        Número de comissões liberadas
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # Liberar comissões por FIFO (mais antigas primeiro)
            cur.execute(LIBERAR_COMISSOES_FIFO, (
                datetime.now().isoformat(), datetime.now().isoformat(),
                cnpj, parcelas_pagas
            ))
            liberadas = cur.rowcount
            conn.commit()

            logger.info(f"✅ {liberadas} comissões liberadas para CNPJ {cnpj}")
            return liberadas
    except Exception as e:
        logger.error(f"❌ Erro ao liberar comissões: {e}")
        conn.rollback()
        return 0
    finally:
        release_conn(conn)


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
                    sucesso = _inserir_comissao_pendente(dados)
                    if sucesso:
                        registros_criados += 1
                    else:
                        registros_existentes += 1

                except Exception as e:
                    logger.error(f"❌ Erro ao inserir parcela {parcela} para {cliente.cnpj}: {e}")
                    registros_existentes += 1

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
    dados_brutos = _buscar_comissoes_pendentes_dados(vendedor_id, status, limit)

    comissoes = []
    for row in dados_brutos:
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
    dados_brutos = _buscar_comissoes_liberadas_dados(vendedor_id, limit)

    comissoes = []
    for row in dados_brutos:
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
    dados_brutos = _buscar_resumo_comissoes_dados(vendedor_id)

    resumos = []
    for row in dados_brutos:
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
    return _marcar_comissao_perdida(cnpj, motivo)


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
    return _atualizar_comissoes_cliente_regularizado(cnpj, parcelas_pagas)

