import psycopg2
import os
from dotenv import load_dotenv
import json
import datetime
from ..lib.queries import SELECT_CLIENTES, LOGINS_BY_TENANT
from ..lib.models import Cliente
from typing import Dict
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

def fetch_clientes():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(SELECT_CLIENTES)
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]

    results = []
    for row in rows:
        results.append(dict(zip(columns, row)))

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
            clientes_dict[int(client_id)] = cliente_data
    
    return clientes_dict

def clientes_to_dataframe():
    """Converter clientes para DataFrame pandas"""
    import pandas as pd
    raw_list = fetch_clientes()
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

# REMOVED: to_json_file() - não deve ser executado no import
# Se precisar executar, chame explicitamente: python -m api.scripts.clientes
if __name__ == "__main__":
    to_json_file()