import psycopg2
import os
from dotenv import load_dotenv
import json
import datetime
from ..lib.queries import SELECT_CLIENTES, LOGINS_BY_TENANT
from ..lib.models import Cliente
from typing import Dict, Optional, List
import logging

load_dotenv()
logger = logging.getLogger(__name__)

def get_conn():
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )
    return conn

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))

def sanitize_for_json(obj):
    """Recursively convert date/datetime objects to ISO strings in structures."""
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    return obj

def fetch_clientes(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
) -> List[Dict]:
    """
    Busca clientes do banco PostgreSQL.
    
    Filtra por período considerando TANTO clientes que aderiram 
    quanto clientes que deram churn no período especificado.
    
    Args:
        data_inicio: Data inicial para filtro (formato: YYYY-MM-DD)
        data_fim: Data final para filtro (formato: YYYY-MM-DD)
    
    Returns:
        Lista de dicionários com dados dos clientes que:
        - Aderiram no período (data_adesao) OU
        - Deram churn no período (data_cancelamento)
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(SELECT_CLIENTES)
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]

    results = []
    for row in rows:
        cliente = dict(zip(columns, row))
        
        # Aplicar filtro de data se fornecido
        if data_inicio or data_fim:
            data_adesao = cliente.get('data_adesao')
            data_cancelamento = cliente.get('data_cancelamento')
            
            # Converter data_adesao para date
            if data_adesao and isinstance(data_adesao, str):
                try:
                    data_adesao = datetime.datetime.fromisoformat(data_adesao.replace('Z', '+00:00')).date()
                except:
                    data_adesao = None
            elif isinstance(data_adesao, datetime.datetime):
                data_adesao = data_adesao.date()
            
            # Converter data_cancelamento para date
            if data_cancelamento and isinstance(data_cancelamento, str):
                try:
                    data_cancelamento = datetime.datetime.fromisoformat(data_cancelamento.replace('Z', '+00:00')).date()
                except:
                    data_cancelamento = None
            elif isinstance(data_cancelamento, datetime.datetime):
                data_cancelamento = data_cancelamento.date()
            
            # Converter datas de filtro
            inicio = None
            fim = None
            
            if data_inicio:
                try:
                    inicio = datetime.datetime.strptime(data_inicio, '%Y-%m-%d').date()
                except:
                    logger.warning(f"Formato inválido para data_inicio: {data_inicio}")
            
            if data_fim:
                try:
                    fim = datetime.datetime.strptime(data_fim, '%Y-%m-%d').date()
                except:
                    logger.warning(f"Formato inválido para data_fim: {data_fim}")
            
            # Verificar se cliente está no período
            # Cliente é incluído se:
            # 1. Aderiu no período (data_adesao entre inicio e fim) OU
            # 2. Deu churn no período (data_cancelamento entre inicio e fim)
            
            incluir_cliente = False
            
            # Verificar adesão no período
            if data_adesao:
                adesao_no_periodo = True
                if inicio and data_adesao < inicio:
                    adesao_no_periodo = False
                if fim and data_adesao > fim:
                    adesao_no_periodo = False
                if adesao_no_periodo:
                    incluir_cliente = True
            
            # Verificar churn no período
            if data_cancelamento and not incluir_cliente:
                churn_no_periodo = True
                if inicio and data_cancelamento < inicio:
                    churn_no_periodo = False
                if fim and data_cancelamento > fim:
                    churn_no_periodo = False
                if churn_no_periodo:
                    incluir_cliente = True
            
            # Se não está no período, pular este cliente
            if not incluir_cliente:
                continue
        
        results.append(cliente)

    cur.close()
    conn.close()
        
    # sanitize results to ensure all dates are converted
    results_sanitized = sanitize_for_json(results)

    return results_sanitized

def clientes_to_json():
    """Buscar dados do banco e retornar como dicionário indexado por client_id"""
    raw_list = fetch_clientes()
    
    # Converter lista de dicionários para dicionário indexado por client_id
    clientes_dict = {}
    for cliente_data in raw_list:
        # Garantir que temos um client_id válido
        client_id = cliente_data.get('client_id')
        if client_id:
            # Calculate TMO (Tempo Médio de Onboarding) if dates are available
            data_start = cliente_data.get('data_start_onboarding')
            data_end = cliente_data.get('data_end_onboarding')
            if data_start and data_end:
                data_start = datetime.datetime.fromisoformat(data_start)
                data_end = datetime.datetime.fromisoformat(data_end)
                tmo = (data_end - data_start).days
                cliente_data['tmo'] = tmo
            else:
                cliente_data['tmo'] = None

            clientes_dict[int(client_id)] = cliente_data
    
    return clientes_dict

def clientes_to_dataframe(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
):
    """
    Converter clientes para DataFrame pandas.
    
    Filtra por período considerando tanto adesões quanto churns.
    
    Args:
        data_inicio: Data inicial para filtro (formato: YYYY-MM-DD)
        data_fim: Data final para filtro (formato: YYYY-MM-DD)
    
    Returns:
        DataFrame pandas com dados dos clientes que aderiram OU deram churn no período
    """
    import pandas as pd
    raw_list = fetch_clientes(data_inicio, data_fim)
    df = pd.DataFrame(raw_list)
    return df

def to_json_file(filename='clientes.json'):
    """Salvar clientes em arquivo JSON (uso opcional)"""
    try:
        clientes = clientes_to_json()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(clientes, f, indent=4, ensure_ascii=False)
        print(f"Arquivo {filename} salvo com sucesso!")
    except Exception as e:
        print(f"Erro ao salvar arquivo {filename}: {e}")

def fetch_tenant_logins(tenant_id: int) -> Dict:
    """
    Busca logins de um tenant no banco de dados MySQL.
    
    Args:
        tenant_id: ID do tenant para buscar os logins
    
    Returns:
        Dicionário com estatísticas e lista de logins
    """
    # Importar aqui para evitar dependência circular
    from .health_scores import get_conn
    
    conn = get_conn()
    if conn is None:
        raise Exception("Falha ao conectar ao banco de dados MySQL")
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(LOGINS_BY_TENANT, (tenant_id,))
        logins = cursor.fetchall()
        cursor.close()
        
        # Processar dados
        total_logins = len(logins)
        
        # Converter datetime para string
        logins_processed = []
        for login in logins:
            login_data = {
                'usuario_nome': login['usuario_nome'],
                'usuario_email': login['usuario_email'],
                'data_login': login['data_login'].isoformat() if login['data_login'] else None,
                'data': str(login['data']) if login['data'] else None,
                'hora': str(login['hora']) if login['hora'] else None
            }
            logins_processed.append(login_data)
        
        # Calcular estatísticas
        dias_com_login = len(set(login['data'] for login in logins if login['data']))
        ultimo_login = logins_processed[0] if logins_processed else None
        
        logger.info(f"✅ Encontrados {total_logins} logins para tenant_id {tenant_id}")
        
        return {
            'tenant_id': tenant_id,
            'periodo': '30 dias',
            'total_logins': total_logins,
            'dias_com_login': dias_com_login,
            'ultimo_login': ultimo_login,
            'logins': logins_processed
        }
        
    except Exception as e:
        logger.error(f"Erro ao executar query de logins: {e}")
        raise
    finally:
        conn.close()

def calculate_clientes_evolution(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
) -> List[Dict]:
    """
    Calcula a evolução mensal de clientes pagantes.
    
    Retorna dados agregados por mês com:
    - Novos clientes pagantes (data_adesao no mês)
    - Churns de clientes pagantes (data_cancelamento no mês)
    - Total acumulado de clientes ativos
    
    Args:
        data_inicio: Data inicial para filtro (YYYY-MM-DD)
        data_fim: Data final para filtro (YYYY-MM-DD)
    
    Returns:
        Lista de dicionários com evolução mensal:
        [
            {
                "mes": "jan/2024",
                "novos_clientes": 45,
                "churns": 12,
                "clientes_ativos": 230
            },
            ...
        ]
    """
    from collections import defaultdict
    
    logger.info(f"Calculando evolução de clientes (período: {data_inicio} a {data_fim})...")
    
    # Buscar todos os clientes do período
    clientes_list = fetch_clientes(data_inicio, data_fim)
    
    # Filtrar apenas clientes pagantes (valor > 0)
    clientes_pagantes = [
        c for c in clientes_list 
        if c.get('valor') and float(c.get('valor', 0)) > 0
    ]
    
    logger.info(f"Total de clientes pagantes no período: {len(clientes_pagantes)}")
    
    # Agrupar por mês
    months_map = defaultdict(lambda: {"novos": 0, "churns": 0})
    
    for cliente in clientes_pagantes:
        # Processar data de adesão (novos clientes pagantes)
        data_adesao = cliente.get('data_adesao')
        if data_adesao:
            try:
                if isinstance(data_adesao, str):
                    date = datetime.datetime.fromisoformat(data_adesao.replace('Z', '+00:00'))
                elif isinstance(data_adesao, datetime.datetime):
                    date = data_adesao
                elif isinstance(data_adesao, datetime.date):
                    date = datetime.datetime.combine(data_adesao, datetime.time.min)
                else:
                    continue
                    
                month_key = f"{date.year}-{str(date.month).zfill(2)}"
                months_map[month_key]["novos"] += 1
            except Exception as e:
                logger.warning(f"Erro ao processar data_adesao do cliente {cliente.get('client_id')}: {e}")
        
        # Processar data de cancelamento (churns de clientes pagantes)
        data_cancelamento = cliente.get('data_cancelamento')
        if data_cancelamento:
            try:
                if isinstance(data_cancelamento, str):
                    date = datetime.datetime.fromisoformat(data_cancelamento.replace('Z', '+00:00'))
                elif isinstance(data_cancelamento, datetime.datetime):
                    date = data_cancelamento
                elif isinstance(data_cancelamento, datetime.date):
                    date = datetime.datetime.combine(data_cancelamento, datetime.time.min)
                else:
                    continue
                    
                month_key = f"{date.year}-{str(date.month).zfill(2)}"
                months_map[month_key]["churns"] += 1
            except Exception as e:
                logger.warning(f"Erro ao processar data_cancelamento do cliente {cliente.get('client_id')}: {e}")
    
    # Ordenar por mês
    sorted_months = sorted(months_map.items(), key=lambda x: x[0])
    
    # Calcular clientes ativos acumulados
    clientes_ativos = 0
    evolution = []
    month_names = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
    
    for month_key, data in sorted_months:
        clientes_ativos += data["novos"] - data["churns"]
        
        # Formatar mês para exibição (ex: "jan/2024")
        year, month = month_key.split('-')
        mes_formatado = f"{month_names[int(month) - 1]}/{year}"
        
        evolution.append({
            "mes": mes_formatado,
            "novos_clientes": data["novos"],
            "churns": data["churns"],
            "clientes_ativos": clientes_ativos
        })
    
    logger.info(f"✅ Evolução calculada: {len(evolution)} meses")
    return evolution

# REMOVED: to_json_file() - não deve ser executado no import
# Se precisar executar, chame explicitamente: python -m api.scripts.clientes
if __name__ == "__main__":
    to_json_file()