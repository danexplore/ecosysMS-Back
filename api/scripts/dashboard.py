"""Dashboard KPIs calculation."""
import logging
from typing import Dict, Optional
from decimal import Decimal
from datetime import datetime
from .clientes import fetch_clientes
from .health_scores import merge_dataframes

logger = logging.getLogger(__name__)


def calculate_dashboard_kpis(
    data_adesao_inicio: Optional[str] = None,
    data_adesao_fim: Optional[str] = None
) -> Dict:
    """
    Calcula os principais KPIs do sistema.
    
    Args:
        data_adesao_inicio: Data inicial para filtro (formato: YYYY-MM-DD)
        data_adesao_fim: Data final para filtro (formato: YYYY-MM-DD)
    
    Returns:
        Dict com os KPIs:
        - clientes_ativos: int - Soma de todas as pipelines CS (ONBOARDING, ONGOING, BRADESCO)
        - clientes_pagantes: int - Clientes ativos com valor > 0
        - clientes_onboarding: int - Clientes em CS | ONBOARDING ou CS | BRADESCO sem data_end_onboarding
        - clientes_churn: int - Clientes na pipeline "Churns & Cancelamentos"
        - mrr_value: float - MRR calculado com base nos clientes ativos
        - churn_value: float - Soma dos valores dos clientes em "Churns & Cancelamentos"
        - tmo_dias: float - Tempo médio de onboarding em dias
        - clientes_health: dict - Distribuição por categoria de health score
    """
    try:
        logger.info(f"Iniciando cálculo de KPIs do dashboard (filtro: {data_adesao_inicio} até {data_adesao_fim})...")
        
        # Buscar dados de clientes com filtro de data
        clientes = fetch_clientes(data_adesao_inicio, data_adesao_fim)
        logger.info(f"Total de clientes carregados: {len(clientes)}")
        
        # Pipelines CS consideradas ativas
        pipelines_cs_ativas = ["CS | ONBOARDING", "CS | ONGOING", "CS | BRADESCO"]
        pipeline_churn = "Churns & Cancelamentos"
        
        # Inicializar contadores
        clientes_ativos = 0
        clientes_pagantes = 0
        clientes_onboarding = 0
        clientes_churn = 0
        mrr_value = 0.0
        churn_value = 0.0
        
        # Para cálculo de TMO
        tempos_onboarding = []
        
        # Processar clientes
        for cliente in clientes:
            pipeline = cliente.get('pipeline', '')
            valor = cliente.get('valor', 0)
            data_end_onboarding = cliente.get('data_end_onboarding')
            data_start_onboarding = cliente.get('data_start_onboarding')
            
            # Converter valor para float se for Decimal
            if isinstance(valor, Decimal):
                valor = float(valor)
            elif valor is None:
                valor = 0.0
            
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
            if pipeline in pipelines_cs_ativas:
                clientes_ativos += 1
                
                # Somar ao MRR
                mrr_value += valor
                
                # Clientes pagantes: valor > 0
                if valor > 0:
                    clientes_pagantes += 1
                
                # Clientes em onboarding: CS | ONBOARDING ou CS | BRADESCO sem data_end_onboarding
                if (pipeline in ["CS | ONBOARDING", "CS | BRADESCO"]) and not data_end_onboarding:
                    clientes_onboarding += 1
            
            # Churn value: somar valores de clientes em "Churns & Cancelamentos"
            if pipeline == pipeline_churn:
                churn_value += valor
                clientes_churn += 1
        
        # Calcular TMO médio
        tmo_dias = round(sum(tempos_onboarding) / len(tempos_onboarding), 1) if tempos_onboarding else 0.0
        
        logger.info(f"Clientes ativos: {clientes_ativos}")
        logger.info(f"Clientes pagantes: {clientes_pagantes}")
        logger.info(f"Clientes em onboarding: {clientes_onboarding}")
        logger.info(f"Clientes em churn: {clientes_churn}")
        logger.info(f"MRR: R$ {mrr_value:,.2f}")
        logger.info(f"Churn Value: R$ {churn_value:,.2f}")
        logger.info(f"TMO: {tmo_dias} dias (baseado em {len(tempos_onboarding)} clientes)")
        
        # Buscar distribuição de health scores
        try:
            health_scores = merge_dataframes(data_adesao_inicio, data_adesao_fim)
            clientes_health = calculate_health_distribution(health_scores)
            logger.info(f"Distribuição de health scores: {clientes_health}")
        except Exception as e:
            logger.error(f"Erro ao calcular distribuição de health scores: {e}")
            clientes_health = {
                "Crítico": 0,
                "Normal": 0,
                "Saudável": 0,
                "Campeão": 0
            }
        
        result = {
            "clientes_ativos": clientes_ativos,
            "clientes_pagantes": clientes_pagantes,
            "clientes_onboarding": clientes_onboarding,
            "clientes_churn": clientes_churn,
            "mrr_value": round(mrr_value, 2),
            "churn_value": round(churn_value, 2),
            "tmo_dias": tmo_dias,
            "clientes_health": clientes_health
        }
        
        logger.info("✅ KPIs do dashboard calculados com sucesso")
        return result
        
    except Exception as e:
        logger.error(f"Erro ao calcular KPIs do dashboard: {e}")
        raise


def calculate_health_distribution(health_scores: Dict) -> Dict[str, int]:
    """
    Calcula a distribuição de clientes por categoria de health score.
    
    Args:
        health_scores: Dicionário com health scores dos clientes
    
    Returns:
        Dict com contagem por categoria: {"Crítico": 0, "Baixo": 0, ...}
    """
    distribution = {
        "Crítico": 0,
        "Normal": 0, 
        "Saudável": 0,
        "Campeão": 0
    }
    
    # Iterar sobre os health scores
    for tenant_id, data in health_scores.items():
        if isinstance(data, dict):
            health_level = data.get('categoria', '')
            if health_level in distribution:
                distribution[health_level] += 1
    
    return distribution
