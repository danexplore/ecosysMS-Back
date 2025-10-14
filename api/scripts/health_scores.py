import mysql.connector
from mysql.connector import Error, pooling
import os
import json
from dotenv import load_dotenv
from ..lib.queries import (PRIMEIRO_PILAR, SEGUNDO_PILAR, 
                         TERCEIRO_PILAR, QUARTO_PILAR, 
                         ECONVERSA_STATUS, INTEGRATORS_CONNECTED)
from ..scripts.clientes import clientes_to_dataframe
from typing import Dict, List
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import threading

load_dotenv()
logger = logging.getLogger(__name__)

# Connection pool global e lock para thread-safety
connection_pool = None
pool_lock = threading.Lock()

def init_connection_pool():
    """Inicializa o pool de conexões MySQL (thread-safe)."""
    global connection_pool
    
    # Double-check locking pattern para thread-safety
    if connection_pool is not None:
        return connection_pool
    
    with pool_lock:
        # Verificar novamente dentro do lock
        if connection_pool is not None:
            return connection_pool
        
        try:
            connection_pool = pooling.MySQLConnectionPool(
                pool_name="ecosys_pool",
                pool_size=5,  # Número de conexões no pool
                pool_reset_session=True,
                host=os.getenv('DB_HOST_ECOSYS'),
                database=os.getenv('DB_NAME_ECOSYS'),
                user=os.getenv('DB_USER_ECOSYS'),
                password=os.getenv('DB_PASSWORD_ECOSYS'),
                port=3306,
                autocommit=True,
                connect_timeout=10
            )
            logger.info("✅ Pool de conexões MySQL criado com sucesso")
            return connection_pool
        except Error as e:
            logger.error(f"❌ Erro ao criar pool de conexões: {e}")
            return None

def get_conn():
    """Obtém uma conexão do pool."""
    global connection_pool
    
    if connection_pool is None:
        connection_pool = init_connection_pool()
    
    try:
        return connection_pool.get_connection()
    except Error as e:
        logger.error(f"Erro ao obter conexão do pool: {e}")
        return None

def execute_query(conn, query):
    """Executa query e retorna DataFrame."""
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        
        df = pd.DataFrame(results)
        return df
        
    except Error as e:
        logger.error(f"Erro ao executar query: {e}")
        return None

def execute_queries_parallel(queries: List[tuple]) -> Dict[str, pd.DataFrame]:
    """
    Executa múltiplas queries em paralelo.
    
    Args:
        queries: Lista de tuplas (nome, query_sql)
    
    Returns:
        Dicionário com nome: DataFrame
    """
    results = {}
    
    def execute_single_query(name: str, query: str):
        """Executa uma única query em uma conexão separada"""
        conn = get_conn()
        if conn is None:
            logger.error(f"Falha ao obter conexão para query {name}")
            return name, None
        
        try:
            df = execute_query(conn, query)
            return name, df
        finally:
            conn.close()
    
    # Executar queries em paralelo usando ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=min(len(queries), 5)) as executor:
        future_to_query = {
            executor.submit(execute_single_query, name, query): name 
            for name, query in queries
        }
        
        for future in as_completed(future_to_query):
            name, df = future.result()
            if df is not None:
                results[name] = df
                logger.info(f"Query {name} executada com sucesso")
            else:
                logger.error(f"Falha ao executar query {name}")
    
    return results

def merge_dataframes():
    """Executa queries em paralelo e processa os resultados."""
    
    # Definir todas as queries a serem executadas
    queries = [
        ("tenants", "SELECT id, name, cnpj, slug FROM tenants;"),
        ("primeiro_pilar", PRIMEIRO_PILAR),
        ("segundo_pilar", SEGUNDO_PILAR),
        ("terceiro_pilar", TERCEIRO_PILAR),
        ("quarto_pilar", QUARTO_PILAR),
        ("econversa", ECONVERSA_STATUS),
        ("integrators", INTEGRATORS_CONNECTED)
    ]
    
    # Executar queries em paralelo
    logger.info("Iniciando execução paralela de queries...")
    dfs = execute_queries_parallel(queries)
    
    # Verificar se todas as queries foram bem-sucedidas
    required_keys = ["tenants", "primeiro_pilar", "segundo_pilar", "terceiro_pilar", "quarto_pilar"]
    if not all(key in dfs for key in required_keys):
        raise Exception("Falha ao executar queries necessárias")
    
    # Extrair DataFrames
    df_tenants = dfs["tenants"]
    df_primeiro_pilar = dfs["primeiro_pilar"]
    df_segundo_pilar = dfs["segundo_pilar"]
    df_terceiro_pilar = dfs["terceiro_pilar"]
    df_quarto_pilar = dfs["quarto_pilar"]
    df_econversa = dfs.get("econversa", pd.DataFrame())
    df_integrators = dfs.get("integrators", pd.DataFrame())
    
    logger.info("Queries executadas com sucesso, iniciando processamento...")
    
    # Otimização: Converter tipos de dados uma única vez, antes dos merges
    # Isso é mais eficiente do que múltiplas conversões
    numeric_cols_float = [
        'score_engajamento', 'score_movimentacao_estoque', 'score_crm', 'score_adoption',
        'qntd_acessos_30d', 'dias_desde_ultimo_acesso', 'qntd_entradas_30d',
        'dias_desde_ultima_entrada', 'qntd_saidas_30d', 'dias_desde_ultima_saida',
        'qntd_leads_30d', 'dias_desde_ultimo_lead'
    ]
    
    # Converter todos os DataFrames de uma vez
    for df in [df_primeiro_pilar, df_segundo_pilar, df_terceiro_pilar, df_quarto_pilar]:
        for col in numeric_cols_float:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce', downcast='float')
    
    # Otimização: Usar merge com copy=False para evitar cópias desnecessárias
    # e especificar validate para garantir integridade
    df_fusao = df_tenants.merge(
        df_primeiro_pilar,
        left_on='id',
        right_on='tenant_id',
        how='left',
        suffixes=('', '_p1'),
        copy=False
    )
    
    # Merges subsequentes
    df_fusao = df_fusao.merge(
        df_segundo_pilar,
        left_on='id',
        right_on='tenant_id',
        how='left',
        suffixes=('', '_p2'),
        copy=False
    )
    
    df_fusao = df_fusao.merge(
        df_terceiro_pilar,
        left_on='id',
        right_on='tenant_id',
        how='left',
        suffixes=('', '_p3'),
        copy=False
    )
    
    # Quarto Pilar - Score Adoption
    df_fusao = df_fusao.merge(
        df_quarto_pilar,
        left_on='id',
        right_on='tenant_id',
        how='left',
        suffixes=('', '_p4'),
        copy=False
    )
    
    # Merge com status do eConversa (se disponível)
    if not df_econversa.empty:
        df_fusao = df_fusao.merge(
            df_econversa,
            left_on='id',
            right_on='id',
            how='left',
            copy=False
        )
    
    # Merge com integradores conectados (se disponível)
    if not df_integrators.empty:
        df_fusao = df_fusao.merge(
            df_integrators,
            left_on='id',
            right_on='tenant_id',
            how='left',
            copy=False
        )
    
    # Otimização: Usar operações vetorizadas ao invés de apply
    # Converter status_econversa para booleano
    if 'status_econversa' in df_fusao.columns:
        df_fusao['econversa_status'] = (
            df_fusao['status_econversa']
            .fillna('connecting')
            .str.lower() == 'open'
        )
    else:
        df_fusao['econversa_status'] = False
    
    # Converter string de integradores para lista
    if 'integrators_connected' in df_fusao.columns:
        df_fusao['integrators_connected'] = df_fusao['integrators_connected'].fillna('').str.split(', ')
        # Limpar listas vazias
        df_fusao['integrators_connected'] = df_fusao['integrators_connected'].apply(
            lambda x: [i for i in x if i] if isinstance(x, list) else []
        )
    else:
        df_fusao['integrators_connected'] = [[] for _ in range(len(df_fusao))]
    
    # Renomear id para tenant_id
    if 'id' in df_fusao.columns:
        df_fusao = df_fusao.rename(columns={'id': 'tenant_id'})
    
    # Otimização: Remover colunas duplicadas de uma vez
    cols_to_drop = [col for col in df_fusao.columns 
                    if col.startswith('tenant_id_') or 
                    (col != 'tenant_id' and 'tenant_id' in col)]
    if cols_to_drop:
        df_fusao = df_fusao.drop(columns=cols_to_drop)
        
    # Definir os pesos para cada pilar
    WEIGHTS = {
        'score_engajamento': 0.30,
        'score_movimentacao_estoque': 0.30,
        'score_crm': 0.20,
        'score_adoption': 0.20
    }

    # Otimização: Calcular score total usando operações vetorizadas
    score_columns = list(WEIGHTS.keys())
    
    # Garantir que colunas de score existam e sejam numéricas
    for col in score_columns:
        if col in df_fusao.columns:
            df_fusao[col] = pd.to_numeric(df_fusao[col], errors='coerce').fillna(0.0)
    
    # Calcular score total de forma vetorizada
    df_fusao['score_total'] = sum(
        df_fusao[col] * weight 
        for col, weight in WEIGHTS.items() 
        if col in df_fusao.columns
    )
    
    logger.info("Score total calculado com sucesso")
    
    # Selecionar e reordenar as colunas finais
    colunas_finais = [
        'tenant_id', 'slug', 'name', 'cnpj', 'qntd_acessos_30d',
        'dias_desde_ultimo_acesso', 'score_engajamento',
        'qntd_entradas_30d', 'dias_desde_ultima_entrada',
        'qntd_saidas_30d', 'dias_desde_ultima_saida',
        'score_movimentacao_estoque', 'qntd_leads_30d',
        'dias_desde_ultimo_lead', 'score_crm',
        'econversa_status', 'integrators_connected', 'ads_status', 'reports_status',
        'contracts_status', 'score_adoption', 'score_total'
    ]
    
    # Manter apenas as colunas que existem no DataFrame
    colunas_existentes = [col for col in colunas_finais if col in df_fusao.columns]
    df_fusao = df_fusao[colunas_existentes]

    # Obter lista de clientes
    clientes = clientes_to_dataframe()
    
    # Otimização: Conversões de tipo em batch
    df_fusao['cnpj'] = pd.to_numeric(df_fusao['cnpj'], errors='coerce').fillna(0).astype('int64')
    clientes['cnpj'] = pd.to_numeric(clientes['cnpj'], errors='coerce').fillna(0).astype('int64')
    
    # Filtrar e limpar dados
    df_fusao = df_fusao[df_fusao['cnpj'].isin(clientes['cnpj'])]
    df_fusao = df_fusao.dropna(subset=['tenant_id'])
    df_fusao.sort_values(by='score_total', ascending=False, inplace=True)
    
    # Remover colunas duplicadas
    df_fusao = df_fusao.loc[:, ~df_fusao.columns.duplicated()]
    
    # Reordenar colunas
    colunas_ordenadas = ['tenant_id', 'slug'] + [
        col for col in df_fusao.columns if col not in ['tenant_id', 'slug']
    ]
    df_fusao = df_fusao[colunas_ordenadas]
    
    # Categorização usando função apply (mais seguro que pd.cut com labels duplicados)
    def categorizar_cliente(score):
        if pd.isna(score) or score <= 0.3:
            return 'Crítico'
        elif score <= 0.6:
            return 'Normal'
        elif score <= 0.8:
            return 'Saudável'
        else:
            return 'Campeão'
    
    df_fusao['categoria'] = df_fusao['score_total'].apply(categorizar_cliente)
    
    logger.info(f"Distribuição das categorias:\n{df_fusao['categoria'].value_counts()}")
    
    # Otimização: Conversões de tipo em batch antes da iteração
    int_columns = [
        'cnpj', 'qntd_acessos_30d', 'dias_desde_ultimo_acesso',
        'qntd_entradas_30d', 'dias_desde_ultima_entrada',
        'qntd_saidas_30d', 'dias_desde_ultima_saida',
        'qntd_leads_30d', 'dias_desde_ultimo_lead'
    ]
    
    float_columns = [
        'score_total', 'score_engajamento', 'score_movimentacao_estoque',
        'score_crm', 'score_adoption'
    ]
    
    # Aplicar conversões de tipo de uma vez
    for col in int_columns:
        if col in df_fusao.columns:
            df_fusao[col] = pd.to_numeric(df_fusao[col], errors='coerce').fillna(0).astype('int64')
    
    for col in float_columns:
        if col in df_fusao.columns:
            df_fusao[col] = pd.to_numeric(df_fusao[col], errors='coerce').round(2)
    
    # Converter DataFrame para dicionário de forma otimizada
    resultado = {}
    
    # Otimização: Usar itertuples ao invés de iterrows (muito mais rápido)
    for row in df_fusao.itertuples(index=False):
        if pd.notna(row.slug):
            # Criar estrutura de dados otimizada
            resultado[row.slug] = {
                'tenant_id': str(row.tenant_id) if pd.notna(row.tenant_id) else None,
                'name': row.name if pd.notna(row.name) else None,
                'cnpj': int(row.cnpj) if pd.notna(row.cnpj) else 0,
                'slug': row.slug,
                'scores': {
                    'engajamento': round(float(row.score_engajamento), 2) if pd.notna(row.score_engajamento) else 0.0,
                    'adocao': round(float(row.score_adoption), 2) if pd.notna(row.score_adoption) else 0.0,
                    'estoque': round(float(row.score_movimentacao_estoque), 2) if pd.notna(row.score_movimentacao_estoque) else 0.0,
                    'crm': round(float(row.score_crm), 2) if pd.notna(row.score_crm) else 0.0,
                    'total': round(float(row.score_total), 2) if pd.notna(row.score_total) else 0.0
                },
                'integrations': {
                    'econversa_status': bool(row.econversa_status) if hasattr(row, 'econversa_status') else False,
                    'integrators_connected': row.integrators_connected if hasattr(row, 'integrators_connected') else []
                },
                'metrics': {
                    'acessos': {
                        'quantidade_30d': int(row.qntd_acessos_30d) if pd.notna(row.qntd_acessos_30d) else 0,
                        'dias_ultimo_acesso': int(row.dias_desde_ultimo_acesso) if pd.notna(row.dias_desde_ultimo_acesso) else 9999
                    },
                    'entradas': {
                        'quantidade_30d': int(row.qntd_entradas_30d) if pd.notna(row.qntd_entradas_30d) else 0,
                        'dias_ultima_entrada': int(row.dias_desde_ultima_entrada) if pd.notna(row.dias_desde_ultima_entrada) else 9999
                    },
                    'saidas': {
                        'quantidade_30d': int(row.qntd_saidas_30d) if pd.notna(row.qntd_saidas_30d) else 0,
                        'dias_ultima_saida': int(row.dias_desde_ultima_saida) if pd.notna(row.dias_desde_ultima_saida) else 9999
                    },
                    'leads': {
                        'quantidade_30d': int(row.qntd_leads_30d) if pd.notna(row.qntd_leads_30d) else 0,
                        'dias_ultimo_lead': int(row.dias_desde_ultimo_lead) if pd.notna(row.dias_desde_ultimo_lead) else 9999
                    }
                },
                'categoria': str(row.categoria)
            }
    
    logger.info(f"Processamento concluído. {len(resultado)} clientes processados.")
    return resultado

if __name__ == "__main__":
    resultado = merge_dataframes()
    print("\nProcessamento concluído.")
    
    try:
        # Reformatar com indentação e codificação adequada
        formatted_json = json.dumps(
            resultado, 
            indent=2,
            ensure_ascii=False,
            sort_keys=False
        )
        
        # Imprimir JSON formatado
        print("\nResultados formatados:")
        print(formatted_json)
        
        # Salvar o JSON formatado em um arquivo
        with open('score_saude_clientes.json', 'w', encoding='utf-8') as f:
            f.write(formatted_json)
        print("\nJSON formatado salvo em 'score_saude_clientes.json'")
            
    except (json.JSONDecodeError, TypeError) as e:
        print(f"\nErro ao formatar JSON: {e}")