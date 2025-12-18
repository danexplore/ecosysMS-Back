import os
from dotenv import load_dotenv
import pandas as pd
import requests
import time
import re
import logging
from functools import lru_cache
from typing import Dict, List, Tuple, Optional
from ..lib.db_connection import get_conn, release_conn

load_dotenv()
logger = logging.getLogger(__name__)

def validate_cnpj(cnpj: str) -> Optional[str]:
    """Valida e normaliza CNPJ (remove caracteres não numéricos)"""
    if not cnpj:
        return None
    cnpj_clean = re.sub(r'\D', '', str(cnpj))
    return cnpj_clean if len(cnpj_clean) >= 11 else None

def insert_cliente(name: str, cnpj: str) -> Tuple[bool, str, Optional[int], Optional[Dict]]:
    """Insere um cliente via API e retorna o store_id"""
    # Validar CNPJ
    cnpj_clean = validate_cnpj(cnpj)
    if not cnpj_clean:
        return False, f"❌ CNPJ inválido: {cnpj}", None, None
    
    payload = {
        "name": name[:100],  # Limitar tamanho
        "display_name": name[:100],
        "cnpj": cnpj_clean,
        "_persist_cnpj_bank_credentials": True
    }
    
    session = get_session()
    headers = {
        "Authorization": f"Bearer {os.getenv('CREDERE_STORE_TOKEN')}"
    }
    
    try:
        response = session.post(
            "https://app.meucredere.com.br/api/v1/stores",
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 201:
            response_data = response.json()
            store_id = response_data.get('store', {}).get('id')
            logger.info(f"✅ Cliente {name} inserido (ID: {store_id})")
            return True, f"✅ Cliente {name} inserido com sucesso.", store_id, response_data
        else:
            logger.warning(f"❌ Erro ao inserir {name}: {response.status_code}")
            return False, f"❌ Erro ao inserir {name}: {response.status_code}", None, response.text
    except requests.Timeout:
        logger.error(f"⏰ Timeout ao inserir {name}")
        return False, f"❌ Timeout ao processar {name}", None, None
    except Exception as e:
        logger.error(f"❌ Exceção ao processar {name}: {str(e)}")
        return False, f"❌ Exceção ao processar {name}: {str(e)}", None, None
    
def persist_cnpj_credentials(store_id: int, nome: str) -> Tuple[bool, str, Optional[int]]:
    """Persist CNPJ Bank Credentials para uma loja"""
    url = f"https://app.meucredere.com.br/api/v1/stores/{store_id}/persist_cnpj_bank_credentials"
    
    session = get_session()
    headers = {
        "Authorization": f"Bearer {os.getenv('CREDERE_PERSISTS_TOKEN')}"
    }
    
    params = {"bank_codes": "341,342,422,336"}
    
    try:
        response = session.get(url, headers=headers, params=params, timeout=15)
        
        if response.status_code in [200, 201, 204]:
            logger.info(f"✅ {nome} (ID:{store_id}) - Credenciais persistidas")
            return True, f"✅ {nome} - Credenciais persistidas", response.status_code
        else:
            logger.warning(f"❌ {nome} (ID:{store_id}) - Erro {response.status_code}")
            return False, f"❌ {nome} - Erro {response.status_code}", response.text
    except requests.Timeout:
        logger.error(f"⏰ Timeout ao persistir credenciais de {nome}")
        return False, f"❌ {nome} - Timeout", None
    except Exception as e:
        logger.error(f"❌ {nome} - Exceção: {str(e)}")
        return False, f"❌ {nome} - Exceção: {str(e)}", None

@lru_cache(maxsize=1)
def fetch_existing_clientes() -> Dict[str, str]:
    """
    Busca os CNPJs dos clientes já existentes no Credere (com cache).
    
    Returns:
        Dict[str, str]: Dicionário com CNPJs normalizados como chave e nome como valor
        Exemplo: {"08098404000171": "Empresa ABC Ltda", ...}
    """
    clients_cnpjs = {}
    
    session = get_session()
    headers = {
        "Authorization": f"Bearer {os.getenv('CREDERE_STORE_TOKEN')}"
    }
    
    try:
        response = session.get(
            "https://app.meucredere.com.br/api/v1/stores",
            headers=headers,
            params={"per_page": 500},
            timeout=10
        )
        
        if response.status_code == 200:
            stores = response.json().get('stores', [])
            # Manter CNPJs exatamente como retornados pela API (sem zfill)
            # Isso permite inserir CNPJs com formatação diferente
            clients_cnpjs = {}
            for store in stores:
                cnpj_raw = store.get('cnpj')
                if cnpj_raw:
                    cnpj_normalized = validate_cnpj(cnpj_raw)
                    if cnpj_normalized:
                        # NÃO usar zfill - manter formato original
                        clients_cnpjs[cnpj_normalized] = store['name']
            
            logger.info(f"✅ {len(clients_cnpjs)} clientes existentes carregados")
        else:
            logger.error(f"❌ Erro ao buscar lojas: {response.status_code}")
    except requests.Timeout:
        logger.error("⏰ Timeout ao buscar lojas existentes")
    except Exception as e:
        logger.error(f"❌ Exceção ao buscar lojas: {str(e)}")
    
    return clients_cnpjs

def clear_credere_cache():
    """Limpa o cache de clientes do Credere"""
    fetch_existing_clientes.cache_clear()
    logger.info("🗑️ Cache do Credere limpo")

def check_existing_clients(cnpjs: List[str]) -> List[Dict[str, any]]:
    """
    Verifica quais CNPJs já existem no sistema Credere.
    
    Args:
        cnpjs: Lista de CNPJs (podem estar formatados ou não)
        
    Returns:
        Lista de dicionários com status de cada CNPJ:
        [
            {
                "cnpj_original": "44.285.354/0001-03",
                "cnpj_normalized": "44285354000103",
                "exists": True,
                "client_name": "Empresa XYZ",
                "status": "✅ Cliente existe no Credere"
            },
            ...
        ]
    """
    existing_clients = fetch_existing_clientes()
    results = []
    
    for cnpj_input in cnpjs:
        cnpj_normalized = validate_cnpj(cnpj_input)
        
        # CNPJ inválido
        if not cnpj_normalized:
            results.append({
                "cnpj_original": cnpj_input,
                "cnpj_normalized": None,
                "exists": False,
                "client_name": None,
                "status": "❌ CNPJ inválido",
                "valid": False
            })
            continue
        
        # Verificar se existe (comparação exata, sem zfill)
        if cnpj_normalized in existing_clients:
            results.append({
                "cnpj_original": cnpj_input,
                "cnpj_normalized": cnpj_normalized,
                "exists": True,
                "client_name": existing_clients[cnpj_normalized],
                "status": "✅ Cliente existe no Credere",
                "valid": True
            })
        else:
            results.append({
                "cnpj_original": cnpj_input,
                "cnpj_normalized": cnpj_normalized,
                "exists": False,
                "client_name": None,
                "status": "⚠️ Cliente não encontrado no Credere",
                "valid": True
            })
    
    logger.info(f"📊 Verificados {len(results)} CNPJs: {sum(1 for r in results if r['exists'])} existem")
    return results

def process_client(client: Dict[str, str]) -> Dict:
    """
    Processa um único cliente para inserção no Credere.
    
    Args:
        client: Dicionário com 'name' e 'cnpj' do cliente
        
    Returns:
        dict: Resultado do processamento com status e mensagens
    """
    name = client.get('name', 'Cliente')[:20]
    cnpj = validate_cnpj(client.get('cnpj', ''))
    
    if not cnpj:
        return {
            'success': False,
            'client_name': name,
            'cnpj': client.get('cnpj', ''),
            'store_id': None,
            'insert_message': '❌ CNPJ inválido',
            'persist_success': None,
            'persist_message': None,
            'already_exists': False
        }
    
    cnpj = cnpj.zfill(14)
    
    # Verificar se o cliente já existe (usa cache) - comparação exata
    existing_clients = fetch_existing_clientes()
    if cnpj in existing_clients:
        logger.info(f"⚠️ Cliente {name} ({cnpj}) já existe")
        return {
            'success': False,
            'client_name': name,
            'cnpj': cnpj,
            'store_id': None,
            'insert_message': f"⚠️ Cliente já existe no Credere",
            'persist_success': None,
            'persist_message': None,
            'already_exists': True
        }
    
    # Inserir cliente
    success, msg, store_id, resp_data = insert_cliente(name, cnpj)
    
    result = {
        'success': success,
        'client_name': name,
        'cnpj': cnpj,
        'store_id': store_id,
        'insert_message': msg,
        'persist_success': None,
        'persist_message': None,
        'already_exists': False
    }
    
    # Se inserção foi bem-sucedida, persistir credenciais
    if success and store_id:
        persist_success, persist_msg, persist_resp = persist_cnpj_credentials(store_id, name)
        result['persist_success'] = persist_success
        result['persist_message'] = persist_msg
    
    return result


def process_clients(clients: List[Dict[str, str]]) -> List[Dict]:
    """
    Processa uma lista de clientes em lote.
    
    Args:
        clients: Lista de dicionários com 'name' e 'cnpj'
        
    Returns:
        list: Lista de resultados de cada cliente processado
    """
    logger.info(f"🚀 Iniciando processamento de {len(clients)} clientes")
    
    # Normalizar CNPJs e filtrar já existentes
    cnpjs = [client.get('cnpj', '') for client in clients]
    check_results = check_existing_clients(cnpjs)
    
    # Criar set de CNPJs normalizados que já existem
    existing_cnpjs = {
        r['cnpj_normalized'] 
        for r in check_results 
        if r['exists'] and r['cnpj_normalized']
    }
    
    clients_to_process = [
        client for client in clients
        if validate_cnpj(client.get('cnpj', '')) not in existing_cnpjs
    ]
    
    logger.info(f"📋 {len(existing_cnpjs)} já existem, processando {len(clients_to_process)} novos")
    
    results = []
    for i, client in enumerate(clients_to_process, 1):
        logger.info(f"[{i}/{len(clients_to_process)}] Processando {client.get('name', 'Cliente')}...")
        result = process_client(client)
        results.append(result)
        
        if i < len(clients_to_process):  # Não esperar no último
            time.sleep(0.2)  # Rate limiting
    
    logger.info(f"✅ Processamento concluído: {len(results)} clientes")
    return results