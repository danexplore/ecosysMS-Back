import psycopg2
import os
from dotenv import load_dotenv
import pandas as pd
import requests
import time
from functools import lru_cache

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

def insert_cliente(name, cnpj):
    """Insere um cliente via API e retorna o store_id"""
    payload = {
        "name": name,
        "display_name": name,
        "cnpj": str(cnpj),  # Garante que seja string
        "_persist_cnpj_bank_credentials": True
    }
    
    headers = {
        "Authorization": f"Bearer {os.getenv('CREDERE_STORE_TOKEN')}",
        "Content-Type": "application/json",
        "accept": "application/json"
    }
    
    try:
        response = requests.post("https://app.meucredere.com.br/api/v1/stores", json=payload, headers=headers)
        
        if response.status_code == 201:
            response_data = response.json()
            store_id = response_data.get('store', {}).get('id')
            return True, f"✅ Cliente {name} inserido com sucesso.", store_id, response_data
        else:
            return False, f"❌ Erro ao inserir {name}: {response.status_code}", None, response.text
    except Exception as e:
        return False, f"❌ Exceção ao processar {name}: {str(e)}", None, None
    
def persist_cnpj_credentials(store_id, nome):
    """Persist CNPJ Bank Credentials para uma loja"""
    
    # Constrói a URL com os parâmetros de banco
    url = f"https://app.meucredere.com.br/api/v1/stores/{store_id}/persist_cnpj_bank_credentials?bank_codes=341,342,422,336"
    
    headers = {
        "Authorization": f"Bearer {os.getenv('CREDERE_PERSISTS_TOKEN')}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code in [200, 201, 204]:
            return True, f"✅ {nome} - Credenciais persistidas", response.status_code
        else:
            return False, f"url: {url}\n❌ {nome} - Erro {response.status_code}", response.text
    except Exception as e:
        return False, f"❌ {nome} - Exceção: {str(e)}", None

@lru_cache(maxsize=1)
def fetch_existing_clientes():
    """Busca os CNPJs dos clientes já existentes no Credere"""
    clients_cnpjs = dict()
    
    headers = {
        "Authorization": f"Bearer {os.getenv('CREDERE_STORE_TOKEN')}",
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.get("https://app.meucredere.com.br/api/v1/stores?per_page=500", headers=headers)
        if response.status_code == 200:
            stores = response.json().get('stores', [])
            for store in stores:
                cnpj = store.get('cnpj')
                name = store.get('name')
                if cnpj:
                    clients_cnpjs[cnpj] = name
        else:
            print(f"❌ Erro ao buscar lojas existentes: {response.status_code}")
    except Exception as e:
        print(f"❌ Exceção ao buscar lojas existentes: {str(e)}")
    return clients_cnpjs


def check_existing_clients(cnpjs: list):
    """Verifica quais CNPJs já existem no sistema Credere"""
    existing_cnpjs = set()
    
    existing_cnpjs.add(cnpj for cnpj in fetch_existing_clientes())
    
    return existing_cnpjs

def process_clients(clients: list):
    cnpjs = [client['cnpj'] for client in clients]
    existing_cnpjs = check_existing_clients(cnpjs)
    clients = [client for client in clients if client['cnpj'] not in existing_cnpjs]
    results = []
    for client in clients:
        name = client['name'][0:20]
        cnpj = client['cnpj']
        
        success, msg, store_id, resp_data = insert_cliente(name, cnpj)
        results.append((name, success, msg, store_id, resp_data))
        
        if success and store_id:
            persist_success, persist_msg, persist_resp = persist_cnpj_credentials(store_id, name)
            results.append((name, persist_success, persist_msg, None, persist_resp))
        
        time.sleep(0.20)  # Para evitar rate limiting
    
    return results