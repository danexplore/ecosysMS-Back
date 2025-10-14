import psycopg2
import os
from dotenv import load_dotenv
import json
import datetime
from ..lib.queries import SELECT_CLIENTES
from ..lib.models import Cliente
from typing import Dict

load_dotenv()

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
    raise TypeError ("Type %s not serializable" % type(obj))

def sanitize_for_json(obj):
    """Recursively convert date/datetime objects to ISO strings in structures.

    This ensures nested dicts/lists coming from the DB are JSON-serializable
    even if json.dumps default isn't used everywhere.
    """
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
    # Buscar dados do banco
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
    import pandas as pd
    raw_list = fetch_clientes()
    df = pd.DataFrame(raw_list)
    return df

def to_json_file(filename='clientes.json'):
    # opcional: gravar em arquivo UTF-8
    try:
        clientes = clientes_to_json()
        with open(filename, 'w', encoding='utf-8') as f:
            # Usar ensure_ascii=False para caracteres UTF-8 visíveis
            json.dump(clientes, f, indent=4, ensure_ascii=False)
        print(f"Arquivo {filename} salvo com sucesso!")
    except Exception as e:
        print(f"Erro ao salvar arquivo {filename}: {e}")
        
to_json_file()