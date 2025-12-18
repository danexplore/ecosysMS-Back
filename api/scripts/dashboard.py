"""Dashboard KPIs calculation."""
import logging
from typing import Dict, Optional
from decimal import Decimal
from datetime import datetime
from .clientes import fetch_clientes
from ..lib.db_connection import get_conn, release_conn

logger = logging.getLogger(__name__)

def calculate_dashboard_kpis(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
) -> Dict:
    """
    Calcula os principais KPIs do sistema.
    
    Filtra por período considerando tanto adesões quanto churns.
    
    Args:
        data_inicio: Data inicial para filtro (formato: YYYY-MM-DD)
        data_fim: Data final para filtro (formato: YYYY-MM-DD)
    
    Returns:
        Dict com os KPIs:
        - clientes_ativos: int - Clientes ativos nas pipelines CS
        - clientes_pagantes: int - Clientes ativos com valor > 0
        - clientes_onboarding: int - Clientes em onboarding sem data_end_onboarding
        - novos_clientes: int - Clientes que aderiram no período
        - clientes_churn: int - Clientes que deram churn no período
        - mrr_value: float - MRR dos clientes ativos
        - churn_value: float - Valor perdido com churns do período
        - tmo_dias: float - Tempo médio de onboarding em dias
        - inadimplentes: int - Clientes inadimplentes (parcelas_atrasadas > 0, excluindo churns)
    
    Nota: A contagem de inadimplentes usa a mesma lógica do módulo vendas.py:
          - Considera parcelas_atrasadas > 0
          - Exclui clientes com status CHURNS ou "Solicitar cancelamento"
          - Consistente com o cálculo de comissões
    """
    try:
        logger.info(f"Iniciando cálculo de KPIs do dashboard (filtro: {data_inicio} até {data_fim})...")
        
        # Buscar dados de clientes (adesões OU churns no período)
        clientes = fetch_clientes(data_inicio, data_fim)
        logger.info(f"Total de clientes no período: {len(clientes)}")
        
        # Pipelines CS consideradas ativas
        pipelines_cs_ativas = ["CS | ONBOARDING", "CS | ONGOING", "CS | BRADESCO"]
        pipeline_churn = "Churns & Cancelamentos"
        
        # Inicializar contadores
        clientes_ativos = 0
        clientes_pagantes = 0
        clientes_onboarding = 0
        novos_clientes = 0      # Aderiram no período
        clientes_churn = 0      # Deram churn no período
        mrr_value = 0.0
        churn_value = 0.0
        inadimplentes = 0
        
        # Para cálculo de TMO
        tempos_onboarding = []
        
        # Converter datas de filtro para comparação
        data_inicio_obj = None
        data_fim_obj = None
        if data_inicio:
            try:
                data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            except:
                pass
        if data_fim:
            try:
                data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
            except:
                pass
        
        # Processar clientes
        for cliente in clientes:
            pipeline = cliente.get('pipeline', '')
            status = cliente.get('status', '')
            valor = cliente.get('valor', 0)
            data_end_onboarding = cliente.get('data_end_onboarding')
            data_start_onboarding = cliente.get('data_start_onboarding')
            data_adesao = cliente.get('data_adesao')
            data_cancelamento = cliente.get('data_cancelamento')
            status_financeiro_cliente = cliente.get('status_financeiro', '')
            
            # Converter valor para float se for Decimal
            if isinstance(valor, Decimal):
                valor = float(valor)
            elif valor is None:
                valor = 0.0
            
            # Contar novos clientes (aderiram no período)
            if data_adesao:
                data_adesao_obj = None
                if isinstance(data_adesao, str):
                    try:
                        data_adesao_obj = datetime.fromisoformat(data_adesao.replace('Z', '+00:00')).date()
                    except:
                        pass
                elif isinstance(data_adesao, datetime):
                    data_adesao_obj = data_adesao.date()
                
                if data_adesao_obj:
                    adesao_no_periodo = True
                    if data_inicio_obj and data_adesao_obj < data_inicio_obj:
                        adesao_no_periodo = False
                    if data_fim_obj and data_adesao_obj > data_fim_obj:
                        adesao_no_periodo = False
                    if adesao_no_periodo:
                        novos_clientes += 1
            
            # Contar churns (cancelaram no período)
            if data_cancelamento:
                data_cancelamento_obj = None
                if isinstance(data_cancelamento, str):
                    try:
                        data_cancelamento_obj = datetime.fromisoformat(data_cancelamento.replace('Z', '+00:00')).date()
                    except:
                        pass
                elif isinstance(data_cancelamento, datetime):
                    data_cancelamento_obj = data_cancelamento.date()
                
                if data_cancelamento_obj:
                    churn_no_periodo = True
                    if data_inicio_obj and data_cancelamento_obj < data_inicio_obj:
                        churn_no_periodo = False
                    if data_fim_obj and data_cancelamento_obj > data_fim_obj:
                        churn_no_periodo = False
                    if churn_no_periodo and status in {"CHURNS", "Solicitar cancelamento"}:
                        clientes_churn += 1
                        churn_value += valor  # Somar valor perdido
            
            # Calcular TMO: clientes com data_start e data_end de onboarding
            if data_start_onboarding and data_end_onboarding:
                try:
                    if isinstance(data_start_onboarding, str):
                        data_start_onboarding = datetime.fromisoformat(data_start_onboarding.replace('Z', '+00:00'))
                    if isinstance(data_end_onboarding, str):
                        data_end_onboarding = datetime.fromisoformat(data_end_onboarding.replace('Z', '+00:00'))
                    
                    dias_onboarding = (data_end_onboarding - data_start_onboarding).days
                    if dias_onboarding > 0:  # Considerar apenas tempos positivos válidos
                        tempos_onboarding.append(dias_onboarding)
                except Exception as e:
                    logger.warning(f"Erro ao calcular TMO para cliente {cliente.get('client_id')}: {e}")
            
            # Clientes ativos: todas as pipelines CS
            if pipeline in pipelines_cs_ativas and status not in {"CHURNS", "Solicitar cancelamento"}:
                clientes_ativos += 1
                
                # Somar ao MRR
                mrr_value += valor
                
                # Clientes pagantes: valor > 0
                if valor > 0:
                    clientes_pagantes += 1
                
            # Clientes em onboarding: CS | ONBOARDING ou CS | BRADESCO sem data_end_onboarding
            if (pipeline in ["CS | ONBOARDING", "CS | BRADESCO"] and not data_end_onboarding):
                clientes_onboarding += 1
            
            # Contar inadimplentes (usar parcelas_atrasadas para ser consistente com vendas.py)
            parcelas_atrasadas_cliente = cliente.get('parcelas_atrasadas', 0) or 0
            if parcelas_atrasadas_cliente > 0 and status not in {"CHURNS", "Solicitar cancelamento"}:
                inadimplentes += 1
    
        # Calcular TMO médio
        tmo_dias = round(sum(tempos_onboarding) / len(tempos_onboarding), 1) if tempos_onboarding else 0.0
        
        logger.info(f"Clientes ativos: {clientes_ativos}")
        logger.info(f"Clientes pagantes: {clientes_pagantes}")
        logger.info(f"Clientes em onboarding: {clientes_onboarding}")
        logger.info(f"Clientes em churn: {clientes_churn}")
        logger.info(f"MRR: R$ {mrr_value:,.2f}")
        logger.info(f"Churn Value: R$ {churn_value:,.2f}")
        logger.info(f"TMO: {tmo_dias} dias (baseado em {len(tempos_onboarding)} clientes)")
        logger.info(f"Inadimplentes: {inadimplentes}")
                    
        result = {
            "clientes_ativos": clientes_ativos,
            "clientes_pagantes": clientes_pagantes,
            "clientes_onboarding": clientes_onboarding,
            "novos_clientes": novos_clientes,
            "clientes_churn": clientes_churn,
            "mrr_value": round(mrr_value, 2),
            "churn_value": round(churn_value, 2),
            "tmo_dias": tmo_dias,
            "inadimplentes": inadimplentes
        }
        
        logger.info("✅ KPIs do dashboard calculados com sucesso")
        return result
        
    except Exception as e:
        logger.error(f"Erro ao calcular KPIs do dashboard: {e}")
        raise

def data_ultima_atualizacao_inadimplentes() -> Optional[str]:
    """
    Retorna a data da última atualização dos clientes inadimplentes.
    
    Returns:
        Data da última atualização no formato string (YYYY-MM-DD) ou None se não disponível.
    """
    try:
        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT TO_CHAR(MAX(updated_at), 'DD/MM/YYYY') FROM clientes_inadimplentes
        """)
        
        ultima_atualizacao = cursor.fetchone()[0]
        logger.info(f"Data da última atualização dos inadimplentes: {ultima_atualizacao}")

        return {'data_atualizacao': ultima_atualizacao} if ultima_atualizacao else None
    except Exception as e:
        logger.error(f"Erro ao obter data da última atualização dos inadimplentes: {e}")
        return None
    finally:
        cursor.close()
        release_conn(conn)